# Scheduled Report Exports: Phase Plan

## Phase 1: Export Request Handler and Domain Model

**Goal:** Establish the core API surface and persist the foundational domain entities that underpin the export system.

**Scope:**
- Implement the domain model: Report (reference entity), Export Request, Permission Context, Scheduled Export, and associated persistence layer
- Build the Export Request Handler with endpoints for one-off and scheduled export submission
- Implement row-level permission validation at request time
- Implement the export_enabled workspace flag and its enforcement
- Create audit log infrastructure and record ExportRequested and ScheduledExportCreated events
- Implement pause/resume endpoints for scheduled exports with audit logging

**Acceptance Criteria:**
- POST /exports/one-off accepts report_id, format, user_id and rejects requests if user lacks row-level access or exports are disabled
- POST /exports/scheduled creates a Scheduled Export record owned by the requesting user and rejects requests if user lacks row-level access or exports are disabled
- PUT /exports/scheduled/{schedule_id}/pause and /resume update schedule state and verify the caller is the schedule owner
- Workspace admins can disable exports via POST /admin/exports/disable, blocking all new requests
- Audit log entries are created for all handler operations with workspace context
- All domain model entities persist to the data store with correct relationships

---

## Phase 2: Export Generation Engine

**Goal:** Deliver asynchronous report rendering with permission filtering and size validation.

**Scope:**
- Implement the Export Generation Engine as an asynchronous worker pool
- Build the ExportGenerator interface with format-specific rendering (CSV and PDF)
- Implement row-level permission filtering using the captured Permission Context
- Enforce the 50 MB output size limit with graceful failure
- Implement message queue infrastructure for Export Generation Tasks
- Record ExportGenerationStarted, ExportGenerationCompleted, and ExportGenerationFailed audit events
- Implement blob storage integration for export artifacts

**Acceptance Criteria:**
- Export Generation Tasks can be enqueued from the Export Request Handler and dequeued by worker pool
- CSV and PDF rendering produces correctly formatted output filtered by the captured permission context
- Export artifacts exceeding 50 MB fail with a size-exceeded error recorded in the Export Request status
- Generated artifacts are stored in blob storage with location and size metadata
- Worker pool is thread-safe and idempotent (same inputs produce same output)
- All generation steps are logged for audit trail
- GenerationComplete events are emitted on successful completion

---

## Phase 3: Delivery and Retry System

**Goal:** Ensure reliable delivery of generated exports with intelligent retry logic and delivery attempt tracking.

**Scope:**
- Implement the DeliveryOrchestrator to send exports via email
- Implement the RetryCoordinator with 3-attempt retry policy and intelligent backoff
- Create the ExportDeliveryAttempt entity with attempt tracking (number, outcome, reason, timestamp)
- Implement idempotent delivery at the request + attempt level
- Record ExportDeliveryAttempted audit events for each attempt
- Implement integration with SchedulePauseManager to pause schedules after third failure
- Record ScheduledExportPausedOnDeliveryFailure audit events

**Acceptance Criteria:**
- DeliveryOrchestrator attempts email delivery and records the outcome in ExportDeliveryAttempt
- Failed deliveries are retried with intelligent backoff up to 3 attempts
- After the third failed delivery attempt, the parent Scheduled Export is automatically paused
- Delivery attempts are idempotent (repeated calls with same request_id + attempt_number produce same result)
- All delivery outcomes are recorded in the audit log with failure reasons
- Scheduled exports that were already created but failed delivery remain in data store in paused state

---

## Phase 4: Scheduled Export Manager and Schedule Run History

**Goal:** Automate recurring export execution and provide visibility into schedule run history.

**Scope:**
- Implement the ScheduleOrchestrator to read active Scheduled Export records and trigger exports at configured cadence
- Implement the trigger logic for daily and weekly frequencies
- Create the ScheduleRun entity to record each scheduled export execution with trigger timestamp and associated Export Request
- Implement the 30-day retention policy for Schedule Runs
- Implement the schedule run history query endpoint (GET /exports/scheduled/{schedule_id}/history)
- Implement idempotent trigger behavior (safe to call multiple times)
- Record trigger attempts and schedule state changes in the audit log

**Acceptance Criteria:**
- ScheduleOrchestrator correctly enumerates active Scheduled Export records and identifies those due for execution
- Daily and weekly schedules trigger at the correct cadence
- Each trigger generates an Export Request with the schedule owner's permission context
- Export Request is enqueued and processed through Workflows 1–3 (generation and delivery)
- ScheduleRun records are created and linked to associated Delivery Attempts
- GET /exports/scheduled/{schedule_id}/history returns the 30 most recent runs sorted by recency, with trigger timestamp, export status, and delivery attempt details
- Only the schedule owner can view their schedule's history
- ScheduleOrchestrator is idempotent and all trigger attempts are logged for audit

---

## Phase 5: Integration, Testing, and Admin Visibility

**Goal:** Validate end-to-end workflows, provide administrative controls, and ensure system resilience.

**Scope:**
- Write comprehensive integration tests for all six workflows (one-off, scheduled creation, scheduled trigger/delivery, pause/resume, history, admin disable)
- Implement the admin control panel UI for enabling/disabling export functionality and viewing workspace audit logs
- Implement dashboard or administrative view for monitoring active schedules, recent delivery failures, and paused schedules
- Test failure scenarios: permission denial, oversized exports, delivery failures, schedule pause recovery, export disable/re-enable
- Verify audit log entries are complete and queryable for compliance reporting
- Verify Schedule Run retention (newest 30 retained) and cleanup of older records
- Load test the worker pool and delivery system under concurrent load
- Document all APIs, entities, and retry/backoff behavior

**Acceptance Criteria:**
- All six workflows execute end-to-end without errors
- One-off exports are generated and delivered successfully
- Scheduled exports trigger at the correct cadence and deliver successfully
- Failing schedules are automatically paused after three failures and can be resumed
- Admin disable/re-enable of exports prevents new requests but leaves existing schedules intact
- Permission-denied exports fail gracefully and are audited
- Oversized export failures are recorded and visible in schedule run history
- Audit log contains all expected events and can be filtered by workspace, user, and time range
- Schedule Run records are cleaned up after 30 days
- The system handles concurrent requests and multiple worker pool processes correctly
