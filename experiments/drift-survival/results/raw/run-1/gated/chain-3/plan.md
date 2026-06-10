# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, allowing users to download any report as CSV or PDF, and to schedule recurring exports delivered by email. This feature addresses a gap in our reporting surface: users currently have no way to extract report data for offline use, share snapshots with stakeholders outside the app, or automate recurring data delivery without manual intervention.

The feature ships behind a feature flag so it can be enabled selectively and disabled at any time. Admins retain workspace-level control to disable exports entirely. All export activity is audit-logged.

---

## Acceptance Criteria

### One-off exports

- [ ] A user can export any report they have access to as CSV.
- [ ] A user can export any report they have access to as PDF.
- [ ] An exported file contains only rows the requesting user is permitted to see in the app (row-level permission enforcement is applied at export time).
- [ ] Exports larger than 50 MB are rejected before delivery and the user receives a clear error message indicating the size limit.
- [ ] Generating an export does not block interactive report viewing (export generation is asynchronous or otherwise isolated from the read path).

### Scheduled exports

- [ ] A user can create a recurring export schedule for any report, choosing either daily or weekly delivery frequency.
- [ ] Scheduled exports are delivered by email to the schedule owner only — no other recipients can be configured.
- [ ] The schedule owner can pause their schedule at any time; a paused schedule produces no deliveries until resumed.
- [ ] The schedule owner can resume a paused schedule at any time.

### Delivery reliability

- [ ] If a scheduled export delivery fails, the system retries delivery up to 3 times.
- [ ] If the third retry fails, the schedule is automatically paused.
- [ ] A user can view a history of the last 30 export runs for each of their schedules.

### Governance and observability

- [ ] Admins can disable the export feature entirely for their workspace; when disabled, no exports (one-off or scheduled) can be initiated by any user in that workspace.
- [ ] Every export event (export requested, export succeeded, export failed, retry attempted, schedule paused by system) is recorded in the audit log.

### Launch

- [ ] The entire feature is gated behind a feature flag and is off by default at launch.
