# Business Plan: Scheduled Report Exports

## Summary

We will extend the reporting module with export capabilities that allow users to export any report as CSV or PDF, with support for one-off exports and recurring scheduled exports delivered by email. This feature will enable users to share and archive report data outside the application while maintaining strict compliance with row-level permissions and audit requirements. Scheduled exports will support daily and weekly recurrence with automatic retry and pause mechanisms for reliability, and all export functionality will be guarded by a feature flag and admin controls.

## Acceptance Criteria

- **Export Formats**: Users can export any report as CSV or PDF
- **Permission Compliance**: Every export respects the requesting user's row-level permissions; exported data never includes rows the user cannot view in the app
- **One-Off Exports**: Users can immediately export a report in either format
- **Scheduled Exports**: Users can configure recurring exports (daily or weekly frequency)
- **Email Delivery**: Scheduled exports are delivered to the schedule owner's email address only
- **Schedule Management**: Schedule owners can pause and resume their schedules at any time
- **Retry Logic**: Failed export deliveries are retried up to 3 times; after the third failure, the schedule is automatically paused
- **Export History**: Users can view the last 30 export runs for each of their schedules, including delivery status
- **Non-Blocking Generation**: Generating an export does not block interactive report viewing
- **Size Limit**: Exports larger than 50 MB are rejected with a clear error message to the user
- **Admin Controls**: Administrators can disable export functionality entirely for their workspace
- **Audit Logging**: Every export event is recorded in the workspace audit log
- **Feature Flag**: The feature ships behind a feature flag that can be toggled at launch and post-launch
