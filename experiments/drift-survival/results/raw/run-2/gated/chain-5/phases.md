# Scheduled Report Exports — Phase Plan

## Phase 1: One-Off Export Foundation

**Goal**
Deliver immediate, on-demand export capability for individual users with async generation and signed download URLs.

**Scope**
- Implement Export Service (stateless `generateExport` function)
  - Report definition fetching
  - Row-level permission filtering
  - CSV artifact generation
  - PDF artifact generation
  - Artifact size validation (50 MB limit)
- Create One-Off Export Request entity and data model
- Implement async export queue and background worker
- Build one-off export API (`POST /api/reports/{reportId}/export`, `GET /api/export-requests/{requestId}`)
- Add signed URL generation for artifact downloads
- Implement basic Audit Logger for one-off export events

**Acceptance Criteria**
- User can request a CSV export from a report and receive a request ID immediately
- Background worker generates the CSV artifact respecting row-level permissions
- User can poll the request status and retrieve a signed download URL once ready
- Exports larger than 50 MB are rejected with a clear error message
- Audit log records all one-off export creation events with user ID and timestamp
- One-off export API returns appropriate HTTP error codes (400, 403, 404)

---

## Phase 2: Feature Flag & Admin Control

**Goal**
Implement workspace-level feature control so admins can enable/disable export functionality across the entire workspace.

**Scope**
- Add Feature Flag Service (centralized configuration for export availability)
- Implement Feature Flag / Configuration API (`GET /api/export-config`, `PATCH /api/export-config`)
- Add admin-only access control to disable endpoint
- Hide export buttons in UI when feature is disabled
- Return HTTP 403 Forbidden from export APIs when disabled
- Update Audit Logger to record enable/disable events with admin user ID
- Extend one-off export flow to check feature flag before accepting requests

**Acceptance Criteria**
- Admin can toggle export feature enabled/disabled via API
- When disabled, export UI controls are hidden
- When disabled, export API endpoints return 403 Forbidden with explanatory message
- Feature flag state is persisted and survives service restarts
- Audit log records all feature flag changes with timestamp and admin ID
- One-off exports are rejected with 403 when feature is disabled

---

## Phase 3: Scheduled Exports & Background Scheduler

**Goal**
Deliver recurring export capability with schedule management, automatic triggering, and history tracking.

**Scope**
- Implement Export Schedule entity (ownership, format, frequency, pause state)
- Create Export Run entity to represent schedule execution instances
- Implement Schedule Manager for schedule lifecycle (create, pause/resume, delete)
- Build scheduler component that triggers runs at `next_run_at` times
- Implement scheduled export generation flow (reusing Export Service from Phase 1)
- Add schedule history tracking (last 30 runs per schedule)
- Build Schedule Management API (`POST /api/schedules`, `GET /api/schedules`, `PATCH /api/schedules/{scheduleId}/pause`, `PATCH /api/schedules/{scheduleId}/resume`, `DELETE /api/schedules/{scheduleId}`, `GET /api/schedules/{scheduleId}/history`)
- Extend Audit Logger to record schedule creation, pause/resume, and deletion events
- Add feature flag check to schedule creation

**Acceptance Criteria**
- User can create a DAILY or WEEKLY export schedule with CSV or PDF format
- Schedule is owned by the creating user and immediately registered with the scheduler
- At `next_run_at` time, scheduler automatically creates an Export Run and enqueues generation
- Background worker generates artifact for scheduled run, applying row-level permissions to schedule owner
- Schedule owner can view the last 30 runs in history with status and metadata
- Schedule owner can pause a schedule (cancels pending runs, sets `is_paused` = true)
- Schedule owner can resume a paused schedule (recalculates `next_run_at`, re-registers with scheduler)
- Schedule owner can delete a schedule (removes schedule and pending runs, records audit event)
- Audit log records all schedule lifecycle events with owner ID and timestamp
- Schedule creation is rejected when export feature is disabled (403 Forbidden)

---

## Phase 4: Delivery Engine & Email Transport

**Goal**
Implement reliable email delivery of scheduled exports with automatic retry logic and grace-period auto-pause.

**Scope**
- Implement Delivery Engine with email transport
- Add email configuration and recipient validation
- Implement retry logic (up to 3 total attempts per run)
- Add delay/backoff strategy between retry attempts
- Auto-pause schedule after 3 failed delivery attempts (sets `is_paused` = true)
- Update Export Run entity to track delivery attempts, last error, and delivered timestamp
- Extend scheduled export flow to transition runs through GENERATING → GENERATED → DELIVERING → DELIVERED states
- Add error message storage in `last_delivery_error` field
- Update Audit Logger to record delivery attempts, successes, and auto-pause events
- Extend Audit Log API to filter export-related events
- Update Storage Layer to hold generated artifacts temporarily

**Acceptance Criteria**
- Scheduled export generation completes and marks run GENERATED
- Delivery engine attempts to email the artifact (or a download link) to schedule owner
- On success, run is marked DELIVERED with timestamp
- On delivery failure, run records error message and `delivery_attempts` increments
- If `delivery_attempts` < 3, retry is automatically scheduled with backoff
- If `delivery_attempts` == 3, run is marked FAILED, schedule is auto-paused, audit event records auto-pause reason
- User can view delivery history including status, attempt count, and error messages for each run
- User can download a previously generated artifact directly from run history
- Audit log records delivery success, all failure attempts, and auto-pause events with user ID and timestamp

---

## Phase 5: Storage Optimization & Artifact Management

**Goal**
Finalize artifact storage, lifecycle management, and audit completeness for compliance and operational health.

**Scope**
- Implement Storage Layer for temporary artifact persistence
- Define artifact lifecycle (generation → delivery → expiration)
- Add artifact expiration and cleanup for old runs (keep last 30 per schedule)
- Implement artifact size reporting in run history
- Complete Audit Log API with filtering (`GET /api/audit-log?resource=exports&limit=100&offset=0`)
- Add audit event filtering (users see own events, admins see all)
- Add event action enums (EXPORT_ONE_OFF_CREATED, EXPORT_SCHEDULE_CREATED, EXPORT_SCHEDULE_PAUSED, EXPORT_SCHEDULE_RESUMED, EXPORT_RUN_DELIVERED, EXPORT_RUN_FAILED, EXPORT_FEATURE_DISABLED, EXPORT_SCHEDULE_AUTO_PAUSED)
- Implement artifact download API with proper security (`GET /api/schedules/{scheduleId}/history/{runId}/artifact`)
- Add Content-Type headers for CSV and PDF
- Implement compliance documentation for audit trail

**Acceptance Criteria**
- Generated artifacts are persisted in storage and remain available for the last 30 runs per schedule
- Artifacts older than the 30-run limit are automatically cleaned up
- Artifact size is accurately reported in run history and limited to 50 MB per generation
- Audit log API returns all export events with pagination (limit/offset)
- Users can only view audit events for exports they own; admins can view all
- Schedule owner can download any artifact from their schedule's run history with proper authentication
- Downloads return appropriate Content-Type (text/csv or application/pdf)
- All export operations (creation, delivery, failure, auto-pause, feature flag changes) are recorded in audit log
- Audit trail supports compliance requirements with user ID, timestamp, and action type for all events
