# Scheduled Report Exports: Phase Plan

## Phase 1: Foundation and Data Models

**Goal:** Establish the persistent data structures and permission framework required for scheduled exports.

**Scope:**
- Implement core domain model entities: Report, Export, ScheduledExport, ExportRun, and AuditLogEntry
- Create database schema and ORM mappings for all entities
- Build Permission Enforcer component with row-level access control filtering
- Implement Audit Logger component with event recording and basic query capabilities
- Create feature flag infrastructure to gate export functionality

**Acceptance Criteria:**
- All entity models persist and retrieve correctly from database
- Permission Enforcer correctly filters rows based on user access rules for at least one access control model
- Audit Logger records events with correct timestamp, user ID, resource ID, outcome, and details
- Feature flag can be queried for enabled/disabled state by workspace
- Database schema supports all entity relationships and constraints documented in the domain model

## Phase 2: One-Off Export Generation and Download

**Goal:** Deliver the core export generation workflow, allowing users to create immediate exports of reports in CSV or PDF format.

**Scope:**
- Implement Export Service with GenerateExport method
- Build format conversion logic for CSV and PDF output
- Integrate Permission Enforcer to apply row-level filtering during generation
- Add size validation (reject exports > 50 MB)
- Create REST/API endpoints for initiating one-off exports
- Implement browser download or download link delivery
- Add UI controls for export format selection (gated behind feature flag)
- Wire Audit Logger to record export_created and export_generated events

**Acceptance Criteria:**
- User can successfully download a CSV export of a report they have access to
- User can successfully download a PDF export of a report they have access to
- Exports respect row-level permissions (user sees only authorized rows)
- Exports > 50 MB are rejected with user-facing error message
- Audit log contains records of export creation and generation
- Feature flag disabled state prevents export endpoint access and hides UI controls
- Export includes all requested columns and data

## Phase 3: Scheduled Export Creation and Scheduler Integration

**Goal:** Enable users to create recurring scheduled exports that run at configured times and frequencies.

**Scope:**
- Implement Scheduled Export Service with CreateScheduledExport, PauseScheduledExport, and ResumeScheduledExport methods
- Build Scheduler component to manage scheduled job lifecycle
- Implement schedule validation (frequency, day of week, time of day)
- Create ScheduleExportExecution and CancelScheduleExecution in Scheduler
- Add UI controls for creating and managing scheduled exports
- Wire scheduled export creation audit logging
- Calculate and store first execution time when schedule is created
- Implement pause/resume functionality with status tracking and timestamp recording

**Acceptance Criteria:**
- User can create a daily scheduled export with valid time and format
- User can create a weekly scheduled export specifying day and time
- First execution is scheduled correctly based on creation time and frequency
- Pause action updates status and prevents future executions
- Resume action calculates next execution time and resumes scheduler
- Audit log records schedule creation, pause, and resume events
- Scheduler can retrieve and execute pending schedules at the correct times
- UI displays list of scheduled exports with status (active/paused)

## Phase 4: Scheduled Export Execution and Email Delivery

**Goal:** Automate the generation and delivery of scheduled exports to recipients with retry logic and failure handling.

**Scope:**
- Implement GenerateScheduledExport method in Export Service
- Build Email Delivery System component with SendExportEmail and RetryFailedDelivery methods
- Implement delivery retry logic (up to 3 attempts with scheduled retries)
- Create ExportRun records to track each execution with status, attempt count, and timestamps
- Implement automatic pause on repeated delivery failures (3 failed attempts)
- Wire Audit Logger to record export_generated, export_delivered, export_failed events
- Build scheduler integration to trigger periodic execution
- Handle SMTP failures and invalid email addresses gracefully

**Acceptance Criteria:**
- Scheduled export executes at configured time and generates report with owner's permissions
- Email with export attachment is successfully sent to schedule owner
- System correctly increments delivery attempt counter on each attempt
- Failed delivery is retried automatically up to 3 times with appropriate delays
- Schedule is auto-paused after 3 failed delivery attempts
- ExportRun records accurately reflect execution status, timestamps, and attempt counts
- Audit log contains complete records of generation, delivery attempts, and failures
- Export generation respects size limit (reject if > 50 MB) even for scheduled exports

## Phase 5: History, Monitoring, and Admin Controls

**Goal:** Provide visibility into export execution history, administrative controls, and complete feature flag management.

**Scope:**
- Implement GetScheduledExportHistory method to retrieve up to 30 recent ExportRuns
- Implement GetScheduledExportsByReport to list all schedules for a report
- Build UI screens for viewing execution history with status, timestamps, and failure reasons
- Create admin controls for enabling/disabling the export feature globally
- Implement feature flag disable behavior (skip executions, hide UI, reject endpoints)
- Build audit log query and filtering UI for compliance review
- Create monitoring dashboards showing export activity, failure rates, and storage usage
- Document export feature for users and administrators

**Acceptance Criteria:**
- User can view last 30 execution runs for a scheduled export with full details
- User can see execution status, timestamps, failure reasons, and delivery attempt counts
- Admin can disable export feature and observe that scheduled exports do not execute
- Admin can query audit logs filtered by event type, user, date range, and resource
- Feature disabled state prevents all export endpoints from functioning (403 response)
- Export UI controls are completely hidden when feature is disabled
- Historical execution data is retained even when feature is disabled (for re-enabling)
- Monitoring dashboard accurately reflects export system health and activity
