# Phase Plan: Scheduled Report Exports

## Phase 1: Domain Model and Permission Foundation

**Goal**
Establish the core data structures and permission layer that all export operations depend on.

**Scope**
- Create database schema for Export Schedule, Export Job, Export Delivery, and Audit Log Entry entities
- Implement Permission Enforcer contract for checking row-level access to reports
- Implement Feature Flag Manager contract with workspace-level and global flag support
- Implement Audit Logger contract with fire-and-forget logging
- Create database migrations and seed data for tests

**Acceptance Criteria**
- Schema passes linting and supports all entity relationships (Schedule → Jobs → Deliveries)
- Permission Enforcer returns correct access decisions for users with and without row-level permissions
- Audit Logger persists events without blocking triggering operations
- Feature Flag Manager correctly evaluates enabled/disabled state at workspace and global levels
- Database can be initialized from scratch and supports the full schema for all entities

## Phase 2: One-Off Export Workflow

**Goal**
Enable users to generate and download individual exports immediately with size validation and permission checks.

**Scope**
- Implement Export Service contract for generating one-off exports (asynchronous generation, synchronous return of job ID)
- Implement Size Validator contract for enforcing 50 MB export limit
- Build file generation for CSV export format
- Integrate permission validation and feature flag checks into export flow
- Implement job status lifecycle: `pending` → `generating` → `generated` (or `failed`)
- Add download endpoint that retrieves generated exports

**Acceptance Criteria**
- User can request one-off export and immediately receive job ID for tracking
- Export Service correctly validates user permissions before processing
- Feature flag disabled blocks all export requests with appropriate error
- Generated files under 50 MB are stored and retrievable
- Files exceeding 50 MB fail with user-facing error message
- Audit Logger records export request and generation completion
- Download endpoint validates job ownership and returns file

## Phase 3: Scheduled Export Infrastructure

**Goal**
Build the scheduling engine and schedule lifecycle management (create, pause, resume) with audit trails.

**Scope**
- Implement Scheduling Engine contract for creating schedules with first job enqueueing
- Implement Pause Schedule and Resume Schedule workflows
- Build Scheduling Engine's Check Due Schedules system-triggered operation
- Create job enqueueing mechanism tied to frequency (daily/weekly)
- Integrate schedule creation validation (permission checks, feature flag)
- Build schedule management UI/API endpoints for pause, resume, and viewing schedules

**Acceptance Criteria**
- Schedule creation persists record and enqueues first export job before returning to user
- Pause Schedule transitions state to `paused` and stops future job enqueueing immediately
- Resume Schedule transitions state back to `active` and enqueues next due job
- Check Due Schedules identifies all schedules due based on frequency and last_run_at
- Schedules can only be paused/resumed by their owner
- Audit Logger records all schedule lifecycle events
- Run History Retrieval returns jobs created in last 30 days with linked delivery records

## Phase 4: Email Delivery and Retry Logic

**Goal**
Implement export delivery via email with automatic retry and failure handling.

**Scope**
- Implement Delivery Service contract for creating delivery records and enqueueing email tasks
- Implement email sending with external email service integration
- Implement Retry Delivery contract with attempt tracking (max 3 attempts)
- Implement Check Deliveries for Retry system-triggered operation
- Build delivery failure path: after 3 failed attempts, transition to `failed` and pause schedule
- Add user-facing notification when schedule is paused due to delivery failures
- Integrate Audit Logger to record delivery attempts and failures

**Acceptance Criteria**
- Delivery Service creates record before async email send begins
- Email successfully sends to recipient email on first attempt
- Failed deliveries increment attempt_count and schedule retry
- After 3 failed attempts, delivery transitions to `failed` and triggering schedule pauses
- User receives notification that schedule has been paused
- Audit Logger records each delivery attempt, success, and permanent failure
- Check Deliveries for Retry returns deliveries ready for retry within time window
- Delivery records show attempt history with timestamps and error messages

## Phase 5: PDF Export and Full Integration

**Goal**
Complete the export feature with PDF generation and comprehensive testing across all workflows.

**Scope**
- Implement PDF export format alongside CSV
- Extend one-off export and schedule creation to support PDF selection
- Implement Size Validator for PDF files (same 50 MB limit)
- Build end-to-end validation covering all four major workflows
- Documentation for operators on feature flag administration and troubleshooting

**Acceptance Criteria**
- Users can select PDF format in one-off and schedule creation flows
- PDF generation passes Size Validator with correct file sizing
- All four workflows (one-off, schedule create, scheduled generate+deliver, pause+resume) function correctly
- Audit logs show complete audit trail for representative workflows
- Feature flag can be disabled/enabled and properly gates all export operations
- Operator guide documents feature flag controls and troubleshooting export failures
