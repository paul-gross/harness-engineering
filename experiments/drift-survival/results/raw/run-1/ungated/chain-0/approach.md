# Technical Approach: Scheduled Report Exports

## Architecture outline

The export feature is composed of four primary components layered over the existing reporting module:

**Export service** — a backend service responsible for receiving export requests, enforcing permission checks, generating output files (CSV or PDF), and enforcing the 50 MB size limit. It exposes an internal API consumed by both the on-demand export path and the scheduler. It delegates to the existing report data access layer so that row-level permission rules are applied identically to what the user sees interactively.

**Job queue and async worker** — export generation is decoupled from the HTTP request cycle. When an export is triggered, a job is enqueued; a pool of async workers picks up jobs, calls the export service, writes the output to object storage, and records the result. This prevents export workloads from degrading interactive report performance.

**Scheduler** — a background process responsible for evaluating active export schedules, firing export jobs at their configured cadence (daily or weekly), and managing retry logic. It reads schedule state from the database and enqueues export jobs through the same job queue used by on-demand exports. On third-retry failure it transitions the schedule to a paused-on-failure state and triggers an owner notification.

**Notification service** — delivers email to schedule owners on two events: scheduled export delivery (attaches or links the export artifact) and paused-on-failure notification. Calls into the existing email infrastructure.

**Feature flag and admin control layer** — a thin guard evaluated at the API boundary before any export operation. Checks whether the export feature flag is enabled for the requesting workspace, and whether the admin has disabled exports for that workspace. Both checks are evaluated per-workspace without requiring a code deployment.

**Audit log sink** — every export lifecycle event (initiated, completed, rejected, failed) emits a structured audit record, written to the audit log store. The export service and async workers are both responsible for emitting events at the appropriate lifecycle points.

These components interact as follows: the API layer checks the feature flag and admin workspace setting, then hands the request to the export service, which checks permissions and enqueues a job. Workers execute jobs asynchronously, write results to object storage, and emit audit events. The scheduler drives the same path for recurring exports. The notification service is called by the worker (on successful scheduled delivery) and by the scheduler (on paused-on-failure).

---

## Domain model

**Report** — an existing entity. Has an identifier, an owner, and associated row-level permission rules.

**ExportRequest** — a transient record created when a user initiates a one-off export. Carries: request identifier, requesting user identity, report reference, requested format (CSV or PDF), timestamp of initiation, and current status (pending, processing, completed, rejected, failed).

**ExportArtifact** — the generated output file. Carries: artifact identifier, reference to the producing ExportRequest or ScheduledRun, format, storage location (object storage key), size in bytes, and expiry timestamp.

**ExportSchedule** — a persistent record expressing a user's intent to receive recurring exports of a report. Carries: schedule identifier, owner user identity, report reference, format, cadence (daily or weekly), status (active, paused, paused-on-failure), creation timestamp, and last-modified timestamp.

**ScheduledRun** — a record of one execution of a schedule. Carries: run identifier, parent ExportSchedule reference, scheduled-for timestamp, attempt count, status (pending, processing, delivered, failed, paused-on-failure), and timestamps for each attempt.

**AuditEvent** — an immutable record emitted at each export lifecycle transition. Carries: event identifier, event type, user identity, report identifier, format, schedule or request identifier (where applicable), and timestamp.

**WorkspaceExportConfig** — a per-workspace configuration record. Carries: workspace identifier, whether exports are admin-disabled, and a reference to the applicable feature flag state.

Relationships:
- ExportSchedule has many ScheduledRuns.
- ScheduledRun produces zero or one ExportArtifact (zero if failed, one if delivered).
- ExportRequest produces zero or one ExportArtifact.
- AuditEvent references an ExportRequest or ScheduledRun.
- ExportSchedule belongs to one Report and one owner user.

---

## Key workflows

**On-demand export**

1. User requests an export (format: CSV or PDF) for a report they have access to.
2. The API layer evaluates the feature flag and workspace admin setting; if either disables exports, a clear error is returned immediately.
3. The export service verifies the user has access to the requested report.
4. An ExportRequest record is created with status `pending`; an audit event `export.initiated` is emitted.
5. An async job is enqueued referencing the ExportRequest.
6. The API responds immediately, indicating the export is in progress (async).
7. A worker picks up the job, calls the export service to generate the output applying row-level permission rules.
8. If the generated output exceeds 50 MB, the ExportRequest is transitioned to `rejected`; an audit event `export.rejected` is emitted; the user is surfaced a clear size-limit error message.
9. If generation succeeds and the size is within limits, the artifact is written to object storage; the ExportRequest is transitioned to `completed`; an audit event `export.completed` is emitted; the artifact is made available for download.
10. If generation fails for any other reason, the ExportRequest is transitioned to `failed`; an audit event `export.failed` is emitted.

**Scheduled export — normal delivery**

1. The scheduler evaluates active ExportSchedules due for their next run.
2. For each due schedule, a ScheduledRun is created with status `pending` and attempt count 1.
3. An async export job is enqueued; the export service generates the output under the schedule owner's identity, applying row-level permission rules.
4. On success, the artifact is written to object storage; the ScheduledRun is transitioned to `delivered`; the notification service emails the artifact (or a download link) to the schedule owner; an audit event `export.completed` is emitted.

**Scheduled export — retry and paused-on-failure**

1. If the export job fails, the ScheduledRun increments its attempt count and status transitions to `failed`.
2. If attempt count is less than 3, the scheduler re-enqueues the job after a backoff interval.
3. On the third failure, the ScheduledRun is transitioned to `paused-on-failure`; the parent ExportSchedule is transitioned to `paused-on-failure`; the notification service emails the owner indicating the schedule has been paused due to repeated failures; an audit event `export.failed` is emitted.

**Schedule management**

- Owner creates a schedule: ExportSchedule is created in `active` status.
- Owner pauses a schedule: ExportSchedule status transitions to `paused`; no further runs are enqueued until resumed.
- Owner resumes a schedule: ExportSchedule status transitions to `active`; scheduler resumes normal evaluation.
- Owner views run history: the system returns the last 30 ScheduledRuns for a given ExportSchedule, including status and timestamps.

**Admin disabling exports**

- Admin toggles exports off for their workspace: WorkspaceExportConfig is updated; the feature flag/admin guard begins rejecting all export requests for that workspace with a clear message.
- Any in-flight jobs continue to completion; no new jobs are accepted while disabled.

**Feature flag control**

- A feature flag record can be toggled per workspace or globally without a deployment.
- The API guard reads the flag state at request time; no caching that would prevent near-immediate propagation of flag changes.

---

## Contracts

**Export API (HTTP, user-facing)**

- `POST /reports/{reportId}/exports` — initiate a one-off export. Accepts format (CSV or PDF). Returns an ExportRequest identifier and status. Errors if feature is disabled or user lacks access.
- `GET /exports/{exportId}` — poll status of an on-demand export request. Returns current status and, when completed, a download URL for the artifact.
- `GET /reports/{reportId}/exports/history` — not required for on-demand; exists for discoverability of a user's past exports if needed.

**Schedule API (HTTP, user-facing)**

- `POST /reports/{reportId}/schedules` — create an export schedule. Accepts format and cadence (daily or weekly). Returns the created ExportSchedule.
- `PATCH /schedules/{scheduleId}` — update schedule status (pause or resume). Owner identity enforced.
- `GET /schedules/{scheduleId}/runs` — retrieve the last 30 ScheduledRuns for a schedule, including status and timestamps. Restricted to the schedule owner.
- `DELETE /schedules/{scheduleId}` — delete a schedule entirely (implied by the business plan's ability to manage schedules).

**Admin API (HTTP, admin-facing)**

- `PUT /workspace/export-config` — enable or disable the export feature for the workspace. Requires admin role. Updates WorkspaceExportConfig.
- `GET /workspace/export-config` — retrieve current workspace export configuration.

**Internal: Export service interface**

- `generateExport(reportId, userId, format)` — applies row-level permissions for the given user, generates the output, returns a stream or buffer with size. Raises a size-limit error if output exceeds 50 MB. Called by async workers.
- `enqueueExport(exportRequestId)` / `enqueueScheduledRun(scheduledRunId)` — places a job onto the job queue.

**Internal: Scheduler interface**

- Periodic tick (cron or event-driven) — evaluates ExportSchedules due for their next run, creates ScheduledRuns, enqueues jobs.
- `handleRunFailure(scheduledRunId)` — increments attempt count, schedules retry or transitions to paused-on-failure and triggers owner notification.

**Internal: Notification service interface**

- `sendScheduledDelivery(userId, scheduleId, artifactLocation)` — emails the export artifact or download link to the schedule owner.
- `sendPausedOnFailureNotice(userId, scheduleId)` — emails the owner that the schedule has been automatically paused due to repeated delivery failures.

**Internal: Audit log interface**

- `emitExportEvent(eventType, userId, reportId, format, referenceId, timestamp)` — writes an immutable AuditEvent record. Event types: `export.initiated`, `export.completed`, `export.rejected`, `export.failed`.

**Feature flag interface**

- `isExportEnabled(workspaceId)` — returns a boolean combining the global/per-workspace feature flag state and the workspace admin override. Evaluated per request, not cached beyond a short TTL.
