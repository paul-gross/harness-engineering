# Business Plan: Scheduled Report Exports

## Summary

We will add export capabilities to the reporting module, enabling users to export reports as CSV or PDF on-demand, and to schedule recurring exports delivered via email. The feature addresses a key user need for data portability and automated reporting workflows, while maintaining security through row-level permission enforcement and audit logging.

### What We Build

**Immediate capabilities:**
- One-off CSV and PDF exports of any report, respecting the requesting user's row-level permissions
- Scheduled recurring exports (daily or weekly frequency) delivered to the schedule owner's email
- Pause/resume controls for scheduled exports
- Export history tracking (last 30 runs per schedule) with delivery status visibility
- Automatic pause on repeated delivery failures (max 3 retries before auto-pause)

**Non-blocking and safety measures:**
- Exports run asynchronously to avoid blocking interactive report viewing
- Export size limit of 50 MB with clear error messaging for oversized exports
- Admin controls to disable export functionality workspace-wide
- Complete audit logging of all export events
- Feature flag gating at launch

### Why Now

Users frequently need to share report data with colleagues, integrate into external systems, and receive automated updates. Without this capability, they rely on manual exports, email forwarding, and ad-hoc workarounds that don't scale. Scheduled exports with reliable delivery and clear history reduce friction and establish the reporting module as a primary data source for users' workflows.

## Acceptance Criteria

### Core Export Functionality
- [ ] Users can export any report as CSV from the UI
- [ ] Users can export any report as PDF from the UI
- [ ] Exports contain only rows the requesting user has permission to view (row-level security enforced)
- [ ] Export generation does not block interactive report viewing (asynchronous processing)
- [ ] Exports exceeding 50 MB are rejected with a clear, user-facing error message
- [ ] Every export event is logged to the audit log with user, report, format, timestamp, and outcome

### Scheduled Exports
- [ ] Users can create a scheduled export for any report (frequency: daily or weekly)
- [ ] Scheduled exports are owned by and delivered only to the user who created them
- [ ] Users can pause a scheduled export and resume it without losing configuration
- [ ] Scheduled exports run at defined intervals and initiate email delivery

### Delivery and Retry Logic
- [ ] Failed export deliveries are automatically retried (max 3 attempts total)
- [ ] If delivery fails on all 3 attempts, the schedule is automatically paused with audit logging
- [ ] Users can manually resume a paused schedule at any time

### Export History and Visibility
- [ ] Users can view a history of the last 30 export runs for each schedule they own
- [ ] History includes export timestamp, status (success/failed), file size, and delivery outcome (if applicable)
- [ ] History is accessible from the scheduled export detail view or a dedicated history tab

### Administrative Controls
- [ ] Admins can disable export functionality entirely for their workspace
- [ ] When disabled, all export and scheduled export UI elements are hidden
- [ ] Audit log records when an admin enables or disables export functionality

### Feature Flag
- [ ] The entire export feature launches behind a feature flag
- [ ] Flag controls visibility and availability of export capabilities
- [ ] Feature flag can be toggled without code deployment

### Security and Logging
- [ ] Row-level permissions are enforced in all export formats (CSV and PDF)
- [ ] All export actions (one-off and scheduled) are recorded in the audit log
- [ ] Audit entries include: user ID, report ID, export format, export size, timestamp, status, and any error details
