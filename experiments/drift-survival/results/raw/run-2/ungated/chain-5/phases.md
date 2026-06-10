# Scheduled Report Exports — Phase Plan

## Phase 1: Export API & One-Off Exports

**Goal:** Establish the synchronous export endpoint and implement the core one-off export workflow, allowing users to generate and download report exports on demand.

**Scope:**
- Implement Export API endpoint: `POST /api/reports/{reportId}/exports`
- Build domain models: `ExportRequest`, `ExportArtifact`
- Implement permission checks and feature flag validation
- Design and implement Export Generation Service as async queue processor
- Integrate object storage upload and artifact persistence
- Implement audit logging for export requests and generation events
- Build UI polling mechanism for export status and download link presentation
- Implement size validation (≤ 50 MB limit)

**Acceptance Criteria:**
- User can request a CSV export from a report via the API
- User can request a PDF export from a report via the API
- User receives an `exportId` immediately; UI can poll for completion status
- Export generation runs asynchronously without blocking the API response
- Generated artifact is uploaded to object storage and accessible for download
- Download link is returned to user once generation completes
- Exports respect row-level permission filtering (only user's viewable rows included)
- Export size is validated; requests exceeding 50 MB are rejected with 507 error
- All export requests and completions are recorded in audit log
- Feature flag check prevents exports if `export.enabled` is false

## Phase 2: Export Schedules & Schedule Management

**Goal:** Enable users to create recurring export schedules with configurable frequency and manage those schedules through pause/resume/delete operations.

**Scope:**
- Implement ExportSchedule domain model with frequency and day-of-week configuration
- Implement Schedule Manager with CRUD operations and schedule state tracking
- Implement `POST /api/reports/{reportId}/schedules` endpoint
- Implement `GET /api/schedules/{scheduleId}` endpoint
- Implement `PATCH /api/schedules/{scheduleId}` endpoint for pause/resume and optional frequency edits
- Implement `DELETE /api/schedules/{scheduleId}` endpoint
- Implement scheduler service (cron-like trigger) to identify and trigger active schedules
- Implement next-run-at calculation logic for daily and weekly frequencies
- Build UI for schedule creation form and schedule management/history views
- Audit logging for schedule creation, pause, resume, and delete events

**Acceptance Criteria:**
- User can create a daily export schedule via the API
- User can create a weekly export schedule with day-of-week selection via the API
- Schedule creation validates permissions and feature flags consistently with one-off exports
- `nextRunAt` is correctly calculated for daily (next occurrence at same time) and weekly (next occurrence on selected day)
- User can retrieve their schedule details and current status
- User can pause an active schedule; paused schedule is not triggered by the scheduler
- User can resume a paused schedule; `nextRunAt` is recalculated correctly
- User can delete a schedule (soft or hard per retention policy)
- Scheduler service correctly identifies all active schedules with `nextRunAt ≤ now()` at regular intervals
- Audit log records all schedule management actions with userId and timestamp

## Phase 3: Scheduled Export Execution & ExportRun Tracking

**Goal:** Implement the automated execution of scheduled exports and track each run independently, enabling visibility into the execution history of recurring exports.

**Scope:**
- Implement ExportRun domain model with status, attempt tracking, and failure reasons
- Implement ExportHistory queryable view/index (last 30 runs per schedule)
- Implement `GET /api/schedules/{scheduleId}/history` endpoint with filtering by status and date range
- Integrate Export Generation Service to handle scheduled export requests (enqueue logic)
- Update ExportSchedule to track `lastRunAt` and update `nextRunAt` after each execution
- Implement ExportRun creation and status transitions (generated → delivered/failed)
- Build UI view for export history per schedule, displaying export date, format, delivery status, and retry count
- Implement failure reason tracking and recording in ExportRun

**Acceptance Criteria:**
- Scheduler service enqueues an ExportRequest to the queue for each active schedule at the correct time
- ExportRun record is created with `status = generated` after Export Generation Service completes
- ExportRun is correctly linked to the generated ExportArtifact via `exportId`
- Schedule's `lastRunAt` is updated to the time of execution
- Schedule's `nextRunAt` is correctly recalculated for the next occurrence
- User can retrieve the last 30 runs for a schedule via history endpoint
- History endpoint supports filtering by status (generated, delivered, failed)
- History endpoint supports filtering by date range
- Each ExportRun displays export date, format, delivery status, and attempt count
- If generation fails, ExportRun is created with `status = generated` set to null and failure reason recorded

## Phase 4: Delivery Service & Email Integration

**Goal:** Implement automated email delivery of scheduled exports with retry logic and intelligent pause behavior after repeated failures.

**Scope:**
- Implement Delivery Service as async queue processor
- Implement email composition with download link, report metadata, and schedule management links
- Implement object storage URL generation (pre-signed URLs valid for 7 days)
- Implement retry logic with exponential backoff (1 min, 5 min, 15 min)
- Implement automatic schedule pause after 3 consecutive delivery failures
- Implement email service integration (workspace's email provider)
- Implement `attemptCount` and `lastAttemptAt` tracking on ExportRun
- Update ExportSchedule status to `paused` when auto-pausing due to delivery failures
- Audit logging for delivery attempts, successes, and failures

**Acceptance Criteria:**
- Delivery Service dequeues ExportRun records requiring delivery
- Email is sent to schedule owner with report name, export date/time, and download link
- Pre-signed download link is valid for 7 days (or retention window)
- Email includes link to manage schedule (pause/resume/delete)
- Delivery success updates ExportRun `status = delivered` and records `lastAttemptAt`
- Delivery failure increments `attemptCount`
- First and second delivery failures enqueue retry after exponential backoff
- Third consecutive delivery failure pauses the schedule and updates ExportRun `status = failed`
- Audit log records all delivery attempts with outcome and attempt count
- User can see delivery history in the ExportRun records (via Phase 3 history endpoint)

## Phase 5: Audit, Feature Control & Admin Settings

**Goal:** Implement comprehensive audit logging and administrative controls to enforce feature flags, workspace-level export disablement, and provide audit trail for compliance.

**Scope:**
- Implement audit log recording for all export events: `export.requested`, `export.generated`, `export.size_limit_exceeded`, `export.permission_denied`, `export.schedule_created`, `export.schedule_paused`, `export.schedule_resumed`, `export.schedule_deleted`, `export.delivered`, `export.delivery_failed`, `export.admin_disabled`
- Implement feature flag evaluation: `export.enabled` (default false at launch)
- Implement workspace admin setting: `allowExports` (toggle to enable/disable all exports)
- Implement enforcement point in Export API to check feature flag and admin setting before accepting requests
- Implement automatic schedule pause when admin disables exports globally
- Implement audit logging for flag changes and admin disablement events
- Build admin UI for toggling `allowExports` setting and reviewing audit trail

**Acceptance Criteria:**
- All export request events are logged with userId, reportId, format, and filters
- All export generation completion events are logged with exportId, sizeBytes, and format
- Permission denied events are logged with specific reason
- All schedule lifecycle events (create, pause, resume, delete) are logged with userId and scheduleId
- All delivery attempts and outcomes are logged with runId, scheduleId, and attempt count
- Feature flag `export.enabled` is checked on every export request; if false, request returns 403 error
- Admin can toggle `allowExports` setting for their workspace
- When admin disables exports, all active schedules are automatically paused
- Audit log records admin disablement action with adminUserId and workspaceId
- Admin can view audit log with filtering by event type, user, and date range
- All audit events include timestamp and can be exported for compliance review
