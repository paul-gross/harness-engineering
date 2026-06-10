# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature introduces three primary subsystems:

1. **Export Generation Engine** — handles one-off and scheduled export creation (CSV/PDF), formats data respecting row-level permissions, and enforces size limits before generation begins
2. **Scheduling Service** — manages recurring export schedules (daily/weekly), orchestrates async generation, tracks state (active/paused), and owns delivery lifecycle
3. **Delivery & Retry Handler** — delivers exports via email, implements automatic retry logic (up to 3 attempts), pauses schedules on total failure, and records all attempts in audit logs

These subsystems interact through an asynchronous job queue. The Export Generation Engine enqueues jobs; the Scheduling Service polls the queue and triggers generation at configured intervals; the Delivery & Retry Handler consumes completed exports and manages email delivery with automatic retry logic.

A feature flag (off by default) gates all entry points. Workspace-level admin settings can disable the entire feature, preventing schedule execution and rejecting new export initiation.

The Audit Log subsystem records every event: export generation requests, schedule creation/pause/resume, delivery attempts, successes, failures, and retries.

## Domain Model

### Core Entities

**Report** (existing entity, extended with export capability)
- Inherits row-level permission metadata
- Linked to Export Schedules

**Export Request** (transient, one-off)
- requesterId: user ID
- reportId: report identifier
- format: CSV | PDF
- timestamp: when requested
- status: pending | generating | completed | failed
- sizeCheckPassed: boolean (validated before generation)
- resultFileId: reference to generated file (if successful)

**Export Schedule** (persistent)
- ownerId: user ID (schedule owner)
- reportId: report identifier
- format: CSV | PDF
- frequency: DAILY | WEEKLY
- nextRunTime: ISO datetime
- isActive: boolean (pause/resume state)
- createdAt: timestamp
- lastRunId: reference to most recent export job
- maxSize: 50 MB threshold

**Export Run** (one execution of a schedule)
- scheduleId: references Export Schedule
- executionTime: when the job ran
- status: success | failed
- generatedFileSize: bytes
- deliveryMethod: email
- ownersEmail: recipient address

**Delivery Attempt** (one email send attempt)
- runId: references Export Run
- attemptNumber: 1 | 2 | 3
- sentAt: timestamp
- status: pending | delivered | failed
- errorMessage: failure reason (if applicable)

**Export History** (query surface for schedule owner)
- Aggregates Export Runs for a given schedule
- Limited to last 30 runs
- Includes delivery attempt details

**ExportFeatureConfig** (workspace-level)
- isEnabled: boolean (admin-controlled)
- appliesTo: all users when disabled

## Key Workflows

### One-Off Export Workflow

1. User initiates export from report UI (format: CSV or PDF)
2. Feature flag and workspace config checked — return error if disabled
3. Row-level permission filter applied to report rows
4. Size validation: reject if filtered dataset > 50 MB (check before generation)
5. Async Export Request created and enqueued
6. Export Generation Engine processes job:
   - Generates file in requested format
   - Stores file reference
   - Transitions to completed state
7. User can download file from UI (with permission re-check at download)
8. Audit log records: export_initiated, export_completed (or export_failed)

### Schedule Creation Workflow

1. User opens export schedule dialog for a report
2. Feature flag and workspace config checked — return error if disabled
3. User selects format (CSV/PDF) and frequency (DAILY/WEEKLY)
4. Export Schedule created and persisted
5. Next run time calculated from current time and frequency
6. Schedule enqueued for async execution
7. Audit log records: schedule_created

### Scheduled Export Execution Workflow

1. Scheduling Service polls for due schedules (nextRunTime <= now)
2. Feature flag and workspace config rechecked — skip execution if disabled
3. Permission/data state validated (user still has access, report still exists)
4. Size validation: reject if filtered dataset > 50 MB
5. Export Run created with status: pending
6. Export Generation Engine processes job (same as one-off, but linked to schedule)
7. On completion, Delivery & Retry Handler enqueues delivery
8. Audit log records: export_generated, export_delivered (or delivery_failed)
9. nextRunTime updated: if success, schedule next run; if all 3 deliveries fail, set isActive = false and audit schedule_paused

### Delivery & Retry Workflow

1. Delivery Handler receives completed Export Run
2. Constructs email with export file/link for delivery to schedule owner
3. Attempts to send email to schedule owner
4. On success: Delivery Attempt marked delivered, triggers nextRunTime calculation
5. On failure (first or second attempt):
   - Retry with automatic backoff
   - Create new Delivery Attempt with attemptNumber incremented
   - Enqueue for later retry
6. On failure (third attempt):
   - Mark Delivery Attempt as failed
   - Transitions Export Run to failed
   - Sets Export Schedule isActive = false (auto-pause)
   - Audit log records: schedule_auto_paused

### Schedule Pause/Resume Workflow

1. User requests pause on an Export Schedule they own
2. Authorization check: confirm user is schedule owner
3. Set isActive = false
4. Current pending jobs can complete, but no new jobs enqueued
5. Audit log records: schedule_paused
6. User requests resume on same schedule
7. Recalculate nextRunTime from current time and frequency
8. Set isActive = true
9. Audit log records: schedule_resumed

### Export History Query Workflow

1. User requests history for a schedule they own
2. Authorization check: confirm user is schedule owner
3. Fetch last 30 Export Runs for that schedule, ordered by executionTime desc
4. For each run, include delivery attempt details and file metadata (size, format, timestamp)
5. Return as paginated list

## Contracts

### Export Generation Service

**initiate_export(requesterId: UUID, reportId: UUID, format: "CSV"|"PDF") -> ExportRequest**
- Validates feature flag and workspace config
- Checks requestor has report view permission
- Performs row-level permission filter
- Validates size threshold before queuing
- Returns export request with initial status
- Raises ExportDisabledException if feature is off or admin-disabled

**generate_export(exportRequestId: UUID) -> {fileId: UUID, sizeBytes: int, completedAt: ISO8601}**
- Processes queued export
- Respects row-level permissions (re-applied at generation time)
- Returns file reference and metadata on success
- Raises FileSizeExceeded if post-filter dataset exceeds 50 MB

### Schedule Management Service

**create_schedule(ownerId: UUID, reportId: UUID, format: "CSV"|"PDF", frequency: "DAILY"|"WEEKLY") -> ExportSchedule**
- Validates feature flag and workspace config
- Checks owner has report view permission
- Initializes nextRunTime based on frequency
- Returns schedule object
- Raises ExportDisabledException if feature is off or admin-disabled

**pause_schedule(scheduleId: UUID, requesterId: UUID) -> ExportSchedule**
- Validates requesterId is schedule owner
- Sets isActive = false
- Returns updated schedule

**resume_schedule(scheduleId: UUID, requesterId: UUID) -> ExportSchedule**
- Validates requesterId is schedule owner
- Sets isActive = true
- Recalculates nextRunTime
- Returns updated schedule

**list_schedules(ownerId: UUID) -> [ExportSchedule]**
- Returns all schedules owned by user

### Scheduling & Execution Service

**enqueue_scheduled_export(scheduleId: UUID) -> ExportRun**
- Validates schedule isActive = true
- Validates feature flag and workspace config
- Re-validates owner has report view permission
- Validates size threshold before queuing
- Creates ExportRun with status pending
- Returns run reference
- Raises ScheduleDisabled or ExportDisabled if conditions not met

**tick() -> void** (polling entry point)
- Runs periodically to check for due schedules
- Queries schedules where nextRunTime <= now and isActive = true
- Calls enqueue_scheduled_export for each due schedule
- Updates nextRunTime for successful queues

### Delivery Service

**enqueue_delivery(exportRunId: UUID) -> DeliveryAttempt**
- Creates Delivery Attempt with attemptNumber = 1
- Enqueues for immediate delivery
- Returns attempt reference

**deliver_export(exportRunId: UUID, attemptNumber: 1|2|3) -> {status: "delivered"|"failed", errorMessage?: string}**
- Sends email to schedule owner with export file/link
- On success: returns status delivered
- On failure, attemptNumber < 3: enqueues retry, returns status failed
- On failure, attemptNumber = 3: calls pause_schedule, returns status failed
- Raises ScheduleOwnerNotFound if user context invalid

**retry_delivery(exportRunId: UUID) -> void** (background task)
- Triggered by scheduled retry timer
- Fetches latest Delivery Attempt
- Calls deliver_export with attemptNumber + 1

### Export History Service

**get_export_history(scheduleId: UUID, requesterId: UUID, limit: int = 30) -> [ExportRun]**
- Validates requesterId is schedule owner
- Fetches up to `limit` ExportRuns for scheduleId, ordered by executionTime desc
- Includes delivery attempt details for each run
- Returns paginated list with metadata

### Audit Log Service

**log_event(eventType: string, actorId: UUID, resourceId: UUID, details: object) -> void**
- Records all events: export_initiated, export_generated, export_completed, export_failed, schedule_created, schedule_paused, schedule_resumed, delivery_attempted, delivery_succeeded, delivery_failed, schedule_auto_paused
- Persists to audit log with timestamp and context
- No return value (fire-and-forget)

### Admin Configuration Service

**set_export_enabled(isEnabled: boolean) -> ExportFeatureConfig**
- Admin-only operation
- Sets workspace-wide feature control
- Returns updated config
- Audit log records: export_feature_disabled (or enabled)

**get_export_config() -> ExportFeatureConfig**
- Returns current workspace export settings
- Public read (no auth required for feature flag checks)

### Feature Flag Service

**is_feature_enabled(flagName: "scheduled_exports") -> boolean**
- Checks feature flag state
- Off by default at launch
- Used by all entry points to guard behavior
