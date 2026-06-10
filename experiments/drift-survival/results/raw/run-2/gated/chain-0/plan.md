# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to export reports as CSV or PDF with full respect for row-level permissions. Beyond one-off exports, users can schedule recurring exports (daily or weekly) that are delivered via email. The feature includes automatic retry logic with a 3-attempt limit, export history tracking for the last 30 runs, and admin controls to disable the feature workspace-wide. All exports are asynchronous to avoid blocking interactive report viewing, and the entire feature ships behind a feature flag at launch. This unlocks powerful reporting and automation workflows while maintaining security and system stability.

## Acceptance Criteria

- [ ] Users can export any report as CSV with a single action
- [ ] Users can export any report as PDF with a single action
- [ ] All exports respect the requesting user's row-level permissions — no rows visible only to other users appear in the export
- [ ] Users can schedule a recurring export of any report with frequency set to either daily or weekly
- [ ] Scheduled exports are delivered to the schedule owner via email at the configured frequency
- [ ] The schedule owner can pause their schedule at any time
- [ ] The schedule owner can resume a paused schedule at any time
- [ ] Only the schedule owner receives emails for that schedule; other users cannot access or modify it
- [ ] Failed export deliveries are automatically retried, with a maximum of 3 total delivery attempts
- [ ] If all 3 delivery attempts fail, the schedule is automatically paused
- [ ] Users can view a history of the last 30 export runs for each schedule they own
- [ ] Export history displays information about each run (timestamp, success/failure status, file size, delivery method, etc.)
- [ ] Export generation does not block interactive report viewing
- [ ] Exports larger than 50 MB are rejected with a clear error message before generation begins
- [ ] Admins can disable export functionality entirely via a workspace-level setting
- [ ] When export functionality is disabled by an admin, scheduled exports do not run and users cannot initiate new exports
- [ ] Every export event (one-off export, scheduled export generation, delivery attempt, success, failure, retry, pause, resume) is recorded in the audit log
- [ ] The entire feature is gated behind a feature flag that is off by default at launch
