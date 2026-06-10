# Technical approach: scheduled report exports

## Architecture outline

The feature introduces an **Export Service** as the central new component, operating alongside the existing Reporting Service and layered on top of shared infrastructure for queuing, storage, and email delivery.

**Components and interactions:**

- **Reporting Service** — the existing component that renders reports with row-level permission filtering. The Export Service calls into it to produce filtered data sets; no changes to the Reporting Service's external API are anticipated.
- **Export Service** — the new domain service responsible for orchestrating on-demand and scheduled export workflows. It validates requests, enforces the feature flag and workspace kill switch, enqueues generation jobs, tracks run history, and manages schedule lifecycle (create, pause, resume, delete).
- **Export Job Queue** — an asynchronous job queue (e.g. a background worker pool backed by a persistent queue) that receives export generation requests from the Export Service and processes them without blocking interactive report-viewing paths.
- **Export Storage** — temporary object storage (e.g. an S3-compatible bucket) where generated export files are held until delivery. Files are cleaned up after delivery or expiration.
- **Email Delivery Service** — the existing or shared service responsible for sending emails. The Export Service calls it to deliver generated files to schedule owners. It is treated as an external dependency; delivery failures are surfaced back to the Export Service for retry logic.
- **Scheduler** — a time-based trigger (e.g. a cron-style scheduler or a delayed-job mechanism) that reads active export schedules and enqueues generation jobs at the configured cadences (daily, weekly).
- **Audit Log** — the existing audit logging facility. The Export Service writes a structured record for every significant event: export requests, job outcomes, schedule lifecycle changes, retries, and automatic pauses.
- **Feature Flag / Workspace Configuration Store** — the existing mechanism for feature flags and workspace-level settings. The Export Service reads flag status and the workspace kill switch before processing any request.

Separation of concerns is preserved: the Export Service never renders reports itself (it delegates to the Reporting Service), and the Reporting Service remains unaware of export concepts.

---

## Domain model

**ExportSchedule**
Represents a user-configured recurring export. Fields include: schedule identifier, owner user identifier, report identifier, frequency (daily | weekly), status (active | paused), creation timestamp, and the timestamp of the most recent run. A schedule is owned by exactly one user and targets exactly one report.

**ExportRun**
Represents a single execution of a schedule (or an on-demand export). Fields include: run identifier, parent schedule identifier (nullable for on-demand runs), report identifier, requesting user identifier, format (CSV | PDF), status (pending | generating | succeeded | failed | retried | rejected), attempt count, file size (once known), delivery status, and timestamps for enqueue, generation completion, and delivery.

**ExportFile**
Represents the generated artifact. Fields include: file identifier, associated run identifier, storage location reference, format, size in bytes, and expiry timestamp. Exists only for runs that successfully produce output within the size limit.

**WorkspaceExportConfig**
Represents workspace-level export configuration. Fields include: workspace identifier, feature flag enabled (boolean), export globally enabled (boolean — the admin kill switch). The feature is blocked if either the feature flag is off or the admin has disabled export.

**Relationships:**
- One User → many ExportSchedules (one-to-many)
- One ExportSchedule → many ExportRuns (one-to-many, capped at 30 displayed to user)
- One ExportRun → zero or one ExportFile
- One Workspace → one WorkspaceExportConfig

---

## Key workflows

### On-demand export

1. The user requests an export of a report in a chosen format (CSV or PDF).
2. The Export Service checks the feature flag and the workspace kill switch; if either blocks the feature, it returns an error indicating unavailability.
3. The Export Service verifies the requesting user has access to the report (delegating to the Reporting Service's permission model).
4. An ExportRun record is created with status `pending` and an audit log entry is written.
5. A job is enqueued to the Export Job Queue.
6. The Export Job Queue worker picks up the job, calls the Reporting Service to render the report with the requesting user's row-level permissions applied, and streams the output into the chosen format.
7. If the resulting file size exceeds 50 MB, the worker marks the run `rejected`, records the outcome in the audit log, and surfaces a size-limit error to the user. The file is discarded.
8. If generation succeeds and is within the size limit, the file is written to Export Storage. The ExportRun is updated to `succeeded` and the audit log is updated.
9. The user is notified (or can poll) that the export is ready for download.

### Scheduled export creation

1. The user selects a report, chooses a frequency (daily or weekly), and submits the schedule.
2. The Export Service checks the feature flag and workspace kill switch; if blocked, returns an error.
3. The Export Service verifies the user has access to the report.
4. An ExportSchedule record is created with status `active`. An audit log entry is written.
5. The Scheduler picks up the new schedule on its next polling cycle and begins triggering runs at the configured cadence.

### Scheduled export execution

1. The Scheduler detects a due schedule and enqueues an export generation job, creating an ExportRun with status `pending`.
2. The Export Job Queue worker generates the export file using the schedule owner's permissions (row-level filtering applied as for on-demand exports).
3. On successful generation within the size limit, the file is written to Export Storage and the ExportRun is updated to `succeeded`.
4. The Export Service calls the Email Delivery Service to send the file to the schedule owner's email address.
5. On successful delivery, the ExportRun delivery status is updated. An audit log entry is written.
6. On delivery failure, the system increments the attempt count and enqueues a retry (up to 3 total attempts).
7. If the third attempt fails, the ExportSchedule is automatically set to `paused` and an audit log entry is written recording the automatic pause.

### Schedule management (pause, resume, delete)

1. The schedule owner requests a pause, resume, or deletion via the UI.
2. The Export Service validates ownership and updates the ExportSchedule status accordingly.
3. The Scheduler skips paused or deleted schedules on subsequent cycles.
4. An audit log entry is written for every state change.

### Workspace-level disable (admin)

1. An admin sets the workspace export kill switch to disabled via workspace settings.
2. WorkspaceExportConfig is updated.
3. All subsequent on-demand export requests return a feature-unavailable error.
4. The Scheduler stops enqueuing new jobs for all schedules in the workspace. In-flight jobs are either completed or gracefully abandoned depending on progress.
5. Users see a clear indication that the feature has been disabled.

---

## Contracts

### Export Service — public API surface

**Initiate on-demand export**
Accepts a report identifier, requesting user identity, and desired format (CSV or PDF). Returns a run identifier that the client can use to poll for status or retrieve the download link. Validates access, checks feature availability, and enqueues the job asynchronously. Responds synchronously with acknowledgement only; generation happens out-of-band.

**Get export run status**
Accepts a run identifier and requesting user identity. Returns current run status, format, timestamps, file size (if generated), and error detail (if rejected or failed). Restricted to the owner of the run.

**Create export schedule**
Accepts a report identifier, requesting user identity, and frequency (daily | weekly). Returns the created schedule identifier. Validates access and feature availability.

**List export schedules**
Accepts a user identity. Returns the user's schedules with current status and last-run summary.

**Update schedule status (pause / resume)**
Accepts a schedule identifier, requesting user identity, and desired status. Returns the updated schedule. Validates ownership.

**Delete export schedule**
Accepts a schedule identifier and requesting user identity. Validates ownership and removes the schedule.

**Get schedule run history**
Accepts a schedule identifier and requesting user identity. Returns the most recent 30 ExportRun records for the schedule, including status, timestamps, attempt count, and delivery outcome. Validates ownership.

### Export Service — admin API surface

**Set workspace export configuration**
Accepts a workspace identifier, admin identity, and the desired enabled/disabled state of the export kill switch. Updates WorkspaceExportConfig and propagates the change to the Scheduler.

### Export Job Queue — worker contract

Workers consume jobs that carry: run identifier, report identifier, user identity (for permission filtering), format, and schedule identifier (nullable). Workers are expected to call the Reporting Service with the supplied user identity to obtain a permission-filtered data set, render it to the requested format, enforce the 50 MB size cap, write results to Export Storage, and update the ExportRun record and audit log regardless of outcome. Workers do not call the Email Delivery Service directly — they signal the Export Service on completion, which handles delivery orchestration.

### Reporting Service — consumed interface

The Export Service consumes an existing interface that accepts a report identifier and a user identity and returns the permission-filtered row set for that report. No new interface is added to the Reporting Service; the Export Service reuses whatever the interactive view already relies on.

### Email Delivery Service — consumed interface

The Export Service calls an existing email delivery interface, passing a recipient address (the schedule owner's email), a subject, and an attached or linked export file reference. Delivery success or failure is returned synchronously or via callback; the Export Service uses the outcome to drive retry and automatic-pause logic.

### Audit Log — write interface

The Export Service writes structured audit records. Each record carries: event type (export requested, export succeeded, export rejected, export failed, delivery attempted, delivery succeeded, delivery failed, schedule created, schedule paused, schedule resumed, schedule deleted, auto-paused), user identity, workspace identifier, report identifier, run identifier (where applicable), schedule identifier (where applicable), format (where applicable), timestamp, and freeform detail. The audit log interface is append-only from the Export Service's perspective.
