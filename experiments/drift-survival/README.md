# Drift survival

Measures whether conceptual drift compounds across the planning artifact layers described in [Iterative planning](../../concepts/iterative-planning.md): idea → business plan → technical approach → phase documents.

## Hypothesis

1. **Drift is real and compounds**: the fraction of ground-truth claims that survive intact decays monotonically with layer depth, and unsanctioned additions accumulate.
2. **A conceptual-diff gate flattens the curve**: inserting an added/dropped/mutated diff-and-correct step at each handoff preserves claims that would otherwise decay.

## Design

* **Seed**: a human-authored feature brief ([seed-idea.md](./seed-idea.md)) whose content is exactly 14 numbered atomic claims ([seed-claims.md](./seed-claims.md)). Chain writers see only the prose brief; the numbered claims are extractor-only ground truth.
* **Chains** (N per arm): each layer is written by a fresh subagent that sees **only the previous layer's artifact** — plan from brief, approach from plan, phases from approach.
* **Arms**: *ungated* (straight handoffs) vs *gated* (a conceptual-diff gate corrects each artifact against the previous layer before handoff).
* **Extraction** (k votes per artifact): a pinned extractor classifies every claim as `present` / `mutated` / `absent` with quoted evidence, and lists additions. Majority vote per claim; agreement rate reported.
* **Positive control**: the extractor runs against the seed brief itself — survival there should be ~100%, or the instrument is broken.
* **Scoring**: [score.py](./score.py) — deterministic set arithmetic over the extraction JSON. Survival / mutation / absence by layer depth, additions, resurrections (absent at layer N, back at N+1), agreement rates.

## Interpreting results

* Ungated survival decaying by depth while the positive control stays near 100% = hypothesis 1 supported.
* Gated curve flat (or markedly higher) relative to ungated = hypothesis 2 supported.
* Survival differences smaller than the extraction disagreement rate are noise, not drift.
* High contested-cell rate = the seed claims are too vague to extract reliably; fix the seed before trusting anything.

## Runs

| Run | Date | Model (all roles) | N chains/arm | k votes | Verdict |
| --- | --- | --- | --- | --- | --- |
| run-1 | 2026-06-09 | claude-sonnet-4-6 | 5 | 3 | H1 supported (94→86→86%, additions 5.4→9.4); H2 not supported at depth — gate ratchets. [Report](./results/run-1-report.md) |
| run-2 | 2026-06-09 | claude-haiku-4-5 | 10 | 3 | Haiku drifts less than Sonnet at every layer (99→97→88%); gate works at depth (96% vs 88%). Haiku-grades-Haiku confound noted. [Report](./results/run-2-report.md) |
| run-2 re-judge | 2026-06-10 | writers claude-haiku-4-5, extractors claude-sonnet-4-6 | 10 (reused artifacts) | 3 | Haiku judge was +5–15 pts lenient. Survival gap vs Sonnet collapses (94→87→81%); lower-additions finding survives (3.2→6.9 vs 5.4→9.4). Gate effect at depth collapses (81% vs 81%) but the per-claim ratchet replicates run-1. [Report](./results/run-2-report.md) |
