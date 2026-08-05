# V8 Constitution v0.1

1. V8 is a falsification program, not a promise of edge.
2. A claim is labeled `LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`,
   `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`,
   `OPEN_QUESTION`, or `REJECTED_OPTION`; labels are never interchangeable.
3. MarketState may contain only information observable by decision time. Event,
   knowledge, availability and decision time are distinct fields.
4. Candidate, order and outcome are distinct immutable records. All terminal
   candidate states—including expiry, invalidation and rejection—are retained.
5. Every added component must beat its immediately simpler deterministic baseline
   on a preregistered, costed, frozen out-of-sample comparison.
6. The starting architecture is: point-in-time state → all cheap self-gating
   deterministic Experts → append-only candidate log → deterministic acceptance
   rules → one canonical execution/ledger. Router, learned scorer, ranker and RL
   execution are absent by default.
7. Canonical execution is an attribution control, not proof that alpha and
   execution are statistically independent.
8. The simulation level must match the claim. Unsupported fill, queue, latency,
   or data-quality assumptions fail closed.
9. Outputs bind source, universe, code, configuration, seed, simulator and ledger
   hashes. A missing authority receipt blocks an economic verdict.
10. Screening, replication, promotion, shadow and live monitoring have separate
    statuses. Synthetic tests prove contracts, not economics.
11. Explore broadly in development; report the full search family; use multiplicity
    controls and an untouched chronological evaluation. Never repair a rejected
    hypothesis on frozen OOS.
12. V7's current simulation authority is not certified. Until independently
    renewed, V8 may create contracts and verification artifacts but may not claim
    profitability, validated execution, or a promoted trading system.
13. Ontology: each Candidate has exactly one originating Expert; a single
    decision event may yield Candidates from multiple Experts. An Expert is one
    falsifiable executable hypothesis inside one behavior family; parameter and
    geometry changes are variants of that hypothesis family, not separate
    Experts. Every Expert carries `mechanism_family_id`, `behavior_family_id`,
    `expert_id`, `expert_version`, and `variant_id` where applicable.
14. Complexity budget is defined on two separate axes, never collapsed into
    one number. (a) **Runtime:** the number of active Experts is unbounded;
    the only limits are determinism and the compute budget. Expert count is
    not a validity constraint. (b) **Evidence:** the number of behavior
    families simultaneously carrying a claim on one frozen-OOS evaluation is
    preregistered and enters the family-level multiplicity correction of
    rule 11. At most one learned component per pipeline position. Router,
    shared scorer, ranker, RL execution, and online learning are absent.
15. Learning is offline and registry-gated. Outcome data never mutates an
    active Expert's definition; it may only produce challenger versions that
    must pass a frozen-OOS comparison and registry review before promotion.
16. Risk admission is deterministic and exposure-aware. The baseline holds one
    active exposure per (instrument, direction); a conflicting Candidate is
    rejected (`CAPACITY_REJECTED` / `EXISTING_EXPOSURE_CONFLICT`) and is still
    measured counterfactually. This is an **attribution default**, not a risk
    ceiling: it keeps realized PnL attributable to a single Expert. Together
    with the portfolio heat cap it — never the Expert count of rule 14 — is
    what bounds portfolio scale. Relaxing either is a registry decision
    (O-012, O-018), never a configuration change.
17. Research materializations are compiled once from the tape and reused;
    training reads materialized views, never raw tape, and recompiles only
    when feature, Expert, simulator, or outcome definitions change.

## Minimum coherent architecture

```text
versioned point-in-time tape/state
  -> deterministic self-gating Experts (N, unbounded)
  -> candidate event store (all outcomes)
  -> deterministic acceptance + risk cap
  -> canonical Level-1 simulator / single ledger
  -> preregistered hypothesis lab
```

Anything beyond this diagram requires the applicable registry experiment to pass.
