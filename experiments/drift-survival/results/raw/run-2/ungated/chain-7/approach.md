# Technical Approach: Scheduled Report Exports

## Architecture Outline

The report export system consists of several key components:

1. **Export Service** — Handles one-off and scheduled export generation, format conversion (CSV/PDF), and file size validation. Generates exports asynchronously to avoid blocking the interactive UI.

2. **Schedule Manager** — Creates, updates, pauses, and resumes user-defined export schedules. Manages schedule state and configuration (cadence, delivery target, etc.).

3. **Delivery Engine** — Executes scheduled exports on their designated cadence, applies retry logic (up to 3 attempts), and manages schedule pause-on-failure behavior. Delivers exports via email.

4. **History & Audit System** — Records export runs (success/failure status, timestamp, delivery attempts) and maintains a 30-run sliding window per schedule. Logs all export events for audit compliance.

5. **Feature Flag & Admin Control** — Gates export UI visibility and scheduling capabilities. Provides admin panel to disable exports workspace-wide.

6. **Permission Boundary Filter** — Ensures exports include only rows the requesting user can view in the application. Leverages the existing permission model to filter report data at export time.

These components communicate through a pub/sub event bus for asynchronous work (delivery, retries) and synchronous APIs for schedule management and export initiation.

## Domain Model

### Core Entities

**Report**
- ID (inherited from existing reporting module)
- Name, definition, configuration
- Associated workspace

**Export** (one-off or scheduled instance)
- ID
- Report ID
- Requester User ID
- Format (CSV, PDF)
- Status (pending, completed, failed)
- File size (bytes)
- Generated file path/handle
- Created timestamp

**ExportSchedule**
- ID
- Report ID
- Owner User ID
- Cadence (daily, weekly; day of week if weekly)
- Delivery target (owner email)
- Status (active, paused)
- Created/Modified timestamps

**ExportRun** (history entry)
- ID
- Schedule ID
- Export ID (links to the generated Export)
- Execution timestamp
- Delivery status (success, failed, retried)
- Retry attempt count (0, 1, 2)
- Error message (if failed)

**ExportAuditLog**
- ID
- User ID
- Export ID or Schedule ID
- Action (created_export, scheduled_export, paused_schedule, resumed_schedule, admin_disabled, etc.)
- Timestamp
- Workspace ID

**WorkspaceExportSettings**
- Workspace ID
- Exports enabled (boolean, admin-controlled)
- Last modified timestamp

### Relationships

- Report → many Exports
- Report → many ExportSchedules
- ExportSchedule → many ExportRuns (limited to 30 most recent)
- ExportSchedule → many ExportAuditLogs
- User → many ExportSchedules (owned)
- Workspace → WorkspaceExportSettings

## Key Workflows

### Workflow 1: One-Off Export

1. User clicks "Export" on a report, selects format (CSV or PDF)
2. Export Service validates the report and checks if exports are enabled in the workspace
3. Export Service filters report rows by the requesting user's row-level permissions
4. Export Service generates the export file in the selected format
5. Export Service validates file size ≤ 50 MB; rejects with clear error if exceeded
6. Export is recorded as completed with file path; audit log entry created
7. File is returned to the user (download or preview)

### Workflow 2: Create Recurring Export Schedule

1. User navigates to schedule export UI (gated by feature flag)
2. User selects report, format, cadence (daily/weekly), and confirms target email (always their own email)
3. Schedule Manager validates the report exists and exports are enabled
4. ExportSchedule record is created in "active" status
5. Audit log entry recorded (scheduled_export)
6. First scheduled run is enqueued for the next scheduled time

### Workflow 3: Scheduled Export Execution & Delivery

1. Delivery Engine detects a schedule is due (based on cadence)
2. Delivery Engine calls Export Service to generate the export (same filtering by owner's permissions)
3. Export Service returns completed Export record
4. ExportRun record created with delivery status "pending"
5. Email delivery is attempted
6. On success: ExportRun status → "success"; next scheduled run enqueued
7. On failure: ExportRun status → "failed"; retry_attempt incremented
8. If retry_attempt < 3: retry scheduled for 1 hour later
9. If retry_attempt == 3 and still failed: ExportSchedule status → "paused"; audit log entry "auto_paused"
10. Audit log entry created for the export run

### Workflow 4: Schedule Pause/Resume

1. User clicks pause or resume on their schedule
2. Schedule Manager updates ExportSchedule status (active → paused or paused → active)
3. If resuming: next scheduled run is enqueued for the next cadence window
4. Audit log entry created (paused_schedule or resumed_schedule)

### Workflow 5: Admin Disables Exports Workspace-Wide

1. Workspace admin toggles "Disable Exports" in workspace settings
2. WorkspaceExportSettings.exports_enabled → false
3. Export UI hidden from all users
4. All pending deliveries are canceled; affected ExportRuns marked "failed" with reason "feature disabled"
5. All active schedules remain in database but are not executed while disabled
6. Audit log entry created (admin_disabled_exports)
7. When re-enabled: schedules resume on next cadence window

### Workflow 6: View Export History

1. User navigates to schedule details page
2. System retrieves the 30 most recent ExportRun records for that schedule
3. UI displays each run: timestamp, delivery status, retry count, error message (if failed)

## Contracts

### Export Service API

**generate_export(report_id, format, user_id, ignore_cache=False) → Export**
- Input: report ID, format (CSV or PDF), requesting user's ID, optional cache bypass flag
- Process: Filters report rows by user's row-level permissions; generates file; validates size ≤ 50 MB
- Output: Export record with file path/handle and metadata
- Errors: ReportNotFound, ExportsDisabled, PermissionDenied, FileSizeExceeded, GenerationFailed

**validate_export_enabled(workspace_id) → bool**
- Checks WorkspaceExportSettings; returns whether exports are enabled

### Schedule Manager API

**create_schedule(report_id, format, owner_user_id, cadence, cadence_params) → ExportSchedule**
- Input: report ID, format, owner user ID, cadence type (daily/weekly), cadence-specific params (day of week if weekly)
- Process: Validates report and export enabled; creates ExportSchedule record; creates audit log entry
- Output: ExportSchedule record
- Errors: ReportNotFound, ExportsDisabled, InvalidCadence

**pause_schedule(schedule_id, user_id) → ExportSchedule**
- Input: schedule ID, user ID (verifies ownership)
- Process: Updates status to paused; creates audit log entry
- Output: Updated ExportSchedule
- Errors: ScheduleNotFound, NotOwner

**resume_schedule(schedule_id, user_id) → ExportSchedule**
- Input: schedule ID, user ID (verifies ownership)
- Process: Updates status to active; enqueues next run; creates audit log entry
- Output: Updated ExportSchedule
- Errors: ScheduleNotFound, NotOwner

**get_schedule_history(schedule_id, user_id, limit=30) → [ExportRun]**
- Input: schedule ID, user ID (verifies ownership), optional limit
- Process: Retrieves up to the most recent ExportRuns for the schedule
- Output: Array of ExportRun records ordered by timestamp (newest first)
- Errors: ScheduleNotFound, NotOwner

### Delivery Engine API

**execute_scheduled_export(schedule_id) → ExportRun**
- Input: schedule ID
- Process: Generates export via Export Service; attempts email delivery; manages retry logic; updates ExportRun status and schedule pause behavior
- Output: ExportRun record with final delivery status
- Errors: ScheduleNotFound, ExportsDisabled, DeliveryFailed (may be recovered by retry)

**mark_schedule_paused_on_failure(schedule_id) → void**
- Input: schedule ID
- Process: Sets ExportSchedule status to paused; creates audit log entry
- Errors: ScheduleNotFound

### Admin API

**set_workspace_exports_enabled(workspace_id, enabled) → WorkspaceExportSettings**
- Input: workspace ID, boolean flag (requires admin privilege)
- Process: Updates WorkspaceExportSettings; cancels pending deliveries if disabling; creates audit log entry
- Output: Updated WorkspaceExportSettings
- Errors: Unauthorized, WorkspaceNotFound

### Audit Log API

**record_export_event(workspace_id, user_id, action, resource_id) → ExportAuditLog**
- Input: workspace ID, user ID, action type (string), associated export/schedule ID
- Process: Creates audit log entry with timestamp
- Output: ExportAuditLog record
- Errors: WorkspaceNotFound
