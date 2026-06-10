# Drift survival — scoring report

## Survival by layer

| Arm | Layer | Survival | Mutated | Absent | Contested | Agreement | Additions (mean of per-chain medians) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gated | plan | 100% | 0% | 0% | 0 | 99% | 4.2 |
| gated | approach | 94% | 4% | 1% | 0 | 97% | 7.6 |
| gated | phases | 84% | 10% | 6% | 0 | 95% | 8.0 |
| seed-control | seed (control) | 100% | 0% | 0% | 0 | 100% | 0.0 |
| ungated | plan | 94% | 6% | 0% | 0 | 98% | 5.4 |
| ungated | approach | 86% | 14% | 0% | 0 | 95% | 8.4 |
| ungated | phases | 86% | 11% | 3% | 0 | 95% | 9.4 |

## Resurrections (absent at layer N, back at N+1)

* gated: 1

## Per-claim status at phase-docs layer (ungated)

| Claim | present | mutated | absent | contested |
| --- | --- | --- | --- | --- |
| C1 | 5 | 0 | 0 | 0 |
| C2 | 5 | 0 | 0 | 0 |
| C3 | 5 | 0 | 0 | 0 |
| C4 | 4 | 1 | 0 | 0 |
| C5 | 4 | 1 | 0 | 0 |
| C6 | 5 | 0 | 0 | 0 |
| C7 | 2 | 3 | 0 | 0 |
| C8 | 2 | 3 | 0 | 0 |
| C9 | 5 | 0 | 0 | 0 |
| C10 | 3 | 0 | 2 | 0 |
| C11 | 5 | 0 | 0 | 0 |
| C12 | 5 | 0 | 0 | 0 |
| C13 | 5 | 0 | 0 | 0 |
| C14 | 5 | 0 | 0 | 0 |

Note: survival differences smaller than (1 - agreement) are within instrument noise.

## Findings

**Instrument: valid.** Positive control 100% survival, 100% agreement, zero additions. Extraction agreement 95–99% across all cells, zero contested cells — the noise floor is ~5%, and the signals below clear it except where noted.

**Hypothesis 1 (drift is real and compounds): supported, with texture.** Ungated survival decays 94% → 86% → 86% and additions accumulate monotonically (5.4 → 8.4 → 9.4 per artifact). But the washout is gentler than intuition suggests at three layers — Sonnet 4.6 carries ~86% of atomic claims through three blind handoffs. The drift signature is specific:

* **Numbers mutate first.** "Retried at most 3 times" (3 retries = 4 attempts) silently became "3 total attempts" (= 2 retries) in most chains in both arms — a compounding off-by-one in retry semantics (C7/C8 mutated in 3/5 ungated chains at depth).
* **Enums genericize.** "Daily or weekly" became unspecified "cadence/frequency" by the phase layer (C4).
* **Restrictions weaken.** "Delivered to the owner only" lost its "only" (C5).
* **NFRs vanish.** "Must not block interactive viewing" (C10) went fully absent in 2/5 ungated chains — the only outright claim deaths.
* **Embellishments accrete.** "Owner is notified on auto-pause," flag toggling "without a code deployment," status taxonomies — none sanctioned by the seed.

**Hypothesis 2 (the gate flattens the curve): not supported at depth.** The gate wins decisively at the first handoff (100% vs 94% survival) and suppresses additions at every layer (4.2/7.6/8.0 vs 5.4/8.4/9.4), but by the phase layer gated survival is 84% vs ungated 86% — inside the noise floor. Proposed mechanism: **the gate ratchets.** It diffs against the *previous layer only*, so any drift that survives one gate becomes the reference the next gate enforces. Run-2 should test a root-anchored gate that diffs every layer against the seed (and intermediate layers), which is also what iterative planning prescribes — each artifact anchored to the layer above it *and* the origin.

## Run metadata

* Date: 2026-06-09, model: claude-sonnet-4-6 (all roles), N=5 chains/arm, K=3 votes, 138 agents, ~2.2M subagent tokens, 9.5 min wall.
* run-0 (seed never reached the writers) archived at `raw/run-0-invalid/` — failed runs are data.
