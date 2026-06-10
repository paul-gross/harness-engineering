#!/usr/bin/env python3
"""Deterministic scorer for the drift-survival experiment.

Reads extraction JSON (a list of vote records) and prints a markdown report.
No LLM, no randomness: Counter, median, mean, sorted iteration only.

Record shape:
  {"arm": "ungated|gated|seed-control", "chain": 0, "layer": 1, "layerName": "plan",
   "vote": 0, "claims": [{"id": "C1", "status": "present|mutated|absent", "evidence": "..."}],
   "additions": [{"summary": "..."}]}
"""
import json
import sys
from collections import Counter, defaultdict
from statistics import mean, median

LAYER_NAMES = {0: "seed (control)", 1: "plan", 2: "approach", 3: "phases"}


def resolve(votes):
    """Majority vote over statuses. Strict majority required, else contested."""
    counter = Counter(votes)
    status, n = counter.most_common(1)[0]
    share = n / len(votes)
    return (status if n * 2 > len(votes) else "contested"), share


def main(path):
    records = json.load(open(path))

    # cells[(arm, layer)][(chain, claim)] = [status per vote]
    cells = defaultdict(lambda: defaultdict(list))
    # adds[(arm, layer)][chain] = [addition count per vote]
    adds = defaultdict(lambda: defaultdict(list))

    for r in records:
        for c in r["claims"]:
            cells[(r["arm"], r["layer"])][(r["chain"], c["id"])].append(c["status"])
        adds[(r["arm"], r["layer"])][r["chain"]].append(len(r["additions"]))

    # Resolve every cell once; keep per-chain-claim resolution for resurrection check.
    resolved = {}  # (arm, layer, chain, claim) -> status
    print("# Drift survival — scoring report\n")
    print("## Survival by layer\n")
    print("| Arm | Layer | Survival | Mutated | Absent | Contested | Agreement | Additions (mean of per-chain medians) |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")

    for (arm, layer) in sorted(cells, key=lambda k: (k[0], k[1])):
        statuses, shares = [], []
        for (chain, claim), votes in sorted(cells[(arm, layer)].items()):
            status, share = resolve(votes)
            resolved[(arm, layer, chain, claim)] = status
            statuses.append(status)
            shares.append(share)
        n_resolved = sum(1 for s in statuses if s != "contested")
        contested = len(statuses) - n_resolved

        def rate(name):
            return sum(1 for s in statuses if s == name) / n_resolved if n_resolved else 0.0

        addition_medians = [median(v) for _, v in sorted(adds[(arm, layer)].items())]
        print(
            f"| {arm} | {LAYER_NAMES.get(layer, layer)} "
            f"| {rate('present'):.0%} | {rate('mutated'):.0%} | {rate('absent'):.0%} "
            f"| {contested} | {mean(shares):.0%} | {mean(addition_medians):.1f} |"
        )

    # Resurrections: absent at layer L, present/mutated at layer L+1 (same arm/chain/claim).
    print("\n## Resurrections (absent at layer N, back at N+1)\n")
    res = Counter()
    for (arm, layer, chain, claim), status in resolved.items():
        if layer in (1, 2) and status == "absent":
            after = resolved.get((arm, layer + 1, chain, claim))
            if after in ("present", "mutated"):
                res[arm] += 1
    for arm in sorted(res) or ["(none)"]:
        print(f"* {arm}: {res[arm]}" if arm != "(none)" else "* none observed")

    # Per-claim survival at the deepest layer, ungated arm: which claims die first.
    print("\n## Per-claim status at phase-docs layer (ungated)\n")
    print("| Claim | present | mutated | absent | contested |")
    print("| --- | --- | --- | --- | --- |")
    per_claim = defaultdict(Counter)
    for (arm, layer, chain, claim), status in resolved.items():
        if arm == "ungated" and layer == 3:
            per_claim[claim][status] += 1
    for claim in sorted(per_claim, key=lambda c: int(c[1:])):
        c = per_claim[claim]
        print(f"| {claim} | {c['present']} | {c['mutated']} | {c['absent']} | {c['contested']} |")

    print("\nNote: survival differences smaller than (1 - agreement) are within instrument noise.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/raw/run-1/extractions.json")
