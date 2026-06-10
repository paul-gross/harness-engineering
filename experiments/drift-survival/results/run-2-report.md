# Drift survival — scoring report

## Survival by layer

| Arm | Layer | Survival | Mutated | Absent | Contested | Agreement | Additions (mean of per-chain medians) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gated | plan | 100% | 0% | 0% | 0 | 100% | 2.8 |
| gated | approach | 99% | 1% | 1% | 1 | 99% | 6.9 |
| gated | phases | 96% | 2% | 2% | 0 | 98% | 7.8 |
| seed-control | seed (control) | 100% | 0% | 0% | 0 | 100% | 0.0 |
| ungated | plan | 99% | 1% | 0% | 0 | 100% | 2.9 |
| ungated | approach | 97% | 3% | 0% | 0 | 98% | 6.8 |
| ungated | phases | 88% | 8% | 4% | 3 | 95% | 7.0 |

## Resurrections (absent at layer N, back at N+1)

* none observed

## Per-claim status at phase-docs layer (ungated)

| Claim | present | mutated | absent | contested |
| --- | --- | --- | --- | --- |
| C1 | 9 | 0 | 1 | 0 |
| C2 | 9 | 0 | 1 | 0 |
| C3 | 10 | 0 | 0 | 0 |
| C4 | 9 | 1 | 0 | 0 |
| C5 | 5 | 4 | 0 | 1 |
| C6 | 8 | 2 | 0 | 0 |
| C7 | 9 | 1 | 0 | 0 |
| C8 | 10 | 0 | 0 | 0 |
| C9 | 9 | 1 | 0 | 0 |
| C10 | 4 | 0 | 4 | 2 |
| C11 | 9 | 1 | 0 | 0 |
| C12 | 10 | 0 | 0 | 0 |
| C13 | 10 | 0 | 0 | 0 |
| C14 | 9 | 1 | 0 | 0 |

Note: survival differences smaller than (1 - agreement) are within instrument noise.

## Findings (run-2, Haiku-locked, N=10)

**Instrument: valid on its own terms.** Control 100%, agreement 95–100%, contested 6/420 cells. Caveat: the instrument changed with the phenomenon (Haiku grading Haiku) — see confound below.

**Headline: Haiku drifted *less* than Sonnet, at every layer, in both arms.**

| Ungated | plan | approach | phases | additions (plan→phases) |
| --- | --- | --- | --- | --- |
| Sonnet (run-1, N=5) | 94% | 86% | 86% | 5.4 → 9.4 |
| Haiku (run-2, N=10) | 99% | 97% | 88% | 2.9 → 7.0 |

Proposed mechanism, visible in the artifacts: Haiku copies phrasing nearly verbatim and embellishes far less at the first hop (2.9 vs 5.4 additions per plan). Sonnet elaborates — and elaboration is where mutation lives. Supports the thesis that embellishment is the carrier of drift, and that drift resistance is not monotone in model capability.

**The gate worked at depth this time: 96% vs 88% ungated at phases (above noise).** Per-claim, the gate rescued exactly the claims that died ungated: C5 owner-only (9/10 vs 5/10) and C10 the NFR (8/10 vs 4/10) — the same C10 the gate *killed* in run-1. Consistent with the ratchet mechanism: the adjacent-layer gate amplifies whatever the previous layer preserved. Haiku's approach layer held 97–99% fidelity, so the gate's reference still contained the NFR and the gate defended it; Sonnet's approach layer had already weakened it, so the gate enforced the loss.

**Signature partially replicates across models.** The NFR (C10) is again the biggest casualty (4 absent + 2 contested of 10 ungated) and "owner only" again weakens (C5, 4/10 mutated). But the retry off-by-one that infected most Sonnet chains barely appears (C7/C8 ≈ clean) — Haiku transcribes numbers it does not paraphrase.

**Confound to discharge before trusting the cross-run comparison.** Both the writers and the extractor changed between runs. A more lenient extractor inflates survival; control and agreement prove consistency, not strictness. Decisive check, no chain re-runs needed: re-extract run-2's on-disk artifacts with Sonnet extractors and re-score.

## Run metadata

* Date: 2026-06-09, model: claude-haiku-4-5 (all roles), N=10 chains/arm, K=3 votes, 273 agents, ~4.4M subagent tokens, 7.7 min wall.
