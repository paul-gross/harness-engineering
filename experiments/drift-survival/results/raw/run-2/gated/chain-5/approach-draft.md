# Technical Approach: Scheduled Report Exports

## Architecture Outline

The export system is composed of several architectural tiers:

1. **Export Service** — a request-driven service that generates export artifacts (CSV/PDF) from report definitions, respecting row-level permissions during data materialization. It is non-blocking: export generation is enqueued and processed asynchronously.

2. **Schedule Manager** — owns the lifecycle of recurring export schedules (creation, pause/resume, deletion, history tracking). Schedules are immutable once created except for pause/resume state and are owned by individual users.

3. **Export Queue & Worker** — an async job queue that dequeues export tasks (both one-off and scheduled), invokes the Export Service, and handles delivery (email or immediate download for one-offs).

4. **Delivery Engine** — handles transport and retry logic for scheduled exports; emails are the primary delivery channel. It implements exponential backoff up to 3 total attempts per schedule run, then auto-pauses the schedule if all retries fail.

5. **Feature Flag Service** — controls whether the entire export feature is available; when disabled, the UI hides export controls and API rejects all export requests.

6. **Audit Logger** — records all export events (one-off generation, scheduled creation/modification, delivery attempts, failures, manual pauses) with user identity and timestamp for compliance.

7. **Storage Layer** — holds generated export artifacts temporarily (for download delivery) and maintains schedule definitions, run history, and retry state. Run history is limited to the last 30 runs per schedule.

The architecture is non-blocking at the interactive tier: one-off exports and scheduled generations are enqueued immediately and processed by background workers, so report viewing is never blocked by export generation or delivery.

## Domain Model

### Core Entities

**Report** (existing entity, not modified)
- Owns report definition (columns, filters, sorting)
- Linked to row-level permission rules

**Export Schedule**
- `id`: unique schedule identifier
- `owner_user_id`: the user who owns and can manage the schedule
- `report_id`: the report being exported
- `export_format`: enum (CSV, PDF)
- `frequency`: enum (DAILY, WEEKLY)
- `next_run_at`: timestamp of next scheduled execution
- `is_paused`: boolean (schedule owner can pause/resume)
- `created_at`: timestamp
- `updated_at`: timestamp
- `deleted_at`: soft-delete marker (optional, for archive/restore workflows)

**Export Run** (instance of a scheduled export)
- `id`: unique run identifier
- `schedule_id`: foreign key to Export Schedule
- `status`: enum (QUEUED, GENERATING, GENERATED, DELIVERING, DELIVERED, FAILED)
- `artifact_size_bytes`: size of generated artifact
- `generation_started_at`: timestamp
- `generation_completed_at`: timestamp
- `delivery_attempts`: count of delivery attempts (0-3)
- `last_delivery_error`: error message from most recent failed delivery
- `delivered_at`: timestamp of successful delivery (null if not delivered)
- `created_at`: timestamp

**One-Off Export Request**
- `id`: unique request identifier
- `requesting_user_id`: the user requesting the export
- `report_id`: the report being exported
- `export_format`: enum (CSV, PDF)
- `status`: enum (QUEUED, GENERATING, READY, FAILED)
- `artifact_size_bytes`: size of generated artifact (set after generation)
- `artifact_url`: signed URL for download (valid for temporary duration)
- `generation_started_at`: timestamp
- `generation_completed_at`: timestamp
- `download_expires_at`: timestamp after which artifact is deleted
- `error_message`: populated if generation fails
- `created_at`: timestamp

### Relationships & Constraints

- Each Export Schedule is owned by exactly one user; that user is the sole recipient of scheduled exports.
- Each Export Run belongs to exactly one Export Schedule; runs are immutable once created.
- Row-level permissions are evaluated at export generation time: only rows visible to the requesting/owning user are included in the artifact.
- Artifacts larger than 50 MB are rejected during generation; the Export Run or One-Off Export Request is marked FAILED with a clear error message.
- Export Schedules are soft-deleted but remain queryable for history and administrative auditing.

## Key Workflows

### Workflow 1: One-Off Export (Immediate Download)

1. User views a report and clicks "Export as CSV" or "Export as PDF".
2. The system creates a One-Off Export Request in QUEUED status and returns an immediate response with a request ID and placeholder artifact URL.
3. The export service is enqueued with the request ID.
4. Background worker:
   - Marks the request GENERATING.
   - Fetches the report definition and applies row-level permission filters for the requesting user.
   - Materializes the filtered dataset and generates the artifact (CSV or PDF).
   - Validates artifact size; if > 50 MB, marks request FAILED and stores an error message.
   - If valid, stores the artifact and generates a signed download URL, marks the request READY.
5. User can poll or wait for the artifact URL; once available, they download directly.
6. The artifact is retained temporarily (e.g., 24 hours) then purged; the request record remains for audit.

### Workflow 2: Create a Scheduled Export

1. User navigates to report and clicks "Schedule Export".
2. User selects:
   - Export format (CSV or PDF)
   - Frequency (DAILY or WEEKLY)
   - Optionally, the day of week (if WEEKLY)
   - Confirms the schedule is owned by them (pre-selected)
3. The system creates an Export Schedule in active (non-paused) state and records the event in the audit log.
4. The schedule is immediately registered in the scheduler for the next run slot (e.g., daily at a fixed time, weekly on the selected day).
5. Confirmation is shown to the user; schedule ID is provided for future reference.

### Workflow 3: Scheduled Export Generation & Delivery

1. Scheduler triggers a scheduled export at its `next_run_at` time.
2. An Export Run is created in QUEUED status.
3. Export service is enqueued with the Export Run ID.
4. Background worker:
   - Marks the run GENERATING.
   - Fetches the report definition and applies row-level permission filters for the schedule owner.
   - Materializes the filtered dataset and generates the artifact.
   - Validates artifact size; if > 50 MB, marks run FAILED and exits (no delivery attempt).
   - If valid, marks the run GENERATED.
5. Delivery engine picks up the run:
   - Attempts to email the artifact (or a download link) to the schedule owner's email.
   - Marks run status to DELIVERING, then DELIVERED on success.
   - On failure, increments `delivery_attempts`.
6. Retry logic (on delivery failure):
   - If `delivery_attempts` < 3, schedules a retry (exponential backoff: 1 hour, 4 hours, 24 hours for attempts 1, 2, 3).
   - If `delivery_attempts` == 3 (all retries exhausted), marks run FAILED and automatically pauses the schedule (sets `is_paused` = true). Audit log records the auto-pause with reason.
7. Scheduler calculates next run time (e.g., 24 hours for daily, 7 days for weekly) and updates `next_run_at`.

### Workflow 4: View Export History

1. User navigates to their scheduled export settings page.
2. System displays a list of Export Schedules owned by the user, with controls to pause/resume.
3. User clicks on a schedule to view its run history.
4. System displays the last 30 Export Runs (paginated or scrollable), showing:
   - Run timestamp
   - Status
   - Artifact size
   - Delivery status and any error messages
5. User can download a generated artifact directly from the history (if the artifact is still retained) or view error details.

### Workflow 5: Pause & Resume a Schedule

1. Schedule owner navigates to their scheduled export settings.
2. User clicks "Pause" on an active schedule.
3. System sets `is_paused` = true for the schedule and records the pause event in the audit log.
4. Scheduler skips future runs for the paused schedule.
5. To resume, user clicks "Resume" on a paused schedule.
6. System sets `is_paused` = false and recalculates `next_run_at` (e.g., next day for daily, next week for weekly). Audit log records the resume event.

### Workflow 6: Administrative Disable

1. Workspace admin navigates to export settings in the admin panel.
2. Admin toggles export functionality ON or OFF via a feature flag or configuration setting.
3. When disabled:
   - No new schedules can be created.
   - UI hides all export buttons and schedule management pages.
   - API endpoints for export return HTTP 403 Forbidden with a message explaining the feature is disabled workspace-wide.
   - Existing schedules continue to exist but are not processed until the feature is re-enabled.
4. All export-disable events are recorded in the audit log.

## Contracts

### Export Service

**generateExport(reportId, userId, exportFormat, filters?) -> ExportArtifact**
- Generates an export artifact for the given report, applying row-level permissions based on the user's access.
- `reportId`: the report definition to export
- `userId`: the user requesting/owning the export (used to filter rows by permission)
- `exportFormat`: "CSV" or "PDF"
- `filters`: optional additional runtime filters (not yet in acceptance criteria; reserved for future)
- Returns: ExportArtifact object containing artifact binary data, size in bytes, and generated timestamp
- Throws: ExportSizeExceeded if artifact > 50 MB; ReportNotFound if report doesn't exist; AccessDenied if user has no access to the report
- Side effects: none (stateless function)

### One-Off Export API

**POST /api/reports/{reportId}/export**
- Creates a one-off export request for immediate download
- Request body: { format: "CSV" | "PDF" }
- Returns: { requestId, status: "QUEUED", artifactUrl: null } (immediate response)
- Side effects: creates One-Off Export Request record, enqueues background job
- HTTP 400 if format is invalid; 403 if export feature is disabled; 404 if report not found; 403 if user lacks read access to report

**GET /api/export-requests/{requestId}**
- Polls the status of a one-off export request
- Returns: { requestId, status, artifactUrl, artifactSize, errorMessage, createdAt, completedAt }
- HTTP 404 if request not found; 403 if user is not the requester

### Schedule Management API

**POST /api/schedules**
- Creates a new export schedule
- Request body: { reportId, format: "CSV" | "PDF", frequency: "DAILY" | "WEEKLY", weekDay?: 0-6 }
- Returns: { scheduleId, ownerId, reportId, format, frequency, weekDay, isPaused, createdAt, nextRunAt }
- Side effects: creates Export Schedule record, registers with scheduler, records audit event
- HTTP 400 if frequency/format invalid or weekDay out of range (when WEEKLY); 403 if disabled workspace-wide; 404 if report not found

**GET /api/schedules**
- Lists all schedules owned by the requesting user
- Returns: [{ scheduleId, reportId, format, frequency, isPaused, nextRunAt, createdAt }, ...]
- No pagination constraint in acceptance criteria (implement pagination if UI prefers)

**PATCH /api/schedules/{scheduleId}/pause**
- Pauses a schedule
- Returns: { scheduleId, isPaused: true, nextRunAt: null }
- Side effects: updates Export Schedule, cancels pending runs, records audit event
- HTTP 403 if user is not the schedule owner; 404 if schedule not found

**PATCH /api/schedules/{scheduleId}/resume**
- Resumes a paused schedule
- Returns: { scheduleId, isPaused: false, nextRunAt }
- Side effects: updates Export Schedule, re-registers with scheduler, records audit event
- HTTP 403 if user is not the schedule owner; 404 if schedule not found

**DELETE /api/schedules/{scheduleId}**
- Soft-deletes a schedule (or hard-deletes if configurable)
- Returns: { scheduleId, deletedAt }
- Side effects: soft-deletes Export Schedule, records audit event, cancels pending runs
- HTTP 403 if user is not the schedule owner; 404 if schedule not found

**GET /api/schedules/{scheduleId}/history**
- Retrieves the last 30 runs for a schedule
- Returns: [{ runId, status, artifactSize, generatedAt, deliveredAt, attemptCount, errorMessage }, ...]
- Optional pagination query params (limit, offset) per implementation preference
- HTTP 403 if user is not the schedule owner; 404 if schedule not found

**GET /api/schedules/{scheduleId}/history/{runId}/artifact**
- Downloads a previously generated artifact from run history (if still retained)
- Returns: binary artifact data with appropriate Content-Type header
- HTTP 403 if user is not the schedule owner; 404 if run not found; 410 Gone if artifact has been purged

### Feature Flag / Configuration API

**GET /api/export-config**
- Workspace-level read: returns whether export feature is enabled
- Returns: { isEnabled: boolean }
- No auth required (or public read allowed)

**PATCH /api/export-config** (admin-only)
- Enables or disables export feature workspace-wide
- Request body: { isEnabled: boolean }
- Returns: { isEnabled: boolean, updatedAt, updatedByUserId }
- Side effects: updates configuration, records audit event
- HTTP 403 if user is not a workspace admin

### Audit Log API

**GET /api/audit-log?resource=exports&limit=100&offset=0** (admin-only or filtered by user)
- Queries audit events related to exports
- Returns: [{ eventId, timestamp, userId, action, resourceId, details }, ...]
- `action` enums: EXPORT_ONE_OFF_CREATED, EXPORT_SCHEDULE_CREATED, EXPORT_SCHEDULE_PAUSED, EXPORT_SCHEDULE_RESUMED, EXPORT_RUN_DELIVERED, EXPORT_RUN_FAILED, EXPORT_FEATURE_DISABLED, etc.
- Filtering: users see only events they own; admins see all
- HTTP 403 if insufficient permissions

### Scheduler Integration

**registerSchedule(scheduleId, nextRunAt, frequency)**
- Internal contract: called when a schedule is created or resumed
- Registers the schedule with the background scheduler (e.g., a cron service, task queue with time-based dispatch, or in-process scheduler)
- Side effect: ensures the schedule's `next_run_at` is registered for background processing

**cancelSchedule(scheduleId)**
- Internal contract: called when a schedule is paused or deleted
- Removes the schedule from the background scheduler so no future runs are generated
- Side effect: clears any pending work for the schedule

### Email Delivery

**sendExportEmail(recipientEmail, recipientName, reportName, artifactUrl, artifactSize)**
- Sends an email with a download link and metadata about the export
- Recipient is always the schedule owner; email address comes from the user profile
- Email includes report name, export format, size, and a link valid for a limited time (e.g., 30 days)
- On failure, raises DeliveryException with a descriptive message
- Side effect: updates the Export Run delivery status

### Job Queue

**enqueueExportJob(exportRequestId | exportRunId, type: "one_off" | "scheduled")**
- Pushes an export job onto the async queue
- Worker processes jobs in order, invoking the Export Service and Delivery Engine
- On completion or error, updates the corresponding request/run record with status and any error details
