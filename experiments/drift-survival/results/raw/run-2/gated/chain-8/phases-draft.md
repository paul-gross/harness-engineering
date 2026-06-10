# Scheduled Report Exports — Implementation Phases

## Phase 1: Core Domain Model and On-Demand Export Service

**Goal**: Establish the foundational data model and implement the asynchronous export generation engine with row-level security enforcement.

**Scope**:
- Define and migrate database schema for `ScheduledExport`, `ExportRun`, `DeliveryAttempt`, and `ExportAuditLog` entities
- Implement the `Export Service` with support for CSV and PDF generation
- Add row-level permission validation to export generation (uses existing user permission system)
- Implement the 50 MB file size validation
- Build on-demand export endpoint (POST /reports/{reportId}/export)
- Implement synchronous audit logging to `ExportAuditLog` for export actions
- Create data layer repositories for all four new entities

**Acceptance Criteria**:
- User can trigger on-demand CSV and PDF exports from a report UI
- Export generation runs asynchronously without blocking the UI request
- Exports respect user's row-level report permissions (only visible rows included)
- Exports exceeding 50 MB are rejected with appropriate error message
- Export completion and failures are logged to `ExportAuditLog` with action types `EXPORT_INITIATED`, `EXPORT_COMPLETED`, `EXPORT_FAILED`
- Database stores all export runs with status tracking (PENDING, COMPLETED, FAILED)
- Export files are persisted and retrievable for download within session/temporary window

---

## Phase 2: Email Delivery Service and Retry Logic

**Goal**: Implement reliable email delivery of exports with automatic retry and failure tracking.

**Scope**:
- Implement the `Email Delivery Service` with retry logic (up to 3 attempts, exponential backoff)
- Create `DeliveryAttempt` records to track each send attempt
- Implement automatic pause of schedules after 3 consecutive delivery failures (auto-pause logic)
- Add email template and attachment handling for export delivery
- Integrate with existing email infrastructure or external mail service
- Audit logging for delivery outcomes (DELIVERY_SENT, DELIVERY_FAILED)

**Acceptance Criteria**:
- Email with export attachment is sent to schedule owner's email address
- On delivery success, `DeliveryAttempt` is marked SENT
- On delivery failure, system automatically retries up to 2 more times
- Exponential backoff is applied between retry attempts
- After 3 failed attempts, parent `ScheduledExport` is automatically paused
- `paused_at` timestamp is recorded when auto-pause occurs
- All delivery attempts are logged with attempt number and status
- Schedule owner receives notification when their schedule is auto-paused

---

## Phase 3: Scheduled Export Manager and Job Execution

**Goal**: Implement scheduled execution of exports at user-defined frequencies with proper orchestration.

**Scope**:
- Implement the `Scheduled Export Manager` as a background job processor
- Add job scheduling logic to detect due exports (DAILY or WEEKLY frequencies)
- Implement scheduled export creation workflow (user specifies frequency and time)
- Create scheduled export CRUD operations and list endpoints
- Integrate scheduler with Export Service and Email Delivery Service
- Implement pause/resume functionality for scheduled exports
- Audit logging for schedule lifecycle events (SCHEDULE_CREATED, SCHEDULE_PAUSED_AUTO, SCHEDULE_PAUSED_MANUAL, SCHEDULE_RESUMED)

**Acceptance Criteria**:
- User can create a scheduled export with daily or weekly frequency and specific time of day
- Scheduled exports are stored with ACTIVE status by default
- Background job runs at configured intervals and detects due exports based on frequency and scheduled_time
- Due exports trigger export generation and email delivery workflows
- `ExportRun` records are created with triggered_at timestamp
- User can pause an active schedule (manual pause), updating status to PAUSED
- User can resume a paused schedule, updating status to ACTIVE and clearing paused_at
- Schedule lifecycle actions (create, pause, resume) are logged to `ExportAuditLog`
- Audit log includes schedule creation and resume actions with schedule details in metadata

---

## Phase 4: Export History and Admin Dashboard

**Goal**: Provide visibility into export history and administrative controls for export functionality.

**Scope**:
- Implement export history view showing last 30 runs per schedule
- Build detail views for individual export runs with delivery attempt history
- Create admin dashboard for feature flag toggle and workspace-wide export visibility
- Implement feature flag state persistence (FEATURE_ENABLED, FEATURE_DISABLED audit events)
- Add conditional UI rendering based on feature flag state
- Implement feature flag validation in all export endpoints
- Create analytics/reporting views for export usage patterns

**Acceptance Criteria**:
- User can navigate to a scheduled export detail view and see export history
- Export history displays triggered_at, status, file_size, and delivery outcome for last 30 runs
- Clicking into an export run shows all delivery attempts with timestamps and error messages
- Admin can toggle "Enable Export Functionality" feature flag in workspace settings
- When feature is disabled, all export UI elements are hidden and export endpoints reject requests
- When feature is enabled, export functionality is fully visible and operational
- Feature flag toggle is logged to `ExportAuditLog` with FEATURE_ENABLED or FEATURE_DISABLED actions
- Audit log entries show comprehensive history of all administrative toggles and their timestamps

---

## Phase 5: Testing, Performance, and Production Readiness

**Goal**: Ensure system reliability, performance, and observability in production environments.

**Scope**:
- Write comprehensive unit tests for Export Service (permission validation, size limits, format generation)
- Write integration tests for scheduled execution, email delivery with retries, and audit logging
- Performance test export generation with large datasets near the 50 MB boundary
- Load test scheduled export manager with many concurrent schedules
- Implement monitoring and alerting for scheduled export failures
- Add distributed tracing for export and delivery workflows
- Document operational procedures for manual intervention (pause/resume, retry triggers, etc.)
- Create migration guides for existing export functionality (if any) to new system

**Acceptance Criteria**:
- Unit test coverage >= 80% for Export Service, Email Delivery Service, and Scheduled Export Manager
- Integration tests verify end-to-end workflows: on-demand export, scheduled execution, retry logic, auto-pause
- Performance tests confirm exports up to 49 MB complete within acceptable time (< 30 sec target)
- Load tests with 100+ active schedules show no degradation or missed executions
- Monitoring alerts are configured for failed exports and delivery failures
- Distributed traces can be followed from schedule trigger through email delivery
- Operational runbook documents manual override procedures and troubleshooting steps
- All audit log actions can be queried and filtered for compliance/debugging purposes
