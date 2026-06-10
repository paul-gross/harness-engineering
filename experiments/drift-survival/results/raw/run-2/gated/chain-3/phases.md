# Scheduled Report Exports — Phase Plan

## Phase 1: Foundation & Core Domain Models

**Goal:** Establish the data model and core export infrastructure for one-off exports.

**Scope:**
- Define and implement `Export` domain model (UUID, report_id, format, created_by, created_at, status, file_size_bytes, error_message)
- Implement `AuditLogEntry` domain model for compliance tracking
- Create database migrations for both tables
- Implement Export Service with permission validation and file size constraint enforcement (≤ 50 MB)
- Create POST `/reports/{report_id}/exports` endpoint (CSV or PDF)
- Create GET `/exports/{export_id}` endpoint for status polling
- Wire Audit Logger to record one-off export events (export_requested, export_generated, export_failed)

**Acceptance criteria:**
- One-off exports can be requested and generated in CSV and PDF formats
- Row-level permissions are respected during export generation
- Files exceeding 50 MB trigger a 413 error with user-facing message
- All export events are logged to AuditLogEntry
- Export status can be polled via GET endpoint
- Audit logs can be queried by resource_id and event_type

---

## Phase 2: Scheduled Export Model & Scheduling Engine

**Goal:** Implement the recurring export definition and background scheduling system.

**Scope:**
- Define and implement `ScheduledExport` domain model (owner_id, recurrence, scheduled_for, is_paused, paused_at, paused_reason, created_at, updated_at)
- Define and implement `ExportRun` domain model for tracking individual scheduled executions (run_at, completed_at, status, delivery_attempts, last_delivery_error)
- Create database migrations
- Implement Scheduling Engine that detects due scheduled exports and initiates execution
- Create POST `/reports/{report_id}/scheduled-exports` endpoint
- Create GET `/scheduled-exports/{scheduled_export_id}` endpoint
- Implement pause/resume logic in ScheduledExport (PATCH endpoints)
- Wire Audit Logger to record scheduled export lifecycle events (created, paused, resumed)

**Acceptance criteria:**
- Scheduled exports can be created with daily or weekly recurrence
- Scheduling Engine successfully detects and triggers due scheduled exports
- Pause operation prevents future runs and logs audit event
- Resume operation recalculates next run time and logs audit event
- Scheduled export details can be fetched
- Audit logs capture all scheduled export lifecycle events

---

## Phase 3: Delivery Service & Retry Logic

**Goal:** Deliver generated scheduled exports via email with automatic retry and failure handling.

**Scope:**
- Implement Delivery Service with SMTP/email integration
- Implement retry logic (up to 3 total delivery attempts)
- Auto-pause ScheduledExport after 3 failed delivery attempts with pause_reason = "automatic_pause_after_delivery_failures"
- Update ExportRun status to track delivery attempts and failures (delivery_pending, delivered, failed)
- Wire Delivery Service into scheduled export execution workflow
- Wire Audit Logger to record delivery lifecycle events (delivery_succeeded, delivery_failed)

**Acceptance criteria:**
- Scheduled exports are sent via email to schedule owner on successful generation
- Failed delivery attempts trigger automatic retries up to 3 times
- After 3 failed attempts, ScheduledExport is automatically paused
- Pause reason is captured and auditable
- ExportRun tracks delivery_attempts and last_delivery_error
- Audit logs capture all delivery outcomes

---

## Phase 4: History & Export Visibility

**Goal:** Provide users with queryable execution history and audit trails.

**Scope:**
- Implement `ExportHistory` view (or query interface) returning the 30 most recent ExportRun records per ScheduledExport
- Create GET `/scheduled-exports/{scheduled_export_id}/history` endpoint with optional `?limit` parameter
- Implement permission checks to restrict history access to schedule owner and workspace admins
- Create GET `/audit-logs` endpoint with filtering by resource_type, resource_id, event_type, limit, and offset
- Implement permission checks for audit log access (workspace admin only)

**Acceptance criteria:**
- Users can query the 30 most recent execution runs for a scheduled export they own
- History includes run_at, completed_at, status, file_size_bytes, delivery_attempts, last_delivery_error
- Audit logs can be queried by resource_type and resource_id with pagination
- Only schedule owner and admins can access history for a scheduled export
- Only admins can access audit logs
- Queries return correct filtering and ordering (most recent first)

---

## Phase 5: Feature Flag & Admin Controls

**Goal:** Gate the entire feature and provide workspace-level controls.

**Scope:**
- Implement Feature Flag Controller with workspace-level `exports.enabled` flag (defaults to true)
- Implement UI rendering logic: hide export buttons when flag is disabled
- Implement API enforcement: all export endpoints return 403 when disabled
- Create PATCH `/workspace/settings/exports-enabled` admin endpoint
- Wire Audit Logger to record admin feature flag changes
- Optional: implement DELETE `/scheduled-exports/{scheduled_export_id}` endpoint for cleanup (with audit logging)

**Acceptance criteria:**
- When exports.enabled is false, all export UI elements are hidden
- When exports.enabled is false, all export API endpoints return 403 with message "Export functionality is disabled"
- Admins can toggle the feature flag via workspace settings endpoint
- Admin feature flag changes are logged to audit trail
- One-off exports, scheduled exports, and all scheduled execution is blocked when flag is disabled
