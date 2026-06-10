# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature consists of five main components:

1. **Export Service** — handles one-off and scheduled report export generation, format conversion, and delivery orchestration
2. **Permission Enforcer** — applies row-level access control during export generation to prevent data leakage
3. **Scheduler** — manages the lifecycle of scheduled export definitions and triggers execution at configured intervals
4. **Email Delivery System** — delivers generated exports via email with retry logic and failure handling
5. **Audit Logger** — records all export events for compliance and transparency

These components interact as follows:
- Users interact with the **Export Service** via the reporting module UI to trigger one-off exports or create scheduled exports
- The **Scheduler** periodically evaluates scheduled exports and invokes the **Export Service** to generate reports
- The **Export Service** consults the **Permission Enforcer** to ensure the requesting user only sees authorized rows
- Generated exports are passed to the **Email Delivery System** for sending to recipients
- The **Audit Logger** records export initiation, completion, delivery attempts, and failures throughout the flow
- A **Feature Flag** gates visibility of export UI controls and enforces export endpoint access

## Domain Model

### Core Entities

**Report**
- Identifier (report ID)
- Definition (query, filters, columns, permissions model)
- Owner
- Row-level access control rules

**Export**
- Identifier (export ID)
- Report reference
- Format (CSV or PDF)
- Requested by (user)
- Generated at (timestamp)
- File blob (the exported data)
- Size (bytes)
- Status (generated, delivered, failed)
- Audit trail entry reference

**ScheduledExport**
- Identifier (schedule ID)
- Report reference
- Owner (schedule creator and recipient)
- Format (CSV or PDF)
- Frequency (daily or weekly)
- Day of week (if weekly)
- Time of day
- Status (active or paused)
- Paused at (timestamp, if paused)
- Paused by (user ID, if paused)
- Created at (timestamp)
- Last executed at (timestamp)
- Retention policy (keep last 30 runs)

**ExportRun**
- Identifier (run ID)
- ScheduledExport reference
- Status (success or failed)
- Attempted at (timestamp)
- Completed at (timestamp)
- Failure reason (if status is failed)
- Delivery attempt count (1-3)
- Next retry scheduled (timestamp, if applicable)

**AuditLogEntry**
- Event type (export_created, export_generated, export_delivered, export_failed, schedule_created, schedule_paused, schedule_resumed, schedule_deleted)
- Timestamp
- User ID (who initiated or triggered)
- Resource (report ID, export ID, schedule ID)
- Outcome (success or failure)
- Details (format, size, error message)

### Relationships

- A **Report** has many **Exports** (one-off exports)
- A **Report** has many **ScheduledExports** (recurring exports)
- A **ScheduledExport** has many **ExportRuns** (execution history, limited to 30)
- Each **Export** or **ExportRun** has one **AuditLogEntry**
- Each **ScheduledExport** is owned by one **User** and delivers to that user only

## Key Workflows

### Workflow 1: One-Off Export

1. User selects a report and initiates an export, specifying CSV or PDF format
2. Export Service validates the export request:
   - Check feature flag is enabled
   - Verify user has read access to the report
   - Validate format selection
3. Export Service generates a report using the requesting user's row-level permissions:
   - Query the report data
   - Apply Permission Enforcer to filter rows
   - Generate output in requested format
4. Export Service validates size:
   - If size > 50 MB, reject with user-facing error and log failure audit event
   - If size ≤ 50 MB, proceed
5. Audit Logger records the export generation
6. System returns export download link or initiates browser download

### Workflow 2: Create Scheduled Export

1. User navigates to scheduled exports section and creates a new schedule
2. User specifies:
   - Report to export
   - Export format (CSV or PDF)
   - Frequency (daily or weekly)
   - Day of week (if weekly)
   - Time of day for export to run
3. Export Service validates the request:
   - Check feature flag is enabled
   - Verify user has read access to the report
   - Validate frequency and time configuration
4. ScheduledExport record is created with status = "active"
5. Audit Logger records the schedule creation
6. Scheduler immediately schedules the first execution based on the configured time

### Workflow 3: Execute Scheduled Export

1. Scheduler detects that a scheduled export's next execution time has arrived
2. Scheduler invokes Export Service to generate the report using the schedule owner's permissions
3. Export Service generates report:
   - Apply Permission Enforcer to filter rows based on schedule owner's access
   - Generate output in configured format
   - Validate size (reject if > 50 MB)
4. If generation succeeds, pass export file to Email Delivery System
5. Email Delivery System attempts delivery:
   - Send email with export attachment to schedule owner
   - Record delivery attempt
6. If delivery succeeds:
   - ExportRun created with status = "success"
   - Audit Logger records successful delivery
   - Scheduler calculates next execution time
7. If delivery fails:
   - ExportRun created with status = "failed", attempt count incremented
   - If attempt count < 3, schedule retry
   - If attempt count == 3, pause the schedule and mark ScheduledExport with status = "paused"
   - Audit Logger records failure and auto-pause event

### Workflow 4: Pause/Resume Schedule

1. User navigates to scheduled exports list
2. User selects a schedule and chooses pause or resume
3. Schedule Service updates the ScheduledExport record:
   - If pause: status = "paused", paused_at = now, paused_by = user_id
   - If resume: status = "active", paused_at = null, paused_by = null
4. Scheduler cancels any pending executions for paused schedules
5. Audit Logger records the pause/resume event

### Workflow 5: View Export History

1. User navigates to scheduled exports list
2. User selects a schedule and views execution history
3. System retrieves the last 30 ExportRun records for the ScheduledExport
4. UI displays:
   - Execution timestamp
   - Status (success or failed)
   - Failure reason (if failed)
   - Delivery attempt count

### Workflow 6: Disable Export Feature (Admin)

1. Workspace admin accesses the feature flag configuration
2. Admin disables the export feature flag
3. Feature Flag Service propagates the change
4. On next request, all export endpoints check the flag and reject with 403 if disabled
5. Export UI controls are hidden via conditional rendering
6. Scheduled exports continue to exist (for re-enabling) but execution is skipped
7. Audit Logger records the admin action

## Contracts

### Export Service Interface

**GenerateExport(reportId, userId, format) → Export**
- Input: report identifier, requesting user ID, export format (CSV or PDF)
- Output: Export object with file blob, size, status
- Behavior: applies row-level permissions, generates formatted output, validates size
- Errors: report not found, user lacks permission, format invalid, size exceeds limit

**GenerateScheduledExport(scheduledExportId) → ExportRun**
- Input: scheduled export identifier
- Output: ExportRun object with status, generated at, completion time
- Behavior: generates report using schedule owner's permissions, validates size
- Errors: scheduled export not found, report not found, size exceeds limit

### Scheduled Export Service Interface

**CreateScheduledExport(reportId, userId, format, frequency, dayOfWeek, timeOfDay) → ScheduledExport**
- Input: report ID, creating user ID, format, frequency, optional day of week, time of day
- Output: ScheduledExport object with ID, created status
- Behavior: validates inputs, creates persistent schedule record, schedules first execution
- Errors: report not found, user lacks permission, invalid frequency

**PauseScheduledExport(scheduleId, userId) → ScheduledExport**
- Input: schedule ID, user ID
- Output: updated ScheduledExport with status = paused
- Behavior: validates user is schedule owner, pauses future executions, cancels pending runs
- Errors: schedule not found, user is not owner, schedule already paused

**ResumeScheduledExport(scheduleId, userId) → ScheduledExport**
- Input: schedule ID, user ID
- Output: updated ScheduledExport with status = active
- Behavior: validates user is schedule owner, calculates next execution, resumes scheduler
- Errors: schedule not found, user is not owner, schedule not paused

**GetScheduledExportHistory(scheduleId, limit) → [ExportRun]**
- Input: schedule ID, limit (default 30)
- Output: list of ExportRun objects ordered by timestamp descending
- Behavior: retrieves up to the most recent N execution records
- Errors: schedule not found

**GetScheduledExportsByReport(reportId) → [ScheduledExport]**
- Input: report ID
- Output: list of ScheduledExport objects
- Behavior: retrieves all active and paused schedules for a report
- Errors: report not found

### Email Delivery Interface

**SendExportEmail(recipientEmail, fileName, fileBlob, subject) → DeliveryAttempt**
- Input: recipient email address, file name, file content, email subject
- Output: DeliveryAttempt record with status, timestamp
- Behavior: sends email with export attachment, records attempt
- Errors: email invalid, file too large, SMTP failure

**RetryFailedDelivery(exportRunId, maxAttempts) → DeliveryAttempt**
- Input: export run ID, maximum allowed attempts
- Output: DeliveryAttempt record
- Behavior: resends email, increments attempt counter, schedules next retry if still under limit
- Errors: max attempts exceeded, export run not found

### Permission Enforcer Interface

**FilterReportRowsByUserAccess(reportId, userId, data) → data**
- Input: report ID, user ID, report data rows
- Output: filtered data rows visible to the user
- Behavior: applies row-level access control rules to data, removes unauthorized rows
- Errors: report not found, user not found

### Scheduler Interface

**ScheduleExportExecution(scheduleId, executionTime) → void**
- Input: schedule ID, execution time (absolute or relative)
- Behavior: registers a scheduled job to trigger export generation at the specified time
- Errors: schedule not found, past execution time

**CancelScheduleExecution(scheduleId) → void**
- Input: schedule ID
- Behavior: cancels any pending executions for the schedule
- Errors: schedule not found

### Audit Logger Interface

**LogExportEvent(eventType, userId, resourceId, outcome, details) → AuditLogEntry**
- Input: event type, user ID, resource ID (report/export/schedule), outcome, details dict
- Output: AuditLogEntry object
- Behavior: records event with timestamp and all provided details
- Errors: invalid event type

### Feature Flag Interface

**IsExportFeatureEnabled(workspaceId) → boolean**
- Input: workspace ID
- Output: true if feature is enabled, false otherwise
- Behavior: checks feature flag configuration for the workspace
- Errors: workspace not found
