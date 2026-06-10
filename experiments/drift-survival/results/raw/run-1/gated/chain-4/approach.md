# Technical Approach: Scheduled Report Exports

## Architecture Outline

The feature introduces two new subsystems that integrate with the existing reporting module: an **Export Service** and a **Scheduler Service**. Both operate behind a single feature flag and are subject to a workspace-level admin toggle.

**Export Service** handles the transformation of report data into downloadable file formats (CSV and PDF). It runs asynchronously, decoupled from the interactive report view, so that export generation does not compete with live queries for resources. It applies the requesting user's row-level permissions at generation time, enforces a 50 MB size cap before delivering output, and writes every export event to the audit log.

**Scheduler Service** manages the lifecycle of recurring export schedules. It maintains schedule configuration (cadence, owner, paused state) and drives periodic job execution. At each scheduled run it invokes the Export Service on behalf of the schedule owner and routes the resulting file to an email delivery channel. It tracks run history per schedule, implements retry logic (up to 3 attempts), and automatically pauses a schedule after a third consecutive failure.

**Email Delivery Channel** is a thin abstraction over the platform's existing email infrastructure. The Scheduler Service calls it with a recipient (the schedule owner only), a subject, and an attached export file. This keeps email mechanics out of the Scheduler Service and allows the delivery mechanism to evolve independently.

**Audit Log** is an existing cross-cutting service. Both the Export Service and the Scheduler Service write structured events to it — one event per export generation and one event per schedule state change.

**Feature Flag + Workspace Admin Toggle** sit in front of both subsystems. The feature flag governs whether the capability is available on the platform at all; the workspace admin toggle provides a per-workspace override. Any request to initiate an export or a scheduled run is rejected at the entry point if either gate is closed.

Component interaction summary:
- Report View → Export Service (on-demand export request)
- Scheduler Service → Export Service (scheduled run triggers export)
- Export Service → Audit Log (export event)
- Scheduler Service → Email Delivery Channel (send completed export)
- Scheduler Service → Audit Log (schedule state change events)
- All entry points → Feature Flag + Workspace Admin Toggle (gate check)

---

## Domain Model

**Report** (existing entity, referenced but not owned by this feature)
- Identified by a report ID
- Associated with a set of row-level permission rules
- Accessed by users with appropriate permissions

**ExportJob**
- Belongs to a single requesting user (the permission principal)
- References a Report
- Has a format (CSV or PDF)
- Has a status (pending, in-progress, completed, rejected, failed)
- Records file size once generation completes
- Records a rejection reason when the size cap is exceeded or generation fails
- Carries a timestamp

**ExportSchedule**
- Belongs to a single owner (user)
- References a Report
- Has a format (CSV or PDF)
- Has a cadence (daily or weekly)
- Has a state (active or paused)
- Contains a pause reason when automatically paused due to failure

**ScheduledRun**
- Belongs to an ExportSchedule
- References the ExportJob it produced (if generation was attempted)
- Has a status (succeeded, failed, retrying, skipped)
- Records the attempt count (1–3)
- Records a timestamp for when the run was triggered and when it concluded
- A schedule retains the last 30 ScheduledRun records

**AuditEvent** (existing entity, extended)
- Actor (user ID or system for scheduled runs)
- Action type (export-initiated, export-completed, export-rejected, schedule-created, schedule-paused, schedule-resumed, schedule-auto-paused)
- Target identifiers (report ID, export job ID, schedule ID as applicable)
- Timestamp and workspace context

**WorkspaceExportSettings** (new per-workspace configuration)
- Workspace identifier
- Export enabled flag (admin-controlled)

---

## Key Workflows

### On-Demand Export

1. User requests an export of a report in a chosen format from the report view.
2. The system checks the feature flag and the workspace's export-enabled setting; if either gate is closed, the request is rejected immediately with an appropriate error.
3. An ExportJob is created in pending state for the requesting user and report.
4. An audit event is written recording the export initiation.
5. The Export Service fetches report data applying the user's row-level permissions — only permitted rows are included.
6. The service estimates or measures the output size; if it would exceed 50 MB the job transitions to rejected, an audit event is written, and the user is notified with a clear explanation.
7. If within the size limit, the file is generated and the ExportJob transitions to completed.
8. An audit event is written recording successful completion.
9. The file is made available for the user to download.

### Scheduled Export — Run Execution

1. The Scheduler Service fires at the configured cadence for each active ExportSchedule.
2. A ScheduledRun record is created (attempt 1).
3. The feature flag and workspace export-enabled setting are checked; if either gate is closed, the run is recorded as skipped and no export is attempted.
4. The Export Service is invoked on behalf of the schedule owner, applying their row-level permissions exactly as in the on-demand flow.
5. If generation fails or the size limit is exceeded, the ScheduledRun is marked failed. If attempt count is below 3, a retry is scheduled and attempt count is incremented. If the third attempt fails, the ExportSchedule is transitioned to paused with a system-set pause reason, and an audit event is written for the auto-pause.
6. On successful generation, the file is passed to the Email Delivery Channel, which sends it to the schedule owner's email address only.
7. The ScheduledRun is marked succeeded with a completion timestamp.
8. Run history for the schedule is trimmed to the most recent 30 entries.

### Schedule Lifecycle Management

1. A user creates a schedule by specifying a report, format, and cadence. The schedule is created in active state. An audit event is written.
2. A user pauses a schedule: the schedule transitions to paused state. An audit event is written. No further runs are triggered until resumed.
3. A user resumes a schedule: the schedule transitions back to active state. The failure-based auto-pause reason is cleared. An audit event is written. Runs resume at the next cadence tick.

---

## Contracts

### Export API (HTTP, user-facing)

**Initiate on-demand export**
Accepts a report identifier and a desired format. Returns an export job identifier and initial status. Rejects immediately if the feature gate is closed or the user does not have access to the report.

**Poll export job status**
Accepts an export job identifier. Returns current status, and when completed provides a time-limited download URL for the generated file. Returns a rejection reason when the job is in rejected or failed state.

### Schedule Management API (HTTP, user-facing)

**Create schedule**
Accepts a report identifier, format, and cadence. Creates a new active ExportSchedule for the authenticated user. Rejects if the feature gate is closed or the user does not have access to the report.

**List schedules**
Returns all ExportSchedules owned by the authenticated user, including current state and cadence.

**Pause schedule**
Accepts a schedule identifier. Transitions the schedule to paused. Only the schedule owner may call this. Returns the updated schedule.

**Resume schedule**
Accepts a schedule identifier. Transitions the schedule to active. Only the schedule owner may call this. Returns the updated schedule.

**Get run history**
Accepts a schedule identifier. Returns the last 30 ScheduledRun records for that schedule, each with status, attempt count, and timestamps.

### Internal: Export Service Interface

Accepts a report identifier, a requesting user identity (used as the permission principal), and a desired format. Returns either a generated file handle with size metadata or a structured error (size-exceeded, permission-error, generation-error). This interface is called by both the on-demand API handler and the Scheduler Service.

### Internal: Email Delivery Interface

Accepts a recipient email address (always the schedule owner), a subject line, and a file attachment handle. Returns a delivery acknowledgement or a structured delivery error. Does not support multiple recipients.

### Workspace Admin API (HTTP, admin-facing)

**Get export settings**
Returns the WorkspaceExportSettings for the caller's workspace.

**Update export settings**
Accepts an updated export-enabled flag. Persists the change. Affects all subsequent export requests and scheduled runs for the workspace immediately.

### Audit Log Contract (internal write interface)

Structured event writes with: actor identity, action type (drawn from the enumerated action types in the domain model), target entity references, timestamp, and workspace context. Both the Export Service and Scheduler Service use this interface; the implementation is owned by the existing audit subsystem.
