# Phase plan: scheduled report exports

## Phase 1: Foundation — domain model and core infrastructure

**Goal**
Establish the data layer, feature-flag integration, and the Export Service shell so that subsequent phases have a stable foundation to build on.

**Scope**
- Define and migrate database schemas for `ExportSchedule`, `ExportRun`, `ExportFile`, and `WorkspaceExportConfig`.
- Implement the `WorkspaceExportConfig` read/write path, including the admin API endpoint for setting the workspace kill switch.
- Wire up feature-flag and workspace kill-switch checks in the Export Service so that every inbound request is gated before any work is performed.
- Integrate with the existing Audit Log write interface; emit records for schedule creation and workspace-config changes.
- Stand up the Export Job Queue infrastructure (persistent queue + worker pool scaffold) with no job logic yet — workers receive jobs and acknowledge them without processing.

**Acceptance criteria**
- Database migrations apply cleanly in a fresh environment and roll back without data loss.
- The admin API endpoint updates `WorkspaceExportConfig`; subsequent reads return the updated state.
- A request to any Export Service endpoint when the workspace kill switch is disabled returns a feature-unavailable error and does not create any records.
- A request when the feature flag is off returns the same feature-unavailable error.
- Audit log records are written for workspace-config changes with all required fields populated (event type, user identity, workspace identifier, timestamp).
- The job queue infrastructure starts without error; a test job placed on the queue is acknowledged and logged by a worker.

---

## Phase 2: On-demand export

**Goal**
Deliver end-to-end on-demand export: a user can request a report export, the system generates the file asynchronously, enforces the size limit, and makes the result available for download.

**Scope**
- Implement the "initiate on-demand export" API endpoint: validate user access via the Reporting Service's permission model, create an `ExportRun` record in `pending` status, enqueue a generation job, and return a run identifier.
- Implement the "get export run status" API endpoint, restricted to the run owner.
- Implement the Export Job Queue worker: call the Reporting Service with the requesting user's identity, render to CSV or PDF, enforce the 50 MB size cap (mark `rejected` and discard if exceeded), write the file to Export Storage on success, and update the `ExportRun` record and audit log regardless of outcome.
- Implement the Export Storage write/read paths (upload on generation, generate a download reference for status polling).
- Emit audit log records for: export requested, export succeeded, export rejected, export failed.

**Acceptance criteria**
- A valid on-demand export request returns a run identifier synchronously; the HTTP response does not block on generation.
- Polling the run status endpoint reflects transitions: `pending` → `generating` → `succeeded` (or `rejected` / `failed`).
- A successfully generated file within the size limit is retrievable via the download reference returned in the status response; the file content matches a report rendered with the requesting user's row-level permissions.
- A report whose rendered output exceeds 50 MB produces a run with status `rejected`; no file is stored; the status endpoint returns a size-limit error detail.
- Requesting a run status for a run owned by a different user returns an authorization error.
- All audit log records for on-demand flows contain the required fields (run identifier, report identifier, user identity, workspace identifier, format, timestamp, event type).

---

## Phase 3: Scheduled export creation and execution

**Goal**
Deliver recurring scheduled exports: users can create a schedule and the system will generate and email the export at the configured cadence.

**Scope**
- Implement the "create export schedule" API endpoint: validate access, create the `ExportSchedule` record in `active` status, write an audit log entry.
- Implement the Scheduler component: poll for due active schedules, create `ExportRun` records in `pending` status, and enqueue generation jobs.
- Extend the Export Job Queue worker to handle scheduled runs: generate the export file using the schedule owner's permissions (same path as on-demand generation).
- Implement email delivery orchestration in the Export Service: on successful generation of a scheduled run, call the Email Delivery Service; on success update delivery status; on failure increment attempt count and re-enqueue (up to 3 attempts); on third failure set the `ExportSchedule` to `paused` and write an audit log entry for the automatic pause.
- Implement the "get schedule run history" API endpoint, returning up to 30 most recent `ExportRun` records for a schedule, restricted to the schedule owner.
- Emit audit log records for: delivery attempted, delivery succeeded, delivery failed, auto-paused.

**Acceptance criteria**
- Creating a schedule via the API returns a schedule identifier; the `ExportSchedule` record has status `active`.
- The Scheduler enqueues a generation job at the configured cadence; a `daily` schedule produces exactly one run per day; a `weekly` schedule produces exactly one run per week (verifiable via test-clock or time-manipulation in tests).
- A scheduled run uses the schedule owner's row-level permissions, not the requesting user's (confirmed by comparing output against a direct Reporting Service call with the owner's identity).
- On successful generation, the schedule owner receives an email containing or linking the export file.
- On email delivery failure, the attempt count increments; after 3 failed attempts the schedule transitions to `paused` and no further jobs are enqueued for it.
- The run history endpoint returns up to 30 records in reverse-chronological order, each with status, timestamps, attempt count, and delivery outcome; a request from a non-owner returns an authorization error.
- Audit log records for delivery events and auto-pause contain all required fields.

---

## Phase 4: Schedule management and workspace-level disable

**Goal**
Complete the feature by delivering schedule lifecycle controls (pause, resume, delete) and the workspace-level admin disable behavior, then harden the full flow with cleanup, expiry, and end-to-end verification.

**Scope**
- Implement the "update schedule status (pause / resume)" and "delete export schedule" API endpoints, both with ownership validation.
- Implement the "list export schedules" API endpoint for a user.
- Ensure the Scheduler skips paused and deleted schedules on each polling cycle.
- Implement the workspace-level disable behavior in the Scheduler: stop enqueuing new jobs for all schedules in a disabled workspace; handle in-flight jobs (complete or gracefully abandon).
- Implement `ExportFile` expiry: clean up stored files after delivery or after the expiry timestamp, whichever comes first.
- Emit audit log records for: schedule paused, schedule resumed, schedule deleted.
- End-to-end integration tests covering the full on-demand and scheduled flows, including the workspace kill-switch path.

**Acceptance criteria**
- Pausing a schedule stops the Scheduler from enqueuing further jobs for it; no new runs are created while the schedule is paused.
- Resuming a paused schedule causes the Scheduler to resume enqueuing jobs at the configured cadence.
- Deleting a schedule prevents any future runs; the schedule no longer appears in the list endpoint response.
- Only the schedule owner can pause, resume, or delete their schedule; requests from other users return authorization errors.
- When a workspace kill switch is disabled, no new export jobs are enqueued for any schedule in that workspace; users receive a feature-unavailable error on on-demand requests.
- In-flight generation jobs that began before a kill-switch disable either complete and deliver normally or are abandoned cleanly without leaving orphaned records.
- Generated files are removed from Export Storage after successful delivery or after their expiry timestamp, whichever comes first; no files remain in storage beyond their expiry.
- Audit log records for all schedule lifecycle events and workspace-disable events contain all required fields.
- A full end-to-end integration test passes: create schedule → run triggers → file generated → email delivered → pause → no new run → resume → run triggers again.
