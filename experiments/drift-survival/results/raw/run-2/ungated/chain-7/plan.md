# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to export reports as CSV or PDF with full respect for row-level permission boundaries. Beyond one-off exports, users can set up recurring daily or weekly exports delivered by email. The feature includes automatic retry logic with a 3-attempt limit, a 30-run history per schedule, and admin controls to disable exports workspace-wide. All exports are audit-logged, and the feature launches behind a feature flag.

This capability addresses user demand for report portability and automation while maintaining security boundaries and system stability. By respecting permissions in exports, we ensure data compliance. By gating the feature flag-first, we can safely roll out to users and monitor system impact.

## Acceptance Criteria

### Export Functionality
- [ ] Users can export any report as CSV
- [ ] Users can export any report as PDF
- [ ] Exports respect the requesting user's row-level permissions (no rows the user cannot see in the app are included)
- [ ] Exports are rejected with a clear error message if they exceed 50 MB

### Scheduled Exports
- [ ] Users can schedule a recurring export on a daily or weekly cadence
- [ ] Scheduled exports are delivered by email
- [ ] Scheduled exports are delivered only to the schedule owner
- [ ] Schedule owners can pause and resume their schedules at any time

### Reliability & History
- [ ] Failed deliveries are automatically retried up to 3 times
- [ ] After the third retry failure, the schedule is automatically paused
- [ ] Users can view the history of the last 30 export runs for each schedule
- [ ] Each history entry includes delivery status (success/failed/retried)

### Admin Controls
- [ ] Admins can disable export functionality entirely for their workspace

### Audit & Feature Flag
- [ ] Every export event is recorded in the audit log
- [ ] The feature ships behind a feature flag at launch
- [ ] The feature flag controls visibility of export UI and scheduling capabilities

### System Constraints
- [ ] Generating an export does not block interactive report viewing (exports are asynchronous)
