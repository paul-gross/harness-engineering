# Scheduled Report Exports — Technical Approach

## Architecture Outline

The export system comprises several interconnected components:

**Export Engine** — A stateless service that handles synchronous export generation (CSV and PDF rendering). It applies row-level permission filtering and enforces size limits before returning the generated file. All logic is user-aware and permission-aware.

**Scheduler Service** — An async background worker that manages recurring export schedules. It polls or processes scheduled jobs, invokes the export engine, and routes results to the delivery pipeline. The scheduler respects pause/resume state and tracks execution history.

**Delivery Pipeline** — An email delivery system with retry logic. It accepts generated exports from the scheduler, enqueues them for delivery, handles transient failures with exponential backoff (up to 3 retries), and pauses the schedule on exhaustion. It notifies the schedule owner on pause.

**Audit System** — A write-once log that records every export event (one-off and scheduled), capturing user identity, report details, format, file size, status, and timestamp.

**Feature Flag System** — Configuration that gates the entire feature (UI surface, API endpoints, background workers) and allows per-workspace admin control to disable exports entirely.

**Permission Layer** — Integrates with the existing row-level authorization system. Every export operation (one-off and scheduled) re-checks permissions at generation time, ensuring exported data never leaks rows the requesting user cannot access in the app.

These components are orchestrated such that:
- One-off exports are generated synchronously and returned directly to the user
- Scheduled exports are generated asynchronously without blocking interactive report viewing
- The export engine, scheduler, and delivery pipeline are decoupled (scheduler calls export engine, then hands output to delivery)
- All failures in delivery are caught and retried transparently to the user, with the schedule owner notified only if retries exhaust

## Domain Model

**Report** — An existing domain entity. Exports reference a report by ID and inherit the report's structure and permissions.

**Export** (abstract) — Represents a one-off or recurring export request.

**OneOffExport** — A transient export request with:
  - ID, user ID, report ID, format (CSV or PDF)
  - Generated file (bytes), size
  - Creation timestamp, completion timestamp
  - Status (pending, succeeded, failed)
  - Error message (if failed)

**ScheduledExport** — A recurring export configuration with:
  - ID, owner user ID, report ID, format (CSV or PDF)
  - Recurrence rule (daily, weekly, with day-of-week for weekly)
  - Delivery configuration (email recipient — always the owner)
  - Paused flag
  - Creation timestamp, last run timestamp, next scheduled run timestamp
  - Active status

**ExportRun** — A single execution of a scheduled export with:
  - ID, scheduled export ID, execution timestamp
  - Status (pending, succeeded, failed)
  - Generated file size
  - Delivery status (pending, sent, failed)
  - Failure reason (if failed)
  - Retry count
  - Error details (for audit trail)
  - Stored for the last 30 runs per scheduled export

**AuditLogEntry** — A log record for export events with:
  - Timestamp, user ID, workspace ID
  - Export type (one-off or scheduled)
  - Report ID, format, file size
  - Status, outcome
  - Any relevant error codes

**ExportPermissionSnapshot** — A runtime artifact created during export generation that lists the specific rows the requesting user is authorized to view. Used to filter export output.

## Key Workflows

### One-Off Export

1. User triggers export from the report UI (selects format: CSV or PDF)
2. System checks feature flag; if disabled, reject with clear message
3. System validates user has permission to view the report
4. Export engine generates file, applying row-level permission filtering:
   - Compute the set of rows the user can access
   - Exclude all other rows from output
5. System measures file size; if > 50 MB, reject with user-facing error (e.g., "Report too large to export")
6. System returns file to user as download
7. System records export event in audit log (success or failure)

### Scheduled Export Creation

1. User navigates to a report and creates a new scheduled export
2. System checks feature flag and report permissions
3. User specifies:
   - Export format (CSV or PDF)
   - Recurrence (daily or weekly; if weekly, day of week)
4. System validates configuration and stores the ScheduledExport entity
5. System calculates next scheduled run time (accounting for timezone if relevant)
6. System records creation in audit log

### Scheduled Export Execution and Delivery

1. Scheduler background worker awakens at the scheduled time for a ScheduledExport
2. Scheduler invokes the export engine with the schedule owner's user context (re-authorizes the owner's current row-level permissions)
3. Export engine generates file with current permission filtering:
   - Fetch current permissions for the schedule owner
   - Filter rows accordingly
   - Measure size
4. If size > 50 MB, the run fails (scheduled exports also respect the size limit); run is recorded as failed, schedule is paused, owner is notified
5. If generation succeeds, scheduler enqueues the file for delivery to the owner's email
6. Delivery pipeline attempts to send the email; on failure, retries up to 3 times with exponential backoff
7. If all 3 retries fail:
   - The run is marked as failed in ExportRun history
   - The schedule is automatically paused
   - The schedule owner is notified via email (a final "your scheduled export failed and has been paused" message)
8. If delivery succeeds, run is marked as successful
9. System records the run in ExportRun history (one entry per execution)
10. System updates next scheduled run time

### Scheduled Export Lifecycle Management

**View Runs** — Schedule owner can view ExportRun history for their schedule (read-only list of last 30 runs with status, timestamp, file size, and error details if failed).

**Pause** — Schedule owner can pause a schedule. No further runs are triggered until resumed.

**Resume** — Schedule owner can resume a paused schedule. Next run time is recalculated.

**Delete** — Schedule owner can delete a schedule. Future runs are canceled; past runs remain in audit log.

### Permission Re-Check for Scheduled Exports

Because report permissions can change between schedule creation and execution, the scheduler re-authorizes the schedule owner at each run:
- Fetch the schedule owner's current row-level permissions for the target report
- If permissions have been revoked, the exported file will be empty or contain only the remaining accessible rows
- If the owner no longer has any access to the report, the run fails with a clear error (owner is notified)

## Contracts

### Export Engine API

**`generate_export(user_id, report_id, format, timezone?)`** → `{file: bytes, size: int, row_count: int}`
- Accepts a user context, report ID, format (CSV or PDF), and optional timezone
- Applies row-level permission filtering for the given user
- Raises `PermissionDenied` if user cannot view the report
- Raises `FileTooLarge` if output exceeds 50 MB
- Raises `ReportNotFound` if report does not exist
- Returns the generated file and metadata (size, row count for audit purposes)

### Scheduler Service API

**`create_scheduled_export(owner_id, report_id, format, recurrence_rule)`** → `ScheduledExport`
- Creates and stores a new scheduled export
- Recurrence rule specifies daily, weekly with day, etc.
- Calculates and stores next run time
- Returns the created schedule
- Raises `PermissionDenied` if owner cannot view the report

**`pause_scheduled_export(schedule_id, requester_id)`** → void
- Pauses a schedule
- Raises `Unauthorized` if requester is not the schedule owner

**`resume_scheduled_export(schedule_id, requester_id)`** → void
- Resumes a paused schedule
- Recalculates next run time
- Raises `Unauthorized` if requester is not the schedule owner

**`delete_scheduled_export(schedule_id, requester_id)`** → void
- Soft-deletes a schedule (marks as inactive)
- Raises `Unauthorized` if requester is not the schedule owner

**`list_scheduled_exports(owner_id)`** → `[ScheduledExport]`
- Returns all active schedules owned by the given user
- Includes pause status, next run time, and last run result

**`get_export_run_history(schedule_id, requester_id, limit=30)`** → `[ExportRun]`
- Returns the last N execution records for a schedule
- Includes status, timestamp, file size, and error details
- Raises `Unauthorized` if requester is not the schedule owner

### Delivery Pipeline API

**`enqueue_export_for_delivery(export_run_id, recipient_email, file: bytes, report_name, format)`** → void
- Enqueues an export run for email delivery
- Automatically retries on transient failures (up to 3 times)
- On exhaustion, updates the associated ScheduledExport to paused and sends final notification

### Audit Log API

**`record_export_event(user_id, report_id, format, file_size, status, export_type, error_code?)`** → void
- Writes an immutable audit log entry
- Captures all export activity (one-off and scheduled)
- Includes status (success or failure) and error codes for post-hoc analysis

### Feature Flag API

**`is_export_enabled(workspace_id)`** → bool
- Returns whether exports are enabled for the workspace
- Admins can update this flag via workspace settings

**`is_export_enabled_for_user(user_id)`** → bool
- Composed check: feature flag is on AND user has permission to export (checked at API boundary)
