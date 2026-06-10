# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to download any report as CSV or PDF and to schedule recurring exports delivered by email. This closes a significant gap in reporting workflow: today users can view data in the app but cannot take it elsewhere without manual copy-paste. Export functionality lets users integrate report data into downstream tools, share it with stakeholders who lack app access, and automate recurring data pulls without manual intervention.

The feature ships behind a feature flag at launch so we can roll it out incrementally and give workspace admins the ability to disable it entirely if it is not appropriate for their context. Security and compliance are first-class concerns: every export respects the requesting user's row-level permissions, every export event is written to the audit log, and scheduled exports are delivered only to the schedule owner.

## Acceptance Criteria

### One-off exports

- A user can export any report they have access to as CSV.
- A user can export any report they have access to as PDF.
- Exported files contain only rows the requesting user is permitted to see in the app (row-level permissions are enforced at export time, not at schedule creation time).
- Exports are generated asynchronously and do not block interactive report viewing.
- If a generated export exceeds 50 MB, the export is rejected and the user receives a clear error message explaining the size limit.
- Every export attempt (success or failure) is recorded in the audit log with at minimum: user, report, format, timestamp, and outcome.

### Scheduled exports

- A user can create a recurring export schedule for any report, choosing either daily or weekly frequency.
- Scheduled exports are delivered by email to the schedule owner and to no other recipient.
- A user can pause and resume any schedule they own at any time.
- Each scheduled export run respects the schedule owner's row-level permissions at the time of generation.
- Failed deliveries are retried automatically, up to a maximum of 3 attempts total (1 initial attempt + 2 retries).
- If the third attempt fails, the schedule is automatically paused and the owner is notified.
- A user can view the history of the last 30 export runs for each of their schedules, including run timestamp, status (success / failed / retried), and any error detail.

### Administration

- Workspace admins can disable the entire export feature for their workspace; when disabled, no exports can be initiated (one-off or scheduled) by any user in that workspace.
- The feature is gated behind a feature flag and is off by default at launch; it must be enabled explicitly before any user can access it.

### Non-functional

- The 50 MB size limit and the 3-retry cap are enforced consistently across both one-off and scheduled export paths.
- Audit log entries are written even when an export is rejected (e.g., size limit exceeded, feature disabled).
