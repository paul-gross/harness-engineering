# Technical Approach — Scheduled Report Exports

## Architecture outline

The export feature introduces three new vertical slices layered on top of the existing reporting module.

**Export service** — a dedicated backend service responsible for generating export artifacts (CSV and PDF). It receives export requests, enforces row-level permissions against the data layer, streams or buffers the generated file, enforces size limits, and emits audit log entries at each lifecycle stage. It exposes an internal API consumed by both the API gateway and the scheduler.

**Async job queue** — export generation is offloaded to a background job queue so that interactive report viewing is never blocked. The API layer enqueues a job and returns immediately; workers pull from the queue, invoke the export service, and update job status. An existing queue infrastructure (e.g. Sidekiq, Celery, or BullMQ, depending on the stack) is extended with a dedicated export worker pool.

**Scheduler** — a time-driven component that reads active export schedules, emits export jobs at the configured cadence (daily or weekly), tracks per-run outcomes, enforces retry logic (up to 3 attempts per scheduled run), auto-pauses a schedule after three consecutive failures, and maintains a capped run-history log (last 30 runs per schedule).

**Email delivery adapter** — a thin adapter wrapping the existing transactional email infrastructure. It accepts a rendered export artifact plus a recipient address and dispatches the email. Retry responsibility lives in the scheduler, not in this adapter.

**Feature flag and admin kill-switch layer** — a middleware/guard layer that sits in front of all export API endpoints and UI entry points. It evaluates (a) whether the export feature flag is enabled for the environment and (b) whether the admin kill-switch is active for the requesting user's workspace. If either check fails, the request is rejected before any export logic executes and all UI surfaces are suppressed.

**Audit log sink** — the existing audit log infrastructure is extended with a set of export-specific event types. The export service and scheduler both write to this sink synchronously within the same logical operation as the export action.

Components interact as follows: the API gateway authenticates requests, evaluates the feature flag and admin kill-switch, then routes on-demand export requests to the job queue. Workers dequeue jobs, call the export service, and write outcomes to the audit log. The scheduler runs on a cron-like trigger, generates jobs for due schedules, feeds them through the same worker pipeline, and on success hands the artifact to the email delivery adapter. All actors write audit events through the shared audit log sink.

## Domain model

**Report** — an existing entity. Referenced by exports; no structural changes required. A user's access to a report, including which rows they may see, is already encoded in the reporting module's permission model.

**ExportJob** — represents a single export generation attempt. Attributes: identifier, report reference, requesting user, format (CSV or PDF), status (pending, running, succeeded, failed, rejected), size in bytes (populated on completion), error message (populated on failure), created-at, completed-at. An ExportJob is ephemeral and not retained beyond operational need.

**ExportSchedule** — represents a user's recurring export configuration. Attributes: identifier, owner (user reference), report reference, frequency (daily or weekly), status (active, paused), created-at, updated-at. Owned exclusively by one user; no shared-ownership model.

**ScheduledRun** — represents one execution attempt within a schedule. Attributes: identifier, schedule reference, attempt number (1–3), status (delivered, failed, auto-paused), triggered-at, completed-at. A ScheduledRun is created when the scheduler fires a job for a schedule; each retry increments attempt number. The system retains the last 30 ScheduledRuns per ExportSchedule.

**AuditEvent** — extends the existing audit log entity with export-specific event types: `export.initiated`, `export.succeeded`, `export.failed`, `export.rejected`, `scheduled_export.initiated`, `scheduled_export.delivered`, `scheduled_export.failed`, `scheduled_export.paused`. Common attributes: event type, actor identity, report identity, format, timestamp, outcome detail.

**WorkspaceExportSettings** — a per-workspace configuration record. Attributes: workspace reference, exports-enabled (boolean). Managed by workspace admins. When exports-enabled is false, the admin kill-switch blocks all export activity for that workspace.

Relationships: an ExportSchedule has many ScheduledRuns; a ScheduledRun is associated with one ExportJob; a Report is referenced by many ExportSchedules and ExportJobs; a WorkspaceExportSettings record belongs to one Workspace.

## Key workflows

**On-demand export — happy path**

1. User requests an export (format + report) via the UI or API.
2. Feature flag and admin kill-switch are evaluated; if either blocks, return an error and halt.
3. The API layer authenticates the user and verifies they have access to the report.
4. An ExportJob is created with status `pending` and an audit event `export.initiated` is written.
5. The job is enqueued to the background worker pool.
6. A worker picks up the job, sets status to `running`, queries the report data filtered by the user's row-level permissions, and renders the chosen format.
7. If the rendered artifact exceeds 50 MB, the job transitions to `rejected`, a user-facing error is returned, and `export.rejected` is written to the audit log.
8. On success the artifact is stored transiently, the job transitions to `succeeded`, and `export.succeeded` is written to the audit log.
9. The user is notified that the export is ready and can download it.

**On-demand export — failure path**

If an unrecoverable error occurs during generation (steps 6–8), the job transitions to `failed`, `export.failed` is written to the audit log with the error detail, and the user receives an error notification.

**Scheduled export — execution**

1. The scheduler evaluates all ExportSchedules with status `active` whose next-run time is due.
2. For each due schedule, a ScheduledRun is created (attempt number 1) and an ExportJob is enqueued using the schedule owner's identity and permissions.
3. The job executes via the same worker pipeline as on-demand exports.
4. On success the artifact is handed to the email delivery adapter, which sends it to the schedule owner. The ScheduledRun is recorded as `delivered` and `scheduled_export.delivered` is written to the audit log. The schedule's next-run time is advanced.
5. On failure the ScheduledRun is recorded as `failed` and `scheduled_export.failed` is written. If attempt number is less than 3, a new ScheduledRun is created with attempt number incremented and the job is re-enqueued after a backoff interval.
6. If the third attempt fails, the ExportSchedule transitions to status `paused`, the ScheduledRun is recorded as `auto-paused`, and `scheduled_export.paused` is written to the audit log. The owner is notified that the schedule has been auto-paused.
7. Run history is maintained by retaining only the 30 most recent ScheduledRuns per schedule; older records are pruned.

**Schedule management — create, pause, resume**

A user creates an ExportSchedule by selecting a report, a format, and a frequency. The schedule starts in `active` status. The user may transition it to `paused` at any time; a paused schedule is skipped by the scheduler on every trigger cycle. The user may transition it back to `active` to resume delivery. No data is lost during a pause.

**Admin kill-switch**

An admin updates WorkspaceExportSettings.exports-enabled to false. From that point forward, the feature flag and admin kill-switch layer rejects all export API calls from users in that workspace and suppresses all export UI surfaces. Existing ExportSchedules are not deleted; they remain dormant and resume if the kill-switch is toggled back on.

**Feature flag gate**

When the feature flag is off globally, no export API routes are registered or reachable, and the client receives no export UI components. This is enforced at the platform level before any workspace-level checks run.

## Contracts

**Export API — on-demand**

An authenticated HTTP endpoint accepts a request identifying a report and a desired export format. It responds synchronously with a job identifier and a status URL the client can poll. A separate endpoint accepts a job identifier and returns the current job status and, when complete, a download URL for the artifact. Both endpoints are gated by the feature flag and admin kill-switch.

**Export API — schedules**

A CRUD endpoint set scoped to the authenticated user manages ExportSchedules: create a schedule (report, format, frequency), list owned schedules, update a schedule (pause or resume, change frequency), and delete a schedule. A read endpoint returns the run history (last 30 ScheduledRuns) for a given schedule. All endpoints are gated by the feature flag and admin kill-switch.

**Admin settings API**

An admin-only endpoint reads and writes WorkspaceExportSettings for the caller's workspace. The write operation accepts a single boolean payload toggling exports-enabled.

**Export service internal interface**

An internal interface callable by the job worker. It accepts a report identifier, a user identity (used to scope row-level permission filtering), and a format. It returns either a rendered artifact with its byte size, or a structured error indicating failure reason (permission error, size-limit exceeded, generation error). It does not handle queuing or retry — those concerns belong to the caller.

**Email delivery adapter interface**

An internal interface callable by the scheduler on successful scheduled export completion. It accepts a recipient email address and an artifact (either as a byte stream or a storage reference). It returns a delivery acknowledgement or a structured error. Retry is the caller's responsibility.

**Audit log sink interface**

An append-only internal interface accepting a structured audit event value. Callers provide event type, actor identity, report identity, format, timestamp, and a free-form outcome detail field. The interface is fire-and-write; callers do not receive application-level feedback beyond write confirmation. The sink is backed by the existing audit log infrastructure.

**Feature flag and admin kill-switch interface**

A synchronous guard callable by API middleware. It accepts a workspace identifier and evaluates two conditions in order: (1) is the export feature flag enabled for the current environment, and (2) is exports-enabled true for the given workspace. It returns an allow or deny decision with a reason code. Denial short-circuits further request processing.
