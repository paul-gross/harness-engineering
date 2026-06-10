# Scheduled Report Exports — Phase Plan

## Phase 1: Data Model and Foundation

**Goal:** Establish the database schema and core entities required for scheduled exports, audit logging, and feature flagging.

**Scope:**
- Create Export, ExportSchedule, ExportRun, AuditEvent, and FeatureFlag database tables with appropriate indexes
- Implement database migrations
- Create data access objects (DAOs) or ORM models for all entities
- Implement soft-delete or archive patterns for audit trail integrity
- Set up audit event creation utilities (helper functions to log events consistently)

**Acceptance Criteria:**
- All five tables exist in the database with correct schema
- Foreign key relationships between Export, ExportSchedule, and ExportRun are enforced
- Indexes on frequently queried columns (report_id, owner_id, schedule_id, created_at, next_scheduled_at) exist
- Audit event helpers can be called to record an event with all required fields
- Database rollback/rollforward migrations pass in test environments

## Phase 2: API Layer — One-Off Exports and Permissions

**Goal:** Deliver HTTP endpoints for creating and retrieving one-off exports, with permission validation integrated into the API contract.

**Scope:**
- Implement `POST /reports/{report_id}/exports` endpoint (create one-off export, enqueue job)
- Implement `GET /exports/{export_id}` endpoint (retrieve export metadata and status)
- Implement `GET /exports/{export_id}/download` endpoint (redirect to presigned artifact URL)
- Add permission checks (user must have read access to the report)
- Add feature flag checks (if feature disabled, return 403)
- Integrate with existing permission model to validate report access
- Wire audit event logging for export creation and completion events
- Return appropriate error responses (403, 404, 400, 503)

**Acceptance Criteria:**
- `POST /reports/{report_id}/exports` creates an Export record with status=pending and returns export_id
- `GET /exports/{export_id}` returns complete export metadata including status, artifact_url, and error_reason
- Users cannot export reports they lack read access to (403 response)
- When feature flag is disabled, export endpoints return 403
- Export events are logged to AuditEvent table (export_requested, export_completed, export_failed)
- Download endpoint redirects to presigned artifact URL with correct expiration

## Phase 3: Export Engine and Async Processing

**Goal:** Implement the background export generation pipeline that processes export jobs and handles large dataset constraints.

**Scope:**
- Create Export Engine worker/consumer that dequeues export jobs from async job queue
- Apply row-level permission filtering to exported data (enforce same filters as report UI)
- Implement CSV generation with proper encoding and escaping
- Implement PDF generation (using existing PDF library or third-party service)
- Add 50 MB size limit enforcement with graceful rejection
- Implement presigned URL generation for artifact storage (S3 or equivalent)
- Integrate error handling with Export record status and error_reason fields
- Wire audit event logging (export_completed, export_failed events)
- Add retry/failure recovery for transient errors (query timeouts, temporary service unavailability)

**Acceptance Criteria:**
- Export job dequeued from async queue and status transitions from pending to generating
- CSV exports generate with correct data, proper escaping, and headers
- PDF exports generate with correct data and formatting
- Exports exceeding 50 MB are rejected with status=rejected and error="Export exceeds 50 MB limit"
- Successful exports create presigned URLs valid for 7 days (configurable)
- Failures update Export.error_reason with descriptive message (permission error, query timeout, generation error, etc.)
- Audit events recorded for all completion paths (success and failure)
- Export status polled via GET /exports/{export_id} reflects actual state

## Phase 4: Scheduler, Delivery, and Retry Logic

**Goal:** Deliver scheduled export triggering at configured recurrence with email delivery and retry resilience.

**Scope:**
- Implement Scheduler service (cron job or job queue consumer) that wakes at scheduled intervals
- Implement schedule activation logic (validate schedule is active, call Export Engine for generation)
- Create ExportRun records to link Schedule to generated Export
- Implement Delivery Job consumer that sends export via email
- Implement retry logic with exponential backoff (1 min, 5 min, 15 min for attempts 1, 2, 3)
- Implement auto-pause logic: after 3 failed delivery attempts, pause schedule and set paused_reason
- Send in-app notification to schedule owner on auto-pause
- Update ExportSchedule.last_triggered_at and recalculate next_scheduled_at
- Wire audit event logging (schedule_triggered, delivery_attempted, delivery_succeeded, delivery_failed, schedule_auto_paused)
- Add persistence for scheduler state (poll database periodically for new/updated schedules or use event-driven triggers)

**Acceptance Criteria:**
- Scheduler wakes at configured time and triggers due schedules
- Triggered schedule with active status creates Export via Export Engine (same generation pipeline as one-off)
- ExportRun created linking Schedule to Export
- Delivery job enqueued with email recipient and attachment
- First delivery attempt occurs within 5 minutes of ExportRun creation
- Failed delivery is retried after 1 min, then 5 min, then 15 min
- After 3 failed attempts, ExportSchedule status transitions to paused with paused_reason="auto_paused_after_delivery_failures"
- In-app notification created for schedule owner on auto-pause
- Audit events recorded for all state transitions (schedule_triggered, delivery_attempted, delivery_succeeded, delivery_failed, schedule_auto_paused)
- Restarting scheduler daemon does not cause duplicate exports or deliveries

## Phase 5: Schedule Management API and Feature Control

**Goal:** Deliver full schedule lifecycle management and workspace-level feature flagging.

**Scope:**
- Implement `POST /schedules` endpoint (create schedule, validate report access and feature flag)
- Implement `GET /schedules` endpoint (list schedules for current user or all schedules for admins)
- Implement `GET /schedules/{schedule_id}` endpoint (retrieve schedule detail)
- Implement `PATCH /schedules/{schedule_id}` endpoint (pause/resume with reason tracking)
- Implement `DELETE /schedules/{schedule_id}` endpoint (delete schedule and unregister from scheduler)
- Implement `GET /schedules/{schedule_id}/runs` endpoint (list ExportRun history with pagination)
- Implement `GET /workspace/features/scheduled_exports` endpoint (retrieve feature flag state)
- Implement `PATCH /workspace/features/scheduled_exports` endpoint (toggle feature, admin-only)
- Implement feature flag enforcement: when disabled, all export and schedule endpoints return 403; UI hides export features
- Implement schedule recalculation on pause/resume (next_scheduled_at updated based on recurrence)
- Implement audit logging for all schedule lifecycle events (schedule_created, schedule_paused, schedule_resumed, schedule_deleted, feature_toggled)
- Implement `GET /audit` endpoint with filtering by resource_type, resource_id, event_type, actor_id (admins can query all; users can query own events only)

**Acceptance Criteria:**
- `POST /schedules` creates ExportSchedule with correct recurrence and calculates next_scheduled_at
- `GET /schedules` returns user's own schedules (or all for admins)
- `PATCH /schedules/{schedule_id}` with action=pause updates status and paused_reason
- `PATCH /schedules/{schedule_id}` with action=resume recalculates next_scheduled_at and resets paused_reason
- `DELETE /schedules/{schedule_id}` removes schedule from database and scheduler
- `GET /schedules/{schedule_id}/runs` returns paginated list of ExportRun records with delivery status
- Toggling feature flag to disabled prevents new exports and schedules (API returns 403)
- Existing schedules remain in database when feature disabled but are skipped by scheduler
- Toggling feature flag to enabled resumes schedules based on their next_scheduled_at
- `GET /audit` returns filtered events with correct actor, resource, and event_type
- Non-admins can only query their own audit events
- All schedule state changes recorded in AuditEvent table
