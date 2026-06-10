# Technical Approach: Scheduled Report Exports

## Architecture outline

The export feature introduces three new subsystems layered onto the existing reporting module:

**Export service** — a backend service responsible for generating export files (CSV and PDF). It receives export requests, queries the report data source while enforcing row-level permissions for the requesting user, serializes the output, and stores the resulting file. Generation runs asynchronously: the caller receives a job reference immediately and polls or is notified when the export is ready. The service enforces a 50 MB output cap and rejects requests that would exceed it.

**Scheduler service** — a backend service that manages recurring export schedules. It stores schedule definitions (owner, report reference, frequency, status) and drives execution by enqueuing export jobs on the configured cadence. It maintains per-schedule run history (last 30 entries) and handles the retry-and-pause lifecycle: up to three delivery retries per run; automatic pause and owner notification on exhaustion.

**Delivery service** — a thin email-dispatch layer invoked after successful export generation for scheduled runs. It sends the export file (or a link to it) to the schedule owner's address only. No third-party recipients are permitted.

**Feature flag layer** — a workspace-level gate, disabled by default at launch, that the export service and scheduler service check before processing any request. When the flag is disabled by an admin, all export endpoints and scheduled jobs are inert.

**Audit log integration** — both the export service and delivery service emit structured audit events at each significant transition (job initiated, file generated, delivery attempted, delivery succeeded, delivery failed, schedule paused).

The existing reporting module is unchanged except for the addition of export entry points (download buttons, schedule management UI). All heavy work runs out-of-band from interactive report viewing.

---

## Domain model

**Report** — an existing entity. Referenced by exports and schedules; not modified by this feature.

**ExportJob** — represents a single export generation request, whether initiated by a user on demand or by the scheduler. Fields: identifier, owning user, referenced report, requested format (CSV or PDF), status (pending / running / completed / failed / rejected), initiated-at timestamp, completed-at timestamp, rejection or failure reason, and a reference to the produced file artifact when complete.

**ExportFile** — the produced artifact. Fields: identifier, size in bytes, format, storage location reference, created-at timestamp. Linked 1:1 from a completed ExportJob.

**ExportSchedule** — a recurring schedule owned by one user for one report. Fields: identifier, owner user, referenced report, output format, frequency (daily or weekly), status (active / paused), created-at timestamp, next-run-at timestamp. A schedule has many ScheduleRunRecords.

**ScheduleRunRecord** — one entry in a schedule's run history. Fields: identifier, parent schedule, triggered-at timestamp, outcome (success / failure), attempt count, associated ExportJob identifier, failure reason when applicable.

**WorkspaceExportSettings** — workspace-level administrative configuration. Fields: workspace identifier, exports-enabled boolean. Controls the feature flag.

Relationships:
- One user owns zero or more ExportJobs and zero or more ExportSchedules.
- One ExportSchedule references one Report; one ExportJob references one Report.
- One ExportJob produces at most one ExportFile.
- One ExportSchedule has many ScheduleRunRecords; each ScheduleRunRecord is linked to the ExportJob that was created for that run.

---

## Key workflows

**On-demand export (CSV or PDF)**

1. User requests an export for a report they have access to.
2. The feature flag is checked against the workspace; if disabled, the request is rejected with a clear message.
3. An ExportJob is created in `pending` status; the job identifier is returned to the caller immediately.
4. Asynchronously, the export service fetches report data applying the user's row-level permission filter.
5. The service estimates or streams output size; if it would exceed 50 MB, the job transitions to `rejected` and a human-readable error is surfaced to the user.
6. Otherwise, the file is serialized to the requested format, stored, and an ExportFile is created. The ExportJob transitions to `completed`.
7. An audit event is emitted for both initiation and completion (or rejection).
8. The user is notified (UI polling or push) that the file is ready and can download it.

**Scheduled export execution**

1. The scheduler service fires for each active ExportSchedule whose `next-run-at` has elapsed.
2. The feature flag is checked; if disabled, the run is skipped (schedule is not paused, just deferred).
3. An ExportJob is created as in the on-demand flow, using the schedule owner's identity for permission enforcement.
4. On successful file generation, the delivery service emails the file or a download link to the schedule owner only.
5. A ScheduleRunRecord is written with outcome `success`. The schedule's `next-run-at` is advanced.
6. Audit events are emitted for job initiation, completion, and delivery.

**Scheduled export retry and pause**

1. If export generation or email delivery fails, the attempt count on the ScheduleRunRecord is incremented.
2. The job is re-enqueued for retry. Steps repeat up to 3 retries.
3. If all 3 retries fail, the ExportSchedule transitions to `paused`, the run record is finalized as `failure`, and a notification email is sent to the schedule owner explaining the automatic pause.
4. An audit event is emitted for the pause action.

**Schedule management (owner)**

- Owner creates a schedule: chooses report, format, frequency; schedule is saved as `active` with the next-run-at computed from the current time and frequency.
- Owner pauses a schedule: status set to `paused`; no further jobs are enqueued until resumed.
- Owner resumes a schedule: status set to `active`; next-run-at is recomputed from the current time.
- Owner views run history: the last 30 ScheduleRunRecords for the schedule are returned, each showing outcome, timestamps, and any failure reason.

**Admin disabling exports**

1. Admin sets `exports-enabled = false` on WorkspaceExportSettings.
2. All subsequent export requests (on-demand or scheduled) are rejected at the feature flag check.
3. Existing schedules remain stored but produce no deliveries while the flag is off.

---

## Contracts

**Export API**

- *Initiate on-demand export* — accepts a report identifier and desired format (CSV or PDF); returns an ExportJob identifier and initial status. Requires the requesting user to have access to the report. Gated by the workspace feature flag.
- *Get export job status* — accepts an ExportJob identifier; returns current status, and when complete, a short-lived download URL for the ExportFile. Scoped to the owning user.
- *Download export file* — serves the binary file content for a completed ExportJob. Enforces ownership.

**Schedule management API**

- *Create schedule* — accepts report identifier, format, and frequency; creates an ExportSchedule in `active` status for the authenticated user. Gated by the workspace feature flag.
- *List schedules* — returns all ExportSchedules owned by the authenticated user, including status and next-run-at.
- *Pause schedule* — accepts a schedule identifier; transitions status to `paused`. Scoped to owner.
- *Resume schedule* — accepts a schedule identifier; transitions status to `active` and recomputes next-run-at. Scoped to owner.
- *Get run history* — accepts a schedule identifier; returns the most recent 30 ScheduleRunRecords for that schedule, ordered newest-first. Scoped to owner.

**Admin API**

- *Get workspace export settings* — returns current `exports-enabled` state for the workspace.
- *Update workspace export settings* — accepts an `exports-enabled` boolean; updates WorkspaceExportSettings. Requires admin role.

**Internal service interfaces**

- *Export service <- scheduler service* — the scheduler enqueues an export job request carrying: schedule identifier, report identifier, owner user identity, format, and attempt number. The export service processes this identically to an on-demand request except it routes the result to the delivery service on success.
- *Delivery service <- export service* — after successful scheduled export generation, the export service calls the delivery service with: ExportFile reference, schedule owner email address, schedule identifier, and run record identifier. The delivery service resolves the owner's email from user identity; no caller-supplied recipient overrides are accepted.
- *Audit log <- export service and delivery service* — each service emits structured events on state transitions. Events include: actor (user or system), action type, resource type and identifier, outcome, and timestamp.
- *Feature flag interface* — both the export service and scheduler service query WorkspaceExportSettings by workspace identifier before processing any work. This check is synchronous and fast (cacheable).
