# Recoverable Regret Protocol

**Status:** PROVISIONAL_DECISION. This contract documents the evaluation plane
as **built and certified** under D-071 .. D-074 (`tools/regret.py`,
`tools/regret_reference.py`, `tools/regret_phase1.py`,
`tools/regret_phase2.py`, `tools/regret_phase3.py`). It was written after the
instrument, to close a corpus gap: the phases existed in the register and in
the code with no contract of record. Every number it reports is MODEL_DERIVED
under an uncertified simulator; the economic verdict remains
`NO_ECONOMIC_CLAIM` (rule 12).

## 1. Position in the architecture

The evaluator is a **measurement plane layered on top of** the V8 decision
path. It does not replace, extend, or feed back into it.

```text
MarketState → Experts → Candidate Store → V8 policy → Replay Model
                              │                            │
                              └────────────┬───────────────┘
                                           ▼
                                     Outcome Cube
                                           ▼
                              Constrained Hindsight Evaluator
                                           ▼
                           Systematicity → Recoverability gate
                                           ▼
                              Finding | UNKNOWN | Rejected
```

The instrument is a **read-only consumer of a completed Lab store**. It never
re-runs `Lab.run`, never creates a second Candidate population, and never
touches an Expert, a geometry, or a verdict.

## 2. Constitutional invariants

These are not implementation choices. A change to any of them is a change to
what the evaluator means.

| # | Invariant |
|---|---|
| I1 | The Expert stays deterministic; the evaluator never influences proposal generation |
| I2 | A Candidate is an immutable proposal; the evaluator may not create, modify, or delete one |
| I3 | Future data is never a decision feature; PIT lineage is asserted, not assumed |
| I4 | Replay output is MODEL_DERIVED, never observed truth |
| I5 | The actual policy remains the V8 policy; the evaluator scores it, it does not become it |
| I6 | The evaluator abstains rather than fills a cell it cannot justify |

I2 is what distinguishes this from a search: the evaluator explores the space
of **actions on Candidates that were actually proposed**, never the space of
Candidates that might have been proposed.

## 3. Pipeline

| Stage | Output | Failure mode it prevents |
|---|---|---|
| `CandidateSnapshot` join | per-Candidate birth state, geometry, actual action | re-derives `episode_key` rather than trusting a stored edge |
| PIT lineage assertion | violation count (must be 0) | a birth feature whose availability clock postdates the decision clock |
| Ledger reconciliation | `Replay(C, a_actual, M) == observed` | an evaluator whose replay disagrees with the run it is scoring |
| `LegalActionManifest` | `A(C)` | an action universe that excludes the action actually taken |
| `ModelDerivedOutcomeCube` | `cube.jsonl` | a manufactured value for a degenerate future (`OUTCOME_CUBE_SPEC` §3) |
| `LegalHindsightGap` | `regret.jsonl` | a maximum taken over a set containing an unevaluable cell |

Reconciliation is the load-bearing gate. If the evaluator's replay of the
actual action does not reproduce the ledger, every counterfactual it computes
is measured against a different world than the one that was executed.

## 4. Phases as built

### Phase 0 — instrument and reconciliation (D-071)

Produces a reconciliation verdict, a cube, and a per-Candidate gap. **Computes
no statistics** — no slicing, no multiplicity correction, no attribution, no
recoverability.

Certification evidence: a golden synthetic fixture reconciles 12/12 exact at
1e-12; a real 12-month single-symbol BTCUSDT 1h store (1,532 Candidates, from a
checksum-verified 6-symbol tape — 144 archives, 59,130 rows, 0 duplicates,
monotonic, 0 venue-sequence gaps) reconciles 754/754 exact at 1e-12 with zero
field deviation; PIT lineage clean on both; `hindsight >= actual` holds with
zero negative gaps across 543 COMPUTED Candidates; an independently written
reference walk (`tools/regret_reference.py`, importing nothing from
`v8.simulator`) agrees with the canonical simulator on 150 randomized paths;
five fault-injection cases behave as specified.

### Phase 1 — Candidate-local opportunity accounting (D-072)

A pure join plus a pre-declared descriptive breakdown over the full certified
dev dataset (9,218 Candidates: 6 symbols x 3 pilot Experts x a 12-month trimmed
window). Labelled `MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED`. Zero statistics by
construction.

### Phase 2 — systematicity discovery (D-072)

Reuses `src/v8/statistics.py` **in full** — `select_block_size`,
`bootstrap_ci`, `effective_independent_episodes`, `practical_significance`,
`expected_false_positives` / `effective_search_size` — with zero new estimator
code. This is deliberate: a second estimator implementation is a second place
for a multiplicity error to hide.

Declared family: 72 slices (3 Experts x 6 symbols x 2 directions x 2
estimands), scored on a chronological **discovery** half (4,609 Candidates).
Any `CANDIDATE_SYSTEMATIC` slice is queried against the untouched
**confirmation** half (4,609 Candidates) **exactly once**.

Result: 12 of 72 slices (16.7%, against `expected_false_positives(72, 0.05)` =
3.6 under the null) reached `CANDIDATE_SYSTEMATIC` on
`mean_legal_hindsight_gap`; none on `mean_actual_vs_no_trade`; all 12
replicated as `SYSTEMATIC_FINDING` with zero `FAILED_CONFIRMATION` and stable
estimates across halves (`trend_pullback|BTCUSDT|LONG`: 0.677R CI[0.593, 0.760]
→ 0.499R CI[0.402, 0.594]; `failed_breakout|BTCUSDT|SHORT`: 1.052R
CI[0.965, 1.136] → 1.005R CI[0.923, 1.088]). The pattern is directionally
coherent: `trend_pullback` clears the Bonferroni-corrected bar
(`alpha_slate` ~0.000694) on LONG across all 6 symbols and never on SHORT;
`failed_breakout` mirrors it on SHORT; `liquidity_sweep_reclaim` clears no
slice.

### Phase 3 — recoverability (D-073)

Tests all 12 confirmed findings against a small declared **decision-time**
policy class: `ALWAYS_TRADE` (the deployed policy, present for the
`V_A <= V_R` containment requirement) plus 24 `THRESHOLD_GATE` policies
(3 declared birth-state features x 2 directions x 4 discovery-half quantiles)
that choose `NO_TRADE` when a birth-time feature crosses a threshold.

Policy selection happens on the discovery half only; `V_A`, `V_R` and
`G_R = V_R - V_A` are estimated on the same untouched confirmation half, with
the same bootstrap machinery and the same 0.05R materiality floor.

Result: 11 of 12 slices reach `RECOVERABLE_WITHIN_CLASS`
(`ci_lower(G_R) > 0` and `mean(G_R) >= 0.05R`); `trend_pullback|SOLUSDT|LONG`
fails at `ci_lower` = -0.005 and is classified `NOT_RECOVERABLE_WITHIN_CLASS` —
a scoped negative for this class and this environment, never an absolute
unpredictability claim.

### Phase 4 — controlled single-component intervention (D-074)

Targets exactly one of the 11: `failed_breakout|SHORT`, chosen because it is
the one pattern with cross-symbol coherence (4 of 6 symbols independently
select `bb_pct_b NO_TRADE_BELOW` ~0.73) rather than the heterogeneous
`trend_pullback` pattern. A **new registered variant** `failed_breakout` v2
adds one declared, frozen pre-entry filter (skip the Candidate when
`bb_pct_b < 0.70` at the setup bar — a round pre-declared threshold, not the
fitted per-symbol value). Every other line is byte-identical to v1. The shipped
v1 is never mutated in place (rule 15, D-023).

## 5. What "recoverable" means, precisely

```text
V_A  = mean utility of the actual (deployed) policy on the confirmation half
V_R  = mean utility of the best policy selected from the declared class
G_R  = V_R - V_A
```

A slice is `RECOVERABLE_WITHIN_CLASS` when `ci_lower(G_R) > 0` and
`mean(G_R) >= 0.05R`. Three qualifications are part of the definition, not
caveats attached to it:

1. **Scoped to the declared class.** "Not recoverable" means *this policy class
   did not recover it here*, never "no decision rule could".
2. **Selection is not protected by the CI.** The bootstrap CI protects the mean
   estimate on confirmation; it does not protect the discovery-half
   feature/threshold selection step. Twelve independently selected single-
   feature gates finding no common rule is evidence **against** a single clean
   mechanism and **for** either genuine cross-symbol heterogeneity or
   discovery-half overfitting.
3. **Hindsight opportunity is not recoverable opportunity.** Phase 2's finding
   says value was left on the table inside the represented action universe.
   Only Phase 3 addresses whether a decision-time-realizable policy could have
   taken it.

## 6. The result stated at full precision

**`V_R` remains negative on every one of the 11 recoverable slices.** Example:
`failed_breakout|XRPUSDT|SHORT` — `V_A` = -0.387R, `V_R` = -0.062R,
`G_R` = +0.325R CI[0.179, 0.468].

This is a replicated **loss-reduction** effect from a decision-time-selectable
subset of Candidates. It is not a profitability finding: no slice's gated
policy clears zero. Rule 12's block on any profitability or
validated-execution claim is untouched, and nothing in this protocol may be
cited as evidence of edge.

## 7. Dual implementation and parity

The protocol requires a slow, transparent reference alongside the optimized
evaluator, with semantic parity as the acceptance condition.
`tools/regret_reference.py` is that reference: written from
`SIMULATION_TRUTH_SPEC` text, importing nothing from `v8.simulator`, and agreed
with the canonical simulator on 150 randomized paths.

In V8.2 this requirement composes with the runtime migration: the Python
evaluator becomes the oracle for the native `CubeReducer`, under the same
value-level parity gate as every other stage
(`PARITY_AND_IDENTITY_SPEC` §5). The reference walk's randomized-path generator
is reused there rather than rewritten.

## 8. Cheap executable tests

1. Reconciliation is exact at 1e-12 on every executed Candidate, or the run is
   refused.
2. PIT lineage violations = 0.
3. `gap(C) >= 0` on every COMPUTED Candidate.
4. The confirmation half is queried exactly once per declared slice; a second
   query is a hard error, not a warning.
5. Fault injection: TP-shortened axis attribution, cost-doubling isolation,
   direction-flip structural illegality, habitat-randomization structural
   non-claim, and missing-evidence explicit refusal each behave as specified.
6. The reference walk and the canonical simulator agree on randomized paths.
7. The evaluator's Candidate count equals the store's; an evaluator that
   produced a Candidate would fail this.

## 9. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** every result in §4 is real command output
  recorded under D-071 .. D-074, with the ACCP evidence chain
  RIR-V8RR-001 → FER-V8RR-002 → FDR-V8RR-003 → FCR-V8RR-004 and the phase
  contracts FCR-V8RR-007 / FCR-V8RR-009.
- **DESIGN_INFERENCE:** the invariant table in §2 and the architectural
  position in §1 are a written statement of properties the implementation
  already has; they add no new commitment.
- **Not claimed:** profitability, edge, validated execution, or any
  interpretation of `G_R` as realizable return. The population boundary also
  holds: this instrument's Candidate population and the diagnostic engine's are
  **not** interchangeable.
