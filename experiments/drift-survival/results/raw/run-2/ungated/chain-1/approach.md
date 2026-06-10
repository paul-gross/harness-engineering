# Scheduled Report Exports — Technical Approach

## Architecture Outline

The scheduled report exports feature comprises four primary components:

1. **Export Service** — Handles on-demand and scheduled export generation, including format conversion (CSV, PDF), size validation, and async processing
2. **Scheduler Service** — Manages recurring export schedules, tracks execution history, handles pausing/resuming, and coordinates retry logic
3. **Delivery Service** — Manages email dispatch of completed exports, implements retry mechanisms, and tracks delivery status
4. **Audit & Feature Control** — Records all export events to the audit log and provides feature flag and admin controls for export functionality

These components operate asynchronously and are decoupled through message queues or job scheduling infrastructure. The flow follows this pattern:

- User initiates an export → Export Service validates permissions and size, queues async job
- Scheduled export triggers → Scheduler Service queues export job at configured frequency
- Export job completes → Delivery Service sends email to recipient
- Delivery fails → Retry logic automatically attempts redelivery (max 3 retries)
- Third retry fails → Scheduler Service pauses the schedule and records failure

Row-level security is enforced at the data retrieval layer: before any export is generated, the requesting user's permissions are evaluated to filter which rows are included. The export pipeline never bypasses this permission check.

## Domain Model

**Export** — Represents a single export instance (one-off or scheduled)
- `id`: unique identifier
- `report_id`: reference to the source report
- `format`: CSV or PDF
- `requested_by_user_id`: the user who initiated the export
- `status`: pending, generating, ready, delivered, failed
- `file_size_bytes`: size of the generated export
- `generated_at`: timestamp when export was completed
- `requested_at`: timestamp of export request

**ScheduledExport** — Represents a recurring export configuration
- `id`: unique identifier
- `export_id`: reference to the Export template (defines report, format, recipient)
- `owner_user_id`: the user who owns this schedule
- `frequency`: daily or weekly
- `delivery_email`: the recipient email address
- `is_active`: boolean indicating if the schedule is paused/resumed
- `created_at`: timestamp of schedule creation
- `last_run_at`: timestamp of the most recent execution
- `next_run_at`: timestamp of the next scheduled execution

**ExportRun** — Represents a single execution of a scheduled export
- `id`: unique identifier
- `scheduled_export_id`: reference to the parent schedule
- `export_id`: reference to the generated Export
- `ran_at`: timestamp of execution
- `delivery_status`: pending, delivered, failed_will_retry, failed_permanent
- `retry_count`: number of retry attempts made
- `error_message`: explanation if delivery failed

**AuditLogEntry** — Records all export activity
- `id`: unique identifier
- `event_type`: export_requested, export_generated, export_failed, scheduled_export_created, scheduled_export_paused, scheduled_export_resumed, export_delivered
- `user_id`: the user involved in the event
- `report_id`: the affected report
- `scheduled_export_id`: optional, if related to a scheduled export
- `details`: structured metadata about the event
- `created_at`: timestamp of the event

## Key Workflows

### On-Demand Export Workflow

1. User requests export of a report in CSV or PDF format
2. Export Service validates:
   - User has access to the report (through row-level permission check)
   - Export size does not exceed 50 MB threshold
   - Export feature is enabled (check feature flag)
3. If validation passes:
   - Queue async export job with user's permission context
   - Return job ID to user for tracking
   - Audit log records the export request
4. Async job executes:
   - Retrieve report data filtered by user's row-level permissions
   - Generate file in requested format
   - Validate final size does not exceed 50 MB
   - Store file and update Export status to "ready"
   - Audit log records successful generation
5. If size exceeds limit or generation fails:
   - Update Export status to "failed"
   - Audit log records the failure with reason
   - Return clear error message to user

### Scheduled Export Workflow

1. User creates a scheduled export:
   - Specify report, format, frequency (daily/weekly)
   - Designate delivery email address (defaults to owner's email)
   - Audit log records creation
2. Scheduler Service monitors schedules:
   - At each scheduled time, trigger export job
   - Pass user's permission context to ensure row-level security
3. Export job executes (same as on-demand workflow, but run asynchronously)
4. Upon successful generation:
   - Delivery Service queues email with export attachment
   - ExportRun record created with status "pending"
5. Email delivery executes:
   - Send email to designated recipient
   - Update ExportRun status to "delivered"
   - Audit log records delivery
6. If delivery fails:
   - Increment retry_count on ExportRun
   - If retry_count < 3: re-queue with exponential backoff
   - If retry_count == 3: update status to "failed_permanent", pause schedule, audit log records failure
7. Schedule pause/resume:
   - User can pause a schedule at any time (sets is_active to false)
   - User can resume a paused schedule (sets is_active to true)
   - Each action is recorded in audit log

### Export History View Workflow

1. User navigates to scheduled export details
2. System retrieves last 30 ExportRun records for that ScheduledExport
3. Display delivery status, timestamp, retry count, and any error messages
4. Provide transparency on delivery status (pending, delivered, failed, etc.)

### Admin Governance Workflow

1. Admin accesses workspace settings
2. Can enable or disable export functionality (controls feature flag state)
3. Audit log automatically records all such governance changes
4. When disabled, all export requests (one-off and scheduled) are rejected with appropriate error message

## Contracts

### Export Service API

**Request Export**
- Input: `report_id`, `format` (CSV or PDF), `user_context` (with row-level permissions)
- Output: `export_id`, `job_status` (pending/queued)
- Errors: `FeatureDisabled`, `UnauthorizedReport`, `InvalidFormat`, `ExportSizeExceeded`, `MaxExportSizeExceeded`

**Get Export Status**
- Input: `export_id`
- Output: `status`, `file_url` (if ready), `file_size_bytes`, `error_message` (if failed)

**Download Export**
- Input: `export_id`
- Output: file stream (CSV or PDF)
- Errors: `ExportNotReady`, `ExportExpired`, `NotAuthorized`

### Scheduler Service API

**Create Scheduled Export**
- Input: `report_id`, `format`, `frequency` (daily or weekly), `delivery_email`, `user_id`
- Output: `scheduled_export_id`
- Errors: `FeatureDisabled`, `UnauthorizedReport`, `InvalidFrequency`

**Pause Schedule**
- Input: `scheduled_export_id`, `user_id`
- Output: status confirmation
- Errors: `ScheduleNotFound`, `NotAuthorized`, `AlreadyPaused`

**Resume Schedule**
- Input: `scheduled_export_id`, `user_id`
- Output: status confirmation, `next_run_at`
- Errors: `ScheduleNotFound`, `NotAuthorized`, `NotPaused`

**Get Schedule History**
- Input: `scheduled_export_id`, `limit` (default 30)
- Output: list of ExportRun records with delivery_status, ran_at, retry_count, error_message

**Delete Schedule**
- Input: `scheduled_export_id`, `user_id`
- Output: status confirmation
- Errors: `ScheduleNotFound`, `NotAuthorized`

### Delivery Service API

**Queue Delivery**
- Input: `export_id`, `recipient_email`, `scheduled_export_id` (optional)
- Output: delivery job ID
- Internal API (triggered by scheduler or export service)

**Retry Delivery**
- Input: `export_run_id`, `retry_count`
- Output: status confirmation
- Internal API, called automatically when delivery fails

### Audit Service API

**Log Event**
- Input: `event_type`, `user_id`, `report_id`, `scheduled_export_id` (optional), `details`
- Output: audit log entry ID
- Internal API (called by other services)

**Get Audit Log**
- Input: filters (report_id, user_id, event_type, date range)
- Output: list of audit log entries
- Admin API

### Feature Control API

**Check Feature Enabled**
- Input: none (uses feature flag state)
- Output: boolean
- Internal API, checked before all export operations

**Set Export Feature State**
- Input: `enabled` (boolean), `admin_user_id`
- Output: status confirmation
- Admin API
- Errors: `NotAuthorized`

### Row-Level Permission Enforcement

All data retrieval for exports must pass through a permission filtering layer:

**Filter Data by User Permissions**
- Input: `report_id`, `user_id`, `raw_data` (all rows)
- Output: `filtered_data` (only rows the user can view)
- Called before any export format generation
- Ensures that the export pipeline never violates security boundaries
