# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature spans four main components:

1. **Export Service** — handles on-demand and scheduled export generation, coordinating CSV/PDF rendering with permission enforcement
2. **Export Scheduler** — manages recurring schedules and triggers export jobs at the configured frequency (daily/weekly)
3. **Email Delivery Queue** — persists export jobs awaiting delivery and implements retry logic with exponential backoff
4. **Export History & Audit** — records all export events (generation, delivery, failures) with user, report, type, timestamp, and status metadata

The feature flag gates all export-related endpoints and scheduler initialization at application startup. All permission validation flows through the requesting user's row-level authorization context to ensure no unauthorized rows leak into exports.

## Domain Model

**Report** — the source document being exported
- `id` (UUID)
- `name` (string)
- `owner_id` (user ID)
- `access_control` (ACL or permission scope)

**ExportSchedule** — a recurring export configuration
- `id` (UUID)
- `schedule_owner_id` (user ID who created the schedule)
- `report_id` (foreign key to Report)
- `export_format` (enum: CSV, PDF)
- `frequency` (enum: DAILY, WEEKLY)
- `day_of_week` (optional, for weekly schedules; enum: MON..SUN)
- `time_of_day` (time in owner's local timezone, or UTC if not timezone-aware)
- `is_paused` (boolean, default false)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**ExportJob** — an individual export task (on-demand or scheduled)
- `id` (UUID)
- `export_schedule_id` (nullable; null for one-off exports)
- `triggered_by_id` (user ID who triggered the export)
- `report_id` (foreign key to Report)
- `export_format` (enum: CSV, PDF)
- `status` (enum: PENDING, PROCESSING, READY, DELIVERED, FAILED)
- `error_message` (nullable, populated if status is FAILED)
- `file_path` (nullable, populated once export is ready)
- `file_size_bytes` (nullable, size of generated export)
- `created_at` (timestamp)
- `started_at` (nullable)
- `completed_at` (nullable)

**ExportDelivery** — tracks delivery attempts for a scheduled export job
- `id` (UUID)
- `export_job_id` (foreign key to ExportJob)
- `attempt_number` (1, 2, or 3)
- `recipient_email` (email of schedule owner)
- `status` (enum: PENDING, SENT, FAILED)
- `error_reason` (nullable, reason for failure)
- `attempted_at` (timestamp)
- `sent_at` (nullable)

**ExportAuditLog** — audit trail for compliance
- `id` (UUID)
- `export_job_id` (foreign key to ExportJob)
- `actor_user_id` (user ID performing the action)
- `action` (enum: GENERATED, DELIVERED, FAILED, PAUSED_DUE_TO_FAILURES)
- `report_id` (denormalized for query efficiency)
- `export_format` (denormalized)
- `row_count` (number of rows in the exported report, after permission filtering)
- `timestamp` (when the action occurred)

## Key Workflows

### One-Off Export

1. User requests export of a report in CSV or PDF format
2. Export Service fetches the report and the user's row-level permissions
3. Report data is filtered to include only rows the user can access
4. If filtered dataset exceeds 50 MB, reject with a user-facing error
5. CSV or PDF is generated in the background (non-blocking)
6. ExportJob is created with status PENDING, then transitioned to PROCESSING when work begins
7. Upon completion, ExportJob status becomes READY and file_path is set
8. User is notified (in-app or via callback) that the export is ready for download
9. Audit log entry is recorded with action=GENERATED

### Schedule Creation

1. User creates an ExportSchedule with report ID, format, frequency, and time-of-day
2. Validation ensures:
   - User has permission to read the report
   - Frequency and time-of-day are valid
3. ExportSchedule is persisted
4. Scheduler picks up the new schedule on its next polling cycle (or is notified via event)
5. Audit log entry records the schedule creation (implementation may treat this as a separate log type)

### Scheduled Export Trigger

1. Scheduler checks all active (non-paused) ExportSchedules at their configured frequency and time
2. For each matching schedule, Export Service creates an ExportJob with export_schedule_id set
3. Export Job follows the same generation flow as one-off exports
4. Once READY, the job is enqueued to Email Delivery Queue with status PENDING

### Email Delivery

1. Delivery Queue polls for PENDING delivery jobs
2. Email is sent to the ExportSchedule owner with the export attachment
3. On success, ExportDelivery status becomes SENT, and ExportJob status becomes DELIVERED
4. On failure, ExportDelivery status becomes FAILED with error_reason recorded
5. Delivery Queue reschedules the job for retry (exponential backoff, max 3 attempts)
6. After the 3rd failed attempt, ExportSchedule is automatically paused, and audit log records action=PAUSED_DUE_TO_FAILURES
7. Audit log entries record all delivery attempts and outcomes

### Pause/Resume Schedule

1. Schedule owner requests pause or resume of an ExportSchedule
2. System updates is_paused boolean and updated_at timestamp
3. Scheduler respects is_paused flag and skips trigger checks for paused schedules
4. Audit log records the pause/resume action

### Export History

1. Schedule owner requests the run history for a specific ExportSchedule
2. System returns the last 30 ExportJob records linked to that schedule (ordered by created_at DESC)
3. Each row includes job status, export format, file size, completion time, and delivery status
4. Audit log entries are accessible as supplementary context for each job

## Contracts

### Export Service API

**POST /api/exports** — Trigger a one-off export
- **Parameters:**
  - `report_id` (string, UUID)
  - `format` (string, enum: CSV, PDF)
- **Returns:** `ExportJob` with id and status=PENDING
- **Errors:**
  - 404 if report not found
  - 403 if user lacks read permission on report
  - 400 if format is invalid

**GET /api/exports/{export_job_id}** — Retrieve export job status and file URL
- **Parameters:** (path) `export_job_id`
- **Returns:** `ExportJob` (including file_path if status is READY or DELIVERED)
- **Errors:**
  - 404 if job not found
  - 403 if user is not the job creator

### Schedule Management API

**POST /api/export-schedules** — Create a recurring export schedule
- **Parameters:**
  - `report_id` (string, UUID)
  - `export_format` (string, enum: CSV, PDF)
  - `frequency` (string, enum: DAILY, WEEKLY)
  - `day_of_week` (optional, string or integer, required if frequency=WEEKLY)
  - `time_of_day` (string, HH:MM format in user's local timezone or UTC)
- **Returns:** `ExportSchedule`
- **Errors:**
  - 404 if report not found
  - 403 if user lacks read permission
  - 400 if frequency and time_of_day are invalid

**GET /api/export-schedules** — List schedules owned by the current user
- **Returns:** Array of `ExportSchedule`

**GET /api/export-schedules/{schedule_id}/history** — Retrieve run history
- **Parameters:** (path) `schedule_id`
- **Query:** `limit` (default 30, max 100)
- **Returns:** Array of `ExportJob` (last N runs, most recent first)
- **Errors:**
  - 404 if schedule not found
  - 403 if user is not the schedule owner

**PATCH /api/export-schedules/{schedule_id}** — Pause or resume a schedule
- **Parameters:** (path) `schedule_id`
- **Body:**
  - `is_paused` (boolean)
- **Returns:** `ExportSchedule`
- **Errors:**
  - 404 if schedule not found
  - 403 if user is not the schedule owner

**DELETE /api/export-schedules/{schedule_id}** — Delete a schedule
- **Parameters:** (path) `schedule_id`
- **Errors:**
  - 404 if schedule not found
  - 403 if user is not the schedule owner

### Admin Configuration API

**GET /api/admin/export-config** — Retrieve export feature settings
- **Returns:** `{ export_feature_enabled: boolean }`
- **Errors:**
  - 403 if user is not an admin

**PATCH /api/admin/export-config** — Update export feature settings
- **Parameters:**
  - `export_feature_enabled` (boolean)
- **Returns:** `{ export_feature_enabled: boolean }`
- **Errors:**
  - 403 if user is not an admin

### Audit Log API

**GET /api/audit-logs** — Query audit log for export events
- **Query parameters:**
  - `entity_type` (string, enum: EXPORT, SCHEDULE)
  - `action` (string, optional)
  - `date_range` (optional, start and end timestamps)
  - `page` (integer, default 1)
- **Returns:** Paginated array of `ExportAuditLog`
- **Errors:**
  - 403 if user is not an admin

### Feature Flag Interface

**isExportFeatureEnabled()** — Check if export feature is active
- **Returns:** boolean (derived from admin config or feature flag service)
- **Used by:** All export endpoints and scheduler initialization to gate functionality
