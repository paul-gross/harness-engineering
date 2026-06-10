# Scheduled Report Exports: Phase Plan

## Phase 1: Core Domain and API Foundation

**Goal:** Establish the data model and export API endpoints for one-off exports, providing the foundational infrastructure that scheduled exports will build upon.

**Scope:**
- Implement core domain entities: Report, Export, and AuditLogEntry
- Create Export Service API (POST /api/exports, GET /api/exports/:exportId, GET /api/exports/:exportId/download)
- Implement basic audit logging for export events
- Add feature flag check to all export endpoints
- Implement permission validation to ensure users can only export reports they have access to
- Support CSV and PDF format selection
- Return appropriate error codes (403, 404, 400) for validation failures

**Acceptance Criteria:**
- Users can initiate one-off CSV and PDF exports via POST /api/exports
- Export status polling works via GET /api/exports/:exportId
- Export download returns the correct binary file with appropriate content-type and content-disposition headers
- Feature flag prevents export API access when disabled (returns 403)
- Users cannot export reports they lack read permission for (returns 403)
- Invalid report IDs return 404; invalid formats return 400
- Audit log entries are created for export_requested events
- Export records show pending/complete/failed/oversized status

## Phase 2: Asynchronous Export Processing and Formatting

**Goal:** Implement the background processing pipeline to handle actual report generation, permission filtering, and format conversion for exports.

**Scope:**
- Build the Permission Filter that intercepts report queries and applies row-level access controls
- Implement the async job execution flow (enqueue, dequeue, process)
- Create the Formatter component that converts filtered result sets to CSV and PDF
- Implement the 50 MB size limit check with oversized status
- Store generated artifacts (S3, blob storage, or local file)
- Update Export status to complete/failed/oversized based on processing outcome
- Write audit log entries for export_completed, export_failed, and export_oversized events
- Implement error handling and metadata capture (row count, size in bytes, error messages)

**Acceptance Criteria:**
- Background export job successfully retrieves report query and executes it
- Permission Filter correctly removes rows that the requester cannot access
- CSV exports are generated in valid CSV format with all filtered data
- PDF exports are generated in valid PDF format with proper formatting
- Files exceeding 50 MB are marked as oversized and do not proceed to artifact storage
- Artifacts are persisted and retrievable via download endpoint
- Export status transitions from pending to complete, failed, or oversized correctly
- Audit log captures row counts, file sizes, and error messages
- Export status polling returns accurate row count and size information for complete exports

## Phase 3: Scheduled Export Management and Execution

**Goal:** Enable users to create and manage recurring export schedules, with background scheduler executing scheduled exports on defined recurrence patterns.

**Scope:**
- Implement Schedule and ScheduleRun domain entities
- Create Schedule Service API (POST /api/schedules, GET /api/schedules, PATCH /api/schedules/:scheduleId, DELETE /api/schedules/:scheduleId)
- Implement recurrence pattern validation (daily and weekly with day/time options)
- Build the background scheduler that evaluates active schedules and enqueues export tasks
- Calculate next_run timestamps based on recurrence patterns
- Support schedule pause/resume functionality
- Set email delivery address to schedule owner's email at schedule creation time
- Write audit log entries for schedule lifecycle events (schedule_created, schedule_paused, schedule_resumed, schedule_deleted)

**Acceptance Criteria:**
- Users can create daily and weekly recurring export schedules via POST /api/schedules
- Recurrence patterns are validated (valid day-of-week values, valid hour ranges)
- Users can list their own schedules (implicitly scoped) via GET /api/schedules
- Users can pause/resume schedules via PATCH /api/schedules/:scheduleId
- Users can delete schedules via DELETE /api/schedules/:scheduleId
- Paused schedules have next_run set to null
- Background scheduler wakes up periodically and identifies schedules due for execution
- Audit log entries are written for all schedule state changes
- Schedule creation fails with 403 if feature flag is disabled or user lacks read permission

## Phase 4: Scheduled Export Delivery and Retry Logic

**Goal:** Deliver completed scheduled exports via email with robust retry logic and delivery tracking, ensuring reliable export distribution.

**Scope:**
- Implement the Delivery Service for email composition and sending
- Build retry logic with attempt counting (maximum 3 attempts) and configurable backoff timing
- Implement ScheduleRun tracking to record delivery status and attempt history
- Automatically pause schedules after 3 failed delivery attempts
- Write audit log entries for delivery attempts (schedule_run_delivered, schedule_run_delivery_failed, schedule_run_max_retries_exceeded)
- Implement the GetScheduleRuns endpoint (GET /api/schedules/:scheduleId/runs) to surface run history
- Handle email failures gracefully without blocking export task completion
- Update next_run timestamp on successful delivery

**Acceptance Criteria:**
- Email containing scheduled export artifact is successfully sent to schedule owner's email address on export completion
- Email includes report name, export date, and attached artifact
- Delivery failures trigger retry logic with incremented attempt count
- Up to 3 delivery attempts are made with appropriate backoff timing
- After 3 failed attempts, the schedule is automatically paused with audit log entry
- Users can view last 30 ScheduleRuns via GET /api/schedules/:scheduleId/runs
- ScheduleRun records show delivery_status and attempt_count
- Delivery Service errors do not prevent export completion
- Audit log entries capture delivery attempts and failures with error information

## Phase 5: Admin Controls and Observability

**Goal:** Provide workspace administrators with feature flag controls and ensure comprehensive audit trail for compliance and troubleshooting.

**Scope:**
- Implement admin endpoint to toggle "Enable Report Exports" feature flag
- Wire feature flag checks into scheduler to prevent execution when disabled
- Write audit log entries for feature flag state changes
- Implement artifact expiration and cleanup for old exports (configurable retention)
- Implement audit log cleanup/archival for old ScheduleRuns (> 30 days)
- Create audit log query APIs or admin dashboards for export and schedule events
- Document feature flag behavior: disabled state hides UI, returns 403 on API calls, stops scheduled jobs

**Acceptance Criteria:**
- Admins can enable/disable export functionality via settings/configuration interface
- When disabled: export UI is hidden, API endpoints return 403, scheduled jobs do not execute
- When enabled: functionality resumes respecting active/paused schedule status
- Feature flag state changes are written to audit log
- Old ScheduleRuns (> 30 days old) are archived or deleted per retention policy
- Old artifacts are cleaned up according to configured retention policy
- Audit log provides queryable history of all export and schedule events
- All error scenarios (permission denials, failures, retries) are logged with sufficient context for troubleshooting
