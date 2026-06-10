# run-0 (invalid)

First execution attempt, 2026-06-09. **Invalid — do not score.**

The seed brief was passed to the workflow via its `args` channel and arrived as `undefined`. Every plan writer received an empty input, wrote a "no brief was provided" plan, and the chains degenerated into fully generic, domain-free planning documents. All 138 agents completed without error; the run was green and measured nothing.

`workflow-output.json` holds the complete workflow result, including all 93 extraction records (every claim `absent` at every layer — correctly, since no claims were ever present).

## Lessons

* **Validate inputs at the orchestration layer.** The positive control (extracting the seed brief itself) could not catch this — the contamination was upstream of extraction. The rerun adds a guard that throws if the seed texts are missing, so the run fails instead of succeeding vacuously.
* **Agents proceed confidently on empty input.** Given `undefined` as a feature brief, downstream writers produced a complete, plausible, entirely generic delivery plan — phases, acceptance criteria, runbooks — anchored to nothing. A live demonstration of why handoff fidelity, not agent diligence, is the thing to verify.
* **Archive invalid runs; don't delete them.** This directory exists because the artifacts were initially deleted and had to be recovered from the task output. Failed runs are data.
