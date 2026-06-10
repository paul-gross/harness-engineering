# Scheduled Report Exports — Phase Plan

## Phase 1: Core Export Service and On-Demand Exports

**Goal:** Deliver the foundational export capability, allowing users to trigger one-off report exports in CSV and PDF formats with proper permission enforcement.

**Scope:**
- Implement the Export Service component with on-demand export generation
- Build the ExportJob domain model (status enum: PENDING, PROCESSING, READY, DELIVERED, FAILED)
- Integrate row-level permission filtering to ensure users only export authorized rows
- Implement the 50 MB file size validation gate
- Build background job processing for CSV and PDF rendering (non-blocking)
- Create POST /api/exports endpoint (trigger one-off export)
- Create GET /api/exports/{export_job_id} endpoint (retrieve job status and file URL)
- Add feature flag gating to both export endpoints
- Implement basic ExportAuditLog with GENERATED action
- Write tests covering happy path and error cases (missing report, permission denial, invalid format)

**Acceptance Criteria:**
- User can successfully request a CSV export of a report they have read access to
- User can successfully request a PDF export of a report they have read access to
- Export request rejected with 403 if user lacks read permission
- Export request rejected with 400 for invalid format
- Export request rejected with 400 if filtered dataset exceeds 50 MB
- Export job status transitions from PENDING → PROCESSING → READY
- User can retrieve export job status and download the file once READY
- Audit log contains GENERATED entry for each export with row count, format, and timestamp
- Feature flag gates export endpoints; requests return 403 when disabled

---

## Phase 2: Export Scheduling and Scheduler Infrastructure

**Goal:** Build recurring export configuration and the scheduler daemon that triggers exports at their configured frequency.

**Scope:**
- Implement the ExportSchedule domain model (frequency: DAILY/WEEKLY, time_of_day, day_of_week)
- Store ExportSchedule with timezone awareness (user's local timezone or UTC fallback)
- Create POST /api/export-schedules endpoint (create recurring schedule)
- Create GET /api/export-schedules endpoint (list user's own schedules)
- Create PATCH /api/export-schedules/{schedule_id} endpoint (pause/resume)
- Create DELETE /api/export-schedules/{schedule_id} endpoint (delete schedule)
- Implement the Export Scheduler component with polling mechanism
- Wire scheduler to trigger ExportJob creation for all active schedules at their configured time
- Scheduler respects is_paused flag and skips paused schedules
- Add feature flag gating to all schedule management endpoints and scheduler initialization
- Log schedule creation, pause, and resume events to audit log
- Write tests covering schedule CRUD, timezone handling, polling behavior, and pause/resume logic

**Acceptance Criteria:**
- User can create an ExportSchedule for a report they have read access to
- Schedule creation rejects with 403 if user lacks read permission
- Schedule creation rejects with 400 for invalid frequency or time-of-day
- User can list only their own ExportSchedules
- User can pause an ExportSchedule they own; scheduler skips paused schedules
- User can resume a paused ExportSchedule
- User can delete an ExportSchedule they own
- Scheduler daemon initializes only if feature flag is enabled
- Scheduler correctly triggers exports at configured DAILY and WEEKLY times
- Audit log records schedule creation, pause, and resume actions
- DELETE endpoint returns 404 if schedule not found; 403 if not owner

---

## Phase 3: Email Delivery Queue and Retry Logic

**Goal:** Implement persistent delivery of scheduled exports via email with exponential backoff retry and automatic schedule pausing on repeated failures.

**Scope:**
- Implement the ExportDelivery domain model (attempt_number, status: PENDING/SENT/FAILED, error_reason, retry timestamps)
- Build the Email Delivery Queue component with persistence layer
- Implement delivery job polling mechanism (picks up READY exports from scheduled runs)
- Integrate email sending (attachment handling, recipient = schedule owner)
- Implement exponential backoff retry logic (max 3 attempts)
- Implement automatic schedule pause on 3rd failed delivery attempt
- Update ExportJob status flow to include DELIVERED state
- Log delivery attempts (success and failures) to ExportAuditLog with action=DELIVERED or action=PAUSED_DUE_TO_FAILURES
- Write tests covering email delivery, retry behavior, and automatic pause logic

**Acceptance Criteria:**
- Scheduled export transitions to READY, then is enqueued for delivery
- Email is successfully sent to schedule owner with export attachment on first attempt
- On email send failure, ExportDelivery status becomes FAILED with error_reason recorded
- Delivery Queue retries failed jobs with exponential backoff (up to 3 attempts)
- After 3rd failed attempt, ExportSchedule is automatically paused
- Audit log contains DELIVERED entry on successful email delivery
- Audit log contains PAUSED_DUE_TO_FAILURES entry when schedule is auto-paused
- Subsequent scheduled runs do not trigger while schedule is paused (verified by scheduler behavior)

---

## Phase 4: Export History and Audit Reporting

**Goal:** Provide users with visibility into their export schedule run history and enable admins to audit all export activity.

**Scope:**
- Implement GET /api/export-schedules/{schedule_id}/history endpoint
- Return last N ExportJobs for a schedule (default 30, max 100), ordered by created_at DESC
- Include job status, export format, file size, completion time, and delivery status for each job
- Create GET /api/audit-logs endpoint with query filters (entity_type, action, date_range, pagination)
- Gate audit log endpoint to admin-only access
- Ensure audit log contains all export-related events (GENERATED, DELIVERED, FAILED, PAUSED_DUE_TO_FAILURES)
- Write tests covering history retrieval, permission checks, and audit log filtering

**Acceptance Criteria:**
- User can retrieve run history for an ExportSchedule they own
- History endpoint returns 404 if schedule not found; 403 if user is not owner
- History response includes all required fields (status, format, file size, completion time, delivery status)
- History is paginated and ordered newest-first
- Admin can query audit logs filtered by entity_type, action, and date_range
- Audit log endpoint returns 403 if user is not admin
- All export-related actions (generation, delivery, pause) are recorded in audit log with proper metadata (actor_user_id, report_id, row_count, timestamp)

---

## Phase 5: Admin Configuration and Feature Flag Management

**Goal:** Provide admin tools for managing the export feature flag and exporting feature settings.

**Scope:**
- Implement GET /api/admin/export-config endpoint (returns export_feature_enabled flag)
- Implement PATCH /api/admin/export-config endpoint (admin updates feature flag)
- Gate both admin config endpoints to admin-only access
- Wire feature flag state to gate all export Service, Scheduler, and Delivery Queue operations
- Implement startup checks: scheduler and delivery queue initialize only if feature flag is enabled
- Write tests covering feature flag gating and endpoint access control

**Acceptance Criteria:**
- Admin can retrieve current export feature flag state
- Admin can enable or disable the export feature flag via PATCH endpoint
- Non-admin users receive 403 when attempting to access admin config endpoints
- When feature flag is disabled, all export endpoints return 403
- When feature flag is disabled, scheduler daemon does not initialize at startup
- When feature flag is disabled, delivery queue does not process pending jobs
- Feature flag changes are immediately reflected in all running components (or require restart if appropriate for architecture)
