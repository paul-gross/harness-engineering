# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to download any report as CSV or PDF, and to schedule recurring exports delivered by email.

The motivation is twofold. First, users need to get data out of the application for offline analysis, presentation, and archiving — one-off exports address this directly. Second, many workflows depend on a regular cadence of reporting; scheduled exports remove the manual step of returning to the app on a recurring basis and ensure stakeholders receive fresh data automatically.

All exports are permission-scoped: the output a user receives will contain only the rows they are authorized to see in the app. This is a non-negotiable constraint that preserves the trust model of the existing reporting surface.

The feature ships behind a feature flag at launch to allow controlled rollout and fast rollback if needed.

---

## Acceptance Criteria

### One-off exports

- A user can export any report they have access to as CSV.
- A user can export any report they have access to as PDF.
- Exported files contain only the rows the requesting user is permitted to see in the app (row-level permission enforcement).
- Exports larger than 50 MB are rejected before delivery with a clear, user-facing error message.
- Export generation is performed asynchronously and does not block interactive report viewing.
- Every export event (initiated, completed, failed, rejected) is recorded in the audit log with user identity, report identifier, format, and timestamp.

### Scheduled exports

- A user can create a recurring export schedule for any report, choosing either daily or weekly delivery.
- Scheduled exports are delivered by email exclusively to the owner of the schedule (no third-party delivery).
- A user can pause and resume any schedule they own at any time.
- Failed deliveries are retried automatically, up to a maximum of 3 attempts.
- If the third retry fails, the schedule is automatically paused and the owner is notified.
- A user can view a history of the last 30 export runs for each of their schedules, including status (success, failed, paused) and timestamp.

### Administration

- Admins can disable the entire export feature for their workspace; when disabled, no exports (one-off or scheduled) can be initiated by any user in that workspace.
- The feature is controlled by a feature flag and is off by default at launch; enabling it for a workspace exposes the full export surface to users in that workspace.

### Audit and compliance

- All export events are recorded in the audit log regardless of whether the feature flag is enabled or disabled (i.e., rejected attempts due to a disabled workspace are also logged).
