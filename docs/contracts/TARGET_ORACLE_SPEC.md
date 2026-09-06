# Target V8 Oracle Specification v1.0

**Normative reference for the economic target, opportunity universe, counterfactual authority, regret semantics, and implementation admission of V8.**

**Date:** 2026-08-19 · **Scope:** V8 / V8.2 research and implementation program · **Language:** normative English to match the existing V8 monograph and code contracts.

## Document status and reading rule

**Status: NORMATIVE REFERENCE / IMPLEMENTATION-READY / ECONOMICALLY UNVALIDATED.**
This specification is intended to be stable enough to bind implementation. It does *not* claim that V8 is profitable, that any Target Oracle has been learned, that any Hindsight Oracle output is realizable, or that any execution model above its declared authority is validated. Changes to locked definitions require an explicit version bump or registry decision.

This document inherits the V8 evidence vocabulary:
`LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`, `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`, `OPEN_QUESTION`, `REJECTED_OPTION`.
The labels describe evidentiary status; they are not interchangeable with runtime status.

**Source basis.** This specification consolidates two project sources: the existing *V8 Final Research Monograph* and *Target V8 Oracle Research Audit v0.1*. The monograph supplies the existing PIT, Candidate, replay, evidence, and promotion invariants. The audit supplies the P0 objective, opportunity-universe, identifiability, regret-decomposition, non-stationarity, execution-authority, and abstention findings.

## Abstract

V8 requires a target that is stricter than “maximize backtest PnL” and more useful than a perfect-hindsight trader. This specification defines that target through exactly three top-level Oracle roles. `PARITY_ORACLE` is an engineering reference for semantic equivalence. `HINDSIGHT_ORACLE` is a bounded counterfactual measurement operator that may inspect realized outcomes but cannot by itself establish selectable edge. `TARGET_ORACLE` is the decision-time-realizable policy family V8 attempts to approach under a versioned objective, opportunity universe, cost model, capacity model, information boundary, and authority contract.

The central design principle is that economic optimality is conditional. There is no context-free “best trader.” A Target Oracle is only defined relative to a feasible policy class and a declared `UtilityContract`. Opportunity existence is likewise conditional: a missed opportunity must be PIT-legal, schema-legal, tradable under the declared environment, and supported strongly enough to justify the requested counterfactual claim. Unsupported profitable hindsight paths are not opportunities; they are model-derived or unknown.

The specification therefore separates opportunity generation from Expert coverage, economic value from counterfactual identifiability, retrospective value from prospective/live value, and component regret from total policy gap. Detection, representation, selection, geometry, execution, and allocation are decision domains inside the Hindsight/Target systems, not additional Oracle classes. L1/L2/L3 and `LIVE_RECEIPT` are evidentiary authority levels, not new Oracles.

## Executive design summary

```text
                           V8 ORACLE TAXONOMY

  PARITY_ORACLE                  HINDSIGHT_ORACLE
  engineering reference         measurement ceiling
        │                              │
        │                              ├─ L1 / L2 / L3 authority
        │                              ├─ counterfactual status
        │                              └─ no realizability claim by itself
        │
        └──────────── engineering trust only ────────────┐
                                                         │
                                                         ▼
                                               TARGET_ORACLE
                                      decision-time realizable policy family
                                                         │
                         ┌───────────────────────────────┼──────────────────────────────┐
                         ▼               ▼               ▼              ▼              ▼
                      detection      representation    selection      execution     allocation
                                                         │
                                                         ▼
                                                   LIVE_RECEIPT
                                             real-world economic receipt
```

**Locked naming rule.** V8 recognizes exactly three top-level Oracle roles: `PARITY_ORACLE`, `HINDSIGHT_ORACLE`, and `TARGET_ORACLE`. Terms such as “Detection Oracle,” “Execution Oracle,” “Profit Oracle,” “Perfect Oracle,” or “Market Oracle” must not introduce new top-level classes. Detection, selection, execution, allocation, and similar labels name decision domains. L1–L3 name authority levels. `LIVE_RECEIPT` is evidence from reality, not an Oracle.

---

## 1. Oracle Constitution

The following rules constrain meaning, not merely implementation. A change that violates one of these rules changes what the Oracle system *is* and requires a specification version bump or an explicit replacement decision.

1. **Exactly three top-level Oracles.** `PARITY_ORACLE`, `HINDSIGHT_ORACLE`, and `TARGET_ORACLE` are the complete top-level taxonomy.
2. **No promise of edge.** An Oracle specification is a measurement and target contract, not a profitability claim.
3. **No universal best trader.** Target optimality is always conditional on a versioned objective, constraints, costs, capacity assumptions, information set, opportunity universe, and policy class.
4. **Future information is evaluator-only.** Realized future information may be used by Hindsight evaluation but must never enter a decision-time feature of Target policies.
5. **Hindsight opportunity is not recoverable opportunity.** Hindsight value is a measurement ceiling, not evidence that a policy could have selected the better action ex ante.
6. **Opportunity existence is not defined by realized profit alone.** A profitable path discovered after the outcome is not automatically a missed opportunity.
7. **Opportunity Universe is Expert-independent.** Experts cover subsets of the environment-level Candidate grammar; they do not define the universe against which coverage is measured.
8. **The Opportunity Universe is finite, versioned, and preregistered for each evaluation family.** Expanding grammar, grids, instruments, timeframes, or execution modes creates a new universe version and a new trial lineage.
9. **Candidate is not action.** Candidate identity, order identity, and realized outcome remain distinct. Direction changes that alter the proposal create a new Candidate, not a counterfactual action on the old Candidate.
10. **Candidate birth is immutable.** Setup, trigger, direction, invalidation, expiry, and declared risk geometry are frozen at Candidate birth for a given version.
11. **Counterfactual authority is explicit.** Every counterfactual is labeled `IDENTIFIED`, `PARTIALLY_IDENTIFIED`, `MODEL_DERIVED`, or `NOT_IDENTIFIABLE`.
12. **Missing support fails closed.** Lack of evidence never becomes a point-valued profitable Oracle outcome.
13. **Simulation level must match claim level.** L1 bar replay cannot support L3 reactive-impact economic claims. A simulator is not upgraded by confidence language.
14. **`LIVE_RECEIPT` outranks simulation.** Realized fills and operational receipts are evidence from the deployed environment, not an Oracle prediction.
15. **NetUtility is primary; hard constraints are lexicographic.** A policy violating a hard drawdown, tail-risk, capacity, heat, or coverage constraint cannot be called a better Target Oracle merely because its scalar return is higher.
16. **Utility weights are versioned.** When a scalar sub-objective or penalty is used, its weights and sensitivity band are part of the artifact identity.
17. **Abstention is not free performance.** Lower trade count is not improvement unless utility, risk, and minimum-coverage requirements jointly pass.
18. **Regret is not naively additive.** Detection, representation, selection, geometry, execution, and allocation effects may interact. Component attributions require an explicit baseline and decomposition rule.
19. **Frozen OOS is necessary but not sufficient.** Historical replication, prospective/shadow evaluation, and live realized value are distinct objects.
20. **Complexity is never its own admission argument.** Learned or richer components must beat the immediately simpler admissible baseline on a preregistered, costed comparison.
21. **UNKNOWN is a valid result.** The system must prefer an explicit unknown to an unjustified numeric answer.
22. **All economic artifacts are authority-bound.** Source, universe, code, configuration, cost model, capacity model, simulator, policy, seed where relevant, and ledger hashes are part of the claim identity.

---

## 2. Terminology and taxonomy

### 2.1 PARITY_ORACLE
`PARITY_ORACLE` is an engineering reference implementation or reference calculation used to verify semantic equivalence of another implementation. Its purpose is correctness, not economic optimization. In current V8.2 history, the frozen Python implementation served this role during the Rust migration.

### 2.2 HINDSIGHT_ORACLE
`HINDSIGHT_ORACLE` is a bounded counterfactual measurement operator. It may inspect realized future outcomes after the fact, but only inside a declared Opportunity Universe, Action Universe, execution model, and authority level. It estimates what value was available under those declared assumptions. It is not deployable and does not imply selectability.

### 2.3 TARGET_ORACLE
`TARGET_ORACLE` is the family of decision-time-realizable policies that V8 attempts to approximate. It is indexed by the economic and epistemic contracts that define the task:

```text
TARGET_ORACLE(
    UtilityContract,
    OpportunityUniverseVersion,
    InformationContract,
    CostModel,
    CapacityModel,
    AuthorityContract,
    PolicyClass,
    EnvironmentTarget
)
```

Different contracts may yield different Target Oracles. The phrase “best policy” is therefore shorthand for “best policy in the declared feasible family under this contract.”

### 2.4 Decision domains are not Oracles

| Domain | Question | Oracle identity |
|---|---|---|
| Detection | Which PIT-legal opportunities are represented at all? | Subproblem inside Hindsight/Target |
| Representation | Was the opportunity encoded as the right Candidate proposal? | Subproblem inside Hindsight/Target |
| Selection | TRADE, NO_TRADE, or defer? | Subproblem inside Hindsight/Target |
| Geometry | Which legal entry/stop/target/expiry geometry? | Subproblem inside Hindsight/Target |
| Execution | How is the decision submitted and filled? | Subproblem inside Hindsight/Target |
| Allocation | How is scarce capital/risk distributed across simultaneous Candidates? | Subproblem inside Hindsight/Target |

### 2.5 Authority levels are not Oracles

| Authority | Meaning | Typical limit |
|---|---|---|
| `ORACLE_L1` | Bar/tape replay with static or canonical fills | No queue, endogenous impact, or unobserved microstructure claim |
| `ORACLE_L2` | Spread/slippage/liquidity-aware evaluation with supported cost/fill mechanics | Still not a full reactive market |
| `ORACLE_L3` | Validated reactive simulator with endogenous impact/liquidity response | Still model-derived; below live receipts |
| `LIVE_RECEIPT` | Realized execution and PnL receipts from the target venue/environment | Historical realized evidence, not a counterfactual upper bound |

### 2.6 Value notions

| Value notion | Definition |
|---|---|
| `RETROSPECTIVE_VALUE` | Value measured in the historical environment, including diagnostic hindsight where explicitly allowed. |
| `REPLICATION_VALUE` | Frozen policy replay on untouched historical chronology under a fixed execution contract. |
| `PROSPECTIVE_SHADOW_VALUE` | Forward or shadow estimate/receipt before capital-bearing deployment; assumptions about drift must be declared. |
| `LIVE_REALIZED_VALUE` | Realized after-cost value from actual deployed decisions and fills. |

---

## 3. Formal problem definition

At decision time `t`, let `I_t` be the allowed information set. Let `U_v(t)` be the Candidate Opportunity Universe under universe version `v`. Let `S_a(t)` be the supported counterfactual set under authority contract `a`. Let `P` be a declared policy class and `C` a UtilityContract.

The evaluable universe is:
```text
U_eval(t; v, a) = U_v(t) ∩ S_a(t)
```

The feasible policy family is:
```text
P_feasible(C, v, a) =
{
    π ∈ P :
    π uses only I_t at decision time
    ∧ π emits only schema-legal Candidates/actions
    ∧ π satisfies all hard UtilityContract constraints
    ∧ π stays inside authority-supported action/capacity bounds
}
```

The Target Oracle is not a realized future sequence chosen with hindsight. It is the best admissible policy family under the target environment and the declared objective:

```text
π* ∈ argmax_{π ∈ P_feasible}  Expected[ NetUtility_C(π) ]

subject to the lexicographic hard constraints in C.
```

**Important:** if the target environment distribution is not identified, the specification does not permit pretending the expectation above is known. The corresponding value is bounded, model-derived, prospective, or `UNKNOWN` according to the authority contract.

---

## 4. Information boundary

### 4.1 InformationSet(t)
`InformationSet(t)` contains only information that is both known and available by the decision clock. Event time, knowledge time, availability time, and decision time are distinct. A field observed in historical files but unavailable to the live system at `t` is not a legal decision feature.

```text
InformationField {
    name
    value
    event_time
    knowledge_time
    availability_time
    source_id
    source_version
}

LEGAL_AT(t, field) :=
    field.knowledge_time   ≤ t
    ∧ field.availability_time ≤ t
```

### 4.2 Future-data rule
Future data may enter:
- Hindsight counterfactual outcome measurement;
- offline labels after the decision event;
- post-hoc diagnostics and error attribution.

Future data may not enter:
- Target policy features at the original decision time;
- Candidate birth state;
- threshold selection performed after opening the protected evaluation slice;
- execution assumptions presented as if known ex ante.

### 4.3 Hindsight is a separate plane
The Hindsight evaluator is read-only with respect to the original decision record. It must not rewrite the actual Candidate population in place. When an expanded Opportunity Universe is evaluated, that expanded population belongs to its own explicit universe version and research lineage.

---

## 5. Opportunity universe

### 5.1 Why Candidate logs are insufficient
The existing V8 Outcome Cube measures value left on the table inside the represented Candidate/action universe. That is necessary for action regret, but insufficient for measuring opportunities that no Expert represented. Target V8 therefore requires an Expert-independent Candidate Opportunity Universe.

### 5.2 Three opportunity states

```text
DETECTABLE_CANDIDATE
        ↓ realized, authority-valid outcome
HINDSIGHT_OPPORTUNITY
        ↓ ex-ante selector survives protected evaluation
RECOVERABLE_OPPORTUNITY
```

| State | Meaning | Claim allowed |
|---|---|---|
| `DETECTABLE_CANDIDATE` | A Candidate can be constructed from legal decision-time primitives under the frozen grammar. | Representational coverage only. |
| `HINDSIGHT_OPPORTUNITY` | A detectable Candidate has favorable after-cost value under a legitimate hindsight evaluation. | Retrospective opportunity only. |
| `RECOVERABLE_OPPORTUNITY` | A decision-time policy can select or exploit the opportunity under protected evaluation. | Recoverability claim within the tested policy class. |

### 5.3 Canonical finite Candidate grammar
The Opportunity Universe is not the infinite Cartesian product of every timestamp, feature transform, threshold, leverage, stop, target, holding period, and model. That construction would be hindsight mining, not a stable target.

For universe version `v`:
```text
U_v(t) =
{
    Candidate C = g(I_t, θ)
    |
    g ∈ Grammar_v
    ∧ θ ∈ Θ_g,v
    ∧ PIT_VALID(C)
    ∧ SCHEMA_VALID(C)
    ∧ TRADABLE_FOR_DETECTION(C)
}
```

`Grammar_v` and each parameter grid `Θ_g,v` are finite, versioned, and preregistered before protected evaluation.

### 5.4 Primitive families
Version 1 permits grammar primitives only from explicitly registered MarketState families:

| Primitive family | Examples | Availability rule |
|---|---|---|
| Price / return | returns, displacement, gap, range position | PIT bar/tape values only |
| Volatility / range | realized volatility proxies, ATR-like range state | No future-window confirmation |
| Volume / activity | volume state, activity shock | Feed-resolution declared |
| Liquidity | spread/depth/liquidity state | Only when data exists at decision time |
| Order flow | imbalance/flow-derived state | Feed granularity and availability clock required |
| Funding / basis | funding, basis, derivative state | Venue-specific source and timestamp required |
| Derivatives stress | liquidation/OI-related state | Unavailable channels fail closed |

### 5.5 Predicate grammar
A deterministic baseline grammar may compose registered features with a bounded predicate IR:
```text
ABOVE(x, q)
BELOW(x, q)
CROSS_ABOVE(x, q)
CROSS_BELOW(x, q)
IN_RANGE(x, lo, hi)
RISING(x, n)
FALLING(x, n)
PERSIST(predicate, n)
AND(...)
OR(...)
NOT(...)
SEQUENCE(A → B, max_delay)
```

The exact operators and grids are registry artifacts. A post-outcome concept such as “this was a swing low” is legal only at the time its confirmation became available. The grammar must encode that availability delay rather than silently backdating the information.

### 5.6 Behavior template
```text
CandidateTemplate {
    mechanism_family_id
    behavior_family_id
    habitat_predicate
    setup_predicate
    trigger_predicate
    direction
    invalidation
    expiry
    risk_geometry
}
```

The Opportunity Universe is generated from these templates; Experts are named, falsifiable policies that cover subsets of the grammar. A grammar Candidate need not correspond to a currently shipped Expert.

### 5.7 Support and evaluability
```text
U_opportunity = all PIT-legal Candidates under Grammar_v
U_support     = Candidates/actions supported by the declared data/execution authority
U_eval        = U_opportunity ∩ U_support
```

`U_opportunity \ U_support` is not discarded. It is retained with `NOT_IDENTIFIABLE` or a weaker authority tag. It cannot receive a fabricated point-valued profit.

### 5.8 Coverage, not immediate “detection regret”
The first implementation metric is `RepresentationalCoverageGap`, not a monetary Detection Regret:
```text
coverage =
    | supported hindsight opportunities represented by shipped Experts |
    ---------------------------------------------------------------------
    | supported hindsight opportunities in the frozen Opportunity Universe |
```

A missed hindsight opportunity becomes a *recoverable detection failure* only after a decision-time policy class demonstrates protected, after-cost recoverability. This prevents hindsight coverage from being misreported as deployable money.

---

## 6. Candidate and action universe

### 6.1 Candidate ontology
A Candidate is a proposal born at a decision event. Candidate identity includes its originating grammar/template or Expert, direction, trigger semantics, invalidation, expiry, and declared geometry. Candidate, order, fill, and outcome are distinct immutable records.

### 6.2 Direction semantics
Changing direction creates a new Candidate. A Hindsight action evaluator must not reinterpret a LONG Candidate as SHORT. However, the Opportunity Grammar may independently generate separate LONG and SHORT Candidates from the same environment state when both are legal templates.

### 6.3 Action universe
For a fixed Candidate `C`, the legal action set `A(C)` may include `NO_TRADE`, the actual action, and preregistered legal geometry/execution variants that preserve Candidate identity. Every axis must declare whether varying it preserves identity or creates a new Candidate.

### 6.4 No silent population mutation
An evaluator operating on the actual Candidate store may not create a second Candidate population and still call the output “action regret.” An Opportunity Universe evaluator may create grammar Candidates only under its own versioned universe contract and must report that the population differs from the live/shipped Expert population.

---

## 7. Objective / UtilityContract

### 7.1 Rejected objective
`REJECTED_OPTION`: `maximize raw PnL` as the complete Oracle definition. It ignores drawdown, tail risk, capacity, participation, and the dependence of optimal policy on explicit transaction-cost and preference assumptions.

### 7.2 Primary economic quantity
The primary economic quantity is declared after-cost NetUtility:
```text
NetEconomicValue =
    GrossTradingValue
  - Fees
  - Funding
  - Slippage
  - MarketImpact
  - OtherVersionedExecutionCosts
```

NetEconomicValue is not by itself the complete Target objective.

### 7.3 Lexicographic hard constraints
Version 1 uses a constrained/lexicographic contract: a policy is first required to satisfy hard feasibility constraints, then optimized on the primary objective inside the feasible set.

| Constraint family | Examples | Semantics |
|---|---|---|
| Drawdown | maximum drawdown ceiling, recovery constraints | Hard fail when breached |
| Tail risk | tail loss / expected shortfall style ceiling | Hard fail when breached |
| Capacity / heat | gross exposure, per-cluster heat, venue/instrument capacity | Hard feasible-set boundary |
| Coverage | minimum participation / opportunity coverage where relevant | Prevents trivial abstention |
| Operational | latency, authority, data availability, execution mode | Hard admissibility boundary |

### 7.4 UtilityContract schema
```text
UtilityContract {
    contract_id
    version

    primary_objective
    horizon
    accounting_currency

    fee_model_id
    funding_model_id
    slippage_model_id
    impact_model_id

    hard_constraints {
        drawdown
        tail_risk
        capacity
        portfolio_heat
        coverage
        operational
    }

    optional_scalar_penalties {
        names
        weights
        sensitivity_band
    }

    stress_grid_id
    effective_from
}
```

### 7.5 Sensitivity requirement
If the ranking of policies changes materially under a defensible neighboring range of fees, slippage, impact, risk penalties, or capacity, the report must surface the instability. A winner that exists only at one knife-edge parameter point is not a stable Target claim.

### 7.6 Pareto reporting
Reports should expose the relevant utility/risk/coverage frontier even when promotion uses lexicographic constraints. The frontier is diagnostic; it does not permit selecting a new point after the protected evaluation is opened.

---

## 8. Oracle authority and counterfactual identifiability

### 8.1 Counterfactual status taxonomy

| Status | Meaning | Permitted claim |
|---|---|---|
| `IDENTIFIED` | Counterfactual is supported under the declared data, action, and execution contract strongly enough for the requested point estimate. | Point estimate within the declared model/authority; never “ground truth” without qualification. |
| `PARTIALLY_IDENTIFIED` | Only a defensible interval/bound is supported. | Bound-aware comparison only; ranking prohibited when bounds overlap under the admission rule. |
| `MODEL_DERIVED` | Value depends materially on a simulation/model assumption not identified by the available data. | Diagnostic/model result; no promotion as empirical economic truth. |
| `NOT_IDENTIFIABLE` | Support, data, or environment assumptions are insufficient. | `UNKNOWN`; no numeric opportunity claim. |

### 8.2 “Identified” is contract-relative
`IDENTIFIED` never means metaphysically or market-wide “true.” It means identified *under the declared data/support/execution contract*. An L1 replay can be internally identified and still be too weak to support an L3 or live economic claim.

### 8.3 Authority-status composition
Every Oracle outcome carries both an authority level and an identifiability status:
```text
CounterfactualAuthority {
    oracle_authority_level  // L1, L2, L3, LIVE_RECEIPT
    identifiability_status  // IDENTIFIED, PARTIAL, MODEL_DERIVED, NOT_IDENTIFIABLE
    support_rule_id
    environment_model_id
    assumptions[]
}
```

### 8.4 Ranking rule
Point ranking is allowed only when the comparison rule is justified at the relevant authority. For partial bounds, promotion requires a preregistered bound-aware condition. A convenient default is refusal when intervals overlap in a way that prevents a dominance claim.

### 8.5 No fabricated fills
Queue position, partial fill probability, hidden liquidity, endogenous impact, or market response may not be invented at L1/L2 and then presented as identified. If the needed data or validated model is missing, the evaluator returns a weaker status or `UNKNOWN`.

---

## 9. Hindsight Oracle contract

### 9.1 Purpose
The Hindsight Oracle measures a ceiling inside a declared counterfactual universe. It answers: *given the frozen opportunity/action universe and the declared replay authority, what value was available after outcomes became known?*

### 9.2 Hindsight layers
The same top-level Hindsight Oracle may expose domain-specific measurements:
- coverage / missed representation inside the Opportunity Universe;
- Candidate representation alternatives when identity permits comparison;
- trade vs no-trade selection;
- legal geometry variants;
- execution variants supported by the authority model;
- capital-allocation variants when portfolio interaction is supported.

### 9.3 Existing Outcome Cube compatibility
The existing Candidate-bound legal hindsight gap remains valid as a narrower Hindsight measurement:
```text
gap(C) =
    max{ Replay(C, a, M) : a ∈ A(C), status(C,a)=OK }
    - Replay(C, a_actual, M)
```

This quantity measures value left on the table *inside the represented Candidate/action universe*. It must not be relabeled as Target recoverability.

### 9.4 Hindsight non-claims
The Hindsight Oracle does not establish:
- that the better action was knowable at decision time;
- that the Candidate would have been generated by a realizable detector;
- that a future policy can generalize to the same regime;
- that L1/L2 simulated value survives L3/live execution;
- that a positive hindsight opportunity is economically significant after search/multiplicity controls.

---

## 10. Target Oracle contract

### 10.1 Definition
The Target Oracle is the comparator family for deployable V8 improvement. It may use only decision-time information and must satisfy the frozen UtilityContract, Opportunity Universe, authority boundary, and policy-class constraints.

### 10.2 Target decision domains

| Domain | Target question | Primary failure mode |
|---|---|---|
| Detection | Can the policy represent the relevant PIT-legal opportunities? | Opportunity never enters the Candidate population. |
| Representation | Does the Candidate encode the opportunity with the correct legal semantics? | Wrong direction/template/trigger/invalidation/expiry identity. |
| Selection | Should this Candidate trade, abstain, or defer? | Bad TRADE/NO_TRADE decision. |
| Geometry | Which identity-preserving risk/exit geometry is justified? | Entry/stop/target/expiry mismatch. |
| Execution | How should the accepted decision be submitted and filled? | Cost, slippage, impact, timing loss. |
| Allocation | How should scarce risk/capital be allocated among simultaneous accepted Candidates? | Correlation/capacity/heat misallocation. |

### 10.3 Target Oracle is a family, not a single neural network
No implementation technology is privileged by the definition. A deterministic rule, shallow model, learned router, constrained optimizer, or other policy may approximate a Target subproblem if and only if it passes its admission experiment against the simpler baseline.

### 10.4 Learned components are challengers
Version 1 does not allow a learned detector to define the Opportunity Universe that is then used to certify that same detector. The deterministic grammar is the baseline measurement frame. Learned detectors may challenge Expert coverage or selection on a fixed evaluation universe.

### 10.5 Target output
A Target policy result is not “Oracle achieved.” The correct language is:
- `RECOVERABLE_WITHIN_CLASS` — decision-time policy class improved the declared baseline under the protected test;
- `PROMOTABLE_WITHIN_CONTRACT` — all required statistical, utility, risk, and authority gates passed;
- `SHADOW_SUPPORTED` — prospective/shadow evidence passed;
- `LIVE_SUPPORTED` — live receipts satisfy the predeclared deployment certificate.

---

## 11. Regret taxonomy and attribution

### 11.1 Rejected additive story
`REJECTED_OPTION`:
```text
TotalRegret =
    DetectionRegret
  + RepresentationRegret
  + SelectionRegret
  + GeometryRegret
  + ExecutionRegret
  + AllocationRegret
```
This is not generally valid because changing an upstream component changes downstream populations, feasible actions, costs, impact, and allocation interactions.

### 11.2 Required attribution vocabulary

| Quantity | Definition |
|---|---|
| `ISOLATED_COMPONENT_EFFECT` | Effect of replacing one component while holding the declared downstream/upstream reference configuration fixed. |
| `MARGINAL_COMPONENT_EFFECT` | Incremental effect of adding/replacing a component relative to a specified baseline sequence. |
| `INTERACTION_EFFECT` | Effect attributable to cross-component interactions not assignable uniquely without a decomposition rule. |
| `TOTAL_POLICY_GAP` | Difference between the actual/reference policy and a declared Target comparator policy under the same evaluation contract. |

### 11.3 Domain labels
The following labels may be used for isolated or marginal analyses, with the method stated explicitly:
- detection / representational coverage effect;
- representation effect;
- selection effect;
- geometry effect;
- execution effect;
- allocation effect;
- residual / irreducible-within-class effect.

### 11.4 Percentage attribution rule
A report must not state “X% of loss comes from detection” unless it records:
- the reference and target policies;
- the causal/pipeline decomposition graph;
- the attribution algorithm;
- interaction handling;
- the authority level of each counterfactual;
- the uncertainty of the attribution itself.

### 11.5 Shapley/path attribution is deferred
Version 1 requires isolated and marginal effects first. Shapley-like or path-specific decomposition is permitted only as a registered v1.1+ extension with an explicit structural causal model and compute budget.

---

## 12. Recoverability

### 12.1 Core distinction
```text
Hindsight opportunity
    ≠
Decision-time recoverable opportunity
    ≠
Promotable policy
    ≠
Live-supported policy
```

### 12.2 Existing V8 recoverability semantics
The existing V8 Recoverable Regret design remains the canonical pattern for Candidate-bound recovery:
```text
V_A = mean utility of the actual/reference policy
V_R = mean utility of the best policy selected from the declared decision-time class
G_R = V_R - V_A
```

A positive `G_R` is an improvement claim within the tested class, not automatically a profitability claim. Absolute utility must separately clear the UtilityContract and promotion gates.

### 12.3 Detection recovery
For missed representation, Version 1 uses a two-step procedure:
1. Measure `RepresentationalCoverageGap` on the frozen Opportunity Universe.
2. Test whether a decision-time policy can identify useful parts of the missed set on protected chronology.

Only the second step may support a recoverable detection claim.

### 12.4 Irreducible-within-class
Failure to recover a hindsight gap means only that the declared policy class did not recover it under the declared environment and evaluation. It must not be reported as proof that no realizable policy exists.

---

## 13. Non-stationarity and value notions

### 13.1 Frozen OOS boundary
Chronological frozen OOS remains mandatory for protected historical comparison, but it is not a substitute for prospective evidence. A policy can pass historical replication and fail when the environment distribution changes.

### 13.2 Four value layers

| Layer | What it answers | Economic authority |
|---|---|---|
| Retrospective | What happened / what was available in the recorded past? | Historical only. |
| Replication | Does a frozen policy reproduce value on untouched chronology? | Historical OOS evidence. |
| Prospective / shadow | Does the frozen policy survive forward time without capital-bearing promotion? | Prospective operational evidence. |
| Live realized | Does the deployed system produce acceptable receipts under real fills/costs? | Highest empirical deployment evidence, still time/regime bounded. |

### 13.3 Dynamic Target
V8 may eventually define regime-conditional or slowly varying Target comparator families. Version 1 does not assume a stationary universal Oracle. Any dynamic comparator must be causal: regime assignment and adaptation may use only information available by the corresponding decision time.

### 13.4 Future-policy estimation
Future off-policy or drift-aware estimators may be used as diagnostics or prospective tools, but their structural assumptions must be explicit. They do not replace shadow/live receipts.

---

## 14. Statistical gates

### 14.1 Search lineage
Every change to Opportunity Grammar, Candidate template, policy feature set, threshold family, objective contract, cost model, or execution model that can alter economic selection is a new registered research choice. Protected evaluation may not be reused as a tuning surface without opening a new lineage and paying the corresponding evidence cost.

### 14.2 Chronology and dependence
- Use chronological partitions.
- Use dependence-aware uncertainty at an appropriate block/cluster unit.
- Preserve cross-asset and overlapping-candidate dependence in diagnostics.
- Do not report naive trade-level IID significance when the dependence structure contradicts it.

### 14.3 Multiple testing
The family size must include explored Expert variants, grammar variants, policy thresholds, and other materially selected alternatives. Reality-Check/SPA/FDR/PBO/DSR-style tools may be appropriate diagnostics or controls, but none repairs leakage, invalid execution, or a repeatedly opened holdout.

### 14.4 Utility + risk + coverage certificate
A promotable policy must jointly satisfy:
- positive or otherwise preregistered after-cost NetUtility condition;
- hard drawdown/tail/capacity/heat constraints;
- minimum coverage/participation where the contract requires it;
- authority and data-validity requirements;
- replication across the declared chronological/regime tests.

### 14.5 Abstention
A policy that improves selected-subset metrics merely by rejecting almost everything fails unless it also satisfies the coverage and opportunity-cost constraints in the UtilityContract.

---

## 15. Shadow/live promotion

```text
SCREENING
   ↓
REPLICATION
   ↓
PROMOTION CANDIDATE
   ↓
SHADOW / FORWARD
   ↓
LIMITED LIVE
   ↓
LIVE-SUPPORTED
```

| Stage | Required evidence | Forbidden inference |
|---|---|---|
| Screening | Cheap deterministic baseline, costs, null/control | No deployment claim |
| Replication | Untouched chronology, dependence-aware uncertainty | No “future-proof” claim |
| Promotion candidate | Beats immediately simpler baseline and UtilityContract gates | No live execution claim |
| Shadow | Frozen forward decisions, operational receipts, no capital-bearing adaptation | No substitution of replay for realized execution |
| Limited live | Predeclared risk/capital cap, realized fills/costs, rollback semantics | No extrapolation beyond capacity/regime |
| Live-supported | Deployment certificate satisfied across the declared horizon | No universal or permanent edge claim |

Any live adaptation that changes policy semantics creates a new policy version and terminates the comparability of the prior certificate unless explicitly covered by the adaptation contract.

---

## 16. Failure and UNKNOWN semantics

### 16.1 UNKNOWN is first-class
The evaluator returns `UNKNOWN` when the requested claim exceeds available support, authority, data, or identification. UNKNOWN must propagate rather than being numerically imputed into a ranking.

### 16.2 Canonical refusal reasons

| Reason | Example |
|---|---|
| `MISSING_DECISION_TIME_DATA` | Feature exists historically but was not available at decision time. |
| `OUT_OF_SUPPORT_ACTION` | Target action/size not supported by logged/execution evidence. |
| `EXECUTION_AUTHORITY_TOO_WEAK` | L1 replay asked to support L3 impact claim. |
| `UNDEFINED_FUTURE` | Insufficient future horizon to evaluate the declared expiry. |
| `NON_IDENTIFIABLE_FILL` | Queue/partial fill cannot be justified. |
| `CONSTRAINT_INFEASIBLE` | No policy in the declared class satisfies hard constraints. |
| `PROTECTED_SLICE_ALREADY_CONSUMED` | Evaluation would reopen a one-use holdout without new lineage. |
| `MODEL_ONLY_COUNTERFACTUAL` | Value depends on an unvalidated simulator assumption. |
| `INSUFFICIENT_SUPPORT` | Too little supported data for the requested estimate/bound. |

### 16.3 Partial identification
When a defensible bound exists, the system records the interval rather than collapsing to UNKNOWN. However, the promotion rule must specify how bounds are compared. A point estimate may not be manufactured from the midpoint unless that estimator is independently justified and registered.

---

## 17. Artifact schemas

### 17.1 OpportunityUniverseVersion
```text
OpportunityUniverseVersion {
    universe_id
    version
    parent_universe_id?

    instrument_universe
    timeframe_set
    information_contract_id

    primitive_registry_hash
    predicate_ir_version
    behavior_template_registry_hash
    parameter_grid_hash

    tradability_rule_id
    support_rule_id
    authority_contract_id

    search_universe_size
    complexity_budget
    created_at
    code_hash
}
```

### 17.2 OracleEvaluationRecord
```text
OracleEvaluationRecord {
    evaluation_id
    oracle_role              // PARITY | HINDSIGHT | TARGET
    authority_level          // L1 | L2 | L3 | LIVE_RECEIPT
    identifiability_status

    information_contract_id
    opportunity_universe_id
    utility_contract_id
    policy_class_id
    cost_model_id
    capacity_model_id
    environment_target_id

    candidate_population_hash
    action_manifest_hash
    simulator_or_receipt_hash
    code_hash
    config_hash

    value_notation            // retrospective | replication | prospective | live
    point_estimate?
    lower_bound?
    upper_bound?
    uncertainty_artifact_id?

    refusal_reason?
    assumptions[]
    lineage_id
}
```

### 17.3 RegretAttributionRecord
```text
RegretAttributionRecord {
    attribution_id
    total_policy_gap
    reference_policy_id
    target_policy_id

    decomposition_method      // ISOLATED | MARGINAL | registered extension
    component_domain
    interaction_handling
    causal_graph_id?

    authority_summary
    uncertainty_summary
    forbidden_percent_claim_if_unresolved_interactions
}
```

### 17.4 DeploymentCertificate
```text
DeploymentCertificate {
    certificate_id
    policy_version
    utility_contract_id
    universe_id

    replication_gate
    risk_gate
    coverage_gate
    authority_gate
    shadow_gate
    live_gate?

    capacity_limit
    rollback_condition
    valid_from
    expires_or_revalidate_at
}
```

### 17.5 Integration with Evaluation Evidence Bundle (`v8.eval.v1`)
All Oracle evaluation, regret attribution, and opportunity universe artifacts are stored natively within the `v8.eval.v1` immutable evidence bundle (`EVALUATION_EVIDENCE_SYSTEM.md` §4):
- `OpportunityUniverseVersion` $\rightarrow$ `provenance/opportunity_universe.json`
- `OracleEvaluationRecord` $\rightarrow$ `economics/oracle_evaluation.parquet` & `statistics/reality_check.json` <!-- AUDIT-DOC-PATHS: SPECIFIED_OUTPUT `statistics/reality_check.json` is written by `v8-core/src/oracle/coverage.rs` inside the `v8.eval.v1` evidence bundle root, so this bundle-relative name is not a repository tree path. -->
- `RegretAttributionRecord` $\rightarrow$ `economics/regret_attribution.parquet` & Section S in `report.html` <!-- AUDIT-DOC-PATHS: SPECIFIED_OUTPUT `economics/regret_attribution.parquet` is written by `v8-core/src/oracle/coverage.rs` inside the `v8.eval.v1` evidence bundle root, so this bundle-relative name is not a repository tree path. -->
- Coverage & Scout Hypotheses $\rightarrow$ `analysis/hypotheses.jsonl` & `analysis/findings.jsonl`

---

## 18. Tests and invariants

### 18.1 Contract tests
1. A future-known field inserted into `InformationSet(t)` must hard-fail PIT validation.
2. Re-evaluating the same frozen Opportunity Universe with identical inputs must produce byte-identical Candidate identities and manifests.
3. Changing direction on a Candidate must produce a different Candidate identity, not an action variant.
4. Expanding any grammar grid must change `universe_id` and search-universe accounting.
5. An out-of-support action must never emit an `IDENTIFIED` point value.
6. An L1 evaluation requesting L3 authority must fail with `EXECUTION_AUTHORITY_TOO_WEAK`.
7. A policy violating a hard UtilityContract constraint must never outrank a feasible policy merely on primary return.
8. Zero/near-zero coverage must not pass a contract with a nonzero coverage floor.
9. UNKNOWN values must propagate through summaries and may not be silently treated as zero.
10. Opening a protected one-use evaluation twice under the same lineage must hard-fail.

### 18.2 Hindsight tests
1. The actual Candidate/action must be present in the relevant comparison set whenever a gap is defined.
2. Candidate-bound Hindsight evaluation must not create new Candidate identities.
3. Opportunity-Universe Hindsight evaluation must bind the alternative Candidate population hash explicitly.
4. Hindsight metrics must be labeled retrospective and must not appear in Target promotion fields.
5. Any cell whose potential maximizer is non-evaluable under the authority contract must abstain or return a bound.

### 18.3 Regret tests
1. Reports must reject an additive total if interaction handling is unspecified.
2. Every marginal/isolated effect must name its reference configuration.
3. Percentage attribution must be disabled unless a registered decomposition method covers interactions.

### 18.4 Fault injection
At minimum, inject future leakage, missing feed availability, unsupported size, queue-fill ambiguity, execution-model downgrade, cost doubling, capacity conflict, universe mutation after freeze, and repeated-holdout access. The correct behavior is refusal, weaker authority, or a new lineage—not silent continuation.

---

## 19. Implementation admission plan

This section defines implementation order. It is intentionally staged so that V8 does not build learned optimization on top of an undefined opportunity or authority surface.

| Phase | Implementation | Admission gate |
|---|---|---|
| `O0` | Contracts, enums, hashes, artifact schemas; no economics changed. | Schema tests, determinism, backward-compatible reading where required. |
| `O1` | Deterministic Opportunity Grammar + versioned universe generation. | PIT legality, finite search accounting, stable identities, no Expert dependency. |
| `O2` | Support/identifiability classifier + authority contract. | No unsupported point values; L1/L2/L3 claims fail closed. |
| `O3` | Representational coverage analysis against shipped Experts. | Population reconciliation, multiplicity accounting, no recoverability overclaim. |
| `O4` | Isolated/marginal component-effect framework. | Explicit reference configurations; no naive additive total. |
| `O5` | Decision-time recoverability policies for missed/represented opportunities. | Protected chronology, UtilityContract, risk + coverage + absolute value gates. |
| `O6` | Execution authority upgrades (L2, then validated L3 where data permits). | Policy ranking stability/re-evaluation; model-derived status respected. |
| `O7` | Shadow and limited-live promotion receipts. | DeploymentCertificate, capacity cap, rollback, version freeze. |

### 19.1 First Rust ownership boundary
The initial Rust implementation should own the contracts and deterministic grammar rather than a learned Target policy. A suggested module boundary is:

```text
v8-core/src/oracle/
    mod.rs
    taxonomy.rs
    utility.rs
    information.rs
    opportunity.rs
    support.rs
    authority.rs
    coverage.rs
    regret.rs
    artifacts.rs
```

### 19.2 What must not be implemented first
- a learned detector that defines and evaluates its own opportunity universe;
- Shapley regret attribution before isolated/marginal semantics are proven;
- L3 reactive execution claims without a validated simulator/data path;
- a universal scalar score that mixes return/risk/coverage without a UtilityContract;
- automatic promotion based solely on Hindsight gains.

---

## 20. Open questions and deferred work

| ID | Question | v1.0 treatment | Resolution path |
|---|---|---|---|
| O-OR-001 | Exact primitive/template registry for Opportunity Grammar? | `OPEN_QUESTION` | Implement minimal deterministic registry from existing PIT MarketState and Candidate semantics; every expansion is versioned. |
| O-OR-002 | Exact UtilityContract thresholds/weights? | `PROVISIONAL_DECISION` | Versioned contract + sensitivity band; do not encode a universal set in the Oracle ontology. |
| O-OR-003 | Bound-aware ranking rule for partially identified counterfactuals? | `OPEN_QUESTION` | Start fail-closed on overlapping bounds; register alternatives later. |
| O-OR-004 | Shapley/path decomposition for interactions? | `OPEN_QUESTION` | Deferred to v1.1; isolated/marginal effects first. |
| O-OR-005 | Future OPE / regime-drift estimator? | `OPEN_QUESTION` | Prospective diagnostic only until separately validated; never replaces shadow/live receipts. |
| O-OR-006 | Validated L3 reactive execution simulator? | `OPEN_QUESTION` | Data/model validation project; L1/L2 remain lower authority. |

---

## 21. Decision register

| ID | Decision | Status | Consequence |
|---|---|---|---|
| D-OR-001 | V8 has exactly three top-level Oracle roles. | `LOCKED_INVARIANT` | No additional top-level Oracle naming without a spec version change. |
| D-OR-002 | Target optimality is contract-relative, not raw-PnL universal. | `LOCKED_INVARIANT` | Every Target evaluation binds UtilityContract, cost/capacity, authority, universe, and policy class. |
| D-OR-003 | Utility uses primary after-cost value plus lexicographic hard constraints. | `PROVISIONAL_DECISION` | Exact thresholds/weights are versioned and may vary by deployment contract. |
| D-OR-004 | Opportunity Universe is Expert-independent, finite, deterministic, versioned, and preregistered. | `LOCKED_INVARIANT` | Grammar mutation creates new universe identity and research lineage. |
| D-OR-005 | Profitable hindsight alone does not define a missed opportunity. | `LOCKED_INVARIANT` | Opportunity requires PIT/schema legality and counterfactual authority. |
| D-OR-006 | Evaluable universe is Opportunity Universe intersected with supported counterfactuals. | `LOCKED_INVARIANT` | Unsupported opportunities remain UNKNOWN/model-derived rather than receiving fabricated PnL. |
| D-OR-007 | Identifiability status and execution authority are orthogonal fields. | `LOCKED_INVARIANT` | L1/L2/L3 does not itself imply identified truth. |
| D-OR-008 | Regret decomposition is non-additive by default. | `LOCKED_INVARIANT` | Isolated/marginal/interactions/total-policy-gap vocabulary is mandatory. |
| D-OR-009 | Representational coverage precedes monetary Detection Regret. | `PROVISIONAL_DECISION` | Missed hindsight set must pass decision-time recoverability before economic detection claims. |
| D-OR-010 | Frozen OOS, prospective/shadow, and live value are distinct. | `LOCKED_INVARIANT` | No historical test is relabeled as live support. |
| D-OR-011 | L1/L2/L3/LIVE_RECEIPT are authority levels, not Oracle classes. | `LOCKED_INVARIANT` | Prevents taxonomy explosion and claim laundering. |
| D-OR-012 | UNKNOWN is a valid fail-closed result. | `LOCKED_INVARIANT` | No numeric imputation solely to preserve ranking/report completeness. |

---

## 22. Claim register

| ID | Claim | Status | Boundary |
|---|---|---|---|
| C-OR-001 | There is no context-free unique “best trading policy”; optimality depends on objective, frictions, and constraints. | `LITERATURE_SUPPORTED` | Does not prove any chosen V8 UtilityContract is economically correct. |
| C-OR-002 | Decision quality/regret may be a more appropriate optimization target than prediction accuracy for downstream decisions. | `LITERATURE_SUPPORTED` | Does not define V8’s trading opportunity ontology. |
| C-OR-003 | Support/overlap limitations can make off-policy counterfactual values non-identifiable. | `LITERATURE_SUPPORTED` | Exact V8 support tests remain implementation-specific. |
| C-OR-004 | Future/non-stationary policy value is distinct from historical OOS value. | `LITERATURE_SUPPORTED` | Future-value estimators require their own assumptions and validation. |
| C-OR-005 | Component effects in sequential systems need not add uniquely without a chosen causal decomposition. | `LITERATURE_SUPPORTED` | Does not select a unique Shapley/path decomposition for V8. |
| C-OR-006 | Execution/impact modeling can change absolute value and policy ranking. | `LITERATURE_SUPPORTED` | Does not certify any V8 L3 simulator. |
| C-OR-007 | Abstention must be assessed jointly with risk and coverage, not rewarded merely for trading less. | `LITERATURE_SUPPORTED` | Specific V8 coverage floors remain contractual decisions. |
| C-OR-008 | The canonical V8 Opportunity Grammar defined here will capture economically meaningful opportunities. | `OPEN_QUESTION` | Must be tested; grammar is a measurement frame, not proof of market ontology. |
| C-OR-009 | A recoverable Target policy exists that is profitable after costs. | `OPEN_QUESTION` | No current Oracle specification or audit establishes this. |

---

## 23. Research basis and references

The references below are the primary or authoritative sources carried forward from *Target V8 Oracle Research Audit v0.1*. They justify design boundaries; none is cited as proof that V8 itself has edge.

1. Herdegen, M. & Muhle-Karbe, J. [Portfolio Optimization under Transaction Costs with Recursive Preferences](https://arxiv.org/abs/2402.08387).
2. [Portfolio Choice with Transaction Costs: a User’s Guide](https://arxiv.org/abs/1207.7330).
3. [A robust perspective on transaction-cost-aware portfolio choice](https://lbsresearch.london.edu/id/eprint/920/1/VDM%20Robust%20Perspective%20on%20Transaction%20Costs.pdf).
4. Capitaine, A. et al. [Online Decision-Focused Learning](https://arxiv.org/abs/2505.13564).
5. [Off-Policy Evaluation and Learning for the Future under Non-Stationarity](https://arxiv.org/abs/2506.20417).
6. [Off-Policy Evaluation for Action-Dependent Non-Stationary Environments](https://arxiv.org/abs/2301.10330).
7. [Off-policy evaluation work on non-stationary contextual/sequential environments](https://arxiv.org/abs/2302.11725).
8. Triantafyllou, S. et al. [Counterfactual Effect Decomposition in Multi-Agent Sequential Decision Making](https://arxiv.org/abs/2410.12539).
9. Abbade, L. R. & Reali Costa. [Realistic Market Impact Modeling for Reinforcement Learning Trading Environments](https://arxiv.org/abs/2603.29086).
10. Olby, O. et al. [Market Simulation-based RL for Execution Optimisation](https://arxiv.org/abs/2510.22206).
11. Xu, Y. et al. [Selective Conformal Risk Control](https://arxiv.org/abs/2512.12844).
12. [Conformal Selective Prediction with General Risk Control](https://arxiv.org/abs/2603.24704).

### 23.1 Project source relationship
- **V8 Final Research Monograph:** supplies the existing V8 Constitution, PIT/availability-time rule, Candidate/order/outcome distinction, deterministic baseline admission rule, simulation-authority matching, artifact binding, chronological OOS discipline, Outcome Cube, and Recoverable Regret semantics.
- **Target V8 Oracle Research Audit v0.1:** supplies the P0-A/P0-B/P0-C audit and the external research support for contract-relative objective, opportunity-universe independence, identifiability taxonomy, non-additive regret, non-stationarity, execution authority, and abstention/coverage semantics.

---

## Appendix A. Mapping to existing V8

| Existing V8 concept | Oracle-spec role | Change |
|---|---|---|
| MarketState PIT contract | `InformationSet(t)` | No semantic relaxation; reused as decision-time boundary. |
| Experts | Policies covering subsets of Opportunity Grammar | They no longer define the measurement universe. |
| Candidate lifecycle | Immutable proposal ontology | Extended to grammar-generated research Candidates under explicit universe versions. |
| Outcome Cube | Candidate-bound Hindsight measurement | Retained; not redefined as Target Oracle. |
| Recoverable Regret Phase 3 | Pattern for decision-time recoverability | Generalized conceptually to missed representation and other domains. |
| RiskGate / portfolio heat | UtilityContract hard constraints / allocation feasibility | Bound into target feasibility and promotion certificates. |
| Simulation authority | L1/L2/L3 + identifiability matrix | Made explicit as Oracle claim authority. |
| Screening → replication → promotion → shadow/live | Target admission ladder | Retained and bound to Oracle terminology. |
| Python parity oracle | `PARITY_ORACLE` | Terminology separated from economic Hindsight/Target meaning. |

---

## Appendix B. Non-goals

- This document does not define a profitable Expert.
- It does not certify the existing 28 Experts economically.
- It does not choose final UtilityContract thresholds for any deployment capital base.
- It does not certify an L3 reactive simulator.
- It does not prove that the finite Opportunity Grammar is a complete ontology of market opportunity.
- It does not authorize a learned router, scorer, ranker, RL executor, or online learner without its own admission experiment.
- It does not permit Hindsight outputs to be described as live-achievable returns.

---

## Appendix C. Minimal implementation interfaces

The following are interface sketches, not final Rust code. Their purpose is to make ownership and semantics explicit before implementation.

```rust
enum OracleRole {
    Parity,
    Hindsight,
    Target,
}

enum AuthorityLevel {
    L1,
    L2,
    L3,
    LiveReceipt,
}

enum Identifiability {
    Identified,
    PartiallyIdentified,
    ModelDerived,
    NotIdentifiable,
}

enum ValueNotion {
    Retrospective,
    Replication,
    ProspectiveShadow,
    LiveRealized,
}

struct OracleContext {
    role: OracleRole,
    authority: AuthorityLevel,
    information_contract_id: Hash,
    opportunity_universe_id: Hash,
    utility_contract_id: Hash,
    policy_class_id: Hash,
    cost_model_id: Hash,
    capacity_model_id: Hash,
    environment_target_id: Hash,
}

trait OpportunityGrammar {
    fn generate(
        &self,
        state: &MarketState,
        decision_time: Timestamp,
    ) -> Result<Vec<GrammarCandidate>, OracleRefusal>;
}

trait SupportClassifier {
    fn classify(
        &self,
        candidate: &GrammarCandidate,
        action: &Action,
        authority: AuthorityLevel,
    ) -> CounterfactualAuthority;
}

trait HindsightEvaluator {
    fn evaluate(
        &self,
        candidate: &GrammarCandidate,
        action_set: &ActionManifest,
        context: &OracleContext,
    ) -> OracleOutcome;
}

trait TargetPolicy {
    fn decide(
        &self,
        information: &InformationSet,
        candidates: &[GrammarCandidate],
        constraints: &UtilityContract,
    ) -> DecisionSet;
}
```

**Implementation rule:** these interfaces must preserve the three-Oracle taxonomy. A module named `detection_oracle.rs`, `execution_oracle.rs`, or similar should be rejected unless “oracle” refers unambiguously to one of the three top-level roles. Prefer domain names such as `coverage.rs`, `selection.rs`, `execution.rs`, and `allocation.rs`.
