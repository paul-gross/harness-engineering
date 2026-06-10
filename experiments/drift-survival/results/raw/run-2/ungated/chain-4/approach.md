# Scheduled Report Exports – Technical Approach

## Architecture Outline

The scheduled report exports feature builds on the existing reporting module with three new layers:

1. **Export Service** — handles synchronous and asynchronous export generation (CSV and PDF), enforces size limits, and integrates with the audit log
2. **Schedule Manager** — manages the lifecycle of scheduled exports (create, pause, resume, delete), owns persistence, and tracks run history
3. **Delivery & Retry Engine** — coordinates email delivery, implements exponential retry logic (up to 3 attempts), marks schedules as paused on final failure, and maintains delivery event records
4. **Feature Flag & Admin Controls** — gates export functionality at launch and allows administrators to disable exports workspace-wide

The system treats exports (one-off and scheduled) as first-class events in the audit trail. The run history is derived from delivery event records rather than schedule state, giving users and administrators visibility into execution details without querying schedule objects directly.

## Domain Model

### Export
- **id** — unique identifier
- **report_id** — the report being exported
- **format** — CSV or PDF
- **requested_by** — user who initiated the export
- **created_at** — export creation timestamp
- **status** — pending, completed, failed
- **file_size_bytes** — size of the generated file (if successful)
- **error_message** — reason for failure (if applicable)

Exports are ephemeral; they may be stored temporarily or discarded after delivery. The audit log is the permanent record.

### ScheduledExport
- **id** — unique identifier
- **report_id** — the report being exported on schedule
- **owner_id** — user who created the schedule
- **format** — CSV or PDF
- **frequency** — daily or weekly
- **schedule_time** — hour and minute when exports should run (0–23, 0–59)
- **weekday** — if weekly, day of week (optional)
- **status** — active or paused
- **pause_reason** — reason schedule was paused (if applicable)
- **created_at** — schedule creation timestamp
- **updated_at** — last modification timestamp

### ExportRun
- **id** — unique identifier
- **scheduled_export_id** — reference to the schedule (or null for one-off exports)
- **export_id** — reference to the export that was generated
- **scheduled_at** — when the run was supposed to start
- **started_at** — when generation actually started
- **completed_at** — when delivery was attempted or completed
- **status** — success, failed, retrying
- **attempt_number** — 1, 2, or 3
- **error_message** — delivery failure reason (if applicable)

This entity tracks every execution attempt, enabling the 30-day history UI and allowing the system to distinguish between delivery failures and generation failures.

### Audit Log Entry (extended)
Export and scheduled-export operations are recorded as audit events:
- **action** — export_created, export_failed, schedule_created, schedule_paused, schedule_resumed, schedule_deleted, export_delivered, export_delivery_failed
- **user_id**
- **resource_type** — export or scheduled_export
- **resource_id**
- **context** — report_id, format, frequency, reason for pause, etc.

## Key Workflows

### One-Off Export

1. User requests an export (CSV or PDF) of a report
2. System checks feature flag and admin workspace setting; if disabled, return error
3. System applies the user's row-level permissions to the report query
4. System generates export asynchronously
5. System validates file size; if > 50 MB, reject with actionable error and log audit event (export_failed)
6. On success, system logs audit event (export_created) and makes file available for download
7. On failure (generation or size limit), system logs audit event (export_failed) with error details

### Create Scheduled Export

1. User provides report, format (CSV/PDF), and frequency (daily/weekly) plus optional time and weekday
2. System validates inputs and checks permissions
3. System creates ScheduledExport record in active status
4. System logs audit event (schedule_created)
5. System enqueues the next scheduled run based on frequency and time parameters

### Execute Scheduled Export

(Triggered by scheduler at the configured time)

1. Scheduler checks if schedule is active; if paused, skip
2. Scheduler generates export (as per one-off workflow) with the schedule owner's permissions
3. On generation success:
   - Scheduler creates ExportRun record with status = retrying
   - Scheduler enqueues email delivery task
   - On delivery success, scheduler updates ExportRun status = success and enqueues next run
   - On delivery failure, scheduler increments attempt_number and enqueues retry
4. On generation failure:
   - Scheduler creates ExportRun record with status = failed and error details
   - Scheduler does not retry generation; pauses schedule and logs audit event (schedule_paused)
   - Scheduler notifies owner of failure

### Retry Delivery

(Triggered for failed delivery attempts)

1. Scheduler checks ExportRun attempt_number
2. If attempt_number < 3:
   - Scheduler increments attempt_number
   - Scheduler waits exponentially (2^attempt * base_delay, e.g., 30 seconds × 2, 4, 8 for attempts 2, 3, 4)
   - Scheduler attempts delivery again and updates ExportRun accordingly
3. If attempt_number = 3 and delivery fails:
   - Scheduler marks ExportRun status = failed
   - Scheduler sets ScheduledExport status = paused with pause_reason = "delivery_failed_after_retries"
   - Scheduler logs audit events (export_delivery_failed, schedule_paused)
   - Scheduler sends notification to owner

### Pause / Resume Schedule

1. User requests pause or resume of a schedule
2. System updates ScheduledExport status (paused/active)
3. System logs audit event (schedule_paused or schedule_resumed)
4. If resuming, system enqueues next scheduled run

### View Run History

1. User requests history for a scheduled export
2. System queries ExportRun records for that schedule, ordered by scheduled_at desc
3. System returns last 30 runs with status, attempt_number, timestamps, and error messages
4. System filters runs older than 30 days automatically (or includes them with stale markers)

### Admin Disable Exports

1. Administrator enables/disables export functionality at workspace level
2. System persists setting in workspace configuration
3. When disabled, all export requests (one-off and scheduled generation) are rejected with "exports disabled" error
4. Scheduled exports remain in the database but no new runs are enqueued until re-enabled

## Contracts

### Export Service API

**GenerateExport(report_id, format, user_id, is_scheduled=false)**
- Applies user's row-level permissions to report query
- Generates CSV or PDF output
- Returns (success: bool, file_bytes: bytes | null, error_message: str | null, size_bytes: int | null)
- Raises SizeLimitExceeded if file > 50 MB before completion

**ValidateExportRequest(report_id, format, user_id)**
- Checks feature flag and workspace admin setting
- Checks user has access to report
- Returns (allowed: bool, reason: str | null)

### Schedule Manager API

**CreateSchedule(report_id, format, frequency, time, weekday, owner_id)**
- Validates inputs (frequency in [daily, weekly], time in range, weekday if weekly)
- Creates ScheduledExport record
- Enqueues next scheduled run
- Returns schedule_id or error

**GetSchedule(schedule_id, requester_id)**
- Returns ScheduledExport details or 403 if requester is not owner
- Returns schedule_id, report_id, format, frequency, status, created_at, updated_at

**PauseSchedule(schedule_id, requester_id)**
- Sets status = paused, updates pause_reason to "user_paused"
- Returns updated ScheduledExport or 403 if not owner

**ResumeSchedule(schedule_id, requester_id)**
- Sets status = active, clears pause_reason
- Enqueues next scheduled run
- Returns updated ScheduledExport or 403 if not owner

**DeleteSchedule(schedule_id, requester_id)**
- Deletes ScheduledExport record
- Cancels any pending runs
- Logs audit event
- Returns success or 403 if not owner

**GetRunHistory(schedule_id, requester_id, limit=30)**
- Returns list of ExportRun records for schedule, ordered by scheduled_at desc, limited to 30 most recent
- Includes status, attempt_number, timestamps, error_message, and file_size_bytes
- Returns 403 if requester is not owner

### Delivery & Retry Engine API

**SendExportEmail(export_id, recipient_email, export_run_id)**
- Attaches generated file to email
- Sends to recipient
- Returns (success: bool, error_message: str | null, attempt_number: int)
- On failure, does not retry; caller responsible for enqueueing retry

**RetryFailedDelivery(export_run_id)**
- Increments attempt_number in ExportRun
- Calculates exponential backoff based on attempt_number
- Enqueues retry task if attempt_number < 3
- If attempt_number = 3 and fails, pauses schedule and notifies owner

### Notification API

**NotifyScheduleFailure(schedule_id, owner_id, reason)**
- Sends email to owner with:
  - Schedule details (report name, frequency)
  - Failure reason (generation failed, delivery failed after retries)
  - Action: pause reason shown, user can resume later
- Logged as audit event

### Audit Log API

**LogExportEvent(action, user_id, export_id, context)**
- Persists audit event with timestamp
- Actions: export_created, export_failed, schedule_created, schedule_paused, schedule_resumed, schedule_deleted, export_delivered, export_delivery_failed

### Feature Flag & Admin Control API

**GetExportSettings(workspace_id)**
- Returns (feature_flag_enabled: bool, admin_disabled: bool)

**SetWorkspaceExportSetting(workspace_id, enabled: bool)**
- Admin-only
- Persists workspace setting
- Logged as audit event
