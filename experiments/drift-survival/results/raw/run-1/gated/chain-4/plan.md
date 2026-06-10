# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to download any report as CSV or PDF and to schedule recurring exports delivered by email. This addresses a clear user need for taking report data out of the application for offline analysis, sharing, and automated workflows.

The feature has two distinct surfaces. The first is on-demand export, where a user generates a one-off download of a report in their chosen format. The second is scheduled export, where a user configures a daily or weekly cadence for a report to be emailed to them automatically. Both surfaces must respect the user's existing row-level permissions — an export is a view of the same data, not an elevated one.

Because this is a new surface with meaningful operational implications (background job load, email delivery, file size), it will ship behind a feature flag. Admins retain the ability to disable export functionality entirely for their workspace, and every export action must be recorded in the audit log for compliance and traceability.

---

## Acceptance Criteria

### On-demand export

- A user can export any report they have access to as CSV or PDF from within the report view.
- Exported data contains only rows the requesting user is permitted to see, enforced server-side using the same row-level permission rules as the interactive report view.
- Export generation is asynchronous and does not degrade the performance of interactive report viewing.
- Exports larger than 50 MB are rejected before delivery; the user receives a clear error message explaining why the export was not completed.
- Every export event is written to the audit log.

### Scheduled exports

- A user can create a schedule for any report they have access to, choosing either a daily or weekly delivery cadence.
- Scheduled exports are delivered by email exclusively to the owner of the schedule; delivery to third parties is not supported.
- The schedule owner can pause and resume their schedule at any time; a paused schedule produces no deliveries until resumed.
- Failed deliveries are retried automatically, up to a maximum of 3 attempts per scheduled run.
- If the third retry attempt fails, the schedule is automatically paused.
- Each scheduled export run is subject to the same permission enforcement and size limit as on-demand exports.
- Each schedule exposes a run history showing the last 30 export runs, including status and timestamp for each.

### Workspace and platform constraints

- The entire export feature (on-demand and scheduled) is gated behind a feature flag at launch.
- Workspace admins can disable export functionality entirely for their workspace; when disabled, no user in that workspace can initiate or receive exports regardless of the feature flag state.
