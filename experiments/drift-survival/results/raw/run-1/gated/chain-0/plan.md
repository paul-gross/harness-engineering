# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, allowing users to download any report as CSV or PDF. Exports will respect each user's row-level permissions, ensuring that exported data never includes rows the user cannot see in the application.

Beyond one-off downloads, users will be able to schedule recurring exports on a daily or weekly cadence. Scheduled exports are delivered by email to the schedule owner only. Owners can pause and resume their schedules at any time. Failed deliveries will be retried up to three times; if all retries fail, the schedule is automatically paused. Users can view the last 30 run history entries per schedule for transparency.

This feature ships behind a feature flag at launch to allow controlled rollout. Admins can disable export functionality entirely for their workspace. All export events are recorded in the audit log. Export generation runs asynchronously so interactive report viewing is never blocked. Exports exceeding 50 MB are rejected with a clear error message.

The goal is to give users a reliable, self-service way to access and distribute report data on their own schedule, while preserving security, performance, and auditability guarantees the platform already provides.

---

## Acceptance Criteria

### One-off exports

- A user can export any report they have access to as CSV.
- A user can export any report they have access to as PDF.
- The exported file contains only rows the requesting user is permitted to see in the application (row-level permissions are enforced at export time).
- Export generation does not block interactive report viewing (generation is asynchronous or otherwise off the critical path).
- If the resulting export file would exceed 50 MB, the export is rejected and the user receives a clear, human-readable error message explaining the limit.

### Scheduled exports

- A user can create a recurring export schedule for a report, choosing either daily or weekly frequency.
- Scheduled exports are delivered by email exclusively to the owner of the schedule; no other recipients are allowed.
- A schedule owner can pause their schedule at any time; a paused schedule produces no deliveries.
- A schedule owner can resume a paused schedule at any time.
- If an export delivery fails, it is retried automatically, at most 3 times before giving up.
- If all 3 retries fail, the schedule is automatically paused and the owner is notified.
- A user can view the run history for each of their schedules, showing at least the last 30 runs with outcome (success or failure) and relevant timestamps.

### Security and permissions

- Row-level permission enforcement applies equally to scheduled exports as to one-off exports.
- Scheduled export emails are sent only to the schedule owner; no third-party delivery is permitted.

### Administration

- An admin can disable export functionality entirely for their workspace.

### Audit logging

- Every export event (one-off or scheduled, success or failure, initiation and completion) is recorded in the audit log.

### Feature flag

- The entire export feature (one-off and scheduled) ships behind a feature flag and is disabled by default at launch.
- Enabling the feature flag activates export functionality for the targeted workspace(s) or users.
