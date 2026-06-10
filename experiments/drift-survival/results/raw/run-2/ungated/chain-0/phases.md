# Scheduled Report Exports — Phase Plan

## Phase 1: Domain Model & Feature Flag Foundation

**Goal:** Establish the data model and feature flag infrastructure that will control the entire export feature.

**Scope:**
- Define and persist all domain entities: `ExportRequest`, `ScheduledExport`, `ExportExecution`, and `AuditLogEntry` with their schemas and database tables
- Implement the `IsExportEnabled` and `SetExportEnabled` feature flag operations
- Set up the audit logging system to capture all export-related events
- Create basic permission validation infrastructure (read access checks for reports)

**Acceptance criteria:**
- All domain entities can be created, read, updated in the database
- Feature flag can be toggled by workspace admin and checked before export operations
- Audit logger successfully records events without blocking the main request path
- Permission validation correctly identifies when a user lacks read access to a report

## Phase 2: On-Demand Export Workflow

**Goal:** Deliver the synchronous on-demand export capability with format rendering and error handling.

**Scope:**
- Implement the `GenerateExport` contract to handle CSV and PDF rendering
- Implement `ValidateExportSize` to perform pre-flight checks (50 MB limit)
- Wire feature flag checks into on-demand export endpoints
- Apply row-level permission filters during report query execution
- Stream files to users on success, return user-facing error messages on failure
- Log all on-demand export events (success and failure) to audit trail

**Acceptance criteria:**
- On-demand CSV and PDF exports generate successfully for authorized users
- Exports respect row-level permission filters
- Requests reject when feature flag is disabled
- Requests reject when user lacks report read access
- Requests reject when estimated size exceeds 50 MB
- All successful and failed export attempts are logged in audit trail
- Users receive clear error messages for each failure mode

## Phase 3: Scheduled Export Management & Background Execution

**Goal:** Enable users to define and execute recurring exports via background jobs.

**Scope:**
- Implement `CreateScheduledExport` to define recurring exports with daily/weekly recurrence
- Implement the scheduler component to trigger executions at scheduled times with exactly-once semantics
- Implement background job execution that generates CSV exports with the schedule owner's permissions
- Implement `PauseSchedule` and `ResumeSchedule` to control schedule lifecycle
- Update `next_run_at` timestamps after each execution
- Apply size limits to scheduled exports and mark oversized executions as failed
- Create `ExportExecution` records with generation status and file metadata

**Acceptance criteria:**
- Scheduled exports can be created with daily and weekly recurrence patterns
- Scheduler correctly calculates next run times based on recurrence configuration
- Background jobs execute at scheduled times and generate ExportExecution records
- Permission filters are applied to scheduled export queries
- Oversized scheduled exports fail with appropriate error message
- Pause/resume operations update schedule state and next_run_at correctly
- All schedule lifecycle events are logged to audit trail

## Phase 4: Delivery Pipeline with Retry & Circuit Breaker

**Goal:** Implement reliable email delivery with retry logic and automatic pause on persistent failures.

**Scope:**
- Implement the delivery pipeline to email export files to configured recipients
- Implement exponential backoff retry logic (up to 3 attempts with 5min, 15min, 60min delays)
- Implement circuit-breaker semantics: pause schedule after third consecutive delivery failure
- Track delivery attempt counts and outcomes in `ExportExecution` records
- Clear `next_run_at` when schedule is auto-paused to prevent further scheduling
- Log each delivery attempt (success, failure, retry) to audit trail
- Implement `RetryDelivery` endpoint for explicit admin-initiated retries

**Acceptance criteria:**
- Export files are successfully emailed to configured delivery addresses
- Failed delivery attempts trigger exponential backoff retries automatically
- Schedule automatically pauses after third delivery failure
- Paused schedules do not execute until manually resumed
- All delivery attempts (including retries) are logged to audit trail
- Audit log clearly indicates when schedule is auto-paused due to circuit breaker
- Admin can manually retry delivery of failed executions

## Phase 5: Execution History & Feature Completeness

**Goal:** Provide visibility into scheduled export execution history and finalize all operational features.

**Scope:**
- Implement `GetExecutionHistory` to retrieve the 30 most recent executions per schedule
- Implement execution history UI showing status, file size, delivery attempt count, and outcome
- Finalize read-only/hidden export management UI when feature flag is disabled
- Implement cleanup/retention policy for execution history (keep last 30 records per schedule)
- Verify all audit logging is complete across all workflows (on-demand, scheduled, delivery, pause/resume, flag toggle)
- Integration testing across all components with various failure scenarios

**Acceptance criteria:**
- Execution history can be retrieved for any schedule the user owns or administers
- Execution history displays up to 30 most recent records with full details
- Retrieval respects permission boundaries (owner or admin only)
- Export management UI becomes read-only when feature flag is disabled
- Execution records are properly retained and cleaned up
- All user-facing export management features work end-to-end with feature flag toggled both ways
- Audit trail contains comprehensive records for compliance and troubleshooting across all scenarios
