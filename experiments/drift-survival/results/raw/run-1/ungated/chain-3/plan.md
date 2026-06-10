# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to download any report as CSV or PDF and to schedule recurring exports delivered by email. This feature addresses a clear user need for offline access to report data and for automated, recurring data delivery without manual intervention.

The feature is scoped to respect existing security boundaries: every export enforces the requesting user's row-level permissions, so no user can extract data they could not see in the application. Generating an export is fully asynchronous so it does not degrade the interactive report-viewing experience.

To give admins control, the entire feature can be disabled per workspace. Because this is a new surface area, the feature ships behind a feature flag at launch, giving us a safe rollout path. Every export action — triggered, scheduled, delivered, retried, or failed — is recorded in the audit log for compliance and troubleshooting.

---

## Acceptance Criteria

### One-off exports

- A user can export any report they have access to as CSV or PDF.
- The exported file contains only rows the requesting user is permitted to see (row-level permission enforcement is applied at export time, not at query time).
- Exports are generated asynchronously and do not block or degrade interactive report viewing.
- Exports larger than 50 MB are rejected before delivery with a clear, user-facing error message explaining the size limit.
- Every export request (successful or rejected) is recorded in the audit log with the user, report, format, timestamp, and outcome.

### Scheduled exports

- A user can create a recurring export schedule for any report they have access to, choosing either daily or weekly frequency.
- Scheduled exports are delivered by email exclusively to the owner of the schedule; no other recipient can be configured.
- The schedule owner can pause and resume their schedule at any time.
- If a scheduled export delivery fails, the system retries delivery up to 3 times.
- If the third retry also fails, the schedule is automatically paused and the owner is notified.
- A user can view the history of the last 30 export runs for each of their schedules, including delivery status (success, failed, retried, paused).
- Each scheduled export run is recorded in the audit log.

### Admin controls

- Workspace admins can disable export functionality entirely for their workspace.
- When exports are disabled, all one-off and scheduled export actions are blocked and users see a clear message indicating exports are not available.
- The disabled/enabled state is reflected consistently across the UI and API.

### Feature flag

- The entire export feature (one-off and scheduled) is hidden behind a feature flag at launch.
- The feature flag can be toggled without a code deployment.
- When the flag is off, no export-related UI or API surface is accessible.
