# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature consists of the following components:

1. **Export Service** — handles synchronous one-off export generation and asynchronous scheduled export generation
2. **Scheduling Engine** — manages recurring export schedules, state transitions (active/paused), and triggering
3. **Delivery Service** — handles email delivery with retry logic and failure tracking
4. **Audit Logger** — records all export-related events for compliance and debugging
5. **Permission Enforcer** — validates row-level access at export time to ensure data confidentiality
6. **Size Validator** — enforces the 50 MB export size limit
7. **Feature Flag Manager** — gates the entire export functionality

The export request flow branches at the user's choice: one-off exports are generated synchronously and returned to the user immediately, while scheduled exports are queued as asynchronous tasks that execute on a defined schedule and are delivered via email.

## Domain Model

### Export Schedule
- `id` — unique identifier
- `owner_id` — user who created and owns the schedule
- `report_id` — the report being exported
- `format` — export format (CSV or PDF)
- `frequency` — recurrence pattern (daily or weekly)
- `state` — current state: `active` or `paused`
- `created_at` — schedule creation timestamp
- `last_run_at` — timestamp of the most recent export generation
- `created_by_id` — audit trail

### Export Job
- `id` — unique identifier
- `schedule_id` — the schedule that triggered this job (null for one-off exports)
- `status` — job status: `pending`, `generating`, `generated`, `delivery_pending`, `delivered`, `failed`
- `created_at` — job creation timestamp
- `completed_at` — job completion timestamp
- `generated_at` — when the export file was finalized
- `file_path` — location of the generated export file
- `file_size` — size of the export in bytes
- `error_message` — if status is `failed`, the reason

### Export Delivery
- `id` — unique identifier
- `job_id` — the export job being delivered
- `recipient_email` — destination email address
- `status` — delivery status: `pending`, `sent`, `failed`
- `attempted_at` — timestamp of last delivery attempt
- `attempt_count` — number of delivery attempts (1–3)
- `error_message` — failure reason if status is `failed`

### Audit Log Entry
- `id` — unique identifier
- `event_type` — type of event (export_requested, export_generated, delivery_attempted, delivery_failed, schedule_paused, schedule_resumed, schedule_created, etc.)
- `user_id` — the user who triggered the action (null for system-triggered events)
- `resource_type` — the entity type (schedule, job, or delivery)
- `resource_id` — the entity being logged
- `timestamp` — when the event occurred
- `details` — structured data about the event (report_id, file_size, error codes, etc.)

## Key Workflows

### One-Off Export Workflow
1. User clicks "Export" on a report, selects a format (CSV or PDF)
2. Export Service validates the user's row-level permissions on the report
3. Export Service checks the feature flag; if disabled, returns error
4. Export Service generates the export asynchronously (non-blocking)
5. User immediately receives a job ID for polling or later retrieval
6. Export Service checks the generated file size against the 50 MB limit
7. If size exceeds limit, the job fails with a user-facing error and is not persisted beyond status
8. If size is within limits, the file is stored and a download link is provided
9. Audit Logger records the export request and completion

### Schedule Creation Workflow
1. User navigates to "Manage Exports" and clicks "Create Schedule"
2. User selects a report, export format, and recurrence (daily or weekly)
3. System validates the user can access the report
4. System checks the feature flag; if disabled, returns error
5. Schedule is created in `active` state with the user as owner
6. Audit Logger records the schedule creation
7. Scheduling Engine enqueues the first export job for the next scheduled time

### Scheduled Export Generation and Delivery Workflow
1. Scheduling Engine checks which schedules are due (based on frequency)
2. For each active schedule due to run:
   a. Creates an Export Job in `pending` state
   b. Export Service generates the export asynchronously
   c. Size Validator checks the generated file against the 50 MB limit
   d. If size exceeds limit, job fails and schedule is paused with an error state
   e. If size is acceptable, job transitions to `generated` state
   f. Audit Logger records export generation
3. Delivery Service picks up jobs in `generated` state
4. Delivery Service sends email to schedule owner with a download link or attachment
5. On successful send, Delivery record transitions to `sent` state
6. Audit Logger records delivery success
7. Scheduling Engine enqueues the next job based on the schedule's frequency

### Delivery Retry Workflow
1. Delivery Service attempts to send email
2. If delivery fails, Delivery Service increments `attempt_count`
3. If `attempt_count` < 3:
   a. Schedule the next retry
   b. Delivery status remains `pending`
   c. Audit Logger records the failed attempt
4. If `attempt_count` == 3:
   a. Delivery status transitions to `failed`
   b. Schedule transitions to `paused` state
   c. User receives a notification that their schedule has been paused
   d. Audit Logger records permanent failure and schedule pause

### Pause and Resume Workflow
1. Schedule owner navigates to their schedules
2. Owner clicks "Pause" on a schedule, triggering state transition from `active` to `paused`
3. Scheduling Engine stops enqueueing new export jobs for that schedule
4. Audit Logger records the pause action
5. Owner can later click "Resume" to transition back to `active` state
6. Scheduling Engine enqueues the next job based on the updated schedule

### Run History Retrieval Workflow
1. Schedule owner views a schedule's details page
2. System retrieves all Export Jobs linked to that schedule created in the last 30 days
3. For each job, the system retrieves linked Delivery records
4. System displays a table with timestamp, status, and delivery outcome
5. User can click into individual jobs to see error messages and retry history

## Contracts

### Export Service

**Generate One-Off Export**
- Input: `report_id`, `user_id`, `format` (CSV or PDF)
- Output: `job_id` for tracking
- Side effects: Creates Export Job, enqueues asynchronous generation task
- Errors: Feature flag disabled, user lacks permission, report not found
- Guarantees: Job is created before async generation begins; user gets immediate feedback

**Generate Scheduled Export**
- Input: `schedule_id`
- Output: `job_id`
- Side effects: Creates Export Job, enqueues asynchronous generation task
- Errors: Schedule not found, schedule is paused
- Guarantees: Idempotent (subsequent calls with same schedule_id in same batch do not create duplicates)

**Validate Export Size**
- Input: `file_path`, `max_size_bytes`
- Output: Boolean indicating whether the file passes the size check
- Errors: File not found
- Guarantees: Deterministic; always makes the same decision for the same file

### Scheduling Engine

**Create Schedule**
- Input: `user_id`, `report_id`, `format`, `frequency` (daily or weekly)
- Output: `schedule_id`
- Side effects: Inserts Schedule record, enqueues first export job
- Errors: Feature flag disabled, user lacks permission, invalid frequency
- Guarantees: Schedule is persisted before first job is enqueued

**Pause Schedule**
- Input: `schedule_id`, `user_id` (for authorization)
- Output: Updated schedule record
- Side effects: Transitions state to `paused`, stops future job enqueueing
- Errors: Schedule not found, user is not owner, schedule already paused
- Guarantees: No new jobs are created for paused schedules after this call returns

**Resume Schedule**
- Input: `schedule_id`, `user_id`
- Output: Updated schedule record
- Side effects: Transitions state to `active`, enqueues next job based on frequency
- Errors: Schedule not found, user is not owner, schedule not paused
- Guarantees: Next job is enqueued after this call returns

**Check Due Schedules**
- Input: None (system-triggered)
- Output: List of schedule IDs due for generation
- Side effects: None
- Errors: Database unavailable
- Guarantees: Returns consistent results across multiple calls in the same minute

### Delivery Service

**Deliver Export**
- Input: `job_id`, `recipient_email`
- Output: `delivery_id`
- Side effects: Creates Delivery record, enqueues email send task
- Errors: Job not found, job not in `generated` state
- Guarantees: Delivery record is created before async send begins

**Retry Delivery**
- Input: `delivery_id`
- Output: Updated delivery record
- Side effects: Increments attempt count, schedules next retry or marks as permanently failed
- Errors: Delivery not found, max attempts exceeded
- Guarantees: Exactly one additional send attempt is scheduled per call

**Check Deliveries for Retry**
- Input: None (system-triggered)
- Output: List of delivery IDs ready for retry
- Side effects: None
- Errors: Database unavailable
- Guarantees: Returns consistent results across polling windows

### Permission Enforcer

**Check Row Access**
- Input: `user_id`, `report_id`
- Output: Boolean indicating whether user can export the report
- Side effects: None
- Errors: Report not found, user not found
- Guarantees: Deterministic; uses the same permission rules as the UI report view

**Check Admin Disable Status**
- Input: `workspace_id`
- Output: Boolean indicating whether exports are disabled
- Side effects: None
- Errors: Workspace not found
- Guarantees: Deterministic; reflects the feature flag state at call time

### Audit Logger

**Log Event**
- Input: `event_type`, `user_id`, `resource_type`, `resource_id`, `details`
- Output: `entry_id`
- Side effects: Inserts Audit Log entry
- Errors: None (log writes should not fail requests)
- Guarantees: Fire-and-forget; does not block the triggering operation

**Retrieve Event History**
- Input: `resource_type`, `resource_id`, `days_back` (e.g., 30)
- Output: List of Audit Log entries
- Side effects: None
- Errors: Invalid parameters
- Guarantees: Returns entries in chronological order, oldest first

### Feature Flag Manager

**Is Feature Enabled**
- Input: `workspace_id` (optional; if omitted, uses global flag)
- Output: Boolean
- Side effects: None
- Errors: None
- Guarantees: Cached at request time; consistent within a single request
