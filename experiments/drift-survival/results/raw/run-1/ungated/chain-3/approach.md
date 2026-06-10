# Technical Approach: Scheduled Report Exports

## Architecture outline

The export feature is composed of four primary layers that interact to fulfill both one-off and scheduled export requests.

**API layer** — A set of new HTTP endpoints handles export initiation, schedule management, and status queries. All endpoints are gated behind a feature flag check and a workspace-level export-enabled check before any business logic executes. Row-level permission enforcement is applied here when resolving the report's data set.

**Export worker** — An asynchronous job processor accepts export jobs from the queue, applies row-level filtering using the requesting user's identity, generates the output artifact (CSV or PDF), enforces the 50 MB size limit, and writes the result to object storage. It emits structured events to the audit log on every meaningful state transition.

**Scheduler** — A time-driven component reads active recurring schedules and enqueues export jobs according to each schedule's frequency. On job completion, it handles delivery by dispatching an email with the artifact to the schedule owner. It tracks delivery attempts, orchestrates up to three retries on failure, transitions the schedule to paused on exhausted retries, and sends the owner a failure notification.

**Audit logger** — A cross-cutting service that receives structured export events (triggered, completed, rejected, delivered, retried, failed, paused) from the API layer and the export worker, and appends them to the persistent audit log with user, report, format, timestamp, and outcome.

**Feature flag service** — A runtime-evaluable toggle that can be flipped without a deployment. The API layer and UI both consult this service on each request; when the flag is off, no export surface is reachable.

**Admin configuration store** — Holds the per-workspace export-enabled setting. Both the API layer and the UI read this to enforce the admin disable control consistently.

---

## Domain model

**Report** — An existing entity representing a saved query or dashboard. Reports have an owner and are associated with a workspace. A report's data set is subject to row-level permissions scoped to the requesting user at read time.

**ExportJob** — Represents a single export run, whether triggered manually or by the scheduler. Fields: identifier, report reference, requesting user, format (CSV or PDF), status (pending, processing, completed, rejected, failed), artifact location, artifact size, error detail, created timestamp, completed timestamp. An ExportJob is immutable once it reaches a terminal status.

**ExportSchedule** — Represents a user's recurring export configuration. Fields: identifier, owner (user reference), report reference, format, frequency (daily or weekly), status (active, paused), created timestamp, last-modified timestamp. A schedule belongs to exactly one user and one report.

**ExportRun** — A historical record linking an ExportSchedule to the ExportJob it produced. Fields: schedule reference, job reference, delivery status (success, failed, retried), delivery attempt count, run timestamp. At most 30 ExportRuns are retained per schedule; older ones are pruned.

**AuditEvent** — An append-only record of any export-related action. Fields: event type, actor (user reference or system), report reference, format, schedule reference (when applicable), timestamp, outcome, metadata blob.

**WorkspaceExportConfig** — Per-workspace configuration. Fields: workspace reference, exports-enabled boolean.

**FeatureFlag** — A runtime toggle with a name key (`export-feature`) and an enabled boolean. Evaluated without a deployment.

Relationships:
- A Report has zero or many ExportSchedules; a Report has zero or many ExportJobs.
- An ExportSchedule has zero or many ExportRuns.
- Each ExportRun references exactly one ExportJob.
- A WorkspaceExportConfig belongs to exactly one workspace.
- AuditEvents reference a Report and optionally an ExportSchedule.

---

## Key workflows

**One-off export**

1. User requests an export for a report in a given format.
2. API layer checks the feature flag; if off, returns a not-available response.
3. API layer checks the workspace export-enabled setting; if disabled, returns a not-available response.
4. API layer verifies the user has access to the report; if not, returns unauthorized.
5. API layer creates an ExportJob in pending status and enqueues it. Returns the job identifier to the caller immediately (async — does not wait for completion).
6. Export worker picks up the job, resolves the report's data set with the user's row-level permissions applied, and begins generating the artifact.
7. If the projected artifact exceeds 50 MB, the worker marks the job rejected, records a size-limit error detail, and emits an audit event (rejected outcome).
8. On successful generation, the worker writes the artifact to object storage, marks the job completed, and emits an audit event (completed outcome).
9. On worker failure, the job is marked failed and an audit event is emitted.

**Scheduled export creation**

1. User submits a schedule request specifying report, format, and frequency.
2. API layer runs the same feature-flag and workspace-enabled checks as in the one-off flow.
3. API layer verifies the user has access to the report.
4. API layer creates an ExportSchedule in active status and persists it.

**Scheduled export execution**

1. Scheduler evaluates all active ExportSchedules whose next-run time has elapsed.
2. For each due schedule, the scheduler creates an ExportJob (owned by the schedule's owner) and enqueues it, then creates an ExportRun record linked to the schedule and job.
3. Export worker processes the job as in the one-off flow (with permission enforcement using the schedule owner's identity).
4. On job completion, the scheduler dispatches a delivery email with the artifact to the schedule owner and updates the ExportRun delivery status to success. An audit event is emitted.
5. On delivery failure, the scheduler increments the delivery attempt count and re-queues delivery. If attempt count reaches 3 and delivery still fails, the scheduler marks the ExportSchedule paused, updates the ExportRun delivery status to paused, sends a failure notification email to the owner, and emits an audit event.
6. ExportRun retention is enforced: if a schedule now has more than 30 ExportRuns, the oldest are pruned.

**Schedule pause and resume**

1. Schedule owner requests a pause or resume on one of their schedules.
2. API layer checks feature flag, workspace-enabled, and ownership.
3. Schedule status is updated to paused or active accordingly.

**Admin disable exports**

1. Workspace admin sets the workspace export-enabled flag to false via the admin API.
2. WorkspaceExportConfig is updated.
3. Subsequent one-off and scheduled export API requests receive a not-available response.
4. UI reads the config on load and hides all export surfaces when disabled.

**Feature flag off**

1. The feature flag `export-feature` is toggled to off outside of a deployment.
2. All export API endpoints return a not-available response immediately after the flag value is observed as off (no restart required).
3. UI reads the flag on load and renders no export-related UI elements.

---

## Contracts

**Export API endpoints**

- **Initiate one-off export** — accepts a report identifier and a format (CSV or PDF). Returns a job identifier and a polling or webhook mechanism for status. Enforces feature flag, workspace export-enabled, and report access.

- **Get export job status** — accepts a job identifier. Returns the current status, artifact download URL (when completed), and error detail (when rejected or failed). Access is restricted to the requesting user who initiated the job.

- **Create export schedule** — accepts a report identifier, format, and frequency. Returns the created schedule's identifier and current state. Enforces feature flag, workspace export-enabled, and report access.

- **Update schedule status** — accepts a schedule identifier and a target status (paused or active). Restricted to the schedule owner.

- **Get schedule run history** — accepts a schedule identifier. Returns up to 30 ExportRun records with delivery status and timestamps. Restricted to the schedule owner.

- **Delete export schedule** — accepts a schedule identifier. Removes the schedule and its run history. Restricted to the schedule owner.

- **Admin: get/set workspace export config** — reads or writes the exports-enabled boolean for a workspace. Restricted to workspace admins.

**Export worker interface**

The worker consumes a job queue. Each job message carries: job identifier, report identifier, requesting user identifier, and format. The worker is the sole writer of job terminal statuses and artifact locations. It publishes completion and failure events that the scheduler and audit logger consume.

**Scheduler interface**

The scheduler is driven by a time-based trigger (cron or equivalent). It reads ExportSchedules, enqueues jobs, and handles delivery. It consumes export worker completion events to determine when to attempt delivery. It is the sole writer of ExportRun delivery status and the sole component that transitions a schedule to paused on retry exhaustion.

**Audit logger interface**

Accepts structured event payloads from the API layer and export worker. Each payload declares an event type, actor, affected entities, timestamp, and outcome. The audit logger is append-only; no consumer may update or delete audit records. Queries against the audit log are read-only and available to admins for compliance review.

**Feature flag interface**

Provides a single evaluation call that accepts a flag key and returns an enabled boolean. The result must reflect the current flag value without requiring a process restart. All export API handlers and the UI call this interface before executing any export logic.

**Email delivery interface**

The scheduler calls an email delivery service with a recipient address, a subject, a message body, and an artifact attachment or download link. The interface returns a delivery acknowledgment or a retriable error, which drives the retry logic.
