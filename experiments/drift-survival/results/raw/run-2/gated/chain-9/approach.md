# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature comprises four main architectural layers:

1. **Export Engine** — handles one-off and scheduled export generation, format conversion (CSV/PDF), size validation, and permission enforcement
2. **Scheduling Service** — manages recurring export schedules, triggers execution at configured intervals, and maintains schedule state (active/paused)
3. **Delivery Service** — delivers generated exports via email with retry logic and failure handling
4. **Audit and Admin Control** — records all export events, enforces workspace-level feature flag controls, and provides admin visibility

The export engine generates exports asynchronously (non-blocking) and stores results in a temporary queue. The scheduling service polls or subscribes to time-based triggers and enqueues export jobs. The delivery service consumes the queue, attempts email delivery, implements retry with backoff, and updates schedule state on persistent failures. All operations flow through the audit system which records user identity, export scope, format, and delivery outcome.

A workspace-level feature flag gates the entire export functionality, allowing admins to disable exports globally for compliance. Permission checks happen at export generation time—the export engine respects the requesting user's row-level access controls, filtering the dataset before serialization.

## Domain Model

**Export** — represents a single export instance (one-off or scheduled run)
- Fields: `id`, `report_id`, `user_id`, `format` (csv|pdf), `status` (pending|generating|ready|delivered|failed), `file_url`, `size_bytes`, `created_at`, `completed_at`
- Lifecycle: created → generating → ready (or failed) → delivered (or failed)

**ScheduledExport** — represents a recurring export configuration
- Fields: `id`, `report_id`, `owner_user_id`, `recurrence` (daily|weekly), `format`, `paused` (boolean), `created_at`, `paused_at`, `last_run_at`
- Relationships: owns many `Export` instances (the execution history)

**ExportRun** — a single execution of a scheduled export
- Fields: `scheduled_export_id`, `export_id`, `scheduled_for`, `executed_at`, `status` (success|failed), `retry_count`, `error_message`
- Tracks the history of each schedule's runs, enabling the 30-day history view

**AuditLog** — records export activity
- Fields: `id`, `event_type` (export_requested|export_completed|export_failed|schedule_created|schedule_paused|schedule_resumed), `user_id`, `workspace_id`, `report_id`, `scheduled_export_id`, `details` (JSON), `timestamp`

**ExportConfig** (workspace-scoped) — feature flag state
- Fields: `workspace_id`, `exports_enabled` (boolean), `last_modified_by`, `modified_at`

## Key Workflows

### One-Off Export Workflow
1. User requests export of a report in a specific format (CSV or PDF)
2. System validates: export feature enabled → user has report access → report + user permissions are resolved
3. Export record created with status `pending`
4. Export generation job enqueued asynchronously
5. System calculates dataset size; if > 50 MB, mark export failed with user-facing error message
6. Data is fetched and filtered by user's row-level permissions
7. Export generation runs: serializes to format, writes to temporary storage
8. Export marked `ready` with file URL
9. Audit event recorded: `export_completed` or `export_failed`
10. User is notified export is ready (UI indicator, download link, or email)

### Scheduled Export Creation Workflow
1. User configures a new scheduled export: select report, choose format, pick recurrence (daily/weekly), confirm owner (self)
2. System validates permissions and feature flag
3. ScheduledExport record created with `paused = false`, `last_run_at = null`
4. Audit event recorded: `schedule_created`
5. Scheduler will trigger first run on next recurrence boundary

### Scheduled Export Execution Workflow
1. Scheduler detects that a ScheduledExport with `paused = false` is due for execution
2. Same validation and generation logic as one-off export applies
3. New Export record created, linked to ScheduledExport
4. ExportRun record created with `scheduled_for` timestamp
5. Export generation proceeds (async, non-blocking)
6. On success: Export marked `ready`, ExportRun marked `success`, proceed to delivery
7. On failure: Export marked `failed`, ExportRun marked `failed` with error message, enqueue for delivery retry

### Export Delivery Workflow
1. Once an export is `ready`, it is enqueued for delivery
2. Delivery service picks up export and determines recipient:
   - For one-off exports: recipient configured at request time (or logged-in user default)
   - For scheduled exports: owner's email address
3. Email prepared with export attachment and sent
4. On success: Export marked `delivered`, audit event recorded `export_completed`
5. On failure: increment `retry_count`, reschedule with backoff
6. After 3rd attempt failure: set ScheduledExport `paused = true`, audit event recorded, admin/owner notified
7. All delivery attempts logged in ExportRun for history tracking

### Schedule Pause/Resume Workflow
1. Owner views scheduled export detail, clicks "Pause" or "Resume"
2. System updates ScheduledExport: toggle `paused` boolean, update `paused_at` if applicable
3. No immediate side effects on pending exports; scheduler checks `paused` flag before triggering new runs
4. Audit events recorded: `schedule_paused` or `schedule_resumed`

### Export History View Workflow
1. User navigates to scheduled export detail page
2. System queries ExportRun table filtered by `scheduled_export_id`, ordered by execution date descending, limited to 30 most recent
3. For each run, display: scheduled date, executed date, status (success/failed), error message (if failed), download link (if ready)

### Admin Disable Exports Workflow
1. Admin opens workspace settings → export controls
2. Admin toggles "Enable Exports" off
3. System sets ExportConfig `exports_enabled = false`
4. All subsequent export requests rejected at validation layer
5. Existing scheduled exports remain paused until feature is re-enabled
6. Audit event recorded: `exports_disabled` or `exports_enabled`

## Contracts

### Export Generation Service
**Input:**
- `report_id`: identifier of the report to export
- `user_id`: requesting user (for permission filtering)
- `format`: "csv" or "pdf"

**Output:**
- `status`: "success" or "error"
- `file_url`: signed/temporary URL to downloadable file (on success)
- `size_bytes`: size of generated export (on success)
- `error_message`: user-facing error string (on failure, e.g., "Export exceeds 50 MB limit")

**Side Effects:**
- Writes export record with status transitions
- Records audit event
- Respects user's row-level permissions during data fetch

### Scheduler Service
**Trigger:** Time-based event (daily, weekly recurrence check)

**Input:**
- `scheduled_export_id`: the schedule to execute
- `execution_time`: when this run was triggered

**Output:**
- Enqueues an export generation job
- Creates ExportRun record

**Responsibilities:**
- Checks `paused` flag; skips if paused
- Respects recurrence rule (daily = every 24h, weekly = every 7 days from creation or last run)
- Handles concurrent execution (no duplicate runs for same schedule in the same interval)

### Delivery Service
**Input:**
- `export_id`: the export to deliver
- `recipient_email`: destination email address
- `retry_count`: current attempt number (1, 2, or 3)

**Output:**
- `status`: "sent", "failed", "paused_schedule" (on 3rd failure)
- `error_detail`: SMTP error or other delivery reason (if failed)

**Side Effects:**
- Updates Export status to `delivered` or `failed`
- Updates ExportRun with retry count and error message
- If 3rd retry fails: sets ScheduledExport `paused = true`, records audit event
- Records delivery attempt in audit log

### Permission Enforcement
**Service:** Export Engine at generation time

**Behavior:**
- Resolves the dataset query for the report
- Applies the requesting user's row-level access control rules
- Filters rows to only those the user can view in the UI
- No additional data is accessible in the export

**Contract:**
- Exported data is a subset of what the user would see if they manually reviewed the entire report in the application

### Admin Control API
**Endpoints:**
- `GET /workspace/exports/config` — returns `exports_enabled` status
- `PUT /workspace/exports/config` — updates `exports_enabled` flag (admin only)
- `GET /workspace/exports/audit` — returns paginated audit log filtered by export events

**Permissions:**
- Only workspace admins can modify `exports_enabled`
- Only workspace admins can view export audit log
- Users can view their own export and schedule history

### Feature Flag Contract
**Runtime check:**
- Before accepting any export request (one-off or schedule creation): `if not exports_enabled: reject with "Exports are disabled by workspace admin"`
- Scheduled exports continue to exist in the system but do not execute while paused (by admin or owner)
