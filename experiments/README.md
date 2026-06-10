# Experiments

Runnable experiments that back the network's claims with data.  Where the concept notes assert an intuition, an experiment here measures it.

## Format

Each experiment is a directory with a fixed shape:

| File | Purpose |
| --- | --- |
| `README.md` | Hypothesis, design, and how to interpret results |
| Seed inputs | Pinned, human-authored ground truth |
| `prompts/` | Pinned prompts — the instrument, versioned with the results |
| `RUN.md` | The protocol a Claude Code session executes |
| Scoring script | Deterministic scoring — no LLM downstream of the extraction output |
| `results/` | Committed runs, each stamped with model version and date |

## Rules

* **Runs on a subscription**: all LLM work is subagent fan-out inside a Claude Code session — no API-key CLI invocations
* **Pin everything**: model, prompts, and seeds are committed alongside the results they produced
* **Measure the instrument before the phenomenon**: every protocol includes a noise-floor or positive-control step
* **Quarantine judgment**: LLM judgment is collapsed into closed-vocabulary JSON and stabilized by voting; everything downstream is pure arithmetic

## Catalog

| Experiment | Claim under test |
| --- | --- |
| [Drift survival](./drift-survival/README.md) | Drift compounds across planning artifact layers ([High level thinking drift](../concepts/high-level-thinking-drift.md)) |
