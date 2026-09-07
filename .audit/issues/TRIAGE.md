# Issue Triage Ledger — V8.6 execution lane (worktree `v86-exec` @ `8e3112f6`)

Date: 2026-09-07. Auditor: agent. Scope: `.audit/issues/61–73.json` (13) + `docs/issues/*.md` (49).
Policy: AGENTS.md RUST ONLY (`src/v8/`, `tests/` frozen — Python fixes prohibited);
Constitution Rule 12 (`NO_ECONOMIC_CLAIM` without WRC/DSR/SPA + authority receipt);
Rule 44 (full-text spec anchor for any D-series/architectural change).

## A. Audit issues 61–73 — disposition

| # | Title | Disposition | Evidence / Note |
|---|-------|-------------|-----------------|
| 61 | Cost 5.7× measured edge (P0) | MEASURE-ONLY, no code fix autonomous | Measurement record, explicitly "düzeltme önermiyor". Rust venue schema already authoritative: `v8-core/src/venue.rs:111` (VIP0 0.02% maker / 0.05% taker). Feasibility direction (grow R unit) is strategy = human/Kaizen-gov decision → DEFER with note. |
| 62 | PENDING→TRIGGERED has no trigger predicate (P0) | DONE in Rust | D-057 entry-trigger gate: `v8-core/src/runloop.rs:1149`, `:1858`; runloop PHASE comments. Python `lab.py` untouched (frozen). |
| 63 | Stop = fixed ATR multiple, not structural (P0) | DONE in Rust (structural path exists) | `v8-core/src/usdm_sim.rs` structural stop (`struct_stop`, `structural_invalidation_price`, campaign `stop_price`); `v8-core/src/kaizen/chop_suppression.rs:42` `structural_stop`. Full per-expert `stop_price` mandate = registry/gov decision → residual DEFER. |
| 64 | RR 1:1 + expiry=8 hardcoded (P0) | PARTIAL in Rust; residual HUMAN | Breakeven/expiry machinery exists (`simulator.rs:54-55,92-93` breakeven fields; expiry handling). Per-expert structural `target_r` + `w_min` feasibility gate mandate = challenger-registry change (Constitution rule 12, new variant rule) → DEFER with note. |
| 65 | Most literature preconditions unimplemented (P0) | DOCUMENT-ONLY by design | Issue itself says "bu bir düzeltme değil" + condition-set change = new variant (challenger + frozen-OOS + registry). Per-expert literature-condition mapping table = human research task → DEFER with note. |
| 66 | prior_high/low unbounded prefix extreme (P1 bug) | DONE in Rust | Windowed extreme: `v8-core/src/state.rs:796` (bounded 32-bar windowed extreme, D-034/D-059); fail-closed pre-entry invalidation `runloop.rs:692,1003`. |
| 67 | trigger_ref computed, never consumed (P1 bug) | DONE in Rust | D-057 gate consumes declared entry trigger (`runloop.rs:1149,1858`); dead-field registry guard (`runloop.rs:1865,1914` `IDENTITY_ONLY_GEOMETRY_KEYS`, `:2128,:2194`). |
| 68 | ExposureBook adverse selection via alphabetical order (P1) | DONE in Rust | Declared rule ascending `sha1(expert_id)`: `runloop.rs:10-11,300-301,352-353`; regression probe `:1412,:1626-1628,:1655`. |
| 69 | EXCESS_COST_THRESHOLD 0.10 below realistic taker (P1) | PARTIAL in Rust; residual HUMAN | Cost-only feasibility gate exists (`kaizen/chop_suppression.rs:11` A1 gate); authoritative `FeeSchedule` in `venue.rs:111,129`. Changing default cost/threshold = economic-feasibility claim → needs authority receipt → DEFER with note. |
| 70 | risk_geometry invariants unenforced (P1 bug) | DONE in Rust | `validate_geometry` (`v8-core/src/simulator.rs:6,181,192-222`): `target_r>0`, `stop_r>0`, `expiry_bars>=1` integer, fail-closed. `bollinger_reversion` Setup-3 RR<1 justification residual → DEFER (registry decision). |
| 71 | Gap asymmetry (P1) | DONE in Rust | Symmetric at declared barrier: `simulator.rs:22-23`, `:278`; asymmetry discussion anchored `:1150`. Conservatism budget reporting residual = docs task (autonomous, queued W-docs). |
| 72 | synth.py unrealistic gaps (P1 bug) | DONE by architecture (Rust side) | Python `synth.py` frozen (cannot touch). Rust Foundry v2 governs synthetic use: 3 populations, passport, `Synthetic FAIL = falsification ∧ PASS ≠ economic claim` (D-150). Golden-hash mismatch is a Python-tree matter → NOTE, not this lane. |
| 73 | EPIC umbrella (P0) | TRACKING only | Refuted-hypothesis log + scope limits recorded in issue body. No code. Closed when 61–72 dispositions land + residual notes filed. |

Python-tree acceptance items (trigger contract in `lab.py`, `stop_price` in `simulator.step()`,
`validate_geometry` in `src/v8/simulator.py`, `synth.py` docstring, golden hash) are
NOT actionable in this lane: `src/v8/` + `tests/` are frozen per AGENTS.md §2 and
`tools/audit_python_boundary.py`. They are recorded here as explicitly out-of-scope,
not as skipped work.

## B. docs/issues (49) — preliminary triage index

Conventions: LANE=Rust-autonomous | HUMAN=registry/gov/economic-claim decision | RES=research-measure-only.
D-coverage = latest D-series that already carries the work (D-140…D-159 range).

| File | Lane | Note |
|------|------|------|
| ISSUE_164_CAPITAL_CONSTRAINED_USDM_SIMULATOR | DONE (D-140..D-144 USD-M engine) | Verify `usdm_sim.rs` + quad baseline receipts |
| ISSUE_AUD001_ORACLE_INDEPENDENCE_AND_NEGATIVE_CONTROLS | DONE (D-139 causal fortress, D-152 passports) | Verify negative-control tests exist |
| ISSUE_AUD002_POPULATION_LINEAGE_AND_RECONCILIATION | DONE (D-152 evidence profile, D-156) | Verify lineage DAG tests |
| ISSUE_AUD003_D116_INDEPENDENT_ECONOMIC_PARITY | HUMAN (D-116 parity unmapped OPEN_PIN, D-159 carried) | Defer with note |
| ISSUE_AUD004A_PIT_TEMPORAL_FAULT_INJECTION | DONE (D-139 kill-rate suite LEAK-001..012) | Verify suite green |
| ISSUE_AUD004B_SEARCH_LINEAGE_AND_MULTIPLICITY_LEDGER | PARTIAL→HUMAN (genuine DSR receipt OPEN_PIN, D-156) | Implement ledger if missing; estimator itself deferred |
| ISSUE_AUD004C_NULL_WORLD_FALSIFICATION_BATTERY | RES/LANE (D-150 Foundry falsification battery) | Verify tests |
| ISSUE_AUD005A_O4_REGRET_ATTRIBUTION | LANE (regret.rs) | Verify |
| ISSUE_AUD005B_O5_RECOVERABILITY_CHALLENGER | RES/HUMAN (challenger + frozen-OOS gate) | Defer promotion decision |
| ISSUE_AUD006A_VETO_COUNTERFACTUAL_ATTRIBUTION | LANE (judiciary/) | Verify |
| ISSUE_AUD006B_SCHEDULER_RENAME_SENSITIVITY | LANE (scheduler declared order, cf. #68) | Verify test |
| ISSUE_AUD007_TRUE_JOINT_4D_REGIME_CUBE | LANE (outcome cube) | Verify |
| ISSUE_AUD008_MAKER_FILL_PROBABILITY_AND_ADVERSE_SELECTION | HUMAN (maker-fill assumption prohibited w/o authority) | Defer with note |
| ISSUE_AUD009A_STATIC_CAPITAL_VIABILITY_ENVELOPE | LANE (portfolio feasibility) | Verify |
| ISSUE_AUD009B_SCENARIO_CAPITAL_RUIN_AND_SAR | PARTIAL→HUMAN (fail-closed w/o liquidity inputs, D-156) | Verify fail-closed; SaR inputs deferred |
| ISSUE_AUD010_EVIDENCE_AUTHORITY_AND_UNKNOWN_SURFACE | HUMAN (gov taxonomy) | Defer with note |
| ISSUE_GOV001_BRANCH_PROTECTION_ENFORCEMENT | HUMAN (repo settings, maintainer-only) | Defer with note; never autonomous |
| ISSUE_IMPL001_TYPE_SAFETY_ERROR_ARCHITECTURE_MODULARIZATION | LANE (error.rs, modularization) | Verify clippy + layout |
| ISSUE_IMPL002_RESUME_CHECKPOINTING_CI_RELEASE | LANE (checkpoint.rs) | Verify |
| ISSUE_KZ001_EXPERT_FORENSICS_AND_FAILURE_TAXONOMY | DONE (D-141 proving ground, D-144) | Verify |
| ISSUE_KZ002_HYPOTHESIS_AND_CHALLENGER_REGISTRY | DONE (D-141 registry, D-145 ledger) | Verify |
| ISSUE_KZ003_ROBUSTNESS_SURFACE_AND_PLATEAU_CLIFF_ANALYSIS | LANE | Verify |
| ISSUE_KZ004_PURGED_WFA_AND_ONESHOT_FROZEN_OOS_GATE | LANE/HUMAN (gate autonomous; promotion human) | Verify gate; defer promotions |
| ISSUE_KZ005_ADAPTIVE_SWEEP_AUTHORITY | HUMAN (sweep authority + e-BH gate) | Defer with note |
| ISSUE_KZ006_MEGA001 … | DONE (D-144 mega/lead-time) | Verify |
| ISSUE_KZ007_EXIT001 … | DONE (Structural24hTrail, D-140/142) | Verify |
| ISSUE_KZ008_CAMP001 … | DONE (campaign clustering) | Verify |
| ISSUE_KZ009_CAP001 … | LANE (quantization.rs) | Verify |
| ISSUE_KZ010_ALLOC001 … | LANE (allocator/liquidity floor) | Verify |
| ISSUE_KZ011_VERIFY001 … | HUMAN (acceptance proof vs 05-Feb overfit) | Defer verdict; verify harness only |
| ISSUE_KZ012_COST001 … | DONE/PARTIAL (FeeSchedule authoritative; excess-cost gate) | Verify; threshold change deferred (§A #69) |
| ISSUE_KZ013_SCALE001 … | HUMAN (pyramiding = sizing/strategy decision) | Defer with note |
| ISSUE_KZ014_PORT001 … | HUMAN (portfolio heat allocation policy) | Defer with note |
| ISSUE_KZ015_GOV001 … | HUMAN (gov guardrails) | Defer with note |
| ISSUE_KZ016_DATA001 … | HUMAN (OI/liquidation data sponsorship) | Defer with note |
| ISSUE_KZ018_CHOP001 … | DONE (chop_suppression.rs) | Verify |
| ISSUE_PERF001_ZERO_COPY_MEMMAP_STREAMING_BINARY_IPC | LANE | Verify |
| ISSUE_PERF002_ZERO_ALLOC_TYPED_RISK_GEOMETRY_REPLAY | LANE | Verify |
| ISSUE_PERF003_ZERO_ALLOC_STATE_FEATURE_RUNLOOP | LANE | Verify |
| ISSUE_PERF004_INCREMENTAL_DATASET_HASHING_CACHE_HOTPATH | LANE (cache.rs, D-156) | Verify |
| ISSUE_PERF005_DIRECT_SYMBOL_INDEXING_INNER_REPLAY_LOOPS | LANE | Verify |
| ISSUE_PERF006_ZERO_COPY_PREDICATE_EVAL_INDICATOR_PRECOMPUTE | LANE | Verify |
| ISSUE_SEC001_CRYPTO_UPGRADE_INPUT_SANITIZATION_TELEMETRY | LANE | Verify |
| ISSUE_V83_URGENT_AUDIT_ARTIFACT_CANONICALIZATION | DONE (D-156, D-159) | Verify |
| ISSUE_V83_URGENT_FROZEN_OOS_SUCCESSION_EXPERIMENT | LANE/HUMAN (experiment lane; succession verdict human) | Verify harness |
| ISSUE_V83_URGENT_G5_SUCCESSION_AUTHORITY | HUMAN (G5 authority, D-152 G5 NO_ECONOMIC_CLAIM) | Defer with note |
| ISSUE_V83_URGENT_PROSPECTIVE_SHADOW_RUNNER | LANE/HUMAN (runner lane; promotion human) | Verify runner |
| ISSUE_V85_RATIFICATION_CANDIDATE | HUMAN (D-147 non-binding; ratification = committee) | Defer with note |
| ISSUE_VALIDITY001_RESEARCH_FLAWS_REMEDIATION | HUMAN (D-159 carried OPEN_PINs) | Defer deltas with note |

## C. Execution queue (autonomous, in order)

1. W-verify: `cargo test` + `cargo clippy` green in worktree (baseline seal already at W0 `ccefdbc9`; re-verify after ledger commit since ledger is docs-only).
2. W-docs: residual autonomous docs tasks (#71 conservatism budget note, #65 mapping-table stub marking OPEN_QUESTIONs, #64/#69 feasibility-gate wording) + CHANGELOG entry.
3. W-per-issue verification: walk §B LANE rows, one `cargo test <suite>` per row, record receipts in `.audit/issues/verification.log`.
4. W-human-notes: single `HUMAN_DEFERRED.md` with one row per HUMAN item (decision needed + authority + blocker).
5. PR from worktree branch (no merge — maintainer-only), with R# traceability matrix, Rule-44 anchors, monograph rebuild via `tools/build_monograph.py` (EN+TR) if any docs/decision/contract file changed.

Monograph/site rule compliance: no hand-edit of `site/*.html` (builder only, D-159 §330 precedent);
EN+TR mirrors for any decision/contract change; `IMPLEMENTATION_LAYOUT.md` touched only if modules change
(none in this ledger step); `tools/audit_doc_path_refs.py` run before PR.
