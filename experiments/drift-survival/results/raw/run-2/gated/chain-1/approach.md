# Scheduled Report Exports — Technical Approach

## Architecture Outline

The export system consists of four primary components:

1. **Export API layer** — HTTP endpoints for triggering one-off exports and managing scheduled exports
2. **Export engine** — async service responsible for generating exports in the requested format (CSV/PDF), applying row-level permission filtering, and managing the export lifecycle
3. **Scheduler service** — manages recurring export schedules, triggers exports at the designated cadence, and tracks delivery outcomes
4. **Audit and persistence layer** — records all export events and maintains export schedule state, delivery history, and retry metadata

The architecture emphasizes asynchronous processing: one-off exports and scheduled exports both queue work to the export engine rather than blocking the request path. The scheduler service polls or reacts to scheduled times and enqueues export jobs. The export engine processes jobs serially, applies permission filtering during generation, and invokes the email delivery system.

A feature flag gates the entire capability at the API layer. Workspace-level admin controls bypass the flag and allow admins to disable exports entirely, which removes UI export options and prevents all export operations.

## Domain Model

### Core Entities

**Export Schedule**
- ID (unique identifier)
- report_id (which report is exported)
- owner_user_id (the requesting user who will receive deliveries)
- cadence (DAILY or WEEKLY)
- execution_day_of_week (if weekly; nullable if daily)
- execution_time (time of day, e.g., 09:00 UTC)
- status (ACTIVE, PAUSED)
- created_at
- updated_at

**Export Job**
- ID (unique identifier)
- schedule_id (references an Export Schedule; null if one-off export)
- report_id
- requesting_user_id (the user who triggered or owns the export)
- format (CSV or PDF)
- status (PENDING, PROCESSING, COMPLETED, FAILED)
- file_url (location of generated file; null if not yet generated)
- file_size_bytes (null if not yet generated)
- created_at
- started_at (null if not yet started)
- completed_at (null if not yet completed)
- error_message (null if successful)

**Export Delivery Attempt**
- ID
- export_job_id
- recipient_email
- attempt_number (1, 2, or 3)
- status (PENDING, DELIVERED, FAILED)
- error_message (null if delivered)
- attempted_at
- delivered_at (null if not delivered)

**Export Run History** (for UI transparency)
- schedule_id
- export_job_id
- job_status
- delivery_status (aggregated from all attempts)
- last_attempt_at
- created_at

### Relationships and Invariants

- One Export Schedule can generate many Export Jobs (one per trigger)
- One Export Job can have multiple Export Delivery Attempts (up to 3 retries)
- An Export Schedule status of PAUSED prevents new jobs from being created
- An Export Job status of FAILED with 3 failed delivery attempts automatically triggers the parent Export Schedule to PAUSED
- Row-level permissions are evaluated at job generation time; the set of accessible rows is frozen in the job record (or applied during file generation)

## Key Workflows

### One-Off Export Workflow

1. User initiates export from the report UI (CSV or PDF format)
2. API validates:
   - Feature flag is enabled
   - Workspace has not disabled exports
   - User has permission to view the report
3. API enqueues an Export Job with status PENDING
4. API returns immediately with a job ID and status URL (no blocking)
5. Export engine picks up the job:
   - Fetches the report definition and the user's row-level permissions
   - Generates the export file (CSV or PDF) with only rows the user can see
   - Validates file size; rejects if > 50 MB
   - Stores file in persistent storage
   - Updates Export Job status to COMPLETED and records file_url
6. API records an audit log entry: user, report, export format, timestamp
7. User polls status URL or receives notification when export is ready for download

### Scheduled Export Workflow — Creation

1. User navigates to report settings and creates a schedule (e.g., "Email me CSV every Monday at 9 AM")
2. API validates:
   - Feature flag is enabled
   - Workspace has not disabled exports
   - User has permission to view the report
   - Cadence and time are valid
3. API creates an Export Schedule record with status ACTIVE and owner_user_id = requesting user
4. API records an audit log entry
5. Scheduler service discovers the new schedule (via polling or event) and marks it ready for triggering

### Scheduled Export Workflow — Trigger and Delivery

1. Scheduler service detects that a schedule's trigger time has arrived
2. Scheduler enqueues an Export Job (linked to the schedule) with the default format (CSV, or configurable per schedule)
3. Export engine processes the job (same as one-off export, but delivery recipient is the schedule owner)
4. Upon completion, export engine enqueues a delivery attempt:
   - Recipient: schedule owner's email
   - Attempt number: 1
   - Status: PENDING
5. Email delivery system attempts to send the file
6. If delivery succeeds:
   - Export Delivery Attempt status → DELIVERED
   - Export Job status → COMPLETED
7. If delivery fails:
   - Export Delivery Attempt status → FAILED
   - Export engine checks: attempt_number < 3?
     - If yes: enqueue another attempt (attempt_number + 1) with exponential backoff
     - If no: Export Job status → FAILED, and automatically pause the parent Export Schedule

### Schedule Pause/Resume

1. Schedule owner clicks "Pause" on the schedule
   - API updates Export Schedule status → PAUSED
   - No new jobs are enqueued while paused
   - Existing jobs continue to completion
2. Schedule owner clicks "Resume"
   - API updates Export Schedule status → ACTIVE
   - Scheduler resumes triggering on the configured cadence

### Export History Retrieval

1. User views schedule details page
2. API queries Export Run History for the past 30 runs
3. UI displays: job status, delivery status (attempted/delivered/failed), timestamps, retry counts
4. User can inspect individual delivery attempts to understand failures

## Contracts

### Export API Endpoints

**POST /api/reports/{reportId}/export**
- Request body: `{ format: "CSV" | "PDF" }`
- Response: `{ jobId: string, status: "PENDING", statusUrl: string }`
- Behavior: Enqueue one-off export job
- Auth: Requires read permission on the report
- Feature gate: Fails with 403 if feature flag disabled or workspace disables exports

**GET /api/export-jobs/{jobId}**
- Response: `{ id: string, status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED", fileUrl?: string, fileSize?: number, errorMessage?: string }`
- Behavior: Poll export status

**GET /api/export-jobs/{jobId}/download**
- Response: File stream (CSV or PDF)
- Behavior: Download completed export file
- Auth: Only job owner can download

**POST /api/schedules**
- Request body: `{ reportId: string, format: "CSV" | "PDF", cadence: "DAILY" | "WEEKLY", executionTime: string, executionDayOfWeek?: number }`
- Response: `{ scheduleId: string, status: "ACTIVE" }`
- Behavior: Create export schedule
- Auth: Requires read permission on the report
- Feature gate: Fails with 403 if feature flag disabled or workspace disables exports

**GET /api/schedules/{scheduleId}**
- Response: `{ id: string, reportId: string, cadence: string, executionTime: string, status: "ACTIVE" | "PAUSED", ownerId: string }`
- Behavior: Retrieve schedule metadata

**POST /api/schedules/{scheduleId}/pause**
- Response: `{ status: "PAUSED" }`
- Behavior: Pause schedule
- Auth: Only schedule owner

**POST /api/schedules/{scheduleId}/resume**
- Response: `{ status: "ACTIVE" }`
- Behavior: Resume schedule
- Auth: Only schedule owner

**GET /api/schedules/{scheduleId}/runs**
- Query params: `limit=30` (default)
- Response: `{ runs: [{ jobId: string, reportId: string, jobStatus: string, deliveryStatus: string, attemptCount: number, lastAttemptAt: string }] }`
- Behavior: Retrieve last N export runs for the schedule
- Auth: Only schedule owner

### Export Engine Interface

**EnqueueExportJob(jobSpec)**
- Input: jobSpec = `{ reportId, userId, format, scheduleId? }`
- Output: jobId
- Behavior: Create pending export job and enqueue for processing

**ProcessExportJob(jobId)**
- Input: jobId
- Output: success/failure with file metadata or error
- Behavior: Generate export file with user's row-level permissions applied, validate size, store file
- Side effects: Update job status, record audit log

**EnqueueDeliveryAttempt(jobId, recipientEmail, attemptNumber)**
- Input: jobId, recipient email, retry attempt number
- Output: deliveryAttemptId
- Behavior: Create delivery attempt record and enqueue for email sending

### Audit Log Contract

Every export event records:
- user_id
- action: "export_created" | "export_completed" | "export_failed" | "schedule_created" | "schedule_paused" | "schedule_resumed" | "delivery_attempted" | "delivery_succeeded" | "delivery_failed"
- report_id
- schedule_id (if applicable)
- job_id (if applicable)
- metadata: `{ format?, cadence?, attemptNumber?, errorMessage? }`
- timestamp

### Feature Flag and Admin Controls

**Feature flag**: `exports_enabled` (boolean, default false)
- Controls API availability
- When disabled, all export endpoints return 403 Forbidden

**Workspace admin control**: `disable_exports` (boolean, default false)
- When enabled, overrides feature flag and prevents all export operations
- UI does not render export buttons or schedule management UI
- Existing schedules remain in the database but are not triggered

### Permission Evaluation

**Row-level permission filtering** (applied during export generation):
- Query the user's permission context (e.g., which customers, regions, or data scopes they can view)
- Generate the export file containing only rows matching those scopes
- This ensures the export file matches what the user sees in the interactive UI
