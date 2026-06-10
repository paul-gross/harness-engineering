# Phase Plan — Scheduled Report Exports

## Phase 1: Foundation — feature flag, kill-switch, and domain scaffolding

**Goal**

Establish the guarding layer and core data model so that all subsequent phases build on a stable, gateable foundation. No export logic is shipped to users until this phase is complete.

**Scope**

- Define the `WorkspaceExportSettings` table and admin API endpoint (read/write of `exports-enabled`).
- Implement the feature flag and admin kill-switch guard: evaluate flag then workspace setting, return allow/deny with reason code.
- Wire the guard as middleware in front of all export route namespaces (routes return 404 or 403 before any export logic exists behind them).
- Create database migrations and model skeletons for `ExportJob`, `ExportSchedule`, and `ScheduledRun` (schema only; no business logic).
- Extend the audit log schema with the eight export-specific event types; verify the existing sink accepts them without error.

**Acceptance criteria**

- When the feature flag is off, all export-namespaced API routes are unreachable (no route registered or 404 returned consistently).
- When the feature flag is on and `exports-enabled` is false for a workspace, requests from that workspace to export routes are rejected with the expected reason code before reaching any handler.
- When both checks pass, requests reach the (stub) handler and receive a 501 or placeholder response.
- An admin can toggle `exports-enabled` via the admin settings API; the change is reflected on the next request within the same process.
- All eight audit event types can be written to the audit log sink without error; written events are retrievable with their common attributes intact.
- Migrations run cleanly on a fresh schema and roll back without data loss.

---

## Phase 2: On-demand export — job queue and export service

**Goal**

Deliver end-to-end on-demand export for authenticated users: a user can request a CSV or PDF export of a report they have access to, the job runs in the background, and the artifact is available for download.

**Scope**

- Implement the export service internal interface: accepts report identifier, user identity, and format; enforces row-level permissions; renders the artifact; enforces the 50 MB size limit; returns artifact with byte size or a structured error.
- Stand up the dedicated export worker pool within the existing job queue infrastructure.
- Implement the on-demand export API endpoints: enqueue endpoint (returns job identifier and status URL) and status/download endpoint (returns current status and download URL when complete).
- Implement `ExportJob` lifecycle transitions: `pending` → `running` → `succeeded` / `failed` / `rejected`.
- Write audit events at each lifecycle stage: `export.initiated`, `export.succeeded`, `export.failed`, `export.rejected`.
- Deliver user-facing notifications for export ready and export failed states.

**Acceptance criteria**

- A user with report access can request an export via the API; the response contains a job identifier and a pollable status URL.
- Polling the status URL reflects the current job status in real time.
- On success the status endpoint returns a download URL; the artifact is the correct format and contains only rows the requesting user has permission to see.
- An artifact exceeding 50 MB transitions the job to `rejected`; the status endpoint returns an error and no download URL is provided.
- An unrecoverable generation error transitions the job to `failed`; the error detail is present in the status response.
- All four on-demand audit events are written with correct actor identity, report identity, format, timestamp, and outcome detail.
- A user without access to the report cannot obtain an export of it; the job is rejected before generation begins.

---

## Phase 3: Scheduled exports — scheduler, retry logic, and email delivery

**Goal**

Enable recurring scheduled exports: users can configure a schedule, the system runs exports automatically at the configured cadence, retries on failure, auto-pauses after three consecutive failures, and delivers artifacts by email.

**Scope**

- Implement the email delivery adapter: accepts recipient address and artifact, dispatches via the existing transactional email infrastructure, returns delivery acknowledgement or structured error.
- Implement the scheduler: reads active `ExportSchedule` records whose next-run time is due, creates `ScheduledRun` records, enqueues `ExportJob`s using the schedule owner's identity and permissions, advances next-run time on success, manages retry (up to 3 attempts with backoff), transitions the schedule to `paused` after three consecutive failures, and notifies the owner on auto-pause.
- Implement `ScheduledRun` lifecycle: `delivered`, `failed`, `auto-paused`; attempt number incremented per retry.
- Prune run history to the 30 most recent `ScheduledRun` records per schedule.
- Write audit events for all scheduled export lifecycle stages: `scheduled_export.initiated`, `scheduled_export.delivered`, `scheduled_export.failed`, `scheduled_export.paused`.

**Acceptance criteria**

- An active schedule with a due next-run time is picked up by the scheduler; a `ScheduledRun` is created and a job is enqueued using the schedule owner's identity.
- On successful job completion the artifact is delivered by email to the schedule owner; the `ScheduledRun` is recorded as `delivered`; the schedule's next-run time is advanced to the next cadence interval.
- On a single job failure the `ScheduledRun` is recorded as `failed` and a retry is enqueued after the backoff interval with attempt number incremented.
- After three consecutive failed attempts the `ExportSchedule` transitions to `paused`, the final `ScheduledRun` is recorded as `auto-paused`, the owner receives a notification, and the scheduler skips the schedule on subsequent cycles.
- Run history per schedule never exceeds 30 records; records beyond the cap are pruned automatically.
- All four scheduled audit event types are written with correct attributes at the appropriate lifecycle points.
- A paused schedule receives no jobs from the scheduler until it is manually resumed.

---

## Phase 4: Schedule management API and UI surfaces

**Goal**

Give users full self-service control over their export schedules, and ensure all export UI surfaces are suppressed when the feature flag or admin kill-switch is active.

**Scope**

- Implement the schedule management CRUD endpoints: create (report, format, frequency), list owned schedules, update (pause, resume, change frequency), delete. All endpoints gated by the feature flag and admin kill-switch guard.
- Implement the run history read endpoint: returns the last 30 `ScheduledRun` records for a given schedule.
- Deliver UI entry points for on-demand export and schedule management, wired to the above endpoints.
- Suppress all export UI components when the feature flag is off or the admin kill-switch is active for the user's workspace.
- Validate that deleting a schedule does not delete associated run history records needed for audit purposes (or documents the retention policy if records are removed).

**Acceptance criteria**

- A user can create, list, update (pause/resume/frequency change), and delete their own schedules via the API; they cannot read or modify another user's schedules.
- The run history endpoint returns at most 30 records for a given schedule, ordered by triggered-at descending.
- When the feature flag is off, no export UI components are rendered on any page; no export API routes are reachable.
- When `exports-enabled` is false for a workspace, users in that workspace see no export UI and receive the expected denial response from the API.
- Existing `ExportSchedule` records for a workspace with `exports-enabled` false are not deleted; toggling the setting back to true causes the schedules to resume without data loss.
- All CRUD operations on schedules are reflected correctly in subsequent list and run-history responses.
