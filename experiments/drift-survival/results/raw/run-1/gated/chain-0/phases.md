# Phase Plan: Scheduled Report Exports

## Phase 1: Data model and feature flag foundation

**Goal** — Establish the persistence layer and workspace-level feature flag that all later phases depend on. No user-facing behavior is delivered, but the database schema and flag check are in place and tested.

**Scope**
- Define and migrate the database schema for all new entities: `ExportJob`, `ExportFile`, `ExportSchedule`, `ScheduleRunRecord`, and `WorkspaceExportSettings`.
- Implement the `WorkspaceExportSettings` read/write repository and the synchronous feature-flag query used by downstream services.
- Implement the Admin API: `GET /workspace/export-settings` and `PATCH /workspace/export-settings`. Enforce admin-role authorization.
- Wire the feature flag check as a shared guard that can be called by both the export service and scheduler service.

**Acceptance criteria**
- All migrations run cleanly on a fresh database and in rollback.
- `WorkspaceExportSettings` defaults to `exports-enabled = false` when no row exists for a workspace.
- Admin API returns 403 for non-admin callers.
- Admin API round-trips: setting `exports-enabled = true` then querying returns `true`; setting `false` returns `false`.
- Feature flag guard returns "disabled" when `exports-enabled = false` and "enabled" when `true`.
- No export endpoints or job processing exist yet; this phase does not gate any user-facing surface.

---

## Phase 2: On-demand export service

**Goal** — Deliver working on-demand CSV and PDF exports that users can request, poll, and download, including the 50 MB cap and row-level permission enforcement.

**Scope**
- Implement the export service: accept export requests, create `ExportJob` in `pending` status, enqueue asynchronous generation work, and return the job identifier immediately.
- Implement asynchronous job processing: fetch report data with the requesting user's row-level permission filter, estimate/stream output size, reject at 50 MB, serialize to CSV or PDF, store the file, create `ExportFile`, and transition `ExportJob` to `completed` or `failed`/`rejected`.
- Implement the Export API:
  - `POST /export-jobs` — initiate on-demand export (gated by feature flag, scoped to report access).
  - `GET /export-jobs/:id` — poll status; return short-lived download URL when complete; scoped to owning user.
  - `GET /export-jobs/:id/download` — serve binary file content; enforces ownership.
- Emit structured audit events for: job initiated, file generated, job rejected (size), job failed.
- Add export entry points (download buttons) to the existing reporting module UI. These are visible only when the feature flag is enabled.

**Acceptance criteria**
- Requesting an export when the feature flag is disabled returns a clear rejection message; no `ExportJob` is created.
- Requesting an export for a report the user cannot access returns an authorization error.
- A valid request returns a job identifier immediately (before generation completes).
- Polling the job status reflects transitions: `pending` → `running` → `completed` (or `rejected`/`failed`).
- A completed job returns a short-lived download URL; fetching that URL delivers the correct file binary.
- Attempting to download another user's export returns an authorization error.
- A report whose export would exceed 50 MB transitions the job to `rejected` with a human-readable reason.
- Audit events are emitted and contain the correct actor, action, resource, outcome, and timestamp fields.
- CSV and PDF outputs both contain the expected report data for a user with partial row-level access (rows outside the user's permission are absent).

---

## Phase 3: Scheduler service and schedule management API

**Goal** — Enable users to create recurring export schedules (daily or weekly) and have the scheduler automatically enqueue export jobs on cadence.

**Scope**
- Implement the scheduler service: store `ExportSchedule` definitions, compute and persist `next-run-at`, poll for elapsed schedules, and enqueue export job requests to the export service using the schedule owner's identity.
- Implement the Schedule Management API:
  - `POST /schedules` — create schedule (gated by feature flag; compute initial `next-run-at`).
  - `GET /schedules` — list caller's schedules with status and `next-run-at`.
  - `POST /schedules/:id/pause` — set status to `paused`; scoped to owner.
  - `POST /schedules/:id/resume` — set status to `active`; recompute `next-run-at`; scoped to owner.
  - `GET /schedules/:id/run-history` — return most recent 30 `ScheduleRunRecord` entries, newest-first; scoped to owner.
- On each scheduler firing: check feature flag; if disabled, skip run without pausing the schedule; if enabled, create `ExportJob` via export service and write a `ScheduleRunRecord`.
- Advance `next-run-at` on successful run; write `ScheduleRunRecord` with outcome `success`.
- Add schedule management UI to the reporting module (create, pause, resume, view run history).

**Acceptance criteria**
- Creating a schedule returns an `ExportSchedule` in `active` status with a correctly computed `next-run-at`.
- Listing schedules returns only the authenticated user's schedules.
- Pausing a schedule prevents the scheduler from enqueuing new jobs for it; resuming re-enables it with a recomputed `next-run-at`.
- When the feature flag is disabled and a schedule's `next-run-at` elapses, no `ExportJob` is created and the schedule remains `active` (not paused).
- When the feature flag is enabled and `next-run-at` elapses, an `ExportJob` is created using the schedule owner's identity and the row-level permission filter is applied.
- After a successful run, `next-run-at` advances by the configured frequency (daily or weekly).
- `GET /schedules/:id/run-history` returns records newest-first, capped at 30, scoped to owner.
- Attempting to pause or view run history for another user's schedule returns an authorization error.
- `ScheduleRunRecord` is written for each triggered run with correct outcome, timestamps, and linked `ExportJob` identifier.

---

## Phase 4: Delivery service and retry-and-pause lifecycle

**Goal** — Complete the scheduled export flow by delivering the generated file to the schedule owner via email and implementing the retry-and-pause lifecycle for failures.

**Scope**
- Implement the delivery service: accept delivery requests from the export service (carrying `ExportFile` reference, schedule owner identity, schedule identifier, run record identifier), resolve the owner's email address from user identity, and dispatch the export file or download link via email. No caller-supplied recipient overrides accepted.
- Wire the export service to call the delivery service after successful scheduled export generation.
- Implement the retry-and-pause lifecycle in the scheduler service:
  - On export generation or email delivery failure, increment attempt count on `ScheduleRunRecord` and re-enqueue for retry.
  - Retry up to 3 times per run.
  - On exhaustion of all 3 retries, transition `ExportSchedule` to `paused`, finalize `ScheduleRunRecord` as `failure`, and send the owner a notification email explaining the automatic pause.
- Emit structured audit events for: delivery attempted, delivery succeeded, delivery failed, schedule paused (automatic).

**Acceptance criteria**
- After successful scheduled export generation, the schedule owner receives an email containing the file or a valid download link.
- The delivery service does not accept or use any recipient address other than the one resolved from the schedule owner's identity.
- On first failure (generation or delivery), the run is retried; the `ScheduleRunRecord` shows attempt count 2.
- On second failure, attempt count reaches 3 and a third retry is made.
- On third failure, attempt count reaches 4; all 3 retries are now exhausted and no further retries are enqueued.
- On exhaustion of all 3 retries, the `ExportSchedule` transitions to `paused`, the `ScheduleRunRecord` is finalized with outcome `failure`, and the owner receives a pause notification email.
- A paused schedule does not enqueue further jobs until the owner explicitly resumes it.
- Audit events are emitted for every delivery state transition and for the automatic pause action, with correct actor, action, resource, outcome, and timestamp fields.
- A manually paused schedule that fails during a run that started before the pause does not re-pause or re-notify (pause lifecycle is only triggered by retry exhaustion, not manual pause).
