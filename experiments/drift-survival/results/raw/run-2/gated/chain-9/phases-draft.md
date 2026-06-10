# Scheduled Report Exports — Phase Plan

## Phase 1: Core Data Model and One-Off Export Foundation

**Goal:** Establish the persistence layer and implement basic one-off export functionality for CSV and PDF formats.

**Scope:**
- Create database schema for `Export`, `ExportConfig`, and `AuditLog` entities
- Implement the Export Generation Service with format conversion (CSV/PDF) and size validation (50 MB limit)
- Build the one-off export workflow: validate permissions, generate export, record audit events
- Implement workspace-level feature flag (ExportConfig) and validation at request time
- Add permission enforcement: row-level access control filtering during data fetch
- Create API endpoint(s) for initiating one-off exports
- Implement audit logging for export_requested and export_completed/export_failed events

**Acceptance criteria:**
- A user can request a one-off export of a report in CSV or PDF format
- Export generation respects user's row-level permissions (exported data matches UI visibility)
- Exports exceeding 50 MB are rejected with appropriate error message
- Feature flag gates all export requests; disabled exports return clear rejection message
- All export operations (success/failure) are logged in AuditLog
- Audit log can be queried to verify export events are recorded with user_id, report_id, format, and outcome
- File URL is returned on success and is downloadable within a reasonable time window

---

## Phase 2: Scheduled Export Configuration and Lifecycle

**Goal:** Enable users to create and manage recurring export schedules with pause/resume capability.

**Scope:**
- Create database schema for `ScheduledExport` and `ExportRun` entities
- Build scheduled export creation workflow: validate permissions, create ScheduledExport record, record audit event
- Implement schedule pause/resume functionality with UI controls and audit events
- Add persistence and state management for `paused` and `last_run_at` fields
- Build schedule detail view with 30-day execution history (via ExportRun table)
- Implement admin disable exports workflow (sets ExportConfig `exports_enabled = false`)
- Create admin control API endpoints: GET/PUT /workspace/exports/config

**Acceptance criteria:**
- A user can create a scheduled export with daily or weekly recurrence
- Schedule creation validates feature flag and user permissions
- Users can pause and resume their own schedules
- Paused schedules do not execute
- 30-day execution history is visible on schedule detail page with status and error messages
- Admins can disable/enable exports globally via workspace settings
- Schedule pause/resume/creation/admin-disable events are logged in AuditLog
- All schedule operations are audit-logged with user_id, scheduled_export_id, and event type

---

## Phase 3: Scheduler Service and Asynchronous Execution

**Goal:** Implement the time-based trigger system that detects due schedules and enqueues export generation jobs.

**Scope:**
- Build Scheduler Service that polls or subscribes to time-based triggers
- Implement recurrence logic: daily (every 24h) and weekly (every 7 days)
- Check `paused` flag before triggering execution; skip paused schedules
- Prevent duplicate concurrent runs for the same schedule within an interval
- On trigger: enqueue export generation job, create ExportRun record with `scheduled_for` timestamp
- Implement asynchronous job queuing (non-blocking)
- Integrate scheduler with export generation from Phase 1

**Acceptance criteria:**
- Scheduler correctly identifies schedules due for execution based on recurrence rule
- A scheduled export with daily recurrence runs every 24 hours (or on next scheduler check)
- A scheduled export with weekly recurrence runs every 7 days from last_run_at or creation
- Paused schedules are never triggered
- No duplicate runs occur for the same schedule within the same interval
- ExportRun records are created with correct `scheduled_for` and `executed_at` timestamps
- Export generation executes asynchronously without blocking the scheduler
- last_run_at is updated on each successful execution

---

## Phase 4: Delivery Service and Retry Logic

**Goal:** Deliver generated exports to recipients via email with intelligent retry and failure handling.

**Scope:**
- Build Delivery Service that consumes the export queue
- Determine recipient: owner's email for scheduled exports, configured email for one-off exports
- Prepare email with export attachment and send via SMTP
- Implement retry logic: up to 3 attempts with exponential backoff
- On success: mark Export `delivered`, update ExportRun status, record audit event
- On 3rd failure: pause the ScheduledExport, notify owner/admin, record audit event
- Track delivery attempts in ExportRun with error detail and retry_count
- Implement fallback notification for delivery failures

**Acceptance criteria:**
- An export ready for delivery is picked up by the delivery service
- Email is sent successfully with attachment to correct recipient
- On delivery success, Export status transitions to `delivered` and audit event is recorded
- On delivery failure, retry count increments and delivery is rescheduled with backoff
- After 3 failed delivery attempts, the ScheduledExport is auto-paused
- Owner and admins are notified when a schedule is paused due to delivery failure
- All delivery attempts (success/failure/retry) are logged in ExportRun
- ExportRun tracks retry_count and error_detail (SMTP error, etc.)

---

## Phase 5: Admin Visibility and Audit Reporting

**Goal:** Provide comprehensive audit trails and admin dashboards for export activity and compliance oversight.

**Scope:**
- Build admin audit log view: paginated query of AuditLog filtered by export events
- Implement admin export controls dashboard with global disable toggle
- Surface export event metrics: total exports, scheduled exports count, delivery failures, common error patterns
- Add permissions layer: only admins can view/modify ExportConfig and audit log
- Users can view only their own export and schedule history
- Implement audit event filtering and searching by date range, user, report, status
- Add workspace compliance report: exports disabled periods, failure patterns, bulk export activity

**Acceptance criteria:**
- Admin can access /workspace/exports/config to view and toggle exports_enabled flag
- Admin can access /workspace/exports/audit to view paginated audit log
- Audit log filters by event_type (export_requested, export_completed, export_failed, schedule_created, schedule_paused, etc.)
- Users can see only their own export and schedule history
- Non-admins cannot access workspace-level ExportConfig or audit log endpoints
- Audit log entries include user_id, report_id, workspace_id, timestamp, and outcome
- Admin dashboard surfaces actionable metrics: recent failures, paused schedules, disabled periods
- All phase 1-4 audit events are queryable and correctly filtered by permission level
