# Phase plan: Scheduled report exports

## Phase 1: Foundation — audit log, feature flag, and domain model

**Goal**
Establish the data layer and the cross-cutting infrastructure that every subsequent phase depends on: the audit log, the workspace feature flag, and all domain entities.

**Scope**
- Create the `AuditLogEntry` append-only table and its write service; no update or delete paths are exposed.
- Add `exports_enabled` boolean to the `Workspace` entity and expose it via `PATCH /workspace/settings` (admin only).
- Create the `ExportRequest`, `ExportSchedule`, `ExportRun`, and `DeliveryAttempt` database tables with the relationships described in the domain model.
- Write repository/data-access layer for each new entity.
- No business logic beyond persistence; no job queue integration yet.

**Acceptance criteria**
- `PATCH /workspace/settings` with `exports_enabled: false` persists the flag; a subsequent read returns `false`.
- Writing an `AuditLogEntry` via the write service succeeds; a second call with the same data produces a second independent record (append-only confirmed).
- Attempting to update or delete an `AuditLogEntry` via the service is rejected.
- All new tables exist in the schema with correct foreign-key relationships and constraints (verified by migration tests or schema assertions).
- An `ExportSchedule` with 31 `ExportRun` rows correctly retains the 30 most recent when queried (capping behavior implemented at the query layer).

---

## Phase 2: One-off export service

**Goal**
Deliver the ability for users to request a one-off CSV or PDF export of a report, with feature-flag gating, row-level permission enforcement, size limiting, and full audit logging.

**Scope**
- Implement the background job queue integration for export jobs (job schema: type, report identifier, format, acting user identifier, export request or run identifier, attempt number).
- Implement the export worker: re-fetches row-level permissions at execution time, generates CSV or PDF artifact, enforces 50 MB limit.
- Implement the export service: creates `ExportRequest` in pending state, enqueues the job, writes `AuditLogEntry` on every outcome (success, size-limit rejection, feature-disabled rejection).
- Expose `POST /reports/{reportId}/exports` and `GET /exports/{exportId}` (status polling with time-limited download URL on completion).
- Feature flag checked at API entry; rejections still produce an `AuditLogEntry`.

**Acceptance criteria**
- `POST /reports/{reportId}/exports` when `exports_enabled` is `false` returns an error and creates a feature-disabled rejection `AuditLogEntry`; no `ExportRequest` row is created.
- A valid export request transitions through `pending` → `in-progress` → `completed`; the artifact download URL is available on `GET /exports/{exportId}`.
- An artifact exceeding 50 MB causes the `ExportRequest` to be marked `rejected` and writes a size-limit `AuditLogEntry`; the download URL is not present.
- The export worker does not reuse cached permission state: if a user's permissions are revoked between request and execution, the worker fetches updated permissions at generation time.
- Every outcome (success, size rejection, feature rejection, generation failure) produces exactly one `AuditLogEntry` with the correct event type and actor identity.

---

## Phase 3: Delivery service and scheduled export execution

**Goal**
Deliver the scheduler service, the delivery service, and the end-to-end scheduled export flow including retry logic, auto-pause, and owner notification.

**Scope**
- Implement the delivery service: accepts artifact reference, recipient email, run identifier; calls existing email infrastructure; returns `sent | failed`; caller updates `ExportRun` and triggers retry or pause logic.
- Implement the scheduler service: stores `ExportSchedule` definitions, determines due schedules at daily/weekly cadence, creates `ExportRun` records, enqueues export jobs with the schedule owner as acting user.
- Implement retry logic in the export worker for scheduled jobs: increment attempt count, re-enqueue if attempt < 3, mark `ExportRun` failed and pause `ExportSchedule` on attempt 3, send owner pause notification.
- Wire delivery service results back to `ExportRun` status and `DeliveryAttempt` records.
- Write `AuditLogEntry` for every scheduled run attempt (success and failure).

**Acceptance criteria**
- A due active schedule produces an `ExportRun` and an enqueued job; a non-due schedule does not.
- On successful generation and delivery: `ExportRun` is marked `success`, one `DeliveryAttempt` with status `sent` exists, and a success `AuditLogEntry` is written.
- On generation failure: attempt count is incremented; if attempt count < 3, the job is re-enqueued; if attempt count reaches 3, `ExportRun` is marked `failed`, `ExportSchedule` status becomes `paused`, the owner receives a pause notification email, and a final failed `AuditLogEntry` is written.
- The delivery service correctly reports `failed` when the email provider fails, and the caller (export service) initiates retry logic based on that result.
- A paused schedule is not picked up by the scheduler for new runs until explicitly resumed.
- The export worker re-evaluates the schedule owner's row-level permissions at generation time, not at schedule-creation time.

---

## Phase 4: Schedule management API and run history

**Goal**
Expose the full schedule management surface to users — create, list, fetch, pause, resume, delete, and view run history — completing the user-facing API.

**Scope**
- Implement `POST /reports/{reportId}/schedules` (create schedule, feature-flag gated).
- Implement `GET /schedules` (list caller's schedules with current status).
- Implement `GET /schedules/{scheduleId}` (single schedule with metadata).
- Implement `PATCH /schedules/{scheduleId}` (pause | resume; owner-only; no cancellation of in-flight runs).
- Implement `DELETE /schedules/{scheduleId}` (delete and stop future runs; owner-only).
- Implement `GET /schedules/{scheduleId}/runs` (last 30 runs, ordered by timestamp descending, with status, attempt count, and error detail).
- Enforce ownership: all mutation endpoints verify the calling user owns the schedule.

**Acceptance criteria**
- `POST /reports/{reportId}/schedules` when `exports_enabled` is `false` returns an error; no `ExportSchedule` row is created.
- A user can only pause, resume, or delete schedules they own; attempts by another user return a 403.
- `PATCH /schedules/{scheduleId}` with `status: paused` sets the schedule to paused; a subsequent scheduler run does not enqueue a job for it.
- `PATCH /schedules/{scheduleId}` with `status: active` on a system-paused schedule resumes it; the next scheduler run picks it up normally.
- `DELETE /schedules/{scheduleId}` removes the schedule; future scheduler runs do not process it; in-flight runs already enqueued complete normally.
- `GET /schedules/{scheduleId}/runs` returns at most 30 records ordered by `run_timestamp` descending, each containing timestamp, status, attempt count, and error detail.

---

## Phase 5: Reporting UI integration and end-to-end hardening

**Goal**
Surface all export and schedule management controls in the reporting UI and validate the complete system end-to-end, including the workspace admin disable flow.

**Scope**
- Add export controls to the reporting UI: one-off export button (CSV/PDF), polling or push notification for completion, download link on success, user-facing error on size-limit or feature-disabled rejection.
- Add schedule management UI: create schedule form (format, frequency), schedule list with status indicators, pause/resume/delete actions, run history view per schedule.
- Implement workspace admin UI for toggling `exports_enabled`.
- Validate the workspace admin disable flow: in-flight exports complete; pending scheduled jobs not yet picked up are skipped with a feature-disabled rejection and `AuditLogEntry`.
- Load and integration testing across the full export path; confirm audit log completeness across all scenarios.

**Acceptance criteria**
- A user can initiate a one-off export from the reporting UI, see a progress indicator, and download the artifact when complete without leaving the page.
- A user receives a visible error when an export is rejected for size limit or disabled feature flag.
- A user can create, pause, resume, and delete a schedule entirely from the UI; the run history view shows the last 30 runs with correct status and error detail.
- A workspace admin toggling `exports_enabled` to `false` causes all subsequent export and schedule creation requests to fail with a clear error in the UI.
- Scheduled jobs that were enqueued before the flag was disabled but not yet picked up are skipped; each produces a feature-disabled rejection `AuditLogEntry`.
- The audit log contains an entry for every attempted export action across all test scenarios — no gaps for any success, failure, or rejection path.
