# Technical Approach: Scheduled Report Exports

## Architecture Outline

The export system comprises four main components:

1. **Export Service** — handles one-off and scheduled export generation, format conversion, and delivery coordination
2. **Permission Filter** — intercepts report data and applies row-level access controls before export
3. **Delivery System** — manages email scheduling, retry logic, and transport
4. **Audit Logger** — records all export events for compliance and observability

These components integrate with the existing reporting module via a lightweight export gateway that intercepts report queries and applies the permission filter. Scheduled exports are driven by a background job scheduler (cron or similar) that wakes up at configured intervals, evaluates which schedules should run, and enqueues export tasks.

Export generation happens asynchronously: the user's UI request returns immediately after enqueuing; the export runs in the background and notifications (email delivery, audit log entry) complete independently. PDF generation and email sending are non-blocking I/O operations handled by the delivery system.

The feature flag gates all user-facing export UI and the export service endpoints; when disabled, export buttons disappear and any direct export API calls return 403 Forbidden.

## Domain Model

### Core Entities

**Report**
- Unique identifier
- Owner/creator
- Configuration (columns, filters, sorting, pagination)
- Schema for row-level permission evaluation

**Export**
- ID (unique identifier)
- Report reference
- Requested format (CSV or PDF)
- Requester/owner (the user who initiated or scheduled the export)
- Generation timestamp
- Status (pending, complete, failed, oversized)
- Metadata (row count, size in bytes, error message if failed)
- Generated artifact reference (S3 key, blob storage path, or local file handle)

**Schedule**
- ID (unique identifier)
- Report reference
- Schedule owner (user who created the schedule)
- Recurrence pattern (daily or weekly, with time of day and day-of-week for weekly)
- Export format (CSV or PDF)
- Email delivery address (always the schedule owner's email at schedule creation)
- Status (active, paused)
- Last run timestamp
- Created/updated timestamps

**ScheduleRun**
- ID (unique identifier)
- Schedule reference
- Generated Export reference
- Delivery status (pending, succeeded, failed)
- Attempt count (1-3 for retries)
- Next retry timestamp (if still retrying)
- Timestamps (created, completed)

**AuditLogEntry**
- Event type (export_requested, export_completed, export_failed, schedule_created, schedule_paused, schedule_resumed, schedule_run_delivered, schedule_run_delivery_failed)
- Actor (user ID, admin if triggered by workspace config)
- Target (export ID or schedule ID)
- Metadata (report name, format, row count, reason for failure, error code)
- Timestamp

### Relationships

```
Report has many Schedules
Schedule has many ScheduleRuns
ScheduleRun references one Export
Export references one Report and one user (requester)
AuditLogEntry references either Export or Schedule
```

## Key Workflows

### One-Off Export (User-Initiated)

1. User clicks "Export" on a report, selects format (CSV or PDF), and submits
2. UI sends export request to Export Service endpoint
3. Export Service:
   - Validates feature flag is enabled; returns 403 if disabled
   - Validates user has permission to view the report
   - Enqueues an export task (async job)
   - Returns Export ID and status (pending) immediately
4. Background worker retrieves the report query and executes it
5. Permission Filter evaluates row-level permissions for each row and removes ineligible rows
6. Formatter (CSV or PDF) converts the filtered result set
7. System checks output size against 50 MB limit; if exceeded, marks Export as oversized and logs error
8. If size OK, artifact is stored (S3, blob storage, or temp file) and Export status becomes complete
9. Audit log entry is written (export_completed or export_failed)
10. If enabled, UI polls Export Service for status or receives a webhook notification

### Scheduled Export (Creation)

1. User navigates to a report and clicks "Schedule Export"
2. UI presents a form to configure recurrence (daily or weekly), time, and format
3. User submits; UI sends request to Schedule Service endpoint
4. Schedule Service:
   - Validates feature flag is enabled; returns 403 if disabled
   - Validates user has permission to view the report
   - Validates recurrence pattern (e.g., day of week is valid for weekly)
   - Creates Schedule record with owner = current user, email = user's email, status = active
   - Sets next_run timestamp based on pattern and current time
5. Audit log entry is written (schedule_created)
6. UI returns success and displays the schedule ID

### Scheduled Export (Execution & Delivery)

1. Background scheduler wakes up (e.g., every 5 or 10 minutes)
2. Queries for all active Schedules where next_run <= now
3. For each qualifying schedule:
   - Creates a ScheduleRun record with status = pending, attempt_count = 1
   - Enqueues an export task (identical to one-off export)
4. Export task runs:
   - Retrieves the report query and executes it
   - Permission Filter evaluates row-level permissions for each row and removes ineligible rows
   - Formatter (CSV or PDF) converts the filtered result set
   - System checks output size against 50 MB limit; if exceeded, marks Export as oversized and logs error
   - If size OK, artifact is stored (S3, blob storage, or temp file) and Export status becomes complete
5. Upon export completion:
   - ScheduleRun is updated with the Export reference and status
   - Delivery Service sends email with the artifact attached
   - If email succeeds: ScheduleRun.delivery_status = succeeded, schedule's next_run is updated
   - If email fails: ScheduleRun.delivery_status = failed, attempt_count is incremented
6. Retry logic:
   - If attempt_count < 3, schedules a retry for attempt_count minutes later (or exponential backoff)
   - If attempt_count == 3 (final retry fails), pauses the Schedule, logs error, and writes audit entry
7. Audit log entries are written for delivery_succeeded and delivery_failed events
8. Cleanup: old ScheduleRuns (> 30 days) are archived or deleted per retention policy

### Schedule Management (Pause/Resume)

1. User views their scheduled exports and clicks pause/resume
2. UI sends request to Schedule Service endpoint
3. Schedule Service updates Schedule.status and next_run (set to null if paused)
4. Audit log entry is written (schedule_paused or schedule_resumed)

### Admin Controls

1. Admin accesses workspace settings and toggles "Enable Report Exports" feature flag
2. Settings Service updates feature flag configuration
3. If disabled:
   - Export UI is hidden for all users
   - Export API endpoints return 403 Forbidden with clear message
   - Scheduled export jobs stop running (scheduler skips execution)
   - Existing schedules remain in database but are dormant
4. If enabled:
   - Export UI is visible
   - Scheduled export jobs resume (respecting their active/paused status)
   - Audit log entry is written (feature_flag_toggled)

## Contracts

### Export Service API

**POST /api/exports** — Initiate one-off export
- **Request**: `{ reportId, format: "csv" | "pdf" }`
- **Response**: `{ exportId, status: "pending", createdAt }`
- **Errors**: 403 if feature flag disabled, 404 if report not found, 403 if user lacks read permission, 400 if format invalid
- **Side effects**: Creates Export record, enqueues async task, writes audit log

**GET /api/exports/:exportId** — Poll export status
- **Response**: `{ exportId, reportId, status: "pending" | "complete" | "failed" | "oversized", rowCount?, sizeBytes?, errorMessage?, downloadUrl? }`
- **Errors**: 404 if export not found, 403 if user is not the requester
- **Side effects**: None (read-only)

**GET /api/exports/:exportId/download** — Download completed export
- **Response**: Binary file (CSV or PDF)
- **Errors**: 404 if export not found, 410 if artifact expired, 400 if export still pending or failed
- **Headers**: Content-Type (text/csv or application/pdf), Content-Disposition (attachment)
- **Side effects**: None (artifact may have an access log)

### Schedule Service API

**POST /api/schedules** — Create scheduled export
- **Request**: `{ reportId, format: "csv" | "pdf", recurrence: { frequency: "daily" | "weekly", dayOfWeek?: 0-6, hourOfDay: 0-23 } }`
- **Response**: `{ scheduleId, reportId, nextRun, status: "active", createdAt }`
- **Errors**: 403 if feature flag disabled, 404 if report not found, 403 if user lacks read permission, 400 if recurrence invalid
- **Side effects**: Creates Schedule record, calculates next_run, writes audit log

**GET /api/schedules** — List user's schedules
- **Query params**: (none; implicitly scoped to current user)
- **Response**: `[ { scheduleId, reportId, format, recurrence, status, nextRun, createdAt, lastRun }, ... ]`
- **Errors**: None
- **Side effects**: None

**GET /api/schedules/:scheduleId/runs** — Fetch last 30 runs for a schedule
- **Response**: `[ { runId, scheduleId, exportId, deliveryStatus, attemptCount, createdAt, completedAt }, ... ]` (ordered descending by createdAt, limit 30)
- **Errors**: 404 if schedule not found, 403 if user is not the schedule owner
- **Side effects**: None

**PATCH /api/schedules/:scheduleId** — Update schedule status (pause/resume)
- **Request**: `{ status: "active" | "paused" }`
- **Response**: `{ scheduleId, status, nextRun?, updatedAt }`
- **Errors**: 404 if schedule not found, 403 if user is not the schedule owner, 400 if invalid status
- **Side effects**: Updates Schedule record, updates next_run (null if paused), writes audit log

**DELETE /api/schedules/:scheduleId** — Delete a schedule
- **Response**: `{ success: true }`
- **Errors**: 404 if schedule not found, 403 if user is not the schedule owner
- **Side effects**: Deletes Schedule (soft-delete preferred for audit trail), writes audit log

### Permission Filter Contract

**ApplyRowLevelPermissions(reportId, resultSet, userId) -> FilteredResultSet**
- Takes a report query result set and a user ID
- Evaluates row-level access control rules (defined per report; logic depends on report schema and user context)
- Returns a filtered result set containing only rows the user can access
- If no rows are accessible, returns empty result set (not an error)
- **Performance**: Must be efficient for large result sets (streaming or batch filtering)

### Audit Logger Contract

**LogExportEvent(eventType, actor, targetExportId, metadata) -> void**
- **Event types**: export_requested, export_completed, export_failed, export_oversized, export_downloaded
- **Metadata example**: `{ reportName, format, rowCount, sizeBytes, errorMessage }`
- **Errors**: Audit log writes should not block or fail the primary operation (fire-and-forget or async queue)

**LogScheduleEvent(eventType, actor, targetScheduleId, metadata) -> void**
- **Event types**: schedule_created, schedule_paused, schedule_resumed, schedule_deleted, schedule_run_delivered, schedule_run_delivery_failed, schedule_run_max_retries_exceeded
- **Metadata example**: `{ reportName, recurrence, attemptCount, errorMessage }`

### Email Delivery Contract

**SendScheduledExportEmail(scheduleOwnerEmail, reportName, format, artifact) -> DeliveryStatus**
- Constructs email with report name, export date, and artifact attachment
- Sends via configured SMTP or cloud mail service
- Returns success or failure
- **Retry responsibility**: Delivery Service owns retry logic; this contract returns immediate result only
- **Side effects**: Writes audit log entry (schedule_run_delivered or schedule_run_delivery_failed)

### Feature Flag Contract

**IsExportFeatureEnabled(workspaceId) -> boolean**
- Returns true if export functionality is enabled for the workspace
- Checked at entry to all export endpoints and by the scheduled export scheduler
- **Performance**: Should be cached (TTL ~5 minutes) to avoid repeated database lookups
