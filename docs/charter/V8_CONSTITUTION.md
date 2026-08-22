# V8 Constitution v0.2 (Ratified under CC-PROP-V8.3-GL-001 / CC-RES-V8.3-GL-001)

1. V8 is a falsification program, not a promise of edge.
2. A claim is labeled `LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`,
   `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`,
   `OPEN_QUESTION`, or `REJECTED_OPTION`; labels are never interchangeable.
3. MarketState may contain only information observable by decision time. Event,
   knowledge, availability and decision time are distinct fields.
4. **Economic Object Separation:** `MarketState`, `EconomicExposureStructure`,
   `OpportunityEpisode`, `ObserverEvidence`, `ReconciledOpportunityState`,
   `ExecutionCampaign`, `Order / Fill / Position`, and `Outcome` are distinct,
   immutable records. None may be used as a proxy for another. All terminal
   states—including expiry, invalidation, abstention, and rejection—are retained.
5. Every added component must beat its immediately simpler deterministic baseline
   on a preregistered, costed, frozen out-of-sample comparison.
6. **Minimum Coherent Architecture:**
   $$\text{PIT MarketState} \rightarrow \text{Opportunity Grammar} \rightarrow \text{Canonical Opportunity Book} \leftarrow \text{Expert Stances} \rightarrow \text{Evidence Reconciliation} \rightarrow \text{Selective Utility} \rightarrow \text{Portfolio Feasibility} \rightarrow \text{Execution Campaign} \rightarrow \text{Orders/Fills/Ledger}$$
   Router, learned scorer, global ranker, and uncertified RL execution are absent by default.
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
13. **Observer Constitution:** An Expert is a versioned epistemic observer, not an
    economic sovereign. Experts possess epistemic authority to observe, support,
    contradict, abstain, and report uncertainty; they possess ZERO authority to
    create economic opportunity identity, allocate capital, create positions, or
    compel execution. Every Expert carries `mechanism_family_id`, `behavior_family_id`,
    `expert_id`, `expert_version`, and `variant_id`.
14. **Complexity & Multiplicity Budget:** (a) **Runtime:** The number of active
    observers is unbounded; compute and determinism are the only bounds. Increasing
    observer count must not mechanically increase opportunity count, portfolio heat,
    trade count, or capital entitlement. (b) **Evidence:** The number of behavior
    families simultaneously claiming edge on frozen OOS enters family-level
    multiplicity correction (Rule 11). Shared scorers and cross-expert rankers
    are strictly absent.
15. Learning is offline and registry-gated. Outcome data never mutates an
    active Expert's definition; it may only produce challenger versions that
    must pass a frozen-OOS comparison and registry review before promotion.
16. **Exposure-Structure Risk Admission:** Portfolio constraints operate on
    `ExposureStructure` definitions, not raw symbol strings or Expert identities.
    Conflicting stances are resolved or rejected with counterfactual tracking.
    Together with the factor covariance heat cap, this bounds portfolio scale.
17. Research materializations are compiled once from the tape and reused;
    training reads materialized views, never raw tape, and recompiles when
    `OpportunityGrammar`, `ExposureMapping`, `ExpertHabitat`, feature, simulator,
    or reconciliation definitions change.
18. **Opportunity Sovereignty:** Economic opportunity identity is established
    independently of the Expert observing it. An observation cannot create
    additional economic reality merely through producer, symbol, strategy, or
    observer multiplicity.
19. **Identity Constitution:**
    $$\text{Symbol} \neq \text{Instrument} \neq \text{EconomicExposure} \neq \text{Opportunity} \neq \text{Trade}$$
20. **Observer Multiplicity Invariance:** Adding exact or collinear copies of an
    observer ($E, E_{\text{clone1}}, \dots$) or duplicated market feeds yields
    zero marginal epistemic evidence and strictly leaves opportunity identity,
    trade count, and portfolio risk invariant ($N_{\text{eff}} = 1.0$).
21. **Habitat & First-Class Abstention:** An Expert operates within a preregistered
    habitat. Outside its habitat or under high epistemic uncertainty, the default
    action is `ABSTAIN` / `NO_TRADE`. Silence is an active, unpenalized epistemic state.
22. **Correlated Witnesses & Evidence Lineage:** Every evidence stance carries
    explicit lineage (`observer_id`, `evidence_family_id`, `feature_lineage`,
    `data_lineage`, `habitat_version`, `dependency_group`). Raw vote counting is
    forbidden; evidence aggregation must discount cross-witness dependence.
23. **Falsifiable Opportunity Grammar:** `CanonicalOpportunity` is an operational,
    versioned, falsifiable measurement coordinate system, not metaphysical ground
    truth. When boundary identity is ambiguous, `UNKNOWN` is an authoritative state.
    Forced merging or splitting is prohibited.
24. **Opportunity $\neq$ Trade (After-Cost Net Economic Value):** A verified market
    opportunity is admitted to execution only if expected gross edge exceeds all
    frictions (spread, fees, funding, slippage markouts, and uncertainty buffer):
    $$\mathbb{E}[\Delta \text{PnL}_{\text{net}}] = \text{GrossEdge} - \text{Friction} - \text{UncertaintyPenalty} > 0$$
    Sub-friction setups default strictly to `NO_TRADE`.
25. **Universe Expansion Invariance:** Adding symbols, venues, instruments, or
    observers expands the search and evidence space; it does NOT mechanically expand
    portfolio leverage, trade frequency, or aggregate risk.
26. **False-Collapse Protection:** Multi-leg geometries, spot-perpetual basis,
    calendar spreads, and cross-venue dislocations with distinct payoff structures
    must preserve their distinct leg-level identities in `ExposureStructure` and
    must not be collapsed into naive single-underlying directional bets.
27. **Constitutional Falsifiability:** The V8.3 architecture is bound by mandatory
    Invariant Tests (T1–T12) and Economic Gates (G0–G5). Failure of any invariant
    represents an immediate architectural defeat, strictly prohibiting heuristic
    tolerance relaxation or test-tweaking.

## Minimum Coherent Architecture

```text
versioned point-in-time tape/state
  -> Economic Exposure / Opportunity Grammar
  -> Canonical Opportunity Book
     ├── Expert A -> Stance (Support)
     ├── Expert B -> Stance (Support)
     ├── Expert C -> Stance (Abstain)
     └── Expert D -> Stance (Contradict)
  -> Evidence Reconciliation (Dependence & Covariance Discounted)
  -> Reconciled Opportunity State
  -> Selective Utility Decision (TRADE / NO_TRADE / DEFER)
  -> Portfolio Feasibility & Factor Covariance Budget
  -> Execution Campaign (Multi-Leg & Basis Protected)
  -> Canonical Orders / Fills / Positions / Ledger
  -> Preregistered Hypothesis Lab & Counterfactual Regret Cube
```

Anything beyond this diagram requires the applicable registry experiment to pass.
