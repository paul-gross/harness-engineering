# Scheduled Report Exports — Phase Plan

## Phase 1: Foundation & One-Off Exports

**Goal**
Establish the core export infrastructure and enable users to generate one-off CSV/PDF exports with permission validation and size constraints.

**Scope**
- Implement Export Request entity and transient state machine (pending → generating → completed | failed)
- Build Export Generation Engine with format handling (CSV/PDF) and row-level permission filtering
- Implement size validation (50 MB threshold check before generation)
- Add feature flag (off by default) controlling export initiation
- Build export download UI with permission re-check at download time
- Implement audit logging for: export_initiated, export_completed, export_failed
- Add workspace-level ExportFeatureConfig with admin disable/enable capability

**Acceptance Criteria**
- User can initiate CSV export from report UI; system checks feature flag and rejects if disabled
- System applies row-level permission filter to report rows before size calculation
- Export rejects with error if filtered dataset exceeds 50 MB
- Successfully generated export can be downloaded from UI with permission re-check
- Feature flag off prevents all export initiation attempts
- Admin workspace setting can disable export feature globally
- Audit log contains all export_initiated, export_completed, and export_failed events with timestamps

---

## Phase 2: Schedule Management

**Goal**
Enable users to create and manage recurring export schedules with pause/resume capability and state persistence.

**Scope**
- Implement Export Schedule entity with DAILY/WEEKLY frequency configuration
- Build Schedule Management Service with create, list, pause, resume operations
- Implement nextRunTime calculation logic for frequency-based scheduling
- Add authorization checks (schedule owner validation)
- Extend audit logging for: schedule_created, schedule_paused, schedule_resumed
- Build UI for schedule creation dialog and schedule management (view, pause, resume)

**Acceptance Criteria**
- User can create export schedule for a report specifying format (CSV/PDF) and frequency (DAILY/WEEKLY)
- Feature flag and workspace config are checked at schedule creation; creation rejected if disabled
- nextRunTime is correctly calculated based on frequency
- User can list all schedules they own
- User can pause a schedule they own; paused schedules do not execute but pending jobs can complete
- User can resume a paused schedule; nextRunTime is recalculated from current time
- Only schedule owner can pause/resume their own schedules (authorization enforced)
- Audit log records schedule_created, schedule_paused, schedule_resumed events

---

## Phase 3: Scheduled Execution & Delivery

**Goal**
Implement the scheduling engine that executes due schedules, generates exports asynchronously, and delivers them to schedule owners via email.

**Scope**
- Build Scheduling & Execution Service with tick() polling logic
- Implement Export Run entity and execution lifecycle (pending → success | failed)
- Build Delivery & Retry Handler with email delivery integration
- Implement Delivery Attempt entity with automatic retry logic (up to 3 attempts with backoff)
- Implement retry scheduling and background task processing
- Add automatic schedule pause (isActive = false) on total delivery failure
- Extend audit logging for: export_generated, export_delivered, delivery_failed, schedule_auto_paused
- Build async job queue for execution coordination

**Acceptance Criteria**
- Scheduling Service tick() runs periodically and identifies schedules where nextRunTime <= now
- Feature flag and workspace config are rechecked before executing due schedule; execution skipped if disabled
- Row-level permission is re-validated at execution time; schedule not executed if owner lost access
- Size validation check applied before Export Run creation; execution rejected if filtered dataset exceeds 50 MB
- Export Run is created with status pending and enqueued to Export Generation Engine
- Export Generation Engine respects row-level permissions at generation time
- On generation success, Delivery & Retry Handler enqueues delivery to schedule owner email
- First delivery failure automatically enqueues retry with backoff
- Second delivery failure enqueues second retry with backoff
- Third delivery failure triggers schedule_auto_paused (isActive = false) and audit log record
- Audit log records export_generated, export_delivered, delivery_failed, and schedule_auto_paused events

---

## Phase 4: Export History & Monitoring

**Goal**
Provide visibility into past exports and delivery status for schedule owners and enable workspace administrators to monitor feature usage.

**Scope**
- Implement Export History Service with get_export_history(scheduleId, requesterId, limit)
- Build Export History query surface limited to last 30 runs with pagination
- Include delivery attempt details and file metadata (size, format, timestamp) in history response
- Build export history UI showing all runs for a schedule with delivery status
- Implement audit log query/filtering for export events by actor, resource, or event type
- Build admin monitoring dashboard showing feature usage, delivery success rates, and schedule counts

**Acceptance Criteria**
- Schedule owner can query export history for schedules they own
- Authorization check enforces only owner can view their schedule history
- History returns up to 30 most recent Export Runs ordered by executionTime descending
- Each run includes delivery attempt details (attempt count, status, timestamps)
- Each run includes file metadata (format, size in bytes, generation timestamp)
- Pagination works correctly for histories with more than 30 runs
- Admin dashboard displays total export schedules, total exports generated, delivery success rate, and feature flag state
- Audit log entries are queryable and filterable by event type, actor ID, and resource ID

---

## Phase 5: Polish & Hardening

**Goal**
Ensure system reliability, performance, and edge case handling across all subsystems.

**Scope**
- Implement job queue persistence and recovery (handle crashes during generation/delivery)
- Add rate limiting for export creation and schedule execution to prevent abuse
- Implement cleanup jobs (delete old files, prune audit logs beyond retention window)
- Add monitoring and alerting for delivery failures, queue backlog, and feature flag state
- Comprehensive error handling and user-facing error messages
- Performance optimization: index nextRunTime for efficient schedule polling
- Add request validation and input sanitization for all API contracts
- Integration tests for end-to-end workflows (one-off export, schedule creation, delivery, retry, pause/resume)

**Acceptance Criteria**
- System recovers from Export Generation Engine crash without losing export state (jobs can be retried)
- System recovers from Delivery & Retry Handler crash; in-flight delivery attempts are resent
- Rate limiting prevents single user from creating > 100 exports per hour
- Rate limiting prevents single schedule from exceeding 10 pending jobs in queue
- Audit log retention cleanup runs weekly and deletes records older than 90 days
- Monitoring alerts on delivery failure rate exceeding 10% for any 1-hour window
- Monitoring alerts on queue backlog exceeding 1000 jobs
- All user-facing errors include actionable error messages (e.g., "export exceeds 50 MB limit by X MB")
- nextRunTime index exists and schedule polling query completes in < 100ms for 10,000 active schedules
- Input validation rejects invalid UUIDs, invalid formats, invalid frequencies
- All end-to-end workflows (one-off, schedule creation, delivery, pause/resume) pass integration tests
