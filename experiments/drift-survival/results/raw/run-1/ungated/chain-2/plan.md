# Business plan: scheduled report exports

## Summary

We will add export and scheduled delivery capabilities to the reporting module. Users today can view reports interactively but have no way to take data out of the system or receive it on a recurring basis. This gap limits the reporting module's value for operational and analytical workflows where stakeholders need data in portable formats or delivered automatically on a schedule.

The feature has two layers. The first is on-demand export: any report can be exported as CSV or PDF, with the export honoring the requesting user's row-level permissions exactly as the interactive view does. The second is scheduled export: users can configure a daily or weekly delivery of a report to their own email address, manage (pause, resume, delete) those schedules, and review a history of recent runs.

To protect system reliability, export generation runs asynchronously so it never competes with interactive report viewing. A 50 MB size cap prevents runaway jobs. Failed deliveries are retried up to three times before the schedule is automatically paused to avoid silent accumulation of failures. Admins retain full control via a workspace-level kill switch that disables the feature entirely. All export activity is written to the audit log. The entire feature ships behind a feature flag so it can be enabled selectively at launch.

---

## Acceptance criteria

### On-demand export

- A user can export any report they have access to as CSV.
- A user can export any report they have access to as PDF.
- An exported file contains only the rows the requesting user is permitted to see under the application's row-level permission rules — no row that is hidden in the interactive view appears in any export.
- Export generation is asynchronous and does not degrade interactive report-viewing performance.
- If a generated export exceeds 50 MB, the export is rejected and the user receives a clear error message explaining the size limit.
- Every export attempt (successful or not) is recorded in the audit log with at minimum: user identity, report identifier, format requested, timestamp, and outcome.

### Scheduled exports

- A user can create a recurring export schedule for any report they have access to, choosing either daily or weekly frequency.
- Scheduled exports are delivered by email exclusively to the owner of the schedule — no other recipients.
- The owner can pause an active schedule and resume a paused schedule at any time.
- When a scheduled export delivery fails, the system retries delivery up to 3 times.
- If the third retry also fails, the schedule is automatically paused.
- A user can view the history of the last 30 export runs for each of their schedules, including timestamps and delivery status for each run.
- All scheduled export events (creation, execution, retry, automatic pause, manual pause/resume) are recorded in the audit log.

### Administration and access control

- An admin can disable the export feature entirely for their workspace.
- When export is disabled at the workspace level, on-demand exports and scheduled deliveries are both blocked; affected users receive a clear indication that the feature is unavailable.
- The entire export feature (on-demand and scheduled) is gated behind a feature flag and does not activate for workspaces where the flag is off.
