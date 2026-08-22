# V8 Constitution v0.3 — Evidence Constitution v2 (Ratified under CC-BILL-V8.3-AUTHORITY-003 & CC-AMEND-V8.3-KAIZEN-004)

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
28. **3-Dimensional Authority Tensor:** Authority is not a 1-dimensional scalar
    ladder. It is defined across three orthogonal dimensions:
    $$\text{Authority} = (\text{EvidenceAuthority}, \text{DecisionAuthority}, \text{RealizationStatus})$$
    where:
    - $\text{EvidenceAuthority} \in \{\text{Counterfactual}, \text{ModelDerived}, \text{Observed}\}$
    - $\text{DecisionAuthority} \in \{\text{DiagnosticOnly}, \text{Reconciled}, \text{UtilityEligible}, \text{PortfolioAuthorized}, \text{ExecutionAuthorized}\}$
    - $\text{RealizationStatus} \in \{\text{Hypothetical}, \text{Simulated}, \text{Filled}, \text{CashflowSettled}\}$
    A high decision authority grant (e.g. `PortfolioAuthorized`) never promotes epistemic evidence or realization status into reality.
29. **No Naked Economic Claims:** Internal calculations may use `f64`, but no economic
    or statistical value may cross a module boundary, enter a report, or influence a
    decision without typed authority wrapping:
    $$\text{ClaimValue}\langle T \rangle = \{ \text{value}: T, \text{authority}: \text{Authority}, \text{receipt\_id}: \text{ReceiptId} \}$$
    Every economic claim requires an immutable cryptographic receipt.
30. **Closed Algebra of 6 Statutory Claim Classes:** Systems, agents, and reports are
    strictly restricted to 6 statutory claim classes: `DIAGNOSTIC_SIGNAL`,
    `COUNTERFACTUAL_POTENTIAL`, `RECOVERABLE_REGRET`, `SIMULATED_CASHFLOW`,
    `REALIZED_CASHFLOW`, and `SUPPORTED_EDGE`. Every claim is registered in the
    central `ClaimRegistry`. Transitioning `COUNTERFACTUAL_POTENTIAL` to `REALIZED_CASHFLOW`
    is legally and architecturally impossible.
31. **Renderer Firewall:** Visualizers, dashboard renderers, HTML generators, and CLI
    output formatters are prohibited from arbitrary string formatting. All titles,
    labels, and metric qualifiers must be derived directly from the certified `ClaimValue`
    type. Unauthorized use of words such as `realized`, `profit`, `alpha`, or `cashflow`
    fails compilation and CI verification.
32. **Constitutional Adversarial Audit & Audit-of-Audit:** The constitutional duty of the
    independent auditor is not to approve, but to actively falsify claims (`FALSIFY CLAIM`).
    Economic authorization requires three distinct signatures:
    $$\text{Implementation Receipt} + \text{Independent Adversarial Audit Receipt} + \text{Verdict Receipt} \implies \text{Authorized Claim}$$
    The audit system itself is continuously subjected to mandatory automated sabotage tests
    (tampered hashes, simulated leakage, clone inflation, missing ledgers).
33. **Sovereign Kaizen Controller:** `KaizenController` is the single sovereign research,
    experiment, and verdict authority. Subsystems, expert grammars, and simulators emit
    only passive observation telemetry; only `KaizenVerdictEngine` may issue normative verdicts.
34. **Execution Physics Instrument Status:** The USD-M engine and venue simulators possess
    zero autonomous decision authority; they operate strictly as passive laboratory
    instruments (`ExecutionBackend`) providing venue execution physics (fees, funding,
    margin, tick/step quantization, and slippage).
35. **Constitutional Reachability & Forbidden Legacy Import:** All call-graph paths leading
    to an economic claim must traverse Kaizen (`SHADOW_AUTHORITY_PATH` is a P0 failure).
    Importing frozen legacy candidate/Python code paths in production is strictly prohibited
    and enforced by compile-time assertions (`FORBIDDEN_LEGACY_IMPORT`).
36. **Four-Plane Separation of Powers:** V8 governance operates across 4 strictly separated planes:
    $$\text{Constitution} \implies \text{Central Committee / Judiciary} \implies \text{Kaizen (Sole Execution Engine)} \implies \text{Implementer / Agents} \implies \text{Double-Entry Ledger}$$
    The Central Committee decides policy; Judiciary reviews & falsifies; Kaizen orchestrates; Agents implement; Ledger certifies truth.
37. **Execution Oversight Corps:** Independent Procedural and Technical Commissioners monitor execution runs under strict capability limits: `READ`, `TRACE`, `TEST`, `REPLAY`, `CHALLENGE`, `BLOCK` are permitted; `WRITE PROD CODE`, `MERGE`, and `DECLARE SUCCESS` are strictly forbidden.
38. **Anti-Clone & Epistemic Diversity Mandate (Amendment A1):** To prevent correlated agent consensus ($N_{\text{eff}} \approx 2$ despite $N=9$), auditors are completely blinded from the implementer's Chain-of-Thought reasoning (`Blind Protocol`). Homogeneous agent consensus carries zero evidentiary value.
39. **No Naked Veto & Expedited Appeal (Amendment A2):** Arbitrary or unevidenced vetoes are prohibited (`No Naked Veto`). Every block decision must produce a reproducible, panic-inducing Rust unit test (`#[test]`) or receipt violation proof. An expedited 1-turn Judicial Panel appeal is guaranteed against unjust blocks.
40. **Risk-Weighted Mobilization & Token Budget Firewall (Amendment A3):** Oversight is mobilized in 3 tiers:
    - *Tier 0 (Routine):* Primary Implementer + Automated CI tests.
    - *Tier 1 (Material):* Primary Implementer + 1 Execution Commissioner + Automated Audit.
    - *Tier 2 (Constitutional / Economic):* Full Assembly (5 Committee Agents + Primary Implementer + 2 Execution Commissioners + Red-Team + Verdict Authority).
    Every run produces an immutable Token Budget & Governance Efficiency receipt.
41. **Cryptographic Constitution Pinning & Kaizen Self-Audit Ban (Amendment A4):** Every execution mandate pins the immutable `constitution_tree_hash` at checkout. Kaizen possesses zero authority to audit its own orchestration; it is subject to external constitutional judicial review.
42. **Mandatory 6-Section Red-Team Adversarial Charter:** The Red-Team is an adversarial falsification antibody, not a consensus rubber-stamp. Every audit must structure findings into: (1) Strongest Case For, (2) Strongest Case Against, (3) Top 3 Catastrophic Failures, (4) Top 3 Subtle Failures, (5) Executable Falsification Tests, and (6) Dissenting Opinion / Vote.

## Minimum Coherent Architecture (Authority DAG)

```text
                      CONSTITUTION
                           │
          ┌────────────────┴────────────────┐
          │                                 │
  5 PERSISTENT                        JUDICIARY
 COMMITTEE AGENTS                       │
          │                     ┌────────┴────────┐
          │                     │                 │
          │               EXECUTION         INDEPENDENT
          │              COMMISSIONERS        RED TEAM
          │
          ▼
    DECISION REGISTER
          ↓
        KAIZEN (Sovereign Orchestration)
          ↓
    EXECUTION MANDATE (Constitution Tree Pinned)
          ↓
 PRIMARY IMPLEMENTER (Blind Oversight Monitored)
          ↓
   WORKER AGENTS
          ↓
  BLAKE3 RECEIPTS + CLAIM REGISTRY
          ↓
 DOUBLE-ENTRY CASHFLOW LEDGER (Conservation Invariant Verified)
          ↓
  KAIZEN VERDICT ENGINE (Tri-Signed: Impl + Audit + Verdict)
```

Anything beyond this diagram requires the applicable registry experiment to pass.

