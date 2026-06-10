# Scheduled Report Exports: Phase Plan

## Phase 1: Core Export Engine & Data Model

**Goal:** Establish the foundation for all export functionality with the export engine, data model, and basic on-demand export support.

**Scope:**
- Implement domain entities: `Export`, `ScheduledExport`, `ExportDeliveryAttempt`
- Create database schema and migrations for all three entities
- Implement `Export Engine` with `generate_export()` and `get_export()` methods
- Add row-level permission filtering in export generation
- Implement 50 MB file size validation and rejection handling
- Create basic storage mechanism for generated export files
- Add on-demand export endpoint that calls the Export Engine
- Implement feature flag controller with `is_export_enabled()`, `enable_exports()`, `disable_exports()`

**Acceptance Criteria:**
- Database schema is created and migrations run successfully
- On-demand export can be generated synchronously with permission filtering applied
- Files ≤ 50 MB are stored and files > 50 MB are rejected with appropriate error
- Feature flag gates export API access; disabled flag prevents export generation
- Export object can be retrieved with status and file metadata
- All export entities can be persisted and retrieved from database

---

## Phase 2: Audit Logger & Feature Flag Integration

**Goal:** Add observability and governance to export operations with comprehensive audit logging and feature flag enforcement.

**Scope:**
- Implement `Audit Logger` with `log_export_event()` method
- Define audit event types: EXPORT_REQUESTED, EXPORT_GENERATED, EXPORT_REJECTED, EXPORT_DELIVERED, EXPORT_DELIVERY_FAILED, SCHEDULED_EXPORT_*
- Integrate audit logging into on-demand export workflow
- Add audit logging to feature flag controller operations
- Create audit query/retrieval capability for compliance
- Wire feature flag checks into all export-related UI and API endpoints

**Acceptance Criteria:**
- Every export event is logged with event type, user ID, report ID, format, result, and timestamp
- On-demand export flow generates audit events for requested, generated/rejected, and delivered states
- Feature flag disable/enable operations are audited
- Audit logs can be retrieved and filtered by date range, user, and report
- API endpoints return 403 when feature flag is disabled
- UI hides export controls when feature flag is disabled

---

## Phase 3: Scheduled Export Manager & Lifecycle

**Goal:** Implement the scheduling infrastructure to create, pause, and resume recurring export schedules.

**Scope:**
- Implement `Scheduled Export Manager` with CRUD operations
- Implement `create_scheduled_export()` with frequency calculation (DAILY, WEEKLY)
- Implement `pause_scheduled_export()` and `resume_scheduled_export()` with ownership validation
- Implement `get_scheduled_export()` and `list_scheduled_exports()`
- Add background scheduler trigger mechanism for checking due schedules
- Create UI for "Schedule Exports" interface (report selection, frequency, format)
- Create UI for schedule detail page with pause/resume controls
- Integrate audit logging for schedule creation, pause, and resume events

**Acceptance Criteria:**
- ScheduledExport can be created with calculated next_run_at based on frequency
- Only schedule owner can pause or resume their schedule
- Paused schedule has is_paused=true and paused_at timestamp set
- Resume recalculates next_run_at from current time
- Background scheduler identifies schedules due for execution (next_run_at ≤ now)
- Schedule list displays active and paused schedules with next run time
- Pause/resume events are audited with user ID and timestamp

---

## Phase 4: Delivery Service with Retry Logic

**Goal:** Implement email delivery with robust retry handling and delivery history tracking.

**Scope:**
- Implement `Delivery Service` with `queue_export_for_delivery()` and `get_delivery_history()` methods
- Implement email queueing and asynchronous delivery processing
- Implement retry logic: 3 attempts with configurable delays (e.g., 1 hour between attempts)
- Create `ExportDeliveryAttempt` records for each delivery attempt
- Auto-pause schedule after 3 failed delivery attempts
- Implement delivery history retrieval with 30-day default retention window
- Create delivery history UI on scheduled export detail page
- Integrate audit logging for delivery success/failure and auto-pause events

**Acceptance Criteria:**
- Exports are queued and processed asynchronously via Delivery Service
- Email delivery attempts are recorded with timestamp and status
- Failed delivery automatically schedules retry (up to 3 total attempts)
- After 3 failed attempts, schedule is auto-paused and paused_at is set
- Delivery history displays all attempts with timestamps and final status
- Delivery history is queryable by date range (default 30 days)
- Auto-pause event is audited with reason "3 failed delivery attempts"

---

## Phase 5: Scheduled Export Execution & Integration

**Goal:** Wire scheduled exports into the background scheduler and complete the end-to-end workflow.

**Scope:**
- Integrate scheduled export trigger into background scheduler
- Implement scheduled export execution workflow: retrieve report, apply permissions, generate export
- Handle rejection during scheduled execution: log and pause schedule (not delivery attempts)
- For successful generation, queue export for delivery via Delivery Service
- Update ScheduledExport.next_run_at after execution
- Wire all components together: Export Engine → Delivery Service → Audit Logger
- Add handling for size-based rejection (pause schedule if export > 50 MB)
- Create dashboard/monitoring view showing active schedules, next runs, and recent delivery history

**Acceptance Criteria:**
- Background scheduler successfully triggers scheduled export execution at next_run_at
- Scheduled export execution generates export with permission filtering
- If generated export > 50 MB, schedule is paused and rejection is logged
- If generated export ≤ 50 MB, export is created, queued for delivery, and next_run_at is updated
- Export.is_scheduled=true for exports generated from schedules
- Full audit trail exists from creation through execution to delivery attempt
- Dashboard displays list of active schedules with next run times and recent delivery statuses
- All integration tests pass for end-to-end scheduled export flow
