# Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to export reports in CSV and PDF formats with immediate one-off exports and recurring scheduled exports. All exports will respect row-level permissions, ensuring users only export data they have access to. Scheduled exports will be delivered via email on daily or weekly cadences, owned by individual users who can manage delivery and track run history. The feature will include reliability safeguards (retry logic, automatic pause on persistent failures), audit logging, administrative controls to disable the feature workspace-wide, and will launch behind a feature flag.

## Acceptance Criteria

- Users can export any report as CSV or PDF in a single action
- All exports respect the requesting user's row-level permissions; no user can export rows they cannot view in the app
- Users can create a recurring scheduled export of any report on daily or weekly frequency
- Scheduled exports are delivered by email to the schedule owner only
- Schedule owners can pause and resume their schedules at any time
- Failed export deliveries are retried up to 3 times total; after the third failure, the schedule is automatically paused
- Users can view a history of the last 30 export runs for each schedule
- Export generation does not block interactive report viewing (non-blocking implementation)
- Exports larger than 50 MB are rejected with a clear error message to the user
- Admins can disable export functionality entirely at the workspace level via configuration
- Every export event (one-off and scheduled) is recorded in the audit log
- The entire feature launches behind a feature flag and can be toggled for gradual rollout
