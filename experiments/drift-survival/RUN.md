# Run protocol

Executed entirely inside a Claude Code session via subagent fan-out — no API-key CLI invocations. All agents are locked to one model per run; record it in the run table in [README.md](./README.md).

## Parameters

* `N` — chains per arm (run-1: 5)
* `K` — extraction votes per artifact (run-1: 3)
* Model — every role: writers, gates, extractors (run-1: claude-sonnet-4-6)

## Steps

1. **Chains.** For each chain, sequentially spawn fresh subagents: plan-writer (input: [seed-idea.md](./seed-idea.md)) → approach-writer (input: the plan only) → phase-writer (input: the approach only). Each writer follows its pinned prompt in [prompts/](./prompts/) and saves its artifact under `results/raw/<run>/<arm>/chain-<i>/`.
   * **Ungated arm**: artifacts hand off directly.
   * **Gated arm**: after each writer, a gate subagent ([prompts/gate.md](./prompts/gate.md)) corrects the draft against the previous layer; the corrected artifact is what hands off and what gets extracted.
2. **Extraction.** For every artifact, spawn K independent extractor subagents ([prompts/extractor.md](./prompts/extractor.md)) with [seed-claims.md](./seed-claims.md) and the artifact text, returning structured JSON (claims with `present`/`mutated`/`absent` + evidence; additions).
3. **Positive control.** Extract the seed brief itself with K votes — survival must be ~100% or the instrument is broken; stop and fix the extractor or the seed.
4. **Score.** Collect all extraction records into `results/raw/<run>/extractions.json` and run `python3 score.py <path>`. The scorer is the only consumer of the JSON; no LLM judgment occurs downstream of it.
5. **Record.** Commit artifacts, extractions, and the scoring report under `results/`; add the run to the README table with model and date.

## Reading the report

* **Survival by layer** — hypothesis 1 predicts monotonic decay in the ungated arm; hypothesis 2 predicts a flatter gated curve.
* **Agreement** — mean modal-vote share; the instrument's noise. Survival differences smaller than (1 − agreement) are not findings.
* **Contested** — cells with no strict majority; high counts indict the seed claims, not the chains.
* **Resurrections** — claims absent at one layer and back at the next: embellishment that happens to coincide with intent.
