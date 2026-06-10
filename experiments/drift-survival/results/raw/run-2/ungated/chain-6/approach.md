# Scheduled Report Exports – Technical Approach

## Architecture Outline

The scheduled report exports feature introduces three primary architectural layers:

1. **Export Engine** — a core service responsible for generating report snapshots in CSV and PDF formats. The engine reads report definitions, evaluates row-level access control based on the requesting user, and serializes data to the requested format. This is intentionally decoupled from the reporting UI to allow both on-demand and batch operations to reuse the same generation logic.

2. **Scheduling & Delivery System** — an asynchronous job processor that manages schedule definitions, evaluates execution cadences (daily/weekly), invokes the export engine at scheduled times, and hands off results to the email delivery pipeline. This layer persists schedule state, tracks execution history, and implements retry logic and failure handling.

3. **API & UI Boundary** — REST and GraphQL endpoints for CRUD operations on schedules, status queries, and on-demand export requests. The UI layer consumes these to present export options and manage schedule configuration. Feature flag logic gates the entire surface here to enable workspace-wide disable.

4. **Audit & Compliance** — a logging layer that records all export events (user, report, format, timestamp, delivery status) to a durable audit table. This layer is invoked at key transition points (export initiated, export completed, delivery succeeded, delivery failed, schedule paused, etc.).

The export engine itself is designed as a pull-based reader over the report data set, with streaming support for large exports to avoid memory exhaustion and to enable the 50 MB rejection gate at generation time.

## Domain Model

### Core Entities

**Report** (existing)
- Exists and represents a configured report with a definition (filters, grouping, columns, etc.)
- Has an associated query that evaluates row-level access control
- Is the subject of an export request

**Export**
- Uniquely identifies one snapshot of a report in a particular format (CSV or PDF)
- Belongs to one Report
- Has a format (CSV | PDF)
- Has a requestor user and a requested timestamp
- Has a size (bytes) recorded at generation time
- Has a delivery status (pending | delivered | failed)
- Is immutable once generated (the artifact is archived; the record is append-only)

**Schedule**
- Defines a recurring export of a specific Report
- Has an owner (user) and a desired cadence (daily | weekly, with time-of-day and optional day-of-week)
- Has an enabled/paused state
- Has a delivery configuration (email recipients — initially the owner only, with future expansion possible)
- Tracks the last execution timestamp and the last successful delivery timestamp
- Is mutable (owner can pause, resume, or delete)

**ScheduleRun**
- Represents a single execution of a Schedule
- Has the schedule it belongs to, a run timestamp, and an export that was generated
- Records the delivery attempt outcome (pending | delivered | failed)
- Records failure details and retry count for the execution

**ExportAuditLog**
- A denormalized audit record capturing: user, report, format, timestamp, export size, delivery status, and metadata
- Is append-only and used for compliance queries

### Relationships

- Report has-many Exports and has-many Schedules (one Report can be exported many times and scheduled many times)
- Schedule has-many ScheduleRuns (one Schedule generates multiple runs over time)
- ScheduleRun has-one Export (each run produces exactly one export artifact)
- ScheduleRun references ExportAuditLog entries
- Export logically triggers zero or more ExportAuditLog entries

## Key Workflows

### On-Demand Export

**Trigger:** User clicks "Export as CSV" or "Export as PDF" on a report view

**Flow:**
1. Client submits an export request to the API with the report ID and requested format
2. API validates the feature flag is enabled and the user has permission to view the report
3. API submits an async job to the export queue (does not block the request)
4. API returns a job ID to the client for polling
5. Export engine picks up the job
6. Engine evaluates the user's row-level access control rules against the report query
7. Engine streams the report result set, serializing to the requested format
8. Engine monitors the output size; if it exceeds 50 MB before completion, the generation is aborted and marked failed
9. On success, the export artifact is persisted to blob storage and an Export record is created
10. An ExportAuditLog entry is written (event: export_completed, size, format)
11. Client polls the job endpoint until completion and presents a download link
12. User downloads the artifact

### Scheduled Export Execution

**Trigger:** Background job processor detects that a schedule is due to execute

**Flow:**
1. Job scheduler evaluates all active (non-paused) schedules at their configured times
2. For each due schedule, the scheduler creates a new ScheduleRun record in pending state
3. The run is enqueued to the export job queue (reuses the same engine as on-demand)
4. Export engine processes the run (identical to on-demand export, with the owning schedule context)
5. On successful generation, the Export is created and the ScheduleRun is marked with the export ID
6. The email delivery system is invoked with the artifact and the schedule owner's email
7. Email delivery: on success, ScheduleRun is marked delivered and ExportAuditLog is written (event: export_delivered)
8. Email delivery: on failure, ScheduleRun is marked failed with retry_count incremented
9. If retry_count reaches 3, the schedule is automatically paused and an admin notification is sent
10. If delivery succeeds but takes multiple retries, ScheduleRun is still marked delivered on final success

### Schedule Lifecycle Management

**Create Schedule:**
1. User specifies report, cadence (daily/weekly), time-of-day, and optionally day-of-week
2. API validates user has permission to export the report
3. Schedule record is created in enabled state
4. First execution is scheduled based on the cadence and current time
5. ExportAuditLog entry: event: schedule_created

**Pause/Resume:**
1. User toggles the enabled flag on the schedule
2. If pausing, no new ScheduleRuns are created for this schedule
3. If resuming, the next execution is recalculated and scheduled immediately
4. ExportAuditLog entry: event: schedule_paused or event: schedule_resumed

**Delete:**
1. User deletes a schedule
2. No new ScheduleRuns are created
3. Existing ScheduleRun records are retained for historical audit
4. ExportAuditLog entry: event: schedule_deleted

### Schedule History & Visibility

**Get Schedule History:**
1. User requests the last 30 ScheduleRun records for a schedule they own
2. API returns runs ordered by timestamp (newest first), with export size and delivery status
3. User can see which runs succeeded and which failed

### Workspace-Level Export Disable

**Enable/Disable Exports (Admin):**
1. Admin uses workspace settings to toggle the export feature flag
2. When disabled, all UI export options are hidden (feature flag check on the frontend)
3. All API export and schedule endpoints reject requests with a 403 error
4. Scheduled exports are not executed while disabled
5. Existing schedules are paused (not deleted) when exports are disabled
6. Existing schedules resume their state when exports are re-enabled
7. ExportAuditLog entry: event: export_feature_disabled or event: export_feature_enabled

## Contracts

### API Surface

**On-Demand Export Initiation**
- **Endpoint:** `POST /api/reports/:reportId/exports`
- **Body:** `{ format: "csv" | "pdf" }`
- **Returns:** `{ jobId: string, reportId: string, format: string, createdAt: timestamp }`
- **Errors:** 403 if user lacks report view permission, 503 if feature flag disabled, 400 if format invalid

**Export Job Status**
- **Endpoint:** `GET /api/exports/:jobId`
- **Returns:** `{ jobId: string, status: "pending" | "completed" | "failed", downloadUrl?: string, errorMessage?: string, size?: number, completedAt?: timestamp }`
- **Errors:** 404 if job not found, 403 if not the requester

**Download Export Artifact**
- **Endpoint:** `GET /api/exports/:jobId/download`
- **Returns:** Binary blob with appropriate Content-Type (text/csv or application/pdf)
- **Errors:** 404 if artifact not found, 403 if not the requester

**Create Schedule**
- **Endpoint:** `POST /api/reports/:reportId/schedules`
- **Body:** `{ cadence: "daily" | "weekly", timeOfDay: "HH:MM", dayOfWeek?: 0-6 }`
- **Returns:** `{ scheduleId: string, reportId: string, cadence: string, timeOfDay: string, dayOfWeek?: number, enabled: true, createdAt: timestamp, nextRunAt: timestamp }`
- **Errors:** 403 if user lacks report permission, 503 if feature disabled, 400 if cadence/time invalid

**List Schedules**
- **Endpoint:** `GET /api/schedules` (user's own) or `GET /api/schedules?owner=userId` (admin)
- **Returns:** `[{ scheduleId, reportId, cadence, timeOfDay, dayOfWeek, enabled, createdAt, nextRunAt, lastRunAt, lastDeliveryStatus }]`
- **Errors:** 403 if querying another user's schedules without admin permission

**Update Schedule (Pause/Resume)**
- **Endpoint:** `PATCH /api/schedules/:scheduleId`
- **Body:** `{ enabled: boolean }`
- **Returns:** Updated schedule object with nextRunAt recalculated
- **Errors:** 403 if not the owner, 404 if schedule not found

**Delete Schedule**
- **Endpoint:** `DELETE /api/schedules/:scheduleId`
- **Returns:** 204 No Content
- **Errors:** 403 if not the owner, 404 if schedule not found

**Get Schedule History**
- **Endpoint:** `GET /api/schedules/:scheduleId/runs?limit=30`
- **Returns:** `[{ runId, scheduledAt, completedAt, exportSize, deliveryStatus, errorMessage?, retryCount }]`
- **Errors:** 403 if not the owner, 404 if schedule not found

**Admin: Disable/Enable Exports**
- **Endpoint:** `PATCH /api/admin/workspace/exports`
- **Body:** `{ enabled: boolean }`
- **Returns:** `{ enabled: boolean, disabledAt?: timestamp, disabledBy?: string }`
- **Errors:** 403 if not an admin

### Internal Contracts

**Export Engine Interface**
- **Input:** `{ reportId, userId, format, requestId }`
- **Output:** Success → `{ exportId, size, artifactUri }` | Failure → `{ error, reason }`
- **Behavior:** Streams the report data with row-level filtering applied, generates format, monitors size, rejects if > 50 MB
- **Side effects:** Writes Export record and ExportAuditLog entry

**Job Queue Interface**
- **Enqueue:** `{ type: "export", reportId, userId, format, scheduleId?, requestId }`
- **Dequeue:** Returns the oldest pending job and marks it processing
- **Complete:** `{ jobId, success: boolean, exportId?, error? }`
- **Deadletter:** Moves job to deadletter queue after max retries

**Email Delivery Interface**
- **Input:** `{ to: string, scheduleId, exportName, artifactUri, deliveryStatus, lastDeliveryStatus }`
- **Output:** Success or Failure with error code
- **Behavior:** Sends a transactional email with the export artifact or a link to retrieve it

**Audit Log Interface**
- **Append:** `{ event, userId, reportId, scheduleId?, format?, size?, deliveryStatus, timestamp, metadata }`
- **Query:** `{ userId?, reportId?, scheduleId?, eventType?, timeRange?, limit, offset }`
- **Behavior:** All writes are append-only; all reads include filtering by user/report scope for non-admins
