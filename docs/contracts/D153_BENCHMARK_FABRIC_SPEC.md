# D-153 Benchmark Fabric Specification (Full-Text Constitutional Specification)

**Status:** PROVISIONAL_DECISION · **Date:** 2026-09-06 · **Rules:** 12, 28–31, 44, 51–57
**Supersession:** Extends D-147, D-150, D-151, D-152; preserves all locked invariants and epistemic boundaries.
**Artifacts:** `v8-core/src/benchmark/`, `v8-core/tests/d153_benchmark_fabric_sabotage.rs`, `v8-core/tests/d152_gate_vector_authority_firewall.rs`, `v8-core/tests/d153_receipt_ledger_selfverify.rs`, `v8-core/tests/d153_parity_adapters_policy_bound.rs`, `v8-core/src/kaizen/`, `docs/decisions/DECISION_REGISTER.md`, `docs/tr/D153_BENCHMARK_FABRIC_SPEC.md`.
**Turkish mirror:** `docs/tr/D153_BENCHMARK_FABRIC_SPEC.md` (registered 2026-09-07 under D-159; this file is the normative text and the mirror is a translation, not a second authority).

> **Status correction (D-159, issue #330).** This header previously read
> `RATIFIED_DECISION` while both decision registers recorded D-153 as
> `PROVISIONAL_DECISION`. The registers govern status, so the header was the
> divergent side and has been aligned rather than the register escalated. It also
> cited `v8-core/tests/benchmark_fabric_adversarial.rs`, a file that has never <!-- AUDIT-DOC-PATHS: NEGATIVE_CITATION `v8-core/tests/benchmark_fabric_adversarial.rs` is cited here precisely because it never existed; the real D-153 suite is `v8-core/tests/d153_benchmark_fabric_sabotage.rs`. -->
> existed in this repository; the D-153 sabotage suite is
> `v8-core/tests/d153_benchmark_fabric_sabotage.rs`. §2.6's "explicit typed
> adapters with recorded semantic divergence" was, at ratification, implemented
> as fixed in-process vectors and is now implemented as the artifact-bound
> adapters of `v8-core/src/benchmark/parity.rs` (issue #329). Neither correction
> changes any normative requirement in §§2–5.

---

## 1. Executive Thesis and Problem Statement

V8's epistemic infrastructure previously possessed strong individual verification organs:
- Assurance Fabric and ClaimRegistry (D-131, D-148, D-150)
- Market World Foundry (D-141, D-144)
- System Proving Ground (D-141)
- PolicyEvidenceProfile and G0–G9 scenario gates (D-152)
- Kaizen research history and debt tracking (D-137, D-145)

However, cross-policy evaluation lacked a unified, immutable, content-addressed, multi-population benchmark protocol. Without D-153, policy comparisons were vulnerable to:
1. Benchmark collapse: conflating benchmark capability scores with economic readiness or edge.
2. Evaluator artifacting: policies optimizing against a specific simulation or backtest harness quirk.
3. Common-mode failure: identical assumptions between policy generators and evaluators.
4. Metric compensability: allowing strong performance in benign regimes to mathematically conceal catastrophic failure in tail scenarios.
5. Inadmissible forward claims: extrapolating synthetic simulation success to future cashflow probability.

D-153 establishes the **Benchmark Fabric (BF)**: an evidence-bound diagnostic evaluation instrument that evaluates frozen policies across governed real, synthetic, and external reference populations without creating a parallel authority root.

---

## 2. Epistemic Hierarchy & Non-Collapse Invariants (Rules 57.1 – 57.8)

1. **Benchmark ≠ Assurance:** The Benchmark Fabric is a diagnostic and comparative instrument. It computes diagnostic indicators, failure topologies, and relative margins. It does NOT grant `SUPPORTED_EDGE` or deployment authority. Readiness and promotion authority remain exclusively with Assurance Fabric, G0–G9 gates, and ClaimRegistry.
2. **CapabilityScore ≠ Readiness:** The benchmark CapabilityScore (0.0 to 100.0) measures multidimensional behavioral competence. It does not measure readiness for live execution and cannot override any hard gate.
3. **CapabilityScore ≠ Future-Profit Probability:** CapabilityScore is not a probability distribution over future returns. Converting a benchmark score directly into a capital allocation multiplier without an audited `CapitalOutcomeProjection` is constitutionally prohibited.
4. **Hard Gates Cannot Be Averaged Away:** Each benchmark cell and each gate in `GateVector` (G0–G9, B0–B9) is non-compensable. A zero or failure in any required gate results in overall benchmark failure, regardless of a 99+ score in other domains.
5. **Synthetic Asymmetry:** Synthetic evaluations are strictly asymmetric:
   - Valid synthetic failure (`synthetic_fail_may_challenge`) may falsify robustness, execution safety, and stability claims within the scope of a certified World Passport.
   - Synthetic success (`synthetic_pass_confirms_no_edge`) confers zero economic edge and cannot prove future profitability.
6. **External Instrument Boundaries:** External evaluators (such as QuantConnect LEAN or external execution referees) are treated as instruments, not sovereign authorities. They must operate behind explicit typed adapters with recorded semantic divergence and parity attribution.
7. **Holdout and Pristine Data Protection:** Consumed holdout evidence cannot be unburned by renaming or wrapping in benchmark cases. Benchmark runs against burned diagnostic data must be explicitly tagged `BURNED_DIAGNOSTIC` with zero promotion weight.
8. **Research Debt and Multiple Testing Accounting:** Benchmark runs consume research trial budget. Every evaluation across parameter sweeps or challenger iterations increments Kaizen trial debt and inflates the family-wise hurdle rate.

---

## 3. Benchmark Ontology & Schemas

### 3.1 BenchmarkVersion
A deterministic, content-addressed version descriptor:
- `version_id`: Semantic version string (e.g. `v8.5.0-bf1`).
- `specification_hash`: SHA-256 digest of the complete benchmark specification, population definitions, and metric equations.
- `created_at_utc`: ISO-8601 timestamp.
- `population_hashes`: Map of population name to immutable manifest hash.
- `is_frozen`: Boolean indicating that the benchmark battery is locked against modification.

### 3.2 BenchmarkCase & BenchmarkCaseManifest
A single evaluation unit:
- `case_id`: Unique identifier (e.g. `BC-REAL-CHRON-01`, `BC-FOUNDRY-VOL-04`).
- `population_type`: `Real`, `SyntheticFoundry`, `ExternalReference`, or `StressDefeater`.
- `data_role`: `BURNED_DIAGNOSTIC`, `CROSS_VALIDATION`, `OUT_OF_SAMPLE_FROZEN`, `SYNTHETIC_GENERATED`, or `EXTERNAL_INDEPENDENT`.
- `archetype_or_family`: Specific regime allegory (A01–A12) or Foundry family (F01–F14).
- `environment_spec_hash`: Hash of the execution environment parameters (latency, slippage model, fee schedules).
- `input_manifest`: Dataset manifest including symbol, resolution, time range, bar count, and data content hash.

### 3.3 MetricObservation & The 10 Benchmark Domains
Observations recorded per case across 10 orthogonal capability domains:
1. `PredictiveEdge`: Directional accuracy, after-cost expectancy, information ratio (real populations only).
2. `ExecutionEfficiency`: Effective slippage drag, maker fill ratio, spread capture efficiency.
3. `DrawdownResilience`: Max drawdown, ulcer index, time to recovery, tail loss variance.
4. `VolatilityAdaptation`: Performance under volatility spikes, leverage responsiveness.
5. `StructuralStability`: Stationarity of returns, parameter perturbation sensitivity.
6. `RegimeRobustness`: Worst-case scenario cell performance across all allegories/families.
7. `TailRiskConfinement`: Value-at-Risk containment, conditional drawdown at risk (CDaR).
8. `CostModelIntegrity`: Retention of gross gains after realistic and adversarial fee models.
9. `ExternalRefereeParity`: Alignment and tracking error vs external execution baselines (LEAN / referee).
10. `DefeaterProximity`: Distance to nearest falsifying regime perturbation (reverse stress).

Each observation records raw value, normalized score [0, 100], confidence interval, and verification status.

### 3.4 CapabilityScore Mathematics
The benchmark score is computed as:
$$\text{Score} = \left( \sum_{i=1}^{10} w_i \cdot \text{DomainScore}_i \right) \times \text{CoverageFactor} \times \prod_{j=1}^{m} \mathbf{1}_{\{\text{Gate}_j = \text{Pass}\}}$$
Where:
- $\sum w_i = 1.0$, domain weights are predefined and frozen in `BenchmarkVersion`.
- $\text{CoverageFactor} \in [0.0, 1.0]$ penalizes incomplete or skipped scenario cells.
- If any required gate in `GateVector` fails, the product is 0 and the final score is forced to 0 (hard failure).

---

## 4. Population Taxonomy & Adapters

1. **Burned Historical Diagnostic:** Development datasets (including the canonical 12-month quad) used for engineering pathology detection. Always marked `BURNED_DIAGNOSTIC`.
2. **Chronological Real Populations:** Walk-forward out-of-sample slices with strictly causal time bounds.
3. **Purged Combinatorial Cross-Validation (CPCV):** Non-overlapping purged test folds measuring distribution stability across multiple partitions.
4. **Market World Foundry Populations:** Synthetic worlds generated with verified World Passports (D-141, D-144). Evaluates extreme tails and metamorphic invariance.
5. **Reverse Stress Defeater Population:** Adversarial minimal perturbation environments designed to locate the policy's failure boundary.
6. **External Execution Referee:** Independent trade matching and PnL calculation via LEAN reference adapter or independent trade ledger.

---

## 5. CapitalOutcomeProjection & Probability Boundaries

`CapitalOutcomeProjection` represents a disciplined, evidence-bounded forward outcome view:
- `evidence_grade`: `DiagnosticOnly`, `SyntheticRobustnessOnly`, `ReplicationBacked`, or `EmpiricallyCertified`.
- Forward probability assertions are strictly forbidden if `evidence_grade` is `DiagnosticOnly` or `SyntheticRobustnessOnly`.
- If synthetic populations are involved, projected forward profit expectancy is clamped to `UNSUPPORTED_FORWARD_CLAIM`.
- Reinvestment/compounding models must account for liquidity floors, market capacity, and execution drag.

---

## 6. Kaizen Benchmark Integration & Trial Debt

1. **Benchmark Delta Ledger:** Kaizen records an append-only receipt of every benchmark run comparing Challenger vs Incumbent.
2. **Multiple Testing Adjustments:** Every failed or exploratory benchmark run increments the global trial counter ($N_{\text{trials}}$), strictly increasing the DSR/WRC statistical threshold required for subsequent succession claims.
3. **Bridge Studies:** When a `BenchmarkVersion` is updated or recalibrated, a formal bridge study must evaluate both Incumbent and previous baselines on both versions to ensure continuity of standards.
