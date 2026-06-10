# Phase Plan: Scheduled Report Exports

## Phase 1: Foundation — Export Service and On-Demand Export

**Goal**
Deliver the core export capability: users can request a report export on demand and download the resulting file. All supporting infrastructure (feature flag, workspace admin toggle, audit log integration) is wired in this phase.

**Scope**
- ExportJob domain model and persistence
- WorkspaceExportSettings model and persistence
- Feature flag and workspace admin toggle gate checks at export entry points
- Export Service: permission-aware report data fetching, CSV and PDF generation, 50 MB size cap enforcement
- On-demand Export API: initiate export endpoint, poll-for-status endpoint, time-limited download URL
- Workspace Admin API: get and update export settings endpoints
- Audit log writes for export-initiated, export-completed, and export-rejected events

**Acceptance criteria**
- A user with report access can request a CSV or PDF export and receive a download URL upon completion
- A user without report access receives an immediate rejection
- An export that would exceed 50 MB transitions to rejected status and returns a clear rejection reason; no file is produced
- Audit log records one export-initiated event at job creation and one export-completed or export-rejected event at resolution
- Closing the workspace admin toggle causes all subsequent export requests to be rejected immediately; re-enabling it allows exports again
- Closing the feature flag causes all subsequent export requests to be rejected immediately
- Poll endpoint returns current job status and, when completed, a time-limited download URL

---

## Phase 2: Email Delivery Channel

**Goal**
Introduce the Email Delivery Channel abstraction so that completed exports can be sent to a recipient, decoupled from the Scheduler Service that will use it in the next phase.

**Scope**
- Email Delivery Channel interface and implementation wrapping the platform's existing email infrastructure
- Accepts a single recipient email address, a subject line, and a file attachment handle
- Returns a delivery acknowledgement or a structured delivery error
- Unit and integration coverage for the delivery channel in isolation

**Acceptance criteria**
- Calling the Email Delivery Channel with a valid recipient, subject, and attachment handle results in an email being sent with the file attached
- The interface enforces single-recipient-only; passing multiple recipients is rejected at the interface boundary
- A delivery failure from the underlying email infrastructure surfaces as a structured delivery error rather than an unhandled exception
- The Scheduler Service does not yet exist; the channel is verified as a standalone component

---

## Phase 3: Scheduler Service and Scheduled Export Execution

**Goal**
Deliver the Scheduler Service: recurring export schedules can be created and executed, with retry logic, auto-pause on repeated failure, and email delivery of completed exports.

**Scope**
- ExportSchedule domain model and persistence (owner, report, format, cadence, state, pause reason)
- ScheduledRun domain model and persistence (status, attempt count, triggered and concluded timestamps, run history capped at 30)
- Scheduler Service: cadence-based firing, feature flag and workspace toggle gate check per run (producing skipped runs when closed), Export Service invocation on behalf of schedule owner, retry logic (up to 3 attempts), auto-pause after third consecutive failure
- Email Delivery Channel integration: completed export file routed to schedule owner's email
- Audit log writes for schedule-auto-paused events and schedule state change events

**Acceptance criteria**
- An active ExportSchedule triggers a ScheduledRun at each configured cadence tick; the Export Service is invoked with the schedule owner's identity and permissions
- A run that fails is retried; attempt count increments with each retry; after a third consecutive failure the schedule transitions to paused with a system-set pause reason and a schedule-auto-paused audit event is written
- A successful run results in an email sent to the schedule owner's address with the export file attached; no other recipients receive the email
- A run triggered when the feature flag or workspace admin toggle is closed is recorded as skipped; no export is attempted and no email is sent
- Run history for a schedule never exceeds 30 entries; older entries are trimmed after each run
- A skipped run does not count toward the consecutive-failure retry counter

---

## Phase 4: Schedule Lifecycle Management API

**Goal**
Expose the full user-facing Schedule Management API so users can create, pause, resume, and inspect their export schedules.

**Scope**
- Schedule Management API: create schedule, list schedules, pause schedule, resume schedule, get run history endpoints
- Ownership enforcement: only the schedule owner may pause, resume, or retrieve run history for a schedule
- Audit log writes for schedule-created, schedule-paused, and schedule-resumed events
- Clearing of auto-pause reason on resume

**Acceptance criteria**
- A user can create a schedule specifying a report, format, and cadence; the schedule is created in active state and a schedule-created audit event is written
- Creating a schedule for a report the user cannot access is rejected
- Creating a schedule when the feature gate is closed is rejected
- List schedules returns all and only the authenticated user's schedules with current state and cadence
- A user can pause their own schedule; the schedule transitions to paused and a schedule-paused audit event is written; no further runs fire
- A user cannot pause another user's schedule
- A user can resume their own schedule; auto-pause reason is cleared; the schedule transitions to active and a schedule-resumed audit event is written; runs resume at the next cadence tick
- Get run history returns the last 30 ScheduledRun records for a schedule the caller owns, each with status, attempt count, and timestamps
- A user cannot retrieve run history for a schedule they do not own
