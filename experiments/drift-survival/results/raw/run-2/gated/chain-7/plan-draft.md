# Scheduled Report Exports

## Summary

We will add comprehensive export capabilities to the reporting module, enabling users to export reports in multiple formats (CSV and PDF) with full support for recurring, scheduled exports. This feature addresses user demand for offline access to report data and automated delivery workflows.

Users can perform one-off exports of any report while respecting their row-level permissions — ensuring exported data never exceeds what the user can view in the application. Beyond ad-hoc exports, users can schedule recurring exports (daily or weekly) that are automatically generated and delivered via email. Scheduled exports are owned by individual users and can be paused or resumed at any time.

The feature includes built-in reliability mechanisms: failed deliveries are automatically retried up to 3 times, with the schedule pausing automatically if the third attempt fails. Users gain visibility into export reliability through a 30-day run history for each schedule. To protect system resources, exports larger than 50 MB are rejected. The feature ships behind a feature flag, and workspace admins can disable exports entirely if needed.

This unlocks new workflows for data analysis, compliance reporting, and automated business intelligence feeds while maintaining security, reliability, and system health.

## Acceptance Criteria

* **One-off exports** — Users can export any report as CSV or PDF from the UI
* **Row-level permission enforcement** — Exports only contain rows the user can view in the application; permission checks run at export time
* **Scheduled exports** — Users can create a schedule to export a report daily or weekly
* **Email delivery** — Scheduled exports are delivered via email to the schedule owner
* **Pause and resume** — Schedule owners can pause and resume their schedules; paused schedules do not generate or deliver exports
* **Automatic retry** — Failed export deliveries are automatically retried up to 3 times
* **Pause on permanent failure** — After 3 failed retries, the schedule is automatically paused; the user receives notification of the failure
* **Run history** — Each schedule displays a history of the last 30 export runs, including timestamp, status (success/failed), and delivery outcome
* **Non-blocking generation** — Exports are generated asynchronously; export requests do not block interactive report viewing
* **Size limit enforcement** — Exports larger than 50 MB are rejected with a user-facing error message
* **Admin control** — Workspace admins can disable export functionality entirely; when disabled, exports are unavailable to all users
* **Audit logging** — Every export event (request, completion, delivery attempt, schedule state change) is recorded in the audit log
* **Feature flag** — The feature launches behind a feature flag; exports are unavailable until the flag is enabled
