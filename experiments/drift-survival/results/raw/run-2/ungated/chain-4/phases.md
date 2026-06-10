# Scheduled Report Exports – Phase Plan

## Phase 1: Foundation – Export Service & Domain Model

**Goal:** Build the core export generation capability with data models to support both one-off and scheduled exports.

**Scope:**
- Implement Export domain model (id, report_id, format, requested_by, created_at, status, file_size_bytes, error_message)
- Implement ScheduledExport domain model (id, report_id, owner_id, format, frequency, schedule_time, weekday, status, pause_reason, created_at, updated_at)
- Implement ExportRun domain model (id, scheduled_export_id, export_id, scheduled_at, started_at, completed_at, status, attempt_number, error_message)
- Implement Export Service with GenerateExport method supporting CSV and PDF generation
- Implement ValidateExportRequest to check feature flag, workspace admin setting, and user permissions
- Integrate row-level permission enforcement into export generation
- Implement 50 MB file size limit validation with SizeLimitExceeded exception
- Add database schema for Export, ScheduledExport, and ExportRun tables

**Acceptance Criteria:**
- One-off exports can be generated in CSV and PDF formats
- File size validation rejects exports larger than 50 MB
- Export request validation checks feature flag and admin workspace setting
- User permissions are applied to report queries before export generation
- All three domain models can be persisted and retrieved from the database
- Export generation completes successfully for a test report within expected time bounds

---

## Phase 2: Audit Trail & Basic Schedule Management

**Goal:** Add audit logging for export operations and implement schedule creation/retrieval/deletion.

**Scope:**
- Extend Audit Log with export and scheduled export events (export_created, export_failed, schedule_created, schedule_paused, schedule_resumed, schedule_deleted, export_delivered, export_delivery_failed)
- Log export creation and failure events in the one-off export workflow
- Implement Schedule Manager with CreateSchedule, GetSchedule, DeleteSchedule methods
- Add input validation for CreateSchedule (frequency values, time ranges, weekday when applicable)
- Enqueue initial scheduled run upon schedule creation
- Log schedule creation and deletion audit events
- Implement PauseSchedule and ResumeSchedule methods with audit logging

**Acceptance Criteria:**
- Export creation and failure events are logged to the audit trail with proper context
- Schedules can be created with valid inputs (daily/weekly frequency, valid times, optional weekday)
- Schedule creation rejects invalid inputs with clear error messages
- Schedule creation enqueues the next run
- Schedules can be paused, resumed, and deleted by their owner
- Pause/resume/delete operations are logged to the audit trail
- Schedule queries enforce ownership (users can only access their own schedules)

---

## Phase 3: Scheduled Execution & Delivery Engine

**Goal:** Build the scheduler and delivery engine to execute scheduled exports and attempt email delivery.

**Scope:**
- Implement scheduler trigger mechanism that checks for active schedules at configured times
- Implement Execute Scheduled Export workflow (generation with owner's permissions, ExportRun creation)
- Implement Delivery & Retry Engine with SendExportEmail method
- Implement exponential retry logic for failed deliveries (up to 3 attempts with 2^attempt * base_delay backoff)
- Track attempt_number and retry state in ExportRun records
- On generation success, enqueue email delivery and set ExportRun status to retrying
- On generation failure, create ExportRun with failed status, pause schedule, log audit event, and notify owner
- Implement RetryFailedDelivery method with exponential backoff calculation
- After 3 failed delivery attempts, pause schedule with pause_reason = "delivery_failed_after_retries"
- On delivery success, set ExportRun status to success and enqueue next scheduled run

**Acceptance Criteria:**
- Scheduler executes scheduled exports at the correct time for daily and weekly frequencies
- Exports generated during scheduled execution use the schedule owner's row-level permissions
- ExportRun records are created for each execution attempt
- Email delivery succeeds and ExportRun status is set to success
- Failed deliveries trigger exponential backoff retry logic
- Retry attempts (up to 3) increment attempt_number and are tracked in ExportRun
- On final delivery failure (attempt 3), schedule is paused with appropriate reason
- Generation failures pause the schedule and send owner notification
- Delivery success enqueues the next scheduled run

---

## Phase 4: History Visibility & User Controls

**Goal:** Provide users and administrators visibility into execution history and centralized export controls.

**Scope:**
- Implement GetRunHistory method to retrieve ExportRun records for a schedule (last 30 runs, ordered by scheduled_at desc)
- Include status, attempt_number, timestamps, error_message, and file_size_bytes in history response
- Enforce ownership check on history access (users can only access their own schedules' history)
- Implement historical data retention (30-day window for active display, older records with stale markers or archival)
- Implement Feature Flag & Admin Control API (GetExportSettings, SetWorkspaceExportSetting)
- Add workspace-level admin setting to enable/disable all exports
- When exports are disabled, reject all one-off and scheduled export requests with "exports disabled" error
- Log workspace setting changes as audit events
- Implement NotifyScheduleFailure notification method for owner notifications on generation and delivery failures

**Acceptance Criteria:**
- Users can retrieve run history for their scheduled exports (last 30 runs)
- Run history includes status, attempt counts, timestamps, error messages, and file sizes
- Ownership enforcement prevents users from viewing other users' schedules and histories
- Administrators can enable/disable exports at workspace level
- When disabled, all export requests are rejected with clear error message
- Scheduled exports remain in database but no new runs are enqueued while disabled
- Export/schedule setting changes are logged to audit trail
- Owners receive email notifications on generation and delivery failures with actionable information

---

## Phase 5: Integration Testing & Operational Hardening

**Goal:** Validate the end-to-end system, handle edge cases, and prepare for production operation.

**Scope:**
- End-to-end integration tests for one-off export workflows (success and failure paths)
- End-to-end integration tests for scheduled export creation, execution, and delivery
- Integration tests for retry logic and exponential backoff under simulated delivery failures
- Integration tests for pause/resume and schedule deletion workflows
- Integration tests for workspace-level disable/enable of exports
- Edge case handling (schedule execution during storage outages, delivery service unavailability, orphaned ExportRun records)
- Concurrency testing (multiple schedules running simultaneously, scheduler handling rapid frequency changes)
- Audit trail verification tests (all expected events logged with correct context)
- Performance testing (large report export generation, history query performance with 30+ days of runs)
- Error message clarity and user guidance for common failure scenarios
- Documentation of scheduler configuration and monitoring requirements

**Acceptance Criteria:**
- All one-off export scenarios (success, generation failure, size limit exceeded, feature disabled) pass integration tests
- All scheduled export scenarios (creation, execution, delivery success, retry, final failure pause) pass integration tests
- Exponential retry backoff is correctly calculated and applied across all attempts
- Schedule pause/resume/delete workflows function correctly and audit trail is complete
- Workspace disable/enable of exports prevents/allows requests as expected
- Concurrent schedule executions do not interfere with each other
- Audit events are logged for all documented actions with proper context and user attribution
- Performance benchmarks show acceptable latency for typical report exports and history queries
- Error messages guide users toward resolution (e.g., schedule paused with reason, file too large with limit, feature disabled)
