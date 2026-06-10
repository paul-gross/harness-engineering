# Scheduled Report Exports — Business Plan

## Summary

We will add export capabilities to the reporting module, enabling users to export any report in CSV or PDF format, with support for one-off and recurring scheduled exports. This feature addresses the need for users to consume report data outside the app and enables automated reporting workflows.

The feature respects row-level permissions for all exports, ensuring users cannot access data through exports that they cannot view in the app. Scheduled exports are delivered via email to the schedule owner only, with automatic retry logic and pause-on-failure safeguards to handle delivery unreliability. Exports will not block interactive report viewing, and the feature ships behind a feature flag to allow controlled rollout.

## Acceptance Criteria

- [ ] Users can export any report as CSV with a single action
- [ ] Users can export any report as PDF with a single action
- [ ] All exports respect the requesting user's row-level permissions; exported data never includes rows the user cannot see in the app
- [ ] Users can create a scheduled recurring export for any report
- [ ] Scheduled exports can be configured for daily or weekly recurrence
- [ ] Scheduled exports are delivered via email to the schedule owner
- [ ] Only the schedule owner can view, pause, resume, or delete their scheduled exports
- [ ] Users can view a history of the last 30 export runs for each scheduled export, including success/failure status
- [ ] Failed export deliveries are automatically retried up to 3 times
- [ ] If a scheduled export fails all 3 retries, the schedule is automatically paused and the owner is notified
- [ ] Generating an export does not block interactive report viewing (exports are processed asynchronously)
- [ ] Exports larger than 50 MB are rejected with a clear, user-facing error message
- [ ] Workspace admins can disable export functionality entirely for their workspace
- [ ] Every export event (one-off and scheduled) is recorded in the audit log with relevant details (user, report, format, size, status)
- [ ] The feature ships behind a feature flag that admins can enable or disable
- [ ] Feature flag defaults to disabled at launch
