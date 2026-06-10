# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature comprises five primary components:

1. **Export Service** — orchestrates export generation, respects permissions, enforces size limits, and handles async processing
2. **Scheduling Engine** — manages recurring export definitions, triggers scheduled runs, and implements pause/resume logic
3. **Delivery Service** — sends generated exports via email with retry logic and failure tracking
4. **Audit Logger** — records all export events (one-off and scheduled) for compliance
5. **Feature Flag Controller** — gates the entire feature and provides admin controls

These components interact as follows:
- The Scheduling Engine triggers export runs at configured intervals (daily/weekly)
- The Export Service generates the report data in the requested format (CSV or PDF), respecting row-level permissions
- Generated exports are validated for size constraints before delivery
- The Delivery Service attempts to send the export via email, with automatic retries on failure
- All events flow through the Audit Logger for compliance tracking
- The Feature Flag Controller can disable the entire feature globally

## Domain Model

**Export** — represents a one-off or scheduled export request
- `id` (UUID)
- `report_id` (foreign key to report)
- `format` (enum: CSV, PDF)
- `created_by` (user_id)
- `created_at` (timestamp)
- `status` (enum: pending, generating, generated, failed)
- `file_size_bytes` (nullable, populated after generation)
- `error_message` (nullable, populated on failure)

**ScheduledExport** — represents a recurring export definition
- `id` (UUID)
- `export_id` (foreign key to export, the template)
- `owner_id` (user_id)
- `recurrence` (enum: daily, weekly)
- `scheduled_for` (timestamp, next run time)
- `is_paused` (boolean)
- `paused_at` (nullable timestamp)
- `paused_reason` (nullable string)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**ExportRun** — represents a single execution of a scheduled export
- `id` (UUID)
- `scheduled_export_id` (foreign key)
- `export_id` (foreign key)
- `run_at` (timestamp)
- `completed_at` (nullable timestamp)
- `status` (enum: pending, generating, generated, delivery_pending, delivered, failed)
- `delivery_attempts` (integer, 0-3)
- `last_delivery_error` (nullable string)

**ExportHistory** — queryable view over recent ExportRun records
- Retains the last 30 runs per ScheduledExport
- Accessible to the schedule owner and workspace admins

**AuditLogEntry** — compliance record for all export activity
- `event_type` (enum: export_requested, export_generated, export_failed, scheduled_export_created, scheduled_export_paused, scheduled_export_resumed, scheduled_export_delivery_succeeded, scheduled_export_delivery_failed)
- `user_id` (nullable, for admin-triggered events)
- `resource_id` (export_id or scheduled_export_id)
- `resource_type` (enum: export, scheduled_export)
- `details` (JSON, context-dependent)
- `timestamp` (timestamp)

## Key Workflows

### One-Off Export (CSV or PDF)

1. User selects a report and chooses an export format (CSV or PDF)
2. Export Service receives the request and validates the user has read access to the report
3. Export Service generates the report data, filtering rows based on row-level permissions
4. Export is serialized into the requested format
5. Service validates file size ≤ 50 MB; if exceeded, returns user-facing error and logs failure
6. Service returns the generated file to the user for immediate download
7. Audit Logger records the export event with outcome (success or size-exceeded failure)

### Scheduled Export Creation

1. User creates a scheduled export by selecting a report, format, and recurrence (daily/weekly)
2. System creates a ScheduledExport record with owner set to the current user
3. System calculates the next run time based on the recurrence pattern
4. Scheduling Engine registers the schedule for background processing
5. Audit Logger records the scheduled export creation event

### Scheduled Export Execution

1. Scheduling Engine detects that a scheduled export is due (based on next run time)
2. Service checks if the ScheduledExport is paused; if paused, skips the run
3. Service generates an ExportRun record and begins export generation
4. Export Service filters report data based on row-level permissions as of the execution time
5. Service validates file size ≤ 50 MB; if exceeded, marks ExportRun as failed and logs audit event
6. Delivery Service is triggered to send the export via email to the schedule owner
7. Delivery Service attempts to send the email; if successful, marks ExportRun as delivered and increments scheduled_export.scheduled_for to the next occurrence
8. If delivery fails, Delivery Service automatically retries up to 3 times total
9. After 3 failed delivery attempts, ScheduledExport is automatically paused with pause_reason = "automatic_pause_after_delivery_failures"
10. Audit Logger records all steps: generation, delivery attempts, success, and auto-pause

### Pause Scheduled Export

1. Schedule owner requests pause on a ScheduledExport
2. System sets is_paused = true, paused_at = now(), paused_reason = "manually_paused"
3. Scheduling Engine skips all future runs until resumed
4. Audit Logger records the pause event

### Resume Scheduled Export

1. Schedule owner requests resume on a paused ScheduledExport
2. System sets is_paused = false, clears paused_at and paused_reason
3. System recalculates next run time based on recurrence pattern and current time
4. Scheduling Engine re-registers the schedule
5. Audit Logger records the resume event

### View Export History

1. Schedule owner requests history for a ScheduledExport
2. System returns ExportHistory view filtered to the 30 most recent ExportRun records for that ScheduledExport
3. User sees execution timestamps, delivery status, file sizes, and error messages (if any)

### Admin Export Control

1. Workspace admin accesses workspace settings to toggle export functionality
2. Feature Flag Controller is set to disabled
3. All export functionality (one-off and scheduled) is hidden from users
4. Audit Logger records the admin action and timestamp

## Contracts

### Export API

**POST /reports/{report_id}/exports** — create a one-off export
- Request: `{ format: "CSV" | "PDF" }`
- Response: `{ export_id, download_url, status, created_at }`
- Errors: 403 (insufficient permissions), 400 (invalid format), 413 (resulting file would exceed 50 MB)
- Logs: audit event with outcome

**GET /exports/{export_id}** — poll export status
- Response: `{ export_id, status, file_size_bytes, error_message, created_at }`
- Errors: 404 (not found), 403 (insufficient permissions)

### Scheduled Export API

**POST /reports/{report_id}/scheduled-exports** — create a scheduled export
- Request: `{ format: "CSV" | "PDF", recurrence: "daily" | "weekly" }`
- Response: `{ scheduled_export_id, owner_id, recurrence, scheduled_for, is_paused, created_at }`
- Errors: 403 (insufficient permissions), 400 (invalid format/recurrence)
- Logs: audit event with creation details

**GET /scheduled-exports/{scheduled_export_id}** — fetch scheduled export details
- Response: `{ scheduled_export_id, export_id, report_id, owner_id, format, recurrence, scheduled_for, is_paused, paused_at, paused_reason, created_at, updated_at }`
- Errors: 404 (not found), 403 (insufficient permissions)

**PATCH /scheduled-exports/{scheduled_export_id}/pause** — pause a schedule
- Request: (empty body)
- Response: `{ scheduled_export_id, is_paused, paused_at }`
- Errors: 404 (not found), 403 (insufficient permissions), 409 (already paused)
- Logs: audit event

**PATCH /scheduled-exports/{scheduled_export_id}/resume** — resume a schedule
- Request: (empty body)
- Response: `{ scheduled_export_id, is_paused, scheduled_for }`
- Errors: 404 (not found), 403 (insufficient permissions), 409 (not paused)
- Logs: audit event

**GET /scheduled-exports/{scheduled_export_id}/history** — fetch execution history
- Query: `?limit=30` (defaults to 30)
- Response: `{ scheduled_export_id, runs: [ { run_id, run_at, completed_at, status, file_size_bytes, delivery_attempts, last_delivery_error } ] }`
- Errors: 404 (not found), 403 (insufficient permissions)

**DELETE /scheduled-exports/{scheduled_export_id}** — delete a scheduled export (optional)
- Response: `{ scheduled_export_id, deleted_at }`
- Errors: 404 (not found), 403 (insufficient permissions)
- Logs: audit event

### Audit API

**GET /audit-logs?resource_type=export&resource_id={id}** — fetch audit events for an export
- Query: `?event_type=export_generated`, `?limit=100`, `?offset=0`
- Response: `{ entries: [ { event_type, user_id, resource_id, resource_type, details, timestamp } ] }`
- Errors: 403 (insufficient permissions for audit access)

### Admin API

**PATCH /workspace/settings/exports-enabled** — toggle export feature globally
- Request: `{ enabled: boolean }`
- Response: `{ exports_enabled, updated_at }`
- Errors: 403 (insufficient admin permissions)
- Logs: audit event with admin user_id

### Feature Flag Contracts

The Feature Flag Controller exposes:
- **Workspace-level flag**: `exports.enabled` (boolean, defaults to true)
- **UI rendering contract**: when disabled, export buttons are hidden in report views
- **API enforcement contract**: when disabled, all export endpoints return 403 with message "Export functionality is disabled"

### Retry and Backoff Strategy

Delivery Service implements a simple retry strategy:
- **Attempt 1**: immediate
- **Attempt 2**: after 5 minutes
- **Attempt 3**: after 30 minutes
- After 3 failures: ScheduledExport is auto-paused
- Transient errors (connection timeouts, 5xx responses) trigger retries
- Permanent errors (invalid email address, 4xx responses) trigger immediate pause without retry exhaustion
