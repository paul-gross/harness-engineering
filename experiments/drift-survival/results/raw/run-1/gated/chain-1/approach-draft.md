# Technical Approach: Scheduled Report Exports

## Architecture outline

The feature introduces three new subsystems layered onto the existing reporting module, coordinated through a central export service:

**Export service** — the core orchestrator. Receives export requests (one-off and scheduled), enforces workspace-level and row-level permissions, dispatches work to an async job queue, and records every significant event to the audit log. It is the single entry point for all export activity.

**Async job worker** — a background worker pool that consumes jobs from the queue. Workers retrieve report data through the existing report query engine (ensuring row-level permission filtering is applied at query time), generate the output file in the requested format (CSV or PDF), enforce the 50 MB size limit, and either store the file for download (one-off) or hand it to the delivery service (scheduled).

**Schedule manager** — owns the lifecycle of recurring export schedules. Stores schedule configuration, emits scheduled jobs on their cadence (daily/weekly), tracks run history (last 30 runs per schedule), manages pause/resume state, and applies the retry and auto-pause policy for failed deliveries.

**Delivery service** — handles email delivery of completed scheduled export files. Accepts a completed export artifact and a schedule record, sends to the schedule owner, and reports success or failure back to the schedule manager for retry accounting.

**Feature flag gate** — a thin middleware check evaluated before any export surface is reachable. Reads from the workspace feature flag store. When the flag is off, all export endpoints return a disabled response without touching other subsystems.

**Admin workspace toggle** — a workspace-level configuration record checked by the export service before processing any request. Distinct from the feature flag: the flag controls availability at rollout; the toggle is an operator control within a workspace. Mutations to the toggle are recorded in the audit log.

The existing report query engine is consumed by the async worker but is not modified. The existing audit log is extended with new event types; its schema and write path are not otherwise changed.

## Domain model

**ExportRequest** — represents a single one-off export. Attributes: id, workspace id, requesting user id, report id, format (CSV | PDF), status (pending | processing | complete | failed | rejected), created at, completed at, file reference (nullable), rejection reason (nullable).

**ExportSchedule** — represents a recurring export configuration. Attributes: id, workspace id, owner user id, report id, format, frequency (daily | weekly), state (active | paused), created at, updated at, paused at (nullable), paused reason (nullable — system-paused vs user-paused distinction).

**ScheduledRun** — one execution of a schedule. Attributes: id, schedule id, scheduled at, started at (nullable), completed at (nullable), status (pending | processing | delivered | failed | retried | abandoned), attempt count, delivery status detail. Retained for the last 30 runs per schedule; older records are pruned.

**WorkspaceExportConfig** — per-workspace admin settings. Attributes: workspace id, exports enabled (boolean), toggled by user id, toggled at.

**AuditEvent** — extends the existing audit log. New event types: export.initiated, export.completed, export.failed, export.rejected, schedule.created, schedule.paused, schedule.resumed, schedule.run.delivered, schedule.run.failed, schedule.run.retried, schedule.run.abandoned, workspace.export.disabled, workspace.export.enabled.

**Relationships:**
- An ExportSchedule has many ScheduledRuns (capped at 30).
- A ScheduledRun belongs to one ExportSchedule.
- An ExportRequest belongs to one user and one report.
- WorkspaceExportConfig is one-to-one with a workspace.
- AuditEvents reference any of the above entities by id.

## Key workflows

**One-off export**

1. User requests an export for a report in a given format.
2. Feature flag gate checks the flag for the workspace; if off, return disabled.
3. Export service checks WorkspaceExportConfig; if exports disabled, return disabled.
4. Export service verifies the user has access to the report.
5. Export service creates an ExportRequest record (status: pending) and enqueues a job.
6. Response returns immediately with the ExportRequest id (async acknowledgement).
7. Worker picks up the job, applies row-level permission filtering via the report query engine, generates the file.
8. If the generated file exceeds 50 MB, the worker marks ExportRequest as rejected with a size-limit reason and writes an audit event; no file is stored.
9. On success, the worker stores the file, marks ExportRequest complete, writes an audit event.
10. On failure, the worker marks ExportRequest failed and writes an audit event.
11. The user polls or is notified (via existing notification channel) that the export is ready or failed.

**Scheduled export — run execution**

1. Schedule manager fires a ScheduledRun for each active ExportSchedule whose cadence is due.
2. For each run, a ScheduledRun record is created (status: pending) and a job is enqueued.
3. Worker executes identically to the one-off flow (steps 7–9 above), except on success it passes the file to the delivery service rather than storing for download.
4. Delivery service emails the file to the schedule owner.
5. On delivery success, ScheduledRun is marked delivered; an audit event is written.
6. On delivery failure, ScheduledRun status is set to failed; attempt count is incremented; an audit event is written.
7. Schedule manager evaluates retry eligibility: if attempt count < 3, re-enqueue with backoff (status: retried).
8. If attempt count reaches 3 and delivery still fails, ScheduledRun is marked abandoned, the ExportSchedule is set to paused (paused reason: system), and an audit event is written.

**Pause and resume**

1. Owner requests pause of a schedule.
2. Export service verifies the requestor is the schedule owner.
3. ExportSchedule state is set to paused (paused reason: user); no future runs are emitted until resumed.
4. Audit event written.
5. Owner requests resume; export service verifies ownership; state is set to active; audit event written.
6. Any runs that were pending in the queue while paused are discarded (not executed after resume).

**Admin workspace toggle**

1. Admin sets exports enabled/disabled on the workspace.
2. WorkspaceExportConfig is updated; audit event written with the admin's user id, timestamp, and previous/new state.
3. Any in-progress export jobs complete normally (toggle is checked at request initiation, not mid-job).
4. Active schedules remain in their current state; if exports are re-enabled, active schedules resume emitting runs normally.

**Feature flag enable/disable**

- When the flag is enabled, all export surfaces become reachable; no data migration is required.
- When the flag is disabled, export endpoints return a disabled response; no schedules are paused and no data is deleted. Re-enabling restores full functionality.

## Contracts

**Export API (user-facing)**

- Initiate one-off export: accepts report id and format; validates access; returns export request id and status. Synchronous submission, asynchronous execution.
- Get export status: accepts export request id; returns current status, completion timestamp, download reference if complete, rejection reason if rejected.
- Download export file: accepts export request id; returns the file if status is complete and the requesting user is the original requester.

**Schedule API (user-facing)**

- Create schedule: accepts report id, format, and frequency; creates an active schedule for the calling user; returns schedule id.
- Pause schedule: accepts schedule id; validates ownership; transitions state to paused.
- Resume schedule: accepts schedule id; validates ownership; transitions state to active.
- Get schedule: accepts schedule id; returns schedule configuration and state.
- List schedules: returns all schedules owned by the calling user in the workspace.
- Get run history: accepts schedule id; returns the last 30 ScheduledRun records with status and timestamps.

**Admin API**

- Get workspace export config: returns current enabled state and last-toggled metadata.
- Set workspace export config: accepts enabled boolean; updates config; writes audit event.

**Internal interfaces**

- Export service → Job queue: enqueue message containing export request id or scheduled run id, type (one-off | scheduled), and format.
- Worker → Report query engine: request report data for a given report id and user id; engine applies row-level permission filtering and returns a result set or streaming cursor.
- Worker → Delivery service: submit completed file artifact, schedule id, and run id for email delivery.
- Schedule manager → Job queue: enqueue scheduled run job on cadence; discard pending jobs on schedule pause.
- Any subsystem → Audit log: write event with event type, acting user id, workspace id, entity id, and timestamp.

**Feature flag interface**

- Evaluated as a boolean gate keyed by workspace id and feature flag name. No parameters beyond workspace context are required. Returns enabled or disabled.
