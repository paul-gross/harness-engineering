# Scheduled Report Exports — Business Plan

## Summary

We will add export and scheduled delivery capabilities to the reporting module. Users will be able to export any report as CSV or PDF on demand, and configure recurring exports delivered by email on a daily or weekly cadence.

The motivation is to extend report value beyond the application itself — users need to share, archive, and analyze report data in external tools. Scheduled exports further reduce manual effort by automating routine data pulls.

All exports enforce the requesting user's row-level permissions so that exported data never exceeds what the user can see in the app. The feature launches behind a feature flag, supports an admin-level kill switch per workspace, and records every export event in the audit log for compliance.

---

## Acceptance criteria

### On-demand export

- A user can export any report they have access to as CSV or as PDF.
- The exported file contains only rows the requesting user is permitted to see (row-level permissions are enforced at export time, not at render time).
- Exports larger than 50 MB are rejected before delivery with a clear, user-facing error message explaining the size limit.
- Export generation runs asynchronously and does not degrade or block interactive report viewing for any user.
- Every export event (initiated, succeeded, failed, rejected) is written to the audit log with user identity, report identity, format, timestamp, and outcome.

### Scheduled exports

- A user can create a recurring export schedule for any report they can access, choosing either a daily or weekly delivery frequency.
- Scheduled exports are delivered by email exclusively to the owner of the schedule — no other recipients.
- The owner can pause and resume their schedule at any time; a paused schedule skips deliveries until resumed.
- Failed deliveries are retried automatically, up to a maximum of 3 attempts per scheduled run.
- If the third retry fails, the schedule is automatically paused and the owner is notified.
- The owner can view a run history showing the outcome (delivered, failed, paused) of the last 30 export runs for each schedule.
- All size and permission constraints that apply to on-demand exports apply equally to scheduled exports.
- Every scheduled export event is written to the audit log.

### Administration

- Admins can disable export functionality entirely for their workspace; when disabled, all on-demand and scheduled export entry points are hidden or blocked for all users in that workspace.
- Pausing or disabling does not delete schedules or history; resuming or re-enabling restores prior configuration.

### Feature flag

- The entire export feature (on-demand and scheduled) is gated behind a feature flag at launch.
- When the flag is off, no export UI or API surface is exposed.
