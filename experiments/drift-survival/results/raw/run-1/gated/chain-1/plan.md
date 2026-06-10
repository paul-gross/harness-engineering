# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to download any report as CSV or PDF and to schedule recurring exports delivered by email. This closes a gap for users who need to share or archive report data outside the application, and for those who want automated delivery without logging in each time.

The feature ships behind a feature flag to allow controlled rollout. All export activity is recorded in the audit log for compliance. Admins retain control via a workspace-level toggle to disable exports entirely. The implementation must preserve row-level permissions so that an exported file never contains data the requesting user is not authorized to see, and must not degrade the interactive report viewing experience.

## Acceptance criteria

### One-off exports

- A user can export any report they have access to as CSV.
- A user can export any report they have access to as PDF.
- The exported file contains only rows the requesting user is permitted to see (row-level permission enforcement at export time).
- Exports larger than 50 MB are rejected before delivery with a clear error message that explains the size limit.
- Export generation runs asynchronously and does not block or degrade interactive report viewing.

### Scheduled exports

- A user can create a recurring export schedule for any report, choosing daily or weekly frequency.
- Scheduled exports are delivered by email exclusively to the owner of the schedule (no third-party recipients).
- The owner can pause a schedule at any time; a paused schedule produces no deliveries until resumed.
- The owner can resume a paused schedule at any time.
- Failed deliveries are retried automatically, up to a maximum of 3 retry attempts per scheduled run.
- If the third retry fails, the schedule is automatically paused.
- The owner can view a history of the last 30 export runs for each schedule, including delivery status and timestamps.

### Access control and administration

- An admin can disable export functionality entirely for their workspace; when disabled, no exports (one-off or scheduled) can be initiated by any user in that workspace.
- Every export event (initiation, delivery, failure, retry, schedule pause/resume, admin toggle) is recorded in the audit log with the acting user, timestamp, and relevant identifiers.

### Rollout

- The entire feature (one-off exports, scheduled exports, admin toggle) is gated behind a feature flag and is off by default at launch.
- Enabling the feature flag makes the full feature available; disabling it hides all export surfaces without data loss.
