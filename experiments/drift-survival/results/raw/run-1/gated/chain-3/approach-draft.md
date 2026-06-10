# Technical Approach: Scheduled Report Exports

## Architecture outline

The feature introduces an **Export Service** as a new backend component, sitting alongside the existing Reporting module. The Export Service is responsible for both on-demand and scheduled export generation, and it integrates with the following existing and new components:

- **Reporting module** — the Export Service calls into the Reporting module to fetch report data, applying the requesting user's row-level permission filter before generating any output. The Reporting module is not modified to be export-aware; the Export Service is a consumer of its query interface.
- **Export worker** — an asynchronous background worker (or queue consumer) that generates the actual CSV/PDF artifact. The Export Service enqueues a job; the worker picks it up, streams report data through a format renderer (CSV or PDF), stores the resulting artifact, and updates job state. This decouples export generation from the HTTP response path so interactive report viewing is never blocked.
- **Export storage** — a temporary object store (e.g. S3-compatible bucket or local blob store) where generated artifacts are held until delivered or discarded. Artifacts are not retained permanently.
- **Scheduler** — a new component that owns the schedule registry and drives recurring delivery. On each tick (at minimum daily granularity), the Scheduler evaluates all active schedules whose next-delivery time has passed, enqueues an Export job per schedule, and updates the schedule's next-delivery timestamp.
- **Delivery Service** — sends the generated artifact to the schedule owner via email. The Delivery Service is called by the Export worker after successful generation. On failure it reports back so the retry logic in the Export Service can increment the attempt counter and decide whether to re-enqueue or pause the schedule.
- **Audit Log** — a write-only append store. Every significant export event emits an audit record. The Export Service writes to the Audit Log directly; neither the worker nor the Delivery Service bypass it.
- **Feature flag / workspace settings** — a lightweight workspace-scoped configuration layer. Before any export is initiated (on-demand or scheduled dispatch), the Export Service checks the workspace's export-enabled flag. When disabled, the request is rejected immediately and no job is enqueued.

## Domain model

**ExportJob**
Represents a single export generation attempt, whether triggered ad hoc or by a schedule.
- Belongs to a requesting user and a target report.
- Carries the output format (CSV or PDF).
- Has a status lifecycle: `pending → generating → succeeded | failed`.
- Records the artifact location (populated on success) and error detail (populated on failure).
- Is linked to an ExportSchedule when triggered by one (nullable for on-demand jobs).
- Tracks attempt number to support retry logic.

**ExportSchedule**
Represents a user's recurring delivery configuration for a report.
- Belongs to a single owner (user) and a target report.
- Specifies frequency: `daily` or `weekly`.
- Has a status: `active | paused`.
- Records the pause source: `user` (manually paused) or `system` (auto-paused after exhausting retries).
- Tracks `next_delivery_at` (computed and updated after each dispatch).
- Has a soft-deletable lifecycle so history is preserved.

**ExportRun**
A record of one delivery attempt for a schedule, providing the run history view.
- Belongs to an ExportSchedule.
- References the ExportJob that was generated for this run.
- Records the outcome: `delivered | failed | retrying`.
- At most 30 runs are retained per schedule (older runs are pruned or archived).

**WorkspaceExportSettings**
A per-workspace configuration record.
- Holds `exports_enabled: boolean`.
- Modified only by workspace admins.
- Consulted by the Export Service on every export initiation.

**AuditEvent**
An immutable record of a significant export-related action.
- Carries an event type (e.g. `export_requested`, `export_succeeded`, `export_failed`, `retry_attempted`, `schedule_paused_by_system`).
- References the actor (user ID) and relevant object (ExportJob ID and/or ExportSchedule ID).
- Records a timestamp and any contextual metadata.

## Key workflows

**On-demand export**
1. The user requests an export of a report in a given format.
2. The Export Service checks `WorkspaceExportSettings.exports_enabled`; if false, it rejects the request and records an audit event.
3. The Export Service creates an `ExportJob` in `pending` status and emits an `export_requested` audit event.
4. The Export Service enqueues the job to the Export worker and returns an acknowledgement to the caller (the user does not wait for generation).
5. The Export worker fetches the report data via the Reporting module, applying the user's row-level permission filter.
6. The worker estimates artifact size; if it would exceed 50 MB, the job transitions to `failed` with a size-limit error, an `export_failed` audit event is recorded, and the user is notified.
7. On success, the worker renders the artifact (CSV or PDF), stores it, updates the job to `succeeded`, records an `export_succeeded` audit event, and delivers (or makes available for download) the artifact to the requesting user.

**Scheduled export dispatch**
1. The Scheduler fires at its configured interval and queries for all `active` ExportSchedules whose `next_delivery_at` is in the past.
2. For each due schedule, the Scheduler creates an `ExportJob` (owned by the schedule owner) and an `ExportRun` record linking them, then enqueues the job.
3. The Scheduler updates `next_delivery_at` on the schedule.
4. Export generation proceeds as in the on-demand flow (steps 5–7 above), except delivery goes to the Delivery Service rather than a download link.
5. The Delivery Service emails the artifact to the schedule owner.
6. On delivery success, the ExportRun is marked `delivered`.
7. On delivery failure, the ExportRun is marked `retrying`, the attempt counter on the ExportJob increments, and the job is re-enqueued (up to 3 total attempts). A `retry_attempted` audit event is emitted per retry.
8. If the third attempt fails, the ExportSchedule is transitioned to `paused` with `pause_source = system`, a `schedule_paused_by_system` audit event is recorded, and the ExportRun is marked `failed`.

**Schedule management (pause / resume)**
1. The schedule owner sends a pause or resume request.
2. The Export Service validates ownership.
3. On pause: the schedule status is set to `paused` with `pause_source = user`. Any in-flight jobs for this schedule complete normally but no new jobs are dispatched.
4. On resume: the schedule status is set to `active` and `next_delivery_at` is recalculated from the current time according to the configured frequency.

**Run history view**
1. The user requests the run history for one of their schedules.
2. The Export Service returns the most recent 30 ExportRun records for that schedule, ordered by creation time descending.

**Admin disable exports**
1. A workspace admin sets `WorkspaceExportSettings.exports_enabled = false`.
2. All subsequent on-demand and scheduled export initiations are rejected at the Export Service gate.
3. In-flight ExportJobs that are already being processed by the worker complete their current attempt (they were already past the gate); no new jobs are enqueued for any schedule in the workspace.

## Contracts

**Export Service — HTTP API (internal, called by the application frontend)**

- `POST /exports` — initiate a one-off export. Accepts report ID and format (csv or pdf). Returns an ExportJob identifier and initial status. Checks the workspace export flag and user report access before accepting.
- `GET /exports/{job_id}` — poll the status of an ExportJob; returns status and, when succeeded, a time-limited download URL for the artifact.
- `POST /export-schedules` — create a new schedule. Accepts report ID and frequency (daily or weekly). Returns the created ExportSchedule.
- `PATCH /export-schedules/{schedule_id}` — update schedule status. Accepts a status transition (pause or resume). Validates that the caller is the schedule owner.
- `DELETE /export-schedules/{schedule_id}` — soft-delete a schedule. Stops future dispatches; run history is retained.
- `GET /export-schedules/{schedule_id}/runs` — list the last 30 ExportRun records for the schedule. Validates caller is the schedule owner.

**Export Service — Admin API**

- `PATCH /workspaces/{workspace_id}/export-settings` — set `exports_enabled`. Restricted to workspace admins.
- `GET /workspaces/{workspace_id}/export-settings` — retrieve current settings. Restricted to workspace admins.

**Export worker interface (internal queue message)**

The Export Service publishes a job message containing: job ID, report ID, requesting user ID, output format, attempt number, and optionally a schedule ID. The worker reads this message, processes the job, and writes its result back to the Export Service (via a callback or shared job-state store) rather than directly to the API.

**Reporting module query interface (consumed by the Export worker)**

The Export worker calls the Reporting module's existing query interface, passing the report ID and the requesting user's identity so row-level permission filtering is applied identically to the interactive report view. The Reporting module returns a paginated or streaming result set; the worker consumes it without modifications to the Reporting module's interface.

**Delivery Service interface (internal, called by the Export worker on success)**

The Export worker calls the Delivery Service with: recipient email address (the schedule owner's address, resolved from user ID), artifact reference (storage key), report name, and schedule metadata for email body composition. The Delivery Service returns a delivery status (succeeded or failed); the worker uses this to update ExportRun state and trigger retry logic.

**Audit Log interface (write-only, called by the Export Service)**

The Export Service emits structured audit events. Each event carries: event type, actor user ID, workspace ID, relevant object IDs (job, schedule), timestamp, and a metadata blob for event-specific fields (e.g. failure reason, format, size). The Audit Log interface accepts these writes and guarantees append-only persistence; no read interface is required for this feature.

**Feature flag interface (read-only, consumed by the Export Service)**

The Export Service reads the workspace export-enabled flag from `WorkspaceExportSettings` before processing any request. This is a simple boolean lookup keyed by workspace ID. No polling or caching invalidation complexity is required at launch; a synchronous database read per request is sufficient.
