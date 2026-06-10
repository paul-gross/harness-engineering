# Phase Plan: Scheduled Report Exports

## Phase 1: Core Export Job Infrastructure

**Goal**
Establish the foundational data model, queue infrastructure, and Export Service HTTP API needed to run a single on-demand export end-to-end.

**Scope**
- `ExportJob` model with status lifecycle (`pending → generating → succeeded | failed`), artifact location, error detail, and attempt tracking
- `WorkspaceExportSettings` model with `exports_enabled` flag; admin API endpoints (`GET` and `PATCH /workspaces/{workspace_id}/export-settings`)
- Export Service `POST /exports` and `GET /exports/{job_id}` endpoints; workspace flag check and user report-access check on initiation
- Export worker: consumes job messages, calls Reporting module query interface with user identity for row-level filtering, enforces 50 MB size limit, renders CSV and PDF artifacts, stores artifacts in Export storage, updates job state
- Export storage integration (S3-compatible bucket or local blob store); time-limited download URL generation
- Audit Log integration in the Export Service: `export_requested`, `export_succeeded`, `export_failed` events

**Acceptance criteria**
- A request to `POST /exports` with a valid report ID and format returns an ExportJob ID and `pending` status within the HTTP response; the caller does not block on generation.
- The Export worker transitions the job to `succeeded` and stores the artifact; `GET /exports/{job_id}` returns `succeeded` and a valid download URL.
- A job whose rendered artifact would exceed 50 MB transitions to `failed` with a size-limit error message.
- When `exports_enabled` is `false`, `POST /exports` returns a rejection response and no job is created or enqueued.
- Setting `exports_enabled` via `PATCH /workspaces/{workspace_id}/export-settings` is restricted to workspace admins; non-admins receive a 403.
- Audit events `export_requested`, `export_succeeded`, and `export_failed` are written to the Audit Log for the corresponding job outcomes; the Audit Log entries include actor user ID, workspace ID, job ID, and timestamp.
- Row-level permission filtering is applied identically to the interactive report view: a user with restricted access cannot export rows they cannot view.

---

## Phase 2: Scheduling and Recurring Dispatch

**Goal**
Add the `ExportSchedule` and `ExportRun` models and the Scheduler component so that recurring exports are dispatched automatically.

**Scope**
- `ExportSchedule` model: owner, target report, frequency (`daily` / `weekly`), status (`active | paused`), `pause_source`, `next_delivery_at`
- `ExportRun` model: schedule reference, job reference, outcome (`delivered | failed | retrying`); retention cap of 30 runs per schedule
- Export Service endpoints: `POST /export-schedules`, `PATCH /export-schedules/{schedule_id}`, `GET /export-schedules/{schedule_id}/runs`; ownership validation on mutation and read
- Scheduler component: periodic tick (at minimum daily granularity), queries `active` schedules with `next_delivery_at` in the past, creates `ExportJob` and `ExportRun` records, enqueues jobs, updates `next_delivery_at`
- Export worker: detects schedule-triggered jobs (via optional schedule ID in job message), routes delivery to the Delivery Service instead of producing a download URL

**Acceptance criteria**
- `POST /export-schedules` creates a schedule with `active` status and a correctly computed `next_delivery_at`; non-owners cannot create schedules on behalf of other users.
- The Scheduler enqueues exactly one job per due active schedule per tick; `next_delivery_at` is advanced to the next occurrence after each dispatch.
- `GET /export-schedules/{schedule_id}/runs` returns at most 30 runs in descending creation-time order; only the schedule owner can retrieve the list.
- A non-owner request to `PATCH /export-schedules/{schedule_id}` is rejected with a 403.
- Export worker correctly distinguishes on-demand jobs (no schedule ID) from scheduled jobs (schedule ID present) and routes each to the appropriate delivery path.
- When `exports_enabled` is set to `false`, the Scheduler does not enqueue new jobs for any schedule; existing in-flight jobs complete normally.

---

## Phase 3: Delivery Service and Retry Logic

**Goal**
Complete the end-to-end scheduled delivery path by integrating the Delivery Service and implementing retry-to-pause logic.

**Scope**
- Delivery Service: accepts artifact reference, recipient email, report name, and schedule metadata; sends email; returns delivery status
- Export worker: calls Delivery Service after successful generation for scheduled jobs; on delivery failure increments attempt counter and re-enqueues job (up to 3 total attempts); updates `ExportRun` outcome (`retrying`, `delivered`, or `failed`)
- Auto-pause logic: after the third failed delivery attempt, the Export Service transitions the schedule to `paused` with `pause_source = system`
- Audit events: `retry_attempted` on each retry; `schedule_paused_by_system` when auto-pause fires
- Pause/resume workflow: `PATCH /export-schedules/{schedule_id}` with pause sets `pause_source = user`; resume sets status to `active` and recalculates `next_delivery_at` from the current time

**Acceptance criteria**
- A successfully generated scheduled export results in an email to the schedule owner's address; `ExportRun.outcome` is set to `delivered`.
- On delivery failure the job is re-enqueued; `ExportRun.outcome` is `retrying` and the attempt counter increments; a `retry_attempted` audit event is recorded.
- After three total delivery failures the schedule status transitions to `paused` with `pause_source = system`; a `schedule_paused_by_system` audit event is recorded; the `ExportRun` is marked `failed`; no further jobs are dispatched for that schedule.
- A user-initiated pause sets `pause_source = user`; in-flight jobs for that schedule complete normally; no new jobs are dispatched.
- A resume request sets status to `active` and sets `next_delivery_at` to the next future occurrence based on frequency and the current timestamp.
- Audit events for retry and system-pause carry actor user ID (schedule owner), workspace ID, job ID, schedule ID, and timestamp.

---

## Phase 4: Observability, Hardening, and Launch Readiness

**Goal**
Harden all components for production operation — run history pruning, audit completeness, end-to-end testing, and feature-flag-gated rollout.

**Scope**
- Run history pruning: enforce the 30-run retention cap per schedule (prune or archive older `ExportRun` records)
- Audit completeness review: verify all significant export events are captured; add any missing event types (e.g. schedule creation)
- End-to-end integration tests covering: on-demand export happy path, size-limit rejection, workspace-flag rejection, scheduled dispatch, retry-to-pause sequence, pause/resume lifecycle
- Load and concurrency validation: Scheduler tick does not enqueue duplicate jobs when overlapping ticks occur; Export worker handles concurrent jobs without artifact collision in Export storage
- Feature flag default-off verification: the `exports_enabled` flag defaults to `false` for all existing workspaces at deploy time; no export is possible until an admin explicitly enables it
- Operational runbook: artifact TTL / cleanup policy for Export storage; monitoring alerts for worker queue depth and delivery failure rate

**Acceptance criteria**
- `ExportRun` records beyond 30 per schedule are pruned or archived; `GET /export-schedules/{schedule_id}/runs` never returns more than 30 records.
- All significant export events (`export_requested`, `export_succeeded`, `export_failed`, `retry_attempted`, `schedule_paused_by_system`) are present in the Audit Log for a complete on-demand and scheduled flow exercised in a test environment.
- Integration test suite passes end-to-end for all key workflows: on-demand happy path, size-limit failure, flag-disabled rejection, scheduled dispatch with delivery, retry-to-pause sequence, and pause/resume.
- Concurrent Scheduler ticks do not produce duplicate `ExportJob` / `ExportRun` pairs for the same schedule in the same tick window.
- All existing workspaces have `exports_enabled = false` after deployment; no workspace gains export access without an explicit admin action.
- Artifact cleanup policy is documented and operationally enforced (e.g. TTL-based expiry on the object store).
