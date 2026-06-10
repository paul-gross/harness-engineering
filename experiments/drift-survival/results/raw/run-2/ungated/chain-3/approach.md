# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature spans three primary layers:

**API and User-Facing Layer** — HTTP endpoints and UI surfaces for creating, managing, and viewing exports and schedules. Includes one-off export generation and schedule CRUD operations (create, pause, resume, delete).

**Export Engine** — Asynchronous processing layer that handles export generation in the background. Accepts export jobs from the API, applies permission filtering, generates CSV/PDF output, stores artifacts, and records audit events. Fails gracefully when exports exceed size limits.

**Scheduler and Delivery Layer** — Background job orchestration that triggers scheduled exports at their configured recurrence (daily, weekly), enqueues delivery jobs, implements retry logic with exponential backoff (up to 3 attempts), and auto-pauses schedules after final failure.

**Audit and Observability Layer** — Records all export and schedule events, delivery attempts, and administrator actions. Provides queryable history of export runs per schedule.

**Feature Flag System** — Workspace-level gating that allows admins to enable/disable the entire feature and controls visibility in the UI.

These layers interact as follows:
- User creates export or schedule via API
- Export request flows to Export Engine, which generates artifact and records event
- For scheduled exports, Scheduler enqueues delivery jobs at configured intervals
- Delivery jobs attempt to send email; failures trigger automatic retry
- All events (exports, deliveries, admin toggles) flow to Audit Log
- UI surfaces export history and schedule state from Audit Log and Schedule state

## Domain Model

**Report** — existing entity representing a configured report query. Identified by `report_id`. No changes to existing Report structure required.

**Export** — represents a single export operation (one-off or triggered by a schedule).
- `export_id`: unique identifier
- `report_id`: the report being exported
- `requested_by`: user ID of the exporter
- `format`: enum (CSV, PDF)
- `status`: enum (pending, generating, succeeded, failed, rejected)
- `artifact_url`: signed URL to the export file (null if failed/pending)
- `artifact_size_bytes`: size of generated artifact
- `created_at`: timestamp
- `completed_at`: timestamp (null if pending)
- `error_reason`: string describing why export failed (size limit, permission error, generation error, etc.)

**ExportSchedule** — represents a recurring export configuration.
- `schedule_id`: unique identifier
- `report_id`: the report being exported
- `owner_id`: user ID of the schedule owner
- `format`: enum (CSV, PDF)
- `recurrence`: enum (daily, weekly) + configuration (day of week if weekly)
- `status`: enum (active, paused)
- `paused_reason`: string explaining why paused (e.g. "auto_paused_after_delivery_failures", "user_paused")
- `email_recipients`: list of email addresses (initially just owner, extensible for future)
- `created_at`: timestamp
- `last_triggered_at`: timestamp of last scheduled job execution
- `next_scheduled_at`: timestamp of next scheduled job execution

**ExportRun** — an execution of a scheduled export (join between Export and ExportSchedule).
- `run_id`: unique identifier
- `schedule_id`: the schedule that triggered this export
- `export_id`: the generated Export
- `triggered_at`: when the schedule triggered
- `delivery_attempts`: count of email delivery attempts
- `last_delivery_attempt_at`: timestamp
- `delivery_status`: enum (pending, succeeded, failed)
- `delivery_error`: string describing last delivery error

**AuditEvent** — immutable record of all system activity.
- `event_id`: unique identifier
- `event_type`: enum (export_requested, export_completed, export_failed, schedule_created, schedule_paused, schedule_resumed, schedule_deleted, delivery_attempted, delivery_succeeded, delivery_failed, feature_toggled)
- `actor_id`: user ID of the actor (null for system-triggered events)
- `actor_role`: "user" or "admin"
- `resource_type`: enum (export, schedule, feature_flag)
- `resource_id`: ID of the affected resource
- `details`: JSON object with context-specific fields (e.g. export format, error reason, retry count)
- `created_at`: timestamp

**FeatureFlag** — workspace-level configuration controlling export functionality.
- `workspace_id`: scope
- `feature_key`: "scheduled_exports"
- `enabled`: boolean
- `toggled_by`: user ID of the admin who last toggled
- `toggled_at`: timestamp

## Key Workflows

### User Initiates One-Off Export

1. User selects "Export" from report UI, chooses format (CSV/PDF)
2. Frontend calls `POST /reports/{report_id}/exports` with format parameter
3. API validates user has read access to report (via existing permission model)
4. API creates Export record with status=pending
5. API enqueues async export job
6. API returns export_id and polling URL to frontend
7. Frontend polls export status endpoint
8. Export Engine dequeues job, applies row-level permission filter to data
9. Export Engine generates file (CSV or PDF conversion)
10. If file size > 50 MB: Export record status=rejected, error="Export exceeds 50 MB limit", audit event logged
11. If generation succeeds: Export saved to durable storage, status=succeeded, artifact_url set
12. If generation fails (permission error, query timeout, etc.): status=failed, error_reason set
13. Audit event recorded (export_completed or export_failed)
14. Frontend receives success or error state and presents to user

### User Creates Scheduled Export

1. User navigates to "Schedule Exports" UI
2. User selects report, format, recurrence (daily/weekly), day-of-week if applicable
3. Frontend calls `POST /schedules` with report_id, format, recurrence config, owner_id
4. API validates user owns the resource and feature flag is enabled
5. API creates ExportSchedule record with status=active
6. API calculates next_scheduled_at based on recurrence
7. Scheduler service picks up the schedule and registers it in internal job queue
8. Audit event logged (schedule_created)
9. UI shows schedule in list with status, recurrence, next run time

### Scheduler Triggers Scheduled Export

1. Scheduler wakes at scheduled time (via cron or job queue)
2. Scheduler dequeues ExportSchedule(s) due to run
3. For each due schedule:
   - Validates schedule is still active (status != paused)
   - Calls Export Engine to generate export (same as one-off workflow)
   - Creates ExportRun record linked to Export and ExportSchedule
   - Updates ExportSchedule.last_triggered_at
   - Calculates and sets next_scheduled_at
4. Enqueues delivery job with delivery_attempts=0
5. Audit event logged (schedule_triggered)

### Delivery with Retry Logic

1. Delivery job woken by job queue
2. Retrieves ExportRun and presigned artifact URL
3. Composes email to schedule owner with artifact attached (or link in email body for PDF)
4. Attempts to send via email service
5. **Success path**: delivery_status=succeeded, audit event logged (delivery_succeeded), workflow ends
6. **Failure path**:
   - delivery_attempts incremented
   - If delivery_attempts < 3:
     - Schedule retry with exponential backoff (e.g. 1 min, 5 min, 15 min)
     - delivery_status=pending, audit event logged (delivery_attempted with attempt count)
   - If delivery_attempts == 3:
     - ExportSchedule.status = paused
     - ExportSchedule.paused_reason = "auto_paused_after_delivery_failures"
     - In-app notification sent to schedule owner (future: email notification)
     - delivery_status=failed, audit event logged (schedule_auto_paused)

### User Pauses/Resumes Schedule

1. User clicks "Pause" or "Resume" on schedule in UI
2. Frontend calls `PATCH /schedules/{schedule_id}` with action="pause" or action="resume"
3. API updates ExportSchedule.status and paused_reason (user-paused or active)
4. API recalculates next_scheduled_at if resuming
5. Scheduler daemon reloads schedule from database (polling or event-driven)
6. Audit event logged (schedule_paused or schedule_resumed with reason)

### User Views Export History

1. User navigates to schedule detail page
2. Frontend calls `GET /schedules/{schedule_id}/runs?limit=30`
3. API queries ExportRun records, joined with Export records, ordered by created_at DESC
4. API returns list with status, timestamp, delivery_attempts, error messages
5. UI renders table showing last 30 runs with status badges and timestamps

### Admin Toggles Export Feature

1. Admin navigates to workspace settings → Export Controls
2. Admin toggles "Enable Export & Scheduling" on/off
3. Frontend calls `PATCH /workspace/features/scheduled_exports` with enabled=true/false
4. API updates FeatureFlag record
5. API audit event logged (feature_toggled)
6. If disabled:
   - All active schedules remain in database but are skipped by scheduler
   - Export API endpoints return 403 with "Feature disabled" message
7. If re-enabled:
   - Schedules resume according to their next_scheduled_at (no data loss)

## Contracts

### Export API

**POST /reports/{report_id}/exports**
- Request: `{ format: "CSV" | "PDF" }`
- Response: `{ export_id, status, created_at, polling_url }`
- Errors: 403 Forbidden (permission denied), 400 Bad Request (invalid format), 503 Service Unavailable (feature disabled)

**GET /exports/{export_id}**
- Response: `{ export_id, report_id, requested_by, format, status, artifact_url, artifact_size_bytes, created_at, completed_at, error_reason }`
- Errors: 404 Not Found, 403 Forbidden (not the requester)

**GET /exports/{export_id}/download**
- Redirects to presigned artifact URL (S3 or equivalent)
- Errors: 404 Not Found, 403 Forbidden, 410 Gone (artifact expired)

### Schedule API

**POST /schedules**
- Request: `{ report_id, format, recurrence: "daily" | "weekly", recurrence_config: { day_of_week?: number }, owner_id }`
- Response: `{ schedule_id, report_id, owner_id, status, created_at, next_scheduled_at }`
- Errors: 403 Forbidden (permission denied, feature disabled), 400 Bad Request (invalid config)

**GET /schedules**
- Query: `?owner_id={owner_id}&status={active|paused}`
- Response: `[{ schedule_id, report_id, owner_id, format, status, paused_reason, recurrence, last_triggered_at, next_scheduled_at, created_at }]`
- Errors: 403 Forbidden (can only list own schedules; admins can list all)

**GET /schedules/{schedule_id}**
- Response: `{ schedule_id, report_id, owner_id, format, status, paused_reason, recurrence, last_triggered_at, next_scheduled_at, created_at }`
- Errors: 404 Not Found, 403 Forbidden (not owner)

**PATCH /schedules/{schedule_id}**
- Request: `{ action: "pause" | "resume", reason?: string }`
- Response: `{ schedule_id, status, paused_reason, updated_at }`
- Errors: 404 Not Found, 403 Forbidden (not owner), 400 Bad Request (invalid transition)

**DELETE /schedules/{schedule_id}**
- Response: 204 No Content
- Errors: 404 Not Found, 403 Forbidden (not owner)

**GET /schedules/{schedule_id}/runs**
- Query: `?limit=30&offset=0`
- Response: `{ runs: [{ run_id, export_id, triggered_at, status, delivery_attempts, last_delivery_attempt_at, export_status, export_error, delivery_error }] }`
- Errors: 404 Not Found, 403 Forbidden (not owner)

### Audit Log API

**GET /audit**
- Query: `?resource_type={export|schedule|feature_flag}&resource_id={id}&event_type={...}&actor_id={id}&limit=100`
- Response: `{ events: [{ event_id, event_type, actor_id, resource_type, resource_id, details, created_at }] }`
- Errors: 403 Forbidden (non-admins can only query own events)

### Feature Flag API

**GET /workspace/features/scheduled_exports**
- Response: `{ enabled: boolean, toggled_by: user_id, toggled_at: timestamp }`

**PATCH /workspace/features/scheduled_exports**
- Request: `{ enabled: boolean }`
- Response: `{ enabled, toggled_by, toggled_at }`
- Errors: 403 Forbidden (requires admin role)

### Async Job Contracts

**Export Job Queue**
- Input: `{ export_id, report_id, requested_by, format, permission_context }`
- Output: updates Export record (status, artifact_url, error_reason) and audit log

**Delivery Job Queue**
- Input: `{ run_id, schedule_id, export_id, delivery_attempts, email_recipient }`
- Output: updates ExportRun record (delivery_status, delivery_attempts) and audit log
