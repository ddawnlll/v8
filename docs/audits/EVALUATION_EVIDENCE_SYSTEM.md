# V8 Evaluation Evidence System & Scientific Audit Specification (v8.eval.v1)

**Status:** DESIGN_INFERENCE / LOCKED_INVARIANT.
**Scope:** Replaces legacy single-report generation with an immutable, structured scientific evidence bundle designed for autonomous research agents (Scout -> Investigator -> Decision loop) and deterministic audit verification.

---

## 1. Paradigm Shift: From Report Generator to Scientific Evidence Substrate

Legacy quantitative backtesting systems and earlier V8 iterations treated evaluation primarily as a **report generation step**—producing an aggregated HTML or text summary containing P&L curves, Sharpe ratios, and summary win rates. 

Under **v8.eval.v1**, evaluation is redefined:
> **An evaluation run does not merely generate a human-facing report. It produces an immutable, queryable, content-addressed Evidence Bundle upon which autonomous agents can formulate, test, confirm, or refute falsifiable scientific hypotheses.**

```
                                LEGACY VIEW (Outcome Only)
                      ┌──────────────────────────────────────────┐
                      │  Input Tape ──► Engine ──► Final P&L/HTML│
                      └──────────────────────────────────────────┘

                                V8.2+ SCIENTIFIC PARADIGM
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                          │
 │   Market Data (PIT) ──► S0-S7 Pipeline ──► Immutable Evidence Bundle (v8.eval.v1)        │
 │                                                  │                                       │
 │                          ┌───────────────────────┴───────────────────────┐               │
 │                          ▼                                               ▼               │
 │                 Structured Evidence Store                     Deterministic Schema Cache  │
 │              (Parquet Traces, DAG, Ledgers)                 (Distributions, Nulls, Stats)│
 │                          │                                               │               │
 │                          └───────────────────────┬───────────────────────┘               │
 │                                                  ▼                                       │
 │                                       Autonomous Agent Swarm                             │
 │                         ┌─────────────────────────────────────────┐                      │
 │                         │  • Triage Agent (Anomaly Detection)     │                      │
 │                         │  • Scout Agents (Hypothesis Generation) │                      │
 │                         │  • Investigator Agents (Corpus Testing) │                      │
 │                         │  • Decision Agent (Registry Governance) │                      │
 │                         └────────────────────┬────────────────────┘                      │
 │                                              ▼                                           │
 │                                    Confirmed Finding Graph                               │
 │                                 (EPIDEMIOLOGICAL / STATISTICAL)                          │
 │                                              │                                           │
 │                          ┌───────────────────┴───────────────────┐                       │
 │                          ▼                                       ▼                       │
 │                  Human HTML Report (A-W)                 Machine Evidence API            │
 │                   (Executive Viewport)                  (JSON-RPC / Substrate)           │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
```

The HTML report is strictly a **read-only presentation view (viewport)** for human operators. The canonical authority resides exclusively in **machine-readable, schema-validated, content-addressed structured artifacts**. Agents never parse raw HTML.

---

## 2. Literature Foundations & Methodological Lineage

Recent agentic evaluation and quantitative finance literature (2025–2026) converges on the principles underpinning `v8.eval.v1`:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                LITERATURE MAPPING MATRIX                                     │
├─────────────────────────┬──────────────────────────────────┬─────────────────────────────────┤
│ Foundation / Paper      │ Core Principle                   │ V8.eval.v1 Implementation       │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Harness-Bench           │ Outcome != Performance;          │ Saves raw execution traces,     │
│ (arXiv:2605.27922)      │ artifacts + traces + usage stats │ validator outputs, and state DAG│
│                         │ + validator outputs required.    │ alongside realized returns.     │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ ClawTrack               │ Separation of Outcome Grading    │ Process telemetry: Goal         │
│ (arXiv:2607.28037)      │ vs Process Grading; trajectory,  │ alignment, filter efficiency,   │
│                         │ audit logs, workspace snapshots. │ dedup/veto conservation.        │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ A²E Protocol            │ Decouple task spec, environment, │ Typed execution records:        │
│ (arXiv:2608.07346)      │ expected actions, and execution. │ signals -> candidates ->        │
│                         │                                  │ transitions -> trades.          │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ On Randomness in Evals  │ Single-run variance renders      │ pass@1, optimistic retry, and   │
│ (arXiv:2602.07150)      │ small differences noisy;         │ pessimistic consistency bounds   │
│                         │ compute consistency boundaries.  │ across perturbation sweeps.     │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Princeton Agent         │ 4 Pillars: Consistency,          │ Reliability Envelope: Outcome,  │
│ Reliability             │ Robustness, Predictability,      │ trajectory, and resource        │
│ (arXiv:2602.16666)      │ Safety.                          │ consistency across environments.│
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Insights Generator      │ Scalable corpus diagnosis via    │ Two-tier agent investigation:    │
│ (arXiv:2605.21347)      │ Schema Cache + Scout/Investigator│ Scout generates hypotheses;     │
│                         │ separation; confirmed findings.  │ Investigator verifies on corpus.│
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ AlgoXpert Framework     │ Parameter perturbation cliffs &  │ Robustness Surfaces: cost, stop,│
│ (arXiv:2603.09219)      │ IS-WFA-OOS degradation metrics.  │ target, and joint fragility.    │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ SysTradeBench           │ Hard fail-closed validity gates; │ Validity Gates: Leakage,        │
│ (arXiv:2604.04812)      │ frozen strategy checksums.       │ Accounting, SIMD/Thread Parity. │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ AgentRx                 │ Execution trajectory fault       │ Formal Failure Ontology:        │
│ (arXiv:2602.02475)      │ localization & ontology mapping. │ 9-category structured taxons.   │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Bailey et al. (PBO/DSR) │ Multiple-testing deflated Sharpe │ Research Ledger & trial count   │
│ & White Reality Check   │ & probability of overfitting.    │ penalty across lifetime corpus. │
└─────────────────────────┴──────────────────────────────────┴─────────────────────────────────┘
```

---

## 3. Reliability Envelope vs Single-Run Outcomes

Single-run backtest performance is an illusion of precision. In trading engines, while execution arithmetic may be deterministic, the **execution circumstance** varies across real-world deployments.

V8 constructs a multi-dimensional **Reliability Envelope**:

$$\text{Reliability Envelope} = \mathcal{E}(\text{Threads}, \text{SIMD}, \text{Cache State}, \text{CPU Architecture}, \text{Input Perturbations}, \text{Cost Shocks})$$

### Core Invariant: Semantic Invariance under Circumstantial Perturbation
$$\forall c_1, c_2 \in \text{ExecutionCircumstances}, \quad \text{Semantics}(S, c_1) \equiv \text{Semantics}(S, c_2) \implies \text{Economics}(S, c_1) \equiv \text{Economics}(S, c_2)$$

The reliability envelope assesses:
1. **Thread Parity ($T \in \{1, 2, 4, 8\}$):** Does candidate allocation or state aggregation drift with concurrency?
2. **SIMD vs Scalar Parity:** Do AVX2/AVX-512 vector paths produce bit-identical decisions compared to scalar fallbacks?
3. **Cache Cold vs Warm:** Does pre-warmed state alter lookback indexing or float rounding?
4. **Input Data Perturbations:** Injecting 1-bar timestamp jitter, micro-slippage, or dropped funding rates.
5. **Parameter Neighborhood Stability:** Does a $\pm 2\%$ perturbation in indicator threshold cause an catastrophic performance cliff ($\Delta \text{Sharpe} > 50\%$)?

---

## 4. Total Artifact Structure & Directory Layout (`v8.eval.v1`)

Every evaluation run creates a self-contained, immutable bundle under `evaluation/<RUN_ID>/`:

```
evaluation/
└── RUN_ID/
    ├── manifest.json                  # Entry gateway & cryptographic receipt
    ├── executive.json                 # Machine-readable scorecard & critical verdicts
    ├── report.html                    # Presentation viewport (Sections A–W)
    │
    ├── provenance/                    # Cryptographic lineage & reproduction DAG
    │   ├── environment.json           # Host CPU, OS, compiler, Rust toolchain, flags
    │   ├── inputs.json                # Data sources, symbol list, interval, bar counts
    │   ├── hashes.json                # Binary, tape, config, and artifact checksums
    │   ├── config.json                # Evaluator configuration snapshot
    │   └── artifact_dag.json          # Dependency graph of all generated artifacts
    │
    ├── data/                          # Input data forensic layer
    │   ├── bars.parquet               # PIT ingested OHLCV + funding rows
    │   ├── data_quality.parquet       # Per-bar quality flags, gap indicators
    │   └── feature_census.parquet     # Feature distributions, null rates, quantiles
    │
    ├── execution/                     # Full pipeline event telemetry
    │   ├── evaluations.parquet        # S0: All bar-level expert evaluation attempts
    │   ├── signals.parquet            # S1: Emitted raw behavioral signals
    │   ├── candidates.parquet         # S2: Formed candidate episodes
    │   ├── transitions.parquet        # S3-S4: State transitions (dedup, cooldown)
    │   ├── vetoes.parquet             # S5: Risk, capacity, and heat veto events
    │   └── trades.parquet             # S6-S7: Admitted orders, fills, and trade logs
    │
    ├── economics/                     # Financial performance forensic layer
    │   ├── portfolio.parquet          # Aggregate portfolio metrics & drawdown series
    │   ├── experts.parquet            # Per-expert return decomposition & attribution
    │   ├── costs.parquet              # Spread, fee, slippage, and funding drag
    │   └── equity_curve.parquet       # High-resolution step-by-step equity curve
    │
    ├── paths/                         # Trade path & trajectory forensics
    │   ├── mfe_mae.parquet            # Maximum Favorable/Adverse Excursion records
    │   ├── markouts.parquet           # Post-trigger price trajectories (t+1..t+k)
    │   ├── exits.parquet              # Exit barrier classification & touch sequences
    │   └── intrabar_ambiguity.parquet # High/Low touch ambiguity & penalty bounds
    │
    ├── slices/                        # Cohort & regime conditional performance
    │   ├── regime.parquet             # Volatility/Trend regime slices
    │   ├── direction.parquet          # Long vs Short asymmetry
    │   ├── time_of_day.parquet        # Session / TOD / DOW performance
    │   ├── volatility.parquet         # ATR / Realized Volatility quantiles
    │   └── liquidity.parquet          # Volume / OFI regime slices
    │
    ├── robustness/                    # Counterfactual surfaces & stability
    │   ├── cost_surface.parquet       # Friction vs Net Expectancy grid
    │   ├── exit_surface.parquet       # SL/TP/Expiry geometry perturbation grid
    │   ├── parameter_surface.parquet  # Neighborhood parameter sensitivity
    │   ├── perturbations.parquet      # Injected stress & data corruption tests
    │   └── degradation.parquet        # IS -> WFA -> OOS -> Holdout degradation
    │
    ├── statistics/                    # Rigorous hypothesis testing artifacts
    │   ├── bootstrap.json             # Stationary bootstrap CIs on Expectancy/Sharpe
    │   ├── permutations.json          # Trade order & return permutation distributions
    │   ├── nulls.json                 # 10-family null benchmark comparisons
    │   ├── reality_check.json         # White's Reality Check & Hansen's SPA tests
    │   ├── multiple_testing.json      # Lifetime research trials & DSR corrections
    │   └── backtest_overfit.json      # Bailey's Probability of Backtest Overfit (PBO)
    │
    ├── correctness/                   # Rust engine invariant & parity receipts
    │   ├── invariants.json            # Conservation and lifecycle invariant checks
    │   ├── replay_digest.json         # Deterministic replay hash verification
    │   ├── thread_parity.json         # 1 vs 2 vs 4 vs 8 thread parity results
    │   ├── simd_parity.json           # AVX2/AVX-512 vs Scalar bit-level parity
    │   └── implementation_parity.json # Minimal reference oracle differential report
    │
    └── analysis/                      # Agent reasoning & finding graph
        ├── schema_cache.json          # Precomputed column statistics for LLM queries
        ├── hypotheses.jsonl           # Preregistered and Scout-generated hypotheses
        ├── findings.jsonl             # Confirmed, Refuted, or Inconclusive findings
        ├── anomalies.jsonl            # Automated outlier & diagnostic alerts
        └── recommendations.jsonl      # Concrete next preregistered challengers
```

---

## 5. `manifest.json` Entry Gateway & Accounting Invariants

Agents first inspect `manifest.json` (~10 KB) before querying large Parquet datasets. If any hard gate fails, the evaluation run is immediately classified as `INVALID_RUN`.

```json
{
  "schema": "v8.eval.v1",
  "run_id": "RUN-20260819-BTC-001",
  "timestamp_utc": "2026-08-19T03:00:00Z",
  "git_commit": "a1f89c0d2e4b6789123456789abcdef01234567",
  "binary_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "tape_hash": "7a3560f7690623a9d4fa1534da6cc0a7d9796e625a6eb8ee99b3b0d2de0bc5ef",
  "config_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
  "dataset": {
    "instrument": "BTCUSDT",
    "timeframe": "1h",
    "raw_bars": 9948,
    "warmup_bars": 1188,
    "eligible_bars": 8760,
    "start_utc": "2025-07-01T00:00:00Z",
    "end_utc": "2026-07-01T00:00:00Z"
  },
  "funnel_conservation": {
    "evaluations": 245280,
    "setups_triggered": 42647,
    "deduplicated": 14766,
    "vetoed_risk_capacity": 27879,
    "admitted_trades": 2,
    "invariant_holds": true,
    "accounting_equation": "42647 == 14766 (dedup) + 27879 (veto) + 2 (admitted)"
  },
  "validity_gates": {
    "temporal_leakage": "PASS",
    "accounting_conservation": "PASS",
    "determinism_replay": "PASS",
    "simd_scalar_parity": "PASS",
    "thread_parity": "PASS",
    "overall_validity": "VALID"
  },
  "economic_verdict": "INSUFFICIENT_EVIDENCE",
  "summary_metrics": {
    "gross_expectancy_R": -0.012,
    "net_expectancy_R": -0.048,
    "total_trades": 2,
    "sharpe_ratio": -0.18,
    "max_drawdown_R": 1.96
  },
  "critical_findings": [
    "F-0012: Extreme veto rate (99.99%) driven by unparameterized EXISTING_EXPOSURE_CONFLICT.",
    "F-0014: Expert identity collapse in admission veto logs."
  ],
  "artifacts": {
    "root_dir": "evaluation/RUN-20260819-BTC-001",
    "total_size_bytes": 14820942
  }
}
```

### Invariant Equation
$$\text{Setups} = \text{Deduplicated} + \text{Vetoed}_{\text{Risk/Capacity}} + \text{Admitted}$$
Any mismatch ($\Delta \neq 0$) trips an immediate `FAIL-CLOSED` error.

---

## 6. Data Forensic Layer: Temporal Integrity & Quality DAG

```
   Raw Venue Feeds (Vision Archive)
               │
               ▼
   [Checksum & Ingestion Validator] ──► Temporal Integrity Checks (monotonicity, gaps, lookahead)
               │
               ▼
   [Feature Normalization Engine]   ──► Feature Census (NaN, Inf, Null Rate, Variance, Quantiles)
               │
               ▼
   [State Store Materialization]    ──► Provenance DAG (every column mapped to origin code)
```

1. **Temporal Integrity Forensic:**
   - Monotonic increasing timestamp assertion: $\forall t_i, t_i < t_{i+1}$.
   - Availability-time verification: $t_{\text{decision}} \ge t_{\text{availability}} > t_{\text{event}}$.
   - Missing bar & holiday audit with venue calendar verification.
   - Purge & embargo window enforcement across development/OOS partitions.

2. **Feature Quality Census:**
   - Metrics computed per feature: $N$, Missing $\%$, NaN count, Infinite values, Zero variance flags, Quantiles ($p_1, p_{25}, p_{50}, p_{75}, p_{99}$), Min/Max, Discontinuity jumps, and Stale repeated-value sequences.

3. **Source Lineage DAG:**
   - Every column in `feature_census.parquet` is cryptographically tied to its exact generating Rust function hash and upstream source field.

---

## 7. Funnel Forensic: Granular Conversion & Lost Expectancy

Every Expert's signal funnel is audited at every stage:

$$\text{Bars Observed} \xrightarrow{E} \text{Eligible Evals} \xrightarrow{S} \text{Setup} \xrightarrow{D} \text{Dedup Filter} \xrightarrow{R} \text{Risk/Cap Filter} \xrightarrow{A} \text{Admitted} \xrightarrow{T} \text{Filled Trade} \xrightarrow{X} \text{Outcome}$$

For every transition:
- **Count & Conversion Rate:** Percentage of signals surviving each stage.
- **Reason Codes:** Categorized rejection tags (e.g., `COOLDOWN_ACTIVE`, `OPPOSITE_EXPOSURE_ACTIVE`, `HEAT_CAP_EXCEEDED`).
- **Lost Expectancy Estimate ($\Delta \mathbb{E}[R]$):** Theoretical counterfactual return of rejected signals vs admitted signals, measuring whether risk filters successfully reject negative edge or inadvertently filter profitable setups.
- **Trace IDs:** Full array of Candidate IDs for agentic drilldown.

---

## 8. Economic Forensic Layer

Economic performance is separated into **Gross Edge**, **Friction Drag**, and **Net Realized Edge**:

$$\text{Net } R = \text{Gross } R - (\text{Fee } R + \text{Slippage } R + \text{Funding } R + \text{Delay Penalty } R)$$

```
┌───────────────────────────┬───────────────────────────┬───────────────────────────┐
│ Returns & Expectancy      │ Trade & Risk Statistics   │ Execution Economics       │
├───────────────────────────┼───────────────────────────┼───────────────────────────┤
│ • Gross Expectancy ($R$)  │ • Sample Count ($N$)      │ • Total Fee Drag ($R$)    │
│ • Net Expectancy ($R$)    │ • Win Rate ($\%$)         │ • Slippage Drag ($R$)     │
│ • Median $R$ per Trade    │ • Profit Factor ($PF$)    │ • Net Funding Drag ($R$)  │
│ • Annualized Return       │ • Payoff Ratio (Win/Loss) │ • Annual Turnover         │
│ • Sharpe Ratio (Ann.)     │ • Max Drawdown ($R$)      │ • Gross -> Net Decay      │
│ • Sortino Ratio           │ • Average Drawdown ($R$)  │ • Break-Even Cost Limit   │
│ • Calmar Ratio            │ • CVaR / Expected Shortfall│ • Capacity Estimate ($)   │
└───────────────────────────┴───────────────────────────┴───────────────────────────┘
```

---

## 9. Counterfactual Robustness Surfaces

Rather than testing isolated discrete exits, `v8.eval.v1` evaluates continuous response surfaces across four core dimensions:

1. **Cost Surface:** $\mathbb{E}[R](c)$ where cost $c \in [0, 20\text{ bps}]$. Determines the zero-edge intercept (Break-even friction).
2. **Stop Surface:** $\mathbb{E}[R](\text{Stop\_R})$ where $\text{Stop\_R} \in [0.2R, 3.0R]$. Measures stop-loss tightness sensitivity.
3. **Target Surface:** $\mathbb{E}[R](\text{Target\_R})$ where $\text{Target\_R} \in [0.5R, 10.0R]$. Evaluates profit target truncation.
4. **Expiry Surface:** $\mathbb{E}[R](\text{Expiry\_Bars})$ where $\text{Expiry} \in [1, 100\text{ bars}]$.
5. **Joint Fragility Metrics:**
   - **Plateau Width:** Parameter radius over which $\mathbb{E}[R] > 0$.
   - **Performance Cliff (AlgoXpert):** Maximum first derivative $\max |\nabla \text{Sharpe}|$ across parameter neighbors.
   - **Local Fragility Index:** Variance of performance under small $\pm 5\%$ parameter perturbations.

---

## 10. Path Forensics & Trajectory Classification

Every trade produces high-resolution intrabar trajectory metrics:

```
 Entry ──► (Time to MAE, MAE) ──► (Time to MFE, MFE) ──► Barrier Sequence ──► Realized Exit ──► Post-Exit Path
```

### Automated Path Classifications
- **Stop Too Tight:** Trade hit SL, but subsequently reached $+1.0R$ favorable excursion within the original trade horizon.
- **Target Too Tight:** Trade hit TP, followed by immediate strong continuation ($> +2.0R$ additional excursion).
- **Dead Trade:** Neither SL nor TP approached ($|MAE| < 0.2R, |MFE| < 0.2R$) for $> 80\%$ of expiry duration (zero-information capital lockup).
- **Bad Entry:** MAE occurs immediately ($t_{\text{MAE}} = 1$) with zero favorable movement ($MFE < 0.05R$).
- **Good Signal / Bad Execution:** Markout trajectory at $t+k$ is strongly positive, but realized trade is negative due to spread/slippage.
- **Bad Signal / Lucky Exit:** Trajectory is predominantly adverse, but trade exited with a small gain due to an ephemeral intrabar spike.

---

## 11. 10-Family Null Model Benchmark Suite

An observed edge is statistically meaningful only if it significantly outperforms a battery of structured Null Models that preserve trivial time-series properties:

```
┌──────────────────────────────────────┬──────────────────────────────────────────────────────────┐
│ Null Model Variant                   │ Preserved Invariant / Purpose                            │
├──────────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ 1. Random Entry Uniform              │ Tests whether timing carries information over random.    │
│ 2. Random Direction                  │ Preserves exact entry times; randomizes Long/Short side. │
│ 3. Randomized Timestamps (Poisson)   │ Preserves trade count and duration; randomizes times.    │
│ 4. Always Long                       │ Quantifies underlying market drift / beta baseline.      │
│ 5. Always Short                      │ Quantifies short-side market drift baseline.             │
│ 6. Inverted Signal                   │ Directly tests directional sign fidelity ($S -> -S$).    │
│ 7. Shuffled Expert Labels            │ Tests whether specific expert identities matter.         │
│ 8. Matched-Frequency Random Strategy │ Matches empirical trade spacing & interval distribution. │
│ 9. Matched-Duration Random Strategy  │ Matches empirical trade holding-time distribution.       │
│ 10. Matched-Regime Random Strategy   │ Generates random trades strictly within the same regime. │
└──────────────────────────────────────┴──────────────────────────────────────────────────────────┘
```

---

## 12. Multiple-Testing Accounting & Research Debt Ledger

The probability of false discovery increases dramatically with cumulative exploration:

$$P(\text{False Positive}) = 1 - (1 - \alpha)^K \xrightarrow[K \to \infty]{} 1.0$$

Where $K$ is the **cumulative number of hypotheses and parameter variants ever tested on this dataset in the project's lifetime**.

1. **Deflated Sharpe Ratio (DSR):** Adjusts Sharpe for non-normality, sample length, and $K$ trials (Bailey & de Prado).
2. **White's Reality Check & Hansen's Superior Predictive Ability (SPA):** Evaluates whether the best strategy in the family beats the benchmark after accounting for the full family search space.
3. **Probability of Backtest Overfitting (PBO):** Combinatorially Symmetric Cross-Validation (CSCV) over chronological partitions.
4. **Global Research Ledger:** Every evaluation run appends tested hypotheses, variants, and slice queries to `research_ledger.jsonl`. Penalties are calculated from cumulative research history, not single-run configuration count.

---

## 13. Research Ledger Specification (`hypotheses.jsonl`)

Hypotheses are formal, immutable records:

```json
{
  "hypothesis_id": "H-0192",
  "parent_hypothesis": "H-0145",
  "created_by": "agent:scout-volatility",
  "created_at_run": "RUN-20260819-BTC-001",
  "status": "SUPPORTED",
  "claim": "bollinger_breakout LONG suffers from premature stop loss in HIGH_VOLATILITY regime.",
  "preregistered_test": {
    "cohort_filter": "expert == 'bollinger_breakout' and direction == 'LONG' and regime == 'HIGH_VOL'",
    "counterfactual_variant": "stop_multiplier = 1.5",
    "primary_metric": "net_expectancy_R",
    "required_n": 100,
    "significance_threshold_p": 0.01
  },
  "evidence_for": [
    "Cohort N=342, baseline net_R = -0.14R, counterfactual net_R = +0.08R (bootstrap p=0.004).",
    "38.4% of stopped trades achieved +1.0R post-stop MFE."
  ],
  "evidence_against": [
    "Max drawdown increases from 12.4R to 16.8R under wider stop."
  ],
  "falsification_criterion": "Effect must hold with p < 0.05 on untouched Frozen OOS Fold 2.",
  "derived_challengers": ["EXP-V8-CHALLENGER-BB-042"]
}
```

---

## 14. Validation Partitioning: IS -> WFA -> Frozen OOS -> Holdout

Evaluations strictly follow a 4-tier chronological partition hierarchy with purge gaps:

```
  [Development In-Sample] ──► [Walk-Forward Folds 1..N] ──► [Frozen Out-of-Sample] ──► [Final Holdout]
      (Exploration)              (Purged Anchored)             (Single Audit Run)       (Locked Archive)
```

For every boundary, degradation ratios are recorded:
- $\text{Degradation}_{\text{IS}\to\text{WFA}} = 1 - \frac{\text{Sharpe}_{\text{WFA}}}{\text{Sharpe}_{\text{IS}}}$
- $\text{Degradation}_{\text{WFA}\to\text{OOS}} = 1 - \frac{\text{Sharpe}_{\text{OOS}}}{\text{Sharpe}_{\text{WFA}}}$
- $\text{Degradation}_{\text{OOS}\to\text{Holdout}} = 1 - \frac{\text{Sharpe}_{\text{Holdout}}}{\text{Sharpe}_{\text{OOS}}}$

---

## 15. Implementation Risk vs Statistical Validity (2D Matrix)

Statistical robustness and engine correctness are orthogonal axes. A strategy with stellar statistics on a buggy engine is worthless; a perfectly implemented strategy with zero statistical edge is equally unviable.

```
                            STATISTICAL VALIDITY × IMPLEMENTATION VALIDITY
 ┌──────────────────────────────────────┬──────────────────────────────────────────────────────────┐
 │                                      │                  ENGINE CORRECTNESS                      │
 │                                      ├────────────────────────────┬─────────────────────────────┤
 │                                      │ Engine Verified (PASS)     │ Engine Suspect (FAIL)       │
 ├────────────────┬─────────────────────┼────────────────────────────┼─────────────────────────────┤
 │ STATISTICAL    │ Edge Valid (PASS)   │ CANDIDATE PROMOTED         │ BLOCKED / QUARANTINED       │
 │ VALIDITY       │ Edge Invalid (FAIL) │ REJECTED HYPOTHESIS        │ UNINTERPRETABLE / CORRUPT   │
 └────────────────┴─────────────────────┴────────────────────────────┴─────────────────────────────┘
```

V8 maintains a **Minimal Specification Oracle Replay**: A lightweight 20-scenario reference harness verifying canonical gap-throughs, SL/TP collisions, funding settlements, fee calculations, and partial bar fills against the Rust compute core.

---

## 16. Perturbation & Injected Stress Suite

Evaluation includes synthetic stress environments (distinct from historical estimates):

1. **Data Perturbations:** Injected 1-minute bar timestamp shifts, missing funding rate rows, synthetic spread widenings ($2\times..5\times$), random missing bars ($1\%..5\%$).
2. **Market Stress:** Volatility shocks ($1.5\times$), sudden liquidity vacuum ($10\times$ slippage multiplier), prolonged zero-volume periods.
3. **Engine Perturbations:** Dynamic thread reassignment, cold cache evaluation, memory fragmentation stress.

---

## 17. Autonomous Agent Reliability Profile

Autonomous agents operating on the evidence substrate are themselves evaluated for epistemic reliability:

- **Finding Consistency:** Do independent runs of the Scout agent identify the identical failure modes on the same evidence bundle?
- **Attribution Consistency:** Do independent Investigator agents converge on the same root cause?
- **Recommendation Consistency:** Do diagnostic agents propose consistent preregistered challenger configurations?
- **Epistemic Calibration:** When an agent reports `confidence = 0.90`, do $\approx 90\%$ of those findings replicate on subsequent OOS data?
- **Resource Footprint:** Token consumption, tool-call count, and execution latency per confirmed finding.

---

## 18. Structured Finding Schema (`findings.jsonl`)

Findings are formatted as machine-verifiable objects:

```json
{
  "finding_id": "F-08421",
  "scope": {
    "expert": "failed_breakout",
    "side": "SHORT",
    "regime": "HIGH_VOLATILITY"
  },
  "claim": "Current stop geometry truncates positive trade trajectories.",
  "epistemic_status": "SUPPORTED",
  "severity": "HIGH",
  "confidence": 0.88,
  "observations": [
    "31.2% of stopped trades reached +0.5R favorable excursion before hitting stop.",
    "Counterfactual trailing stop (+1.5R initial) improves cohort expectancy by +0.12R."
  ],
  "statistical_evidence": {
    "n": 412,
    "bootstrap_ci": [0.04, 0.19],
    "p_value": 0.011,
    "effect_size_R": 0.12
  },
  "alternative_explanations": [
    "Confounding by high-volatility regime drift.",
    "Intrabar high/low touch ordering ambiguity."
  ],
  "falsifiers": [
    "Effect vanishes in frozen out-of-sample partition.",
    "Effect vanishes under pessimistic intrabar barrier ordering."
  ],
  "supporting_artifacts": [
    "trades.parquet?expert=failed_breakout&side=SHORT",
    "paths/mfe_mae.parquet?id_in=[...]",
    "slices/volatility.parquet"
  ],
  "recommended_next_test": "O-027_ADAPTIVE_STOP_EXPERIMENT"
}
```

---

## 19. Failure Ontology & Taxonomy

Every diagnostic anomaly maps to a strict 9-category ontology:

```
FAILURE TAXONOMY
├── DATA
│   ├── missing_bars
│   ├── timestamp_inversion
│   ├── temporal_leakage
│   └── feature_stale_or_nan
├── SIGNAL
│   ├── zero_edge
│   ├── directional_inversion
│   ├── regime_incompatibility
│   └── overtrigger_chatter
├── ADMISSION
│   ├── excessive_dedup_loss
│   ├── exposure_conflict_block
│   ├── portfolio_heat_saturation
│   └── identity_loss_in_logs
├── EXECUTION
│   ├── excessive_cost_drag
│   ├── slippage_asymmetry
│   ├── gap_through_liquidation
│   └── intrabar_ambiguity
├── EXIT
│   ├── stop_too_tight
│   ├── target_too_tight
│   ├── premature_expiry
│   └── trailing_stop_whipsaw
├── STATISTICS
│   ├── insufficient_sample_n
│   ├── multiple_testing_inflation
│   ├── out_of_sample_collapse
│   ├── null_indistinguishable
│   └── parameter_cliff
├── ENGINE
│   ├── nondeterministic_replay
│   ├── simd_scalar_divergence
│   ├── thread_race_condition
│   └── accounting_imbalance
├── PORTFOLIO
│   ├── cross_expert_correlation
│   ├── asset_concentration
│   └── simultaneous_drawdown
└── UNCLASSIFIED_NEW_FAILURE_CLASS
```

---

## 20. Cross-Run Regression Analysis

Every evaluation automatically computes a differential delta vector against reference benchmarks:

$$\Delta \text{Run} = \text{Current Run} - \text{Reference Run} \quad (\text{Reference} \in \{\text{Prior Run}, \text{Baseline Locked}, \text{Production Candidate}\})$$

Key delta indicators:
- $\Delta \text{Net Expectancy } (R)$
- $\Delta \text{Max Drawdown } (R)$
- $\Delta \text{Cost Sensitivity Slope}$
- $\Delta \text{OOS Stability Index}$
- $\Delta \text{Signal Funnel Conversion } (\%)$
- $\Delta \text{Compute Runtime } (\text{ms/bar})$
- $\text{Bit-level Semantic Drift Check } (\text{PASS} / \text{DRIFT})$

---

## 21. Additive Performance Decomposition

Performance shifts between runs are mathematically decomposed into constituent contributions without claiming unfounded causal interventions:

$$\Delta \mathbb{E}[R]_{\text{total}} = \Delta \mathbb{E}[R]_{\text{exit\_geometry}} + \Delta \mathbb{E}[R]_{\text{cost\_model}} + \Delta \mathbb{E}[R]_{\text{direction\_mix}} + \Delta \mathbb{E}[R]_{\text{regime\_distribution}} + \epsilon_{\text{residual}}$$

```
  +0.100 R Total Improvement
  ├── +0.041 R (Exit geometry change)
  ├── +0.028 R (Updated realistic cost model)
  ├── +0.017 R (Directional weighting balance)
  ├── +0.009 R (Favorable regime shift)
  └── +0.005 R (Residual unexplained variance)
```

---

## 22. Hard Validity Gates vs Scores (Fail-Closed)

High-severity data and implementation integrity failures are **never averaged into composite scores**. They trigger immediate, non-negotiable **FAIL-CLOSED** termination:

```
if TEMPORAL_LEAKAGE_DETECTED           == TRUE -> VERDICT = INVALID_RUN
if ACCOUNTING_CONSERVATION_MISMATCH    == TRUE -> VERDICT = INVALID_RUN
if NONDETERMINISTIC_REPLAY_HASH        == TRUE -> VERDICT = INVALID_RUN
if SIMD_SCALAR_PARITY_DIVERGENCE       == TRUE -> VERDICT = INVALID_RUN
if CORRUPT_STATE_CACHE_DETECTED        == TRUE -> VERDICT = INVALID_RUN
if BROKEN_COST_MODEL_OR_MISSING_FEE   == TRUE -> VERDICT = INVALID_RUN
```
Only runs passing all Hard Validity Gates are admitted into statistical and economic interpretation.

---

## 23. Semantic Drift Gate & Change Attribution

When automated repair or optimization code is submitted, V8 classifies the modification:

1. **BUG_FIX:** Fixes an implementation defect without altering defined strategy math. Must reproduce identical signals on clean canonical inputs.
2. **IMPLEMENTATION_OPTIMIZATION:** SIMD, memory, or threading speedup. Must maintain $100\%$ bit-exact trace identity.
3. **SEMANTIC_STRATEGY_CHANGE:** Alters indicator thresholds, entry/exit logic, or filters. Requires a fresh preregistered hypothesis and resets multiple-testing trial counters.
4. **NEW_CHALLENGER:** Introduces a novel behavior family or machine-learned scoring model.

---

## 24. Multi-Agent Investigation Architecture

```
                       RUST ENGINE EVALUATION
                                 │
                                 ▼
                     IMMUTABLE EVIDENCE BUNDLE
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
      Deterministic Audit               Schema Builder
     (Invariants, Parity)            (Distributions, Stats)
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                           TRIAGE AGENT
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
             Scout A          Scout B         Scout C
          (Exit Paths)       (Regimes)       (Engine/Data)
                 │               │               │
                 └───────────────┼───────────────┘
                                 ▼
                          HYPOTHESIS POOL
                                 │
                                 ▼
                       INVESTIGATOR AGENTS
                 (Full Corpus Statistical Proof)
                                 │
                     [Confirmed / Refuted / Inconclusive]
                                 │
                                 ▼
                           FINDING GRAPH
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
         Human HTML Report              Machine Evidence API
         (Viewport View)                (Autonomous Queries)
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                          DECISION AGENT
                 (KEEP / REPAIR / NEW CHALLENGER)
```

---

## 25. Tiered Computation & Caching Budget

To maintain rapid development cycles without burning excessive compute, analytical tasks are partitioned into four operational tiers:

```
┌────────┬─────────────────────────┬──────────────────────────────────────────────────────────┐
│ Tier   │ Execution Trigger       │ Workloads & Invariants                                   │
├────────┼─────────────────────────┼──────────────────────────────────────────────────────────┤
│ Tier 0 │ Every commit / run      │ Invariants, accounting conservation, basic economics,   │
│        │ (Mandatory, < 2 sec)    │ per-expert metrics, MFE/MAE, bit-exact cross-run diff.   │
├────────┼─────────────────────────┼──────────────────────────────────────────────────────────┤
│ Tier 1 │ Content-Addressed Cache │ Stationary bootstrap, return permutations, 10 nulls,     │
│        │ (On hash change, < 30s) │ cost surfaces, exit surfaces, markouts.                  │
├────────┼─────────────────────────┼──────────────────────────────────────────────────────────┤
│ Tier 2 │ Hypothesis-Driven       │ Expensive counterfactual replays, multidimensional       │
│        │ (Agent request, < 5m)   │ parameter surfaces, WFA fold evaluation, perturbations.  │
├────────┼─────────────────────────┼──────────────────────────────────────────────────────────┤
│ Tier 3 │ Promotion Gate Only     │ True untouched Frozen OOS opening, PBO/DSR/SPA tests,    │
│        │ (Candidate certification)│ multi-environment reference parity, holdout burn.        │
└────────┴─────────────────────────┴──────────────────────────────────────────────────────────┘
```

---

## 26. Canonical Human Report Structure (Sections A through W)

The human-facing `report.html` renders a 23-section executive view:

- **Section A — Run Identity & Provenance:** Hashes, git commit, binary identity, input tape, platform.
- **Section B — Validity Gates:** Pass/Fail status on all hard integrity and parity gates.
- **Section C — Data Integrity:** Temporal integrity, missing bars, feature census, NaN/Inf checks.
- **Section D — Execution Conservation:** Step-by-step funnel accounting conservation equations.
- **Section E — Portfolio Economics:** High-level returns, net vs gross $R$, Sharpe, Sortino, Calmar.
- **Section F — Expert Scoreboard:** Comparative table of all active and candidate behavior experts.
- **Section G — Expert Deep Forensics:** Per-expert signal-to-trade attrition and conversion paths.
- **Section H — Trade Path Analysis:** Intrabar MFE/MAE trajectories, barrier touch sequences, time-to-excursion.
- **Section I — Cost & Execution Surface:** Sensitivity curves across fees, slippage, and funding rates.
- **Section J — Exit Counterfactuals:** Comparative response curves for alternative stop, target, and expiry rules.
- **Section K — Regime / Slice Diagnostics:** Performance partitioned by Volatility, Trend, TOD, and Liquidity.
- **Section L — Statistical Evidence:** Stationary bootstrap confidence intervals and permutation tests.
- **Section M — Multiple Testing & Research Debt:** Lifetime trial counter, White's Reality Check, and DSR.
- **Section N — WFA / OOS Stability:** Chronological walk-forward fold consistency and degradation metrics.
- **Section O — Parameter Fragility:** Parameter neighborhood cliffs, plateau width, and fragility index.
- **Section P — Engine Correctness:** Thread parity, SIMD parity, and reference oracle differential checks.
- **Section Q — Stress & Perturbation:** Performance degradation under synthetic market and data faults.
- **Section R — Cross-Run Regression:** Delta metrics vs prior run, baseline, and production target.
- **Section S — Failure Attribution:** Ontological taxonomy mapping and root-cause localization.
- **Section T — Confirmed Findings:** Machine-verified statistical conclusions from Investigator agents.
- **Section U — Refuted Hypotheses:** Preregistered claims formally disproven on the corpus.
- **Section V — Unknowns & Epistemic Gaps:** Inconclusive queries requiring further data or instrumentation.
- **Section W — Recommended Experiments:** Formally preregistered challenger specifications for subsequent iterations.

---

## 27. Integration with Target V8 Oracle Architecture (`TARGET_ORACLE_SPEC` v1.0)

The `v8.eval.v1` evaluation evidence substrate operates as the empirical and agentic verification foundation for the 3-Oracle taxonomy (`PARITY_ORACLE`, `HINDSIGHT_ORACLE`, `TARGET_ORACLE`):

1. **Opportunity Universe & Scout Agent Grounding:**
   - Autonomous Scout Agents formulate behavioral hypotheses not solely against existing Expert Candidate logs, but against the versioned **Opportunity Universe** ($U_v(t)$) generated from PIT MarketState primitives.
   - The metric `RepresentationalCoverageGap` (the ratio of hindsight opportunities captured by active Experts vs the Opportunity Grammar) serves as the primary anomaly detection trigger for Triage and Scout agents.

2. **Counterfactual Identifiability & Authority Governance:**
   - All counterfactual artifacts generated within `robustness/` and `paths/` are strictly bound to their Counterfactual Authority status (`IDENTIFIED`, `PARTIALLY_IDENTIFIED`, `MODEL_DERIVED`, `NOT_IDENTIFIABLE`) across execution levels ($L1, L2, L3, \text{LIVE\_RECEIPT}$).
   - The Hard Validity Gates (Section 22) reject any promotion or ranking claim where counterfactual evidence exceeds its declared authority level (e.g., attempting to promote an L1 bar-replay finding as an L3 reactive impact result).

3. **Harmonization of Failure Ontology (Section 19) & Regret Attribution:**
   - The 9-category Failure Ontology directly feeds the 7-domain Non-Additive Regret Attribution tree:
     - `DATA` & `SIGNAL` failures $\rightarrow$ **Detection Regret & Representation Regret**
     - `ADMISSION` failures $\rightarrow$ **Selection Regret & Allocation Regret**
     - `EXIT` failures $\rightarrow$ **Geometry Regret**
     - `EXECUTION` failures $\rightarrow$ **Execution Regret**
     - Unexplainable variance / unrecoverable components $\rightarrow$ **Irreducible Regret**

4. **Audit Viewport Alignment (Sections A–W):**
   - **Section S (Failure Attribution)** outputs the `RegretAttributionRecord` with isolated and marginal component effects.
   - **Section V (Unknowns & Epistemic Gaps)** explicitly renders all `UNKNOWN` and fail-closed refusal outcomes as first-class epistemic receipts.
   - **Section W (Recommended Experiments)** emits `DeploymentCertificate` candidates and preregistered challenger definitions for subsequent promotion stages.
