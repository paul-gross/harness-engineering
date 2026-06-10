# Technical Approach: Scheduled Report Exports

## Architecture Outline

The export feature is composed of four primary components layered on top of the existing reporting surface:

**Export Request Handler** sits at the API boundary. It validates that the requesting user has access to the target report, applies the workspace-level feature-flag check, and either processes the export synchronously (for small reports below the size threshold) or enqueues an asynchronous export job. It is also responsible for writing the initial audit log entry.

**Export Job Worker** is an asynchronous background processor. It pulls jobs from the export queue, invokes the row-level permission filter against the report data source, streams the result into the requested format (CSV or PDF), checks the 50 MB size constraint before finalizing, uploads the artifact to object storage, and writes completion or failure audit log entries. On failure it updates the retry counter and re-enqueues or marks the job as permanently failed.

**Scheduler Service** manages recurring export schedules. It stores schedule definitions, tracks next-run timestamps, and on each tick emits export jobs to the same Export Job Worker queue used for one-off exports. After a job completes it records the run in the schedule run history and, on third consecutive failure, pauses the schedule and dispatches an owner-notification email.

**Notification / Delivery Service** handles all outbound email. It is called by the Export Job Worker (for one-off export ready / failure notices) and by the Scheduler Service (for scheduled delivery and pause notifications). For scheduled exports it attaches the export artifact or a download link; for failure and pause notices it sends plain status emails. Delivery is strictly to the authenticated owner — no third-party addresses.

**Feature Flag + Workspace Config Store** is a lightweight configuration layer consulted by the Export Request Handler and the Scheduler Service before any export is allowed to proceed. It also gates the scheduler tick so that paused-workspace jobs are never enqueued.

These components interact through:
- A synchronous HTTP layer (API → Export Request Handler)
- An asynchronous job queue (Export Request Handler / Scheduler Service → Export Job Worker)
- Direct service calls for audit logging and notification
- Object storage for artifact persistence

## Domain Model

**Report** — an existing entity representing a reportable data set. Has an owner workspace, a defined data source query, and a row-level permission policy. The export feature adds no new fields to this entity.

**ExportJob** — represents a single export execution, one-off or scheduled. Fields: job identifier, report reference, requesting user, originating schedule (nullable — null for one-off), requested format (CSV | PDF), status (pending | processing | completed | failed | rejected), artifact storage reference (nullable until complete), size in bytes (nullable until complete), retry count, created-at, completed-at, audit-log entries list.

**ExportSchedule** — represents a recurring delivery configuration. Fields: schedule identifier, owning user, report reference, frequency (daily | weekly), delivery day/time anchor, status (active | paused), created-at, last-modified-at.

**ScheduleRun** — one entry per scheduler tick for a given schedule. Fields: run identifier, schedule reference, triggered-at, export job reference, run status (success | failed | paused-on-failure), delivered-at.

**AuditLogEntry** — append-only record of every notable export event. Fields: entry identifier, event type (initiated | completed | failed | rejected | schedule-paused), user identity, workspace identifier, report identifier, export job reference (nullable for workspace-disabled rejections), format, feature-flag state at event time, timestamp. Written regardless of feature-flag state.

**WorkspaceExportConfig** — per-workspace configuration record. Fields: workspace identifier, exports-enabled boolean, feature-flag override (inherits global flag by default).

Relationships:
- An ExportJob belongs to one Report and one User; optionally to one ExportSchedule.
- An ExportSchedule belongs to one Report and one User; has many ScheduleRuns.
- A ScheduleRun references one ExportJob.
- AuditLogEntry references a User, a Report, and optionally an ExportJob.

## Key Workflows

**One-off export request**
1. User requests an export (format, report).
2. Export Request Handler checks the workspace feature flag; if disabled, writes a rejected AuditLogEntry and returns an error to the user.
3. Handler verifies the user has view access to the report; if not, returns 403.
4. Handler creates an ExportJob with status pending and writes an initiated AuditLogEntry.
5. Handler enqueues the job and returns a job reference to the user (non-blocking).
6. Export Job Worker picks up the job, applies row-level permission filtering, streams rows into the target format.
7. Worker checks artifact size; if above 50 MB, marks the job rejected, writes a rejected AuditLogEntry, and notifies the user of the rejection.
8. On success, worker uploads the artifact, marks the job completed, writes a completed AuditLogEntry, and notifies the user that the export is ready.
9. On processing failure, worker increments retry count and re-enqueues (up to a platform-defined retry ceiling for one-off jobs); on final failure it marks the job failed and writes a failed AuditLogEntry.

**Scheduled export tick**
1. Scheduler Service evaluates all active schedules whose next-run timestamp has passed.
2. For each due schedule, it checks the workspace feature flag; if disabled, it skips enqueuing (no job, no audit entry for the skip — the workspace admin disabled the feature deliberately).
3. Scheduler creates an ExportJob (linked to the schedule) with status pending and enqueues it.
4. Export Job Worker processes the job identically to a one-off export (permission filtering, size check, artifact upload).
5. On success, worker writes the completed AuditLogEntry; Scheduler records a success ScheduleRun, updates next-run timestamp, and delivers the artifact by email to the schedule owner.
6. On failure, Scheduler records a failed ScheduleRun and increments the consecutive-failure counter. If the counter reaches 3, the schedule status is set to paused, a schedule-paused AuditLogEntry is written, and the owner receives a pause notification email.

**Schedule management (create / pause / resume)**
1. User creates a schedule by specifying report, format, and frequency; Scheduler Service validates access and persists an ExportSchedule with status active.
2. User pauses a schedule they own; Scheduler Service sets status to paused — the next scheduler tick skips it.
3. User resumes a schedule they own; Scheduler Service resets status to active and clears the consecutive-failure counter.
4. User views run history; Scheduler Service returns the most recent 30 ScheduleRun records for the requested schedule, verified to be owned by the requesting user.

**Workspace admin disabling exports**
1. Admin sets exports-enabled to false on the WorkspaceExportConfig.
2. All subsequent one-off export requests are rejected at the handler layer with an AuditLogEntry.
3. Scheduler Service skips enqueuing for all schedules belonging to the workspace on subsequent ticks (schedules remain defined but produce no jobs while disabled).
4. Re-enabling exports restores normal operation without needing to recreate schedules.

## Contracts

**Export API (HTTP)**

- *Initiate one-off export* — accepts report identifier and desired format; returns a job reference and polling/status URL. Synchronous acknowledgement only; the actual artifact is produced asynchronously.
- *Get job status* — accepts job identifier; returns current status, artifact download URL when complete, error details when rejected or failed.
- *Create schedule* — accepts report identifier, format, and frequency (daily or weekly with delivery anchor); returns schedule identifier.
- *Pause schedule* — accepts schedule identifier; transitions status to paused. Caller must own the schedule.
- *Resume schedule* — accepts schedule identifier; transitions status to active, resets failure counter. Caller must own the schedule.
- *Get schedule run history* — accepts schedule identifier; returns the 30 most recent ScheduleRun records (status, triggered-at, delivered-at). Caller must own the schedule.

All endpoints require an authenticated session. All endpoints return a workspace-disabled error if the workspace feature flag is off (and write the audit entry for one-off initiation attempts; schedule management calls return the error without an audit entry since no export was attempted).

**Export Job Worker queue contract**

- Producer (Export Request Handler and Scheduler Service) writes: job identifier, report identifier, requesting user identifier, format, originating schedule identifier (nullable).
- Consumer (Export Job Worker) reads the above fields and writes back: job status update, artifact storage reference, size, retry count, audit log event.

**Scheduler internal contract**

- The Scheduler Service exposes no public API surface; it is driven by an internal timer/cron trigger.
- It reads ExportSchedule records and WorkspaceExportConfig to decide what to enqueue.
- It writes ScheduleRun records and reads ExportJob status back from the worker via job status updates.

**Notification / Delivery Service contract**

- Accepts: recipient user identifier (resolved to email internally — no external addresses accepted), notification type (export-ready | export-failed | export-rejected | schedule-paused), payload (artifact download URL or error description, schedule identifier).
- Returns: delivery acknowledgement or delivery failure indicator (failure is logged but does not alter the export job or schedule status beyond what the retry logic already manages).

**Audit Log contract**

- Append-only write interface: event type, user identity, workspace identifier, report identifier, export job reference (nullable), format (nullable), feature-flag state, timestamp.
- No external delete or update interface.
- Read access is scoped to admin-level consumers only and is outside the scope of this feature.
