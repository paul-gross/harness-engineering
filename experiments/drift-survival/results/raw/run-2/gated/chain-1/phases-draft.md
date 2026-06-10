# Scheduled Report Exports — Phase Plan

## Phase 1: Foundation and Core Domain Model

**Goal**: Establish the database schema, basic API structure, and entity models that all subsequent phases depend on.

**Scope**:
- Implement Export Schedule, Export Job, Export Delivery Attempt, and Export Run History entities
- Create database migrations for all four tables with proper relationships and indexes
- Implement repository/data access layer for CRUD operations on all entities
- Set up feature flag infrastructure (`exports_enabled`)
- Create workspace-level admin control configuration for disabling exports (`disable_exports`)
- Implement basic permission checks at the API layer (feature flag and admin overrides)
- Define and implement the audit log entity and logging interface

**Acceptance criteria**:
- Database schema is created and verified with proper foreign keys and constraints
- All four entities can be created, retrieved, updated via the data access layer
- Feature flag can be toggled and is honored by permission checks
- Admin control can be toggled and blocks all export operations when enabled
- Audit log records are created for test events and can be queried
- Unit tests cover CRUD operations and relationship integrity

## Phase 2: One-Off Export Workflow

**Goal**: Deliver a working end-to-end flow for users to trigger and download one-off exports.

**Scope**:
- Implement `POST /api/reports/{reportId}/export` endpoint that validates permissions, enqueues an Export Job, and returns jobId and statusUrl
- Implement `GET /api/export-jobs/{jobId}` endpoint for polling export status
- Implement `GET /api/export-jobs/{jobId}/download` endpoint with download authorization
- Build the Export Engine core: async job processor that fetches report definition, applies row-level permission filtering, generates CSV/PDF format, validates file size (max 50 MB), and stores file
- Implement file storage/retrieval (persistent storage layer)
- Create the Export Job processing state machine and transitions (PENDING → PROCESSING → COMPLETED/FAILED)
- Record audit log entries for export creation, completion, and failure events
- Implement error handling and error_message population in Export Job on failure

**Acceptance criteria**:
- A user can trigger a one-off CSV export and receive a jobId immediately
- The user can poll the status endpoint and see the job progress through PENDING → PROCESSING → COMPLETED
- Upon completion, the user can download the generated CSV file
- The exported file contains only rows the user has permission to view (verified with test data)
- Export files larger than 50 MB are rejected with FAILED status and error message
- Audit log records are created for export creation, completion, and failure
- One-off exports work for both CSV and PDF formats

## Phase 3: Scheduled Export Workflow and Scheduler Service

**Goal**: Enable recurring exports on defined cadences with automatic email delivery.

**Scope**:
- Implement `POST /api/schedules` endpoint that creates an Export Schedule with cadence and execution time validation
- Implement `GET /api/schedules/{scheduleId}` endpoint for retrieving schedule metadata
- Implement `POST /api/schedules/{scheduleId}/pause` and `POST /api/schedules/{scheduleId}/resume` endpoints
- Build the Scheduler Service: detects when a schedule's trigger time arrives, enqueues Export Jobs linked to the schedule, applies schedule-configured format
- Integrate with email delivery system: enqueue Export Delivery Attempts after job completion
- Implement delivery retry logic: up to 3 attempts with exponential backoff on failure
- Implement automatic schedule pause on 3 failed delivery attempts
- Record audit log entries for schedule creation, pause, resume, and delivery attempts

**Acceptance criteria**:
- A user can create a schedule (e.g., "Daily CSV at 9 AM" or "Weekly PDF on Mondays at 2 PM")
- The Scheduler Service detects and triggers schedules at their designated times
- An Export Job is enqueued when a schedule's trigger time arrives
- The Export Job is linked to the schedule via schedule_id
- Upon job completion, a delivery attempt is enqueued for the schedule owner's email
- Email delivery succeeds and Export Delivery Attempt status is marked DELIVERED
- On email delivery failure, automatic retries occur (up to 3 attempts total) with exponential backoff
- After 3 failed delivery attempts, the parent Export Schedule is automatically paused
- Schedule owner can pause/resume schedules and this takes effect immediately
- Audit log records schedule lifecycle events and all delivery attempts

## Phase 4: Export History and UI Integration

**Goal**: Provide visibility into export and delivery history so users can troubleshoot and monitor their scheduled exports.

**Scope**:
- Implement `GET /api/schedules/{scheduleId}/runs` endpoint with pagination (default limit 30) returning Export Run History
- Populate Export Run History table with aggregated job_status, delivery_status (ATTEMPTED/DELIVERED/FAILED), attempt_count, and last_attempt_at
- Extend Export Run History queries to retrieve individual Export Delivery Attempts for detailed inspection
- Implement authorization checks on all history endpoints (schedule owner only)
- Update audit logging to record all relevant events needed for history reconstruction
- Ensure all workflow events (job creation, completion, failure, delivery attempt) are queryable via history endpoints

**Acceptance criteria**:
- A schedule owner can view the last 30 export runs for their schedule
- Each run shows job status, aggregated delivery status, and timestamps
- The user can inspect individual delivery attempts to understand why delivery failed
- History data accurately reflects all workflow events (creation, processing, completion, delivery)
- Unauthorized users cannot view history for schedules they do not own
- Pagination limit parameter is respected and defaults to 30
- Audit log entries can be queried to reconstruct the complete history of any export or schedule

## Phase 5: Feature Hardening and End-to-End Testing

**Goal**: Validate the complete system across workflows, edge cases, and integration scenarios.

**Scope**:
- Write end-to-end tests covering: one-off exports, scheduled exports, delivery retries, schedule pause/resume, permission filtering, feature flag behavior, and admin disabling
- Validate row-level permission filtering in edge cases (user loses permission between schedule creation and job generation, etc.)
- Test file size validation and rejection of exports exceeding 50 MB
- Test delivery retry backoff and automatic schedule pause on failure threshold
- Test concurrent export jobs and scheduler triggers
- Validate audit log completeness and accuracy
- Test feature flag and admin control behavior in combination
- Document the complete system architecture and operational runbooks
- Perform load testing on scheduler service to verify it can handle many active schedules

**Acceptance criteria**:
- End-to-end test suite passes for all four major workflows (one-off export, scheduled export creation, trigger/delivery, pause/resume)
- Edge case tests pass: permission changes, file size limits, retry exhaustion, feature flag and admin override combinations
- Row-level permission filtering is verified to exclude rows the user cannot see in all formats (CSV and PDF)
- Concurrent export jobs do not corrupt state or fail unexpectedly
- Audit log is complete and accurately reflects all events in order
- Load test shows scheduler can handle at least 100 active schedules without degradation
- All endpoints are documented with request/response contracts and error codes
- Operational runbooks exist for monitoring, troubleshooting, and maintenance
