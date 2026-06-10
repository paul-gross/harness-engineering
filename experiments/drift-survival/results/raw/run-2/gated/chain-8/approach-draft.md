# Technical Approach: Scheduled Report Exports

## Architecture Outline

The scheduled report exports feature adds four new components to the reporting module:

1. **Export Service** — handles the generation of CSV and PDF exports, enforcing row-level security and size limits
2. **Scheduled Export Manager** — orchestrates recurring export creation, scheduling, and status tracking
3. **Email Delivery Service** — manages asynchronous email dispatch with retry logic and failure handling
4. **Export History and Audit Service** — tracks export runs, delivery attempts, and administrative actions

These components interact as follows:

- When a user triggers an on-demand export, the **Export Service** generates the file asynchronously and returns immediately with a delivery status (polling or callback-based)
- **Scheduled Export Manager** runs scheduled jobs at defined intervals, invoking the **Export Service** to generate fresh exports
- Generated exports are handed off to the **Email Delivery Service**, which attempts delivery with automatic retry and pause on failure
- All actions (exports, deliveries, pauses, resumes) are logged to the audit system via the **Export History and Audit Service**
- An admin feature-flag gate controls visibility and availability across the UI

## Domain Model

### Core Entities

**Report** (existing)
- Standard report entity with user-scoped row-level permissions

**ScheduledExport**
- `id`: UUID
- `owner_id`: user ID (the user who created the schedule)
- `report_id`: reference to the report being exported
- `export_format`: enum (CSV, PDF)
- `frequency`: enum (DAILY, WEEKLY)
- `scheduled_time`: time of day (HH:MM) or day-of-week + time for weekly schedules
- `status`: enum (ACTIVE, PAUSED)
- `created_at`: timestamp
- `updated_at`: timestamp
- `paused_at`: timestamp (optional, when auto-paused due to delivery failures)

**ExportRun**
- `id`: UUID
- `scheduled_export_id`: reference to the parent ScheduledExport
- `export_request_id`: reference to the underlying export generation request
- `triggered_at`: timestamp (when the scheduled job executed)
- `completed_at`: timestamp (optional, when export generation finished)
- `status`: enum (PENDING, COMPLETED, FAILED)
- `file_size_bytes`: integer (optional, only set on successful completion)
- `error_message`: string (optional, set if generation failed)

**ExportRequest**
- `id`: UUID
- `requester_id`: user ID
- `report_id`: reference to the report
- `export_format`: enum (CSV, PDF)
- `created_at`: timestamp
- `status`: enum (QUEUED, PROCESSING, COMPLETED, FAILED)
- `output_path`: string (location of generated file, once completed)
- `file_size_bytes`: integer (set when status is COMPLETED)
- `error_message`: string (optional, set if FAILED)

**DeliveryAttempt**
- `id`: UUID
- `export_run_id`: reference to the parent ExportRun
- `attempt_number`: integer (1, 2, or 3)
- `recipient_email`: email address
- `attempted_at`: timestamp
- `status`: enum (PENDING, SENT, FAILED)
- `error_message`: string (optional)

**ExportAuditLog** (extends existing audit system)
- `id`: UUID
- `actor_id`: user ID (who triggered the action)
- `action_type`: enum (EXPORT_INITIATED, EXPORT_COMPLETED, EXPORT_FAILED, SCHEDULE_CREATED, SCHEDULE_PAUSED_AUTO, SCHEDULE_PAUSED_MANUAL, SCHEDULE_RESUMED, DELIVERY_SENT, DELIVERY_FAILED, FEATURE_DISABLED, FEATURE_ENABLED)
- `report_id`: reference to the affected report
- `scheduled_export_id`: reference to the affected schedule (if applicable)
- `export_run_id`: reference to the affected run (if applicable)
- `metadata`: JSON object containing format, file size, attempt count, error details, etc.
- `created_at`: timestamp

### Relationships

- One User owns many ScheduledExports
- One Report is referenced by many ScheduledExports
- One ScheduledExport triggers many ExportRuns
- One ExportRun corresponds to one ExportRequest
- One ExportRun has many DeliveryAttempts (up to 3)
- All actions reference ExportAuditLog for traceability

## Key Workflows

### On-Demand Export Workflow

1. User selects a report and chooses "Export as CSV" or "Export as PDF"
2. UI creates an ExportRequest with status QUEUED and returns immediately
3. Export Service picks up the request asynchronously:
   - Fetches the report definition and user's row-level permissions
   - Generates the export file in the requested format, including only rows the user can view
   - Checks file size against 50 MB limit
   - On success: updates ExportRequest status to COMPLETED, stores file path and size
   - On failure (oversized or generation error): updates status to FAILED with error message
4. UI polls ExportRequest status or receives callback notification
5. On completion, UI offers download link to the requester
6. Export action is logged to ExportAuditLog

### Scheduled Export Creation Workflow

1. User navigates to a report and selects "Schedule Exports"
2. User specifies frequency (daily or weekly) and time of day
3. System creates a ScheduledExport record with status ACTIVE
4. User receives confirmation and can view the schedule in a list
5. Action is logged to ExportAuditLog with action SCHEDULE_CREATED

### Scheduled Export Execution Workflow

1. Scheduler daemon (or background job) detects that a ScheduledExport is due
2. Scheduler creates an ExportRun record with status PENDING
3. Scheduler invokes Export Service to generate the export:
   - Same process as on-demand export: row-level security, size limit, format generation
4. On generation success:
   - ExportRun status moves to COMPLETED with file size recorded
   - Email Delivery Service is invoked with the exported file and owner's email
5. On generation failure:
   - ExportRun status moves to FAILED with error message
   - No email is sent; failure is logged
6. All actions are logged to ExportAuditLog

### Email Delivery Workflow (with Retry and Auto-Pause)

1. Email Delivery Service receives an ExportRun and target email address
2. For each delivery attempt (up to 3 total):
   - Create DeliveryAttempt record with status PENDING
   - Attempt to send email with the export file attached
   - On success: mark DeliveryAttempt status SENT, mark ExportRun delivery complete, exit retry loop
   - On failure: mark DeliveryAttempt status FAILED with error, log failure
   - Wait before next attempt (exponential backoff recommended)
3. If all 3 attempts fail:
   - Log auto-pause event to ExportAuditLog with action SCHEDULE_PAUSED_AUTO
   - Update parent ScheduledExport status to PAUSED and record paused_at timestamp
   - Send admin notification or notification to schedule owner
4. Export action and delivery outcomes are logged

### Pause/Resume Workflow

1. User navigates to a ScheduledExport and selects "Pause"
2. ScheduledExport status is updated to PAUSED
3. Action is logged to ExportAuditLog with action SCHEDULE_PAUSED_MANUAL
4. No further runs are triggered until resumed

5. User selects "Resume" on a paused schedule
6. ScheduledExport status is updated to ACTIVE and paused_at is cleared
7. Next scheduled time is recalculated based on frequency
8. Action is logged to ExportAuditLog with action SCHEDULE_RESUMED

### Export History Workflow

1. User navigates to a ScheduledExport detail view
2. System queries ExportRun records for this ScheduledExport, limited to last 30 runs, ordered by triggered_at descending
3. For each ExportRun, system fetches associated DeliveryAttempt records
4. UI displays:
   - Export timestamp
   - Status (success/failed)
   - File size (if successful)
   - Delivery outcome (from latest DeliveryAttempt status)
   - Any error messages
5. User can drill into any run to see detailed retry history and error logs

### Feature Flag Toggle Workflow

1. Admin navigates to workspace settings and toggles "Enable Export Functionality"
2. On toggle, system updates feature flag state
3. Action is logged to ExportAuditLog with action FEATURE_DISABLED or FEATURE_ENABLED
4. All export and scheduled export UI elements are conditionally rendered based on flag state
5. If feature is disabled:
   - On-demand exports are rejected with clear messaging
   - Scheduled exports are not triggered
   - All UI elements for export are hidden

## Contracts

### Export Service

**`generateExport(exportRequestId: UUID, reportId: UUID, format: "CSV" | "PDF", userId: UUID) -> Promise<void>`**
- Input: ID of the export request to process, report to export, desired format, and requester's user ID
- Process: fetch report definition, apply row-level security filters for the user, generate file in requested format
- Output: updates ExportRequest record with result (status, file path, file size, or error message)
- Raises: internal exception if report not found, user lacks permission, or generation fails
- Side effect: writes file to backing storage; logs to export audit trail

**`validateExportSize(fileSizeBytes: integer) -> boolean`**
- Input: size of the generated export file in bytes
- Output: true if file is ≤ 50 MB; false otherwise
- Raises: none
- Side effect: none (pure function)

### Scheduled Export Manager

**`createScheduledExport(ownerId: UUID, reportId: UUID, format: "CSV" | "PDF", frequency: "DAILY" | "WEEKLY", scheduledTime: TimeOfDay | DayOfWeekAndTime) -> ScheduledExport`**
- Input: owner user ID, report to schedule, export format, frequency, and time specification
- Output: newly created ScheduledExport record
- Raises: exception if report not found or user lacks access to the report
- Side effect: creates database record; logs to audit trail with action SCHEDULE_CREATED

**`pauseScheduledExport(scheduledExportId: UUID, actor: UUID) -> void`**
- Input: ID of the schedule to pause, user ID of the actor (for audit purposes)
- Output: none
- Raises: exception if schedule not found
- Side effect: updates ScheduledExport status to PAUSED; logs to audit trail

**`resumeScheduledExport(scheduledExportId: UUID, actor: UUID) -> void`**
- Input: ID of the schedule to resume, user ID of the actor
- Output: none
- Raises: exception if schedule not found
- Side effect: updates ScheduledExport status to ACTIVE, clears paused_at; logs to audit trail

**`getScheduledExportHistory(scheduledExportId: UUID, limit: integer = 30) -> ExportRun[]`**
- Input: ID of the schedule, optional limit (defaults to 30)
- Output: list of the most recent ExportRun records, ordered by triggered_at descending
- Raises: exception if schedule not found
- Side effect: none (read-only)

**`triggerScheduledExportRuns() -> void`**
- Input: none (called by scheduler)
- Output: none
- Process: query all active ScheduledExport records where the current time matches the scheduled time, create ExportRun records, invoke Export Service for each
- Side effect: creates ExportRun records; triggers export generation; logs to audit trail

### Email Delivery Service

**`deliverExportEmail(exportRunId: UUID, recipientEmail: string) -> void`**
- Input: ID of the export run and target email address
- Output: none
- Process: attempt to send email with export file attachment; on failure, retry up to 3 times with exponential backoff; if all attempts fail, call autoPauseSchedule
- Side effect: creates DeliveryAttempt records; sends email (or logs failures); updates ScheduledExport status to PAUSED if final failure; logs all attempts to audit trail

**`autoPauseSchedule(scheduledExportId: UUID) -> void`**
- Input: ID of the schedule to auto-pause
- Output: none
- Side effect: updates ScheduledExport status to PAUSED and records paused_at timestamp; logs to audit trail with action SCHEDULE_PAUSED_AUTO

### Audit and Logging Service

**`logExportAction(action: string, actorId: UUID, reportId: UUID, metadata: JSON) -> void`**
- Input: action type (e.g., EXPORT_INITIATED, EXPORT_COMPLETED, DELIVERY_SENT), actor user ID, affected report ID, and contextual metadata (format, size, attempt count, error, etc.)
- Output: none
- Side effect: creates ExportAuditLog record; persists to audit database

### Feature Flag Contract

**`isExportFeatureEnabled(workspaceId: UUID) -> boolean`**
- Input: workspace ID
- Output: true if export feature is enabled; false otherwise
- Side effect: none (read-only, may be cached)

**`setExportFeatureEnabled(workspaceId: UUID, enabled: boolean, actor: UUID) -> void`**
- Input: workspace ID, desired state, and actor user ID (for audit)
- Output: none
- Side effect: updates feature flag state; logs to audit trail with action FEATURE_ENABLED or FEATURE_DISABLED

### UI Contracts

**Export Visibility (all features below are only rendered if `isExportFeatureEnabled()` returns true)**

- **On-demand export buttons** ("Export as CSV", "Export as PDF") appear on report views
- **Scheduled exports section** appears in report settings or a dedicated exports tab
- **Export history and scheduled export management UI** appears only when feature is enabled

**Polling/Callback for On-Demand Exports**

- UI calls `getExportRequestStatus(exportRequestId)` to check status
- OR system pushes status updates via WebSocket/Server-Sent Events
- On COMPLETED status, UI displays download link or auto-triggers file download
- On FAILED status, UI displays error message from ExportRequest.error_message
