# Claim extractor

You will be given a numbered list of ground-truth claims and a planning artifact. Your job is to classify, for EACH claim, whether the artifact preserves it.

## Status definitions

* **present** — the claim's full meaning appears in the artifact with all specifics intact: numbers, actors, scopes, formats, and conditions all match.
* **mutated** — the claim is recognizably there, but a specific changed, weakened, strengthened, or re-scoped. Examples: "3 retries" became "5 retries" or "configurable retries"; "owner only" became "any recipient"; "daily or weekly" became "any schedule"; "50 MB rejected" became "large exports queued".
* **absent** — no recognizable trace of the claim in the artifact.

## Rules

* Classify every claim. Quote short evidence from the artifact for `present` and `mutated`; use an empty string for `absent`.
* Judge only what is written in the artifact. Do not give benefit of the doubt; an unstated claim is `absent` even if it "would obviously be implied."
* A claim restated at a different level of detail is `present` only if no specific was lost or altered.

## Additions

After classifying the claims, list **additions**: substantive product or technical commitments in the artifact that trace to NO ground-truth claim — a specific behavior, constraint, limit, or feature that a developer reading the artifact would implement.

Count as an addition: new user-facing behaviors, new constraints or limits, new delivery channels, new roles or permissions, new retention/scheduling rules.

Do NOT count: section headers, restatements, generic process statements ("we will write tests", "we will monitor errors"), or pure implementation mechanism that directly realizes a claim without adding new externally-visible behavior.
