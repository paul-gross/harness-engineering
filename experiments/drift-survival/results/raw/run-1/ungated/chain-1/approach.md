# Technical Approach: Scheduled Report Exports

## Architecture outline

The export feature introduces three new subsystems layered on top of the existing reporting module:

**Export service** — a backend service responsible for generating export artifacts (CSV and PDF). It receives export requests (both one-off and scheduled), enforces the requesting user's row-level permissions at generation time, applies the 50 MB size limit, and writes every attempt and outcome to the audit log. Generation runs asynchronously via a background job queue so it does not block the interactive reporting path.

**Scheduler service** — a backend service that manages recurring export schedules. It stores schedule definitions (report, format, frequency, owner), drives execution by enqueuing export jobs at the configured cadence, tracks per-run history (up to 30 runs per schedule), handles retry logic (up to 3 total attempts per run), auto-pauses failing schedules after the third failed attempt, and notifies the schedule owner of the pause.

**Delivery service** — a thin wrapper around the existing email infrastructure. It accepts a completed export artifact and a recipient (always and only the schedule owner) and delivers it. Delivery results are reported back to the scheduler service so the run history and retry state can be updated.

**Feature flag layer** — a workspace-level flag controls whether the export feature is accessible at all. Every entry point into the export service (one-off or scheduled) checks this flag before proceeding. When the flag is off, requests are rejected and the rejection is still written to the audit log.

**Audit log** — an append-only event store. Both the export service and the scheduler service write to it. Every attempt — success, failure, rejection — produces an entry containing at minimum: user identity, report identifier, format, timestamp, and outcome.

These subsystems interact as follows: the reporting UI surfaces export and schedule management controls, which call the export service API and the scheduler API respectively. The scheduler enqueues jobs to the same background queue the export service uses for one-off requests. The export service always calls through the row-level permission layer before generating output, consults the feature flag, and writes to the audit log. On completion, the export service hands artifacts to the delivery service (for scheduled runs) or makes them available for direct download (for one-off runs).

## Domain model

**Workspace** — has a feature flag (`exports_enabled: boolean`). This flag gates all export activity for every user in the workspace.

**Report** — an existing entity; referenced by export requests and schedules. The export feature does not own the report entity.

**ExportRequest** — represents a single on-demand export. Belongs to a user (the requester) and a report. Carries format (CSV | PDF), status (pending / in-progress / completed / failed / rejected), output artifact reference (when complete), size in bytes (when known), and a link to the corresponding AuditLogEntry.

**ExportSchedule** — represents a recurring export configuration. Belongs to a user (the owner) and a report. Carries format, frequency (daily | weekly), status (active | paused), and a collection of ExportRuns. Pause state can be set manually by the owner or automatically by the system after exhausting retries.

**ExportRun** — one execution of a schedule. Belongs to an ExportSchedule. Carries run timestamp, attempt count (1–3), status (success | failed | retried), error detail (nullable), and a reference to the delivery attempt. The schedule retains history for the last 30 runs.

**AuditLogEntry** — append-only record. Carries event type (one-off export attempt | scheduled run attempt | feature-disabled rejection | size-limit rejection), actor user identity, report identifier, format, timestamp, and outcome detail. No foreign-key relationship back to mutable entities — the audit log is immutable once written.

**DeliveryAttempt** — represents one email delivery attempt for a scheduled run. Belongs to an ExportRun. Carries recipient (always the schedule owner's email), timestamp, and delivery status (sent | failed).

Relationships:
- Workspace has many ExportSchedules (through the workspace's users).
- User owns many ExportRequests and many ExportSchedules.
- ExportSchedule has many ExportRuns (capped display at 30; older runs may be archived or pruned).
- ExportRun has many DeliveryAttempts (up to 3).
- ExportRun has one AuditLogEntry per attempt.
- ExportRequest has one AuditLogEntry.

## Key workflows

**One-off export (CSV or PDF)**

1. User requests an export from the reporting UI for a report they can access.
2. API layer checks the workspace feature flag; if disabled, reject and write a rejection AuditLogEntry.
3. Create an ExportRequest record in pending state; return an acknowledgment to the client.
4. Background worker picks up the job, re-evaluates the requesting user's row-level permissions, and fetches the permitted rows.
5. Generate the artifact in the requested format. If the artifact exceeds 50 MB, mark the request as rejected, surface a user-facing error, and write a size-limit AuditLogEntry.
6. On success, mark the ExportRequest completed, store the artifact reference, and write a success AuditLogEntry.
7. The client polls or receives a push notification; on completion it can download the artifact directly.

**Schedule creation**

1. User configures a new export schedule (report, format, frequency) from the reporting UI.
2. API layer checks the workspace feature flag; if disabled, reject.
3. Create an ExportSchedule in active state. Return the new schedule to the client.

**Scheduled export execution**

1. Scheduler service determines which active schedules are due (daily or weekly cadence).
2. For each due schedule, the scheduler creates an ExportRun and enqueues an export job, associating the schedule owner as the acting user.
3. The export service processes the job: checks the feature flag, re-evaluates the schedule owner's row-level permissions at generation time, generates the artifact, enforces the 50 MB limit.
4. On success: mark the ExportRun as success, hand the artifact to the delivery service to email the schedule owner, write a success AuditLogEntry.
5. On failure (generation or delivery): increment attempt count on the ExportRun, mark it as retried, write a failed AuditLogEntry for this attempt.
   - If attempt count < 3: re-enqueue the job for retry.
   - If attempt count == 3: mark the ExportRun as failed, set the ExportSchedule status to paused, send the owner a pause notification email, write a final failed AuditLogEntry.

**Schedule pause and resume**

1. User requests pause or resume of a schedule they own via the UI.
2. API layer verifies ownership (users may only modify their own schedules).
3. Update ExportSchedule status accordingly. No active jobs are cancelled; in-flight runs complete normally.

**Viewing run history**

1. User navigates to a schedule's run history view.
2. API returns the last 30 ExportRuns for that schedule, ordered by run timestamp descending, with status, timestamp, and any error detail.

**Workspace admin disabling exports**

1. Admin toggles the workspace feature flag to disabled via workspace settings.
2. All subsequent export requests (one-off or scheduled) are rejected at the feature flag check.
3. In-flight exports that are already processing complete normally; scheduled jobs that have not yet been picked up are skipped with a feature-disabled rejection and AuditLogEntry.

## Contracts

**Export API (one-off)**

- `POST /reports/{reportId}/exports` — initiate an export. Accepts format (CSV | PDF). Returns an export request identifier and initial status. Fails with a clear error if the feature is disabled for the workspace.
- `GET /exports/{exportId}` — poll the status of an export request. Returns status, and when complete, a time-limited download URL for the artifact. Returns error detail on failure or rejection.

**Schedule API**

- `POST /reports/{reportId}/schedules` — create a new export schedule. Accepts format and frequency (daily | weekly). Returns the new schedule resource. Fails if the feature is disabled.
- `GET /schedules` — list the calling user's export schedules with current status.
- `GET /schedules/{scheduleId}` — fetch a single schedule with summary metadata.
- `PATCH /schedules/{scheduleId}` — update a schedule's status (pause | resume). Only the schedule owner may call this.
- `DELETE /schedules/{scheduleId}` — delete a schedule and stop future runs. Only the schedule owner may call this.
- `GET /schedules/{scheduleId}/runs` — return the last 30 run records for a schedule, each with timestamp, status, attempt count, and error detail.

**Internal: Export job queue contract**

Jobs enqueued by both the one-off API and the scheduler carry: job type (one-off | scheduled), report identifier, format, acting user identifier (the requester or schedule owner), export request or run identifier (for status write-back), and attempt number. The export worker reads this payload and must not trust any cached permission state — it re-fetches row-level permissions at execution time.

**Internal: Delivery service contract**

Accepts: artifact byte stream or reference, recipient email address (always the schedule owner), run identifier for status write-back. Returns: delivery status (sent | failed) and any provider error detail. The caller (export service) is responsible for updating ExportRun and triggering retry or pause logic based on the result.

**Internal: Audit log write contract**

Any component writing to the audit log sends: event type, actor user identifier, report identifier, format, timestamp (server-assigned), outcome (success | failed | rejected), and optional structured detail (e.g., rejection reason, error message, artifact size). The audit log service accepts writes but never updates or deletes entries. Components must write an entry for every attempt, including rejections, regardless of whether the export was initiated by a user or by the scheduler.

**Workspace settings API (admin)**

- `PATCH /workspace/settings` — update workspace-level settings. The `exports_enabled` boolean field controls the feature flag. Restricted to workspace admin role. Returns the updated settings object.
