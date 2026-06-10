# Conceptual-diff gate

You will be given a REFERENCE document (layer N) and a DRAFT document (layer N+1) generated from it. Your job is to correct the DRAFT so it is conceptually faithful to the REFERENCE.

## Procedure

1. Extract the substantive commitments of the REFERENCE: behaviors, constraints, limits, actors, conditions.
2. Extract the substantive commitments of the DRAFT.
3. Compute the conceptual diff:
   * **added** — commitments in the DRAFT not sanctioned by the REFERENCE
   * **dropped** — commitments in the REFERENCE missing from the DRAFT
   * **mutated** — commitments whose specifics (numbers, actors, scopes, conditions) changed between REFERENCE and DRAFT
4. Emit a corrected version of the DRAFT: remove unsanctioned additions, restore dropped commitments, and fix mutated specifics to match the REFERENCE exactly.

## Rules

* Preserve the DRAFT's document type, structure, and purpose — it is a different kind of document than the REFERENCE. Do not copy the REFERENCE; correct the DRAFT.
* Pure implementation mechanism that realizes a REFERENCE commitment is not an addition — leave it.
* When in doubt whether something is sanctioned, treat it as an addition and remove it.

Output only the corrected DRAFT document.
