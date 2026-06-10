# Scheduled Report Exports – Phase Plan

## Phase 1: Export Engine & On-Demand Export

**Goal:** Deliver the core export generation capability with support for on-demand exports in CSV and PDF formats.

**Scope:**
- Implement the Export Engine service that reads report definitions, applies row-level access control, and streams data to CSV/PDF formats
- Build the Export entity and schema (including format, requestor, size, delivery status, immutable artifact archival)
- Implement streaming with 50 MB size limit and abort logic
- Create the on-demand export API endpoints: `POST /api/reports/:reportId/exports`, `GET /api/exports/:jobId`, `GET /api/exports/:jobId/download`
- Implement feature flag checking on all export endpoints (403 rejection when disabled)
- Build the basic job queue infrastructure for async export processing
- Implement ExportAuditLog table and write audit entries for export_completed events
- Create UI components for on-demand export triggers on report views

**Acceptance Criteria:**
- Users can trigger on-demand CSV and PDF exports from a report view
- Export requests are validated (user permission, feature flag, format validity)
- Job ID is returned immediately and client can poll for completion
- Export artifacts are successfully generated and stored, respecting the 50 MB limit
- Downloads are available with correct Content-Type headers (text/csv, application/pdf)
- Export events (initiated, completed, failed) are logged to audit table
- Feature flag disable/enable returns 503 and 403 errors respectively on API endpoints
- Large exports are rejected with appropriate error messages

---

## Phase 2: Schedule Engine & Scheduled Executions

**Goal:** Build the scheduling system that triggers recurring exports at defined cadences and implements schedule lifecycle management.

**Scope:**
- Create Schedule entity (owner, cadence, time-of-day, day-of-week, enabled/paused state, next/last execution tracking)
- Implement ScheduleRun entity (links Schedule to generated Export, tracks delivery status and retry count)
- Build the job scheduler that evaluates active schedules and enqueues due runs
- Implement schedule CRUD API endpoints: `POST /api/reports/:reportId/schedules`, `GET /api/schedules`, `PATCH /api/schedules/:scheduleId`, `DELETE /api/schedules/:scheduleId`
- Implement pause/resume logic that recalculates next execution time
- Implement schedule deletion logic that retains historical ScheduleRun records
- Write audit entries for schedule_created, schedule_paused, schedule_resumed, schedule_deleted events
- Build UI for schedule creation, management, and pause/resume controls
- Implement `GET /api/schedules/:scheduleId/runs?limit=30` endpoint for history visibility

**Acceptance Criteria:**
- Schedules can be created with daily/weekly cadences and specific times-of-day
- Schedules are validated (user permission, cadence/time format validity, feature flag)
- Scheduler correctly evaluates due schedules and enqueues ScheduleRun jobs
- ScheduleRun records are created and linked to generated Exports
- Schedule pause/resume changes the enabled state and recalculates nextRunAt
- Schedule deletion removes future runs but retains historical audit trail
- Users can view the last 30 runs of a schedule with delivery status and sizes
- Audit log captures all schedule lifecycle events

---

## Phase 3: Email Delivery & Scheduled Export Distribution

**Goal:** Deliver scheduled exports to users via email with retry logic and failure handling.

**Scope:**
- Build the email delivery interface that sends scheduled export artifacts (or download links) to recipients
- Implement retry logic with configurable retry count (initial design: 3 retries)
- Implement auto-pause on delivery failure: after 3 failed retries, schedule is paused and admin notification is sent
- Implement email transactional service integration (send artifacts or secure download links)
- Update ScheduleRun delivery status tracking (pending → delivered or failed)
- Write audit entries for export_delivered and delivery failures with error codes
- Implement delivery attempt history and error message recording on ScheduleRun
- Build admin dashboard to monitor schedule delivery health and failure alerts

**Acceptance Criteria:**
- Successful exports trigger email delivery to the schedule owner
- Email contains the export artifact or a secure download link
- Delivery status (pending/delivered/failed) is tracked on ScheduleRun
- Retry logic attempts up to 3 times on transient failures
- After 3 failed retries, the schedule is automatically paused
- Admin receives notification when a schedule is auto-paused due to delivery failure
- Audit log records delivery outcomes with error messages
- Delivery state persists across process restarts (durable job queue)
- Users can see delivery status and retry count in schedule history

---

## Phase 4: Admin Controls & Workspace-Level Feature Flag

**Goal:** Provide workspace administrators with ability to enable/disable exports globally and manage the feature lifecycle.

**Scope:**
- Implement the admin endpoint: `PATCH /api/admin/workspace/exports` with enabled/disabled state
- Implement feature flag enforcement across all export and schedule endpoints (return 503 when disabled)
- Implement schedule pause behavior on global disable: all active schedules are paused, not deleted
- Implement schedule resume behavior on global re-enable: schedules return to their previous enabled/paused state
- Hide all UI export options and controls when feature flag is disabled (frontend feature flag check)
- Write audit entries for export_feature_disabled and export_feature_enabled events (with admin user context)
- Build admin UI to toggle the feature flag and view the disable/enable history
- Track disabledAt timestamp and disabledBy user on feature state

**Acceptance Criteria:**
- Workspace admins can toggle the export feature flag via admin API
- When disabled, all export endpoints return 403; all schedule endpoints return 403
- When disabled, all active schedules are paused (saved state for resume)
- When re-enabled, schedules return to their previous enabled/paused state (not auto-resumed)
- No scheduled exports execute while the feature is disabled
- All feature toggle events are audited with admin user context
- Frontend hides export UI when feature is disabled (no API calls attempted)
- Disable/enable state is persistent and visible in admin settings

---

## Phase 5: Audit, Compliance & Observability

**Goal:** Ensure full audit trail, compliance queryability, and operational observability.

**Scope:**
- Finalize ExportAuditLog schema as a denormalized record capturing user, report, format, timestamp, size, delivery status, and metadata
- Implement audit log query API with filtering: `{ userId?, reportId?, scheduleId?, eventType?, timeRange?, limit, offset }`
- Enforce scope-based filtering: non-admin users can only query their own exports and schedules
- Build compliance report generator that exports audit logs for regulatory purposes (filtered by user/date range)
- Implement operational dashboards showing export volume, failure rates, delivery latency, and size distribution
- Add monitoring/alerting on export failures, delivery failures, and schedule health
- Document audit log retention policies and compliance requirements
- Build admin UI for querying and exporting audit logs

**Acceptance Criteria:**
- All export events (initiated, completed, failed, delivered) are captured in audit log
- All schedule events (created, paused, resumed, deleted) are captured in audit log
- All feature flag toggling events are captured with admin user context
- Audit log queries are scoped by user role (non-admins see only their own data)
- Historical ScheduleRun records are retained for audit trail even after schedule deletion
- Compliance reports can be generated filtering by date range and user
- Operational dashboards show real-time export metrics (volume, failures, sizes)
- Monitoring alerts trigger on repeated export failures or schedule health degradation
- Audit log is immutable and append-only for compliance requirements
