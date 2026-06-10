# Technical Approach: Scheduled Report Exports

## Architecture Outline

The export system comprises four interconnected subsystems:

1. **Export Request Handler** — synchronous interface that receives one-off and scheduled export requests, validates inputs, enforces permissions, and enqueues work for asynchronous processing.

2. **Export Generation Engine** — asynchronous worker pool that renders reports in the requested format (CSV/PDF), applies row-level permission filtering, validates output size, and emits events to the audit log and delivery system.

3. **Scheduled Export Manager** — manages the lifecycle of recurring export schedules, executes scheduled triggers at configured frequencies, manages pause/resume state, and orchestrates retries after failures.

4. **Delivery and Retry System** — handles email delivery of generated exports, implements the 3-attempt retry policy with intelligent backoff, pauses schedules on final failure, and maintains run history records.

The Export Request Handler is the primary API surface. It accepts both one-off and scheduled export requests, validates row-level permissions at request time, and delegates rendering and delivery to asynchronous subsystems. The Export Generation Engine is the compute boundary — all heavy lifting (report rendering, data filtering, format conversion) happens here and can be parallelized across a worker pool. The Scheduled Export Manager is a stateful orchestrator that reads schedule definitions from persistent storage, triggers exports at the configured cadence, and mutates schedule state (pause, resume, last_run) based on delivery outcomes. The Delivery and Retry System is the durability boundary — it maintains an authoritative record of delivery attempts, implements backoff and retry logic, and coordinates with the Scheduled Export Manager to pause failing schedules.

These subsystems are loosely coupled through message queues (export generation tasks, delivery receipts) and a shared data store (schedules, run history, audit log).

## Domain Model

### Core Entities

**Report** — the source dataset to be exported. Reports are identified by ID, owned by a workspace, and enforce row-level permission filtering via a permission evaluator function. A report may be any dataset in the system (customer list, sales data, etc.) and is not specific to the export module.

**Export Request** — a single request to export a report, either one-off or as part of a scheduled series. Has an ID, references a Report, specifies a format (CSV/PDF), carries the requesting user's ID (for permission evaluation), and records creation timestamp and requesting IP for audit purposes. One-off requests are generated immediately; scheduled requests spawn periodic Export Requests via the Scheduled Export Manager.

**Scheduled Export** — the definition of a recurring export series. Contains schedule ID, references a Report, specifies frequency (daily/weekly), lists delivery email(s), references a schedule owner (user ID), records creation and last modification timestamps, and maintains state (active/paused). The schedule owner is the only user who receives deliveries and can pause/resume the schedule.

**Export Generation Task** — the work item enqueued for asynchronous rendering. References an Export Request, includes format and permission context, and is processed by the Export Generation Engine. Serializable into message queues.

**Export Delivery Attempt** — a record of one delivery attempt (email send). References an Export Request, records attempt number (1–3), delivery email address, timestamp, and outcome (success/failure). Failures record the reason (network error, bounce, etc.). Delivery attempts are immutable once recorded.

**Schedule Run** — a point-in-time record of a single scheduled export execution. References a Scheduled Export, records trigger time, Export Request ID (if generated), and links to associated Delivery Attempts. Schedule runs are retained for 30 days.

**Permission Context** — the set of row-level permissions held by a user at request time. Captured at Export Request creation, applied by the Export Generation Engine to filter rows during rendering. Enables asynchronous processing while preserving permission semantics.

### Relationships

- Report ← Export Request → Scheduled Export (an Export Request may originate from either one-off submission or a Scheduled Export trigger)
- Export Request → Export Generation Task (1-to-1 at enqueue time, 1-to-1 at completion)
- Export Request → Delivery Attempt (1-to-many, up to 3 Delivery Attempts per Export Request)
- Scheduled Export → Schedule Run (1-to-many, newest 30 retained)
- Schedule Run → Delivery Attempt (1-to-many, links Delivery Attempts associated with a scheduled export run)

## Key Workflows

### Workflow 1: One-Off Export Request

1. User submits an export request (report ID, format) via the Export Request Handler.
2. Request Handler validates the requesting user's row-level permissions against the target report. Fails immediately if the user has no access.
3. Request Handler creates an Export Request record with the requesting user's permission context.
4. Request Handler enqueues an Export Generation Task and immediately returns a receipt (request ID, expected completion time).
5. Export Generation Engine dequeues the task, renders the report in the requested format, applies the permission context to filter rows, and validates the output size.
6. If output exceeds 50 MB, the task fails gracefully and records a size-exceeded error in the Export Request status.
7. If rendering succeeds, the Export Generation Engine stores the artifact (in blob storage or similar) and emits a GenerationComplete event.
8. Delivery and Retry System receives the GenerationComplete event and attempts delivery via email.
9. Audit log records: ExportRequested, ExportGenerationStarted, ExportGenerationCompleted (or ExportGenerationFailed), and ExportDeliveryAttempted.

### Workflow 2: Create Scheduled Export

1. User submits a scheduled export request (report ID, format, frequency, delivery email) via the Export Request Handler.
2. Request Handler validates the requesting user's row-level permissions against the target report. Fails immediately if the user has no access.
3. Request Handler creates a Scheduled Export record with the user as owner, sets initial state to active, and records the delivery email and frequency.
4. Request Handler returns the schedule ID and confirmation to the user.
5. Audit log records: ScheduledExportCreated.

### Workflow 3: Scheduled Export Trigger and Delivery

1. Scheduled Export Manager reads all active Scheduled Export records from the data store.
2. At the configured trigger time (daily or weekly), the Manager generates an Export Request with the schedule owner's permission context.
3. Export Request is enqueued for generation as per Workflow 1, with a reference back to the parent Scheduled Export.
4. Export Generation Engine renders the report and emits GenerationComplete.
5. Delivery and Retry System dequeues the GenerationComplete event and attempts email delivery to the configured email address.
6. On success, the Delivery Attempt is marked successful, a Schedule Run is created, and Audit log records: ScheduledExportDelivered.
7. On failure, the Delivery and Retry System schedules a retry with intelligent backoff.
8. After the third failed attempt, the Scheduled Export is automatically paused, and Audit log records: ScheduledExportPausedOnDeliveryFailure.

### Workflow 4: Pause/Resume Schedule

1. Schedule owner submits a pause or resume request to the Export Request Handler, specifying the schedule ID.
2. Request Handler updates the Scheduled Export state (active → paused or paused → active).
3. Audit log records: ScheduledExportPaused or ScheduledExportResumed.
4. If resuming, the Scheduled Export Manager will trigger the next export at the next scheduled time.

### Workflow 5: View Schedule Run History

1. Schedule owner queries the Export Request Handler for run history of a specific Scheduled Export.
2. Request Handler returns the 30 most recent Schedule Run records, sorted by recency, each with:
   - Trigger timestamp
   - Export status (generated successfully, failed, etc.)
   - Associated Delivery Attempt records (attempt number, outcome, reason if failed)
3. User interface renders the history with sufficient detail to understand delivery status and retry outcomes.

### Workflow 6: Admin Disable Export Functionality

1. Admin accesses the admin control panel and sets export_enabled = false for the workspace.
2. Export Request Handler checks this flag before accepting any export request (one-off or scheduled).
3. If disabled, Export Request Handler returns an error: "Export functionality is disabled for this workspace."
4. Scheduled exports that were already created remain in the data store but are not triggered.
5. Audit log records: ExportFunctionalityDisabled.

## Contracts

### Export Request Handler API

**POST /exports/one-off**
- Input: `{ report_id: string, format: 'csv' | 'pdf', user_id: string }`
- Output: `{ request_id: string, status: 'queued' | 'error', error?: string }`
- Preconditions: User must have row-level access to the report; exports must be enabled
- Postconditions: Export Generation Task enqueued if valid; audit log entry created

**POST /exports/scheduled**
- Input: `{ report_id: string, format: 'csv' | 'pdf', frequency: 'daily' | 'weekly', delivery_email: string, user_id: string }`
- Output: `{ schedule_id: string, status: 'created' | 'error', error?: string }`
- Preconditions: User must have row-level access to the report; exports must be enabled
- Postconditions: Scheduled Export record created; audit log entry created

**PUT /exports/scheduled/{schedule_id}/pause**
- Input: `{ schedule_id: string, user_id: string }`
- Output: `{ status: 'paused' | 'error' }`
- Preconditions: Calling user must be the schedule owner
- Postconditions: Scheduled Export state set to paused; audit log entry created

**PUT /exports/scheduled/{schedule_id}/resume**
- Input: `{ schedule_id: string, user_id: string }`
- Output: `{ status: 'resumed' | 'error' }`
- Preconditions: Calling user must be the schedule owner; schedule must be in paused state
- Postconditions: Scheduled Export state set to active; audit log entry created

**GET /exports/scheduled/{schedule_id}/history**
- Input: `{ schedule_id: string, user_id: string }`
- Output: `{ runs: [{ trigger_time: timestamp, status: string, delivery_attempts: [{ attempt_number: int, outcome: 'success' | 'failed', reason?: string, timestamp: timestamp }] }] }`
- Preconditions: Calling user must be the schedule owner
- Postconditions: None (read-only)

**POST /admin/exports/disable**
- Input: `{ workspace_id: string, enabled: boolean }`
- Output: `{ status: 'updated' | 'error' }`
- Preconditions: Calling user must be a workspace admin
- Postconditions: Workspace export_enabled flag updated; audit log entry created

### Export Generation Engine Interface

**Interface: ExportGenerator**
- Method: `generate(request: ExportRequest, permission_context: PermissionContext, format: 'csv' | 'pdf') → ExportArtifact | GenerationError`
- Responsibility: Render the report in the specified format, apply row-level permission filtering, validate output size, and return either an artifact (with storage location and size) or a detailed error.
- Contracts: Must be thread-safe, idempotent (same inputs produce same output), and log all processing steps for audit.

### Scheduled Export Manager Interface

**Interface: ScheduleOrchestrator**
- Method: `trigger_active_schedules() → void`
- Responsibility: Enumerate active schedules, generate Export Requests for those due, and enqueue Export Generation Tasks.
- Contracts: Must be idempotent (safe to call multiple times); calls are logged for audit.

**Interface: SchedulePauseManager**
- Method: `pause_on_delivery_failure(schedule_id: string) → void`
- Responsibility: Set schedule state to paused after third delivery failure.
- Contracts: Idempotent; audit log entry created.

### Delivery and Retry System Interface

**Interface: DeliveryOrchestrator**
- Method: `deliver(export_artifact: ExportArtifact, delivery_email: string, request_id: string, attempt_number: int) → DeliveryResult`
- Responsibility: Send the export via email, record the attempt, and return success or failure reason.
- Contracts: Idempotent at the delivery attempt level (same request_id + attempt_number always produces the same result).

**Interface: RetryCoordinator**
- Method: `schedule_retry(request_id: string, attempt_number: int) → void`
- Responsibility: Schedule the next retry attempt with intelligent backoff if attempt_number < 3; otherwise notify SchedulePauseManager.
- Contracts: Idempotent; all retries are logged.

### Audit Log Contract

**Audit events** recorded for all state transitions and user actions:
- ExportRequested(request_id, report_id, user_id, format, timestamp, requesting_ip)
- ExportGenerationStarted(request_id, timestamp)
- ExportGenerationCompleted(request_id, artifact_size, timestamp)
- ExportGenerationFailed(request_id, error_reason, timestamp)
- ExportDeliveryAttempted(request_id, attempt_number, delivery_email, outcome, reason_if_failed, timestamp)
- ScheduledExportCreated(schedule_id, report_id, owner_id, frequency, delivery_email, timestamp)
- ScheduledExportPaused(schedule_id, user_id, timestamp)
- ScheduledExportResumed(schedule_id, user_id, timestamp)
- ScheduledExportPausedOnDeliveryFailure(schedule_id, request_id, timestamp)
- ExportFunctionalityDisabled(workspace_id, enabled: boolean, admin_id, timestamp)

All audit events include a workspace context to enable workspace-level filtering and compliance reporting.
