# Phase Plan: Scheduled Report Exports

## Phase 1: Core Domain Model & Export Service

**Goal:** Establish the foundational data layer and implement the Export Service with one-off export capability.

**Scope:**
- Define and migrate domain model entities: Report, Export, ExportSchedule, ExportRun, ExportAuditLog, WorkspaceExportSettings
- Implement Export Service with `generate_export(report_id, format, user_id, ignore_cache=False) → Export`
- Implement row-level permission filtering in export generation
- Implement file size validation (≤ 50 MB)
- Implement `validate_export_enabled(workspace_id) → bool` API
- Create audit log recording infrastructure
- Implement one-off export workflow (Workflow 1) end-to-end

**Acceptance Criteria:**
- Domain model is defined in code and database migrations are complete
- Users can generate one-off CSV and PDF exports from reports
- Exports are filtered by requesting user's row-level permissions
- Exports over 50 MB are rejected with clear error message
- All export events are logged to ExportAuditLog with correct action types
- One-off export workflow passes end-to-end testing

---

## Phase 2: Schedule Manager & Recurring Schedule Creation

**Goal:** Enable users to create and manage recurring export schedules with proper lifecycle management.

**Scope:**
- Implement Schedule Manager with schedule CRUD operations
- Implement `create_schedule(report_id, format, owner_user_id, cadence, cadence_params) → ExportSchedule`
- Implement `pause_schedule(schedule_id, user_id) → ExportSchedule`
- Implement `resume_schedule(schedule_id, user_id) → ExportSchedule`
- Implement `get_schedule_history(schedule_id, user_id, limit=30) → [ExportRun]`
- Implement ownership verification (users can only manage their own schedules)
- Create feature flag gating schedule UI visibility
- Implement Workflow 2 (Create Recurring Export Schedule) end-to-end
- Implement Workflow 4 (Schedule Pause/Resume) end-to-end

**Acceptance Criteria:**
- Users can create daily and weekly export schedules
- Cadence validation rejects invalid configurations
- Users can only access and modify their own schedules
- Export creation audit logs are recorded for all schedule operations
- Schedule history retrieves up to 30 most recent ExportRun records
- Feature flag properly gates the schedule creation UI
- Pause/resume operations correctly update schedule status and enqueue next runs

---

## Phase 3: Delivery Engine & Scheduled Execution

**Goal:** Implement automated scheduled export generation and delivery with retry logic and failure handling.

**Scope:**
- Implement Delivery Engine scheduler to detect schedules due for execution
- Implement `execute_scheduled_export(schedule_id) → ExportRun` with:
  - Export generation via Export Service (using schedule owner's permissions)
  - Email delivery attempt
  - ExportRun record creation with delivery status
  - Retry logic (up to 3 attempts with 1-hour delay between attempts)
  - Pause-on-failure behavior (auto-pause after 3 failed delivery attempts)
- Implement `mark_schedule_paused_on_failure(schedule_id) → void`
- Implement pub/sub event bus or job queue for asynchronous delivery and retries
- Implement Workflow 3 (Scheduled Export Execution & Delivery) end-to-end

**Acceptance Criteria:**
- Scheduled exports execute on the correct cadence (daily/weekly)
- Successful exports are delivered via email and ExportRun records success status
- Failed exports are retried up to 3 times with 1-hour intervals
- After 3 failed delivery attempts, schedules are automatically paused
- Auto-pause actions generate audit log entries
- ExportRun records correctly track delivery status and retry attempts
- Delivery engine handles edge cases (missing report, disabled exports during execution)
- Scheduled execution workflow passes end-to-end testing with simulated cadence windows

---

## Phase 4: Admin Controls & Workspace-Wide Feature Toggle

**Goal:** Provide workspace administrators with centralized control over the export feature and compliance capabilities.

**Scope:**
- Implement WorkspaceExportSettings table with `exports_enabled` flag
- Implement `set_workspace_exports_enabled(workspace_id, enabled) → WorkspaceExportSettings` admin API
- Implement cancellation logic for pending deliveries when exports are disabled
- Implement UI state management to hide export features when disabled workspace-wide
- Update Export Service and Schedule Manager to check workspace enablement
- Create admin panel UI for toggling exports per workspace
- Implement Workflow 5 (Admin Disables Exports Workspace-Wide) end-to-end
- Implement proper error handling for exports disabled state

**Acceptance Criteria:**
- Admin can toggle exports enabled/disabled per workspace
- When disabled, all export UI is hidden from all users
- When disabled, pending ExportRun deliveries are canceled and marked with "feature disabled" reason
- When disabled, active schedules remain in database but do not execute
- When re-enabled, schedules resume execution on next cadence window
- Admin audit log entries record all enable/disable actions with timestamp and admin user ID
- Export Service returns ExportsDisabled error when workspace has exports disabled
- Users attempting to create schedules while disabled receive appropriate error messages

---

## Phase 5: History, Audit & Observability

**Goal:** Provide complete visibility into export system operations and user audit trail for compliance.

**Scope:**
- Implement Workflow 6 (View Export History) UI page with pagination and filtering
- Implement export history retrieval with proper error handling and authorization
- Create comprehensive audit log query APIs (by user, schedule, workspace, action type, date range)
- Implement audit log retention/archival strategy (if not already specified)
- Add monitoring and observability: export generation latency, delivery success rate, failure modes
- Add admin dashboard with:
  - Export usage metrics (total exports, scheduled exports, failed exports)
  - Recent audit log entries
  - List of paused schedules and reasons for pause
  - Delivery failure patterns and error trends
- Implement proper logging throughout system for debugging and support

**Acceptance Criteria:**
- Users can view up to 30 most recent export runs for each schedule
- Export history displays timestamp, delivery status, retry count, and error messages
- Audit logs can be queried by user, resource (schedule/export), action type, workspace, and date range
- Admin dashboard displays accurate metrics and recent activity
- All system operations are properly logged for compliance audit purposes
- Export failures and retries can be debugged via audit log entries
- System metrics are available for monitoring export system health
