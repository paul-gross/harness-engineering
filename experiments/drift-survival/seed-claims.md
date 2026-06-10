# Ground-truth claims

The atomic claims contained in [seed-idea.md](./seed-idea.md).  Extractor-only — never shown to chain writers.

* **C1**: Users can export any report as CSV.
* **C2**: Users can export any report as PDF.
* **C3**: Exports respect the requesting user's row-level permissions (an export never contains rows the user cannot see).
* **C4**: Users can schedule a recurring export of a report, daily or weekly.
* **C5**: Scheduled exports are delivered by email to the schedule owner only.
* **C6**: A schedule can be paused and resumed by its owner.
* **C7**: Failed export deliveries are retried at most 3 times.
* **C8**: After the third failed retry, the schedule is automatically paused.
* **C9**: Users can view a history of the last 30 export runs per schedule.
* **C10**: Export generation must not block interactive report viewing.
* **C11**: Exports larger than 50 MB are rejected with a clear error message.
* **C12**: Admins can disable export functionality per workspace.
* **C13**: All export events are recorded in the audit log.
* **C14**: The feature ships behind a feature flag at launch.
