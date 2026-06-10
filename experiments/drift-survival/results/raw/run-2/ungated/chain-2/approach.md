# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports system consists of five primary components:

1. **Export Engine** — handles on-demand and scheduled export generation with permission filtering
2. **Scheduled Export Manager** — manages the lifecycle of recurring export schedules (CRUD, pause/resume, frequency)
3. **Delivery Service** — queues exports and delivers them via email with retry logic
4. **Audit Logger** — records all export events (on-demand and scheduled, successes and failures)
5. **Feature Flag Controller** — gates export visibility and access, with admin workspace override capability

These components interact in a pipeline: scheduled exports are triggered by a background scheduler, the export engine generates the report with permission filtering, the delivery service handles email transmission with retries, and the audit logger captures the entire lifecycle event. On-demand exports follow a simpler path—synchronously generated then immediately returned to the user—while still logging to audit.

The export engine runs asynchronously for scheduled exports to prevent blocking interactive report viewing, while on-demand exports may be returned to the user once generated (implementation detail).

## Domain Model

### Core Entities

**Export** — represents a single export instance
- `id` (UUID)
- `report_id` (foreign key to Report)
- `requested_by_user_id` (the user who initiated the export)
- `export_format` (enum: CSV, PDF)
- `requested_at` (timestamp)
- `generated_at` (timestamp, null if pending/failed)
- `file_size_bytes` (null if pending/failed)
- `status` (enum: PENDING, GENERATED, DELIVERED, FAILED, REJECTED)
- `rejection_reason` (nullable, e.g., "export exceeds 50 MB limit")
- `is_scheduled` (boolean, true if part of a scheduled export)

**ScheduledExport** — represents a recurring export schedule
- `id` (UUID)
- `report_id` (foreign key to Report)
- `owner_user_id` (the user who owns/created the schedule)
- `email_recipient` (the email address, initially = owner email)
- `frequency` (enum: DAILY, WEEKLY)
- `export_format` (enum: CSV, PDF)
- `next_run_at` (timestamp for next scheduled execution)
- `is_paused` (boolean)
- `paused_at` (timestamp, null if not paused)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- `delivery_history_retention_days` (defaults to 30 for query purposes)

**ExportDeliveryAttempt** — represents a single delivery attempt
- `id` (UUID)
- `export_id` (foreign key to Export)
- `scheduled_export_id` (foreign key to ScheduledExport, nullable for on-demand)
- `attempt_number` (1–3)
- `attempted_at` (timestamp)
- `status` (enum: SUCCESS, FAILED)
- `failure_reason` (nullable)
- `email_sent_to` (the recipient email)

### Relationships

- A **Report** has many **ScheduledExports**
- A **ScheduledExport** has many **Exports** (one per run)
- An **Export** has many **ExportDeliveryAttempts** (up to 3)
- A **ScheduledExport** is owned by one **User**
- An **Export** is requested by one **User**

## Key Workflows

### On-Demand Export

1. User requests export (CSV or PDF format) from a report detail page
2. Feature flag is checked; if disabled, user sees "exports unavailable" message
3. Export Engine:
   - Retrieves the report definition and user's row-level permissions
   - Generates the export data, filtering rows user can access
   - Computes file size
   - If file size > 50 MB, rejects with error message; logs REJECTED event to audit
   - If file size ≤ 50 MB, generates export file, saves to storage, updates Export.status to GENERATED
4. Export file is returned to user (via direct download link or email, implementation detail)
5. Audit Logger records: export requested, format, requesting user, result (success/rejection)

### Scheduled Export Lifecycle (Create)

1. User navigates to "Schedule Exports" interface
2. User selects a report, chooses frequency (DAILY or WEEKLY), selects format (CSV or PDF)
3. System creates ScheduledExport record:
   - `owner_user_id` = current user
   - `email_recipient` = current user's email (initially; design allows updates later)
   - `is_paused` = false
   - `next_run_at` = calculated based on frequency
4. Audit Logger records: scheduled export created, owner, frequency, report, format

### Scheduled Export Execution (Triggered by Background Scheduler)

1. Background scheduler checks all non-paused ScheduledExports with `next_run_at` ≤ now
2. For each scheduled export:
   - Retrieve the report and owner user's row-level permissions (as of execution time)
   - Export Engine generates export data with permission filtering
   - If file size > 50 MB, log rejection and pause the schedule (user visibility: delivery history shows "rejected — export too large")
   - If file size ≤ 50 MB:
     - Create Export record with `is_scheduled = true`
     - Queue delivery via Delivery Service
     - Audit Logger records: scheduled export generated, format, size, scheduled export ID
     - Update ScheduledExport.next_run_at for next occurrence

### Scheduled Export Delivery (Retry Logic)

1. Delivery Service dequeues export
2. Attempt 1: Send email with export attachment to `email_recipient`
   - On success: ExportDeliveryAttempt recorded, Export.status = DELIVERED, schedule continues
   - On failure: ExportDeliveryAttempt recorded, Delivery Service schedules Attempt 2 (after delay, e.g., 1 hour)
3. Attempt 2: Repeat attempt 1
   - On success: Export.status = DELIVERED, schedule continues
   - On failure: Delivery Service schedules Attempt 3
4. Attempt 3: Repeat attempt 1
   - On success: Export.status = DELIVERED, schedule continues
   - On failure: ExportDeliveryAttempt recorded, ScheduledExport.is_paused = true, ScheduledExport.paused_at = now
     - Audit Logger records: scheduled export auto-paused due to 3 failed delivery attempts
     - User sees in UI: delivery history shows "paused after 3 failed attempts"

### Scheduled Export Pause / Resume

1. User can pause a schedule from the schedule detail page
   - Set `is_paused = true`, `paused_at = now`
   - Audit Logger records: scheduled export paused by user
2. User can resume a paused schedule
   - Set `is_paused = false`, `paused_at = null`
   - Recalculate `next_run_at` based on frequency
   - Audit Logger records: scheduled export resumed by user

### Delivery History

1. User navigates to scheduled export detail
2. System retrieves ExportDeliveryAttempt records for the ScheduledExport where `attempted_at` >= now - 30 days
3. Display sorted by attempted_at (descending): export date, format, file size, delivery status (all 3 attempts if there were retries), final status (SUCCESS or FAILED after 3 attempts)

### Audit Logging

Every export event is recorded with:
- Event type (EXPORT_REQUESTED, EXPORT_GENERATED, EXPORT_REJECTED, EXPORT_DELIVERED, EXPORT_DELIVERY_FAILED, SCHEDULED_EXPORT_CREATED, SCHEDULED_EXPORT_PAUSED, SCHEDULED_EXPORT_RESUMED, SCHEDULED_EXPORT_AUTO_PAUSED)
- User ID (who triggered the event)
- Report ID
- Export format
- Result (success/reason for failure)
- Timestamp

## Contracts

### Export Engine API

**`generate_export(report_id, user_id, format) -> Export | ExportRejection`**
- Input: `report_id` (UUID), `user_id` (UUID), `format` (CSV | PDF)
- Output: `Export` object with file metadata and storage location, or `ExportRejection` with reason (size, permission, etc.)
- Behavior: Filters report data by user's row-level permissions, generates file, validates size ≤ 50 MB
- Async or sync: Implementation detail; must not block other operations

**`get_export(export_id) -> Export`**
- Returns the Export object with status, file metadata, and download link if generated

### Scheduled Export Manager API

**`create_scheduled_export(report_id, owner_user_id, frequency, format) -> ScheduledExport`**
- Input: `report_id` (UUID), `owner_user_id` (UUID), `frequency` (DAILY | WEEKLY), `format` (CSV | PDF)
- Output: `ScheduledExport` object with ID, next_run_at, and email recipient
- Behavior: Creates schedule, calculates next_run_at based on frequency (next occurrence)

**`pause_scheduled_export(scheduled_export_id, user_id) -> ScheduledExport`**
- Input: `scheduled_export_id` (UUID), `user_id` (UUID requesting the pause)
- Output: Updated ScheduledExport with is_paused = true
- Validation: Only the schedule owner can pause

**`resume_scheduled_export(scheduled_export_id, user_id) -> ScheduledExport`**
- Input: `scheduled_export_id` (UUID), `user_id` (UUID requesting the resume)
- Output: Updated ScheduledExport with is_paused = false, recalculated next_run_at
- Validation: Only the schedule owner can resume

**`get_scheduled_export(scheduled_export_id) -> ScheduledExport`**
- Returns the ScheduledExport object with status, owner, frequency, and next_run_at

**`list_scheduled_exports(report_id) -> [ScheduledExport]`**
- Returns all active and paused schedules for a report

### Delivery Service API

**`queue_export_for_delivery(export_id, scheduled_export_id, email_recipient) -> void`**
- Queues an export for email delivery with initial attempt count = 1
- Behavior: Async processing; will retry up to 3 times on failure

**`get_delivery_history(scheduled_export_id, days=30) -> [ExportDeliveryAttempt]`**
- Returns delivery attempts for a schedule within the last N days, sorted by attempted_at descending

### Audit Logger API

**`log_export_event(event_type, user_id, report_id, export_id, format, result, details) -> void`**
- Records an export event with metadata for compliance and debugging
- Event types: EXPORT_REQUESTED, EXPORT_GENERATED, EXPORT_REJECTED, EXPORT_DELIVERED, EXPORT_DELIVERY_FAILED, SCHEDULED_EXPORT_*, etc.

### Feature Flag Controller API

**`is_export_enabled(workspace_id) -> boolean`**
- Returns true if export feature is enabled for the workspace
- Checked before allowing any export UI/API access

**`disable_exports(workspace_id) -> void`**
- Admin operation to disable all export functionality for a workspace

**`enable_exports(workspace_id) -> void`**
- Admin operation to enable export functionality for a workspace
