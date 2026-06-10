# Business Plan: Scheduled Report Exports

## Summary

We will add export and scheduled delivery capabilities to the reporting module. Users will be able to export any report as CSV or PDF on demand, and optionally schedule recurring exports delivered to their inbox on a daily or weekly cadence.

This capability addresses a recurring user need: getting report data out of the application for offline analysis, sharing with stakeholders who lack app access, and automated delivery of periodic snapshots without manual intervention. It also gives admins control over the feature at the workspace level, and preserves trust by ensuring every export respects the same row-level permissions the user sees in the app.

The feature ships behind a feature flag at launch, giving us a controlled rollout path before general availability.

---

## Acceptance Criteria

### One-off exports

- A user can export any report they have access to as CSV.
- A user can export any report they have access to as PDF.
- Exported data contains only rows the user is permitted to see under the current row-level permission rules — no elevation of access at export time.
- Exports larger than 50 MB are rejected before delivery with a clear, user-facing error message explaining the size limit.
- Export generation runs asynchronously and does not degrade the performance of interactive report viewing.
- Every export event (initiated, completed, rejected, failed) is recorded in the audit log with the user identity, report identifier, format, and timestamp.

### Scheduled exports

- A user can create a recurring export schedule for any report, choosing either daily or weekly frequency.
- Scheduled exports are delivered by email exclusively to the owner of the schedule — no third-party recipients.
- The owner can pause a schedule at any time; a paused schedule produces no deliveries until resumed.
- The owner can resume a paused schedule at any time.
- Failed deliveries are retried automatically, up to a maximum of 3 attempts per scheduled run.
- If the third retry fails, the schedule is automatically paused and the owner is notified.
- A user can view the history of the last 30 export runs for each of their schedules, including status (delivered, failed, paused-on-failure) and timestamps.

### Admin controls

- An admin can disable the export feature entirely for their workspace.
- When export is disabled, one-off and scheduled exports are unavailable to all users in that workspace; attempting to trigger one surfaces a clear message indicating the feature is disabled.

### Feature flag

- The entire export surface (one-off and scheduled) is controlled by a feature flag and is off by default.
- The feature flag can be enabled per workspace or globally without a code deployment.
