# Scheduled Report Exports — Technical Approach

## Architecture Outline

The feature consists of five primary components:

1. **Export Service** — orchestrates on-demand and scheduled export generation, enforces permissions, handles format rendering (CSV/PDF), and applies size limits. Operates synchronously for on-demand exports and asynchronously for scheduled exports.

2. **Scheduler** — manages the lifecycle of scheduled exports, tracks recurrence (daily/weekly), maintains pause/resume state, and triggers scheduled export jobs. Uses a durable task queue or cron-like mechanism with exactly-once semantics.

3. **Delivery Pipeline** — handles email delivery of completed exports, implements retry logic with exponential backoff (up to 3 attempts), pauses schedules after third failure, and provides circuit-breaker semantics to prevent cascading failures.

4. **Audit Logger** — captures all export events (on-demand generation, schedule creation/modification/pause/resume, delivery success/failure, retries) with user identity, timestamp, and outcome for compliance and troubleshooting.

5. **Feature Flag Control** — gates export functionality with a workspace-level enable/disable flag that admins can toggle without redeployment. Controls visibility of export UI and rejects export requests when disabled.

Additionally, an **Execution History Store** retains the last 30 execution records per schedule, including generation status, file size, delivery attempt count, and delivery outcome.

## Domain Model

**Report** — represents a report definition with its filtering rules, column selection, and access control bindings. Reports already exist in the system; the export feature consumes them.

**ExportRequest** (on-demand) — a one-time request to render a report in a specific format (CSV or PDF) for immediate download or email delivery. Owned by the requesting user. Includes:
- `id`, `report_id`, `created_by`, `created_at`
- `format` (CSV | PDF)
- `status` (pending | success | failed)
- `file_size`, `generated_at`, `error_message` (if failed)

**ScheduledExport** — a recurring export definition owned by a user. Includes:
- `id`, `report_id`, `owner_id`, `created_at`
- `recurrence` (daily | weekly), `recurrence_config` (day of week for weekly, time of day)
- `status` (active | paused)
- `delivery_email`, `last_run_at`, `next_run_at`
- `pause_reason` (if paused due to circuit breaker)

**ExportExecution** — a single run of a scheduled export. Includes:
- `id`, `scheduled_export_id`, `scheduled_at`, `started_at`, `completed_at`
- `status` (pending | success | failed)
- `file_size`, `error_message`
- `delivery_attempts` (array of attempt records: timestamp, status, error)

**AuditLogEntry** — immutable record of export-related events:
- `id`, `timestamp`, `user_id`, `event_type` (export_generated, schedule_created, schedule_paused, delivery_attempted, etc.)
- `resource_type`, `resource_id` (references the export request or schedule)
- `details` (format, file size, delivery endpoint, retry count, etc.)

## Key Workflows

### On-Demand Export

1. User requests export of a report in a specific format (CSV or PDF).
2. System checks feature flag; if disabled, reject with user-facing error.
3. System validates that the user has read access to the underlying report.
4. System executes the report query with the user's row-level permission filters applied.
5. System renders the result set in the requested format.
6. System validates file size; if > 50 MB, reject with user-facing error and log audit event.
7. System streams the file to the user or initiates email delivery (immediate).
8. System logs successful export in audit log.
9. On error, system logs failure reason and displays user-facing message.

### Create Scheduled Export

1. User selects a report and configures recurrence (daily or weekly) and delivery email.
2. System validates the user has read access to the report.
3. System creates a ScheduledExport record in active state.
4. System schedules the first execution based on recurrence config.
5. System logs the schedule creation in audit log.
6. System returns schedule ID and next run time to the user.

### Execute Scheduled Export (Background Job)

1. Scheduler triggers an export execution for a ScheduledExport at scheduled time.
2. System fetches the schedule; if paused, skips execution.
3. System executes the report query with the schedule owner's row-level permission filters.
4. System renders the result in CSV format (scheduled exports default to CSV).
5. System validates file size; if > 50 MB, mark execution as failed with size-exceeded reason.
6. System creates an ExportExecution record with generated file.
7. System transitions to delivery workflow.
8. System calculates next run time and updates schedule's `next_run_at`.

### Delivery Workflow (with Retry/Circuit Breaker)

1. System enqueues a delivery job for the ExportExecution with max 3 attempts.
2. System sends email with the export file attachment to the schedule owner's delivery email.
3. On success: update ExportExecution with success status and timestamp, log audit event.
4. On failure: increment delivery attempt count, log attempt with error reason.
5. If attempt count < 3: enqueue retry with exponential backoff (e.g., 5min, 15min, 60min).
6. If attempt count == 3: mark execution as failed, pause the schedule, set pause_reason to "delivery_failures", log audit event for schedule pause.
7. On pause due to circuit breaker: clear the next_run_at to prevent further scheduling until resumed by user.

### View Execution History

1. User requests the execution history for a scheduled export.
2. System retrieves the 30 most recent ExportExecution records for that schedule (ordered by scheduled_at descending).
3. System returns execution records with status, file size, delivery attempt count, and delivery outcome.

### Pause / Resume Schedule

1. User requests pause of an active schedule: system updates status to "paused" and clears next_run_at. Log audit event.
2. User requests resume of a paused schedule: system updates status to "active", recalculates next_run_at based on recurrence config, and logs audit event.

### Disable Export Functionality

1. Workspace admin toggles the export feature flag to disabled.
2. Scheduler stops processing new scheduled exports (existing schedules remain in database but do not execute).
3. On-demand export endpoints reject requests with a user-facing message indicating exports are disabled by workspace admin.
4. All other export management UI (view history, pause/resume, create schedule) becomes read-only or hidden.

## Contracts

### Export Service

**GenerateExport** — initiates an on-demand export
- Input: `report_id` (string), `format` (enum: CSV | PDF), `user_id` (string), `workspace_id` (string)
- Output: `ExportRequest` object with id, status, and (on success) file reference or download URL
- Errors: `ReportNotFound`, `PermissionDenied`, `ExportDisabled`, `FileSizeLimitExceeded`, `InvalidFormatError`

**ValidateExportSize** — checks whether an export would exceed 50 MB without full generation
- Input: `report_id`, `user_id`, estimated row count
- Output: boolean (allowed) or error message
- Used as pre-flight check to fail fast

### Scheduler Service

**CreateScheduledExport** — defines a new recurring export
- Input: `report_id`, `owner_id`, `workspace_id`, `recurrence` (daily | weekly), `recurrence_config` (JSON), `delivery_email`
- Output: `ScheduledExport` object with id, next_run_at, status
- Errors: `ReportNotFound`, `PermissionDenied`, `ExportDisabled`, `InvalidRecurrence`

**PauseSchedule** — pauses a scheduled export
- Input: `schedule_id`, `user_id`
- Output: updated `ScheduledExport` with status = paused
- Errors: `ScheduleNotFound`, `PermissionDenied` (only owner or admin), `AlreadyPaused`

**ResumeSchedule** — resumes a paused scheduled export
- Input: `schedule_id`, `user_id`
- Output: updated `ScheduledExport` with status = active and recalculated next_run_at
- Errors: `ScheduleNotFound`, `PermissionDenied`, `NotPaused`, `ExportDisabled`

**GetExecutionHistory** — retrieves execution records for a schedule
- Input: `schedule_id`, `user_id`, `limit` (default 30, max 100)
- Output: array of `ExportExecution` objects, ordered by scheduled_at descending
- Errors: `ScheduleNotFound`, `PermissionDenied`

### Delivery Service

**EnqueueDelivery** — submits an export for email delivery
- Input: `execution_id`, `recipient_email`, `file_path`, `file_name`
- Output: confirmation with attempt tracking ID
- Errors: `InvalidEmail`, `FileNotFound`

**RetryDelivery** — explicit retry endpoint (may be called by scheduler or admin)
- Input: `execution_id`, `user_id`
- Output: updated `ExportExecution` with new attempt record
- Errors: `ExecutionNotFound`, `PermissionDenied`, `MaxAttemptsExceeded`

### Audit Logger

**LogExportEvent** — records an export-related event
- Input: `event_type` (export_generated | schedule_created | schedule_paused | schedule_resumed | delivery_attempted | delivery_failed | delivery_success | schedule_auto_paused), `user_id`, `workspace_id`, `resource_type`, `resource_id`, `details` (JSON map of contextual data)
- Output: audit log entry ID
- Errors: none (logging must not fail the main request)

### Feature Flag Control

**IsExportEnabled** — checks whether exports are allowed in a workspace
- Input: `workspace_id`
- Output: boolean
- Caching: may cache with TTL (e.g., 1 minute) to reduce flag lookups

**SetExportEnabled** — admin toggles export feature flag
- Input: `workspace_id`, `enabled` (boolean), `admin_user_id`
- Output: confirmation with effective timestamp
- Errors: `PermissionDenied` (admin-only), `WorkspaceNotFound`
