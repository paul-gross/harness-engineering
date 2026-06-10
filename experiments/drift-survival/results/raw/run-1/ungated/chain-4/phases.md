# Phase Plan: Scheduled Report Exports

## Phase 1: Core Export Infrastructure

**Goal**
Establish the foundational data model and the one-off export path end-to-end, including the feature-flag gate, audit logging, and artifact delivery.

**Scope**
- Define and migrate the database schema for `ExportJob`, `AuditLogEntry`, and `WorkspaceExportConfig`.
- Implement the Export Request Handler: feature-flag check, user access verification, `ExportJob` creation, and job enqueuing.
- Implement the Export Job Worker: row-level permission filtering, CSV and PDF stream rendering, 50 MB size constraint enforcement, artifact upload to object storage, job status transitions, and audit log writes.
- Implement the Notification / Delivery Service for `export-ready`, `export-failed`, and `export-rejected` event types (email to authenticated owner only).
- Expose the HTTP endpoints: initiate one-off export and get job status.

**Acceptance criteria**
- A user with view access to a report can request a CSV or PDF export and receive a job reference.
- The export artifact is produced asynchronously, stored in object storage, and retrievable via the status URL.
- Artifacts exceeding 50 MB are rejected; the job status reflects `rejected` and the user receives a rejection email.
- Requests against a workspace with `exports-enabled = false` return a workspace-disabled error and write a `rejected` audit log entry; no job is created.
- Users without view access to the target report receive a 403 and no job is created.
- Processing failures increment the retry counter and re-enqueue up to the platform ceiling; after the final failure the job is marked `failed` and a failure email is sent.
- All notable export events (initiated, completed, failed, rejected) appear in the audit log with correct user, workspace, and feature-flag-state fields.
- Audit log entries are append-only; no update or delete path exists.

---

## Phase 2: Scheduler Service and Recurring Delivery

**Goal**
Layer recurring export schedules on top of the Phase 1 worker, enabling users to configure daily or weekly exports delivered by email.

**Scope**
- Define and migrate the database schema for `ExportSchedule` and `ScheduleRun`.
- Implement the Scheduler Service: schedule evaluation on each cron tick, feature-flag and workspace-config check before enqueuing, `ExportJob` creation linked to the originating schedule, next-run timestamp advancement, and `ScheduleRun` record writes.
- Implement the consecutive-failure counter: on third consecutive failure, set schedule status to `paused`, write a `schedule-paused` audit log entry, and dispatch a pause notification email.
- Extend the Notification / Delivery Service to handle `schedule-paused` and scheduled-delivery email types (artifact attachment or download link).
- Expose the HTTP endpoints: create schedule, pause schedule, resume schedule, and get schedule run history (most recent 30 runs).

**Acceptance criteria**
- A user can create a schedule specifying report, format, and frequency; the schedule persists with status `active`.
- The scheduler tick enqueues an `ExportJob` for each due active schedule and the job is processed identically to a one-off export.
- On successful completion the schedule owner receives the export artifact by email and a `ScheduleRun` record is written with status `success`.
- On failure a `ScheduleRun` record is written with status `failed`; on the third consecutive failure the schedule transitions to `paused`, a `schedule-paused` audit log entry is written, and the owner receives a pause notification email.
- When a workspace has `exports-enabled = false`, the scheduler tick skips all schedules for that workspace — no job is created and no audit entry is written for the skip.
- A user can pause and resume their own schedule; paused schedules produce no jobs on subsequent ticks; resuming clears the consecutive-failure counter.
- A user can retrieve the 30 most recent `ScheduleRun` records for a schedule they own; they cannot access run history for schedules owned by others.
- Schedule management endpoints (create, pause, resume, history) return a workspace-disabled error when the feature flag is off, without writing an audit entry.

---

## Phase 3: Observability, Edge-Case Hardening, and Admin Controls

**Goal**
Harden the system for production operation: close edge-case gaps, add workspace-admin controls, and ensure the audit log and monitoring surfaces are reliable.

**Scope**
- Implement the workspace admin flow for disabling and re-enabling exports via `WorkspaceExportConfig`; verify that re-enabling restores existing schedules without recreation.
- Add idempotency guards to the Export Job Worker to prevent duplicate artifact production if a job message is delivered more than once.
- Enforce ownership checks consistently across all schedule-management endpoints and harden the user-identity resolution in the Notification / Delivery Service.
- Validate that audit log writes are non-blocking with respect to export-job success/failure outcomes (audit failure must not silently suppress the job result).
- Add structured logging and metrics instrumentation to the Export Job Worker and Scheduler Service (job processing latency, queue depth, retry rate, schedule-pause rate).
- Write integration tests covering the full one-off and scheduled export paths against a test object-storage backend.

**Acceptance criteria**
- An admin disabling exports stops all new one-off requests and scheduler enqueuing immediately; re-enabling restores all previously active schedules without any user action.
- Redelivering a job message to the Export Job Worker does not produce a duplicate artifact or a duplicate audit log entry.
- Attempting to pause, resume, or view the run history of a schedule owned by another user returns an authorization error.
- Audit log writes failing (e.g., transient storage error) do not cause the job to be marked failed; the error is logged separately.
- End-to-end integration tests pass for: successful one-off CSV export, successful one-off PDF export, 50 MB rejection, workspace-disabled rejection, three-failure schedule pause, and scheduled delivery email.
- Metrics for job processing latency, retry count, and schedule-pause count are emitted and visible in the observability stack.

---

## Phase 4: Polish, Documentation, and Rollout Readiness

**Goal**
Prepare the feature for a safe, incremental production rollout: finalize the feature-flag rollout controls, document the operational runbook, and confirm readiness through load and chaos testing.

**Scope**
- Finalize the `WorkspaceExportConfig` feature-flag plumbing so the flag can be toggled per workspace without a deploy.
- Implement graceful worker shutdown: in-progress jobs complete before the worker exits; no jobs are lost during deploys.
- Define and document the retry ceiling and queue timeout values as explicit configuration rather than hard-coded constants.
- Write the operational runbook covering: enabling/disabling per workspace, interpreting audit log entries, manually re-queuing a stuck job, and handling a full object-storage partition.
- Run load tests simulating peak concurrent export jobs and scheduled-tick bursts; confirm the queue and worker pool scale within acceptable latency bounds.
- Conduct a chaos test: kill worker mid-job and verify the job is re-queued and completes on the next worker pickup with no duplicate artifact.

**Acceptance criteria**
- The feature flag can be toggled for a single workspace via an admin API call without redeploying the service.
- Deploying a new worker version during active job processing does not lose or corrupt any in-flight jobs.
- Retry ceiling and queue timeout values are externalized in configuration and documented with their default values and tuning guidance.
- The operational runbook exists, covers all four documented scenarios, and has been reviewed by at least one on-call engineer.
- Load tests show no job failures and p99 artifact-ready latency within the agreed SLO under peak load.
- Chaos test confirms a killed worker results in the job completing on the next pickup with exactly one artifact and one completed audit log entry.
