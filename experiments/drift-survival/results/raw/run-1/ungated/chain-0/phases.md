# Phase Plan: Scheduled Report Exports

## Phase 1: Core Export Infrastructure

**Goal**
Establish the foundational export pipeline — the export service, job queue, async workers, and object storage integration — so that on-demand export generation works end to end for a single format.

**Scope**
- Implement the export service with `generateExport(reportId, userId, format)`, applying row-level permission rules via the existing report data access layer.
- Enforce the 50 MB size limit; raise a size-limit error when exceeded.
- Implement the job queue and async worker pool; workers call the export service, write artifacts to object storage, and update ExportRequest status.
- Implement the `ExportRequest` and `ExportArtifact` domain models and their persistence layer.
- Implement `enqueueExport(exportRequestId)`.
- Implement the on-demand export API endpoints: `POST /reports/{reportId}/exports` and `GET /exports/{exportId}`.
- Implement the audit log sink and `emitExportEvent`; emit `export.initiated`, `export.completed`, `export.rejected`, and `export.failed` at the correct lifecycle points.
- Support CSV format only in this phase.

**Acceptance criteria**
- A user with access to a report can initiate a CSV export; the API returns an ExportRequest identifier immediately.
- Polling `GET /exports/{exportId}` reflects status transitions: `pending` → `processing` → `completed`.
- The completed artifact is retrievable via the download URL returned when status is `completed`.
- An artifact that would exceed 50 MB is not written to storage; the ExportRequest transitions to `rejected` and the error is surfaced to the caller.
- A worker failure transitions ExportRequest to `failed`.
- Each lifecycle transition produces a corresponding AuditEvent record with correct event type, user identity, report identifier, and timestamp.
- Row-level permission rules are applied during generation; a user cannot retrieve rows they cannot see interactively.

---

## Phase 2: Feature Flag, Admin Control, and PDF Support

**Goal**
Gate the export feature behind a per-workspace feature flag and admin disable switch, and extend export generation to support PDF output, completing the on-demand export surface.

**Scope**
- Implement `WorkspaceExportConfig` domain model and persistence.
- Implement `isExportEnabled(workspaceId)` combining the global/per-workspace feature flag and the admin override; evaluate per request without caching beyond a short TTL.
- Enforce the feature flag and admin guard at the API boundary before any export operation; return a clear error when either disables exports.
- Implement the admin API: `PUT /workspace/export-config` (requires admin role) and `GET /workspace/export-config`.
- Add PDF as a supported export format to the export service and worker pipeline.

**Acceptance criteria**
- When the feature flag is disabled for a workspace, `POST /reports/{reportId}/exports` returns a clear error and no ExportRequest or job is created.
- When an admin disables exports for a workspace via `PUT /workspace/export-config`, subsequent export requests are rejected with a clear message; in-flight jobs at the moment of disabling run to completion.
- Re-enabling exports via the admin API immediately (within the configured TTL) allows new requests.
- A user can request a PDF export; the completed artifact is retrievable and contains the expected report content.
- CSV and PDF exports both enforce the 50 MB limit and emit the correct audit events.
- The admin config endpoint requires admin role; non-admin callers receive an authorization error.

---

## Phase 3: Scheduler and Recurring Export Delivery

**Goal**
Deliver recurring scheduled exports: the scheduler evaluates active schedules, fires export jobs, writes artifacts, and notifies schedule owners on successful delivery.

**Scope**
- Implement `ExportSchedule` and `ScheduledRun` domain models and their persistence layer.
- Implement the scheduler background process: periodic tick evaluates active ExportSchedules due for their next run, creates ScheduledRuns, and enqueues jobs via `enqueueScheduledRun(scheduledRunId)`.
- Workers execute scheduled jobs under the schedule owner's identity applying row-level permission rules; on success, transition ScheduledRun to `delivered` and write the artifact.
- Implement the notification service: `sendScheduledDelivery(userId, scheduleId, artifactLocation)` emails the artifact or download link to the schedule owner using the existing email infrastructure.
- Implement the schedule management API: `POST /reports/{reportId}/schedules`, `PATCH /schedules/{scheduleId}` (pause/resume), `GET /schedules/{scheduleId}/runs` (last 30 runs), and `DELETE /schedules/{scheduleId}`.
- Enforce schedule owner identity on all schedule mutation endpoints.
- Emit `export.completed` audit events on successful scheduled delivery.

**Acceptance criteria**
- Creating a schedule via `POST /reports/{reportId}/schedules` with a daily or weekly cadence results in an active ExportSchedule.
- The scheduler enqueues an export job at or after the configured cadence; a ScheduledRun record is created with status `pending`.
- On successful delivery the ScheduledRun transitions to `delivered`; an ExportArtifact is persisted; the schedule owner receives a delivery email containing the artifact or a valid download link.
- Pausing a schedule transitions it to `paused`; no further runs are enqueued while paused.
- Resuming a paused schedule transitions it to `active`; the scheduler resumes normal evaluation.
- `GET /schedules/{scheduleId}/runs` returns the last 30 ScheduledRuns with correct status and timestamps; access is restricted to the schedule owner.
- Deleting a schedule removes it and prevents further runs.
- The feature flag and admin guard apply to scheduled exports; a schedule for a disabled workspace does not produce new jobs.

---

## Phase 4: Retry Logic, Paused-on-Failure, and Operational Hardening

**Goal**
Complete the failure-handling path for scheduled exports — automatic retry with backoff, paused-on-failure state, and owner notification on persistent failure — and harden the system for production readiness.

**Scope**
- Implement `handleRunFailure(scheduledRunId)` in the scheduler: increment attempt count, re-enqueue with backoff if attempt count is less than 3, or transition the ScheduledRun and parent ExportSchedule to `paused-on-failure` on the third failure.
- Implement `sendPausedOnFailureNotice(userId, scheduleId)` in the notification service; call it when a schedule transitions to `paused-on-failure`.
- Emit `export.failed` audit events on each failed attempt.
- Validate that in-flight on-demand and scheduled jobs are not left orphaned on worker or scheduler restart (idempotency and at-least-once delivery guarantees).
- Validate the audit log completeness: every export lifecycle transition emitted by both the export service and the async workers produces a well-formed AuditEvent.
- Validate that the feature flag `isExportEnabled` TTL behavior is acceptable under expected flag-change propagation requirements.

**Acceptance criteria**
- When a scheduled export job fails on the first or second attempt, the ScheduledRun attempt count increments and the job is re-enqueued after the backoff interval; a new attempt is made without manual intervention.
- On the third consecutive failure the ScheduledRun transitions to `paused-on-failure`; the parent ExportSchedule transitions to `paused-on-failure`; no further runs are enqueued for that schedule.
- The schedule owner receives a paused-on-failure email identifying the affected schedule.
- A paused-on-failure schedule can be resumed by the owner via `PATCH /schedules/{scheduleId}`; the scheduler resumes normal evaluation after resumption.
- Workers restarted mid-job do not produce duplicate artifacts or duplicate audit events; jobs are picked up and completed correctly.
- The scheduler restarted mid-tick does not double-create ScheduledRuns or double-enqueue jobs for a given cadence window.
- All audit event types (`export.initiated`, `export.completed`, `export.rejected`, `export.failed`) are present and correctly attributed in the audit log for every exercised code path.
