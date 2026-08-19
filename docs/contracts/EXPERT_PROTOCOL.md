# V8 Expert and Routing Protocol v0.1

**Status:** PROVISIONAL_DECISION. This is a research contract, not evidence of an edge.

## 1. Scope and invariant

An `Expert` is one versioned, falsifiable executable hypothesis about one behavior
family. It consumes a point-in-time `MarketState` and may emit zero or more
`CandidateEpisode` transitions. It never submits an order, allocates capital, or
rewrites another Expert's definition.

`MarketState S_t` contains only data with `availability_time <= decision_time t`.
The decision clock, source manifest, feature code hash, Expert version, and
canonical execution version are attached to every evaluation.

The terms below are distinct:

| Term | Meaning | May decide an order? |
|---|---|---|
| Behavior | Observable conditional pattern, not a causal explanation | No |
| Habitat | State region where the behavior is considered applicable | No |
| Setup | Preconditions that create a testable thesis | No |
| Trigger | Observable condition that makes a pending thesis executable | No |
| Invalidation | Evidence that terminates the thesis | No |
| Expiry | Time/event bound after which the thesis is stale | No |
| Risk geometry | Predeclared entry, stop, target, timeout and sizing inputs | No |
| Candidate | Identified lifecycle-bearing hypothesis | No |
| Order | Canonical execution instruction for an accepted candidate | Yes, executor only |
| Outcome | Versioned counterfactual or realized result | No |

### Ontology levels and identity

Every artifact in the research hierarchy is one of five levels; only the
Expert and the Candidate produce records directly.

| Level | Identity | Produces | Example |
|---|---|---|---|
| Strategy class | `strategy_class_id` | nothing (framing only) | mean reversion |
| Mechanism family | `mechanism_family_id` | nothing (causal claim) | forced liquidation / liquidity vacuum |
| Behavior family | `behavior_family_id` | nothing (observable pattern) | capitulation flush + reclaim |
| Expert hypothesis | `expert_id` + `expert_version` | Candidate | `liquidation_reclaim_v1` |
| Candidate episode | `candidate_id` | transitions/outcomes | BTCUSDT 2026-07-20 LONG |

Each Expert carries `mechanism_family_id`, `behavior_family_id`, `expert_id`,
`expert_version`, and `variant_id` where applicable. Parameter, threshold,
lookback, and geometry changes are **variants of the same hypothesis family**,
never separate Experts. Within-family variant exploration is corrected via
White's (2000) Reality Check block-bootstrap max-statistic procedure across
every evaluated variant (D-044 / D-046 / D-107, implemented natively in
`v8-core/src/statistics/reality_check.rs`), spending the family's allocated
`α_f` budget rather than treating multiple variant searches as zero-cost.

The usefulness test for "separate Expert or variant": if two rules can be
falsified independently — different mechanism claim, setup, trigger, or
invalidation logic — they are separate Experts; if only thresholds or geometry
change, they are variants of one Expert.

### Feature-group declaration

Each Expert declares the MarketState feature groups it consumes (`requires`),
e.g. `trend`, `location`, `liquidity`, `flow`, `time`, `cross_market`.
Features outside the declared groups must not influence its evaluation; the
declared set is part of the frozen specification and is audited against actual
consumption, so the habitat definition and the feature usage cannot drift
apart.

## 2. Minimum interface

```text
evaluate(expert_version, state_snapshot, active_candidates) -> [ExpertEvaluation]
ExpertEvaluation = NOT_APPLICABLE | EVIDENCE | CandidateTransition
```

Each evaluation persists applicability reasons, input snapshot/content hashes,
ordered evidence items, near-miss reasons, candidate identity, and elapsed compute.
`None` is not an auditable result and is forbidden in stored research output.
Experts may be stateful only through append-only candidate history; hidden mutable
state is forbidden. One Expert may maintain multiple candidates, provided their
identity is deterministic. The normative identity is `episode_key`, defined once
in `CANDIDATE_LIFECYCLE_SPEC` section 1 and anchored to `setup_anchor_event_id`
(D-026); this protocol does not restate the formula, so the two contracts cannot
drift apart again. Each Expert declares the `setup_anchor_event_id` its behavior
family uses and its deduplication window. Reopening a terminal candidate is
forbidden; apparent reactivation creates a successor with `parent_candidate_id`.

## 3. Routing comparison and baseline

The locked initial baseline is **full self-gating**: invoke every inexpensive
Expert on each decision event. It is the attribution reference for all routers.

| Architecture | Status | Condition |
|---|---|---|
| A: full self-gating | BASELINE | Required first comparison |
| B: deterministic pre-router | PROVISIONAL | Admit only if it preserves valuable-candidate recall and reduces a binding cost/latency constraint |
| C: learned router | DEFERRED | Must not use future-derived labels; must beat B and A on frozen OOS |
| D: hierarchical router | DEFERRED | Same evidence standard, plus stable hierarchy attribution |
| E: hybrid | DEFERRED | Compare directly against A, not only C/D |

“Valuable candidate” means a candidate whose **pre-registered canonical,
out-of-sample** outcome clears the comparison threshold; it must not mean a
hindsight-selected favorable path. Router measurements: valuable-candidate recall,
false exclusion, total CPU/latency, utilization, overlap/duplicate rate, stability
across time/assets, and paired net-economic effect. Compute savings alone cannot
admit a router unless self-gating violates a declared operational budget.

## 4. Expert admission and retirement

An Expert is admitted to the registry only with: a mechanism hypothesis; frozen
specification; ownership/version; full-lifecycle data; deterministic baseline;
costed canonical simulation; chronological OOF plus untouched OOS plan; and
explicit reject condition. It is promoted only after replication; `PASS` means
the stated gate passed, never universal validity. Retire/quarantine on data or
contract breach, unavailable inputs, drift beyond pre-registered limits, or failed
replication. Parameter variants are not separate Experts.

## 5. Evidence and sources

* **PROJECT_EVIDENCE_SUPPORTED:** V7 audit requires runnable vertical slices,
  canonical authority and full lifecycle coverage; current economic certification
  is `FAIL` and blocks profitability claims (`PROJECT_EVIDENCE_AUDIT.md`).
* **LITERATURE_SUPPORTED:** sparse MoE gates can starve/load-imbalance experts,
  hence routing needs measured utilization and recall, not aesthetic justification
  ([Shazeer et al., 2017](https://arxiv.org/abs/1701.06538)). This does not show
  an MoE is useful for trading.
* **DESIGN_INFERENCE:** self-gating is the smallest auditable baseline because it
  does not introduce a second false-negative decision point.
