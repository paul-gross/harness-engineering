# Scheduled Report Exports — Phase Plan

## Phase 1: Core Export Service & Domain Model

**Goal:** Establish the foundational export generation pipeline with data retrieval, format conversion, and size validation.

**Scope:**
- Implement Export domain model with all fields (id, report_id, format, requested_by_user_id, status, file_size_bytes, generated_at, requested_at)
- Build Export Service with Request Export and Get Export Status APIs
- Implement row-level permission filtering layer for data retrieval
- Add format conversion support (CSV and PDF generation)
- Implement size validation (50 MB threshold check at request and post-generation)
- Add feature flag check for export functionality
- Integrate Audit Service to log export_requested and export_generated/export_failed events
- Database schema for Export table with indices on report_id, requested_by_user_id, and status

**Acceptance Criteria:**
- User can request an on-demand CSV export and receive a job ID
- Export Service validates user permissions before processing
- Export size is checked against 50 MB limit before queuing and after generation
- Failed exports (size exceeded, generation error) update status to "failed" and log error
- Export can be downloaded via Download Export API when status is "ready"
- Feature flag blocks all export requests when disabled
- Audit log contains entries for export request and generation events

---

## Phase 2: Scheduler Service & Scheduled Export Management

**Goal:** Implement recurring export scheduling with lifecycle management (create, pause, resume, delete).

**Scope:**
- Implement ScheduledExport domain model with all fields (id, export_id, owner_user_id, frequency, delivery_email, is_active, created_at, last_run_at, next_run_at)
- Build Scheduler Service with Create, Pause, Resume, Delete, and Get Schedule History APIs
- Implement scheduling logic to trigger exports at configured frequency (daily/weekly)
- Pass user permission context to ensure row-level security on scheduled executions
- Implement ExportRun domain model to track individual executions (id, scheduled_export_id, export_id, ran_at, delivery_status, retry_count, error_message)
- Database schema for ScheduledExport and ExportRun tables with indices on owner_user_id, is_active, next_run_at
- Integrate Audit Service to log scheduled_export_created, scheduled_export_paused, scheduled_export_resumed events

**Acceptance Criteria:**
- User can create a scheduled export with report, format, frequency, and delivery email
- Scheduler triggers export job at each scheduled time (daily or weekly as configured)
- Pause/resume toggles is_active flag and records audit events
- Schedule history view shows last 30 ExportRun records with status, timestamp, and retry count
- Next scheduled run time (next_run_at) is calculated and updated after each execution
- Only active schedules (is_active=true) are monitored for triggering
- Audit log contains all schedule lifecycle events

---

## Phase 3: Delivery Service & Email Distribution

**Goal:** Implement asynchronous email delivery of completed exports with automatic retry logic and failure handling.

**Scope:**
- Build Delivery Service with Queue Delivery and Retry Delivery APIs
- Implement email composition and sending for export attachments
- Implement retry mechanism with exponential backoff (max 3 retries)
- Update ExportRun delivery_status after each delivery attempt (pending → delivered or failed_will_retry → failed_permanent)
- On third retry failure: pause schedule (set is_active=false) and record failure in audit log
- Track retry_count and error_message on each ExportRun record
- Integrate Audit Service to log export_delivered and export delivery failures

**Acceptance Criteria:**
- Export completion triggers Delivery Service to queue email
- Email is sent with export file as attachment to designated recipient
- ExportRun status updates to "delivered" after successful send
- Failed delivery automatically re-queues with exponential backoff
- After third failed attempt, schedule is paused and audit log records permanent failure
- Retry count is incremented and tracked on ExportRun
- Error messages explain delivery failure reason (network, invalid email, etc.)

---

## Phase 4: Admin Governance & Audit Visibility

**Goal:** Provide administrative controls over export functionality and comprehensive audit trail for compliance and troubleshooting.

**Scope:**
- Build Feature Control API (Check Feature Enabled and Set Export Feature State)
- Implement admin workspace settings interface to enable/disable exports globally
- Build comprehensive Audit Service with Log Event and Get Audit Log APIs
- Support filtering by report_id, user_id, event_type, and date range
- Ensure all export operations (request, generation, scheduled creation/pause/resume, delivery) are logged
- Implement authorization checks on admin operations
- Create admin dashboard view of audit log showing all export activity

**Acceptance Criteria:**
- Admin can toggle export feature flag in workspace settings
- When disabled, all export requests are rejected with FeatureDisabled error
- Audit log contains complete history of all export events across all users and reports
- Audit entries include event_type, user_id, report_id, timestamp, and structured details
- Admin can filter audit log by various dimensions (user, report, event type, date)
- Admin operations (enable/disable) are themselves recorded in audit log
- Unauthorized users cannot access audit log or admin controls

---

## Phase 5: Testing, Hardening & Documentation

**Goal:** Ensure reliability, security, and operational stability across all components with comprehensive test coverage and runbooks.

**Scope:**
- Integration tests covering full workflows: on-demand export, scheduled export with delivery, pause/resume, retry logic
- Permission boundary testing to verify row-level security is enforced at all data retrieval points
- Error handling and edge case tests (size exceeded, malformed data, email delivery failures, concurrent requests)
- Load testing for scheduler triggering multiple exports simultaneously
- Security review of permission enforcement, audit logging, and admin controls
- Create operational runbooks for monitoring scheduled export execution, handling delivery failures, troubleshooting
- Performance optimization of data filtering and format conversion for large reports
- Documentation of API contracts, domain model, deployment steps, and troubleshooting guide

**Acceptance Criteria:**
- All workflows execute end-to-end with expected behavior
- Permission checks block unauthorized data access in all export scenarios
- Size validation correctly prevents exports exceeding 50 MB limit
- Retry logic with exponential backoff successfully recovers from transient delivery failures
- Scheduler correctly triggers exports for multiple active schedules without race conditions
- Audit log accurately captures all events in proper sequence
- Runbooks document common operational tasks and troubleshooting steps
- System performs acceptably under concurrent export and scheduled trigger loads
