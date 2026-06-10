# Scheduled Report Exports — Phase Plan

## Phase 1: Foundation & One-Off Export

**Goal** — Establish the core export infrastructure and deliver one-off export capability with permission filtering and size limits.

**Scope**
- Implement the Export Engine service with synchronous CSV and PDF rendering
- Integrate row-level permission filtering (build ExportPermissionSnapshot at generation time)
- Enforce 50 MB file size limit
- Implement Feature Flag System gating the entire feature
- Create OneOffExport entity and transient storage
- Add export endpoints to the report UI (format selection)
- Implement Audit System to log one-off export events (write-once log)
- Add permission checks at the API boundary (using is_export_enabled_for_user)

**Acceptance Criteria**
- Users can generate CSV and PDF exports from the report UI
- Exported files contain only rows the requesting user is authorized to view
- Exports exceeding 50 MB are rejected with a user-facing error message
- Every export attempt (success or failure) is recorded in the audit log with user identity, report ID, format, file size, and status
- Feature flag controls whether export UI surfaces and endpoints are accessible
- One-off exports return the file directly to the user within the same request

## Phase 2: Scheduled Export Lifecycle & Storage

**Goal** — Implement the ScheduledExport entity and full user-facing lifecycle management (create, view, pause, resume, delete).

**Scope**
- Implement ScheduledExport entity with recurrence rules (daily and weekly configurations)
- Build recurrence calculation logic (next run time, timezone support)
- Implement Scheduler Service APIs for create, pause, resume, delete, list, and view run history
- Store ExportRun history (last 30 runs per schedule, with execution metadata)
- Add UI screens for:
  - Creating a new scheduled export (format and recurrence selection)
  - Viewing a schedule's metadata and next run time
  - Viewing ExportRun history (status, timestamp, file size, error details)
  - Pause and resume buttons
  - Delete confirmation
- Implement authorization checks (only schedule owner can modify or view their schedules)
- Record schedule creation in the audit log

**Acceptance Criteria**
- Users can create scheduled exports with daily or weekly recurrence
- Next run time is calculated correctly based on recurrence rule and current time
- Schedule owners can view all their active schedules with next run time
- Schedule owners can pause and resume schedules
- Schedule owners can delete schedules (soft-delete; past audit entries remain)
- ExportRun history is accessible and shows last 30 runs with status, timestamp, and file size
- Only the schedule owner can view or modify a schedule (authorization verified on all operations)
- Schedule creation events are logged in the audit log

## Phase 3: Background Execution & Delivery Pipeline

**Goal** — Implement the asynchronous scheduler background worker and email delivery pipeline with retry logic.

**Scope**
- Build Scheduler background worker:
  - Awakens at scheduled times for each active ScheduledExport
  - Invokes the export engine with the schedule owner's user context
  - Re-checks permissions at generation time (respects permission changes since schedule creation)
  - Enqueues generated exports for delivery
  - Handles failures (size limit exceeded or no remaining permissions)
- Implement Delivery Pipeline:
  - Accepts export runs from the scheduler
  - Enqueues emails for delivery to the schedule owner
  - Implements retry logic (up to 3 retries with exponential backoff)
  - Handles transient failure detection
  - On retry exhaustion, pauses the schedule and sends a final notification email
  - Marks ExportRun as failed after all retries exhausted
- Record all execution events in ExportRun history
- Update schedule next run time after execution completes
- Record all execution events in the audit log (scheduled export runs)

**Acceptance Criteria**
- Background worker triggers on schedule (verified via execution logs)
- Export generation uses the schedule owner's current permissions
- Files exceeding 50 MB are rejected, schedule is paused, and owner is notified
- Exports where the owner no longer has permission fail gracefully with clear error messaging
- All delivery attempts are logged and retried automatically (up to 3 times)
- On retry exhaustion, the schedule is paused and the owner receives a final notification email
- Successful deliveries are marked in ExportRun history
- Next scheduled run time is correctly recalculated after each execution
- All scheduled export runs (success and failure) are recorded in the audit log

## Phase 4: Permission Re-Check & Audit Completeness

**Goal** — Ensure all export operations enforce current permissions and all audit events capture sufficient context for compliance and troubleshooting.

**Scope**
- Implement complete permission re-check for scheduled exports at generation time:
  - Fetch current row-level permissions for the schedule owner at execution time
  - Filter export output based on current permissions
  - Handle permission revocation edge cases (empty exports, no access remaining)
- Enhance Audit System to capture all relevant context:
  - User ID, workspace ID, timestamp, export type, report ID, format, file size, status, error codes
  - Export-specific metadata (one-off vs scheduled, schedule ID if applicable)
- Add admin audit log viewing/querying capability (compliance and troubleshooting)
- Verify all failure paths are logged with specific error codes (permission denied, file too large, report not found, etc.)

**Acceptance Criteria**
- Permission changes between schedule creation and execution are reflected in the exported file (current permissions used, not snapshot)
- If a schedule owner loses all access to a report, the next run fails with a clear error (Unauthorized or equivalent)
- All export events (one-off and scheduled, success and failure) are in the audit log with complete context
- Specific error codes (PermissionDenied, FileTooLarge, ReportNotFound, etc.) are captured in audit entries
- Audit log entries include workspace ID, user ID, timestamp, and export metadata for post-hoc analysis
- Admins can query the audit log to review export activity by user, report, date, or status

## Phase 5: Feature Flag Control & Admin Configuration

**Goal** — Deliver workspace-level feature flag control and admin configuration capabilities.

**Scope**
- Implement Feature Flag API (is_export_enabled per workspace)
- Build workspace admin UI to toggle export feature on/off
- Ensure disabling exports stops:
  - UI export surfaces (hide "Export" buttons/menus)
  - API export endpoints (return 403 or equivalent)
  - Background scheduler (no new scheduled exports triggered)
- Document feature flag behavior and admin workflow
- Add metrics/observability around export usage (volume, sizes, formats, success/failure rates)

**Acceptance Criteria**
- Workspace admins can enable/disable exports via workspace settings
- When disabled, all export UI is hidden and all export endpoints reject requests
- Background scheduled export runs do not trigger when the feature is disabled
- Feature flag status is checked on all export operations (one-off and scheduled)
- Audit log captures whether each export succeeded or was blocked by feature flag
- Export usage metrics are observable (count, size distribution, format breakdown, success rate)
