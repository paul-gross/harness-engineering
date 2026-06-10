# Implementation Phases: Scheduled Report Exports

## Phase 1: Foundation — Data model, feature flag gate, and workspace toggle

**Goal**

Establish the persistence layer and the two availability controls (feature flag gate and admin workspace toggle) that gate all export functionality. No export work is performed yet, but the infrastructure that would allow or deny it is fully operational.

**Scope**

- Database migrations for all domain model tables: `ExportRequest`, `ExportSchedule`, `ScheduledRun`, `WorkspaceExportConfig`.
- Audit log schema extension for all new event types (records are written in later phases; the schema is ready now).
- Feature flag gate middleware: reads the workspace-scoped flag and returns a disabled response when off.
- `WorkspaceExportConfig` record seeded per workspace (exports disabled by default).
- Admin API: `GET /workspace/export-config` and `PUT /workspace/export-config`; mutations write `workspace.export.enabled` / `workspace.export.disabled` audit events.
- Export service skeleton: entry-point exists, checks feature flag and `WorkspaceExportConfig`, returns disabled when appropriate.

**Acceptance criteria**

- All migrations apply cleanly against a fresh database and roll back without error.
- Calling any export endpoint with the feature flag off returns a disabled response; no other subsystem is touched.
- Calling any export endpoint with the flag on but `WorkspaceExportConfig.exports_enabled = false` returns a disabled response.
- Admin `PUT /workspace/export-config` toggles the enabled state and writes an audit event containing the acting user id, workspace id, previous state, new state, and timestamp.
- Admin `GET /workspace/export-config` returns the current enabled state.
- No export jobs are enqueued by anything in this phase.

---

## Phase 2: One-off export — async job pipeline and file delivery

**Goal**

Allow a user to request a one-off export, receive an asynchronous acknowledgement, and later download the completed file (or learn why it failed).

**Scope**

- Export service request handling: permission check (user access to report), `ExportRequest` record creation (status: pending), job enqueue.
- Export API: `POST /exports` (initiate), `GET /exports/:id` (status), `GET /exports/:id/download` (file retrieval, requester-only).
- Async job worker: dequeues one-off jobs, invokes the report query engine with the user id for row-level permission filtering, generates CSV and PDF output.
- 50 MB size enforcement: worker marks `ExportRequest` as `rejected` with size-limit reason and writes `export.rejected` audit event if limit is exceeded; no file is stored.
- On success: file stored, `ExportRequest` marked `complete`, `export.completed` audit event written.
- On failure: `ExportRequest` marked `failed`, `export.failed` audit event written.
- `export.initiated` audit event written at request creation.

**Acceptance criteria**

- `POST /exports` returns an `ExportRequest` id and `pending` status synchronously.
- A worker picks up the job, queries the report through the existing report query engine, and produces a valid CSV or PDF file.
- Row-level permission filtering is applied by the report query engine (verified by asserting the worker passes the requesting user id and that the engine's existing filter path is exercised).
- A file exceeding 50 MB causes the request to transition to `rejected` with the size-limit reason; no file is stored; `export.rejected` is written to the audit log.
- A successful export transitions the request to `complete`; the file is retrievable via `GET /exports/:id/download` only by the original requester.
- A simulated worker failure transitions the request to `failed`; `export.failed` is written to the audit log.
- All four audit event types (`export.initiated`, `export.completed`, `export.failed`, `export.rejected`) contain the required fields: event type, acting user id, workspace id, entity id, timestamp.
- The report query engine codebase has no modifications.

---

## Phase 3: Scheduled exports — schedule lifecycle and run execution

**Goal**

Allow users to create recurring export schedules that automatically execute and deliver files by email on a daily or weekly cadence, with retry logic and auto-pause on persistent failure.

**Scope**

- Schedule API: `POST /schedules` (create, starts active), `POST /schedules/:id/pause`, `POST /schedules/:id/resume`, `GET /schedules/:id`, `GET /schedules` (list by owner), `GET /schedules/:id/runs` (last 30 runs).
- Schedule manager: persists `ExportSchedule` records, emits `ScheduledRun` jobs on the configured cadence, discards pending jobs when a schedule is paused, tracks run history capped at 30 (pruning older records).
- Delivery service: accepts a completed file artifact, schedule id, and run id; sends email to the schedule owner; reports success or failure.
- Retry policy in the schedule manager: on delivery failure, increment attempt count and re-enqueue with backoff if attempt count < 3.
- Auto-pause: on third delivery failure, mark `ScheduledRun` as `abandoned`, set `ExportSchedule` to `paused`, write `schedule.run.abandoned` audit event.
- Pause/resume ownership validation: only the schedule owner may pause or resume.
- Audit events for schedule lifecycle: `schedule.created`, `schedule.paused`, `schedule.resumed`, `schedule.run.delivered`, `schedule.run.failed`, `schedule.run.retried`, `schedule.run.abandoned`.

**Acceptance criteria**

- `POST /schedules` creates an `ExportSchedule` in `active` state and writes a `schedule.created` audit event.
- The schedule manager emits a `ScheduledRun` job at the correct cadence (daily or weekly); a `ScheduledRun` record with status `pending` is created before the job is enqueued.
- A successful run results in an email delivered to the schedule owner and the `ScheduledRun` transitioning to `delivered`; `schedule.run.delivered` is written to the audit log.
- On delivery failure the attempt count increments and the job is re-enqueued (up to attempt count 2); `schedule.run.retried` is written.
- On the third delivery failure the `ScheduledRun` is marked `abandoned`, the `ExportSchedule` transitions to `paused`, and `schedule.run.abandoned` is written.
- A paused schedule emits no further jobs; pending jobs for the schedule are discarded.
- `POST /schedules/:id/pause` by a non-owner returns an authorization error; the schedule state does not change.
- `POST /schedules/:id/resume` by the owner transitions state to `active`; `schedule.resumed` is written.
- `GET /schedules/:id/runs` returns at most 30 records; creating a 31st run causes the oldest record to be pruned.
- The worker execution path for scheduled runs is identical to the one-off path (same size limit, same permission filtering, same audit events for export-level outcomes).

---

## Phase 4: End-to-end hardening and operational readiness

**Goal**

Ensure the complete feature is reliable under failure conditions, observable in production, and correctly restricted by both availability controls across every surface.

**Scope**

- Integration tests covering the full one-off flow, the full scheduled-run flow, the retry-and-auto-pause sequence, and the pause/resume lifecycle.
- Negative-path coverage: feature flag off, workspace toggle off, unauthorized access attempts, report access denied, size limit exceeded, worker crash mid-job.
- Audit log completeness verification: assert every defined event type is emitted by its triggering action and contains all required fields.
- Observability instrumentation: structured log lines and/or metrics at job enqueue, job start, job complete/fail, delivery attempt, delivery success/fail, auto-pause trigger.
- Graceful worker shutdown: in-progress jobs complete or requeue safely; no `ExportRequest` or `ScheduledRun` is left permanently in `processing` state after a restart.
- Load and size boundary testing: confirm 50 MB limit is enforced consistently across CSV and PDF paths.

**Acceptance criteria**

- Full one-off export flow passes end-to-end in a staging environment: flag on, toggle enabled, user has access, file under limit, file downloadable.
- Full scheduled export flow passes end-to-end: schedule created, run executed on cadence, file emailed.
- Retry sequence tested end-to-end: three delivery failures result in `abandoned` run and `paused` schedule with all expected audit events.
- Feature flag off returns disabled on every export endpoint; no jobs are enqueued.
- Workspace toggle off returns disabled on every export endpoint; no jobs are enqueued.
- A user without access to the report receives an authorization error at request time; no job is enqueued.
- Worker restart simulation leaves no records permanently stuck in `processing`; affected records are recoverable (re-queued or marked `failed`).
- Every audit event type listed in the domain model is covered by at least one automated test asserting the required fields are present.
- Structured log output for a complete scheduled run contains log lines for enqueue, start, complete, delivery attempt, and delivery success.
