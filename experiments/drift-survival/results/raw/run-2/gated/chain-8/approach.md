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
- Generated exports are handed off to the **Email Delivery Service**, which attempts delivery to the schedule owner's email with automatic retry and pause on failure
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
- `triggered_at`: timestamp (when the scheduled job executed)
- `completed_at`: timestamp (optional, when export generation finished)
- `status`: enum (PENDING, COMPLETED, FAILED)
- `file_size_bytes`: integer (optional, only set on successful completion)
- `error_message`: string (optional, set if generation failed)

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
- One ExportRun has many DeliveryAttempts (up to 3)
- All actions reference ExportAuditLog for traceability

## Key Workflows

### On-Demand Export Workflow

1. User selects a report and chooses "Export as CSV" or "Export as PDF"
2. UI initiates export request and returns immediately
3. Export Service processes the request asynchronously:
   - Fetches the report definition and user's row-level permissions
   - Generates the export file in the requested format, including only rows the user can view
   - Checks file size against 50 MB limit
   - On success: stores file and records export completion
   - On failure (oversized or generation error): records failure with error message
4. UI polls for status or receives callback notification
5. On completion, UI offers download link to the requester
6. Export action is logged to ExportAuditLog

### Scheduled Export Creation Workflow

1. User navigates to a report and selects "Schedule Exports"
2. User specifies frequency (daily or weekly) and time of day
3. System creates a ScheduledExport record with status ACTIVE
4. User receives confirmation and can view the schedule in a list
5. Action is logged to ExportAuditLog with action SCHEDULE_CREATED

### Scheduled Export Execution Workflow

1. Scheduler detects that a ScheduledExport is due
2. Scheduler creates an ExportRun record
3. Scheduler invokes Export Service to generate the export:
   - Same process as on-demand export: row-level security, size limit, format generation
4. On generation success:
   - ExportRun status moves to COMPLETED with file size recorded
   - Email Delivery Service is invoked to deliver the export to the schedule owner's email
5. On generation failure:
   - ExportRun status moves to FAILED with error message
   - No email is sent; failure is logged
6. All actions are logged to ExportAuditLog

### Email Delivery Workflow (with Retry and Auto-Pause)

1. Email Delivery Service receives an ExportRun and the schedule owner's email address
2. For each delivery attempt (up to 3 total):
   - Attempt to send email with the export file attached to the schedule owner
   - On success: mark delivery complete, exit retry loop
   - On failure: log failure and proceed to next attempt if available
   - Wait before next attempt (exponential backoff recommended)
3. If all 3 attempts fail:
   - Log auto-pause event to ExportAuditLog with action SCHEDULE_PAUSED_AUTO
   - Update parent ScheduledExport status to PAUSED and record paused_at timestamp
   - Send notification to schedule owner
4. All delivery outcomes are logged

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
3. For each ExportRun, system fetches associated delivery attempt records
4. UI displays:
   - Export timestamp
   - Status (success/failed)
   - File size (if successful)
   - Delivery outcome
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

## Key Design Principles

- **Asynchronous Processing**: All export generation happens asynchronously to avoid blocking interactive report viewing
- **Row-Level Security**: Every export enforces the requesting user's (or schedule owner's) row-level permissions
- **Size Constraints**: Exports exceeding 50 MB are rejected with clear error messaging
- **Reliable Delivery**: Scheduled exports are delivered to the schedule owner's email with automatic retry (max 3 attempts) and auto-pause on repeated failure
- **Audit Trail**: All export actions, deliveries, and administrative changes are comprehensively logged
- **Feature Control**: The entire feature is gated behind a feature flag that admins can toggle to enable or disable export functionality workspace-wide
