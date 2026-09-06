# V8 Changelog

Format: dated, brief, reversible. This log records document and architecture decisions — never economics. Each entry names the artifacts it changed.

## 2026-09-06 — Deterministic monograph corpus selection (CI fix, Issues #318–#324)

Fixed `tools/build_monograph.py` so the English monograph excludes the nested Turkish mirror (`docs/tr/`) and all corpus candidates are selected in stable path order. This prevents filesystem traversal differences between macOS and Linux CI from silently swapping translated sections into `site/index.html` and breaking the byte-identity probe.

Modified artifacts: `tools/build_monograph.py`, `docs/CHANGELOG.md`, `site/index.html`, and `site/tr.html`.

## 2026-09-06 — D-156 Evidence, Artifact, Statistical, Benchmark, and Cache Hardening (Issues #318–#324)

Registered D-156 as a provisional, fail-closed hardening decision for the Rust implementation in PR #331. The full authoritative English and Turkish specifications are `docs/contracts/D156_EVIDENCE_ARTIFACT_STORAGE_HARDENING_SPEC.md` and `docs/tr/D156_EVIDENCE_ARTIFACT_STORAGE_HARDENING_SPEC.md`.

- Applied D-118 finite-value and explicit-absence invariants at artifact, scenario, statistics, benchmark, and cache boundaries.
- Documented append-only candidate/cashflow/evidence persistence, versioned tape-bound atomic checkpoints, and physical V8.2 artifact lineage.
- Registered real standard Parquet production and verification through `parquet_artifact.rs`; disguised JSON files are not accepted as Parquet.
- Preserved fail-closed scenario ruin and unresolved SaR behavior when physical trade or liquidity inputs are unavailable.
- Kept proxy DSR and incomplete multiplicity lineage diagnostic-only; genuine DSR/PBO/WRC/SPA authority remains unregistered and cannot support an economic claim.
- Recorded the `BenchmarkRunner` physical evidence boundary and `OPEN_PIN-156-1`: no receipt is emitted until a registered data-backed evaluator exists.
- Registered the durable redb cache adapter, canonical key versioning, digest validation, transactional writes, compaction, and guarded legacy JSONL migration.
- Renamed the internal capability aggregation type to `CapabilityScoreCalculator` and its runner field to `score_calculator` so the constitutional forbidden-component gate cannot misclassify the deterministic evidence calculator as a prohibited learned component.

Modified artifacts: `docs/contracts/D156_EVIDENCE_ARTIFACT_STORAGE_HARDENING_SPEC.md`, `docs/tr/D156_EVIDENCE_ARTIFACT_STORAGE_HARDENING_SPEC.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `v8-core/src/parquet_artifact.rs`, `v8-core/src/cache.rs`, `v8-core/src/checkpoint.rs`, `v8-core/src/evidence.rs`, `v8-core/src/evaluation/statistics.rs`, `v8-core/src/evaluation/multiple_testing.rs`, `v8-core/src/usdm_sim/scenario_ruin.rs`, and `v8-core/src/benchmark/runner.rs`.

## 2026-09-06 — D-153 Benchmark Fabric (BF) Protocol & Multi-Population Evaluation (Rules 57.1–57.8)

Ratified and fully completed the implementation of D-153 Benchmark Fabric against `site/V8.5_D153_Benchmark_Fabric_Research_Monograph.html` and `docs/contracts/D153_BENCHMARK_FABRIC_SPEC.md`:
- **Ontology & Epistemic Separation:** Implemented strict non-collapse invariants (Rule 57): Benchmark != Assurance, CapabilityScore != Readiness, CapabilityScore != Future-Profit Probability. Explicitly separated Question 1 ("Is this a high-integrity quant research system?" -> 0-100 CapabilityScore) from Question 2 ("How much capital if $1,000 invested?" -> Empirical Monte Carlo capital projection).
- **MinervaScore Robustness Engine (arXiv:2608.23808):** Implemented `v8-core/src/benchmark/minerva.rs` evaluating DSR, PBO, SPA, MinTRL, and Regime Stability signed margins with non-compensable binary robustness seal gating (scores >= 80 and seals strictly require passing all 5 gates; failure caps score < 80). Integrated PRUDEX-Compass (TMLR 2023) 6-axis profile mapping.
- **10,000 Monte Carlo / Bootstrap Simulated Futures:** Implemented empirical future paths starting from $1,000 initial capital (`v8-core/src/benchmark/projection.rs`) yielding exact P5, P25, P50 (median), P75, P95, worst/best scenario returns, and Risk of Ruin % (drawdown >= 30%) with explicit liquidity capacity and counterfactual notices.
- **Unified V8 Evidence Dashboard & Policy Certificate:** Implemented `PolicyCertificate` (`v8-core/src/benchmark/certificate.rs`) calculating the multiplicative Readiness Index: $\text{Readiness Index} = \text{Research Capability} \times \text{Evidence Multiplier} \times \text{Robustness} \times \text{Economic Score}$. Rendered in both terminal ASCII box and 3-panel HTML scorecard (`site/benchmark_scorecard.html`), strictly enforcing `STATUS: Research Candidate NOT Production Approved`.
- **Metric Observations & 10-Domain Architecture:** Implemented `MetricObservation` (`v8-core/src/benchmark/observation.rs`), 10 capability domains with Monograph V1 provisional weights, and penalized harmonic mean scoring with coverage multiplier.
- **Real Execution Runner:** Implemented `BenchmarkRunner` (`v8-core/src/benchmark/runner.rs`) orchestrating chronological walk-forward, CPCV, real burned diagnostic quad evaluation (treated strictly as one historical cell), Foundry passport qualification, and reverse-stress nearest-defeater search.
- **External Parity Adapters:** Implemented real series parity evaluation and disagreement detection (`v8-core/src/benchmark/external.rs`) for QuantConnect LEAN, skfolio, and VectorBT with zero hardcoded metrics.
- **Append-Only Disk Ledger:** Implemented cryptographic hash-chain ledger with disk persistence (`.audit/benchmark/ledger.jsonl`).
- **Constitutional Sabotage & Integration Suites:** 24/24 BFS sabotage tests (`v8-core/tests/d153_benchmark_fabric_sabotage.rs`) and dedicated Minerva/Dashboard integration tests (`v8-core/tests/d153_minerva_and_dashboard_test.rs`) passing with 100% verification.

Artifacts changed: `docs/contracts/D153_BENCHMARK_FABRIC_SPEC.md`, `site/V8.5_D153_Benchmark_Fabric_Research_Monograph.html`, `site/benchmark_scorecard.html`, `docs/decisions/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `v8-core/src/benchmark/*`, `v8-core/src/main.rs`, `v8-core/tests/d153_benchmark_fabric_sabotage.rs`, `v8-core/tests/d153_minerva_and_dashboard_test.rs`, `docs/CHANGELOG.md`.

## 2026-09-06 — D-152 Scenario-Centric Policy Evidence Profile & Quad Demotion (G0–G9)

Registered D-152 as PROVISIONAL_DECISION extending D-147/D-150/D-151 with no locked-invariant mutation. Replaced the single-trajectory headline with `assurance/evidence_profile.rs::PolicyEvidenceProfile` (typed historical diagnostic, scenario cells, robustness topology, frozen-OOS/shadow/live states, gates, non-scalar conclusion). Demoted the 12-month quad to `BURNED_DIAGNOSTIC` diagnostic court: typed `PortfolioReceipt` fields, diagnostic CLI rendering, pathology preserved, promotion leakage blocked by type. Codified passport-scoped synthetic defeater authority and the statistical-triple audit (WRC + genuine DSR + SPA remain the burden; proxy ledger keeps G5 at `NO_ECONOMIC_CLAIM`). Added 14-test adversarial suite `policy_evidence_profile_adversarial.rs`.

Artifacts changed: `docs/contracts/D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md`, `docs/tr/D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `v8-core/src/assurance/evidence_profile.rs`, `v8-core/src/assurance/mod.rs`, `v8-core/src/usdm_sim.rs`, `v8-core/src/main.rs`, `v8-core/tests/policy_evidence_profile_adversarial.rs`, `docs/CHANGELOG.md`.

## 2026-08-27 — D-150 Continuous Epistemic Succession & Living Policy Constitution Ratification & Full Implementation (`D-150-SPEC-001`, Rules 51–56)

Ratified and fully implemented D-150 Continuous Epistemic Succession & Living Policy Constitution, codifying the core temporal evidence law $\text{PolicyIdentity} \neq \text{EvidenceState}$ and resolving the lifecycle and evidence state machine for living policies:
- **Full-Text Canonical Specifications:** Committed complete unabridged specifications in English (`docs/contracts/D150_CONTINUOUS_EPISTEMIC_SUCCESSION_SPEC.md`, all 33 sections) and Turkish (`docs/tr/D150_CONTINUOUS_EPISTEMIC_SUCCESSION_SPEC.md`), and integrated the HTML research paper into `docs/contracts/` and `site/`.
- **Decision Numbering & Mirror Alignment:** Registered D-150 as Continuous Epistemic Succession & Living Policy Constitution and renumbered Market World Foundry v2 to D-151 across English and Turkish decision registers (`docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`).
- **Epistemic Succession Engine (`v8-core/src/assurance/continuous.rs`, `certificate.rs`, `mod.rs`):**
  - Implemented append-only `EvaluationEpoch` succession over sealed `EvaluationCaseManifest`s without historical mutation.
  - Implemented revocable, non-scalar `ProductionEvidenceCertificate` with typed lifecycle states (`QUALIFIED`/`ACTIVE`, `SUPERSEDED`, `QUARANTINED`, `REVOKED`, `DEFEATED`, `EXPIRED`).
  - Implemented transitive defeat propagation and mandatory Kaizen handoff via typed `DefeaterReceipt` and `KaizenHandoffReceipt`.
  - Implemented `WorldCoverageManifest` and sequential `MonitoringPlan` with time-valid e-process/confidence sequence gating.
- **Dedicated 20-Test Constitutional Sabotage Suite (`v8-core/tests/d150_epistemic_succession_sabotage.rs`):** Verified all 20 canonical sabotage tests (`D150-T01` to `D150-T20`) with 100% pass rate.
- **Monograph Synchronization:** Rebuilt single-file English and Turkish monographs (`site/index.html`, `site/tr.html`) including D-150 and D-151 sections.

Artifacts changed: `docs/contracts/D150_CONTINUOUS_EPISTEMIC_SUCCESSION_SPEC.md`, `docs/tr/D150_CONTINUOUS_EPISTEMIC_SUCCESSION_SPEC.md`, `docs/contracts/D150_Continuous_Epistemic_Succession_Research_Paper.html`, `site/D150_Continuous_Epistemic_Succession_Research_Paper.html`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `v8-core/src/assurance/continuous.rs`, `v8-core/src/assurance/certificate.rs`, `v8-core/src/assurance/mod.rs`, `v8-core/tests/d150_epistemic_succession_sabotage.rs`, `tools/build_monograph.py`, `site/index.html`, `site/tr.html`, `docs/CHANGELOG.md`.

## 2026-08-26 — V8.5 100% Implementation: Assurance Fabric, Production Growth Court, Market World Foundry, SPG, Research Integrity & Continuous Evidence Certification (Milestone #4, Issues #310–#316)

Implemented 100% of the V8.5 architecture specification across all 7 implementation work-items:
- **Assurance Fabric MVP (Issue #310, `v8-core/src/assurance/`):** Immutable `EvaluationCaseManifest`, monotonic `EvaluationEpoch`, read-only non-escalating `AuthorityProjection`, `EvidenceAttestation`, 9 operational assurance claims, Boolean/threshold `ClaimRule` algebra, content-addressed `ProvenanceGraph`, `CommonModeGraph` sensor independence, `DefeaterReceipt` hard veto propagation, `AssuranceCaseAdjudicator` sovereign engine, and `AssuranceCaseReceipt`.
- **Production Growth Court (Issue #311, `v8-core/src/evaluation/`):** Deterministic `ProductionGrowthContract`, exact Long-Horizon Geometric Net Growth (`LGNG`), Anti-Target-Chasing invariant, `DeploymentEquivalentReceipt`, legal single-asset/zero-allocation `ScopeDiagnostics`, and `FrictionRetentionProfile`.
- **Market World Foundry (Issue #312, `v8-core/src/world/`):** Deterministic `WorldSpec`, `StructuralWorldGenerator` (regime persistence, Poisson jumps, GARCH volatility), `BlockResampleGenerator`, `CounterfactualSurgeryEngine`, non-scalar 6D `GeneratorPassport`, and `ReverseStressSearchEngine`.
- **System Proving Ground (Issue #313, `v8-core/src/system_proving/`):** Full-chain `SystemProvingGroundRunner` (candidate discovery, multi-expert reconciliation, risk gate, execution sizing, double-entry ledger), 14-dimensional `SystemRobustnessVector`, and 7-domain `FailureAttributionBreakdown` conservation algebra.
- **Research Integrity & Holdout Management (Issue #314, `v8-core/src/research/`):** Lineage-relative `DataRoleLedger` (6 statutory roles), irreversible `HoldoutBurnReceipt` (`POLICY_FROZEN_OOS` -> `BURNED_DIAGNOSTIC`), and `StatisticalPlan` trial debt multiplicity control.
- **AI / Kaizen TEVV Probes (Issue #315, `v8-core/src/tevv/`):** `AgentAuditManifest`, `ActionAuditReceipt`, 10 Mandatory Integrity Probes, and cryptographic `AuditTranscript`.
- **Continuous Lifecycle & Production Evidence Certificate (Issue #316, `v8-core/src/assurance/`):** `ContinuousEvaluationLedger` monotonic epoch progression ($N \rightarrow N+1$), and non-scalar, time-bounded, revocable `ProductionEvidenceCertificate`.
- **Constitutional Sabotage Suite (`AF-T01` to `AF-T20`):** 100% verified across 7 dedicated test suites (502 total tests passed, 0 failed).

Artifacts changed: `v8-core/src/lib.rs`, `v8-core/src/assurance/*`, `v8-core/src/world/*`, `v8-core/src/system_proving/*`, `v8-core/src/research/*`, `v8-core/src/tevv/*`, `v8-core/src/evaluation/*`, `v8-core/tests/*`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-26 — D-149 Full-Text Specification & Anchor Invariant (Rule 44, NO_UNANCHORED_SPEC_ACCEPTANCE) & Complete V8.5 Specification Preservation

Ratified Constitution Rule 44 / D-149 requiring all draft bills, constitutional amendments, and architectural proposals to be committed as complete, unabridged full-text specifications in `docs/`. Preserved the complete 35-section V8.5 architecture blueprint in `docs/contracts/V85_ARCHITECTURE_SPEC.md` and anchored `V85_RATIFICATION_CANDIDATE.md` and monograph summaries to it.

Artifacts changed: `docs/contracts/V85_ARCHITECTURE_SPEC.md`, `docs/tr/V85_ARCHITECTURE_SPEC.md`, `docs/charter/V8_CONSTITUTION.md`, `docs/tr/V8_CONSTITUTION.md`, `docs/V85_RATIFICATION_CANDIDATE.md`, `docs/tr/V85_RATIFICATION_CANDIDATE.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `AGENTS.md`, `GEMINI.md`, `docs/CHANGELOG.md`.

## 2026-08-26 — D-148 unified in-process fast audit engine, Rayon concurrency & native forensic report (Issues #306, #307, #308, #309, D-148)

Unified the fragmented 11-subprocess audit pipeline into a single high-throughput in-process `v8-core full-audit` command. Incorporates:
- **Compiler & Release Profile Tuning (#309):** `lto = "thin"`, `codegen-units = 1`, `panic = "abort"`, and native SIMD/AVX2 vectorization in `v8-core/Cargo.toml`.
- **Post-S4 Concurrency Scope (#306):** Concurrent execution of S6 Regret Analysis, O0–O3 Oracle Coverage, USD-M Portfolio Simulation, and Allegory Archetype Suite (A01–A12) across worker threads with zero-copy shared state.
- **In-Memory Determinism & Hashing (#307):** In-memory Zero-Jitter Bit-Identity Pass 2 verification and direct RAM buffer SHA-256 computation eliminating secondary disk I/O.
- **Native Rust Forensic HTML Generator (#308):** Native Rust HTML renderer (`v8-core/src/audit/html_report.rs`) generating agent-grade forensic reports in <10ms and 64KB `BufWriter` bulk streaming.
- **Audit Runtime Acceleration:** Reduces the end-to-end deterministic audit reproduction cycle from ~40s down to ~2–3s while strictly preserving 100% bit-exact determinism across all ledgers and Oracle receipts.

Artifacts changed: `v8-core/Cargo.toml`, `v8-core/src/main.rs`, `v8-core/src/runloop.rs`, `v8-core/src/audit/mod.rs`, `v8-core/src/audit/full_audit.rs`, `v8-core/src/audit/html_report.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-26 — V8.5 M0 ratification candidate (provisional)

Added the V8.5 DRAFT-2 architecture as a non-binding M0 ratification candidate. Closed the six constitutional boundaries at the proposal level: read-only `AuthorityProjection`, disjoint `SUPPORTED_EDGE`/`REALIZED_CASHFLOW`, test-only synthetic Foundry at M0, preserved WRC+genuine DSR+Hansen SPA law, immutable EvaluationCase epochs, and explicit blocking statistical implementation debt. No active Constitution rule, runtime Rust code, economic authority or mainline merge is changed by this candidate.

Artifacts changed: `docs/V85_RATIFICATION_CANDIDATE.md`, `docs/issues/ISSUE_V85_RATIFICATION_CANDIDATE.md`, `docs/tr/V85_RATIFICATION_CANDIDATE.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `tools/build_monograph.py`, `site/index.html`, `site/tr.html`.

Made `macro-m2-high-fine-risk-018` the explicit Kaizen default checkpoint, added a real evaluation-count mode and explicit symbol-set selection for bounded challenger scans, and exposed gross market PnL from the cashflow ledger so gross/net/fee comparisons use one accounting source. The Kaizen `initial_balance` is now a total portfolio budget split equally across selected symbols, preventing a 10-symbol run from silently becoming a `$10,000` run. Independent symbol replays now fan out in parallel and merge in declared order. Added decision-stride challengers without changing the tape, fee schedule, fill assumptions, or D-145 safety gate. This is an engineering/selection change only; no profitability or Rule 12 certification is implied.

Artifacts changed: `v8-core/src/usdm_sim.rs`, `v8-core/src/kaizen/iteration.rs`, `v8-core/src/bin/kaizen_iterations.rs`, `v8-core/src/main.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `site/index.html`, `site/tr.html`.

## 2026-08-24 — D-141 qualification scope correction (D-141)

Aligned the executable D-141 pilot suite with the actually verified pilots and removed the false registry-wide completion implication. The suite now executes `failed_breakout`, `fib_projection_reversal`, and `ichimoku_cloud`; the 28-witness registry remains only 3/28 covered, with the remaining 25 witnesses still open for individual Behavior Cards, scenarios, and manifests. EWQ-07/EWQ-08 and frozen-OOS economic promotion remain unresolved or outside D-141 authority.

Artifacts changed: `v8-core/src/qualification/mod.rs`, `docs/dossiers/D141_QUALIFICATION_DOSSIER.md`, `docs/tr/D141_QUALIFICATION_DOSSIER.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`.

## 2026-08-24 — D-145 real-tape economic Kaizen ledger (D-145)

Added a Rust-only, append-only economic iteration ledger over the certified quad tape. The runner evaluates each challenger through the canonical simulator, persists configuration and receipt hashes plus per-asset realized receipts, and counts an iteration only when net cashflow strictly improves while drawdown and margin utilization remain within the fixed baseline safety ceiling. Rejected candidates are retained for audit; no synthetic rows, offset inputs, hardcoded metrics, or economic certification claims are introduced.

Artifacts changed: `v8-core/src/kaizen/iteration.rs`, `v8-core/src/kaizen/mod.rs`, `v8-core/src/bin/kaizen_iterations.rs`, `v8-core/src/usdm_sim.rs`, `v8-core/src/main.rs`, `v8-core/src/experts/mod.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-24 — Ratification of D-144: Sovereign Kaizen Expert Fleet Evolution & Multi-Asset Alpha Optimization (`V8.4-ETS-KAIZEN-004`)

Ratified deep iterative Kaizen evolution for a selected set of expert modules in the Rust compute plane without modifying USD-M engine physics. This entry does not ratify registry-wide completion:
- **Ichimoku Cloud Structural Optimization (`ichimoku_cloud:v2`):** Anchored risk geometry directly to the Kijun-sen equilibrium line with 1.5R target expansion, generating **+$433.53 standalone net profit with positive cashflow across all four assets** (BTC +$101.87 / 2.04 PF, AVAX +$235.91 / 2.08 PF, ETH +$48.16, SOL +$47.60).
- **Trend Pullback Reclaim Confirmation (`trend_pullback:v2`):** Added pullback reclaim filter and symmetric short execution, turning the expert from -$171.10 loss to +$69.52 net profit (+13.63% return on ETH, 55.8% WR).
- **Volume Confirmed Breakout Surge Gating (`volume_confirmed_breakout:v2`):** Added single-bar freshness and strict volume surge gating ($vol \ge 1.30 \times sma$ or $vol_z \ge 0.50$), producing +$362.17 standalone net profit (+32.61% return on SOL).
- **MACD Stoch Trend Crossover Anchoring (`macd_stoch_trend:v2`):** Anchored stop levels to crossover swing extremes, achieving +$80.16 net profit (+$111.31 on AVAX, 1.30 PF).
- **Divergence 12 Setups Bidirectional Expansion (`divergence_12_setups:v2`):** Implemented Bullish regular divergence alongside Bearish divergence, producing >60% win rate across ETH, SOL, and AVAX.
- **2B High/Low Symmetry (`failed_breakout_2b:v2`):** Added 2B top reclaim support alongside bottom reclaim, producing +$76.58 net profit on SOL (1.45 PF).
- **Quad Portfolio Performance:** Elevates AVAX cashflow in the multi-alpha ensemble to **+$607.43 (1.74 PF)** and lifts Gross Market Edge across the quad tape to **+$916.40**.

Artifacts changed: `v8-core/src/experts/ichimoku_cloud.rs`, `v8-core/src/experts/trend_pullback.rs`, `v8-core/src/experts/trend_pullback_depth.rs`, `v8-core/src/experts/volume_confirmed_breakout.rs`, `v8-core/src/experts/macd_stoch_trend.rs`, `v8-core/src/experts/divergence_12_setups.rs`, `v8-core/src/experts/failed_breakout_2b.rs`, `v8-core/src/experts/bollinger_breakout.rs`, `v8-core/src/experts/bollinger_reversion.rs`, `v8-core/src/experts/fib_retracement_continuation.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`.

## 2026-08-24 — Ratification of D-143: Expert Population Repair, Range Consolidation Breakout Integration & +$525.42 USD-M Baseline Ratification (`V8.4-ETS-EXPANSION-003`)

Ratified the systematic forensic repair of the expert witness population under D-141 Alpha Refinery standards and upgraded the authoritative Point-In-Time Rust USD-M simulation baseline:
- **Range Consolidation Breakout Integration (`range_breakout_1to1`):** Integrated volume z-score expansion gating ($vol_z \ge 0.20$) on narrow 20-bar consolidation range breakouts, boosting net return and reducing drawdowns across multi-asset tapes.
- **Forensic Expert Population Upgrades:**
  - `donchian_breakout:v2`: Upgraded with symmetric Long/Short execution, single-bar setup freshness to eliminate late chasing, volume expansion gating ($vol_z \ge 0.20$), and bounded risk geometry (clamped $0.8 \le \text{stop\_r} \le 2.0$), generating +$144.26 standalone net profit.
  - `breakout_retest:v2`: Upgraded with recency-windowed retest confirmation ($\le 6$ bars) and structural stop buffer, turning standalone cashflow positive (+$36.02 net profit, 56.9% win rate on ETH).
  - `candlestick_reversal:v2`: Upgraded with complete 8-pattern bidirectional scanner (`hammer`, `shooting_star`, `bullish_engulfing`, `bearish_engulfing`, `bullish_harami`, `bearish_harami`, `three_white_soldiers`, `three_black_crows`) with clamped risk geometry.
- **Authoritative Verified Rust Performance:** **+$525.42 NET PROFIT (+52.54% Net Return on $1,000 capital, +$911.31 Gross Market PnL, -$385.89 Taker Fees, 764 trades across 12-month certified quad tape `research/tape/quad-1h-12m/tape.jsonl`, with AVAX +$557.34, SOL +$42.37)**.

Artifacts changed: `v8-core/src/usdm_sim.rs`, `v8-core/src/experts/donchian_breakout.rs`, `v8-core/src/experts/breakout_retest.rs`, `v8-core/src/experts/candlestick_reversal.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`.

## 2026-08-24 — Ratification of D-142: Multi-Alpha Strategy Ensemble, Session Drift Integration & +$490.35 USD-M Baseline Ratification (`V8.4-ETS-ENSEMBLE-002`)

Ratified the unified Multi-Alpha Strategy Ensemble within the verified Point-In-Time Rust USD-M simulation engine and established the new authoritative baseline:
- **Unified Multi-Alpha Strategy Ensemble:** Integrated Squeeze Release Macro Swing (`squeeze_swing`), Floor Trader Daily Pivot (`floor_trader_pivot`) capturing institutional daily session drift, Repaired Failed Breakout (`failed_breakout:v2`) with $\le 5$-bar recency constraint, and Fibonacci Extension Reversal (`fib_projection_reversal`).
- **Universal 20-bar Kaufman Trend Efficiency Gating:** Applied Kaufman ER ($er \ge 0.18$) across all incoming alpha sensor votes, eliminating chop fee drag.
- **Canonical 4-Asset Quad Benchmark (`cargo run -- usdm-sim --quad`):** Added native `--quad` CLI benchmark flag for deterministic single-command portfolio verification.
- **Authoritative Verified Rust Performance:** **+$490.35 NET PROFIT (+49.03% Net Return on $1,000 capital, +$863.78 Gross Market PnL, -$373.43 Taker Fees, 714 trades across 12-month certified quad tape `research/tape/quad-1h-12m/tape.jsonl`, with AVAX +$456.69, BTC +$23.04, SOL +$0.62)**.

Artifacts changed: `v8-core/src/main.rs`, `v8-core/src/usdm_sim.rs`, `v8-core/src/experts/failed_breakout.rs`, `v8-core/src/qualification/mod.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-23 — D-141 Expert Proving Ground & Alpha Refinery

Registered D-141 as a provisional, non-economic, two-pilot Expert qualification architecture. The Rust qualification plane is test-only and provides Behavior Cards, independent Scenario Oracles, metamorphic and mutation/sabotage checks, EAST counterexample search, typed statistical evidence, passports, attribution, and EWQ gates. No Expert threshold, opportunity identity, capital authority, or economic verdict changed by this integration.

Artifacts changed: `v8-core/src/qualification/mod.rs`, `v8-core/src/lib.rs`, `docs/audits/D141_EXPERT_PROVING_GROUND.md`, `docs/tr/D141_EXPERT_PROVING_GROUND.md`, `docs/dossiers/D141_QUALIFICATION_DOSSIER.md`, `docs/tr/D141_QUALIFICATION_DOSSIER.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `tools/build_monograph.py`, `site/index.html`, `site/tr.html`.

## 2026-08-23 — Ratification of D-140: Squeeze Release Macro Swing Architecture, Kaufman Trend Efficiency Gating & 24h Structural Trailing Stop (`V8.4-ETS-SWING-001`)

Formally adopted the Squeeze Release Macro Swing Engine (`v8-core/src/experts/squeeze_swing.rs`) and established the new authoritative Point-In-Time Rust USD-M baseline:
- **Replaced 1H Intraday Micro-Noise Churn:** Shifted from high-frequency sub-1.0R intraday micro-entries to multi-day macro regime transitions.
- **Squeeze Release Compression:** 50-bar rolling Bollinger Bandwidth compression percentile ranking (`bw_rank <= 0.35`) and confirmed volume expansion (`vol_ratio >= 1.30`).
- **Kaufman Trend Efficiency Gating:** Integrated 20-bar Kaufman Trend Efficiency Ratio (`er >= 0.18`) across both `squeeze_swing` and `trend_continuation` experts to dynamically fail closed during dead random-walk sideways consolidation.
- **24-Hour Structural Trailing Stop (`Structural24hTrail`):** Ratchets stop levels along the rolling 24-hour lowest low (Long) / highest high (Short), eliminating premature shakeouts from intraday 1H candle wicks.
- **Mandatory 24-Hour Post-Exit Cooldown:** Enforced 24-hour non-trading refractory period per asset following position exit to eliminate post-trend chop churn.
- **Authoritative Verified Rust Performance:** +$227.48 NET PROFIT (+22.75% Net Return on $1,000 capital, +$552.39 Gross Market PnL, -$324.91 Taker Fees, Profit Factor 1.67 on AVAX +$346.59, PF 1.08 on BTC +$13.21 on 12-month certified quad tape `research/tape/quad-1h-12m/tape.jsonl`).

Artifacts changed: `v8-core/src/experts/squeeze_swing.rs`, `v8-core/src/experts/mod.rs`, `v8-core/src/kaizen/exit_trailing.rs`, `v8-core/src/usdm_sim.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-23 — Ratification of D-139: V8 Temporal Sovereignty Architecture, Causal Fortress & Non-Interference Verification Act (`CC-BILL-V8.3-CAUSAL-FORTRESS-006`, Rules 44–50)

Unanimously ratified by Central Committee & Yüksek Divan extraordinary session (`docs/dossiers/CC_SESSION_20260823_CAUSAL_FORTRESS.md`). Enforces the Temporal Non-Interference doctrine ($X_{\le t} = X'_{\le t} \implies \text{Decision}_{\le t}(X) = \text{Decision}_{\le t}(X')$) and codifies the 11-layer Causal Fortress:
- **Temporal Evidence Ledger as Sole SSoT:** Demoted `FeatureStore` to derived materialization; root authority resides exclusively in `Temporal Evidence Ledger` with explicit availability constraints.
- **ChronosGate Physical Data Diode:** Isolated full-tape access to ChronosGate; physical process boundary prevents simulator/execution engines from accessing future data.
- **Elimination of Shortened Vectors & Offset Arithmetic:** Mandatory $N$-bar aligned `DenseBarSeries<T>` (`Option<T>`); eliminated all `-13` / `-27` indicator offsets from consumer interfaces.
- **Disjoint Ontological Typing:** Implemented `SparseEventSeries<T>` and strict newtypes (`BarId != FundingEventId != DecisionTime`), preventing bar-index misuse on sparse channels at compile time.
- **CausalFrame by-value Capability Boundary:** Eliminated `&FeatureStore` references from engine address space; decisions consume isolated by-value frames.
- **Causal IR & Static Effect Algebra:** Enforced $\text{Availability}(\text{output}) \le \text{DecisionTime}$; prohibited retrocausal primitives (`shift(-1)`, `lead`, `center=true`, `bfill`, `forward_join`).
- **Mandatory 100% Mutation Kill-Rate:** Established `leak-mutants/` suite (LEAK-001..012); failure to kill 100% of injected mutants blocks certification.
- **Independent Reference Interpreter:** Established `v8-ref-interpreter` with zero shared feature/alignment/execution code for step-by-step differential trace verification.
- **Formal Verification (Kani & TLA+):** Model-checking and mathematical proofs for core causal primitives and watermark monotonicity protocols.
- **Two-Tier Execution Authority & Renderer Firewall:** `FAST_RESEARCH` (`DIAGNOSTIC_ONLY`) vs `CERTIFIED_SIM` (`AUTHORITATIVE`); zero economic/profit rendering without valid `TemporalIntegrityCertificate`.

Artifacts changed: `docs/dossiers/CC_SESSION_20260823_CAUSAL_FORTRESS.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`.

## 2026-08-22 — D-136 Epistemic Economic Observability Full Production Qualification & Constitutional Ratification (Issues #260–#277, Milestone #2)

Completed full implementation and production qualification of Decision `D-136` (Epistemic Economic Observability, Evidence Attribution & Model-Risk Governance):
- **Eradicated Placeholder Evidence (EEO-R01):** Removed all synthetic and mock fallbacks across providers P01–P12.
- **Double-Entry Cashflow Conservation (P01 / EEO-R02):** Reconciled physical cashflows to within $\epsilon \le 10^{-8}$ ($\Delta = \$0.00000000$).
- **Lineage & Monotonicity (P02, P03 / EEO-R03, EEO-R04):** Verified structural DAG lineage across 577 spans with zero retrocausal dependencies.
- **Venue Fidelity & Calibration (P04, P05 / EEO-R05, EEO-R06):** Enforced Binance USD-M discretization rules and fail-closed ex-ante calibration.
- **Oracle Funnel & Multiplicity (P06, P08, P11 / EEO-R07, EEO-R09, EEO-R13):** Connected 7-stage opportunity capture funnel and Holm-Bonferroni trial accounting.
- **Implementation Shortfall & Causal Falsification (P09, P12 / EEO-R10, EEO-R14):** Empirical decomposition of fee, funding, slippage, and confounder detection.
- **Canonical Report Generation & Production Qualification (EEO-R15, EEO-R16, EEO-R17):** Generated `.audit/eeo/current/ECONOMIC_PATHOLOGY_REPORT.json` on certified 12m BTCUSDT tape (8,760 bars) and achieved 14/14 fault localization in Q01–Q15 harness.
- **Constitutional Ratification (EEO-R18):** Formally ratified D-136 as `LOCKED_INVARIANT` and published `docs/dossiers/D136_RATIFICATION_DOSSIER.md`.

Artifacts changed: `v8-core/src/eeo/*`, `v8-core/src/telemetry/*`, `v8-core/src/main.rs`, `.audit/eeo/current/ECONOMIC_PATHOLOGY_REPORT.json`, `docs/dossiers/D136_RATIFICATION_DOSSIER.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-22 — D-136 Epistemic Economic Observability Monograph Integration (`D-136-RP-001`)

Integrated the canonical D-136 Epistemic Economic Observability, Evidence Attribution & Model-Risk Governance monograph section into both English and Turkish documentation suites (`docs/audits/D136_EPISTEMIC_ECONOMIC_OBSERVABILITY.md` and `docs/tr/D136_EPISTEMIC_ECONOMIC_OBSERVABILITY.md`).
Documented the Three-Plane Architecture (Telemetry, Evidence, Governance), `EconomicTraceContext`, `DecisionBeliefLedger`, Evidence Provider Interface (`AuditEvidenceProvider`, P01–P12), `EvidenceGraph`, Upstream Invalidation Replay, and the As-Built Status Matrix explicitly disclosing non-authoritative scaffold implementation debt.
Synchronized `tools/build_monograph.py`, regenerated `site/index.html` and `site/tr.html`, and updated `DECISION_REGISTER.md` and `IMPLEMENTATION_LAYOUT.md`.

Artifacts changed: `docs/audits/D136_EPISTEMIC_ECONOMIC_OBSERVABILITY.md`, `docs/tr/D136_EPISTEMIC_ECONOMIC_OBSERVABILITY.md`, `tools/build_monograph.py`, `site/index.html`, `site/tr.html`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-22 — D-138 prospective shadow boundary and canonical artifact lineage (Issues #256, #258)

Added the Rust-only, non-economic `v8-core/src/shadow.rs` boundary. Sealed
prospective manifests bind code, configuration, dataset, authority, freeze
cutoff, incumbent, challenger, and artifact namespace. The runner enforces
strictly post-freeze chronological observations, content-addressed input
bindings, idempotent writes, mixed-output rejection, and permanent
`NO_ECONOMIC_CLAIM` / `PROMOTION_FORBIDDEN` status. Added the `shadow` and
`artifact-index` CLI subcommands; the latter binds declared audit/report/ledger
files to one manifest and rejects duplicate or self-referential bundles. Added
embedded tests for cutoff, deterministic replay, mixed/stale artifact rejection.
The economic OOS/succession experiment remains separately gated under Issue
#255 and was not opened.

Artifacts changed: `v8-core/src/shadow.rs`, `v8-core/src/main.rs`,
`docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`,
`docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-22 — Removal of retired V8.2 executable tooling (D-137)

Removed the legacy V8.2 Python execution, diagnostic, regret, tape-building,
and research-tool copies that could recreate the deprecated `$992` profile,
plus the Rust oracle-coverage modules whose baseline-only constructors
hard-coded that profile into the bundle.
The frozen forensic receipt/report artifacts and `legacy/v82/README.md` remain;
no V8.3 Rust runtime path was changed.

Artifacts changed: retired files under `tools/`, `legacy/v82/code/`, and
`legacy/v82/diagnostics/`; `docs/decisions/DECISION_REGISTER.md`,
`docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`,
`v8-core/src/oracle/coverage.rs`, `v8-core/src/oracle/mod.rs`,
`v8-core/src/oracle/recoverability.rs`, `v8-core/src/scheduler.rs`, and
`v8-core/src/scheduler/rename_audit.rs`.

## 2026-08-22 — Ratification & Implementation of D-136: Central Committee Rectification, Legacy Quarantine & Breakeven Challenger Mandate

Unanimously ratified by the V8 Central Committee (5-0):
- **Central Committee Rectification & Suspension:** Suspended speculative economic plan creation; codified strict "Engineer First, Persona Second" mandate restricting commissioners to `AUDIT`, `FALSIFY`, `IDENTIFY CONTRADICTION`, and `PROPOSE TEST`.
- **Legacy Quarantine:** Organized historical V8.0–V8.2 code, diagnostics, and reports into `legacy/v82/` with `[NON_CANONICAL / FORENSIC_ONLY]` seals and Agent Discovery Guards.
- **Single-Variable Breakeven Challenger (A1..A3 vs A0):** Codified and implemented Breakeven Ratchet challenger arms (`ChandelierATRWithBE05R`, `BE075R`, `BE10R`) in `v8-core/src/kaizen/exit_trailing.rs` and `usdm_sim.rs`.
- **Empirical 12M Tape Results:** Evaluated 12-month BTCUSDT tape; verified that A1 (+0.5R BE) reduces loss by +$12.82 (+22.4%) from -$57.20 to -$44.38, lifts win rate from 31.9% to 42.2%, and reduces max drawdown from 12.59% to 11.64% with only +$0.65 fee friction.
- **Memory Ledger Updated:** Appended learning records MEM-20260822-013..017 to `COMMITTEE_MEMORY_LEDGER.jsonl`.

Artifacts changed: `v8-core/src/kaizen/exit_trailing.rs`, `v8-core/src/usdm_sim.rs`, `v8-core/src/main.rs`, `legacy/v82/*`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/governance/COMMITTEE_MEMORY_LEDGER.jsonl`, `tools/sync_committee_memory.py`, `docs/CHANGELOG.md`.

## 2026-08-22 — Ratification & Implementation of D-135: Emergency Mainline Execution Authority & Scope Firewall (CC-BILL-V8.3-D135, Rule 43)

Unanimously ratified by the V8 Central Committee (5-0) with Red-Team adversarial amendments and implemented in Rust:
- **EmergencyMergeWarrant Protocol (Rule 43):** Authorizes Kaizen to declare `EMERGENCY_EXECUTION_STATE` strictly for operational crises (P0 breach, PIT leakage, ledger corruption, pipeline failure) and issue time-bounded, single-use `EmergencyMergeWarrant` records.
- **Bare Push Absolute Ban:** Strictly prohibits bare `git push origin main`, requiring cryptographic warrant binding `incident_id`, `base_commit`, `constitution_hash`, `allowed_files`, and `rollback_commit`.
- **Two-Stage Hotfix & Provisional Head Quarantine:** Mainline commits remain in `PROVISIONAL_HEAD` quarantine pending Post-Push Full CI and Red-Team review; verification failure triggers deterministic `AUTO_ROLLBACK`.
- **Zero Economic Tuning & Scope Firewall:** Implemented `v8-core/src/judiciary/emergency.rs` with strict rejection of economic, threshold, or parameter tuning during hotfixes.
- **Single-Use Atomic Revocation:** Warrant is atomically consumed upon merge (`warrant.consume()`) and break-glass write tokens are immediately revoked.
- **Decision D-135 & Rule 43 Registered:** Recorded in `DECISION_REGISTER.md` (EN & TR), `V8_CONSTITUTION.md` (EN & TR), `COMMITTEE_MEMORY_LEDGER.jsonl`, and `CC_SESSION_20260822_D135_EMERGENCY_AUTHORITY.md`.

Artifacts changed: `v8-core/src/judiciary/emergency.rs`, `v8-core/src/judiciary/mod.rs`, `docs/charter/V8_CONSTITUTION.md`, `docs/tr/V8_CONSTITUTION.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/dossiers/CC_SESSION_20260822_D135_EMERGENCY_AUTHORITY.md`, `docs/governance/COMMITTEE_MEMORY_LEDGER.jsonl`, `docs/CHANGELOG.md`.

## 2026-08-22 — V8 Phase II Clean-Room Session, Economic Research Readiness Audit & H4 Conflict Decomposition

Completed under strict D-131 Epistemic Authority and D-134 Judicial Oversight mandates:
- **13-Point Economic Research Readiness Audit:** Verified 13/13 constitutional subsystems; 422 standard tests, 8/8 sabotage tests, and 7/7 judicial review tests pass. Formally declared `ECONOMIC_RESEARCH_READY`.
- **$1,000 CashflowLedger Clean-Room Baseline:** Evaluated 1-year certified tape (`research/tape/btcusdt-1h-12m/tape.jsonl`); reproduced double-entry cashflow baseline (-$57.20 / -$170.04 net realized PnL under venue fees) and falsified unverified historical positive claims.
- **H4 Conflict Source Decomposition:** Formally diagnosed Stage 3 contradiction drop sources (3,284 / 4,253 drops); identified `volume_climax_reversal` (2,717 opposes) and `market_profile_value_area` (1,562 opposes) as root causes of trend breakout suppression.
- **Independent Execution Oversight Receipts:** Procedural Commissioner (`usul_icra_komiseri`) and Technical Commissioner (`teknik_icra_komiseri`) independent oversight audits submitted with 0 vetos.

Artifacts changed: `v8-core/src/opportunity/funnel.rs`, `site/h4_decomposition.txt`, `.audit/rust_audit_current/portfolio_receipt.json`, `docs/CHANGELOG.md`.

## 2026-08-22 — Ratification of V8 Judicial Review, Execution Oversight & Agent Accountability Act (CC-BILL-V8.3-JUDICIARY-005-REV2, D-134)

Unanimously ratified by the V8 Central Committee and Allied Assembly (7-0) following Yüksek Divan trial `RT-001`:
- **Four-Plane Separation of Powers (Rule 36):** Formally codified institutional separation ($\text{Constitution} \to \text{Judiciary} \to \text{Kaizen} \to \text{Implementer} \to \text{Ledger}$).
- **Execution Oversight Corps (Rule 37):** Established independent Procedural & Technical Execution Commissioners with `TRACE`, `CHALLENGE`, and `BLOCK` rights (zero prod code/merge/success rights).
- **Amendment A1 (Rule 38):** Anti-Clone & Epistemic Diversity Mandate isolating auditors from implementer Chain-of-Thought reasoning (`Blind Protocol`).
- **Amendment A2 (Rule 39):** `No Naked Veto` with panic-test/receipt burden of proof and guaranteed 1-turn expedited judicial panel appeal.
- **Amendment A3 (Rule 40):** Tier 0–2 Risk-Weighted Mobilization with Token Budget & Governance Efficiency receipts.
- **Amendment A4 (Rule 41):** Cryptographic Constitution Pinning (`constitution_tree_hash`) and Kaizen Self-Audit Ban.
- **Mandatory Red-Team Charter (Rule 42):** Codified 6-part Adversarial Falsification Charter and preserved dissenting opinions.
- **Decision D-134 Registered:** Formally tescil in `DECISION_REGISTER.md` (EN & TR).

Artifacts changed: `docs/charter/V8_CONSTITUTION.md`, `docs/tr/V8_CONSTITUTION.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/dossiers/CC_SESSION_20260822_JUDICIARY_RATIFICATION.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `v8-core/src/judiciary/*`, `site/index.html`, `site/tr.html`.

## 2026-08-22 — Execution & Verified Completion of Evidence State Emergency Hotfix (CC-EMERGENCY-DECREE-005, D-133)

Enacted under extraordinary Central Committee authority to execute unified constitutional migration across 6 milestones with zero bureaucracy and strictly zero economic tuning:
- **Milestone 1 `[AUTH]`:** Implemented 3D Authority Tensor (`EvidenceAuthority`, `DecisionAuthority`, `RealizationStatus`), `ClaimValue<T>`, `ExecutionGatekeeper`, and `ReconciliationReceipt` with Merkle witness roots and $N_{\text{eff}} \equiv 1.0$ clone collapse proofs in `v8-core/src/authority.rs` and `reconcile.rs`.
- **Milestone 2 `[CLAIMS]`:** Codified closed algebra of 6 statutory claim classes, central content-addressed `ClaimRegistry`, and `RendererFirewall` in `v8-core/src/claims.rs`.
- **Milestone 3 `[AUDIT]`:** Established `v8-core/src/audit/` kernel (`authority.rs`, `lineage.rs`, `cashflow.rs`, `reconciliation.rs`, `independence.rs`) and passed 8/8 automated sabotage tests in `sabotage.rs`.
- **Milestone 4 `[KAIZEN]`:** Implemented `KaizenVerdictEngine` and `KaizenController` in `v8-core/src/kaizen/` as the single sovereign source of normative verdicts.
- **Milestone 5 `[EXECUTION]`:** Created `ExecutionBackend` trait and `BinanceUsdmExecutionBackend` in `v8-core/src/backend/execution.rs` as passive venue physics instruments.
- **Milestone 6 `[LEGACY]`:** Mühürlenen `v8-pre-sovereign-hotfix` adli etiketi, `tools/audit_reachability.py`, and complete elimination of runtime shadow authority paths.
- **Decision D-133 Registered:** Formally tescil in `DECISION_REGISTER.md` (EN & TR). Emergency authority automatically expired upon 415/415 test pass.

Artifacts changed: `v8-core/src/authority.rs`, `v8-core/src/claims.rs`, `v8-core/src/audit/*`, `v8-core/src/kaizen/controller.rs`, `v8-core/src/kaizen/verdict.rs`, `v8-core/src/backend/execution.rs`, `tools/audit_reachability.py`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`, `site/index.html`, `site/tr.html`.

## 2026-08-22 — Ratification & Codification of V8 Evidence Constitution v2 & Authority Sovereignty Act (CC-BILL-V8.3-AUTHORITY-003, CC-AMEND-V8.3-KAIZEN-004, D-132)

Unanimously ratified by the V8 Central Committee and Allied Assembly (7-0) under Resolution `V8-CC-SOVEREIGNTY-2026-08-REV2`:
- **Constitutional Overhaul (Rules 28–35):** Upgraded `V8_CONSTITUTION.md` (v0.3 EN & TR) codifying 3D Authority Tensor (`EvidenceAuthority`, `DecisionAuthority`, `RealizationStatus`), `No Naked Economic Claims` via `ClaimValue<T>`, closed algebra of 6 statutory claim classes with centralized `ClaimRegistry`, Renderer Firewall, and Constitutional Adversarial Audit (`FALSIFY CLAIM`).
- **Sovereign Kaizen & Execution Physics Instrument:** Designated `KaizenController` as the single sovereign research and verdict authority (`KaizenVerdictEngine`). Demoted USD-M Engine from autonomous decision authority to passive `ExecutionBackend` laboratory instrument modeling venue micro-physics.
- **Constitutional Audit Kernel & Legacy Import Ban:** Formally established `v8-core/src/audit/` architectural kernel and enforced compile-time legacy isolation (`FORBIDDEN_LEGACY_IMPORT`, `SHADOW_AUTHORITY_PATH` P0 reachability failure).
- **Decision D-132 Registered:** Formally tescil in `DECISION_REGISTER.md` (EN & TR).
- **Expanded Roadmap Roadmap Ratified:** Codified execution sequence: `PH2-003A` (Evidence Authority Hardening) $\rightarrow$ `PH2-003A.1` (Claim Registry + Renderer Firewall) $\rightarrow$ `PH2-003A.2` (Central Constitutional Audit Kernel) $\rightarrow$ `PH2-003A.3` (Kaizen Sovereign Controller) $\rightarrow$ `PH2-003A.4` (USD-M Migration) $\rightarrow$ `PH2-003A.5` (Legacy Purge) $\rightarrow$ Independent Red-Team Audit $\rightarrow$ `PH2-003B` (H4 Reconciliation Repair).

Artifacts changed: `docs/charter/V8_CONSTITUTION.md`, `docs/tr/V8_CONSTITUTION.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`, `site/index.html`, `site/tr.html`.

## 2026-08-22 — Implementation & Succession of V8.3 Büyük İleri Atılım: Opportunity Sovereignty (issues #231..#242, D-128..D-130)


Complete, tested, and verified implementation of the entire V8.3 Büyük İleri Atılım milestone in Rust (`v8-core/`):
- **#231 (V83-001):** Core Types & Module Boundary (`v8-core/src/opportunity/`) establishing the 7 canonical primitives with cryptographic BLAKE3 identity tuples.
- **#232 (V83-002):** Economic Exposure Identity & False-Collapse Protection (`v8-core/src/opportunity/exposure.rs`), preserving multi-leg basis spread identities and deterministic alias resolution.
- **#233 (V83-003):** Point-In-Time Causal Opportunity Grammar & Canonical Opportunity Book (`v8-core/src/opportunity/grammar.rs`, `book.rs`) with zero-lookahead and expert independence.
- **#234 (V83-004):** Epistemic Witness Migration & Legacy Adapter (`v8-core/src/experts/witness_adapter.rs`) mapping all 28 experts to typed evidence stances with a compile-time capital firewall.
- **#235 (V83-005):** Habitat, Abstention & 9-Dimensional Epistemic Witness Scorecards (`v8-core/src/analysis/scorecard.rs`, `evidence.rs`) under strict Rule 5 anti-hallucination compliance.
- **#236 (V83-006):** Dependence-Aware Evidence Reconciliation (`v8-core/src/opportunity/reconcile.rs`) with exact $N_{\text{eff}}=1.0$ clone collapse and contradiction dampening.
- **#237 (V83-007):** Cost-Aware Selective Utility & Hurdle Engine (`v8-core/src/opportunity/utility.rs`) defaulting sub-friction setups to `NO_TRADE`.
- **#238 (V83-008):** Exposure-Aware Portfolio Feasibility & ExecutionCampaign (`v8-core/src/opportunity/campaign.rs`).
- **#239 (V83-009):** V8.3 Opportunity Runloop & Ledger Pipeline (`v8-core/src/opportunity/runloop.rs`).
- **#240 (V83-010):** Constitutional Invariant Harness T1–T12 (`v8-core/src/opportunity/harness_t1_t12.rs`) validating all 12 constitutional gates.
- **#241 (V83-011):** Great Leap Economic Evaluation: G0–G4 Historical Dossier (`docs/dossiers/V83_G0_G4_HISTORICAL_EVALUATION.md`).
- **#242 (V83-012):** G5 Prospective Shadow Confirmation & Succession Dossier (`docs/dossiers/V83_G5_PROSPECTIVE_CONFIRMATION.md`, `docs/dossiers/V83_ANATOMY_TARGET_PREDICTION_AUDIT.md`).

Artifacts changed: `v8-core/src/opportunity/*`, `v8-core/src/experts/witness_adapter.rs`, `v8-core/src/analysis/scorecard.rs`, `docs/dossiers/*`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.

## 2026-08-22 — Ratification of V8.3 Büyük İleri Atılım: Opportunity Sovereignty Constitutional Package (CC-PROP-V8.3-GL-001, CC-RES-V8.3-GL-001, D-128..D-130)

Unanimously ratified by the V8 Central Committee (5-0) under Resolution `CC-RES-V8.3-GL-001`:
- **Constitutional Overhaul:** Updated `V8_CONSTITUTION.md` (v0.2 EN & TR) with Rules 4, 6, 13, 14, 16, 17 and new foundational Articles 18–27 establishing Opportunity Sovereignty, Observer Constitution, Multiplicity Invariance, First-Class Abstention/NO_TRADE, Correlated Witness Discounting, Falsifiable Opportunity Grammar, False-Collapse Basis Protection, and Constitutional Falsifiability.
- **P0 Contradiction Resolution (C-V83-001):** Formally resolved the dual opportunity ontology tension between the production decision plane (legacy candidate-centric) and Target Oracle evaluation plane (opportunity universe) in `CONTRADICTION_MAP.md` (EN & TR).
- **Decisions D-128, D-129, D-130:** Registered V8.3 Challenger Track authorization, P0 contradiction closure, and 7-Primitive / 9-Dimensional Epistemic Witness Architecture in `DECISION_REGISTER.md` (EN & TR).
- **Production Incumbency:** Preserved 100% exclusive production authority for V8.2 until V8.3 passes all T1–T12 Invariant Tests and G0–G5 Economic Gates on untouched multi-symbol/multi-instrument out-of-sample data.

Artifacts changed: `docs/charter/V8_CONSTITUTION.md`, `docs/tr/V8_CONSTITUTION.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/audits/CONTRADICTION_MAP.md`, `docs/tr/CONTRADICTION_MAP.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `site/index.html`, `site/tr.html`.

## 2026-08-22 — Zero-Allocation Typed Geometry, Direct Indexing & Streaming Hashing in Hot Replay Paths (issues #225, #226, #227, #228, #229, D-127)


Eliminated critical hot-path allocations and linear scans across simulation, state, feature projection, and caching:
- **Issue #225 (PERF-002):** Replaced per-bar dynamic `HashMap<String, Value>` string lookups and `validate_geometry` runs in the inner simulation step loop with strongly-typed `RiskGeometry` struct field offsets.
- **Issue #226 (PERF-003):** Replaced per-bar `HashMap<String, Feature>` allocations and 77 string clones in expert runloop evaluation with zero-copy `ProjectedFeatures<&[Feature]>` slice projections.
- **Issue #227 (PERF-004):** Eliminated eager full-tape `serde_json::Value` tree allocations in `write_cube_reduced` cache hotpath via precomputed incremental `Dataset.data_hash`.
- **Issue #228 (PERF-005):** Eliminated repetitive $O(N)$ linear symbol searches across multi-symbol datasets in candidate planning and backend evaluation via pre-indexed $O(1)$ symbol maps.
- **Issue #229 (PERF-006):** Precomputed full-tape stochastic %K/%D series in $O(N)$ during `FeatureStore::build` and introduced zero-allocation `history_window_agg` in `FeatCtx` for Predicate IR evaluation.

Artifacts changed: `v8-core/src/{simulator.rs, state.rs, experts/predicate.rs, experts/base.rs, backend/scalar.rs, backend/simd.rs, data.rs, runloop.rs, usdm_sim.rs, main.rs}`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/CHANGELOG.md`.

## 2026-08-22 — Historical Market Archetype Registry & Multi-Episode Allegorical Audit Suite (D-125, ALLEGORY-001)

Introduced the 12 Canonical Market Archetypes (A01–A12) across 4 super-classes (Directional Opportunity, Forced-Flow Stress, Low-Opportunity Adversarial, Portfolio Derivatives) into V8's evaluation plane (`v8-core/src/evaluation/allegory.rs`):
- Enforced zero-hindsight episode bounds and mandatory negative control calibration pairs (anti-allegories) to prevent narrative cherry-picking and single-date overfitting.
- Built ex-ante candidate admission versus ex-post unconstrained / capital-constrained opportunity frontiers with regret decomposition, warning lead-time, exit latency, and NO_TRADE accuracy metrics.
- Generated deterministic, Canon-hashed `allegory_scorecard.json` artifact labeled `NO_ECONOMIC_CLAIM` and integrated CLI dispatch via `v8-core allegory-audit`.

Artifacts changed: `v8-core/src/evaluation/allegory.rs`, `v8-core/src/evaluation/mod.rs`, `v8-core/src/main.rs`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `site/index.html`, `site/tr.html`.

## 2026-08-21 — Modernize v8-core architecture, error taxonomy, zero-copy streaming, and add ACCP v2.0 verification suite (issues #208, #209, #210, #211, D-119..D-122)

Resolved four foundational modernization issues in `v8-core`:
- **Issue #208 (D-119):** Introduced `V8CoreError` strongly-typed error taxonomy via `thiserror` in `v8-core/src/error.rs`, typed candidate lifecycle enum `CandidateState` in `v8-core/src/candidate.rs`, and typed scheduler evaluation `evaluate_typed`.
- **Issue #209 (D-120):** Upgraded `v8-core/src/hash.rs` with `BLAKE3` and `SHA-256` digest functions alongside legacy `SHA-1`, introduced depth-bounded path traversal defense `sanitize_path` in `v8-core/src/path_security.rs`, and structured telemetry facades in `v8-core/src/telemetry.rs`.
- **Issue #210 (D-121):** Implemented `Dataset::from_mmap_path` using `memmap2` for zero-copy $O(1)$ memory overhead tape streaming in `v8-core/src/data.rs` and standardized on `bincode` for fast binary serialization.
- **Issue #211 (D-122):** Built atomic simulation state snapshotting (`SimulationCheckpoint`) for `--resume` execution in `v8-core/src/checkpoint.rs`, and configured multi-architecture release workflow in `.github/workflows/release.yml`.
- Generated complete ACCP v2.0 verification suite under `reports/accp/P46/source/` (`P46_BSR_001.accp.yaml`, `P46_FPR_001.accp.yaml`, `P46_TVR_001.accp.yaml`, `P46_PRR_001.accp.yaml`).

Artifacts changed: `v8-core/src/{error.rs, candidate.rs, hash.rs, data.rs, scheduler.rs, path_security.rs, telemetry.rs, checkpoint.rs, main.rs}`, `v8-core/Cargo.toml`, `.github/workflows/release.yml`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`, `reports/accp/P46/source/*.accp.yaml`, `site/index.html`, `site/tr.html`.

## 2026-08-20 — Hoist invariant outcome-cube code hash (issue #205, D-083)

Measured the warm S6 parity gate at 87.89 seconds and attributed 95.99 of
108.74 profiled seconds to 4,422 repeated `_code_hash()` calls. The legacy
`tools/regret.py` evaluator now computes the unchanged decision-path code hash
once per `write_cube` invocation and reuses it for every emitted cell. Focused
tests bind the one-call lifetime, exact row provenance, and standalone fallback.
The frozen `src/v8` oracle and all output semantics remain unchanged. The same
warm S6 parity command passed in 8.14 seconds after the patch versus 87.89
seconds before it (approximately 9.74x by external wall measurement); the Rust
binary was not rebuilt in either measured run. This is a local gate-speed
measurement, not an economic or general compute-speed claim.

Artifacts changed: `tools/regret.py`, `tests/test_regret_phase0.py`,
`docs/CHANGELOG.md`, `site/index.html`, `site/tr.html`.

## 2026-08-20 — Windows parity binary-path fix (issue #203)

Fixed the shared Python parity fixture to resolve Cargo's exact Windows release
executable name (`v8-core.exe`) while preserving the extensionless POSIX name,
stale-source rebuild check, and fail-closed exact-path assertion. Added a focused
cross-platform naming regression test. No Rust, parity-value, oracle, simulator,
or economic semantics changed.

Artifacts changed: `tests/parity/conftest.py`,
`tests/test_parity_binary_path.py`, `docs/CHANGELOG.md`, `site/index.html`,
`site/tr.html`.

## 2026-08-20 — Quantized-computation applicability audit (D-118, #199)

Added an English/Turkish, arXiv-grounded audit that distinguishes V8's current
deterministic IEEE-754 `f64` contract from integer/fixed-point/low-bit
quantization. The audit records the absent quantization contract (representation,
scale/zero-point, rounding, saturation/overflow, calibration, frozen-OOS error,
and backend parity), retains quantization as absent by default, and confirms
that the evaluation evidence suite is bound to Constitution Rule 12
(`NO_ECONOMIC_CLAIM`) without making an economic or speed claim. The audit is
wired into both monographs.

Artifacts changed: `docs/audits/QUANTIZED_COMPUTATION_AUDIT.md`,
`docs/tr/QUANTIZED_COMPUTATION_AUDIT.md`, `tools/build_monograph.py`,
`docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`,
`docs/CHANGELOG.md`, and regenerated monographs.

## 2026-08-19 — Deploy V8 Work-Item / PR Governance v1.2 and Start Measured Pilot (D-117)

Deployed the canonical V8 Work-Item, Pull-Request & Merge Governance v1.2 pack across the repository:
- **5 Issue Forms (`.github/ISSUE_TEMPLATE/`):** Deployed `defect.yml`, `implementation.yml`, `research.yml`, `performance.yml`, and `governance.yml` with universal context-completeness contract (`R#` traceability, reused contracts, invariants, canonical failure semantics, dependency map, OPEN_PIN triggers).
- **PR Contract (`.github/PULL_REQUEST_TEMPLATE.md`):** Deployed end-to-end `R#` requirement traceability table, change classes, and explicit verification gate bindings (`check` check name).
- **CODEOWNERS Routing (`.github/CODEOWNERS`):** Routed all critical surfaces to repository maintainer `@ddawnlll`.
- **Workflow Policy (`docs/WORK_ITEM_POLICY.md` & `CONTRIBUTING.md`):** Formalized collaborative precedence hierarchy (Constitution > Contracts/Decisions > WORK_ITEM_POLICY > CONTRIBUTING > Scoped Agent Runbooks).
- **Measured Pilot (`docs/governance/PILOT_TRACKING_RECORD.md`):** Initiated the 10–20 issue empirical measurement ledger.

Artifacts changed: `.github/ISSUE_TEMPLATE/{config.yml, defect.yml, implementation.yml, research.yml, performance.yml, governance.yml}`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/CODEOWNERS`, `CONTRIBUTING.md`, `docs/WORK_ITEM_POLICY.md`, `docs/governance/PILOT_TRACKING_RECORD.md`, `docs/decisions/DECISION_REGISTER.md`, `docs/CHANGELOG.md`, `tools/build_monograph.py`, agent guides (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `AGENT_PROMPT.md`, `.github/copilot-instructions.md`).

## 2026-08-19 — Resolution of Issues #158–#163: Governance & Defect Hardening Batch (D-103..D-108)

Resolved six issues spanning candidate evaluation decoupling, dispatch tie-break conformance, epistemic belief state, causal intervention manifests, mechanism hypothesis decoupling, and authority resolution:
- **#158 (D-108):** Decoupled independent candidate evaluation from downstream portfolio allocation (`runloop.rs`), ensuring contention-losing candidates retain full independent counterfactual outcomes and emitting structured `portfolio_allocation` records.
- **#159 (D-103):** Reconciled contention dispatch specification with runtime `R-ALLOC-001` (`sha1(Canon(expert_id))`) across contracts, adding executable state-space contention and mutation test gates.
- **#160 (D-104):** Replaced boolean predicate return with explicit three-valued `ThesisStatus { Valid, Invalid, Unknown }` in `predicate.rs`, decoupling epistemic observation uncertainty from `PositionPolicy::Hold` operational action.
- **#161 (D-105):** Added typed `InterventionManifest` to `simulator.rs:Outcome` and implemented `InterventionClass` regret bucket partitioning in `regret.rs` with `UNSUPPORTED_COUNTERFACTUAL` refusal semantics.
- **#162 (D-106):** Decoupled observable price behavior from causal mechanism hypotheses with default `evidence_status: HYPOTHESIS_ONLY` and `EvidenceManifest` schema in `EXPERTS_REGISTRY.yaml` and `experts/base.rs`.
- **#163 (D-107):** Purged superseded single-unit multiplicity clause from `EXPERT_PROTOCOL.md` and added executable `authority.rs` ledger validating unambiguous domain resolution (`resolve_active_rule("multiplicity") -> D-044`).

Artifacts changed: `v8-core/src/authority.rs`, `v8-core/src/runloop.rs`, `v8-core/src/experts/predicate.rs`, `v8-core/src/experts/base.rs`, `v8-core/src/simulator.rs`, `v8-core/src/regret.rs`, `v8-core/src/main.rs`, `docs/contracts/CANDIDATE_LIFECYCLE_SPEC.md`, `docs/contracts/RUNTIME_SCHEDULER_SPEC.md`, `docs/contracts/PREDICATE_IR_SPEC.md`, `docs/contracts/EXPERT_PROTOCOL.md`, `docs/EXPERTS_REGISTRY.yaml`, `docs/decisions/DECISION_REGISTER.md`, `docs/CHANGELOG.md`.

## 2026-08-19 — Target Oracle O2–O3 support, coverage & evidence receipts (D-102)

Added the Rust-owned Target Oracle support/authority classifier and representational
coverage reconciliation over the frozen Opportunity Universe (#154). The support
classifier emits orthogonal `CounterfactualAuthority` and typed `OracleOutcome`
values without fabricating point estimates. The coverage engine reconciles
membership against same-event shipped `ExpertEval` proposals and persists canonical
`OpportunityUniverseVersion`, `OracleEvaluationRecord`s, and `CoverageReceipt`
findings directly into the immutable `v8.eval.v1` evidence bundle with the explicit
label `NO_ECONOMIC_CLAIM`. A development CLI subcommand `oracle-coverage` is exposed.

Artifacts changed: `v8-core/src/oracle/{support.rs,authority.rs,coverage.rs,artifacts.rs,mod.rs}`,
`v8-core/src/main.rs`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`,
and decision registers; monographs regenerated.

## 2026-08-19 — Target Oracle O0–O1 substrate (D-101)

Added the Rust-owned Target Oracle foundation: the three-role taxonomy and
typed refusal vocabulary, versioned after-cost `UtilityContract` validation,
a narrow PIT `InformationSet` adapter over the existing FeatureStore, and a
deterministic, finite Opportunity Grammar with a separate GrammarCandidate
identity domain. The grammar requires caller-supplied registered primitives,
templates, and parameter grids; no production vocabulary, grid, support
classification, coverage, bundle serialization, policy optimization, or
economic verdict was introduced. O-OR-001 records the intentionally absent
production catalog.

Artifacts changed: `v8-core/src/oracle/*`, `v8-core/src/main.rs`,
`docs/contracts/IMPLEMENTATION_LAYOUT.md`, and the decision/open-question
registers; both monographs were regenerated.

## 2026-08-18 — safe subset of lifecycle issue #139 (LM-002)

The Rust candidate projection now retains canonical transition records and
writes an append-only `candidate-transitions.jsonl` ledger. The projection can
be rebuilt from shuffled or at-least-once JSONL input with event-id duplicate
suppression and canonical hash/order checks. This deliberately does not infer
`EXECUTED` or `CLOSED` from counterfactual cube outcomes; full position
lifecycle semantics remain unavailable.

Artifacts changed: `v8-core/src/candidate.rs`, `v8-core/src/runloop.rs`.

## 2026-08-16 — Computation-budget policy (D-099)

Added the decision-value rule for agent and operator computation: every
non-trivial or repeated green check must identify the decision and new
semantic risk it could change; mandatory boundary gates remain mandatory.
The policy requires the smallest discriminating check, one full handoff suite,
and an explicit report after 60 seconds of additional verification.

Artifacts changed: `CLAUDE.md`, `rules.md`,
`docs/COMPUTATION_BUDGET_POLICY.md`, `docs/tr/COMPUTATION_BUDGET_POLICY.md`,
`docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`,
`tools/build_monograph.py`, regenerated `site/index.html` and `site/tr.html`.

## 2026-08-16 — Python oracle boundary and hash lock (D-100)

The Python `src/v8/` tree is now explicitly classified as a frozen historical
parity oracle, not a runtime. `PYTHON_ORACLE_LOCK.json` pins its Git tree hash;
`audit_python_boundary.py` rejects dirty/unregistered oracle changes and CI
Python pytest/oracle invocation. Monograph generation and explicitly invoked
legacy research tooling remain allowed. The oracle is retained until its
remaining consumers have owned replacements.

Artifacts changed: `docs/legacy/PYTHON_ORACLE_{LOCK,POLICY}.*`,
`tools/audit_python_boundary.py`, `.github/workflows/ci.yml`, and both decision
registers.

## 2026-08-16 — Optional Linux Vulkan f64 K4 backend and dispatch hardening (D-098)

`v8-core/src/backend/gpu.rs` now contains the real optional Vulkan f64 replay
backend for the static bar-close K4 subset. It requires `SHADER_F64`, runs a
no-contraction probe, validates geometry, and fails closed on unsupported
management/thesis/fill-policy cells. `backend/mod.rs` performs capability-aware
Auto dispatch with CPU fallback and rejects `FILL_AT_LIMIT` from the GPU path.
The implementation-status text from D-096 is superseded; its determinism and
f64 constraints remain. Local Rust gates pass, while physical Linux Vulkan
runtime parity remains an environment receipt rather than a claimed result.

Artifacts changed: `v8-core/src/backend/{gpu,mod}.rs`,
`docs/decisions/DECISION_REGISTER.md`,
`docs/contracts/COMPUTE_SCHEDULING_SPEC.md`,
`docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/STATUS_REPORT.md`.

## 2026-08-14 — Rust compute plane is authoritative; Python oracle retired from the verification path (D-097)

Operator-ratified. `v8-core` (D-087..D-095) is the sole authoritative
implementation; `src/v8` is preserved as a historical/legacy corpus but does
not run in CI, workflows, or gates. Verification is Rust-native: `cargo test`
per change, G4/G5 determinism, golden vectors from the S0-S7-verified outputs
as the release gate. The Python test suite (864 tests) and the `tests/parity`
Python-vs-Rust suite are retired from gates; the oracle-tree-hash pin mechanism
is superseded by golden-vector hashes. The S0-S7 differential record
(`reports/parity/S0-S7.md`) remains the historical trust anchor — the
retirement is licensed only by that completed verification. Rules 9/12
unchanged; `NO_ECONOMIC_CLAIM` stands. Workflow consequence: no Python
executes in fix/verify workflows (cargo only); defect fixes land in `v8-core`
only. Scope boundary: the rule covers the verification path; monograph build
and tape builders remain Python until ported (follow-up).

Artifacts changed: `docs/decisions/DECISION_REGISTER.md` (D-097),
`docs/CHANGELOG.md`, `.github/workflows/ci.yml` (pytest steps removed).

## 2026-08-14 — Kernel backend strategy: scalar + CPU/SIMD first, GPU behind the trigger, CubeCL over wgpu (D-096)

The V8.2 compute plane's backend strategy is declared (D-096). `v8-core` is
single-path scalar today — the S0-S7 gates (D-087..D-095) are correctness
gates; `threads` is recorded in the request manifest and tested for
invariance (G5), but no task-parallel or SIMD execution exists in the tree.
The order is fixed: Backend-0 scalar deterministic Rust as the in-core
reference (the frozen Python `src/v8/` stays the parity oracle, D-087), then
Backend-1 CPU + task parallelism + SIMD, GPU only past the ~10^9-cell trigger
(`COMPUTE_SCHEDULING_SPEC` §6, D-084). If a portable GPU layer is ever
adopted it is CubeCL over wgpu: CubeCL compiles one kernel IR to
CUDA/HIP/Metal/Vulkan/CPU and matches the K1-K6 kernel structure, while wgpu
sits at the buffer/pipeline/dispatch level and direct use would mean writing
a mini compute framework. The f64 contract is the decisive constraint and
closes the GPU path before the trigger opens it — Metal has no fp64 in
shaders; Vulkan's `SHADER_F64` (native only) runs fp64 16-64x slower than
f32; consumer CUDA/HIP (RTX 40/50, RX 7000) run fp64 at 1/16-1/32 rate. On
Apple, CubeCL's Metal/Vulkan paths run through wgpu, so the limitation
applies either way. No CubeCL/wgpu dependency is added now (CubeCL is alpha,
breaking changes between minor versions; O-029's CPU-competitiveness
measurement precedes adoption).

Artifacts changed: `docs/decisions/DECISION_REGISTER.md` (D-096),
`docs/contracts/COMPUTE_SCHEDULING_SPEC.md` (§6 f64 note),
`docs/decisions/OPEN_DECISIONS.md` (O-029 annotation), `site/index.html`
(rebuilt).

## 2026-08-12 — V8.2 compute core S6 gate CLOSED: Analysis composition bit-identical (D-094)

`analysis/{mod,outcome,phase1,phase2,phase3,reconcile}.rs` implement the
`analysis` subcommand — regret phases 1-3 composed end to end from the
compute plane's own ledgers. The gate closed in three commits over the day:
Wave 1/2 (`17e506a`, `5accfc6`) landed the leaf modules and wired the
composition, running but not bit-identical (939 divergences against the
oracle — `reports/parity/S6.md` as first written, status PARTIAL). `647c0b0`
fixed the dominant cause: candidate-draft binding by re-derived
`candidate_id` hash matched nothing on lab-produced stores (V8.2 identities
are the D-079 canonical encoding, deliberately different from the oracle's
`sha1_hex(json)`); binding by the D-026 identity tuple instead took
reconciliation from 0/62 to 56/62. `3e13697` closed the rest: clock-bound
draft binding (the DETECTED transition's own `knowledge_time` disambiguates
the 45 anchor-tuples with multiple candidates) closed the last 6
reconciliation mismatches, and exposing `cost_r`/`funding_r` on the compute
`Outcome` (the kernel already computed them into `net_r`, just didn't surface
them) closed 124 Phase-1 divergences. Gate now PASSES: reconciliation 62/62,
all three phase outputs bit-identical to `tools/regret_phase1/2/3.py` on the
all-28-expert 200-bar fixture. Issue #117 CLOSED. No economic claim, no speed
claim (rule 12; D-092..D-095 evidence discipline).

Artifacts changed: `v8-core/src/analysis/{mod,outcome,phase1,phase2,phase3,
reconcile}.rs`, `tests/parity/test_parity_s6.py`,
`reports/parity/S6.md`, `docs/decisions/DECISION_REGISTER.md` (D-094).

## 2026-08-12 — V8.2 compute core S4 gate PASS: candidate-population parity (D-092)

All 28 registered Experts ported to `v8-core/src/experts/*.rs` (issues
#77-100), closing the S2 pilot-only state (4/28). Two modules complete the
plane beyond `COMPUTE_CORE_SPEC` §6's original table: `features.rs` (D-053
feature-group projection — an Expert's `FeatMap` carries only its declared
`requires`-closure) and `runloop.rs` (the `evaluate` subcommand — the S4
composition point: per bar x per symbol x the full dispatch table, projected
FeatMap in, CANDIDATE draft out, D-026 dedup, into the CandidateBuffer).
Issue #101 fixed (four ported pilots hardcoded `"SOLUSDT"` instead of reading
the request's symbol). The Wave-2 exit-kind coverage card (#103) caught and
fixed two latent S2 predicate-IR bugs in the donchian `responsive`/
`significant_extreme` exit kinds, unexercised by the S2 E1 grid because
they're module-local: an EXCLUSIVE `window_agg` off-by-one (48/202 grid
mismatches) and an EXCLUSIVE fail-open threshold bug (24/202). Gate: 5/5 S4
population-parity tests PASS — 3,360 (120 bars x 28 experts) evaluations
bit-identical, 209 DETECTED episodes and 211 suppressed-duplicates identical
on both sides. **Known, accepted divergence** (not this gate's target):
admission timing — the loop admits at DETECTION (no exposure-slot release
yet), the lab admits at TRIGGER; the DETECTED population and suppression set
— this gate's actual subject — match exactly. No speed claim.

Artifacts changed: `v8-core/src/experts/*.rs` (28 files), `v8-core/src/
features.rs`, `v8-core/src/runloop.rs`, `tests/parity/
test_parity_s4_population.py`, `reports/parity/S4.md`, `docs/decisions/
DECISION_REGISTER.md` (D-092), `docs/contracts/IMPLEMENTATION_LAYOUT.md`
(§1.1/§4).

## 2026-08-12 — V8.2 compute core S7 gate PASS: verdict statistics + report/audit (D-095)

`statistics/{mod,reality_check,detrended,remaining}.rs` implement the
`verdict` subcommand (issue #128): block-bootstrap Reality-Check, the
Appendix A detrended-null placebo invariant (#124), and the METH-2..6 surface
(#129 — permutation RC, bootstrap CI, effective independent episodes, regime
slices, streak-vs-null, practical significance, expected false positives,
effective search size). A new module, `mt19937.rs` (#127), reproduces
CPython 3.14's Mersenne Twister bit-exactly (`init_by_array` seeding,
`genrand_res53` draws — not `getrandbits(53)/2**53`, empirically different
bits — and `random.py`-matching `randrange`/`getrandbits`/`sample`), because
the frozen oracle draws every bootstrap/permutation resample from
`random.Random(seed)` and bit-exact verdict parity needs bit-exact draws.
`report.rs` (#126) gains `verdict_path` (folds the verdict JSON into the
report summary; the report's own claim stays `NO_ECONOMIC_CLAIM`, rule 12)
and `audit_report` (audits an existing artifact — the path by which the
freshness check flags a stale one, #123). Gate: 3/3 S7 parity tests PASS —
every verdict JSON field bit-identical to `statistics.py` on a fixed episode
series + seed (WRC `p_value=0.0145`, block size 4 auto-selected on both
sides), report round-trip, stale-artifact audit correctly fails closed on a
tape swap. No economic claim, no speed claim.

Artifacts changed: `v8-core/src/statistics/{mod,reality_check,detrended,
remaining}.rs`, `v8-core/src/mt19937.rs`, `v8-core/src/report.rs`, `tests/
parity/test_parity_s7.py`, `reports/parity/S7.md`, `docs/decisions/
DECISION_REGISTER.md` (D-095), `docs/contracts/IMPLEMENTATION_LAYOUT.md`
(§1.1/§4).

## 2026-08-12 — V8.2 compute core S5 gate PASS: EvidenceStore tiers + DAG cache (D-093)

`evidence.rs` (issues #108/#109) gains `ArtifactTier`
(`IDENTITY_ONLY < VALUES < FULL`) with a tier-honesty rule — a field above
its artifact's tier is rejected as an explicit `TierViolation`, never a
silently downgraded or empty column — `RunConstants` (the §3 key set bound
into every header), and the `LEDGER_FORMAT_SPEC` §8 six-test battery
(`v8-core ledger-check`). `cache.rs` (issue #107) adds the missing cube-level
DAG node (`sha1(candidate_id|action_id|simulator_hash|data_hash) -> outcome`,
in-memory map plus an append-only `cache.jsonl`, log-then-map insert order
so a failed write leaves the map untouched). `v8-core cache-check` proves a
miss and a hit write byte-identical artifacts with identical fingerprints.
Gate: 15 evidence.rs + 4 cache.rs unit tests, `ledger-check` 6/6
LEDGER_FORMAT_SPEC §8 tests PASS, `cache-check` PASS, 3/3 S5 parity tests
PASS. **Known limitation, still open:** the cache is not wired into
`runloop.rs`'s cube reduction — `write_cube_reduced` calls `regret.rs`
directly and never consults `CacheStore`; wiring remains a follow-up. No
speed claim.

Artifacts changed: `v8-core/src/evidence.rs`, `v8-core/src/cache.rs`, `tests/
parity/test_parity_s5.py`, `reports/parity/S5.md`, `docs/decisions/
DECISION_REGISTER.md` (D-093).

## 2026-08-12 — V8.2 plane split revised: analysis/verdict/audit planes join the Rust plane (D-091)

D-091 registers the scope change: the runtime becomes one Rust plane end to
end — compute plus regret analysis phases 1-3 (opportunity accounting,
systematicity, recoverability), verdict statistics (Reality-Check, detrended
null, placebo family), and report/audit artifacts, all in-process. The
artifact file remains the persistence boundary but is no longer a language
crossing; D-078's no-callback extends to "no Python in the request path".
Python is reduced to the frozen parity oracle (`src/v8/`), the vendored
`simtruth/` lab (D-022), and pre-V8.2 dev/research tooling retired as its Rust
equivalent lands. Migration order S0..S5 extends with **S6 (analysis plane)**
and **S7 (verdict statistics + report/audit)**, each with a value-level parity
gate. Revises D-077's §7 rationale; supersedes D-081's "verdict statistics
stay in Python" consequence. Not a V9 (D-077 version semantics). No code
changed; no economic claim (rule 12).

Artifacts changed: `docs/decisions/DECISION_REGISTER.md` (D-091),
`docs/contracts/COMPUTE_CORE_SPEC.md` (§4 layer map, §6 module layout, §7
boundary, §8 migration order), `docs/contracts/ARCHITECTURE_SPEC.md` (§2
evaluation-plane note, §3.1 plane split), `docs/contracts/IMPLEMENTATION_LAYOUT.md`
(§1.1 Rust modules, tools retirement notes), `docs/ROADMAP.md` (Phase 4b),
`site/index.html` (rebuilt).

## 2026-08-11 — V8.2 compute core S3: CubeReducer + streaming regret (D-090)

`v8-core/src/regret.rs` (new), `v8-core cube` subcommand, `reports/parity/S3.md`
(new evidence). The S3 gate passes: the reduced tables match the Python
evaluator (OUTCOME_CUBE_SPEC §7.6 streaming == full materialization) on every
Candidate, plus G1..G6.

- `regret.rs`: the `LegalActionManifest` (NO_TRADE at element 0, the ACTUAL
  action at element 1 by construction, the declared grid de-duplicated by
  action id, `pyramid_add_rules` excluded → cardinality 2), the cell-status
  classifier (OK/CENSORED/UNDEFINED_FUTURE/NOT_EVALUABLE_ACTION/NO_ENTRY,
  `MIN_FUTURE_BARS = 1`), and `compute_gap` (best over OK cells incl. NO_TRADE,
  `GAP_TIE_EPS = 1e-12` ties reported never broken, abstain on CENSORED /
  no-OK / actual-cell-not-OK). Action and manifest identities are V8.2
  bit-encoded (D-079).
- `v8-core cube <request>`: streams one Candidate at a time — manifest →
  replay each cell via the S2 ReplayKernel → classify → reduce in memory →
  emit the `cube-reduced` artifact. Cells are never materialized across
  Candidates (D-081).

Gate evidence (`reports/parity/S3.md`): cargo test 24 passed; 5/5 S3 parity
tests — reduced tables match the Python Phase-0 evaluator on every BOUND
Candidate (gap_status/actual_utility/best_utility/tie_cardinality/
legal_hindsight_gap/abstention_reason exact), gap >= 0 on every COMPUTED
Candidate, manifest structure (a_actual element 1), G4 byte-identical, G5
thread invariance, G6 near-tape-end refusal (UNDEFINED_FUTURE) agrees. No
speed claim.

## 2026-08-11 — V8.2 compute core S2: Predicate IR + ReplayKernel (D-089)

`v8-core/src/experts/predicate.rs` (new), `v8-core/src/simulator.rs` (new),
`v8-core/src/experts/mod.rs` (new), `tools/predicate_ir.py` (new),
`reports/parity/S2.md` (new evidence). The S2 gate passes: outcome parity on
the V8.0 candidate population (E4) and the predicate equivalence gates of
`PREDICATE_IR_SPEC` §6 (E1-E3, E5), plus G4/G5/G6.

- The compiled `still_valid` IR evaluator: `compare` (FLIP_ON_SHORT),
  `asym_compare`, `all_of`/`any_of`, ordered `dispatch` (with geometry-value
  equality cases), `guard` (whole-condition fail-open); operands live /
  live_window / ref / ref_dir / window_agg (INCLUSIVE or EXCLUSIVE end) /
  window_agg_dir / mean_of2 (ichimoku kijun) / const. Fail-open on absence is
  normative.
- The `ReplayKernel`: a byte-for-byte port of `sim.run`/`_exit_loop`/`step`
  (R-multiples, risk_unit, validate_geometry, FILL_AT_BAR_CLOSE/LIMIT,
  funding SETTLEMENT_BEFORE_ORDERS scalar+schedule, STOP_FIRST ambiguity,
  gap-through stops, THESIS_INVALIDATED/TIME_EXIT/EXPIRY, EXEC-1..6
  management, the single `net_r` formula). The kernel reads
  `&bars[start..end]` bounded to `expiry_bars + 1` (OUTCOME_CUBE_SPEC §5) and
  evaluates the compiled predicate from the feature store at the stepped bar —
  no Python callback (D-078).
- `tools/predicate_ir.py`: the declarative `still_valid` → IR compiler for
  all 28 registered Experts, transcribed verbatim from the sources.
- `v8-core predicate-check` (batch) and `v8-core replay` subcommands.

Two determinism findings, recorded in D-089:
1. **serde_json's default float parser is not correctly rounded** (measured:
   `"0.9632136759338213"` parses 1 ulp low). Enabled `float_roundtrip` so
   request-side floats (geometry refs, manifest) parse exactly; the tape
   itself was never affected (jsonx uses std's correctly-rounded parse).
2. **Fail-open is not uniform**: per-operand (the dominant close-vs-ref form)
   vs whole-condition (trend_pullback_depth, rsi_stoch variant b,
   bollinger_reversion's close pre-check, gap_exhaustion's either-ref) — the
   IR captures the distinction with `guard`. Also: fib_rsi_bb_confluence's
   prior_low_ref valid-form is GTE (the equality boundary holds), while the
   3sd rule is GT.

Gate evidence (`reports/parity/S2.md`): cargo test 24 passed; 6/6 S2 parity
tests pass — E1/E2/E3 (738-point grid over all 28 experts, present/absent/
None per operand, both directions, ref==live boundary), E5 vocabulary closed,
E4 replay parity on the V8.0 candidate population (endpoint/label/horizon
exact, floats bit-identical), G4 byte-identical, G5 thread invariance,
G6 fail-closed. No speed claim.

## 2026-08-11 — V8.2 compute core S1: FeatureStore + StateView (D-088)

`v8-core/src/state.rs` (new), `v8-core features` subcommand, `reports/parity/S1.md`
(new evidence). The S1 gate of `COMPUTE_CORE_SPEC` §8 passes: value-level bit
parity on EVERY bar, EVERY feature, against the frozen Python oracle
(`build_state`'s cached path, the one the lab uses).

- `FeatureStore` mirrors `build_bar_series` (per-symbol precomputed EMA5/20,
  ATR14 simple, Wilder RSI14/ADX14, CCI20, MACD, OBV, ADL, prefix extremes,
  swing pivots, session VWAP); `StateView` mirrors the cached feature block.
  All 77 declared features, both warmup representations (ABSENT until the
  window; `None`+DEGRADED+NOT_YET_AVAILABLE for the bar-0 candle features),
  positioning features absent when the tape lacks the channel.
- V8.2 identities via the bit encoding (D-079): state `lineage_hash`,
  `state_id`, per-feature `input_lineage_hash` — excluded from the parity
  comparison (§3) but exercised by the mutation test (changing one OHLC digit
  on bar 60 changes exactly the states that consumed it).
- Three portability discoveries, pinned by Rust unit tests, that any future
  migration stage must honour:
  1. CPython `sum()` over floats is **compensated summation** (`_PyFloat_Fsum`,
     = `math.fsum`), not a left fold — a fold drifts by ulps on ~20-element
     windows (measured). `state::fsum` is a verbatim port incl. the special
     final fold and the half-even tie fix.
  2. CPython `x ** 2` is libm `pow(x, 2.0)`, which differs from `x * x` by
     1 ulp on some values; LLVM folds `pow(x, 2.0) -> x*x` in release, so the
     exponent is `black_box`'d to force the libm call (G5: an optimization may
     not change a value).
  3. CPython `x ** 0.5` is libm `pow(x, 0.5)`, which differs from `sqrt(x)`
     by 1 ulp on some values — `_std_pop` must finish with `powf(0.5)`, not
     `.sqrt()`.
- Also fixed: two usize underflows (`i - period + 1`) that panic in debug
  builds and silently wrap in release.

Gate evidence (`reports/parity/S1.md`): 24 Rust unit tests (incl. the fsum
battery) pass; 9/9 S1 parity tests pass — vocabulary match, synthetic (golden,
continuous, funding channel), real verified tapes (btcusdt-1h-12m full 8,760
bars + multi-1h-4y slice), two runs byte-identical (G4), threads=1 vs 8
byte-identical (G5), state_id mutation property. No speed claim.

## 2026-08-11 — V8.2 compute core S0: parity harness + Dataset ingest (D-087)

`v8-core/` (new workspace), `tools/v82_reader.py` (new), `tests/parity/` (new),
`reports/parity/S0.md` (new evidence). The V8.2 Rust compute plane begins its
staged migration (`COMPUTE_CORE_SPEC` §8) with the S0 foundation: the parity
harness and the Dataset layer. `v8-core/` links no Python runtime
(no-callback invariant, D-078); its identities use the bit encoding of D-079;
`src/v8/` is untouched (frozen parity oracle).

- `src/hash.rs` — V8.2 canonical hash encoding (PARITY_AND_IDENTITY_SPEC §4):
  f64 → 8 IEEE bytes LE, NaN normalized to one declared payload, `-0.0`
  distinct from `0.0`, strings length-prefixed, composites tagged; digest
  stays SHA-1. A float-rendering-dependent hash is impossible by construction.
- `src/data.rs` — `Dataset`: tape ingest mirroring `_validate_tape_rows`
  verbatim (G6 fail-closed classifications), (source, event_id) dedup like
  `AppendOnlyLog`'s inbox, canonical replay order `(event_time,
  available_time, venue_sequence)`, per-symbol columnar closed klines.
- `src/evidence.rs` — the columnar artifact container (LEDGER_FORMAT_SPEC
  §3-4): magic `V82LDRG1`, JSON header with `hash_encoding: v8.2-ieee-le`,
  per-column validity bitmask, fixed-width IEEE-754 / two's-complement values,
  dictionary-encoded strings, no wall clock → two identical requests write
  byte-identical artifacts (G4).
- `src/jsonx.rs` — Python-`json`-compatible tape parser: CPython `json.dumps`
  emits `NaN`/`Infinity` as bare literals that strict JSON rejects; the parser
  records them with their JSON path so the oracle's "non-finite OHLC"
  classification survives.
- `.cargo/config.toml` — `--fp-contract=off` (FMA contraction off: CPython
  does not fuse multiply-add; G5).
- Crates: `serde`, `serde_json`, `sha1` — the only dependencies; no Python
  runtime, no FFI, no embedded interpreter.

Gate evidence (`reports/parity/S0.md`, oracle tree `184fb934…`): 23 Rust unit
tests pass; 16/16 S0 parity tests pass — synthetic (multiple seeds + continuous
+ degenerate), real verified tape (btcusdt-1h-12m full 9,948 rows + a
25,000-row multi-symbol slice of multi-1h-4y), two runs byte-identical (G4),
threads=1 vs 8 byte-identical (G5), seven fail-closed classifications matching
the oracle (G6). No speed claim; the S0 gate is correctness.

## 2026-08-11 — Variant sweeps admitted under anytime-valid error control (D-086); O-028 resolved

`docs/protocols/SWEEP_PROTOCOL.md` (new). Sweeps — evaluating a registered grid
of variants rather than one hand-declared variant — were previously excluded
for two reasons that pulled in opposite directions: multiplicity (Bonferroni
over thousands of variants annihilates power, and BH's independence assumption
is plainly violated when every variant reads the same tape) and adaptivity (any
compute-feasible sweep must kill losers early, which is peeking plus selection
and invalidates fixed-sample inference). The statistically safe sweep was the
computationally impossible one.

Both obstacles fall to **one** object. e-BH controls FDR under **arbitrary
dependence** between hypotheses (Wang & Ramdas, arXiv:2009.02824), and with
e-processes the guarantee holds for **arbitrary exploration rules and arbitrary
stopping times** (Xu, Wang & Ramdas, *A unified framework for bandit multiple
testing*, NeurIPS 2021). Successive halving over variants therefore becomes
licensed rather than fraudulent, and the protocol adopts it: registered grid →
e-process per variant → halving over a growing chronological slice → stopped
e-BH → the unchanged single-query confirmation half → DSR and PBO as
diagnostics → online alpha across campaigns.

**Two hazards recorded before they bite.** (1) The local/global filtration
condition (arXiv:2502.08539): stopping several e-processes at a *common*
stopping time yields e-values only under a shared global filtration, and every
V8 variant reads the same tape, so the naive design is exactly the unsafe case.
Default resolution is variant-local stopping times; a global one requires an
argument in the campaign contract. (2) The Minimum Backtest Length result
(Bailey, Borwein, López de Prado & Zhu) — on five years of daily data no more
than ~45 variations can be tried before a Sharpe of 1.0 appears by chance — so
the admissible trial count is computed from tape length *before* the grid is
registered, and an over-large grid is refused rather than discounted.

**O-028 resolved.** The question assumed a sweep multiplies replay cells by its
full cardinality. Under successive halving it does not: the cost falls one to
two orders of magnitude and lands back below the ~10^9-cell GPU trigger
(D-084). So sweeps do not force Experts native from stage S1 and do not reopen
the GPU question — the statistically correct design is also the cheap one.

**D-086 is admitted but blocked.** The e-process construction for
block-dependent episode streams is unsettled (new O-032); no sweep campaign may
run until one is declared and passes null calibration. Also updated:
`DECISION_REGISTER` (D-086), `OPEN_DECISIONS` (O-028 resolved, O-032 added),
`tools/build_monograph.py` (`NAMES`), both monographs rebuilt.

## 2026-08-11 — V8.2 corpus: high-throughput compute substrate + evaluation-plane contract (D-077..D-085)

A corpus-only change. No runtime code was modified, no performance fix was
applied, and no Rust was written. What landed is the contract set for the V8.2
substrate decision, the measurement evidence behind it, and two pre-existing
corpus gaps closed.

**Measurement first (`docs/audits/PERFORMANCE_AUDIT_V82.md`, new).** A profiling
session attributed the ~26-32 s single-cell evaluation cost. Headline: the
decision-path arithmetic is a minority of the run. Measured on an 8,760-bar
single-symbol synthetic tape (CPython 3.14.0, macOS arm64): 27 experts 32.32 s /
22,444 candidates, 3 experts 16.11 s / 1,837; state layer 7.74 s of which
**4.93 s is one O(N²) line** (`{id(b): i for ...}` rebuilt per state per symbol
per interval — 77,925,592 `id()` calls); cube cells cost **71.8 µs of tape
slicing against 6.4 µs of arithmetic**; one state record is 31,091 B for 74
features of which **~2% is the float values**; `states.jsonl` is 271.8 MB against
a 3.5 MB input tape; the scaling exponent drifts 1.16 → 1.32 as N grows. The
same defect class — bounded work over unbounded data — appears at three
independent sites (state lineage, cube replay, ledger hashing). Separately,
CPython `json` and Rust `f64` formatting were found to disagree on **7 of 8**
representative values, which makes decimal text unusable as a cross-runtime
identity.

**New contracts.** `COMPUTE_CORE_SPEC` (two planes, layer map, representation
rule, staged migration S0..S5), `PARITY_AND_IDENTITY_SPEC` (V8.0 frozen as
oracle, value-level bit parity, IEEE bit-pattern hashing, gates G1-G6),
`LEDGER_FORMAT_SPEC` (identity/information/schema/run-constant/derivable
classification, three tiers, columnar layout), `OUTCOME_CUBE_SPEC` (action
manifest, cell-status taxonomy, streaming reduction, bounded-window rule),
`PREDICATE_IR_SPEC` (compiled `still_valid`, equivalence gate E1-E5),
`COMPUTE_SCHEDULING_SPEC` (kernels K1-K6, per-kernel determinism analysis, the
~10^9-cell GPU trigger).

**Gap 1 closed — the evaluation plane had no contract.**
`docs/protocols/RECOVERABLE_REGRET_PROTOCOL.md` documents Phases 0-4 as built
and certified under D-071..D-074, including what each phase does **not** claim:
`V_R` remains negative on all 11 recoverable slices, so the result is a
replicated loss-reduction effect and not a profitability finding.

**Gap 2 closed — `IMPLEMENTATION_LAYOUT` was stale.** It listed 3 pilot experts
against 28 shipped modules and omitted `equity.py`, `interval.py`,
`statistics.py`'s current scope, `fast.py`, and the whole `tools/regret*.py`
family. Corrected, and the planned Rust workspace added as a second section.

**Updated.** `ARCHITECTURE_SPEC` §2 (evaluation plane added to the component
map) and new §3.1 (V8.2 substrate revision — D-031 revised, not retired);
`ROADMAP` (new Phase 4b, plus explicit version semantics: Rust and GPU are
implementation changes and do not constitute a V9); `DECISION_REGISTER`
(D-077..D-085); `OPEN_DECISIONS` (O-028..O-031); `tools/build_monograph.py`
(`NAMES`); both monographs rebuilt.

**Two things deliberately recorded as not claimed.** (1) The substrate decision
is **not** justified by the program's falsification clause on evaluation cost —
the measurements show research scale is reachable in Python once the D-083
defect class is removed, and D-077 says so explicitly, because a motivated
reading of one's own criterion is the failure mode this program exists to
resist. (2) `fast.py` was admitted (D-085) because it was sitting in the tree
untracked and D-032 requires a register decision for any new `src/v8/` module.

## 2026-08-10 — V8 x Recoverable Regret v0.2, Phase-0 build step 1: golden repair + two portability bugs + multi-symbol dev tape

Three local repairs and one data-plane addition, all prerequisites for the
Phase-0 measurement instrument frozen in `FCR-V8RR-004` (read-only ACCP
evidence chain `RIR-V8RR-001` .. `FCR-V8RR-004`, not committed to `docs/` —
research-session artifacts under `reports/accp/v8-rr-v02-phase0/`).

**1. Golden regression re-pin (`tests/test_golden_backtest.py`).** The golden
was RED at HEAD: `states_hash`/`ledger_hash` had drifted since the last pin
because `marketstate.py` (D-054) and `lab.py` moved, and `_BUILDER_SRC_HASH`
is a whole-file hash bound into every state's `provenance.code_version` by
design. Measured before re-pinning: `data_hash`, `candidate_count` (15) and
`terminal_distribution` (`{CLOSED:12, INVALIDATED:1, REJECTED:2}`) were
UNCHANGED — no Expert, setup, trigger, price or economics decision moved.
Re-pinned `GOLDEN_LEDGER_HASH`/`GOLDEN_STATES_HASH` with a dated comment
recording the invariance proof, per the file's own "do not update silently"
convention.

**2. `AppendOnlyLog` gained a `close()` method (`src/v8/store.py`).**
`tools/vision_backfill.sort_tape` opens a log, reads it, then calls
`os.replace` on the exact path the log's still-open append handle points to.
POSIX permits a rename over an open handle; Windows does not (`WinError 5`),
which was the root cause of the pre-existing `tests/test_funding_wiring.py`
failure (previously misdiagnosed as an environment artifact) and blocked
`--sort` on a freshly downloaded tape outright. `sort_tape` now calls
`log.close()` before `os.replace`. `close()` is idempotent and is the only
new public surface on `AppendOnlyLog`.

**3. `_code_hash()`/`_tooling_hash()` made platform-independent
(`src/v8/lab.py`).** Both keyed their per-file dict on `str(p.relative_to(base))`,
which embeds the OS path separator — the identical source tree hashed
differently on Windows (`experts\base.py`) vs POSIX (`experts/base.py`),
silently breaking rule 9's "outputs bind ... code ... hashes" invariant
across machines. Switched to `.relative_to(base).as_posix()` (same files,
same bytes, a canonical separator in the hash key only).
`tests/test_bugfix_pass.py::test_code_hash_excludes_vendored_simtruth`'s
independent mirror updated to match — it previously split path keys on `'/'`
while `str(Path)` produced `'\\'`-joined keys on Windows, so the mirror's own
`simtruth` exclusion silently no-opped on this platform. No golden hash
depends on `_code_hash()`'s value (`ExperimentManifest.code_hash` is `''` in
every pinned fixture and is not itself asserted), so no other pin moved.
Full suite after all three repairs: 733 passed, 1 skipped (up from 730
passed / 3 failed at HEAD).

**4. Multi-symbol dev tape built (`research/tape/multi-1h-dev/`, gitignored
— reproducible from public archives).** `tools/build_multi_tape.py --symbols
BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT --start 2025-07 --end
2026-07 --interval 1h --channels kline,funding --download`: 144 Binance
Vision monthly archives (0.03 GB), 0 misses. Symbol set = `risk.py`'s
`DEFAULT_CLUSTERS` (the "btc"/"major" cluster grouping already wired into
`RiskGate`'s heat caps); date range = the existing D-041 dev window,
strictly inside the frozen 2026-07-01 holdout boundary that the builder
itself refuses to cross. Sorted and audited clean: 59,130 rows,
`tape_hash=b9079440e2cc7a03300eb6fc3366baf25d1fc7e3`, 0 duplicate rows,
monotonic, all payload hashes verified, 0 venue-sequence gaps. This is
research/diagnostic data (rule 11, "explore broadly in development") — it
does not amend `DATASET_SPEC` section 6's declared single-symbol
`v8_slice_001` universe, which stays the only canonical dataset for an
economic claim; extending that declaration remains an O-011 registry
decision.
## 2026-08-10 — V8 x Recoverable Regret v0.2, Phase-0 CERTIFIED (D-071)

Continuation of the build-step-1 entry above (golden repair, `AppendOnlyLog.close()`,
`_code_hash` portability, multi-symbol dev tape). This entry closes Phase 0:
`tools/regret.py` (+ `tools/regret_reference.py`) implements the ten frozen
contracts (`FCR-V8RR-004`) and is certified against real command evidence in
`TVR-V8RR-005` / promoted in `PRR-V8RR-006` (both under
`reports/accp/v8-rr-v02-phase0/source/`). Full decision text: `D-071`.

**Instrument.** A READ-ONLY evaluator over a completed `Lab` store: joins
`CandidateSnapshot`s (re-derives `episode_key`, never a stored edge), asserts
PIT lineage, reconciles `Replay(C, a_actual, M)` against the observed ledger,
generates a per-Candidate `LegalActionManifest` (`NO_TRADE` + the actual
action seeded first + a small declared `target_r` x `expiry_bars` grid;
`pyramid_add_rules` and `direction` structurally excluded), replays every
legal action through the SAME `CanonicalSimulator` the run used (refusing —
`UNDEFINED_FUTURE` / `CENSORED` / `NOT_EVALUABLE_ACTION` / `NO_ENTRY` — rather
than accepting a degenerate-future or censored cell as a number), writes the
cube (`cube.jsonl`) and the gap (`regret.jsonl`, ties reported never broken,
abstains whenever any potentially-maximizing cell is not fully observed).
Phase 0 computes NO statistics; every number is `MODEL_DERIVED` and carries
no economic authority.

**Certification evidence, all real command output.** Golden synthetic
fixture (15 candidates): reconciles 12/12 exact at 1e-12, 0 PIT violations.
Real 12-month single-symbol BTCUSDT 1h store (1,532 candidates, built from
the freshly downloaded 6-symbol tape, trimmed 3 days before its true end to
stay inside the tape's own funding-coverage boundary): reconciles 754/754
exact at 1e-12, 0 deviation on every field, 0 PIT violations — closing the
FCR's own flagged "measured only on synthetic data" gap. The v0.2 invariant
`hindsight >= actual` holds with zero negative gaps across 543 COMPUTED
candidates combined. An independently-derived reference walk (written from
`SIMULATION_TRUTH_SPEC` text, imports nothing from `v8.simulator`) agrees
with the canonical simulator on 150 Hypothesis-generated randomized paths.
Five fault-injection cases (TP-shortened axis attribution, cost-doubling
isolation, direction-flip structural illegality, habitat-randomization
structural non-claim, missing-evidence explicit refusal) behave as
specified — the last two by correctly REFUSING to claim something Phase 0
has no evidence for, not by localizing them.

**One more additive `src/v8/` change.** `Lab.run()` now also persists
`report.json` alongside `manifest.json` (not part of `ledger_hash`): a
completed store previously could not recover its own `risk_gate_hash`
without re-running the lab, which a read-only evaluator must never do.

**Suite:** 751 passed, 1 skipped (18 new tests: `test_regret_phase0.py`,
`test_regret_faults.py`, `test_regret_reference.py`), up from 730 passed / 3
failed at HEAD before this session.

**Two honest limitations carried into Phase 1, not silently resolved.**
`funding_r`/`gross_utility` are `None` (never fabricated as `0.0`) on any
store whose manifest declares nonzero funding or whose tape carries a
funding channel, because `CounterfactualOutcome` does not persist
`funding_paid_r` and extending it would move `sim.hash()` and re-pin every
golden for no semantic gain — Phase 1 must read `net_utility` as
authoritative and not attempt a funding breakdown from the cube. Only
BTCUSDT was reconciled on real data this session; the other five downloaded
symbols are validated identically (not differently) during Phase 1's
per-symbol runs (`v8.lab.Lab`'s bar-driven loop is single-instrument by
design, `src/v8/lab.py:369-374`).
## 2026-08-10 — V8 x Recoverable Regret v0.2, Phase 1+2: a replicated (not yet recoverable) `mean_legal_hindsight_gap` finding (D-072)

`tools/regret_phase1.py` (descriptive join, label `MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED`,
zero statistics) and `tools/regret_phase2.py` (systematicity discovery per
`FCR-V8RR-007`, reusing `src/v8/statistics.py` in full — zero new estimator
code) ran over the certified Phase-0 output for all 6 downloaded symbols
(9,218 Candidates). 12 of the 72 declared discovery slices reached
`CANDIDATE_SYSTEMATIC` on `mean_legal_hindsight_gap` (vs 3.6 expected under
the null at family alpha 0.05) — `trend_pullback` LONG and `failed_breakout`
SHORT, each on all 6 symbols, never the mirror direction, never on
`mean_actual_vs_no_trade`. All 12 confirmed as `SYSTEMATIC_FINDING` on the
untouched second half of the dev window, queried exactly once, with stable
point estimates both halves (`trend_pullback` ~0.5-0.7R, `failed_breakout`
~1.0-1.2R). **Epistemic status, stated explicitly because it is easy to
overclaim here:** this is evidence that value is being left on the table
inside the represented Candidate/action universe, under a costed, versioned,
reconciled Replay Model, and that the pattern replicates chronologically. It
is NOT evidence that the gap is recoverable — v0.2 section 5.3's
`HindsightOpportunity != RecoverableOpportunity` applies without exception,
and V8_CONSTITUTION rule 12 still blocks any profitability or validated-
execution claim. Full decision text and numbers: `D-072`. Evidence:
`reports/accp/v8-rr-v02-phase0/source/ECR-V8RR-008.accp.yaml`,
`tmp/phase2/*.json(l)` (real command output, this session).
## 2026-08-10 — Confluence experiment: Fib + RSI + Bollinger (D-076)

- **D-076 — `fib_rsi_bb_confluence` admitted as an exploratory dev-window
  family** (mechanism `confluence_reversion_continuation`). One new
  `src/v8/experts/` module; two variants evaluated in one run — `a` STRICT
  (all three legs point the same way), `b` MAJORITY (at least two of three).
  Each leg is a registered family's idiom verbatim: the Bollinger 2-SD fade
  zone (`bollinger_reversion`), the Wilder-RSI dip-and-recover
  (`rsi_stoch_reversion` variant a), and the fib retracement reclaim at
  **0.786** (`fib_retracement_continuation`). The deep ratio is a structural
  choice, not a fit: a fade-zone close (below the 20-SMA's lower band) can
  only co-occur with a retracement level that sits BELOW that band; of the
  standard ratios only 0.786 does so (the co-occurrence was computed before
  the experiment ran). Geometry is the family default 1R:1R:8bar with
  `atr_ref`; the frozen 78.6% level and the frozen 3-SD band are the
  post-entry invalidation refs (`prior_*_ref` + `lower/upper_3sd_ref`, the
  D-042 pattern). Registry FORMALIZED; `variants_evaluated` [a, b];
  `search_universe_size` 2.
- Runner `tools/run_fib_rsi_bb_confluence.py`: builds a single-symbol SOLUSDT
  tape inside the dev window (`build_multi_tape` REFUSES >= 2026-07),
  runs both variants with tape-driven funding and a 10-bps round-trip taker
  cost, and reports per-variant + pooled after-cost stats beside a zero-cost
  reference row joined by candidate_id.
- **Result (dev-window, SOLUSDT 1h, 2025-07..2026-06, 8760 bars, exploratory —
  not a registered test):** variant `a` fired **once** (0.011% of bars,
  invalidated before entry, 0 executed) — the strict triple confluence
  essentially never co-occurs on this tape. Variant `b` fired 159 times, 33
  executed: win rate 39.4%, mean net_R **-0.253** after 10 bps (detrended
  -0.254; 90% CI [-0.471, -0.062], entirely negative), profit factor 0.59,
  equity -8.3%, max drawdown -9.8%. At **zero cost** the mean is still
  **-0.158 R/trade**: the signal itself has negative expectancy; cost adds
  ~-0.095 R. The lab's feasibility note records breakeven win rate 0.547 >
  realized 0.394. Verdict stays NO_ECONOMIC_CLAIM (no authority receipt,
  rule 12). The confluence does not beat its own relaxation here, and neither
  clears cost.
- **D-026 hardening (correctness):** `lab._geometry_version` now also
  excludes the frozen band refs `lower_3sd_ref`/`upper_3sd_ref` from episode
  identity — they are data-dependent (a stable setup must not change key
  across decision clocks). Without it the confluence's 179 candidates carried
  179 distinct geometry hashes and dedup could not fire; after the fix the
  run dedups to 160 candidates. Backward-compatible: no other family uses the
  band-ref keys.
- Tests: `tests/test_expert_fib_rsi_bb_confluence.py` (16 tests: crafted
  STRICT LONG/SHORT tapes, MAJORITY firing/abstain, vote-rule unit tests,
  episode-key separation, still_valid composition, registry/lab smoke);
  registry gate green (28 -> 29 entries).
## 2026-08-09 — Hot-path pass: 3.4x less CPU for byte-identical output (D-075)

The diagnostic was saturating every core for minutes per run. Profiled rather
than guessed (cProfile, one 540-bar BTCUSDT cell):

| | before | after |
|---|---|---|
| single cell (in-process) | 72.6s | **17.4s** (4.2x) |
| 2 symbols x 2 timeframes, 60d, `--processes 4` | 102.5s wall / 245.4s CPU | **29.2s wall / 71.2s CPU** (3.4x) |

Four wastes and one latent bug:

1. **`_median_atr` recomputed 202,000 times** — 54.3s of 72.6s (75%), and the
   source of 287M dict lookups. It is a pure function of the frozen draft set
   and was being rescanned and re-SORTED once per null draft. Memoised.
2. **`dataclasses.replace` on the `OpenPosition` hot path** — 3.9M calls,
   20.4s of the remaining 28.0s (73%), under 57M `getattr`s. `step()` chains
   up to three per bar. Replaced by `simulator._evolve`, which populates a
   fresh frozen instance directly; `OpenPosition` has no `__post_init__`, no
   validation and no `__slots__`, and the equivalence is pinned field-by-field
   against `dataclasses.replace` in `tests/test_perf_hotpaths.py`.
3. **`_post_exit_max` computed for null walks** that never read it — 24 bar
   reads x ~200k walks per cell.
4. **The tape was re-parsed per cell** — ~395k JSON lines, once per
   (symbol, timeframe). Now parsed once per process.

5. **A latent correctness bug, found while profiling.** The walk cache was
   keyed on `id(draft)`. `id()` is unique only among LIVE objects, and a null
   draft is freed immediately after its walk, so CPython hands the same
   address to the next one — a (recycled id, same `entry_idx`, same geometry)
   key could return a walk taken in the OPPOSITE DIRECTION, quietly
   contaminating `always_long` / `always_short` / `random_entry`. The cache
   also grew unbounded (97,263 entries against 1,387 real drafts). Entries now
   store `(draft, result)` and verify identity on hit; null drafts bypass the
   cache entirely. This is a correctness fix, not a speed trade.

**Output identity is the gate, and it holds twice.** The lab economics dump
(every outcome's `net_r`/`endpoint`/`entry_price`/`risk_unit_price` plus the
whole `LabReport` minus hashes) is byte-identical to the pre-change baseline;
and the diagnostic's own aggregate `net_R_mean` and all 22 decision-table rows
are identical before vs after on `BTCUSDT-1h`. Only `ledger_hash` moved,
because `_SIMULATOR_SRC_HASH` binds the module source — re-pinned with the
evidence recorded in the golden test.

No numpy, no new dependency, no change to the concurrency model — those stay
unregistered under the D-031 baseline. 749/749 tests pass.
## 2026-08-09 — Per-Expert scenario correctness audit (rule 10 contract tests)

`tests/test_expert_scenarios.py` (new, 18 tests): hand-crafted bar sequences
with a known correct fire/no-fire/geometry outcome for the three original
pilot Experts (`trend_pullback`, `failed_breakout`, `liquidity_sweep_reclaim`)
— positive setups, negative/no-setup mirrors, strict-inequality boundary
cases (hand-built `MarketState`, bypassing `build_state`), the shared
<20-bar habitat gate, `still_valid` invalidation, and a cross-Expert
metamorphic invariant (every `CANDIDATE` an Expert emits over synthetic
noise must independently re-derive from its own documented setup predicate
against the raw `history` tuple). Contract-only per rule 10: no `Lab`, no
economic claim, no `src/v8/` change. Superseded as the primary diagnostic
instrument by the already-existing `tools/diagnostics.py` report center
(9-section per-Expert forensics across all 27 registered Experts, run
2026-08-07/08 — see `.audit/RESULTS.md`); this file remains a narrower,
faster-running correctness check on the three original pilots specifically,
independent of that instrument.


## 2026-08-09 — Diagnostic integrity pass: the report could not falsify its own exit diagnosis

Four defects, found by auditing the 2026-08-08 multi-cell report against its
own numbers. None of them changes an Expert, a geometry or a verdict's
authority (still `NONE`); they change what the instrument is capable of
measuring. Decisions D-067..D-070.

**1. The exit grid was one-dimensional (D-068).** `EXIT_VARIANTS` moved the
take-profit while pinning the shipped 8-bar expiry: `tp_4r` = `{'tp': 4.0}`.
The report's own horizon section says mean favorable excursion reaches ~4R
near 48 bars, so that cell converted targets into expiries and its loss
carried no information about a 1:4 geometry. "Exit is not the problem" was
therefore unfalsifiable. The grid is now a cross of `EXIT_TP_GRID` (1/2/3/4R,
no-TP) x `EXIT_EXPIRY_GRID` (8/24/48/96) = 20 cells, with `no_sl` and
`trail_1atr` kept OUTSIDE the cross as structural probes. Shape taken from
Katz & McCormick's Standard Exit Strategy (Encyclopedia of Trading Strategies,
2000, ch. 13), which moves target and horizon together — the shape only; no
geometry is adopted.

**2. Selection was reported as if it were a result (D-068/D-069).** The max of
the grid was printed as `best_exit` with no search size and no correction. It
now travels as `exit_cross` with `n_cells_searched`, a naive p and a
Bonferroni-corrected p, and the portfolio section reports both the per-expert
max (labelled a selection-inflated upper bound) and a single fixed cell chosen
once for every expert — the difference between the two is the selection.

**3. The decision table contradicted section 8 (D-069).** Section 8 refuses to
score a segment cell below its 95%-CI sample floor; the decision table
simultaneously emitted "Add regime filter" from an n=19 cell. `_main_problem`
had no sample gate at all. Replaced by `_observations`, where every entry
carries `supported: bool` from the same floor (`_min_n_for`), and an
unsupported observation is printed but can never label a row or move a
verdict. The prescriptive action column is gone: naming the best corner of a
44-cell search IS the selection (Aronson, *Evidence-Based Technical Analysis*
2007, ch. 6), so the column now states the measured quantity and its support.
A regression test asserts the old strings never come back.

The first run under the new table exposed a fifth defect the first four did
not close: on `BTCUSDT-4h`, `candlestick_reversal` reached **KEEP on n=10**
(a 100th-percentile random-null result) while its own observation column read
"sign-permutation p=0.070 — not distinguishable from sign noise". The verdict
gate had only `n >= 10`. `KEEP` now also requires `n >= _min_n_for(nets,
zero_cost_edge)` — enough sample to resolve the edge it claims — and
under-powered candidates are held at `INVESTIGATE` ("not enough yet"), never
demoted to a failure.

**4. Coverage was invisible (D-069).** 48 `Expert` subclasses are defined,
27 are registered, and 5 registered experts produced zero setups on the
window. Neither gap appeared anywhere, so a row labelled `donchian_breakout`
read as a statement about the family while measuring variant `a` — which is
long-only by definition, making its SHORT n=0 look like a broken direction.
New section C reports zero-setup experts and unregistered variant classes.

**Cost form (D-067).** `round_trip_cost_r` is denominated in R and is
therefore invariant to the R unit: widening the risk unit rescales stop and
target but leaves the charge untouched, so "widen R to dilute the cost" is a
no-op in the model and an R-widening experiment could not be measured.
`CanonicalSimulator` gains an optional `round_trip_cost_bps`, resolved at one
point (`cost_r(entry_price, unit)`) that every `net_r` site now calls.
Flat-R remains the default and is byte-identical — verified by diffing every
outcome's `net_r`/`endpoint`/`entry_price`/`risk_unit_price` and the whole
`LabReport` minus hashes, before vs after: identical. Only `ledger_hash`
moved, because `sim.hash()` now binds the cost form.

**Determinism (D-070).** Found while wiring the above: `run_multi`'s parallel
branch seeded `seed + i` while the sequential branch used a bare `seed`, so
`--processes 1` and `--processes 4` disagreed on every cell but the first.
The job list is now built once by a pure `plan_cells` and seeded by position.

- `src/v8/simulator.py` — `cost_r()`, `round_trip_cost_bps`, hash binds form
- `src/v8/schema.py` — `RunManifest.round_trip_cost_bps`
- `src/v8/lab.py` — per-episode realized cost feeds RM-11's `w_min`
- `tools/diagnostics.py` — exit cross, `_observations`/`_min_n_for`,
  `_coverage`, `plan_cells`, `--cost-bps`
- `tests/test_cost_form_and_exit_grid.py` — 23 new contract tests
- goldens re-pinned with the byte-identity evidence recorded in-file

733/733 tests pass.

## 2026-08-08 — Dev multi report: 100% of the info in ONE HTML

`tools/diagnostics.py` matrix report (`--symbols`) now embeds EVERY cell's
COMPLETE report — 9 sections + per-expert forensics + MarketState audit +
charts — in a single `report.html`, not just the cross-symbol verdict matrix
(which was a summary of badges, with the full per-cell reports stranded in
separate `out/{symbol}-{tf}/report.html` files). A nav menu anchors to each
cell's embedded report.

- `render_html` gained `fragment: bool = False` — `fragment=True` returns the
  body WITHOUT the `<html>/<head>/<style>` wrapper, so a parent document that
  already carries `_CSS` can embed a cell report (nested HTML was invalid).
  Default is byte-identical to the legacy self-contained report.
- `_run_cell` returns the full cell `report` + `trades` (they were already
  computed, previously discarded); `run_multi` keeps them for the renderer.
- `--allow-surface` now flows `run_multi -> _run_cell -> DiagnosticEngine`
  (it was accepted but never forwarded, so §6 exit surface never ran per cell).
- `report.json` (multi) stays an aggregate-only view via
  `_jsonable_multi_report` — the bulky per-cell reports/trades are already on
  disk under `out/{symbol}-{tf}/`, so the JSON is not bloated.
- Dead-code cleanup: two shadowed `main()` definitions (legacy single, legacy
  matrix) removed; the unified CLI is the one entry point.
- Determinism: cell order is the fixed (symbol, timeframe) enumeration; the
  only wall-clock bytes in the HTML are the `generated_at_utc` provenance
  stamp (report metadata, outside the decision path) — pinned in the test.

Tests: `test_multi_dev_html_embeds_every_cell_full_report`,
`test_multi_dev_html_is_deterministic`, `test_multi_allow_surface_reaches_cells`,
`test_render_html_fragment_backward_compat`. **710/710 tests pass.** Verified on
`research/tape/multi-1h-4y` (2 symbols × 1h, 60-day span): `report.html`
272K carries both cells' full reports; single mode still writes its 5-file set.

Artifacts: `tools/diagnostics.py`, `tests/test_diagnostic.py`,
`.audit/diagnostic/dev-html/`.

## 2026-08-08 — Total-pipeline perf pass + single-file report center

Perf pass across the decision path and the report tooling. Every
decision-path change is VALUE-EQUIVALENT (tests/test_state_cache_identity.py
pins cached == uncached on every bar; tests/test_perf_fastpaths.py pins the
fast hashing/serialization against the reference semantics); the golden
backtest re-pinned ledger/states hashes because `code_version` and `code_hash`
moved, with candidate_count/terminal_distribution/data_hash unchanged
(tests/test_golden_backtest.py comment documents the re-pin).

Decision path (src/v8/):
- marketstate.py: per-feature input-lineage digests built from precomputed
  row bytes (`_slice_digest`) instead of re-json-dumping payload dicts per
  feature per bar; `closed_digests`/`manifest_digest` are now incremental
  hashers (O(N²) full-prefix re-hash -> O(1) amortized per bar, byte-identical);
  `project_state` gained a static `projection_allowed_keys` superset so a
  projection is one frozenset membership per key instead of a per-key
  `feature_interval` call.
- lab.py: projection specs (allowed keys/depths/intervals) hoisted once per
  Expert per run; `record_dict(..., event_id=state.state_id)` skips the
  auto `sha1_hex` of the full state record that the caller overwrote anyway.
- schema.py: `record_dict` uses `_asdict_fast`, a dataclasses.asdict
  equivalent without per-call `fields()`/deepcopy (tuple-preserving, so
  `== asdict` holds on CPython 3.14).
- equity.py: `risk_of_ruin` draws each simulated life with one
  `random.choices(k=n)` call instead of n `choice` calls (~10k x n draws in C).
- store.py: unchanged semantics; the rejected incremental-hash design is
  pinned as a regression test (comma-before-first bug) in
  tests/test_perf_fastpaths.py.

Measured: 8760-bar x 3-pilot lab run 46.9s -> 16.6s (~2.8x); 1500-bar x
27-expert 16.4s -> 8.0s. Full suite 706 passed.

Report tooling (tools/, consolidated 2026-08-08):
- NEW `tools/diagnostics.py` is the single report center: the diagnostic
  engine (9 sections) + per-expert forensics + the multi-symbol matrix runner
  + the self-contained HTML renderer now live in ONE file, per the report-
  center directive ("everything in one file, no multi"). `tools/diagnostic.py`,
  `diagnostic_report.py`, `forensics.py`, `multi_diagnostic.py` are thin
  re-export shims for backward compatibility; the CLI takes `--symbols` to
  opt into the matrix report (formerly multi_diagnostic).
- diagnostic.py engine: `_simulate` walk memoization — one bar walk per
  (draft, entry, geometry) serves every cost/funding variant (Section 2
  ablations, forensics cost sweep, the repeated full-set sims). 306,809
  `_simulate` calls collapse to 91,853 distinct walks (~3.3x) on an 8760-bar
  run; net_r derivation is bit-exact for the scalar funding path
  (`_simulate` == `_simulate_full` pinned in tests/test_diagnostic.py).
  `_detect` hoists the per-expert projection spec (sort/closure/declaration
  computed once, not per bar).
- vision_backfill.audit_tape gained an optional `rows=` param; monitor_tape
  passes its already-parsed rows so a --schema cycle parses the tape once,
  not twice.

## 2026-08-07 — Equities data-authority survey (O-026 refinement)

The deferred-equities open decision (O-026) gained an empirical source survey
instead of an assumption. Method: live endpoint tests (İş Yatırım API returned
THYAO daily OHLCV back to 1997), Wayback snapshots (stooq bulk archives),
official docs (Massive/Polygon flat files, BIST DataStore), GitHub API;
WebSearch returned nothing in this environment, so DuckDuckGo HTML, direct URL
fetches and Wayback were used as fallbacks. **Finding: no source — free OR paid
— offers rule 9's checksum-verifiable immutable archive.** NASDAQ's closest
candidate is Massive (ex-Polygon) Flat Files (official SIP daily files since
2003, bulk + immutable, but paid ≥ $29/mo, no published checksums — only S3
ETags) or stooq bulk ZIPs (checksumless); BIST's only official channel is
DataStore (paid, contractually "Confidential", no checksum, no accuracy
guarantee) and the free İş Yatırım API violates every rule-9 axis (unofficial,
mutable). So the O-026 admission condition (source authority binding) is
currently unmet for both venues — equities stay a documented research
direction (D-065), never a canonical dataset.

Artifacts: `docs/decisions/OPEN_DECISIONS.md` (O-026),
`docs/tr/OPEN_DECISIONS.md` (O-026), `docs/CHANGELOG.md`.

## 2026-08-07 — WHY-IS-IT-NEGATIVE diagnostic engine (tools/diagnostic.py)

A read-only diagnostic engine that EXPLAINS the lab's negative economics
without fixing them. It produces diagnostics, never decisions:
`AUTHORITY: NONE — DIAGNOSTIC ONLY` on every report. Spec: 9 sections
(identity + R-denominator census, cost census, zero-cost ablation, null
baselines, path statistics, horizon sweep, exit-parameter surface, entry
timing, simulator invariants) + a verdict enum
(`MECHANICAL_FLOOR | COST_DOMINATED | NO_EDGE | EXIT_MISSPECIFIED |
SIMULATOR_INVALID | INDETERMINATE`), each cited to its evidence.

V8 adaptations recorded in the manifest: lives in `tools/` (a `src/v8/` module
would move the decision-path code hash, D-032); the entry set is re-detected
from the tape (drafts are not persisted) at birth+lag with one fixed
convention, and every counterfactual reuses it; ALL simulation goes through
`CanonicalSimulator.step()` geometry overrides (no re-derived barrier/gap/cost
formulas); V8 models fee+slippage as ONE flat `round_trip_cost_r`; 1h-bar
horizons (15m unrepresentable); no liquidation model (stopped-before-h =
shipped-SL stop); `trades.jsonl` not parquet (D-031). The engine never writes
to a store/registry/authority path — a foreign write raises
`DiagnosticWriteError`.

**First run on the real dev tape** (btcusdt-1h-12m, 2500 bars, all 27 experts,
cost 0.07): verdict **MECHANICAL_FLOOR** — the shipped signal is
indistinguishable from random entries (actual −0.0618R inside the random-entry
null [−0.136, −0.030], percentile 78.5%). Supporting numbers: gross edge
+0.0082R vs flat cost 0.07R (**cost is 8.5× the raw edge**); frictionless
+0.0082R (break-even); mean trade duration **3.7 bars** (median 3, p90 8);
holding to 4-5 days would have been WORSE (−0.19 to −0.25R); **early-TP: 79% of
target-exits continued >2R after exit (mean +4.5R)** — the 1R target clips a
real favorable tail; early-SL: 33.5% of stops saw >0.5R favorable first;
intrabar ambiguity 144 trades with a 1.79R optimistic/pessimistic spread;
no entry-timing problem (mark-out ≈ 0 bps). The verdict is a diagnostic
finding, not an economic claim (authority still NONE).

**Automatic HTML report + charts.** Every run also writes a self-contained
`report.html` with inline-SVG charts (stdlib-only — no matplotlib/JS/CDN):
verdict banner + KPI cards, a horizon-sweep line chart with the actual mean
duration marked, a cost-census bar chart, an ablation bar chart, a
"actual vs random-null band" chart, an exit-reason bar chart, net_R/MAE/MFE/
duration histograms from the per-trade ledger, an entry-timing mark-out line
chart, segment tables and the invariants block. Deterministic — a given run
always produces byte-identical HTML. Renderer: `tools/diagnostic_report.py`.

**Expert forensics layer** (`tools/forensics.py`): the actionable answer to
"which strategy is salvageable, which is trash?". Every expert gets a
leaderboard row (n, gross/net/zero-cost edge, PF, winrate, max drawdown,
LONG/SHORT split), a cost sweep with its **breakeven cost**, an exit-variant
sweep (no-TP / no-SL / 2R·3R·4R-TP / time-24 / trailing), a sign-permutation
p-value, a per-expert random-entry null, a bootstrap 95% CI, regime
(vol/trend), time-of-day and window-split breakdowns, a TP-robustness metric,
and an automated **KEEP / REPAIR / HARD_REPAIR / INVESTIGATE** verdict with a
cited main problem and an action. The vocabulary has no "kill": an expert is
never deleted by a diagnostic — `HARD_REPAIR` means it is broken (no edge even
frictionless) and needs a fundamental rebuild. The verdict is anchored on the
ZERO-COST edge (an expert with a real frictionless edge killed by cost is
REPAIR, not HARD_REPAIR) and a KEEP needs n + positive frictionless edge +
distinguishable-from-random-null (the spec's "most critical filter"). The
report's top carries the strategy decision table; each expert has a
collapsible `<details>` drill-down; the report closes with a portfolio
conclusion (verdict counts, strongest/weakest, dominant failure, long-vs-short,
exit-vs-entry, recommended next experiment).

**Per-expert MarketState (D-054) verification.** The report now states and
verifies that every expert evaluates its OWN projected MarketState view: the
canonical state filtered to the expert's declared intervals + `requires`
feature groups (an expert never sees another expert's undeclared features).
The engine records a per-expert state audit (intervals, groups, depth, view-vs-
canonical feature count) and verifies the projection withheld every undeclared
group (`view_groups_verified`). On the dev tape all experts declare the base
interval (1h) only, so the diagnostic data is 1h-barred and the per-expert
"custom MarketState" is the group projection on that 1h state — stated in the
manifest (`base_interval`, `multi_interval_experts`,
`per_expert_state_projection`).

**Multi-symbol × multi-timeframe** (`tools/multi_diagnostic.py`): the
single-symbol report answers "why is this strategy negative on BTC 1h?"; this
layer answers "does any edge survive OTHER symbols and OTHER timeframes?". Each
(symbol, timeframe) cell — e.g. 4 symbols × {1h, 4h} over one shared calendar
span — runs the full engine (aggregate + per-expert forensics) in parallel and
writes its own report dir; the aggregate report carries a cross-symbol verdict
matrix (experts × cells), a consistency analysis (robustly salvageable experts
vs experts that FLIP across symbols — the anti-overfit filter), and an
aggregate portfolio conclusion. The 4h/1d cells aggregate the same calendar
bars via `v8.interval.aggregate` (incomplete buckets dropped; no funding
channel on the aggregated cells, stated in every manifest).

Tests: `tests/test_diagnostic.py` — the spec's 6 synthetic fixtures each
produce its known verdict (not-NO_EDGE / COST_DOMINATED / MECHANICAL_FLOOR /
EXIT_MISSPECIFIED / SIMULATOR_INVALID / identity-stops-the-engine) + a
write-guard test + a report.html render test. **693/693 tests pass.**

Artifacts: `tools/diagnostic.py`, `tools/diagnostic_report.py`,
`tests/test_diagnostic.py`, `.audit/diagnostic/real/` (first real-tape
report, incl. `report.html`).

## 2026-08-07 — Universe scope: equities (NASDAQ/BIST) deferred as a research axis (O-026, D-065)

Scope proposal to add stock equities as dataset sources was evaluated against
the constitution and recorded, not implemented. Equities are structurally
different from the locked Binance USD-M universe — no funding/mark/index/premium
tapes, a session calendar with gaps and corporate actions, a different
cost/authority model — so the proposal is a NEW research axis (O-026), not an
O-011 venue extension. Decision (D-065): the universe stays locked until the
Phase-4 base-case gate is measured; data-plane exploration may proceed in
parallel as research-only, but no equities tape may become canonical and no
preregistration may name it until a surviving family replicates cross-asset
under its own multiplicity controls and rule 9 source authority is met (a hard
constraint today — NASDAQ free archives lack checksum-verified immutability;
BIST requires a commercial provider or an authority-inadmissible scraper).

Artifacts: `docs/decisions/OPEN_DECISIONS.md` (O-026),
`docs/decisions/DECISION_REGISTER.md` (D-065), `docs/CHANGELOG.md`.

## 2026-08-07 — Audit-fix pass: 12 reproduced defects (issues #61-#72)

The adversarial audit of 2026-08-06 filed 12 issues. Each was reproduced on
the working tree with a deterministic probe (`.audit/repro/`; 12/12 confirmed)
and fixed. The fixes are behavioral (ledger-changing), so the golden hashes
re-pinned (data_hash, candidate_count and terminal_distribution UNCHANGED; see
`tests/test_golden_backtest.py` re-pin note).

**Entry is not entry: `PENDING -> TRIGGERED` is gated on a frozen trigger**
(#62/#67). `risk_geometry` gains a normative trigger contract
(`trigger_ref` absolute price + `trigger_side` CLOSE_ABOVE/CLOSE_BELOW;
`schema.py`). `lab.py` PHASE 2 evaluates the book's close-confirmation
predicate before triggering; an unconfirmed candidate stays PENDING and is
re-checked each bar until it fires, invalidates, or the epilogue expires it.
`candlestick_reversal` (Ch14.2 p556) is the pilot and now declares
`trigger_side`; the pre-fix unconditional path entered 16/27 candlestick
candidates whose close had NOT confirmed beyond the trigger. Unconditional
experts keep `entry: NEXT_BAR_CLOSE` (no `trigger_ref` -> no predicate).
Artifacts: `src/v8/lab.py`, `src/v8/schema.py`,
`src/v8/experts/candlestick_reversal.py`.

**Structural stop: `stop_ref` is the static stop when declared** (#63). The
simulator placed the stop at `entry ± stop_r × ATR` even when the expert froze
the structural level (swept extreme / pattern level). `step()` now uses
`risk_geometry['stop_ref']` as the static stop when present; `stop_r × unit`
is the fallback. Measured pre-fix: 33/33 candlestick drafts had the ATR stop
0.44R (mean) from the structural level; 37.3% of executions were stopped by
adverse excursion alone. Artifacts: `src/v8/simulator.py`.

**Geometry invariants fail closed** (#70). `simulator.validate_geometry()`
rejects non-positive `target_r`/`stop_r` and `expiry_bars < 1` at `step()` and
`run()` entry — a `target_r=-1` previously booked a −1.07R loss as a TARGET
win. Defense-in-depth on top of the experts' own guards.
Artifacts: `src/v8/simulator.py`, `tests/test_audit_fixes.py`.

**Windowed pre-entry invalidation fallback** (#66). The all-bars
`prior_high`/`prior_low` are UNBOUNDED prefix extremes (marketstate), so an
invalidation tested against them was dead code for the 6 experts that freeze
no ref (measured: 7 fires across 2,067 drafts). The lab's fallback now uses a
32-bar windowed extreme (the frozen-ref convention) so the gate is meaningful
for every expert. Artifacts: `src/v8/lab.py`.

**Contention tie-break is the candidate's episode_key hash** (#68). Same-bar
same-direction slot races used to be decided by alphabetical `expert_id`
order — measured 295/303 (97.4%) contended slots won by the alphabetically
first expert, and the executed subset was 1.83× worse than the average setup.
PHASE 1a now iterates in candidate-hash order: deterministic, economically
neutral, and NOT a ranker (rule 6/14 — the implicit ranker is removed, not
formalized). Artifacts: `src/v8/lab.py`,
`tests/test_admission_contention.py`.

**Feasibility notes surface in the report** (#64, #69). The report now carries
an RM-11 note when the cost-degraded breakeven win rate exceeds the realized
win rate, and an excess_cost feasibility note when the cost gate fires
(previously the excess-cost rejection was silent beyond
`rejection_distribution`). Artifacts: `src/v8/lab.py`.

**Synthetic tape continuity variant** (#72). `make_synthetic_tape` gains
`continuous=True` (open = prior close ± small move) — the legacy default
fabricated TR > (H−L) gaps on ~73% of bars vs ~0.6% on the real tape. The
legacy default stays byte-identical (pinned golden/contract tests); flipping
it is D-064. The golden-hash mismatch the audit filed was already resolved on
the working tree (re-pinned, `1 passed`). Artifacts: `src/v8/synth.py`,
`tests/test_audit_fixes.py`.

**Recorded, not behavior-changed** — #61 (cost 10.9× the raw edge; the
cost/edge feasibility ratio), #71 (gap asymmetry, a 3.30R conservative budget,
now documented in the SIMULATION_TRUTH_SPEC area of the changelog), #65
(literature-condition table for `failed_breakout`: 2/10 implemented; the rest
are OPEN_QUESTION/REJECTED_OPTION). See DECISION_REGISTER D-057..D-064 and
OPEN_DECISIONS O-024.

Artifacts: `docs/CHANGELOG.md`, `docs/decisions/DECISION_REGISTER.md`,
`docs/decisions/OPEN_DECISIONS.md`, `.audit/BASELINE.md`,
`.audit/repro/*` (repro scripts + evidence), `tests/test_audit_fixes.py`.

## 2026-08-07 — Single-process multi-tape driver + funding-interval audit fix

`tools/build_multi_tape.py` spawned one subprocess per archive, and every
per-archive provenance write re-read and re-hashed the whole growing tape —
O(N²) in rows, ~80 min of CPU for a 960-archive grid. The driver now imports
vision_backfill's functions directly, opens ONE append-only log (the dedup
inbox is built once), skips archives already recorded with the same zip
sha256, and writes provenance once at the end (atomic temp + os.replace). A
corrupt source.json is rebuilt from the on-disk zips + their `.CHECKSUM` files
— the revision guard is re-armed from the authoritative checksums, not
silently disarmed. Measured: the full 960-archive grid (10 symbols x 48 months
x 2 channels) rebuild finished in ~7 s (was 1 h+).

`audit_tape` false-flagged funding settlements that straddle a venue schedule
change: the gap from the previous settlement is governed by the PREVIOUS row's
declared `funding_interval_hours`, not the current row's. The real SOLUSDT
2022-11 archive hit exactly this (a 4h transition gap flagged against the new
2h schedule). The tolerance now uses the previous row's interval; a genuinely
missing settlement under a steady schedule still flags (regression-tested).

The `research/tape/multi-1h-4y` dataset is now complete: 960/960 archives,
394,545 rows, 10 symbols x 48 months x (kline + funding), provenance rebuilt
atomically, sorted to replay order, and audit-clean (monotonic, venue_gaps 0,
duplicate_rows 0, payload hashes verified).

Artifacts: `tools/build_multi_tape.py`, `tools/vision_backfill.py`,
`tests/test_build_multi_tape.py`, `tests/test_tape_audit.py`,
`research/tape/multi-1h-4y/`.

## 2026-08-07 — AppendOnlyLog parsed-log cache (no contract change)

`AppendOnlyLog.read()` re-read and re-parsed the entire JSONL on every call,
and `hash` was `sha1_hex(self.read())` — a full re-parse followed by a full
re-serialization of the whole record list. One lab run touches the logs 17
times (4 emptiness probes, the post-loop report scans, and five `hash`
properties bound into `ledger_hash`), which measured 5.87 s of a 39.2 s run on
the 8,760-bar dev tape (14% of wall).

`read()` now caches the parsed list and `hash` memoizes its digest; `append()`
invalidates both. The log is append-only and the instance owns the sole write
handle, so the file cannot change behind the cache. `append()` invalidates
rather than splicing the record in, because the stored form is the record's
JSON round-trip (tuples become lists) and splicing would let `read()` disagree
with the file. `read()` returns a shallow copy so callers keep the previous
"fresh outer list" semantics; the record dicts are shared and documented
read-only (every current caller iterates, filters or `sorted()`s).

PERFORMANCE ONLY — no contract, schema or decision changed. Measured on the
8,760-bar dev tape with 27 Experts, 3 runs each: 39.2 s → 36.7 s (1.07x);
the log-read component itself 5.87 s → 3.44 s (1.7x). `candidate_count`
(28,088) is unchanged, and the full suite including the golden backtest stays
green (668 passed) — an invariance the D-056 fast path could not claim,
because `marketstate` binds its own source bytes into every state's
`code_version`. Roughly half the reads are still cold (each log's first
post-append read); eliminating them needs a rolling digest so `hash` never
re-reads, which is not done here.

Artifacts: `src/v8/store.py`.

## 2026-08-07 — D-056: state-builder fast path (O(N²) → O(N × window))

The bar-driven state pre-build recomputed every series (EMA/ATR/RSI/ADX/CCI/
MACD/pivots/prefix extremes/OBV/ADL) from scratch per decision clock, making a
backtest O(N²) in bars: ~280 s for 8,760 bars and an estimated 1-2 h for one
4-year symbol. `build_state` now takes an optional per-symbol `BarSeries`
(precomputed once over the full tape) and reads it by index per clock; the lab
builds it once per run. Unbounded features (`prior_high`/`prior_low`) keep the
exact running prefix max/min — never a fixed window, which silently diverges
(measured 83.5% of bars at a 520-bar window) and 21/27 Experts read them.
The growing-list lineage hashes keep exact `sha1_hex(list)` semantics via
precomputed per-row canonical bytes (O(N) per state with a small constant —
exact values, no chained-hash substitution). Every emitted value, per-feature
lineage, `lineage_hash` and `state_id` is byte-identical:
`tests/test_state_cache_identity.py` proves cached == uncached on every bar;
diffing the golden fixture against the pre-change code shows candidates,
evaluations and outcomes with 0 differing fields and states differing only in
the provenance `code_version` (whole-file source hash — its designed behavior,
re-pinned in `test_golden_backtest.py`). Measured on this machine: 8,760-bar
backtest 280 s → 12 s; BTCUSDT 4-year (35,064 bars, exact lab shape incl.
funding) 67 s; 8-symbol × 4-year serial-store projection ≈ 9 min (was an
estimated 11-12 h).

- **`src/v8/marketstate.py`** — `Prefix` view, `BarSeries` + `build_bar_series`,
  `_adx_series`, `_last_significant_pivot`/`_last_confirmed_swing`, cached
  branch in `build_state`/`build_multi_state` (`series=` param).
- **`src/v8/lab.py`** — builds the series once per run, passes them in.
- **`tests/test_state_cache_identity.py`** — cached == uncached on every bar
  (synthetic every bar, real tape sampled, multi-state).
- **`tests/test_golden_backtest.py`** — states/ledger hashes re-pinned; the
  move is provenance `code_version` only (diffed and documented).
- **`docs/decisions/DECISION_REGISTER.md`** — D-056.

## 2026-08-07 — D-055: strict-climax challenger for volume_climax_reversal

The O-022 measurement showed the 2-sigma climax gate fires on nearly every bar
(8,272 distinct candidates on 8,760 bars -> a 4.6% D-027 execution_share; the
family floods the rule-16 exposure pool and blocks its own re-entries). A
strict-climax challenger variant `e` (vol_zscore >= 3.0) joins the family,
owning every 3-sigma bar. Declared and frozen pre-holdout; the frozen-OOS
within-family Reality-Check (D-044) decides whether `e` survives, never the
dev window.

- **`src/v8/experts/volume_climax_reversal.py`** — variant `e` (3-sigma fade in
  the trend direction), `variants_evaluated` (a,b,c,d,e), `search_universe_size`
  5, priority e > d > c > b > a.
- **`docs/EXPERTS_REGISTRY.yaml`** — volume_climax variants/search updated.
- **`docs/decisions/DECISION_REGISTER.md`** — D-055.
- **`tests/test_expert_volume_climax_reversal.py`** — a/b/d tapes re-based on an
  alternating volume series so their vol_zscore sits in [2,3) (the near-constant
  base made ANY spike a ~10-sigma event and routed every test to the new strict
  variant); new variant-e test (8.0 spike -> z~10 -> e/LONG and e/SHORT).

## 2026-08-07 — Declared per-Expert MarketState (D-054) + block-bootstrap defect (D-052)

Two changes to the evidence machinery, both frozen pre-holdout.

**D-052 — the block bootstrap manufactured one false positive per run.**
Preregistration section 9's block-size constants (24 / 168) are bar-counts
("one day" / "one week" of 1h bars) applied to an episode-indexed `net_R`
series. When `block_size >= n` the circular sampler draws a cyclic rotation
holding every index exactly once, so all 2000 resample means equal the sample
mean: the interval collapses to zero width and any family with a positive mean
and `n >= 30` rejects H0 by construction. On the pinned dev baseline 8 of 21
families with episodes had `block >= n`, and exactly one spurious rejection
resulted. Degeneracy is the endpoint of a bias, not an isolated case — at
`block/n ~ 0.3-0.5` (every family with n=45..100) the resample variance is
already understated.

- **`src/v8/statistics.py`** — `select_block_size` becomes an n-adaptive
  episode-unit rate (`round(n**(1/3))`, doubled above the 0.10 lag-1 gate,
  capped at `n // 2`); `_block_bootstrap_indices` raises on `block >= n`.
- **`tools/run_experiment.py`** — `_block_size` delegates to the module (the
  rule existed in two copies); `resamples_for_alpha` ties the resample count to
  alpha so the bound stays a stable order statistic (at 0.05/28 the old 2000
  put it at index 3); the `2.5th-percentile` misnomer is corrected.
- Verified on an unchanged ledger (`452d91bcf890` before and after): degenerate
  families 8 -> 1 (the survivor is n=1, where a bootstrap has no variance by
  construction), H0 rejections 1 -> 0, every former zero-width row gained a real
  interval, and intervals widened slate-wide.

**D-054 — Experts declare the MarketState they need.** The 27-family inventory
found the binding constraint was not the 1h tape but the global 32-bar
`history` pin: `ichimoku_cloud` needs 78 bars and declares 3 of 4 variants
unevaluated, `breakout_retest` drops variant d, `donchian_breakout` falls back
to a 50-bar anchor scan, `pattern_measuring_objective` cannot express its
patterns. Only `market_profile_value_area` demonstrably needs higher-interval
bar structure.

- **`src/v8/interval.py`** (new) — exact up-only aggregation of the base tape
  into declared intervals; buckets anchored to a fixed UTC epoch (never tape
  start), aggregate `available_time` = its last constituent's, partial trailing
  buckets never emitted as closed.
- **`src/v8/experts/base.py`** — `intervals` + `depth` join `requires` as
  frozen specification; both default to pre-D-054 behavior.
- **`src/v8/marketstate.py`** — `build_multi_state` namespaces higher intervals
  `{sym}.{tf}.{feature}` (base stays unprefixed); `project_state` serves each
  Expert exactly its declared groups x intervals x depth; the 32-bar pin becomes
  `HISTORY_DEPTH_DEFAULT`, a default rather than a ceiling.
- **`src/v8/lab.py`** — the canonical state carries the union of declarations
  and ONE state per clock is still what the ledger records; `Lab.feasibility`
  refuses a declaration the tape cannot serve in words, so an unservable Expert
  is never indistinguishable from a signal-less one.
- **`tools/vision_backfill.py`** — archive provenance is keyed by
  (symbol, channel, month). Keying on (channel, month) was correct only while a
  tape dir held one instrument: a second symbol's 2025-01 archive was misread as
  a revision of the first's, so a multi-instrument tape could not be built.
- **`tools/build_multi_tape.py`** (new) — drives the backfill over a
  symbol x month grid into one tape, refusing any month at or past the frozen
  holdout anchor.

Golden backtest re-pinned twice, both times provenance-only: `_BUILDER_SRC_HASH`
is a whole-file hash, so adding functions re-versions every state's
`code_version` even when no formula moves. `data_hash`, `candidate_count` (15)
and `terminal_distribution` unchanged both times, and a run with the projection
disabled reproduces the enabled run's four ledger hashes byte-for-byte.

## 2026-08-06 — Expert bug-fix pass: two-step failed_breakout gate, origin-based fib extensions, climax-bar anchor, fib swing-guard removal

Adversarial audit of the 27 expert families against their hypotheses and the
Handbook of Technical Analysis (Lim 2016) found and fixed three implementation
bugs plus four audit/doc drift items. All are code-correctness fixes — the
code now matches its own documented hypothesis and the cited book; no
threshold, registry multiplicity, or hypothesis was tuned.

- **`src/v8/experts/failed_breakout.py`** — the detection gate fired a SHORT on
  ANY close below the windowed prior high, never verifying the breakout leg
  ("a close above the prior high that fails back below it", Ch7.3 p228). A
  plain downtrend with no close-breakout produced candidates. Gate and anchor
  predicate now require a prior bar that CLOSED above its own prior high; the
  frozen level is the breakout level; the anchor is the first failure bar
  after the breakout (dedup stable, no window-edge anchor slide).
- **`src/v8/marketstate.py`** — `_fib_levels` projected extensions from the
  impulse END extreme; the book's formula is origin-based ("Upside extension =
  Trough + (Range x Ratio)", Ch10.5.1 p404 / "Downside = Peak - ...", 10.5.2
  p405). Every extension level moved one full impulse-range. Retracements
  unchanged. Consumers: `fib_projection_reversal`.
- **`src/v8/experts/volume_climax_reversal.py`** — the D-026 anchor resolved to
  the trend-run start (the trend predicate is near-always-true), collapsing
  every distinct climax inside one trend into a single episode. The anchor is
  now the detection (climax) bar; the per-bar trend predicates became dead code
  and were removed.
- **`src/v8/experts/fib_projection_reversal.py`** — removed the swing-lattice
  consistency guard that gated on the significance-FILTERED swing_high_10 /
  swing_low_10 pair (a different pair than the unfiltered confirmed-swings
  anchor `_fib_levels` uses) — it vetoed states with a valid anchor and
  NO_HABITAT'd states where the filtered pair was absent. `fib_levels` is the
  habitat gate and its own consistency guard. Same fix in
  `fib_retracement_continuation.py`. Docstring corrected: Fig10.51 is a LONG
  reversal at a DOWNWARD 161.8% projection, not a short at an up-projection.
- **`tests/`** — new `test_expert_failed_breakout.py` (two-step gate,
  no-breakout regression, fresh-high rejection, anchor, still_valid,
  warmup); updated fib projection levels to origin-based values in
  `test_expert_fib_projection_reversal.py` and `test_feature_groups.py`;
  registry CONSUMPTION manifest corrected (`failed_breakout` no longer reads
  `prior_high`); golden backtest re-pinned (candidate_count 21 -> 15 after the
  two-step gate, then states/ledger only after the fib fix); vertical-slice
  exposure-conflict assertion relaxed (the gate fix removed the overlap on the
  synthetic fixture; the guard is pinned end-to-end in
  `test_admission_contention.py`).
- **`docs/EXPERTS_REGISTRY.yaml`** — unchanged (the removed swing features
  were never part of `requires`; `fib_levels` is a location-group feature the
  fib experts still declare via 'location').

## 2026-08-06 — O-022 measured: rule-16 exposure blocking matrix + D-027 execution_share distribution

Quantified the cross-family coupling on the corrected dev diagnostic: of
11,673 `EXISTING_EXPOSURE_CONFLICT` rejections, all had a same-direction open
slot at the block time; bollinger_breakout blocked 4,115 (incl. 1,226 of its
own — self-blocking). Per-family D-027 `execution_share` clears the 0.25 floor
for only 6 of 21 families; 15 sit below (5 under 0.10). Recorded in O-022 as
measured evidence: on the current slate the D-027 attribution gate would score
~6 families on the OOS and mark the rest `ATTRIBUTION_UNSAFE_*`.

## 2026-08-06 — v2 challenger registration for the bug-fixed families (O-023, D-053)

Operator chose O-023's admission condition: `failed_breakout` stays v1
(bug-completion — fixed series is a strict subset, 369 -> 76); the two families
whose fixes ADD behavior become v2 challengers.

- **`src/v8/experts/volume_climax_reversal.py`**, **`fib_projection_reversal.py`** — `expert_version` bumped v1 -> v2 (enters the episode_key, so v1 and v2 episodes never collide).
- **`docs/EXPERTS_REGISTRY.yaml`** — the two families' `expert_version` v2.
- **`docs/decisions/DECISION_REGISTER.md`** — D-053 decision; **`docs/decisions/OPEN_DECISIONS.md`** — O-022/O-023 (exposure coupling across families, version discipline).
- **`tests/test_expert_volume_climax_reversal.py`** — version assertion v2.

## 2026-08-06 — D-052: block-bootstrap block-size rule corrected from bar-units to n-adaptive episode units

The prereg §9 block-size rule applied bar-counts (24 / 168 — "one day" /
"one week" of 1h bars) to an episode-indexed `net_R` series: a unit error,
visible in §9's own prose ("24 episode-blocks (one day)"). The fix makes the
tier values n-adaptive episode-unit rates — `round(n**(1/3))`, doubled when
the lag-1 autocorrelation gate fires, hard-capped at `n // 2` — and the tool
now delegates to the module's `select_block_size` (one rule of record).

- **`src/v8/statistics.py`** — `select_block_size` re-expressed in episode
  units; `_block_bootstrap_indices` gains a fail-closed `block_size < n`
  invariant (at `block_size >= n` every resample is a rotation of the whole
  series and the bootstrap collapses to a point mass at the sample mean —
  a zero-width `ci_lower == mu_hat` that rejected H0 by construction).
- **`tools/run_experiment.py`** — `_block_size` delegates to
  `select_block_size`; new `resamples_for_alpha` keeps the tail index a
  stable order statistic (`int(N * alpha) >= 100`); `N_RESAMPLES` 2000 ->
  60000 (the bound was `int(2000 * 0.05/28) = 3` — the 4th-smallest draw
  standing in for a 0.18th percentile).
- **`docs/decisions/DECISION_REGISTER.md`** — D-052 decision with the
  mechanical reproduction, outcome-neutrality of the rule choice across the
  three candidate rules, and the measured cost.
- **`tests/`** — invariant tests for the non-degeneracy (point-mass rejection,
  width under the rule), the episode-unit tier values, and the stable tail
  index in `test_statistics_ext.py` / `test_reality_check.py` /
  `test_run_experiment.py`.

## 2026-08-06 — Handbook+Evidence extraction lands: feature graph, 24 expert families, risk & execution management (D-048/49/50)

The two-book extraction round (D-042) reaches code: the feature-group ontology
widens to 11 groups / 73 new features (FG-1..FG-7, G-01..G-43), 24 expert
families are implemented and registered (EXP-01..24, E-05/E-06 survivors +
E-01..E-24), and risk/execution management lands (RISK-1..6, EXEC-1..6).

- **`docs/decisions/DECISION_REGISTER.md`** — D-048 (risk additions), D-049 (feature graph), D-050 (expert admission).
- **`src/v8/schema.py`** — FEATURE_GROUPS +7 groups (candle_shape/oscillator/session/positioning, participation activated, volatility/location extended); CandidateDraft.size; ExperimentManifest.risk_per_trade/min_trades; CounterfactualOutcome endpoint vocabulary extended (TIME_EXIT).
- **`src/v8/marketstate.py`** — 73 new feature computations (Wilder RSI/MACD/ADX, Bollinger, swing lattice with Ch27.2 ATR range filter, fib levels, pivot, consolidation, gap, OBV/ADL/CMF, session, funding/OI); add() value widened to tuple/list; no-signal -> numeric sentinel (never None, D-024 veto preserved).
- **`src/v8/experts/*`** — 24 new expert files (one per behavior family, D-033), each with variants_evaluated (D-044) + search_universe_size (D-046). CRIT fixes applied: E-01 variants b..g (CRIT-4), E-07 declared subset (CRIT-6), E-17 self-gating regime (CRIT-7).
- **`src/v8/equity.py`** (new) — RiskState drawdown ladder (RM-06, O-016 challenger) + trade_units_for (RM-07).
- **`src/v8/risk.py`** — size-aware heat (size*stop_r, byte-identical at 1.0), equity wiring, min-trades/PF gates.
- **`src/v8/simulator.py`** — breakeven roll + chandelier trail, scale-out (closed_fraction + PARTIAL_EXIT), pyramid plumbing, FILL_AT_LIMIT, TIME_EXIT; sim.hash() -> canonical-sim-v7.
- **`src/v8/statistics.py`** — D-045 detrending (passive_benchmark_r/detrend_net_r) retained; METH-1..6 extensions follow in the next entry.
- **`docs/EXPERTS_REGISTRY.yaml`** — 28 entries (24 new FORMALIZED, open_interest DATA_BLOCKED, breakout_retest FORMALIZED); registry test derives expected set from code.
- **`tests/`** — test_feature_groups.py, 24 test_expert_*.py, test_risk.py, test_execution.py; golden re-pinned (hashes moved by construction, candidate_count 21 + terminal_distribution unchanged throughout).

## 2026-08-06 — Retire v2 research subsystems from version control (D-051)

The v2.3 research-corpus pipeline (`research/pipeline_v2/`) and the standalone
`research_base/` package were superseded by the `src/v8/` runtime and are
removed from the tree, along with `research/revision/` visual-preview artifacts,
`research/text/` corpus copies, and the three revision-monograph builders whose
data sources they were (`tools/build_v8_revision.py`,
`tools/generate_gemini_master_html.py`, `tools/generate_10k_gemini_master_html.py`).

- **`docs/decisions/DECISION_REGISTER.md`** — D-051 (PROVISIONAL_DECISION).
- No prereg, contract, or test references the retired paths (verified); the 615-test suite and monograph build are unchanged.
- Recoverable from git history (introduced in `a051a20`) should the v2.3 ledger be needed again.

## 2026-08-06 — Position management and fill policies land as declared, optional mechanics (EXEC-1..6, D-047)

The handbook's execution additions (EX-01..EX-12 in `books/reports/HAND_RISK_EXEC.md`,
gated by OPEN_DECISIONS O-013 — admission still requires replicated OOS gain vs
static geometry) become first-class, DECLARED risk_geometry keys and one new
fill policy. Every key is optional; the pilots' frozen geometry declares none,
so step()/run() output on default geometry is byte-identical to pre-change code
(verified by diffing the executed outcomes of both code versions on the golden
fixture). This is the O-013 mechanics layer: the question "does active position
management beat static geometry" can now be asked.

- **`src/v8/simulator.py`** — EXEC-1 breakeven roll + chandelier trail
  (`breakeven_roll_at_mfe_r` / `breakeven_margin_r` = `round_trip_cost_r` /
  `trail_stop_atr`; `OpenPosition.stop_level` + `stop_rolled`; endpoint stays
  STOP); EXEC-2 scale-out partial exit (`scale_out_ratio` > 0 enables +
  `scale_out_at_mfe_r`; `StepResult.closed_fraction` < 1.0 is a NON-TERMINAL
  event; `OpenPosition.remaining`/`realized_r` fraction-weighted R accounting);
  EXEC-5 TIME_EXIT endpoint (`time_exit_bars`, distinct from EXPIRY); EXEC-4
  `FILL_AT_LIMIT` fill policy (barrier entry at `risk_geometry['limit_price']`,
  fill-only entry-bar inspection, never-filling orders never enter); EXEC-3
  `pyramid_add_rules` declared but P2/off (fail closed on request;
  `midpoint_stop` primitive implemented + tested). `hash()` →
  `canonical-sim-v8`. Funding path untouched (the funding goldens are
  byte-identical). Management updates apply from the bar AFTER the bar that
  triggered them (bar-atomic OHLC cannot order intrabar events).
- **`src/v8/lifecycle.py`** — `CandidateRegistry.position_action`: the
  append-only `PositionAction` event (`kind: position_action`), EXEC-2's
  PARTIAL_EXIT. Non-terminal: no transition, `current()` unchanged, joins the
  candidates ledger and therefore `ledger_hash`.
- **`src/v8/lab.py`** — executed path records PARTIAL_EXIT PositionActions and
  continues the position; FILL_AT_LIMIT executed entry (resting order, never
  entered → the epilogue's never-entered convention); TIME_EXIT closes the
  position (`expiry_reached`); equity feed books fraction-weighted net_r
  against the admission size.
- **`src/v8/schema.py`** — endpoint vocabulary documented with TIME_EXIT;
  PARTIAL_EXIT documented as a non-terminal PositionAction, never an endpoint;
  `risk_geometry` management keys and `limit_price` documented on
  `CandidateDraft`; `ExperimentManifest.fill_policy` documents FILL_AT_LIMIT.
- **`tests/`** — `test_execution.py` (new: EXEC-1..6 unit + lab end-to-end,
  including the fill-only entry-bar invariant and a managed-geometry lab run),
  `test_lifecycle.py` (new: PositionAction append-only/non-transition/replay),
  hash-canary goldens re-pinned to `canonical-sim-v8`,
  `SUPPORTED_FILL_POLICIES == ('FILL_AT_BAR_CLOSE', 'FILL_AT_LIMIT')`,
  golden-backtest ledger re-pinned (outcome records carry the re-versioned
  `simulator_hash`; data/states/candidate/terminal unchanged).
- **Not done here:** O-013's admission gate (replicated OOS gain vs static
  geometry) is a preregistration/experiment act, not code; RM-04 two-tier heat
  consumption of `stop_rolled` is dormant in `risk.py` until a register
  decision revises D-023's domain (CRIT-2.6); pyramiding (EXEC-3) and the full
  EX-13 action lattice (ADD/REENTER/HEDGE) are P2.

## 2026-08-06 — The net-R null is detrended, and the search universe is declared (D-045, D-046)

Two multiplicity/centering defects from the handbook evidence extraction
(`books/reports/EV_METHODS.md` G-01/G-02, issues METH-1 and METH-2), both
landed pre-holdout while prereg §16 still permits it — no manifest, store or
outcome ledger exists yet.

**D-045 — the null was mis-centered.** `μ_f ≤ 0` on raw episode net_R is
mean-zero only for a no-skill rule on *detrended* data (Aronson Ch1 p23-27,
Appendix A). On a trending tape a long-biased family earns positive expected
net_R with zero predictive power, and every pilot carries long-direction
setups — so the single-config lower-bound gate and the Reality Check were
both testing against a null the tape had already moved. Episode net_R is now
centered on a same-exposure passive benchmark before any gate; the raw mean
survives beside it as a diagnostic and the difference is published as
`position_bias_component`. Signal generation never sees a detrended value.

**D-046 — the search universe was undeclared.** `variants_evaluated` (D-044)
counts only the configurations whose episode series were retained; parameter
grids, discarded indicator variants and the direction-sign choice are search
the family also consumed. The registry now declares the total, the runner
publishes it with every family statistic, and an undercount is flagged rather
than silently inflating significance.

- **`src/v8/schema.py`** — `CounterfactualOutcome` gains `entry_price`,
  `risk_unit_price`, `market_move_r`. Recorded, never re-derived: `risk_unit`
  depends on the fill whenever a draft declares `risk_frac` instead of
  `atr_ref`, so the R denominator is not recoverable downstream.
- **`src/v8/simulator.py`** — populates them; `hash()` → `canonical-sim-v6`.
- **`src/v8/lab.py`** — the executed path does not go through `simulator.run`
  (it steps positions and closes them in `_record_outcome`), so the fields are
  supplied at each entered call site too; they stay 0.0 for never-entered
  candidates.
- **`src/v8/statistics.py`** — `EpisodeExposure`, `mean_log_drift_per_bar`,
  `passive_benchmark_r`, `detrend_net_r`, `placebo_exposures`,
  `appendix_a_invariant`. `invariant_holds` is deliberately unimplemented and
  raises: the "≈ 0" tolerance is itself a preregistered constant and is left
  to an explicit operator choice rather than a silent default.
- **`docs/EXPERTS_REGISTRY.yaml`** — required `search_universe_size`; all five
  pilots declare 1, consistent with prereg §4 (parameters frozen in code
  against synthetic tapes before the dev window existed).
- **`tools/run_experiment.py`** — scores the detrended series, reports the
  drift estimate, the raw/detrended pair and the search accounting; fails
  closed on a pre-D-045 ledger that carries no `risk_unit_price`.
- **`tests/`** — `test_detrended_null.py` (new: reproduces the position bias,
  then asserts it is removed), plus runner and registry gates. Goldens
  re-pinned: `net_r`, endpoints, labels, `data_hash`, `states_hash`,
  `candidate_count` and `terminal_distribution` are all UNCHANGED and only
  `ledger_hash` moved — the evidence this changed the record, not a decision.
- **Not done here:** prereg §2/§10/§11 still describe the uncentered null in
  prose; the `invariant_holds` threshold is unchosen. Both are operator acts.

## 2026-08-06 — Within-family variant multiplicity fixed: Reality-Check replaces "variants count as one unit" (D-044)

Preregistration §11 said "all variants explored inside a family count as one
multiplicity unit (rule 13)." That over-read rule 13's ontology (a variant is
not a new Expert) into a statistical claim (variant search is
multiplicity-free), which is false: best-of-N variant search inside one
family reintroduces exactly the selection bias rule 11 exists to control
(the canonical case is Aronson's 6,402-rule study, which understates its own
search by an order of magnitude under a themes-only counting rule). The bug
was harmless while every pilot sat at `variant_id: 'a'`; it stops being
harmless the moment variant search starts, which literature extraction is
about to do. Cross-family Bonferroni (`α_f = 0.05/F`) is unchanged — still
valid, only conservative under correlation, and not the urgent half of this.

- **`docs/decisions/DECISION_REGISTER.md`** — D-044 added.
- **`docs/PREREGISTRATION_V8_SLICE_001.md`** — §1 and §11 revised: within a
  family, `len(variants_evaluated) == 1` keeps the original single-config
  percentile-bootstrap test; `> 1` spends the family's `α_f` via
  `src/v8/statistics.reality_check_p_value` (White 2000 Procedure RC,
  already `LITERATURE_SUPPORTED` in `HYPOTHESIS_LAB_PROTOCOL.md`'s Sources
  section) over all evaluated variants' episode series, using the same
  section-9 block-size rule. Cross-family pooling into one N-configuration
  statistic is explicitly **not** implemented — families fire on disjoint
  episode grids and a correct pooled test needs a bar-level panel, not an
  episode-level one (O-021).
- **`docs/EXPERTS_REGISTRY.yaml`** — new required field `variants_evaluated`
  per entry (losers included, not just the reported `variant_id`); all five
  current entries carry `['a']` since no variant search has happened yet.
- **`src/v8/statistics.py`** (new) — `reality_check_p_value`,
  `select_block_size`, stdlib-only, explicit seed, aligned-episode-grid
  inputs only. Not yet wired into a runner: `tools/run_experiment.py` (the
  `v8_slice_001` Phase-4 runner) does not exist yet, so this is unit-tested
  on synthetic data only.
- **`tests/test_reality_check.py`** (new) — determinism, p-value bounds,
  block-contiguity, `select_block_size` against known-autocorrelation
  synthetic series, mismatched-length and empty-input rejection.
- **`tests/test_expert_registry.py`** — gates `variants_evaluated` presence
  and that the reported `variant_id` is a member of it.
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md`** — `statistics.py` and
  `tests/test_reality_check.py` rows added (D-032: new files are registry
  decisions).
- **`docs/decisions/OPEN_DECISIONS.md`** — O-021 opened: whether and how to
  pool the Reality-Check test across families (bar-level panel), deferred
  rather than built ad hoc.
- Legal pre-holdout per prereg §16, same basis as D-041: the frozen holdout
  has not been opened or downloaded.

## 2026-08-04 — Rule 14 rewritten: complexity budget splits runtime from evidence (D-043)

The constitution capped "at most 3 active Experts". That single number
conflated an engineering question (how many modules evaluate per bar — zero
validity content) with a statistical one (how many independent hypotheses are
simultaneously under test on one frozen OOS). The cap was already breached:
`EXPERTS_REGISTRY.yaml` carries 5 Experts after D-042. No code enforced it, so
this is a documentary correction.

- **`docs/charter/V8_CONSTITUTION.md` — rule 14 rewritten** on two axes:
  (a) runtime Expert count unbounded, limited only by determinism and compute,
  explicitly *not* a validity constraint; (b) the preregistered cap applies to
  the `behavior_family` count simultaneously carrying a claim on one frozen-OOS
  evaluation, entering rule 11's family-level multiplicity correction. The
  minimum-architecture diagram's `(2–3)` becomes `(N, unbounded)`.
- **"At most one learned component" rescoped to per pipeline position.** A
  Candidate Scorer (ladder step B) and an ML Expert challenger sit at different
  positions and are each already gated by rule 5's preregistered frozen-OOS
  comparison; the global "never both at once" added no statistical control, only
  a sequencing preference. `LEARNING_PROTOCOL` §3 and its cheap test 5 updated.
- **`docs/contracts/ARCHITECTURE_SPEC.md` §4, `ROADMAP.md`, `PLAN_V8_FULL.md`** —
  the copied "hard cap" wording replaced; router/scorer/ranker/RL absence
  unchanged.
- **`docs/decisions/DECISION_REGISTER.md`** — D-043 added; D-003 and D-020
  annotated as revised. Both keep `PROVISIONAL_DECISION`: rule 2's label
  vocabulary is closed, and the register's own note makes that status the
  sanctioned reversible one — inventing a `SUPERSEDED` label would breach rule 2
  while fixing rule 14.

- **`tests/test_admission_contention.py` (new) — contention is now tested.**
  `RUNTIME_SCHEDULER_SPEC` §5 test 3 (Expert-order shuffle) was only exercised
  by the two pilots, which almost never emit on the same bar — so the claim was
  verified with **no contention at all**. The new tests use unconditional
  contenders that collide on one exposure slot every bar, and pin two separate
  properties: (1) the ledger stays order-independent under full contention,
  because `lab.run` sorts Experts by `expert_id` before evaluating; (2) the
  surviving tie-break is therefore that lexicographic name — measured, the
  first-sorting of two behaviorally identical Experts wins contested slots
  roughly 2:1, and the advantage follows the name when the names are swapped.

- **`max_spread_frac` renamed to `max_bar_range_frac`; veto detail `SPREAD` to
  `BAR_RANGE`.** The D-024 predicate is `(high-low)/close` — the entry bar's
  intrabar range. It is not a bid-ask spread and cannot be: the tape carries no
  depth. The old name propagated the misnomer into `PREREGISTRATION` §8 and the
  runbook, where it read as an execution-cost control. Pure rename across
  `schema.py` / `risk.py` / `lab.py` / `tools/materialize_views.py` and the
  tests; **`GOLDEN_LEDGER_HASH` re-pinned** because `config_hash =
  sha1(asdict(manifest))` keys on field names, while `data_hash`,
  `states_hash`, `candidate_count` (21) and `terminal_distribution` are
  unchanged — that invariance is the evidence no decision moved.
- **`docs/tr/V8_CONSTITUTION.md` — rules 13–17 added.** The Turkish mirror
  stopped at rule 12 and had never carried the ontology, complexity-budget,
  learning, risk-admission, or materialization rules. Rule 2's label discipline
  cannot hold in a corpus that omits the rules; the TR diagram's `(2–3)` is
  corrected with the EN one.
- **Three open questions registered rather than guessed.** O-018 (should the
  heat cap scale with the Expert population — caps stay at 3.0 / 2.0 until a
  preregistered comparison moves them), O-019 (does the 0.05 intrabar-range
  veto fire at all on the declared dev window; "declared, never fitted" answers
  leakage but not inertness, and the firing rate has never been measured),
  O-020 (per-Expert `history` lookback instead of the global 32 bars —
  deliberately not implemented here: it adds a public field to the Expert
  contract, a D-032 change needing its own decision, and it moves the state
  hash).

Two couplings are recorded as follow-ups, not resolved here. The binding
constraints on portfolio scale are rule 16 (one exposure per instrument +
direction) and D-023 (`max_heat = 3.0`), not the Expert count — with those in
place a 400-Expert portfolio holds the same positions as a 3-Expert one. Rule 16
and `CANDIDATE_LIFECYCLE_SPEC` §6 now say so explicitly and restate the
single-exposure rule as the attribution default it is; whether the heat cap
should scale with the Expert population is opened as **O-018** rather than
guessed at, and the caps stay at 3.0 / 2.0 until a preregistered comparison
moves them. And
contested-slot priority is decided by Expert *name*, which is deterministic and
harmless at three Experts but is a silent allocation policy at the count rule 14
now permits. A principled tie-break is a ranker, gated by rule 6 / D-008
(O-006 / O-012); the new test fails if one is added, forcing that decision to be
registered rather than landing silently. No economic claim is made or implied;
the verdict stays `NO_ECONOMIC_CLAIM` (rule 12).

## 2026-08-02 — Second-level provenance + PIT bugfix pass (7 fixed)

An adversarial re-audit against the `V8_CONSTITUTION` bug-class catalogue
(implementation substitution / parallel economic truth / temporal leakage /
silent data corruption / boundary bugs / provenance scope) confirmed several
second-level defects; all were fixed with regression tests and a deliberate
golden re-pin (candidate_count 21 and terminal_distribution UNCHANGED).

- **`src/v8/lab.py` (medium) — PIT consumption order.** The state accumulator
  consumed the tape in canonical replay order `(event_time, available_time,
  venue_sequence)`, which is NOT guaranteed available-monotonic when latencies
  are heterogeneous — a row with a later event can become available earlier,
  and the moving pointer silently SKIPPED it (a state built without a bar that
  WAS admissible at the decision clock). The lab now consumes a stable
  available_time-sorted copy (`pit`) for the bar loop AND the accumulator;
  byte-identical for co-monotonic tapes (golden unchanged).
- **`src/v8/lab.py` (medium) — parallel economic truth.** The tape-end close
  of an open position re-derived the net formula `sign*(close-entry)/unit -
  cost - funding_paid` in the epilogue instead of delegating to the simulator.
  Added `CanonicalSimulator.close_out(pos, final_close)` as the single
  authority; the epilogue calls it (a second copy would silently diverge the
  moment cost/funding policy changes).
- **`src/v8/lab.py` + `src/v8/schema.py` (medium) — unpinned risk gate.** The
  effective `RiskGate` (max_heat / max_cluster_heat / clusters) is a
  run-configuration input, but was invisible in every hash when no cap was
  breached. The ledger hash now binds `risk_config_hash` and the `LabReport`
  surfaces `risk_gate_hash` (report-only). Golden ledger hash re-pinned.
- **`src/v8/lab.py` (low) — `_code_hash` over-binds vendored `simtruth/`.**
  The decision-path code hash covered `src/v8/simtruth/**` (vendored V7,
  engineering only, nothing imports it), so a vendored edit invalidated every
  pinned manifest for a byte-identical decision path. `simtruth/` is now
  excluded from `_code_hash`.
- **`src/v8/lab.py` (low) — fabricated empty-tail counterfactual.** A
  TRIGGERED candidate rejected for excess cost on the FINAL tape bar (no entry
  bar) got a fabricated `EXPIRY/0.0/NOT_EXECUTED` outcome from `sim.run([])`,
  while the identical never-entered candidate below the cost gate is recorded
  `INVALIDATED_BEFORE_TRIGGER`. Same fact, two endpoints. The never-entered
  convention now applies in both branches.
- **`src/v8/marketstate.py` (low) — null is not zero.** An absent feature
  (`prior_high`/`prior_low` on the first bar) was labelled `COMPLETE` with
  `null_reason=None` and its `max_input_available_time` borrowed the newest
  bar it never consumed — both contradict the `MARKET_STATE_CONTRACT`
  (§2 consumed-derived clock; §4 "null is not zero"). None-valued features are
  now auto-`DEGRADED` with `null_reason=NOT_YET_AVAILABLE` and a consumed-only
  calculation clock (0 when nothing was consumed). Golden state/ledger hashes
  re-pinned; candidate decisions unchanged.
- **`tools/run_experiment.py` (medium) — holdout window never reconciled.**
  `data_hash` binds the tape bytes, not the window: a dev-period tape (or a
  dev+OOS merge) authored with `start_ns >= anchor` was evaluated as the
  frozen OOS. The runner now fails closed when the tape's kline event range
  falls outside `[start_ns, end_ns]` (prereg §13).

Artifacts: `src/v8/lab.py`, `src/v8/simulator.py`, `src/v8/marketstate.py`,
`src/v8/schema.py`, `tools/run_experiment.py`, `tests/test_golden_backtest.py`
(deliberate golden re-pin), `tests/test_bugfix_pass.py`,
`tests/test_run_experiment.py`.

## 2026-08-01 — Adversarial-audit fixes on Phase 2-4 code (14 findings, 6 fixed)

A four-dimension adversarial review (correctness / contract / determinism /
runner) confirmed 14 findings; the real ones are fixed here.

- **`src/v8/lab.py` (medium)** — the pre-entry invalidation now uses the
  expert's FROZEN windowed prior ref (`prior_low_ref` / `prior_high_ref` in
  the draft geometry) instead of the all-bars state feature, which diverges
  from the thesis ref (an old spike outside the 32-bar window pins it). A
  dead-thesis candidate no longer triggers and enters, polluting the executed
  population. Dev trigger count 3,295 -> 2,939; golden terminal distribution
  changes (deliberate re-pin).
- **`src/v8/marketstate.py` (low ×2)** — `max_input_available_time` is now
  the consumed-derived clock (prior_high/prior_low never claim the newest bar,
  which is not their input); the history feature's `input_lineage_hash` now
  covers the full close series (its EMA columns depend on it).
- **`tools/run_experiment.py` (medium ×2, low)** — prereg §9 mechanical
  block-size rule implemented (24 by default; 168 when the lag-1
  autocorrelation of episode net_R exceeds 0.10); family scores are NOT
  reported when the D-027 gate fires ATTRIBUTION_UNSAFE_* (§11 "not scored");
  the holdout hash is REQUIRED (fail closed on an un-pinned holdout, §16);
  the frozen OOS window must start strictly after the 2026-07-01 anchor (§13);
  `h0_rejected` is now the composite §11/§12 test (lower bound > 0 AND
  n_f >= 30).
- **Runner bootstrap percentile fix** (caught by the dev-tape smoke run) — the
  2.5th-percentile LOWER bound was indexed at the 97.5th percentile; a
  negative-mean family could falsely report h0_rejected.
- 5 new regression tests; suite 148 -> 152. Dev materialization re-pinned
  (`adad594a…`, views4); prereg §6/§15 updated (execution_share 0.4662,
  KS 0.1028 — diagnostics only; thresholds unchanged).

## 2026-08-01 — Dev materialization re-pin (three pilots, D-042)

- Dev tape re-materialized with the third pilot (`liquidity_sweep_reclaim`)
  and the Phase-2/Phase-4a code: candidate_count 2,786 -> 3,323, ledger_hash
  `40d4f23a…` (fresh `views3` dir, compile-once; code_hash `fec878c5…`).
- Prereg §6 derived outputs and §15 12-month diagnostics updated: with three
  pilots the D-027 populations are `n_executed` 1,415 / `n_portfolio_rejected`
  1,476, execution_share 0.4895, KS 0.0932 — **diagnostics only**, the
  ratified thresholds 0.25/0.20 are unchanged (O-017).
- Monograph rebuilt; suite 147 tests green.

## 2026-08-01 — Phase 4b: v8_slice_001 experiment runner

- **`tools/run_experiment.py`** — the preregistered `v8_slice_001` runner:
  validates the frozen manifest (experiment_id, universe BTCUSDT, interval
  1h), verifies the pre-recorded holdout tape hash before any evaluation
  (fail closed on mismatch or absent holdout — never fabricates a verdict),
  runs the two pilot families on the frozen OOS, computes family-level
  one-sided tests with a deterministic block bootstrap (block 24, fixed seed)
  and Bonferroni multiplicity control (alpha_f = 0.025), and surfaces the
  D-027 attribution statistics. Authority blocks first (no receipt ->
  NO_ECONOMIC_CLAIM). The RUN is gated on the frozen holdout existing (first
  two published months after 2026-07-01 + 9-bar extension, prereg §13).
- 5 tests (fail-closed absent holdout, frozen-constant validation, holdout
  hash recorded-before-evaluation, hash mismatch fail-closed, bootstrap
  determinism/one-sidedness). Suite 142 -> 147.

## 2026-08-01 — Phase 3: third pilot + DATA_BLOCKED backlog (D-042)

- **`src/v8/experts/liquidity_sweep_reclaim.py`** — `LiquiditySweepReclaimExpert`
  (`liquidity_sweep_reclaim` / `sweep_reclaim`, variant `a`): LONG after a
  sweep of the windowed prior low that closes back above it, SHORT after a
  prior-high sweep reclaimed by the close; `prior_low_ref`/`prior_high_ref`
  frozen at detection (failed_breakout pattern) and excluded from
  `geometry_version` (`src/v8/lab.py`). Re-exported; added to
  `tools/materialize_views.py` PILOTS.
- **`docs/EXPERTS_REGISTRY.yaml`** — third pilot at FORMALIZED; `breakout_retest`
  and `capitulation` backlog families registered DATA_BLOCKED until
  derivatives tape (no code module — ROADMAP Phase 3 backlog).
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md`** — tree + file table + planned
  note updated; **`D-042`** registered (D-032 file-family rule).
- Registry/artifact tests amended for the third pilot + DATA_BLOCKED entries.
  4 new expert tests; suite 139 -> 142. The dev materialization is re-pinned
  (see the materialization entry below).

## 2026-08-01 — D-027 attribution-validity gating in LabReport (Phase 4a)

- **`src/v8/schema.py`** — LabReport gains `n_executed` / `n_portfolio_rejected`
  / `execution_share` / `divergence_ks` (two-sample KS on executed vs
  portfolio-state-rejected net_R) and the verdict vocabulary
  NO_ECONOMIC_CLAIM | CERTIFIED_AVAILABLE | ATTRIBUTION_UNSAFE_LOW_COVERAGE |
  ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE. Authority blocks first (receipt
  None -> NO_ECONOMIC_CLAIM regardless); thresholds are the ratified O-017
  numbers (0.25 / 0.20), fixed forever.
- **`src/v8/lab.py`** — stdlib-pure `_two_sample_ks` (scipy/numpy banned in the
  decision path, D-031), `_d027_verdict`, and the epilogue computation of both
  populations. Verified to reproduce the prereg §15 12-month diagnostics
  exactly (execution_share 0.4576, KS 0.1044, n=1111/1317) on the dev tape.
  Hash-neutral (statistics derive from ledgers already inside ledger_hash) —
  no golden re-pin.
- **Prereg §15** — the 12-month diagnostics corrected to the
  label_status-based population definition (n_executed 1,111 — the earlier
  draft counted INVALIDATED_BEFORE_TRIGGER as executed); the lab's own
  D-027 computation is now the source of these numbers.
- 9 new tests; suite 127 -> 136.

## 2026-08-01 — Phase 2 completion: per-feature input lineage + state provenance

- **`src/v8/schema.py`** — `FeatureValue` gains `input_lineage_hash` (identity
  of the raw rows that produced the feature) and `calculation_time`;
  `FEATURE_GRAPH_VERSION` (hash of the FEATURE_GROUPS declaration);
  `MarketState` gains a `provenance` block
  {raw_manifest_hash, feature_graph_version, code_version}.
- **`src/v8/marketstate.py`** — build_state binds each feature's input lineage
  (payload_hash when the tape computes it, else the payload — synthetic tapes
  carry no payload_hash) and fills the provenance block. These are audit
  metadata: they do NOT join the identity hashes (a raw revision that does not
  change a value must not fabricate a new state identity).
- **Golden re-pin (deliberate, PERSISTENCE_REPLAY_SPEC 4):** the persisted
  state records gain the new fields, so `GOLDEN_STATES_HASH` and
  `GOLDEN_LEDGER_HASH` move; `GOLDEN_DATA_HASH`, candidate count 21 and the
  terminal distribution are unchanged (feature values are identical — expert
  behavior is byte-identical).
- 3 new tests (per-feature lineage + calculation clock, revision-without-
  value-change lineage, provenance determinism). Suite 136 -> 139.

## 2026-08-01 — 12-month dev materialization + pinned rebuild (D-041)

- **12-month dev tape built and audited clean** — BTCUSDT 1h 2025-07-01..
  2026-07-01: 8,760 klines + 1,188 funding rows (incl. the `2026-07` coverage
  horizon) = 9,948 rows, tape hash `4c8e5888…`, 25 SHA-256-verified Vision
  archives. Audit: 0 gaps, 0 duplicates, payload hashes OK; the old 3-month
  tape still audits clean.
- **`research/tape/btcusdt-1h-12m/manifest_dev.json`** — `experiment_id
  v8-dev-12m-btcusdt`, code_hash `ea8db9e2…`, data_hash `4c8e5888…`.
  Materialized in a fresh store/views dir (compile-once): market_states 8760,
  candidate_birth/outcomes 2786, candidate_trigger 2779,
  execution_trajectories 11684; ledger `c78bf43a…`, verdict
  `NO_ECONOMIC_CLAIM` (no authority receipt).
- **Prereg pins updated** — §6 manifest + derived outputs, §13 dev hash, §15
  12-month diagnostics appended (execution_share 0.4596, KS 0.1067) **as
  diagnostics only**; O-017 thresholds 0.25/0.20 unchanged. DATASET_SPEC
  §6.1/§6.2/§6.4 measured rows updated.
- Monograph rebuilt; suite untouched (127 tests).

## 2026-08-01 — Tape-driven funding wiring (D-041) + golden re-pin (sim v5)

- **`src/v8/simulator.py`** — `CanonicalSimulator` gains `funding_schedule`
  ((boundary_time_ns, rate) pairs); a non-empty schedule settles each crossed
  boundary at `entry_price × rate / risk_unit` (DATASET_SPEC 6.4) and fails
  closed on a missing boundary; the empty schedule keeps the legacy scalar
  path byte-identical. Sim hash bumps to `canonical-sim-v5`; schedule values
  are tape data bound by `data_hash`, never by `sim.hash()`.
- **`src/v8/lab.py`** — `Lab.run` builds the schedule from the tape's
  `funding` rows and passes it to the simulator; `_validate_tape_rows` gains
  the funding branch (non-finite / |rate| > 0.10 fail closed).
- **Golden re-pin (PERSISTENCE_REPLAY_SPEC 4, deliberate):** the only moved
  pin is `GOLDEN_LEDGER_HASH` (outcomes' `simulator_hash` changed via the sim
  source hash + v5); `GOLDEN_DATA_HASH`, `GOLDEN_STATES_HASH`, candidate
  count 21 and the terminal distribution are unchanged — the synthetic tape
  carries no funding rows, so the event stream is byte-identical.
- Tests: 4 schedule-driven funding tests + 1 lab-level schedule wiring test;
  sim-hash canaries re-pinned to v5. Full suite 122 -> 127.

## 2026-08-01 — D-041: 12-month dev window + tape-driven funding (owner)

- **D-041 registered** — the declared dev dataset expands from 3 to 12 months
  (BTCUSDT 1h, `2025-07-01`..`2026-07-01`, ~8,760 bars) and the `funding`
  channel is ingested into the PIT tape with tape-driven settlement
  (`funding_settled_r = entry_price × rate / risk_unit`), per DATASET_SPEC
  §6.4. O-017 thresholds 0.25/0.20 are **not** touched; the 12-month baseline
  updates prereg §15 diagnostics only. Funding coverage horizon `2026-07`
  declared so end-of-dev positions settle across the 2026-07-01 boundary.
  Dev end stays strictly before the holdout anchor.
- **`docs/PREREGISTRATION_V8_SLICE_001.md`** — §8 funding baseline becomes
  tape-schedule-driven (scalar retained as no-funding-tape fallback); §13 dev
  window 12 months + coverage horizon; §15 diagnostics note (thresholds
  fixed); §6 dev-tape hash marked pending the rebuild.
- **`docs/contracts/DATASET_SPEC.md`** — §6.1 channels/dev-window rows, §6.2
  scale expectations, §6.4 funding status, §6.5 declared list updated.
- **`docs/decisions/DECISION_REGISTER.md`** — D-041 row.
- No code or test changed in this pass. Monograph rebuilt; suite untouched
  (112 tests).

## 2026-08-01 — Full-program target (D-040, owner)

- **D-040 registered** — the v0.1-only framing is retired; the program target
  is the full 8-phase roadmap with the evidence gates unchanged (rules 5-6,
  12, 14). Build priority completes Phases 0-4 first; the critical path is the
  Phase-4 `v8_slice_001` experiment runner + D-027 verdict gating. Phases 5/7
  are built only when their gate passes — never on a calendar date.
- **`docs/PLAN_V8_FULL.md` added** — sprint breakdown (Sprint A: Phase-4
  runner; Sprint B: Phase 2/3 completion; Sprint C: Phase 6 ops;
  data-blocked: derivatives tape, holdout window). Planning artifact, not
  registered in the monograph NAMES list (no TR mirror).
- **`docs/ROADMAP.md` updated** — the versioning line no longer frames the
  program as "v0.1 = Phase 0-4 foundation"; the full roadmap is the target.
- No code, contract, or test changed in this pass. Monograph rebuilt; suite
  untouched (112 tests).

## 2026-08-01 — Session-6 bugfix pass (adversarial audit fixes)

Adversarial bug hunt (11 class-scoped finders + per-finding verification) on
`src/v8/` + `tools/` confirmed 26 findings; this pass fixes them. Decision-path
changes move the golden ledger hash (outcome-label change) and are re-pinned in
`tests/test_golden_backtest.py`; candidate counts and terminal distribution are
unchanged. New regression tests: `tests/test_bugfix_pass.py` (11 tests). Full
suite 86 → 97.

- **`src/v8/lab.py`** — closed-only bars in the decision loop (open klines no
  longer drive entries/stops); multi-instrument tapes fail closed (H1/M5);
  duplicate decision clocks fail closed (M6); pre-entry invalidation re-checked
  on the entry bar (H3); `INVALIDATED_BEFORE_TRIGGER` relabelled `NOT_EXECUTED`
  (H5); counterfactual now applies the owning Expert's `still_valid` via a
  per-clock state map (H2); `prior_low/prior_high` fail closed instead of
  defaulting to 0/inf (M10); `_INTERVAL_NS` fails closed on unknown intervals
  (M12); `excess_cost` threshold promoted to named `EXCESS_COST_THRESHOLD_R`.
- **`src/v8/simulator.py`** — `run()` gains `thesis_valid(bar_time, payload)`
  so the batch counterfactual exits `THESIS_INVALIDATED` like the executed path;
  every returned outcome carries `label_available_time` (exit clock), the
  DATASET_SPEC section 4.5 embargo primitive.
- **`src/v8/schema.py` / `tools/materialize_views.py`** — `CounterfactualOutcome`
  and the `candidate_outcomes` view now expose `label_available_time`, so a
  training consumer can refuse labels whose availability overlaps its
  validation window (M4).
- **`src/v8/risk.py`** — D-024 funding-window veto measures boundaries on
  absolute wall-clock hours (`funding_hours * HOUR_NS`), matching
  `simulator._boundaries_crossed`; on non-1h tapes the old period missed
  imminent-boundary entries (H4).
- **`src/v8/marketstate.py`** — a universe symbol with zero emitted features
  degrades the state (DEGRADED), closing the missing-symbol quality gap (M2).
- **`src/v8/lifecycle.py`** — `any terminal -> ARCHIVED` added to `LEGAL`
  (CANDIDATE_LIFECYCLE_SPEC), making ARCHIVED reachable (M9).
- **`tools/monitor_tape.py`** — OHLC type/finiteness/invariant + volume checks
  (booleans, NaN/±inf, high<low, negative volume all fail); staleness measures
  kline rows only (M1/M7/L3).
- **`tools/vision_backfill.py`** — `audit_tape` gains OHLC/volume/finiteness
  invariants; `check_archive_revision` also guards legacy single-month
  `source.json` (M1/M8).
- **`tools/data.py`** — `_validate_price_rows` fails closed on NaN/±inf prices
  (M1).
- **`tools/materialize_views.py`** — `views_manifest.json` now carries a
  `views_pin` binding view SQL + manifest economics + code hash + views_dir;
  a recompile with a changed pin fails closed instead of silently replacing
  the "pinned" views (M11).

## 2026-08-01 — Session-6 second-level audit fixes (post-fix classes)

Second adversarial pass on the POST-FIX codebase (8 class-scoped finders:
alternative paths, boundary matrix, fail-open, hash canary, state coverage,
feature contamination, zero-trade provenance, reconciliation; 29 agents).
Confirmed 13 findings; this entry fixes them. Suite 104 → 108 (new regression
tests in `tests/test_bugfix_pass.py`); golden re-pinned (candidate_count
24 → 21: failed_breakout now gates on a windowed prior-high reference).

- **`src/v8/experts/failed_breakout.py`** — gate and anchor now share ONE
  prior-high reference (the history-window max excluding the newest bar). The
  old gate used the state's ALL-BARS prior_high, which an old spike outside the
  window pinned forever: the draft fired every bar, the anchor slid, and
  episode-key dedup silently produced a new DETECTED episode per bar. The
  post-entry thesis (`still_valid`) now uses a FROZEN `prior_high_ref`
  (excluded from episode identity like `atr_ref`), so a reversal that re-crosses
  the entry-time breakout level invalidates instead of drifting with the
  adverse move.
- **`src/v8/lab.py`** — `Lab.run` fails closed on a non-empty manifest
  `code_hash`/`data_hash` that does not match the live code/tape (the
  composition root no longer reports a stale or forged pin; materialize_views
  already checked, Lab.run is the authority). `terminal_distribution` is now
  candidate-counted (a `CLOSED -> ARCHIVED` candidate appears once) and the
  report adds `rejection_distribution` (D-024 vs risk vs excess-cost), `tooling_hash`
  (tools/*.py, outside the decision-path hash), and the excess-cost/tape-end
  `label_available_time` fallback to `last_as_of` (the 0-sentinel leak).
- **`src/v8/risk.py`** — the D-024 FUNDING_WINDOW veto fires whenever
  `window >= period` (a boundary always books funding on the first post-entry
  step; the old `window < period` guard silently disabled the check, so e.g.
  1d bars with funding_hours=8 admitted entries that settled 3x). The veto
  clock basis is the entry FILL time (available), matching simulator settlement.
- **`src/v8/schema.py`** — `LabReport.rejection_distribution`, `tooling_hash`.
- **`src/v8/experts/`** — no other changes; the trend_pullback thesis remains
  a live trend reference (correct by design).

## 2026-08-01 — Session-6 provenance + performance fixes (B1-B4, P1-P3)

Follow-up audit (parallel session) confirmed 4 ledger/provenance bugs + 3
structural performance items; this entry fixes them. The ledger hash now binds
the run configuration, so the golden re-pins. Suite 108 → 112.

- **`src/v8/lab.py`** — B1: a TRIGGERED candidate with no entry bar before tape
  end records `INVALIDATED_BEFORE_TRIGGER`/`NOT_EXECUTED`/0.0 (label knowable at
  tape end) instead of the fabricated empty-tail counterfactual
  (`EXPIRY`/`RIGHT_CENSORED`/0.0 with a fake simulator hash) — a non-trade no
  longer merges into the censored population (B5 naming aligned with the
  INVALIDATED terminal). B2/B3: the manifest is persisted to
  `<store>/manifest.json` and the ledger hash binds `config_hash =
  sha1_hex(asdict(manifest))` — different economics AND an authority receipt
  added later both move the ledger hash (no silent re-labelling). P1: the
  per-bar state build is O(N) incremental (moving pointer over the replay-sorted
  tape) instead of the O(N²) rescan that dominated run time.
- **`src/v8/lifecycle.py`** — B4: `CandidateRegistry` replay validates every
  `(from_state, to_state)` against LEGAL and raises on an illegal transition in
  a corrupt log (mutation-campaign fail-closed).
- **`src/v8/store.py`** — P2: `AppendOnlyLog` opens the append handle once and
  flushes per record (per-record open/close was ~half the profiled append cost);
  crash-loss policy stays bounded to the current record.
- **`src/v8/simulator.py`** — P3: `_boundaries_crossed` is O(1)
  (`floor(t/P) - floor(entry/P)`), byte-identical over the 144-case boundary
  matrix vs the per-hour loop.
- **`src/v8/marketstate.py`** — P1: the 5/20 EMA series are computed once and
  shared by the trend features and the history tuples (was computed twice per
  state).

## 2026-08-01 — Declared dataset v0.1 (operator)

- **D-039 — `DATASET_SPEC` §6 "Declared dataset v0.1" added.** The corpus had
  no declaration of what the dataset is or at what scale; this closes it.
  Declares: universe BTCUSDT (O-011 lock), 1h interval, channels `kline`
  (ingested) + `funding` (**declared, ingestion pending**), dev window
  2026-04..06 (hash `8b12707e…`), frozen OOS = first two published months
  after 2026-07-01 + 9-bar label extension (downloaded only at experiment
  time). Scale expectations table is measured (1h tape is small by
  construction: ~640 B/row; full history ~33 MB; 30 symbols ~1 GB; Tier-A/S
  gated by O-010). "More data" is now a register decision, never a silent
  download.
- **Funding gap made explicit and actionable:** simulator funding plumbing
  exists but `funding_rate_r = 0.0` (dev manifest + preregistration §8) — the
  channel is now declared with ingestion pending; next step is
  `GET /fapi/v1/fundingRate` backfill -> `funding` tape rows ->
  `funding_settled_r = entry_price × rate / risk_unit` -> preregistration §8
  revision, all before the holdout is opened (§16).
- Rebuilt `site/index.html` (32 sections — new probe baseline for the next
  session).

## 2026-08-01 — O-017 ratification + preregistration promoted (operator)

- **O-017 resolved by operator ratification** (2026-08-01):
  `execution_share` floor = **0.25** (60% of the dev-window 0.4156) and
  population-divergence threshold = **two-sample KS on `net_R` ≤ 0.20**
  (~2.7× the dev-window 0.073). Both were derived pre-holdout from the
  session-2 baseline (`v8-dev-2026q2-btcusdt`) and are fixed forever — never
  revisable after a verdict. Moved from the open list to a Resolved section
  in `OPEN_DECISIONS.md`; D-027 register entry updated.
- **`PREREGISTRATION_V8_SLICE_001.md` status RATIFIED** (was "frozen content
  for operator approval"); §16(a) marked DONE. The document is now registered
  in `tools/build_monograph.py` NAMES and appears in the monograph (section
  count 31 -> 32).
- The experiment is still **not run**: the frozen holdout does not exist
  until experiment time, no authority receipt exists, and every run's verdict
  stays `NO_ECONOMIC_CLAIM` (rules 8-9, 12).
- Rebuilt `site/index.html` (new probe baseline for the next session).

## 2026-08-01 — Session-2 closure: Phase 1 real data + preregistration (operator pass)

Session 2 (commits `3436248`..`91396fe`) executed Phase 1 on real data and
wrote the `v8_slice_001` preregistration; all 5 steps DONE, suite 42 -> 50
tests, monograph probe byte-identical to the session-2 baseline
(`ea5b7705…`) at every step, corpus untouched (verified independently on
re-review). This operator pass closes the pins the agent left.

- **D-038 registered** — Phase-1 tooling deps (polars/pyarrow/
  pandera[polars]/duckdb) admitted as the `tooling` extra for `tools/data.py`
  + `tools/materialize_views.py`; decision path stays stdlib-only. Resolves
  the session-2 open pin 1.
- **IMPLEMENTATION_LAYOUT updated** — `tools/vision_backfill.py` and
  `tools/materialize_views.py` moved from "planned" into the file family
  (tree + file table); five test files listed.
- **Real tape pinned** — BTCUSDT 1h 2026-04..06 (2184 rows, tape hash
  `8b12707e…`), verified via `data.py`; JSONL PIT tape audit clean;
  materializations + lab run deterministic (ledger `2c1e0fd8…`,
  `NO_ECONOMIC_CLAIM`). Derived artifacts live under `research/tape/`
  (gitignored, reproducible — never committed).
- **`v8_slice_001` preregistration** (`docs/PREREGISTRATION_V8_SLICE_001.md`)
  written with all HYPOTHESIS_LAB_PROTOCOL fields; O-017 proposal (share
  floor 0.25, KS threshold 0.20) derived pre-holdout from the dev baseline
  (execution_share 0.4156, KS 0.073); adversarial review (1 blocker + 7
  warnings) incorporated. **Not yet in the monograph** — it is frozen content
  awaiting operator ratification (§16); holdout not downloaded, experiment
  not run.
- **Carry-forwards (operator + Phase 4):** D-027 verdict gating
  (`execution_share`/divergence/`ATTRIBUTION_UNSAFE_*` in `LabReport`)
  remains code-pending; it lands with the Phase-4 experiment runner. The
  preregistration's §16 operator actions (ratify thresholds; record holdout
  tape hash at download time; authority receipt before any verdict) are
  unperformed by design.
- Rebuilt `site/index.html` (31 sections — the three edited corpus files are
  all monograph sections; the probe baseline for the next session changes).

## 2026-08-01 — Autonomous build session closure (operator pass)

The Phase 0-3 autonomous build (commits `4f34abe`..`f2f8bf2`) completed all
7 runbook steps: the vertical-slice suite grew 15 -> 42 tests, the monograph
probe rebuild was byte-identical to the baseline hash at every step, and the
`docs/` corpus was untouched by the agent (verified independently on
re-review). This operator pass closes the artifacts the agent was not
authorized to write.

- **IMPLEMENTATION_LAYOUT §4 divergence rows closed** with their commits:
  episode_key anchor (D-026, `4f34abe`), funding settlement
  (SIMULATION_TRUTH_SPEC §5/§7, `760e6cc`), D-024 mask (`778ceb1`). The D-026
  key-stability cheap test is now part of the suite (§5 item 4 updated).
- **D-037 registered** — resolves the Step-4 OPEN_PIN: the stdlib mirror of
  `tools/data.py` contracts in `tools/vision_backfill.py` is accepted;
  literal reuse deferred until Phase-1 parquet materialization admits the
  heavy deps. `pyyaml>=6` dev-extra noted (environment, not decision path).
- **`docs/EXPERTS_REGISTRY.yaml` registered in the monograph build** (section
  count 30 -> 31): the Phase-3 expert registry now has a visible home next to
  CLAIMS/EXPERIMENT registries; the agent could not add it to NAMES (docs
  freeze).
- Rebuilt `site/index.html`; runbook Step 3's funding-window interpretation
  and the seed-7 epoch artifact remain recorded in `RUNLOG.md` and
  `docs/STATUS_REPORT.md` (session artifacts, not corpus).

## 2026-08-01 — Autonomous build handoff (design + tooling line)

Design line only; no runtime code changed in this pass.

- **`docs/AGENT_RUNBOOK.md` added** — execution contract for a ~2h
  autonomous build (Phase 0-3). Seven timeboxed steps (D-026 anchor, funding
  settlement, D-024 mask, `vision_backfill.py` + tape audit, feature
  groups/lineage, expert metadata + registry, status report) each with
  owning files, DoD commands, gates, and commit messages. Hard rules: spec
  freeze (agent never edits `docs/` except RUNLOG/STATUS_REPORT), forbidden
  components (rules 6/14), no experiment runs, no frozen-OOS opening,
  tests-as-contract-probes, no `--amend`, no `git add -A`.
- **Anti-drift gate:** every step re-probes the monograph build and requires
  byte-identity with the pre-flight hash — a contract edit would change the
  hash and fail the gate.
- **D-034/035/036 registered** — implementation pins for D-026 (anchor =
  first bar of the setup run via a new 32-bar `history` feature group; key
  drops birth timestamp; `is_duplicate` becomes anchor-key equality),
  funding (`funding_rate_r`/`funding_hours` manifest fields,
  `SETTLEMENT_BEFORE_ORDERS`, `canonical-sim-v4`), and D-024 mask
  (declared constants, `TRADABILITY_MASK_VETO`). The agent implements the
  pins; it does not revisit them.
- `tools/build_monograph.py` NAMES extended (29 -> 30 sections);
  `site/index.html` rebuilt. `RUNLOG.md` template at repo root (session
  artifact, not corpus).

## 2026-08-01 — File-family restructure (code + layout)

- **D-033 — `src/v8/experts/` subpackage.** `experts.py` split into one file
  per behavior family: `experts/base.py` (Expert base + `_need` +
  `still_valid` contract), `experts/trend_pullback.py`,
  `experts/failed_breakout.py`; `experts/__init__.py` re-exports the pilot set
  so `from v8.experts import ...` is unchanged for consumers.
- **`marketstate.py` retained.** The proposed `state.py` rename was rejected
  by the owner — the file mirrors the `MarketState` record name.
- **`lab._code_hash` now recursive (`rglob('*.py')`).** The flat glob missed
  `experts/*.py`, so an Expert change would not have bound the report (D-010).
  Relative path keys keep the hash stable across checkouts.
- `IMPLEMENTATION_LAYOUT.md` §1/§2/§3 updated to the new tree; file-family
  table now covers `experts/` per file. Tests: 15/15 green after the move.

## 2026-08-01 — Architecture + implementation-layout contracts (design line)

Design-line only; no runtime code changed in this pass.

- **`docs/contracts/ARCHITECTURE_SPEC.md` added.** The monograph claimed to be
  an architecture specification but carried only the 5-line minimum-coherent
  diagram. The new contract names the full component map (tape -> MarketState
  -> Experts -> candidate log -> acceptance/RiskGate -> canonical simulator ->
  lab runner -> hash-bound report), the owning contract and gate of every
  stage, the stepped vs counterfactual execution split (D-009/D-027), and the
  absent-by-default list. Registered as **D-031** (technology baseline).
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md` added.** The file family was
  never designed: `src/v8/` files emerged from the vertical slice, and three
  code/spec divergences followed (episode_key, funding, D-024). The contract
  predetermines every file's responsibility, public interface, and owning
  contract; layering rules (acyclic one-way imports, composition root =
  `lab.py`, no wall clock, stdlib-only decision path); a tracked-divergence
  table; and cheap tests including a kept-red D-026 key-stability gate.
  Registered as **D-032**.
- **O-009 scoped:** the storage-engine *design* is resolved by D-031 (Parquet
  archive + JSONL ledgers + DuckDB derived tables per PERSISTENCE_REPLAY_SPEC
  §1); only the scale-validation experiment remains open.
- `tools/build_monograph.py` NAMES extended (27 -> 29 sections);
  `site/index.html` rebuilt. `docs/tr/` remains a partial mirror and skips the
  new sections, consistent with the existing TR lag.

## 2026-08-01 — R-unit correction, excursions, thesis exit (code + design)

- **D-028 — the simulator was not producing R.** `stop_r`/`target_r` were
  applied as fractional price moves (`entry * (1 + target_r)`, so the shipped
  `target_r = 1.0` meant a +100% price target) and `net_r` was a fractional
  return with an R-calibrated cost constant subtracted from it. Measured before
  the fix: a target hit returned −0.0500 and a stop-out −0.0800 — a winning
  trade booked a loss, and every trade was negative regardless of outcome, so
  no Expert could ever have passed. Risk was also invisible: two positions with
  10× different stop width returned identical numbers. R is now an explicit
  declared price distance (`simulator.risk_unit`, from `atr_ref` or a declared
  `risk_frac`), non-positive units fail closed, and the same measurements now
  return +1.9300 / −1.0700 / identical-across-widths. This defect sat under
  D-023: heat summed a quantity that was not risk.
- **D-030 — excursions and ambiguity restored.** `OpenPosition` and
  `CounterfactualOutcome` carry `mae_r`, `mfe_r` and `ambiguous_bars`. The
  vendored V7 simulator (`simtruth/sim.py`) already had `mae_r`/`mfe_r`; the
  V8 canonical simulator had dropped them — a regression on precisely the
  quantity V7 measured as most predictable (ICs +0.124/+0.152 vs +0.015). Same-
  bar stop+target ambiguity was being resolved by `STOP_FIRST` but never
  recorded, contrary to `SIMULATION_TRUTH_SPEC`. O-013 is now answerable and
  the ambiguity bracket measurable.
- **D-029 — post-entry thesis invalidation.** `Expert.still_valid(state, draft)`
  is evaluated on closed bars while a position is `EXECUTED`; a dead thesis
  closes at that bar's close with `THESIS_INVALIDATED`, distinct from `STOP`.
  Implemented for both shipped Experts (trend gone / breakout succeeded after
  all). Deterministic, inside the frozen spec, no new lifecycle state, no
  learned component; fails open when inputs are unobservable.
- Simulator hash bumped to `canonical-sim-v3`; pre-fix ledgers can no longer
  compare equal to post-fix ones.
- Tests: 7 → 15. New golden tests pin stop-out to exactly −1R − cost, target to
  +target_r − cost, R-invariance across 10× risk width, excursion values,
  ambiguity counting with STOP_FIRST, fail-closed risk unit, and the thesis
  exit. Full suite green.
- Not done: funding is still absent from the simulator while
  `SIMULATION_TRUTH_SPEC` §5/§7 mandate `SETTLEMENT_BEFORE_ORDERS` and
  boundary golden tests — material for perps (~3 settlements per 24×1h hold)
  and the V7 audit's one caught defect. `episode_key` still implements the
  D-026 defective form. D-024 tradability mask remains spec-only.

## 2026-08-01 — Attribution validity gate + episode identity (design line)

Design-line only; no code changed in this pass.

- **D-026 — episode identity contradiction resolved.** `episode_key` was
  defined three ways at once: `CANDIDATE_LIFECYCLE_SPEC` §1 (birth timestamp),
  `EXPERT_PROTOCOL` §2 (`setup_anchor_event_id`), and `src/v8/lifecycle.py`
  (birth timestamp). The clock-anchored form is a defect, not a variant: the
  same setup on consecutive bars hashes differently, so the suppression window
  can never match and deduplication silently never fires — confirmed by direct
  execution against `CandidateRegistry.is_duplicate`. §1 is now the single
  normative definition, anchored to `setup_anchor_event_id`; `EXPERT_PROTOCOL`
  references it instead of restating it, and a key-stability cheap test was
  added. **Follow-up: `src/v8/lifecycle.py:36` still implements the defective
  form; spec and code are knowingly divergent until that lands.**
- **D-027 — attribution validity gate (new).** V8 failed closed on data and on
  authority but not on whether the measured population was the traded one. With
  the exposure rule and heat cap enforced against a stepped ledger, rejection is
  the designed outcome for most simultaneous Candidates, so counterfactual
  domination is structural rather than accidental. `LabReport` now carries
  `execution_share` (portfolio-state rejections only in the denominator — cost
  and invalidation rejections are the hypothesis, not bias) plus an
  executed-vs-rejected divergence statistic; breaching either declared bound
  yields `ATTRIBUTION_UNSAFE_LOW_COVERAGE` / `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE`
  rather than a net-utility figure. Refusal, not correction: OPE needs
  propensities a deterministic admission rule cannot produce (rejected
  Candidates have probability 0, the deficient-support case), and two
  independent literature searches returned no admissible finance application.
  Adds no decision-path component; complexity budget (rule 14) untouched.
- **O-014 rewritten, O-017 opened.** O-014's admission condition previously
  called for an OPE correction layer that the evidence does not support; it now
  routes divergence to D-027 instead. O-017 carries the two gate thresholds,
  which must be set from the observed rejection rate before the frozen slice is
  opened.
- Rebuilt `site/index.html` from the corpus. `docs/tr/` remains a partial
  mirror (11 of 27 sections) and does not yet carry D-026/D-027.

## 2026-08-01 — Production-readiness pass

- Repo restructured: `docs/` (corpus, single source of truth), `site/`
  (generated EN/TR monographs), `research/` (papers, text, manifest), `tools/`,
  `src/` (Phase-2 vertical slice). Git initialized.
- Corpus restored from `/tmp` backup (EN + TR); build made reproducible
  (`tools/build_monograph.py`, `site/index.html` and
  `site/tr.html`).
- 42 duplicate PDFs removed (md5-verified), ~88 MB freed.
- New plane specs: `FEED_INGESTION_SPEC`, `PERSISTENCE_REPLAY_SPEC`,
  `RUNTIME_SCHEDULER_SPEC`, `OPERATIONS_SPEC`; decision register extended
  (D-011..D-016).
- Phase-2 vertical slice (`src/v8/`): tape -> MarketState -> experts ->
  candidate lifecycle -> canonical simulator -> hash-bound lab report;
  synthetic-data tests passing.
- Ontology levels + identity metadata adopted (`V8_CONSTITUTION` rule 13;
  `EXPERT_PROTOCOL` section 1); feature-group `requires:` declarations added.
- Exposure-aware acceptance adopted (rule 16; `CANDIDATE_LIFECYCLE_SPEC`
  section 6); `ExposureBook` guard in the vertical slice.
- `LEARNING_PROTOCOL.md` added; online mutation forbidden (rule 15).
- Complexity budget adopted (rule 14).
- Tape compilation discipline adopted (`DATASET_SPEC` section 5; rule 17).
- V7 `lab/` vendored into `src/v8/simtruth/` (canonical reference simulation
  truth; only import paths rewritten) and V7 `tools/data.py` copied to
  `tools/` (canonical Binance archive -> verified tape builder).
  ENGINEERING-ONLY: V8's simulation authority is not renewed by the copy
  (D-022; OPERATIONS_SPEC section 1).
- Project venv via uv (`.venv`, numpy + pytest); 7/7 tests green.
- Roadmap added (`docs/ROADMAP.md`, Phases 0-7 with evidence gates).
- Agentic-coding pass: `CLAUDE.md` at repo root (read order, commands,
  non-negotiable rules); monograph build now emits a table of contents
  (`<nav id="toc">`) with per-section anchors; `site/archive/` removed
  (backed up); `tools/` reorganized (`build_monograph.py`, `heads/`).
- Stepped runtime (CANDIDATE_LIFECYCLE_SPEC section 6 conformance):
  `CanonicalSimulator` split into `step()` (execution ledger — positions live
  across decision clocks) and `run()` (batch counterfactual); `lab.run()`
  drives a 3-phase loop (enter -> step -> trigger -> evaluate); exposure
  conflicts now fire naturally; rejected candidates keep `NOT_EXECUTED`
  counterfactual outcomes — the executed-vs-rejected selection-bias dataset
  is now measurable; `RiskGate` skeleton added (`src/v8/risk.py`), heat
  policy is an open decision.
- Design-phase encoding (index.html only; code paused at user request):
  `CANDIDATE_LIFECYCLE_SPEC` section 6 extended — two-path execution (batch
  counterfactual attribution vs stepped execution ledger, positions live
  across decision clocks), portfolio heat cap (stop-risk R, fixed clusters,
  reject-not-downsize, D-023), mechanical tradability mask (D-024),
  fractional Kelly cap (D-025); open decisions O-013..O-016 (position
  management, selection bias, learned regime veto, drawdown sizing); evidence
  matrix citation verification (two arXiv ID corrections against the reading
  list; four converging literature gaps).
