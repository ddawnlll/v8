# V8 Kaizen Continuous Improvement Engine Specification (v8.kaizen.engine.v1)

**Status:** ACTIVE_SPECIFICATION / LOCKED_INVARIANT  
**Scope:** Defines the complete, closed-loop autonomous continuous improvement engine (**Kaizen**) for V8. Connects evaluation evidence, retrospective outcome forensics, target oracle opportunities, hypothesis generation, challenger experimentation, research debt accounting, and registry promotion into a single scientific learning loop.

---

## 1. Executive Summary & Core Philosophy

**Kaizen is V8's closed-loop scientific self-improvement engine.** It is neither a blind parameter optimizer nor a simple static report generator.

```text
                ┌─────────────────────────────┐
                │      CURRENT V8 POLICY      │
                └──────────────┬──────────────┘
                               │
                               ▼
                        EVALUATION RUN
                               │
                               ▼
                     EVIDENCE / OUTCOMES
                               │
                               ▼
                    ┌───────────────────┐
                    │      KAIZEN       │
                    │                   │
                    │  Neden kötü?      │
                    │  Nerede iyi?      │
                    │  Ne düzeltilebilir│
                    │  Ne test edilmeli?│
                    └─────────┬─────────┘
                              │
                ┌─────────────┼───────────────┐
                ▼             ▼               ▼
             ALPHA          COST           GEOMETRY
           hypothesis     hypothesis       hypothesis
                │             │               │
                └─────────────┼───────────────┘
                              ▼
                       CHALLENGER(S)
                              │
                              ▼
                       EXPERIMENTATION
                DEV → WFA → OOS → SHADOW
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                  REJECT              PROMOTE
                                        │
                                        ▼
                                NEW CURRENT V8
                                        │
                                        └──────► Next Cycle
```

### 1.1 The Core Scientific Invariant: Learning vs Policy Churn
$$\text{NEVER: } \text{while } \text{pnl} < \text{target}: \text{optimize\_parameters\_harder}()$$

Kaizen's objective is **not** to maximize past in-sample backtest PnL:
$$\text{Maximize } \mathbb{E}[\text{Future Utility}]$$
$$\text{Subject to: } \begin{cases}
\text{Evidence Validity \& Point-in-Time Data Invariants} \\
\text{Strict Friction Realism (Fees, Slippage, Funding Rates)} \\
\text{Drawdown \& Margin Utilization Constraints} \\
\text{Lifetime Multiplicity Debt Accounting (Bailey PBO \& Deflated Sharpe)} \\
\text{Parameter Neighborhood Plateau Robustness (AlgoXpert Cliff Veto)} \\
\text{One-Shot Frozen Holdout Burning (Zero Reuse)}
\end{cases}$$

---

## 2. Unifying the V8 Research Architecture Under Kaizen

Kaizen is the master orchestrator that integrates existing V8 subsystems into a coherent learning lifecycle:

1. **Evaluation Evidence System (`v8.eval.v1`):** *The sensory system (eyes)* — produces queryable Parquet traces, execution DAGs, cost surfaces, and distribution caches.
2. **Outcome Cube (`OUTCOME_CUBE_SPEC`):** *The retrospective microscope* — evaluates counterfactual actions $A(C)$ (alternative SL, TP, Expiry, NO_TRADE) to isolate recoverable regret.
3. **Target Oracle (`TARGET_ORACLE_SPEC`):** *The opportunity detector* — identifies structural market moves that existing experts failed to detect.
4. **Hypothesis Lab (`HYPOTHESIS_LAB_PROTOCOL`):** *The experimental laboratory* — converts diagnostics into falsifiable claims and structured challenger families.
5. **Sweep Engine (`SWEEP_PROTOCOL`):** *The search engine* — executes finite parameter campaigns under full trial debt accounting.
6. **Learning Protocol (`LEARNING_PROTOCOL`):** *The safety and governance firewall* — enforces that outcome data never directly mutates the active decision plane.
7. **Registry (`CLAIMS_REGISTRY` & `EXPERIMENT_REGISTRY`):** *The decision gate* — records immutable promotion, shadow, or rejection verdicts.

---

## 3. The 7-Stage Kaizen Improvement Loop

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────┐     ┌────────┐
│ 1. OBSERVE│ ──► │2. DIAGNOSE│ ──► │3. OPPORTUNITY│ ──► │4. HYPOTHESIZE│ ──► │5. CHALLENGER │ ──► │6. EXPERIMENT│ ──► │7. DECIDE│
└─────────┘     └──────────┘     └─────────────┘     └────────────┘     └──────────────┘     └────────────┘     └────────┘
```

### Stage 1: Observe (Evidence Ingestion)
Kaizen ingests the complete `EvidenceBundle` from the latest evaluation run:
- Bar traces, signal emissions, candidate formations, risk vetoes, fill records, and cashflows.
- High-resolution equity curves and friction breakdowns (fees, slippage, funding drag).

### Stage 2: Diagnose (Forensic Failure Attribution)
Deterministically decomposes why an expert or portfolio underperformed:
- **Gross vs Friction Attribution:**
  - $\text{Gross } R < 0.0 \implies \text{GrossNegative}$ (Signal / detection flaw).
  - $\text{Gross } R > 0.0 \land \text{Net } R \le 0.0 \implies \text{CostDominated}$ (Execution, churn, or friction drag).
- **Regime Vulnerability:** Checks whether performance collapses under specific volatility (ATR quantiles) or trend regimes (ADX/EMA alignment).
- **Attribution & Capacity:** Checks whether performance was damaged by slot contention or capital rejections.

### Stage 3: Opportunity Discovery (Retrospective & Target Analysis)
Kaizen queries the Outcome Cube and Target Oracle:
- **Regret Localization:** Are stopped-out trades frequently hitting MFE targets later? (Stop too tight $\implies$ Geometry opportunity).
- **NO_TRADE Superiority:** Did taking NO_TRADE in low-volatility chop outperform actual trades in $> 50\%$ of episodes? (Habitat / gating opportunity).
- **Target Oracle Gaps:** Did high-conviction structural price swings occur where no expert emitted candidates? (Alpha coverage opportunity).

### Stage 4: Hypothesize (Falsifiable Scientific Formulation)
Kaizen compiles findings into an immutable `HypothesisRecord`:
- **Claim:** Clear statement of the proposed mechanism.
- **Falsification Rule:** Quantified metric target (e.g. $\Delta \text{Net } R \ge +0.12$, WFA pass rate $\ge 60\%$, no drawdown increase).
- **Challenger Parameter Search Space:** Bounded, discrete candidate family.

### Stage 5: Challenger Creation (Immutable Policy Candidate)
Kaizen generates a new, immutable `PolicyChallenger` artifact without touching the incumbent policy:
- Baseline: Active Expert version $V_k$.
- Challenger: Expert version $V_{k+1}$ (e.g. original logic + ATR regime gate $\theta \in \{1.0, 1.5, 2.0\}$).

### Stage 6: Experimentation & Validation Ladder
The challenger progresses through sequential validation gates:
1. **DEV Robustness Surface:** AlgoXpert plateau search ($\text{Sharpe}(\theta) \ge 0.90 \times \text{Peak}$) + Cliff veto (neighbor drop $\le 30\%$).
2. **Purged Walk-Forward Analysis (WFA):** Chronological folds with purge windows. Majority fold pass required; any single catastrophic drawdown fold triggers an immediate campaign veto.
3. **Research Debt Logging:** All tested variants increment the global lifetime trial counter ($N_{\text{trials}} \mathrel{+}= |\text{Variants}|$).
4. **One-Shot Frozen Holdout:** Evaluated on strictly unsealed out-of-sample data. A cryptographic `HoldoutBurnReceipt` is committed; the dataset is burned against reuse.

### Stage 7: Decide & Registry Action
The Kaizen engine issues a deterministic `RegistryDecision`:
- `PROMOTE`: Challenger becomes the new incumbent baseline.
- `SHADOW`: Challenger runs in parallel shadow tracking mode.
- `QUARANTINE`: Challenger held pending multi-regime observation.
- `REJECT`: Challenger failed falsification criteria; research lineage is permanently archived.

---

## 4. Rust Engine Architecture (`v8-core/src/kaizen/`)

```text
v8-core/src/kaizen/
├── mod.rs                  # Module exports and Kaizen Engine facade
├── engine.rs               # Master KaizenEngine trait & orchestrator
├── diagnosis.rs            # Forensic failure taxonomy & gross/friction attribution
├── opportunity.rs          # Outcome cube regret analysis & target oracle opportunity mining
├── hypothesis.rs           # Falsifiable research hypothesis records
├── challenger.rs           # Policy challenger specification & parameter bounds
├── experiment.rs           # DEV plateau surface, Purged WFA, and Holdout runner
├── selection.rs            # Registry decision rules (Promote / Shadow / Quarantine / Reject)
├── research_debt.rs        # Global lifetime trial accounting & holdout burn receipts
└── adaptive.rs             # Adaptive sequential sweep gate (BLOCKED under O-032)
```

### 4.1 Master Engine Interface

```rust
pub trait KaizenEngine {
    /// Ingests evidence, runs diagnostics, and identifies improvement opportunities.
    fn evaluate(
        &self,
        incumbent: &PolicyArtifact,
        evidence: &EvidenceBundle,
        cube: &OutcomeCube,
    ) -> KaizenPlan;

    /// Compiles actionable opportunities into falsifiable challenger proposals.
    fn propose(
        &self,
        plan: &KaizenPlan,
    ) -> Vec<ChallengerProposal>;

    /// Evaluates experimental evidence and issues a binding registry decision.
    fn decide(
        &self,
        experiment: &ExperimentEvidence,
        multiplicity_budget: &MultiplicityBudget,
    ) -> RegistryDecision;
}
```

---

## 5. Kaizen Invariants & Anti-Overfitting Safeguards

1. **Type-System Decision Plane Isolation:**
   - Diagnostic and hypothesis code cannot access or mutate mutable references in `v8-core` runtime experts.
   - Challengers are standalone immutable structs compiled outside the live execution plane.
2. **Deterministic Attribution:**
   - Every performance delta must be traced to its exact source: Alpha signal, Execution friction, SL/TP geometry, or Habitat gating.
3. **No Retrospective Leakage:**
   - Regret metrics derived from the Outcome Cube are used solely for diagnostic classification, never as in-sample fitting targets.
4. **Lifetime Multiplicity Accounting:**
   - Every candidate evaluated across Kaizen's lifetime adds to the global research trial counter. P-values and Sharpe ratios are penalized using Deflated Sharpe Ratio (DSR) and White's Reality Check (WRC).
5. **One-Shot Holdout Burning:**
   - Out-of-sample data can never be re-queried to tune or repair a failed hypothesis.
