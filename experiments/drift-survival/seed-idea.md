# Feature request: scheduled report exports

We want to add export capabilities to the reporting module.  Users should be able to export any report as CSV, and also as PDF.  Exports must respect the requesting user's row-level permissions — an export must never contain rows the user cannot see in the app.

Beyond one-off exports, users should be able to schedule a recurring export of a report, either daily or weekly.  Scheduled exports are delivered by email, and only to the owner of the schedule.  The owner can pause and resume their schedule at any time.

Delivery isn't always reliable, so failed export deliveries should be retried, but at most 3 times.  If the third retry also fails, the schedule is automatically paused.  For transparency, users should be able to view a history of the last 30 export runs for each schedule.

A few constraints.  Generating an export must not block interactive report viewing.  Exports larger than 50 MB are rejected with a clear error message.  Admins need the ability to disable export functionality entirely for their workspace.  Every export event must be recorded in the audit log.  And since this is a new surface, the whole feature ships behind a feature flag at launch.
