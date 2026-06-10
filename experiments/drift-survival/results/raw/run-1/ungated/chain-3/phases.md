# Phase plan: Scheduled Report Exports

## Phase 1: Foundation — feature flag, workspace config, and domain model

**Goal**

Stand up the data model and the two runtime controls (feature flag and workspace export config) that all subsequent phases depend on. Nothing user-visible is shipped, but the schema, the flag evaluation path, and the admin config API are production-ready.

**Scope**

- Database migrations for all domain entities: ExportJob, ExportSchedule, ExportRun, AuditEvent, WorkspaceExportConfig, FeatureFlag.
- Feature flag service implementation: single evaluation call, no restart required to observe a flag change.
- Admin API endpoints: get and set WorkspaceExportConfig (workspace admin only).
- Stub audit logger: accepts structured event payloads and appends to the persistent audit log (no consumers yet).

**Acceptance criteria**

- All migrations apply cleanly on a fresh database and roll back without data loss.
- Feature flag evaluation returns the correct boolean for `export-feature` within one request cycle of the flag value changing, without a process restart.
- Admin get/set workspace export config endpoints return correct responses and are inaccessible to non-admin roles.
- Audit logger persists a record with the correct fields (event type, actor, report, format, schedule, timestamp, outcome, metadata) when called directly.

---

## Phase 2: One-off export — API layer and export worker

**Goal**

Deliver the end-to-end one-off export path: a user can request a CSV or PDF export of a report, the job is processed asynchronously, the artifact is written to object storage, and every meaningful state transition is audited.

**Scope**

- Initiate one-off export endpoint: feature flag check, workspace-enabled check, report access check, ExportJob creation in pending status, async enqueue, returns job identifier.
- Get export job status endpoint: returns current status, artifact download URL on completion, error detail on rejection or failure. Restricted to the initiating user.
- Export worker: dequeues jobs, applies row-level permissions using the requesting user's identity, generates CSV and PDF artifacts, enforces the 50 MB size limit (rejects and audits if exceeded), writes artifact to object storage, marks job completed or failed, emits audit events.
- Audit events wired for all job state transitions: triggered, completed, rejected, failed.

**Acceptance criteria**

- Initiating an export when the feature flag is off returns a not-available response; no job is created.
- Initiating an export when workspace exports are disabled returns a not-available response; no job is created.
- Initiating an export for a report the user cannot access returns unauthorized.
- A valid export request returns a job identifier immediately without waiting for artifact generation.
- A job whose artifact would exceed 50 MB is marked rejected with a size-limit error detail; an audit event with rejected outcome is recorded.
- A successfully processed job is marked completed; the artifact is retrievable via the status endpoint's download URL; an audit event with completed outcome is recorded.
- A worker failure marks the job failed and records an audit event.
- The status endpoint is inaccessible to any user other than the job initiator.

---

## Phase 3: Scheduler — recurring exports and delivery

**Goal**

Enable users to create recurring export schedules. The scheduler enqueues jobs on time, delivers artifacts by email, retries on delivery failure, pauses exhausted schedules, and records run history.

**Scope**

- Create export schedule endpoint: feature flag check, workspace-enabled check, report access check, ExportSchedule creation in active status.
- Update schedule status endpoint: pause or resume a schedule. Restricted to schedule owner.
- Get schedule run history endpoint: returns up to 30 ExportRun records. Restricted to schedule owner.
- Delete export schedule endpoint: removes schedule and run history. Restricted to schedule owner.
- Scheduler component: time-driven evaluation of active schedules, ExportJob creation owned by the schedule owner, ExportRun record creation, consumes worker completion events.
- Email delivery: dispatches artifact to schedule owner on job completion; updates ExportRun delivery status to success; audits delivery.
- Retry logic: up to three delivery attempts; on exhaustion, schedule transitions to paused, failure notification email sent to owner, ExportRun delivery status updated, audit event emitted.
- ExportRun retention: prune oldest records when a schedule exceeds 30 runs.

**Acceptance criteria**

- Creating a schedule when the feature flag is off or workspace exports are disabled returns a not-available response; no schedule is created.
- Creating a schedule for an inaccessible report returns unauthorized.
- A schedule in active status produces an ExportJob and an ExportRun at each elapsed frequency interval.
- Scheduled jobs apply row-level permissions using the schedule owner's identity, not the current request context.
- Successful artifact delivery updates the ExportRun delivery status to success and records an audit event.
- A delivery failure increments the attempt count and re-queues delivery.
- After three consecutive delivery failures, the schedule is paused, the owner receives a failure notification email, and an audit event is emitted.
- A schedule with more than 30 ExportRuns has the oldest pruned so that at most 30 remain.
- Pause and resume endpoints correctly update schedule status and are inaccessible to non-owners.
- Run history endpoint returns correct records and is inaccessible to non-owners.
- Delete endpoint removes the schedule and its run history and is inaccessible to non-owners.

---

## Phase 4: Admin disable control and feature flag gate in UI

**Goal**

Ensure that disabling exports at the workspace level or toggling the feature flag off immediately hides all export surfaces in the UI and blocks all API paths, making the kill-switch end-to-end effective.

**Scope**

- UI reads the feature flag on load and renders no export-related elements when the flag is off.
- UI reads WorkspaceExportConfig on load and hides all export surfaces when exports are disabled.
- Admin UI (or admin-facing surface) for setting the workspace export-enabled flag, backed by the admin API from Phase 1.
- Integration verification that toggling the flag or the workspace config propagates to both the API layer and the UI without a deployment or restart.

**Acceptance criteria**

- When `export-feature` flag is off, no export UI elements are rendered and all export API endpoints return a not-available response.
- When workspace exports are disabled via the admin API, no export UI elements are rendered and all export API endpoints return a not-available response.
- Re-enabling the flag or workspace config restores full export functionality without a deployment.
- The admin workspace export config control is inaccessible to non-admin users in both the UI and the API.
- Audit events for admin config changes are recorded by the audit logger.
