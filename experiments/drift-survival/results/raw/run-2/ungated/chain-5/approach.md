# Technical Approach: Scheduled Report Exports

## Architecture Outline

The report export system consists of five primary components:

1. **Export API** — Synchronous endpoint that accepts export requests (one-off or schedule creation) with format and filter parameters, validates permissions, and returns an export ID or persists a schedule.

2. **Export Generation Service** — Asynchronous queue processor that builds report data, applies row-level permission filtering, serializes to CSV or PDF, and uploads to object storage. Runs independently to avoid blocking UI interactions.

3. **Schedule Manager** — Responsible for schedule CRUD operations (create, pause, resume, delete), tracking schedule state, and triggering export generation on configured intervals (daily/weekly).

4. **Delivery Service** — Handles email delivery of completed exports, implements retry logic (up to 3 attempts), and automatically pauses schedules after three consecutive failures.

5. **Audit & Feature Control** — Records all export events in the workspace audit log; enforces feature flag and admin workspace-level export disable.

## Domain Model

**Report** — the data source being exported; identified by report ID. Does not store export data directly.

**ExportRequest** — represents a one-off or initial schedule creation request containing:
- `reportId`
- `requestingUserId`
- `format` (csv | pdf)
- `filters` (optional field/value pairs to narrow the report)
- `createdAt`

**ExportArtifact** — the generated export file containing:
- `exportId`
- `reportId`
- `requestingUserId`
- `format`
- `sizeBytes`
- `filePath` (or object storage URI)
- `generatedAt`
- `expiresAt` (optional; compliance retention window)

**ExportSchedule** — recurring export configuration containing:
- `scheduleId`
- `reportId`
- `ownerUserId`
- `frequency` (daily | weekly)
- `dayOfWeek` (for weekly; null for daily)
- `status` (active | paused)
- `deliveryEmail` (derived from owner; immutable)
- `createdAt`
- `nextRunAt`
- `lastRunAt` (null until first run)

**ExportRun** — a single execution of a scheduled export containing:
- `runId`
- `scheduleId`
- `exportId` (references the generated ExportArtifact, or null if generation failed)
- `status` (generated | delivered | failed)
- `attemptCount` (delivery attempts)
- `lastAttemptAt`
- `failureReason` (if status = failed)
- `createdAt`

**ExportHistory** — queryable view/index of the last 30 runs per schedule, ordered by most recent first.

## Key Workflows

### One-Off Export Workflow

1. User requests export of a report in CSV or PDF format from the report UI.
2. Export API checks:
   - Feature flag is enabled OR user is in permitted cohort
   - Admin has not disabled exports for the workspace
   - User has permission to view the report (row-level permission check)
3. Export request is enqueued to the Export Generation Service.
4. Export API returns an `exportId` immediately; UI polls for completion or streams status via WebSocket.
5. Export Generation Service:
   - Retrieves report data filtered to user's viewable rows
   - Serializes to requested format
   - Validates final size ≤ 50 MB; rejects if exceeding limit
   - Uploads artifact to object storage
   - Creates ExportArtifact record
6. UI presents download link once generation completes; artifact is downloaded directly from object storage.
7. Audit log records the export request, format, and completion status.

### Scheduled Export Workflow (Creation)

1. User navigates to report and selects "Schedule Export."
2. User configures: frequency (daily | weekly), day of week (if weekly), and confirms delivery email (owner's email, read-only).
3. Export API validates same permissions and feature-flag checks as one-off.
4. ExportSchedule record is created with `status = active` and `nextRunAt` calculated from frequency and current time.
5. Audit log records schedule creation.

### Scheduled Export Workflow (Execution)

1. Scheduler service (cron-like trigger) identifies all active ExportSchedules with `nextRunAt ≤ now()`.
2. For each schedule:
   - Enqueue an ExportRequest to the Export Generation Service (identical to one-off, but linked to the schedule)
   - Update schedule's `nextRunAt` to the next occurrence
3. Export Generation Service processes the request and creates ExportArtifact.
4. Create ExportRun record with `status = generated`, `exportId = <artifact ID>`, `attemptCount = 0`.
5. Enqueue the export for delivery.

### Scheduled Export Delivery Workflow

1. Delivery Service dequeues an export run requiring delivery.
2. Retrieves ExportArtifact and generates a download link or pre-signed URL.
3. Sends email to the schedule owner containing:
   - Report name
   - Export date/time
   - Download link (valid for 7 days or retention window)
   - Link to manage schedule (pause/resume/delete)
4. On success: update ExportRun `status = delivered`, increment `lastAttemptAt`.
5. On failure:
   - Increment `attemptCount`
   - If `attemptCount < 3`: enqueue for retry after exponential backoff (1min, 5min, 15min)
   - If `attemptCount ≥ 3`: set ExportRun `status = failed`, update ExportSchedule `status = paused`, audit log records auto-pause
6. Audit log records delivery attempt and outcome.

### Schedule Management Workflow (Pause/Resume/Delete)

1. User navigates to their export schedules list (History view).
2. User selects a schedule and chooses pause, resume, or delete.
3. Export API updates ExportSchedule:
   - Pause: `status = paused`
   - Resume: `status = active`, recalculate `nextRunAt`
   - Delete: soft-delete or hard-delete depending on retention policy
4. Audit log records the action.

### Export History Workflow

1. User views "Export History" for a report or schedule.
2. Export History endpoint returns the last 30 ExportRun records for the schedule, sorted by most recent first.
3. Each run displays: export date, format, delivery status, and retry count.
4. User can filter by status (generated, delivered, failed) or date range.
5. User can manually trigger a re-export of a past run if needed (optional enhancement).

## Contracts

### Export API Endpoints

**POST /api/reports/{reportId}/exports**
- Request: `{ format: "csv" | "pdf", filters?: { field: value } }`
- Response: `{ exportId: string, status: "generating" | "generated", downloadUrl?: string, expiresAt?: timestamp }`
- Error: 400 (invalid format or size), 403 (permission denied), 404 (report not found), 429 (rate limit), 507 (size limit exceeded)

**POST /api/reports/{reportId}/schedules**
- Request: `{ frequency: "daily" | "weekly", dayOfWeek?: "mon" | "tue" | ..., filters?: { field: value } }`
- Response: `{ scheduleId: string, ownerUserId: string, deliveryEmail: string, status: "active", nextRunAt: timestamp }`
- Error: 400 (invalid frequency), 403 (permission denied), 404 (report not found), 429 (rate limit)

**GET /api/schedules/{scheduleId}**
- Response: `{ scheduleId, reportId, ownerUserId, frequency, dayOfWeek, status, deliveryEmail, createdAt, nextRunAt, lastRunAt }`
- Error: 404, 403 (not schedule owner)

**GET /api/schedules/{scheduleId}/history**
- Query params: `?limit=30&offset=0&status=delivered&dateFrom=&dateTo=`
- Response: `{ runs: [{ runId, scheduleId, exportId, status, attemptCount, lastAttemptAt, failureReason, createdAt }], total: number }`
- Error: 404, 403 (not schedule owner)

**PATCH /api/schedules/{scheduleId}**
- Request: `{ status: "active" | "paused" }` or `{ dayOfWeek: "mon" | ... }` (edit frequency/day if allowed)
- Response: schedule object with updated fields
- Error: 404, 403 (not schedule owner), 400 (invalid transition)

**DELETE /api/schedules/{scheduleId}**
- Response: 204 (no content)
- Error: 404, 403 (not schedule owner)

### Export Generation Service Contract

**Input Queue Message**
- `{ exportRequestId, reportId, userId, format, filters, isScheduled: boolean, scheduleId?: string }`

**Processing**
- Retrieve report definition and apply filters
- Fetch report data scoped to `userId`'s row-level permissions
- Serialize to CSV (tabular format, standard CSV escaping) or PDF (formatted layout with headers, pagination)
- Validate final size ≤ 50 MB
- Upload to object storage and store reference in ExportArtifact
- Emit event: `"export.generated"` with exportId

**Error Handling**
- Permission denied → emit event `"export.permission_denied"` and fail fast
- Size exceeded → emit event `"export.size_limit_exceeded"` and fail
- Generation timeout (e.g., > 5 min) → emit event `"export.timeout"` and fail
- On failure → do not create ExportArtifact; update ExportRun status

### Delivery Service Contract

**Input Queue Message**
- `{ runId, scheduleId, exportId, ownerEmail }`

**Processing**
- Fetch ExportArtifact and generate download link (e.g., pre-signed URL valid for 7 days)
- Compose email with report metadata, link, and schedule management links
- Send email via workspace's email service
- On success → emit event `"export.delivered"`, update ExportRun
- On failure → increment attempt count, schedule retry or emit `"export.delivery_failed"` after max retries

### Audit Log Contract

**Events Recorded**
- `export.requested` — userId, reportId, format, filters, exportId
- `export.generated` — userId, exportId, sizeBytes, format
- `export.size_limit_exceeded` — userId, reportId, format, estimatedSize
- `export.permission_denied` — userId, reportId, reason
- `export.permission_compliance_check` — userId, rowsExported, rowsFiltered (optional; for transparency)
- `export.schedule_created` — userId, scheduleId, reportId, frequency
- `export.schedule_paused` — userId, scheduleId, reason (manual | auto_failed)
- `export.schedule_resumed` — userId, scheduleId
- `export.schedule_deleted` — userId, scheduleId
- `export.delivered` — scheduleId, runId, deliveryEmail
- `export.delivery_failed` — scheduleId, runId, attemptCount, reason
- `export.admin_disabled` — adminUserId, workspaceId

### Feature Flag & Admin Control Contract

**Feature Flag**: `export.enabled` (boolean, default false at launch)

**Workspace Admin Setting**: `allowExports` (boolean, default true if flag enabled; admins can toggle independently)

**Enforcement Points**:
- Export API checks flag before accepting requests
- If admin disables exports, all schedules are paused and no new exports allowed
- Audit log records flag changes and admin disablement

