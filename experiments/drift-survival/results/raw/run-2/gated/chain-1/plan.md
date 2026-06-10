# Scheduled Report Exports — Business Plan

## Summary

We are adding export and scheduling capabilities to the reporting module to enable users to distribute report data beyond the interactive UI. Users will be able to export any report on-demand as CSV or PDF, with full respect for their row-level permissions. Beyond one-off exports, we will enable users to schedule recurring exports (daily or weekly) that are automatically delivered by email. This feature addresses the need for report data integration into external workflows and regular distribution to stakeholders. To manage reliability, scheduled exports will retry failed deliveries up to 3 times, and will automatically pause if all retries are exhausted. The feature will launch behind a feature flag, and admins will have the ability to disable exports entirely for their workspace.

## Acceptance Criteria

### One-off Exports

- [ ] Users can export any report as CSV
- [ ] Users can export any report as PDF
- [ ] Exports respect the requesting user's row-level permissions — no rows the user cannot see in the app are included
- [ ] Exports larger than 50 MB are rejected with a clear, actionable error message to the user
- [ ] Export generation does not block interactive report viewing (async/background processing)
- [ ] Every export event is recorded in the audit log with the export type, report, user, and timestamp

### Scheduled Exports

- [ ] Users can create a schedule to export a report on a recurring basis (daily or weekly cadence)
- [ ] Scheduled exports are delivered by email
- [ ] Only the owner of the schedule can receive deliveries; the schedule owner is the only recipient
- [ ] The owner can pause a schedule at any time
- [ ] The owner can resume a paused schedule
- [ ] Users can view a history of the last 30 export runs for each schedule for transparency about export reliability and delivery outcomes
- [ ] Every scheduled export event is recorded in the audit log

### Delivery and Resilience

- [ ] Failed export deliveries are automatically retried up to 3 times
- [ ] If the third retry fails, the schedule is automatically paused
- [ ] The schedule history reflects each delivery attempt and its outcome

### Admin Controls and Feature Gating

- [ ] Admins can disable the entire export feature for their workspace
- [ ] The feature ships behind a feature flag (disabled by default)
- [ ] Enabling the feature flag activates both one-off and scheduled export capabilities
- [ ] When the feature is disabled or exports are disabled for the workspace, the UI does not expose export options
