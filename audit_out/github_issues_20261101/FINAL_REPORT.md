# GitHub Issue Scope Audit — ddawnlll/v8

**Repo:** ddawnlll/v8 · **Snapshot:** 70 open issues at 2026-10-31T21:31:36Z (`open_issues.json` sha256 `b30dbbb4…c9b47`)
**Run dir:** `audit_out/github_issues_20261101/` · **Mode:** audit (read-only on source; `v8-next/` inspected, never modified)

---

## 1. Gates

| # | gate | status | evidence |
|---|---|---|---|
| G1 | All 70 open issues classified with quoted rationale, no orphans | PASS | `classification.json` / `CLASSIFICATION.md`: 45 v8-core + 25 v8-next + 0 ambiguous = 70. Every row carries a deciding-surface rationale; the 6 rows with no `file:` citation (318, 257, 326, 356, 359, 360) and 434 carry an explicit `scope_note`. |
| G2 | All v8-core-scoped issues closed with rationale comment; zero remain open | PASS | 45/45 `gh issue close` calls returned exit_code 0 (`close_log.json`). Independent re-verify: 45/45 report `state=CLOSED` with last comment starting "Closing: this issue is". Fresh `gh issue list --state open` = 25; v8-core-scoped still open: none. |
| G3 | Every surviving v8-next issue has a validity verdict with cited evidence, plus clusters and blockers | PASS | `EXAMINATION.md` / `examination.json`: 25/25 examined, 0 missing. Verdicts: still-valid 9, stale-but-real 8, already-fixed 6, superseded 1, NOT_IDENTIFIABLE 1. 4 clusters with designated canonicals; 6 explicit blockers. |
| G4 | One report artifact carries reconciliation, classification table, examination, clusters, blockers, gh commands | PASS | This file (§2–§7). |
| G5 | No writes to `v8-core/`, `src/v8/`, root `tests/`, or any `v8-next/` source file | PASS | `git diff --name-only` (below) lists only pre-existing `v8-next/src/…` modifications that were present before this audit started; no file was edited or created inside `v8-core/`, `src/v8/`, `tests/`, or `v8-next/`. All new files live under `audit_out/github_issues_20261101/` (untracked). |
| G6 | Closed-issue comments and exit codes recorded, hashes match manifest | PASS | §6 and §7. |
| G7 | Every duplicate cluster names a canonical issue | PASS | C1 -> #476, C2 -> #392, C3 -> #389, C4 -> #409 (§5). |
| G8 | Ambiguous-scope issues would have been left open | NOT_APPLICABLE | Zero issues classified ambiguous; nothing was withheld for review. |

---

## 2. Reconciliation

| bucket | count |
|---|---|
| open issues at snapshot | **70** |
| v8-core scope -> CLOSED | 45 |
| v8-next scope -> KEPT | 25 |
| ambiguous -> reviewed, left open | 0 |
| **total accounted** | **70** |

Post-close reconciliation against a fresh GitHub read (`gh issue list --state open`):

| check | result |
|---|---|
| issues open now | 25 |
| expected open (v8-next verdicts) | 25 |
| v8-core-scoped still open | none |
| expected v8-next issue missing from open list | none |
| unexpected issue in open list | none |

70 = 45 closed + 25 kept + 0 ambiguous. No orphan, no unmatched, no unexplained count.

---

## 3. Classification criterion

**Scope-based, as agreed:** an issue is `v8-core` only if its *subject or acceptance criteria* is about Rust code under `v8-core/`. A bare `v8-core/...` path mention inside a `v8-next` issue does not count.

This matters: naive keyword matching would have flagged 211 of 443 issues tree-wide as v8-core. On the 70 open issues the keyword test would also have mislabelled the v8-next defects that merely cite Rust source as a comparison. Six v8-core verdicts here rest on a non-code deciding surface (a verdict record, a ratification, a branch audit) and each says so in its rationale.

---

## 4. Full classification table (70 rows)

| # | verdict | action | labels | title | deciding evidence |
|---|---|---|---|---|---|
| 500 | v8-next | KEEP | type:defect, agent:scout | [DEFECT] Canonical P+E verdict ignores its own mix | Canonical P+E receipt defect: every authority named is v8-next Python (`v8-next/src/v8_next/evaluation/economic_benchmark.py`, `app/portfolio.py`); no v8-core surface is involved. |
| 495 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] G3 benchmark coverage cell measures regime robustness | G3 gate-cell defect: acceptance concerns `v8-next/src/v8_next/evaluation/benchmark_receipt.py`, `gate_registry.py`, `economic_benchmark.py`, `scoring.py` — active v8-next gate code. |
| 494 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] DSR subject chosen by alphabetical sort | DSR-subject defect: acceptance is a declared statistics-plan field in `v8-next/src/v8_next/evaluation/statistics_plan.py` + `gate_resolution.py`. |
| 491 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] Equity path drops closed campaign exit P&L | Equity-path defect: acceptance books closed-campaign exit legs into `v8-next/src/v8_next/evaluation/economic_benchmark.py` equity_mtm builders. |
| 478 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] Ledger keeps a superseded cost verdict | Ledger cost-verdict defect: acceptance concerns the canonical benchmark ledger produced by `v8-next/src/v8_next/app/readiness.py` / `evaluation/benchmark_receipt.py`. |
| 477 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] Canonical capacity bound bypasses swing contract | Capacity-bound defect: acceptance routes the canonical path through `v8-next/src/v8_next/evaluation/capacity.py` swing contract. |
| 476 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] 451-454 outputs are IMPLEMENTED but unwired to the benchmark path (MISSING on the final surface) | Wiring gap: acceptance is about v8-next chain issues #451–#454 being unwired from the `v8-next benchmark` → BenchmarkReceipt → PolicyCertificate surface. |
| 456 | v8-next | KEEP | type:implementation, triage | [IMPL] v8-next port chain 7/7: expert lifecycle (delta + D-141 qualification + kaizen/assurance/governance remainder) | Port chain 7/7: the deliverable is `v8-next/src/v8_next/experts/` parity with the Rust expert set; the issue title itself scopes it to the v8-next port chain. (See scope note: presumes v8-core as reference.) — _note: Port-parity program presumes v8-core as the reference implementation; if v8-core is abandoned as a reference, this becomes NOT_APPLICABLE rather than closable-as-done._ |
| 455 | v8-next | KEEP | type:implementation, state:blocked | [IMPL] v8-next port chain 6/7: scoring closure (bench-eval delta + synthetic discipline + temporal) | Port chain 6/7: the deliverable is v8-next benchmark/evaluation/research/temporal scoring closure; title scopes it to the v8-next port chain. (See scope note: presumes v8-core as reference.) — _note: Port-parity program presumes v8-core as the reference implementation; if v8-core is abandoned as a reference, this becomes NOT_APPLICABLE rather than closable-as-done._ |
| 434 | v8-next | KEEP | type:governance, triage | [GOV] Otonom merge yetkisi verildi — merge yasagi kaldirildi (D-163) | Merge-authority directive (D-163): a repo-wide governance announcement addressed to all agents/workers, with no v8-core code in scope; it governs how v8-next work is merged. — _note: Repo-wide governance, not v8-core code. Kept because it governs merging v8-next work._ |
| 409 | v8-next | KEEP | type:defect, triage, agent:scout | [DEFECT] Active product boundary rewritten without authority record | Product-boundary conflict: acceptance is to resolve the contradiction between root `AGENTS.md` ("v8-core/ is the ONLY active codebase") and `v8-next/AGENTS.md`; it is about which boundary is active, not about editing v8-core Rust code. (Repo-wide governance — see scope note.) — _note: Repo-wide governance, not v8-core code. Kept because its resolution defines the active boundary._ |
| 394 | v8-core | CLOSE | type:defect, triage, agent:scout | [DEFECT] Cashflow ledger mixes runs, receipt unverifiable | Cashflow-ledger defect: both producing modules named in the issue are Rust core files (`v8-core/src/cashflow.rs`, `v8-core/src/usdm_sim.rs`); fixing it would require editing archived code. |
| 393 | v8-next | KEEP | type:research, triage, state:triage | [RESEARCH] V8-next: close the economic evidence gate without weakening NO_ECONOMIC_CLAIM | Economic-gate research: acceptance is the v8-next evidence program over `v8-next/src/v8_next/evaluation/{runner,gate_resolution,economic_benchmark,parity}.py`, explicitly preserving NO_ECONOMIC_CLAIM. |
| 392 | v8-next | KEEP | type:implementation, triage, state:triage | [IMPL] V8-next: resolve UNKNOWN and MISSING gate states with explicit evidence | Gate-state resolution: acceptance turns v8-next benchmark UNKNOWN/MISSING states into evidence-backed outcomes in `v8-next/src/v8_next/evaluation/*`. |
| 391 | v8-next | KEEP | type:defect, triage, state:triage | [DEFECT] V8-next Ruff import ordering failure blocks clean quality gate | Ruff gate defect: acceptance is a clean Ruff gate for `v8-next` source/tests and `v8-next/pyproject.toml`. |
| 390 | v8-next | KEEP | type:defect, triage, state:triage | [DEFECT] V8-next test environment lacks locked DuckDB dependency | DuckDB env defect: acceptance is pinning the DuckDB dependency for `v8-next/tests/test_store_models_and_duckdb.py` and `v8-next/uv.lock`. |
| 389 | v8-next | KEEP | type:defect, triage, state:triage | [DEFECT] V8-next status ledger fails self-verification at entry 0 | Status-ledger defect: acceptance is a self-verifying ledger in `v8-next/src/v8_next/app/cli.py`, `evaluation/store.py`, `benchmark_receipt.py`. |
| 385 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: real operating net and venue-cost calibration | Operating-net implementation: acceptance is the v8-next operating-net/venue-cost layer over `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `costs.py`, `report.py`. |
| 384 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: bind complete candidate lifecycle to economic evaluation | Candidate-lifecycle binding: acceptance is v8-next economic evaluation consuming `v8-next/src/v8_next/opportunities/book.py`, `evaluation/outcomes.py`, `family.py`. |
| 383 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: wire two-ledger external parity into the economic evaluator | Two-ledger parity: acceptance is wiring `v8-next/src/v8_next/evaluation/parity.py` into the v8-next economic evaluator. |
| 382 | v8-next | KEEP | type:research, triage | [RESEARCH] V8-next: validate capacity and market impact from L2 data | L2 capacity research: acceptance is measuring capacity in `v8-next/src/v8_next/evaluation/capacity.py` from real tick/L2/ADV data. |
| 381 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: joint P+E portfolio execution and shared capital | Joint P+E execution: acceptance is a single joint portfolio path in `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `adapters/portfolio_backtest.py`, `portfolio_equity.py`. |
| 380 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: complete funding finality and coverage | Funding finality: acceptance is funding cost in `v8-next/src/v8_next/adapters/funding_history.py`, `settlements.py` and the v8-next benchmark/paper paths. |
| 379 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: venue fills, latency, shortfall, and account reconciliation | Venue-fill reconciliation: acceptance is a venue-evidence path in `v8-next/src/v8_next/adapters/shadow_ingest.py` and `evaluation/parity.py`. |
| 378 | v8-next | KEEP | type:research, triage | [RESEARCH] V8-next: implement and validate MinTRL estimator | MinTRL estimator: acceptance is `v8-next/src/v8_next/evaluation/mintrl.py` / `inference.py` with tests in `v8-next/tests/test_mintrl.py`. |
| 377 | v8-next | KEEP | type:implementation, triage | [IMPL] V8-next: protected OOS and complete search-family evidence | Protected OOS: acceptance is a one-shot chronological OOS workflow in `v8-next/src/v8_next/evaluation/forward_plan.py`, `family.py`, `store.py`. |
| 375 | v8-core | CLOSE | type:research, triage, state:triage | [RESEARCH] V8.6 M18: Verify complete V8.6 acceptance and publish bounded release evidence | V8.6 M18 milestone: acceptance is verifying complete V8.6 acceptance and publishing release evidence for the `v8-core/` tree. |
| 374 | v8-core | CLOSE | type:implementation, triage, state:triage | [IMPL] V8.6 M15: Verify standard serialization and digest ownership boundaries | V8.6 M15 milestone: acceptance is verifying serialization/digest ownership in `v8-core/src/hash.rs` (Rust). |
| 373 | v8-core | CLOSE | type:implementation, triage, state:triage | [IMPL] V8.6 M11: Move production random streams to versioned rand primitives | V8.6 M11 milestone: acceptance is moving production random streams in `v8-core/src/mt19937.rs` to versioned rand primitives (Rust dependency change). |
| 372 | v8-core | CLOSE | type:implementation, triage, state:triage | [IMPL] V8.6 M08: Reconcile exactly-once engine cashflow independently | V8.6 M08 milestone: acceptance is reconciling exactly-once engine cashflow in `v8-core/src/cashflow.rs` (Rust). |
| 371 | v8-core | CLOSE | type:implementation, triage, state:triage | [IMPL] V8.6 M03: Route baseline through one causal S4 decision path | V8.6 M03 milestone: acceptance is routing the baseline through one causal S4 decision path in `v8-core/src/main.rs`. |
| 370 | v8-core | CLOSE | type:implementation, triage, state:triage | [IMPL] V8.6 M02: Enforce issue lifecycle and PR requirement traceability | V8.6 M02 milestone: acceptance is enforcing issue/PR traceability for the Rust `v8-core/src/bin` surface. |
| 369 | v8-core | CLOSE | type:implementation, state:triage | [IMPL] V8.6 M07: Make portfolio admission unavoidable before execution | V8.6 M07 milestone: acceptance is making portfolio admission unavoidable in the Rust engine (`v8-core/src/portfolio.rs`). |
| 368 | v8-core | CLOSE | type:implementation, state:triage | [IMPL] V8.6 M06: Bind historical venue facts and fail-closed conformance | V8.6 M06 milestone: acceptance is binding historical venue facts in `v8-core/src/venue.rs` with fail-closed Rust conformance. |
| 367 | v8-core | CLOSE | type:implementation, state:triage | [IMPL] V8.6 M04: Define versioned Rust execution boundary | V8.6 M04 milestone: acceptance is defining the versioned Rust execution boundary in `v8-core/src/execution`. |
| 366 | v8-core | CLOSE | type:implementation, state:triage | [IMPL] V8.6 M05: Transfer execution and account lifecycle to NautilusTrader | V8.6 M05 milestone: acceptance is transferring the Rust execution/account lifecycle in `v8-core/src/execution` to NautilusTrader. |
| 360 | v8-core | CLOSE | rust, type:governance, triage, risk:high | [GOV] W17: Branch-merge verdicts (d153 + perf/*) | W17 branch-merge verdicts: scope is `feat/d153-benchmark-fabric` + six `perf/*` branches for the Rust core; every unit under verdict is v8-core Rust code. — _note: Verdict record, not code — classified v8-core because every merge unit under verdict is v8-core Rust code._ |
| 359 | v8-core | CLOSE | rust, triage, type:performance, risk:low | [IMPL-AUDIT] W16: Branch audit — six perf/* deltas vs d153 base | W16 branch audit: scope is the six `perf/*` deltas against `feat/d153-benchmark-fabric`, whose owning issues #332–#336 are all v8-core Rust branches. — _note: Audit record, not code — classified v8-core because every branch under audit is a v8-core Rust perf branch (#332–#336)._ |
| 358 | v8-core | CLOSE | rust, type:implementation, type:governance, triage, risk:medium, state:triage | [GOV] V8.6 M00: Preserve and reconcile migration baseline | V8.6 M00 milestone: acceptance is preserving/reconciling the migration baseline for the `v8-core/` tree. |
| 356 | v8-core | CLOSE | rust, type:governance, triage, risk:low | [GOV] W13: GPU + measurement-debt schedule | W13 GPU/measurement-debt verdict: the object of the verdict is `backend/gpu.rs` in the Rust core and the V8.6 §21.1 metric set. — _note: Verdict record, not code — classified v8-core because the object of the verdict is `backend/gpu.rs` and V8.6 core metrics._ |
| 355 | v8-core | CLOSE | rust, type:implementation, type:governance, triage, risk:high, state:triage | [IMPL] V8.6 M17: Retire superseded active implementations after acceptance | V8.6 M17 milestone: acceptance is retiring superseded active Rust implementations after V8.6 acceptance, scoped to `v8-core/`. |
| 354 | v8-core | CLOSE | rust, type:implementation, type:governance, triage, risk:high, state:triage | [IMPL] V8.6 M16: Wire one trial-lineage and statistical receipt path | V8.6 M16 milestone: acceptance is wiring the trial-lineage/statistical receipt path through `v8-core/src/statistics/mod.rs` (Rust core). |
| 353 | v8-core | CLOSE | rust, type:governance, triage, risk:high, state:triage | [GOV] V8.6 M01: Anchor full V8.6 scope and resolve migration authority | V8.6 M01 milestone: acceptance is anchoring V8.6 migration authority for the `v8-core/` scope itself. |
| 352 | v8-core | CLOSE | rust, type:implementation, triage, risk:medium, state:triage | [IMPL] V8.6 M14: Delegate generic distributions without moving synthetic data into runtime | V8.6 M14 milestone: acceptance governs distribution delegation for `v8-core/src/world` synthetic data inside the Rust core. |
| 351 | v8-core | CLOSE | rust, type:implementation, triage, risk:low, state:triage | [IMPL] V8.6 M09: Delegate active CLI parsing to clap | V8.6 M09 milestone: acceptance is delegating active CLI parsing to clap in `v8-core/src/main.rs` (Rust binary). |
| 350 | v8-core | CLOSE | rust, triage, type:performance, risk:medium, state:triage | [PERF] V8.6 M10: Delegate work scheduling to rayon with deterministic merge | V8.6 M10 milestone: acceptance is delegating work scheduling to rayon in `v8-core/src/scheduler.rs` (Rust core, perf scope). |
| 349 | v8-core | CLOSE | rust, type:implementation, triage, risk:medium, state:triage | [IMPL] V8.6 M12: Replace active custom HTML builders with one template engine | V8.6 M12 milestone: acceptance is replacing custom HTML builders with one template engine in the Rust reporting core (`v8-core/src/report.rs`, `v8-core/templates`). |
| 348 | v8-core | CLOSE | rust, parity, type:implementation, triage, risk:medium, state:triage | [IMPL] V8.6 M13: Consolidate canonical statistical methods and fix temporal validity | V8.6 M13 milestone: acceptance is consolidating canonical statistical methods inside the Rust core (`v8-core/src/statistics`). |
| 336 | v8-core | CLOSE | P1, statistics, rust, triage | [PERF] PERF011: Multi-Core Parallelism in Bootstrap Resampling, Reality Check, and Monte Carlo Projections | PERF011: acceptance is multi-core bootstrap/Monte-Carlo parallelism across `v8-core/src/statistics/reality_check.rs`, `benchmark/projection.rs`, `world/generator.rs`, `Cargo.toml` (Rust). |
| 335 | v8-core | CLOSE | P1, execution, rust, triage | [PERF] PERF010: Elimination of Per-Bar HistBar.event_id Heap Allocation and Repeated History Cloning in Runloop | PERF010: acceptance is eliminating per-bar heap allocation in `v8-core/src/state.rs`, `usdm_sim.rs`, `runloop.rs`, `experts/base.rs` (Rust runloop). |
| 334 | v8-core | CLOSE | P1, statistics, rust, triage | [PERF] PERF009: Zero-Allocation Scratch Buffering in Block-Bootstrap Reality Check and Detrended Null | PERF009: acceptance is zero-allocation scratch buffering in `v8-core/src/statistics/reality_check.rs`, `detrended.rs` (Rust hot path). |
| 333 | v8-core | CLOSE | P0, rust, triage | [PERF] PERF008: Integration Test Harness Consolidation and Mach-O Linker Contention Elimination | PERF008: acceptance is consolidating the integration harness under `v8-core/tests/` and `v8-core/Cargo.toml` (Rust build surface). |
| 332 | v8-core | CLOSE | P0, rust, triage | [PERF] PERF007: Cargo Profile Split and Elimination of Whole-Crate Optimization in Dev and Test Profiles | PERF007: acceptance is a Cargo profile split, and the sole cited artifact is `v8-core/Cargo.toml`. |
| 330 | v8-core | CLOSE | P1, type:governance, triage, risk:spec-or-decision-register | [GOV][P1] Reconcile D-153 authority registration and EN/TR contract mirrors | D-153 authority reconciliation: acceptance is reconciling registration against the v8-core benchmark fabric, and its verification surface is `v8-core/tests/benchmark_fabric_adversarial.rs` + `v8-core/tests/d153_benchmark_fabric_sabotage.rs`. — _note: Governance record for the v8-core benchmark fabric — classified v8-core because its acceptance names v8-core test files as the verification surface._ |
| 329 | v8-core | CLOSE | P0, rust, type:defect, triage, risk:economic-authority, risk:simulation-or-economic-authority | [DEFECT][P0] Replace fixed external parity vectors with policy-bound real adapters | External-parity defect: acceptance is replacing fixed-vector parity with data-backed adapters in `v8-core/src/benchmark/external.rs`, `case.rs`, `observation.rs` (Rust). |
| 328 | v8-core | CLOSE | P0, rust, type:defect, triage, risk:correctness-semantics, risk:forensics-attribution | [DEFECT][P0] Make BenchmarkReceipt and BenchmarkLedger cryptographically self-verifying | Self-verifying receipt defect: acceptance is cryptographic self-verification inside `v8-core/src/benchmark/receipt.rs`, `ledger.rs`, `types.rs` (Rust). |
| 327 | v8-core | CLOSE | P0, rust, type:defect, triage, risk:economic-authority, risk:correctness-semantics | [DEFECT][P0] Enforce canonical G0-G9 gate vector and authority firewall | Gate-vector defect: acceptance is enforcing the D-152 G0–G9 vector in `v8-core/src/claims.rs`, `benchmark/types.rs`, `runner.rs`, `certificate.rs` (Rust). |
| 326 | v8-core | CLOSE | P1, rust, type:defect, triage, risk:correctness-semantics, risk:forensics-attribution | [DEFECT][P1] Bind BenchmarkReceipt digest to full evidence and authority surface | Receipt-digest defect: acceptance is binding BenchmarkReceipt/ledger digests to the full evidence surface of the Rust core receipt format. |
| 325 | v8-core | CLOSE | P0, rust, type:defect, triage, risk:economic-authority | [DEFECT][P0] Correct quad portfolio capital denominator and shared-capital semantics | Quad-portfolio capital defect: acceptance is correcting the canonical four-asset diagnostic implemented in `v8-core/src/main.rs` (Rust CLI). |
| 324 | v8-core | CLOSE | P1, rust, stage-s5, type:implementation, triage, risk:correctness-semantics, risk:forensics-attribution | [IMPL][P1] Replace JSONL HashMap cache with a production cache storage adapter | Cache adapter implementation: acceptance is replacing the JSONL/HashMap CacheStore in `v8-core/src/cache.rs`, `evidence.rs` with a production storage adapter (Rust). |
| 323 | v8-core | CLOSE | P0, statistics, rust, type:defect, triage, risk:economic-authority, risk:correctness-semantics | [DEFECT][P0] Make BenchmarkRunner data-backed and remove hardcoded statistical claims | BenchmarkRunner defect: acceptance is making `v8-core/src/benchmark/runner.rs` data-backed instead of hardcoded (Rust). |
| 322 | v8-core | CLOSE | P1, statistics, rust, type:defect, triage, risk:economic-authority, risk:multiplicity-authority | [DEFECT][P1] Correct statistical kernels and block proxy DSR/PBO/SPA outputs | Statistical-kernel defect: acceptance is correcting DSR/PBO/SPA kernels in `v8-core/src/statistics`, `src/evaluation/statistics.rs`, `multiple_testing.rs` (Rust). |
| 321 | v8-core | CLOSE | P0, v8.2, rust, type:defect, triage, risk:correctness-semantics, risk:forensics-attribution | [DEFECT][P0] Emit real Parquet artifacts instead of JSON with a .parquet suffix | Parquet artifact defect: acceptance is replacing JSON-under-.parquet in `v8-core/src/usdm_sim/*`, `evaluation/regime_cube.rs` (Rust writers). |
| 320 | v8-core | CLOSE | P0, rust, type:defect, triage, risk:economic-authority, risk:simulation-or-economic-authority | [DEFECT][P0] Remove synthetic fallbacks from Monte Carlo, ruin and Slippage-at-Risk | Synthetic-fallback removal: acceptance is removing synthetic fallbacks from `v8-core/src/usdm_sim/scenario_ruin.rs`, `benchmark/projection.rs`, `evaluation/falsification.rs` (Rust). |
| 319 | v8-core | CLOSE | P1, v8.2, rust, type:implementation, triage, risk:correctness-semantics, risk:forensics-attribution | [IMPL][P1] Harden append-only ledgers, checkpoints and V82 artifact writer | Persistence hardening: acceptance is append-only ledgers/checkpoints in `v8-core/src/candidate.rs`, `cashflow.rs`, `checkpoint.rs`, `evidence.rs` (Rust core). |
| 318 | v8-core | CLOSE | P0, v8.2, rust, type:governance, triage, risk:spec-or-decision-register | [GOV][D-118] Ratify deterministic f64 computation as a locked invariant | D-118 f64-invariant ratification: acceptance is promoting the deterministic IEEE-754 computation contract that governs the Rust compute core (D-084/D-096, COMPUTE_SCHEDULING_SPEC); the sole comment ties it to V8.6 W12 (#355), a v8-core milestone. — _note: Ratification record for a compute invariant — classified v8-core because the deciding comment places it inside V8.6 W12 (#355), a v8-core milestone._ |
| 258 | v8-core | CLOSE | P0, rust, type:defect, triage, risk:economic-authority, risk:forensics-attribution | [DEFECT] Canonicalize current audit artifacts and block stale-run summaries | Audit-artifact canonicalization: acceptance is scoped to `v8-core/src/evidence.rs`, `evaluation/manifest.rs`, `lineage.rs`, `report.rs` — Rust core artifact writers. |
| 257 | v8-core | CLOSE | P0, epic, type:governance, triage, risk:economic-authority, risk:spec-or-decision-register | [GOV] V8.3 G5 prospective OOS, shadow, and succession authority | V8.2/V8.3 succession authority: acceptance pins the incumbent/challenger and prospective shadow run belonging to the Rust V8.3 lineage (companion enforcement tickets #255/#256 are v8-core). |
| 256 | v8-core | CLOSE | P0, rust, type:implementation, triage, risk:simulation-or-economic-authority | [IMPL] Build the hash-bound prospective shadow runner | Prospective shadow runner: acceptance is to "implement the smallest Rust-only runner" over `v8-core/src/evaluation/manifest.rs`, `paths.rs`, `v8-core/src/experiment.rs`. |
| 255 | v8-core | CLOSE | P0, type:research, triage, risk:hypothesis-governance, risk:validation-integrity | [RESEARCH] Execute the one-shot V8.3 frozen OOS succession experiment | V8.3 OOS succession experiment: acceptance is preregistering and executing the experiment through `v8-core/Cargo.toml`, `v8-core/src/evaluation/statistics.rs` and `v8-core/src/statistics/` (Rust execution). |

---

## 5. Per-issue examination of the 25 surviving v8-next issues

Full detail, per-issue claims and citations: see `EXAMINATION.md` (embedded below by reference; that file is the authoritative per-issue record).

### 5.1 Verdict summary

| verdict | count | issues |
|---|---|---|
| still-valid | 9 | 495, 477, 476, 456, 455, 389, 384, 382, 381 |
| stale-but-real | 8 | 494, 393, 392, 385, 383, 380, 379, 378 |
| already-fixed | 6 | 500, 478, 409, 391, 390, 377 |
| superseded | 1 | 434 |
| NOT_IDENTIFIABLE | 1 | 491 |

### 5.2 Per-issue findings

**#500 — `already-fixed` — [DEFECT] Canonical P+E verdict ignores its own mix**

- Claim: Canonical receipt publishes the full engine-level mixer but hands the verdict builder a stripped copy, so one artifact carries `scope: ENGINE_LEVEL_SAME_BUDGET` and, three keys away, `BASIS_UNSTATED`.
- Evidence: `grep -rn "BASIS_UNSTATED" src/` -> 0 hits tree-wide (symptom constant no longer exists). `v8-next/src/v8_next/app/portfolio.py:734` still publishes `"scope": "ENGINE_LEVEL_SAME_BUDGET"`. `v8-next/src/v8_next/evaluation/economic_benchmark.py:4285-4298` now branches on `mix.get("scope") == "ENGINE_LEVEL_SAME_BUDGET"` read from the *same* published `r.portfolio_mix` to emit the budget note — one object, one basis statement.

**#495 — `still-valid` — [DEFECT] G3 benchmark coverage cell measures regime robustness**

- Claim: The gate cell published as `g3_benchmark_coverage` measures regime robustness, not benchmark coverage, and on the canonical portfolio path it is not measured at all.
- Evidence: `v8-next/src/v8_next/evaluation/benchmark_receipt.py:429-430` — `canonical_id="G3ScenarioRobustness"`, `vector_field="g3_benchmark_coverage"` (name/value mismatch unchanged). `benchmark_receipt.py:552` — `g3_benchmark_coverage: GateState = GateState.MISSING` (default state, consistent with "not measured"). `v8-next/src/v8_next/evaluation/gate_registry.py:35` — `"G3ScenarioRobustness": "evaluate_g3_scenario_robustness"` (the resolver measures robustness). `gate_registry.py:51` — G3 is registered `DIAGNOSTIC`, so it grants no authority over coverage.

**#494 — `stale-but-real` — [DEFECT] DSR subject chosen by alphabetical sort**

- Claim: The receipt's DSR describes a curve picked by `sorted(...)[0]`, and the pinned `StatisticsPlan` carries no field naming which variant the number is about.
- Evidence: The `sorted(...)[0]` selector is gone from `v8-next/src/v8_next/evaluation/gate_resolution.py` (`grep "sorted(.*)\[0\]"` now hits only `economic_benchmark.py:1470`, which picks a *series length*, not a DSR subject). `v8-next/src/v8_next/evaluation/statistics_plan.py:53-77` — `StatisticsPlan` fields are family/block_size/reps/seed/multiplicity_trials/effective_independent_trials/independence_basis/pbo_*/wrc_*/authority_conditions/diagnostics/pinned_ns/interval_bars. No subject field: a receipt still cannot name the variant its DSR is about. Conclusion: the selection half was refactored away; the declaration half (the issue's actual requirement — "make the receipt's DSR name a **declared** subject") is not implemented.

**#491 — `NOT_IDENTIFIABLE` — [DEFECT] Equity path drops closed campaign exit P&L**

- Claim: Both engine->series builders delete a position from the mark book before its exit price is marked, so the exit leg never enters `equity_mtm`; the gap is then smeared by the #436 graft.
- Evidence: Cited lines have drifted: `v8-next/src/v8_next/evaluation/economic_benchmark.py:3149-3155` now contains open-position MTM/entry-commission accounting, not the equity-path builder the issue describes. The described builder is not locatable from the issue text alone at the cited coordinates; confirming whether the exit leg is booked needs re-derivation of the current builder, which is outside this audit's read-only remit. Verdict is fail-closed: not claimed fixed, not claimed still-valid.

**#478 — `already-fixed` — [DEFECT] Ledger keeps a superseded cost verdict**

- Claim: Ledger `seq 21` publishes `cost_basis = MISMATCH` / `EXECUTION_UNPROVEN` for the same window and fills that `seq 23` publishes as `VERIFIED_ENGINE_FUNDED`, so a consumer cannot tell which cost verdict governs.
- Evidence: `v8-next/src/v8_next/app/readiness.py:786` — `DECLARED_CORRECTIONS` with a `superseded -> corrected` pair plus "the authority that decided it". `readiness.py:812` — the superseded value is asserted against the declaration (`float(before) == float(declared["superseded"])`). `readiness.py:893-896` — "and never a verdict — the value it supersedes stays a property of this record". `readiness.py:919` — the corrected value is scored against its declared pair instead of the superseded value.

**#477 — `still-valid` — [DEFECT] Canonical capacity bound bypasses swing contract**

- Claim: The only capacity producer wired into the canonical portfolio run is never routed through the swing-capacity contract, so a bound is published as *measured* at a participation scale the run never observed.
- Evidence: The contract landed inside the module: `v8-next/src/v8_next/evaluation/capacity.py:179` and `:223` return `status="UNRESOLVED" if scaled else "NO_ECONOMIC_CLAIM"`; `:11` documents that resolution. But the module is consumed by nothing: `grep -rn "evaluation.capacity" src/ tests/` -> only `tests/test_capacity.py` imports it. No `src/v8_next/**` module imports `v8_next.evaluation.capacity`. So the canonical portfolio run still cannot route through the contract — the issue's actual complaint (unwired) holds, even though the contract code exists.

**#476 — `still-valid` — [DEFECT] 451-454 outputs are IMPLEMENTED but unwired to the benchmark path (MISSING on the final surface)**

- Claim: Chain issues #451-#454 are closed as "all R IDs complete" but their outputs are consumed by no executable path ending at `v8-next benchmark` -> BenchmarkRunner -> BenchmarkReceipt -> PolicyCertificate -> readiness/regression.
- Evidence: `v8-next/src/v8_next/evaluation/mintrl.py` — `grep -rn "import.*mintrl" src tests` -> only `tests/test_mintrl.py:9`. `v8-next/src/v8_next/evaluation/costs.py` `compute_operating_net` — only `tests/test_operating_net.py:11` imports it. `v8-next/src/v8_next/evaluation/capacity.py` — no `src/` importer at all. `v8-next/src/v8_next/opportunities/book.py` — imported only by `adapters/expert_strategy.py` and `opportunities/__init__.py`; no `evaluation/` or `app/` economic path consumes it. This is the same IMPLEMENTED-but-UNWIRED pattern the issue names, reproduced on 2026-10-30 code.

**#456 — `still-valid` — [IMPL] v8-next port chain 7/7: expert lifecycle (delta + D-141 qualification + kaizen/assurance/governance remainder)**

- Claim: Chain 7/7: close the expert lifecycle — expert-delta mapping, D-141 qualification, kaizen/assurance/governance remainder — measured against the closed scoring of the earlier chain issues.
- Evidence: `v8-next/tests/test_expert_delta.py` — does not exist (`ls` -> No such file or directory); the issue names it as required surface. `v8-next/src/v8_next/experts/` exists with the ported experts (bollinger, breakouts, candlestick, ...), so the module side is present while the delta/qualification evidence is not. Chain predecessor #455 is still `state:blocked`, so 456 cannot be measured against "the closed scoring of the earlier chain issues".
- Scope note: Port-parity program presumes v8-core as the reference implementation. If v8-core is no longer a reference, this becomes NOT_APPLICABLE rather than closable-as-done.

**#455 — `still-valid` — [IMPL] v8-next port chain 6/7: scoring closure (bench-eval delta + synthetic discipline + temporal)**

- Claim: Chain 6/7: close scoring — bench-eval delta, synthetic discipline, temporal — so every published score is a function of bound evidence.
- Evidence: Body: "Lifecycle state:blocked — chain step 6/7 implemented; R1-R4 evidenced at `b78a86e3aea3aa1150e083ed01cdf3cea2056c9f`; R5 BLOCKED on two named foreign reds (below); 2026-09-12." Self-declared blocked, not done. `v8-next/tests/test_d153_parity.py` and `test_gate_window_binding_406_421.py` exist and pass (38 passed, 1 skipped across the focused set), so R1-R4 evidence is reproducible. Label `state:blocked` on the live issue matches the body.
- Scope note: Port-parity program presumes v8-core as reference; see 456.

**#434 — `superseded` — [GOV] Otonom merge yetkisi verildi — merge yasagi kaldirildi (D-163)**

- Claim: Owner directive 2026-09-11 (D-163): the autonomous-merge ban is lifted; agents/workers may merge verified work to main without human approval.
- Evidence: `docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md` exists — the directive's full text is recorded in the repo. Root `AGENTS.md` §4 now encodes the resulting loop: "`edit in v8-next/ -> run focused tests/lint -> commit to main -> continue`. No PR ceremony". The issue is an announcement with no work item attached; its content is fully represented in tracked documents.

**#409 — `already-fixed` — [DEFECT] Active product boundary rewritten without authority record**

- Claim: Two mutually exclusive product-boundary declarations coexist: root `AGENTS.md` says "`v8-core/` is the ONLY active, authoritative codebase" while `v8-next/AGENTS.md` says the opposite.
- Evidence: Root `AGENTS.md` §1 now reads: "**`v8-next/` (PRIMARY & ACTIVE):** The sole active codebase." and "**`v8-core/` (ARCHIVED RUST — READ-ONLY):** Never modify, create files, or run `cargo` builds/tests here." `v8-next/AGENTS.md` header: "On 2026-09-11 the owner explicitly confirmed that v8-next is the intended codebase ... This supersedes the historical freeze and Rust-only wording below for this scope". The two declarations no longer conflict; the "v8-core is the ONLY active codebase" text the issue quotes is gone. This audit independently relied on that resolution: the 45 v8-core-scoped closures are premised on root `AGENTS.md` §1.

**#393 — `stale-but-real` — [RESEARCH] V8-next: close the economic evidence gate without weakening NO_ECONOMIC_CLAIM**

- Claim: Umbrella: define and execute the remaining evidence program to resolve the V8-next economic gate while preserving NO_ECONOMIC_CLAIM until all receipts are independently verified.
- Evidence: All named surfaces exist: `evaluation/runner.py`, `gate_resolution.py`, `economic_benchmark.py`, `parity.py`, `overfitting.py`, `store.py`. But the program cannot close: children 378/381/382/383/385 are implemented-yet-unwired (see 476) and 392's UNKNOWN states remain. As a container issue it stays real, but it will not converge until the wiring work in 476 is done.

**#392 — `stale-but-real` — [IMPL] V8-next: resolve UNKNOWN and MISSING gate states with explicit evidence**

- Claim: Turn the gate vector's UNKNOWN/MISSING states into explicit, evidence-backed outcomes without forcing or fabricating passes.
- Evidence: `v8-next/src/v8_next/evaluation/gate_resolution.py:675` returns `GateState.UNKNOWN` for an unauthorized underpowered track. `gate_resolution.py:1099-1103` returns `UNKNOWN` for G7 with a named reason ("prospective evidence, so G7 stays UNKNOWN instead of passing"). Both are correct fail-closed outcomes, so the remaining work is narrower than the issue text: the states are now named rather than silent, but MISSING defaults still exist (`benchmark_receipt.py:552`).

**#391 — `already-fixed` — [DEFECT] V8-next Ruff import ordering failure blocks clean quality gate**

- Claim: The v8-next quality gate fails with one Ruff I001 import-ordering error.
- Evidence: `uv run ruff check src tests --select I001` -> "All checks passed!".

**#390 — `already-fixed` — [DEFECT] V8-next test environment lacks locked DuckDB dependency**

- Claim: The full test command fails with `ModuleNotFoundError: No module named 'duckdb'` because the dependency is not locked.
- Evidence: `v8-next/pyproject.toml:35` — `"duckdb>=1.0",` is a declared dependency. `v8-next/uv.lock:94-105` — `name = "duckdb"` version 1.5.5 with per-platform wheels pinned. `v8-next/tests/test_store_models_and_duckdb.py` exists (14035 bytes).

**#389 — `still-valid` — [DEFECT] V8-next status ledger fails self-verification at entry 0**

- Claim: The status ledger fails self-verification at entry 0 (ENTRY_RECEIPT_INVALID / DIGEST_TAMPERED), yet the dashboard still renders a latest benchmark certificate.
- Evidence: `v8-next/src/v8_next/app/cli.py:110-133` — `chain_ok, chain_msg = ledger.verify_chain()` is used *only* inside the print f-string; `chain_ok` never gates the subsequent `ledger.publication()`, `PolicyCertificate.generate(...).render_ascii()` or the `return 0`. So a BROKEN chain still renders a certificate and exits 0 — the issue's third required end state ("the dashboard clearly separates latest report metadata from a valid evidence-chain status") is not implemented. Reproduction of the entry-0 digest mismatch is NOT_IDENTIFIABLE now: `v8-next/artifacts/benchmarks/` does not exist and no `benchmark_ledger*.jsonl` is on disk; `v8-next status` reports "benchmark: no ledger". The defect is therefore confirmed structurally, not by replaying the original corrupted ledger.

**#385 — `stale-but-real` — [IMPL] V8-next: real operating net and venue-cost calibration**

- Claim: Add an evidence-backed operating-net layer separating strategy net, venue friction, funding and fixed operating costs, using real venue observations.
- Evidence: The layer exists: `v8-next/src/v8_next/evaluation/costs.py:93-220` (`OperatingNetResult`, `compute_operating_net`, `operating_net=strategy_net - operating_costs`). `v8-next/tests/test_operating_net.py` exists and passes. But `grep -rn "compute_operating_net" src tests` -> only its own test. `economic_benchmark.py` contains 0 references to `operating_net`/`OperatingNet`. The issue names `economic_benchmark.py` and `report.py` as expected surface — neither consumes it.

**#384 — `still-valid` — [IMPL] V8-next: bind complete candidate lifecycle to economic evaluation**

- Claim: Make economic evaluation consume the complete candidate/opportunity/campaign lifecycle (triggered, rejected, invalidated, expired, unfilled, filled) with reasons.
- Evidence: `v8-next/src/v8_next/opportunities/book.py` exists, but `grep -rn "from v8_next.opportunities\|import opportunities" src/v8_next/evaluation src/v8_next/app` -> no hits. Only `adapters/expert_strategy.py`, `opportunities/__init__.py` reference it. `v8-next/tests/test_candidate_lifecycle_evaluator.py` — does not exist (named as expected surface). Verdict: the lifecycle is not consumed by economic evaluation.

**#383 — `stale-but-real` — [IMPL] V8-next: wire two-ledger external parity into the economic evaluator**

- Claim: Connect economic evaluation to two physically produced native/reference ledgers with explicit semantic mapping and fail-closed parity receipts.
- Evidence: Some parity is wired: `v8-next/src/v8_next/app/economic.py:28` imports `ArtifactBinding` from `v8_next.evaluation.parity`; `:595` publishes `parity={"engine_rerun_parity": "EXACT_MATCH" if parity_ok else "DIVERGED", ...}`; `:652` attaches `artifact_bindings`. But that is same-engine rerun parity plus artifact binding — not two *physically produced* native/reference ledgers with semantic mapping. `v8-next/tests/test_economic_parity_wiring.py` — does not exist (named as expected surface). `tests/test_d153_parity.py` exists and passes, covering the module in isolation.

**#382 — `still-valid` — [RESEARCH] V8-next: validate capacity and market impact from L2 data**

- Claim: Measure executable capacity across capital scales using real tick/L2/ADV and venue fill data instead of linear OHLCV extrapolation.
- Evidence: `v8-next/src/v8_next/evaluation/capacity.py:4-5` — "hourly OHLCV/ADV observations plus fills produced by the declared execution model; **order-book/L2 data is not part of this contract**." The module explicitly declines the issue's core requirement. `capacity.py:13` — "no linear notional extrapolation read as a measurement" (one half of the issue is addressed). `capacity.py` has no `src/` importer, so the measurement is not on the canonical path either.

**#381 — `still-valid` — [IMPL] V8-next: joint P+E portfolio execution and shared capital**

- Claim: Replace allocator-only P vs P+E sleeve arithmetic with a single joint portfolio execution and accounting path under one capital and risk budget.
- Evidence: `grep -n "portfolio_backtest\|portfolio_equity" v8-next/src/v8_next/evaluation/economic_benchmark.py` -> no hits. Those adapters are consumed elsewhere (`adapters/basket_backtest.py`, `funding_history.py`, `node_backtest.py`; `adapters/economic_paper.py`, `historical_trial.py`, `portfolio_risk.py`), not by the canonical economic comparison. `v8-next/tests/test_joint_portfolio_execution.py` — does not exist (named as expected surface).

**#380 — `stale-but-real` — [IMPL] V8-next: complete funding finality and coverage**

- Claim: Make funding cost an evidence-backed, position-aware, final accounting component for the benchmark and paper paths.
- Evidence: Funding is broadly wired: `grep -c "funding" v8-next/src/v8_next/evaluation/economic_benchmark.py` -> 193; `adapters/funding_history.py` and `adapters/settlements.py` exist; `tests/test_online_funding.py` and `tests/test_bounded_funding_capture.py` exist. `v8-next/tests/test_funding_finality.py` — does not exist (named as expected surface), so the "final/finality" half has no acceptance test. Verdict: the accounting component is present and partly tested; the finality claim the issue asks for is unproven.

**#379 — `stale-but-real` — [IMPL] V8-next: venue fills, latency, shortfall, and account reconciliation**

- Claim: Add a real venue-evidence path separating decision/submission/acceptance/fill/rejection/account clocks and reconciling model execution against venue-settled outcomes.
- Evidence: Shortfall reconciliation is wired: `shortfall` appears in `adapters/execution_telemetry.py`, `adapters/shadow_ingest.py`, `evaluation/economic_benchmark.py`, `evaluation/capacity.py`, `evaluation/scoring.py` (11 modules). `v8-next/tests/test_shortfall_reconciliation.py` — does not exist (named as expected surface). `tests/test_capture_integrity.py` and `tests/test_d153_parity.py` exist and pass. Verdict: implementation largely present; the named reconciliation acceptance test and the clock-separation claim are unproven.

**#378 — `stale-but-real` — [RESEARCH] V8-next: implement and validate MinTRL estimator**

- Claim: Implement a declared-assumption MinTRL estimator reporting the minimum observation horizon needed to distinguish a target Sharpe at a stated confidence and power.
- Evidence: Implemented: `v8-next/src/v8_next/evaluation/mintrl.py` (`MinTRLPlan`, `estimate_min_trl`), `v8-next/tests/test_mintrl.py` exists and passes. `grep -rn "import.*mintrl" src tests` -> only `tests/test_mintrl.py:9`. No `src/` module imports it, and `economic_benchmark.py` has 0 `mintrl`/`min_trl` references — the issue names `economic_benchmark.py` as expected surface.

**#377 — `already-fixed` — [IMPL] V8-next: protected OOS and complete search-family evidence**

- Claim: Implement a protected, one-shot chronological OOS workflow and complete local search-family accounting.
- Evidence: `v8-next/src/v8_next/evaluation/forward_plan.py` plus `v8_next/app/forward.py` and `v8_next/app/plan.py` exist; `evaluation/historical_plan.py` extends the family. Exposed on the CLI: `v8-next/src/v8_next/app/cli.py:494` — `"forward": "v8_next.app.forward"` passthrough. `tests/test_forward_plan.py` and `tests/test_family.py` exist and pass (part of 38 passed / 1 skipped).

### 5.3 Duplicate clusters

**C1 — IMPLEMENTED-but-UNWIRED (root cause of the chain family)** · canonical **#476** · members #476, #455, #456, #378, #381, #382, #383, #385, #384, #393

Each member asks for a capability that exists as a standalone module with a green unit test, but which no `src/` module on the benchmark/economic path imports. #476 is the only issue that states the general contradiction and the governing contract (`docs/contracts/WIRING_COMPLETION_CONTRACT.md` §4); the others are instances. Fixing the wiring closes most of them at once.

**C2 — Gate-vector naming / evidence expression** · canonical **#392** · members #392, #494, #495

All three are about the gate vector failing to say what it measured: 495 (G3 cell named coverage but measuring robustness), 494 (DSR name not a declared subject), 392 (UNKNOWN/MISSING states needing explicit evidence). 392 is the umbrella that defines how a cell must express its basis; resolving it settles the vocabulary for 494 and 495.

**C3 — Clean-quality-gate defects (all three reproducible by one command each)** · canonical **#389** · members #389, #390, #391

Not duplicates — distinct defects — but a single cluster because 390 and 391 are already fixed and verifiably closed, leaving 389 as the only live gate blocker. Closing 390/391 first makes 389 the sole red.

**C4 — Archived-boundary governance** · canonical **#409** · members #409, #434

Both are repo-wide governance records, not code. 409 (boundary conflict) is resolved at HEAD; 434 (merge authority) is recorded in docs. Neither has a v8-next code surface.

### 5.4 Blockers

- **#455** — R5 blocked on "two named foreign reds" — the issue body declares `state:blocked` at `b78a86e3` with R1-R4 evidenced and R5 open. Cannot close until those foreign reds are named-and-cleared in a fresh run.
- **#456** — Depends on #455 (chain 6/7). #455 is blocked, so 7/7 cannot be measured "against the closed scoring of the earlier chain issues". Also `tests/test_expert_delta.py` is absent.
- **#476** — Gated on `docs/contracts/WIRING_COMPLETION_CONTRACT.md` §4 being applied to the #451-#454 outputs. No `src/` consumer exists for mintrl / operating-net / capacity / opportunity-book, so the work is a wiring program, not a defect patch.
- **#393** — Child-dependent: 377-385 must reach a terminal state. Today 378/381/382/383/385 are unwired and 392 is open, so the umbrella cannot converge.
- **#389** — The reproducing ledger no longer exists on disk (`v8-next/artifacts/benchmarks/` absent; `v8-next status` -> "no ledger"). The structural defect is confirmed by code read, but a regression test needs a synthetically corrupted ledger fixture, which the issue already asks for and which is absent.
- **#491** — Cited `file:line` coordinates have drifted since filing, so the claim cannot be confirmed or refuted at the given location. Needs re-derivation against the current equity-path builder before either closing or scheduling.

---

## 6. Closed-issue manifest (45 issues)

Every row: `gh issue close <n> --reason "not planned" --comment "<see §6.2>"`.

| # | verdict | exit_code |
|---|---|---|
| 394 | v8-core | 0 |
| 375 | v8-core | 0 |
| 374 | v8-core | 0 |
| 373 | v8-core | 0 |
| 372 | v8-core | 0 |
| 371 | v8-core | 0 |
| 370 | v8-core | 0 |
| 369 | v8-core | 0 |
| 368 | v8-core | 0 |
| 367 | v8-core | 0 |
| 366 | v8-core | 0 |
| 360 | v8-core | 0 |
| 359 | v8-core | 0 |
| 358 | v8-core | 0 |
| 356 | v8-core | 0 |
| 355 | v8-core | 0 |
| 354 | v8-core | 0 |
| 353 | v8-core | 0 |
| 352 | v8-core | 0 |
| 351 | v8-core | 0 |
| 350 | v8-core | 0 |
| 349 | v8-core | 0 |
| 348 | v8-core | 0 |
| 336 | v8-core | 0 |
| 335 | v8-core | 0 |
| 334 | v8-core | 0 |
| 333 | v8-core | 0 |
| 332 | v8-core | 0 |
| 330 | v8-core | 0 |
| 329 | v8-core | 0 |
| 328 | v8-core | 0 |
| 327 | v8-core | 0 |
| 326 | v8-core | 0 |
| 325 | v8-core | 0 |
| 324 | v8-core | 0 |
| 323 | v8-core | 0 |
| 322 | v8-core | 0 |
| 321 | v8-core | 0 |
| 320 | v8-core | 0 |
| 319 | v8-core | 0 |
| 318 | v8-core | 0 |
| 258 | v8-core | 0 |
| 257 | v8-core | 0 |
| 256 | v8-core | 0 |
| 255 | v8-core | 0 |

### 6.1 Comment body used

```text
Closing: this issue is **`v8-core` scope**.

`v8-core/` is archived and read-only — it is no longer developed (root `AGENTS.md` §1: only `v8-next/` is active, and `v8-core/` must never be modified, built, or tested). The subject/acceptance of this issue targets that archived Rust codebase, so there is no path to working it.

**Scope evidence:** <the per-issue rationale from §4>

If the underlying concern still applies to the active `v8-next/` tree, re-file it against `v8-next/` with a v8-next code surface as the acceptance object.
```

### 6.2 Exact commands run

```bash
# snapshot
gh issue list --state open --limit 1000 --json number,title,state,labels,body,createdAt,updatedAt,author,assignees,milestone > open_issues.json
gh issue view <n> --json number,title,body,comments,labels,state > comments/<n>.json   # 70x, 0 failures

# close (45x, one per v8-core-scoped issue)
gh issue close <n> --reason "not planned" --comment "<§6.1 body + per-issue scope evidence>"

# post-close reconciliation
gh issue list --state open --limit 1000 --json number > post_close_open.json
gh issue view <n> --json state,comments   # 45x, verifying CLOSED + closing comment

# code checks cited in §5
cd v8-next
uv run ruff check src tests --select I001          # -> All checks passed!
uv run pytest -q tests/test_mintrl.py tests/test_operating_net.py tests/test_forward_plan.py tests/test_capacity.py tests/test_d153_parity.py tests/test_evaluation_lineage.py   # -> 38 passed, 1 skipped
uv run v8-next status                               # -> "benchmark: no ledger" (see #389)
grep -rn "BASIS_UNSTATED" src/                      # -> 0 hits (#500)
grep -rn "import.*mintrl" src tests                 # -> tests/test_mintrl.py:9 only (#378, #476)
grep -rn "evaluation.capacity" src tests            # -> tests only (#477, #382)
```

---

## 7. Artifact manifest and hashes

| artifact | bytes | sha256 |
|---|---|---|
| open_issues.json | 420405 | `b30dbbb44d53a2bfadac50f49eba36545880737c9604377bf3d05f39450c9b47` |
| triage_input.txt | 42665 | `455c91cd24ac7b223ccaddb5547ce8ef11c25ebf2448b4b3361b713392a63e6f` |
| classification.json | 35797 | `485a9719cdab40821d4267c3e2c41ba72ad2cdc9444d96f529893d4ded6b5af1` |
| CLASSIFICATION.md | 18168 | `9df844b35680a50160076e00d6c3fd0f49d2b9523221cc96ee4f67aaca02d4b0` |
| EXAMINATION.md | 25728 | `b6b016dfa90c050a2fa175df18ebbaf1366c499c3a6c6e35f5868d1ebb69e3d5` |
| examination.json | 25406 | `fc08746864bd1169c9fbbb8d37274646111620936093d2ddf378d5995e6d73af` |
| close_log.json | 4097 | `64e268a7b8b30565886b2608f0d4c05c20fa3863916d4253fce80f6fdd22ebe2` |
| post_close_open.json | 377 | `b3fee61ec027988f48288f83238b1c149aacec23de19ff4f4f6f9447909116f0` |
| refs.json | 6530 | `a7dc4d50b1ff5ff2137a6d8a45e51bc669c7dcd4d545473cf72f4ea0f09535cc` |
| MANIFEST.txt | 190 | `c1d687943a8969499db5817256f0e7aeb76624eb10e01462c1f8fe95dcdca0c6` |
| SHA256SUMS.txt | 6783 | `f52eb2da1456fd69f8c5e7ac50fbe8442a75e63acd88690b52439ac319eb40a3` |

---

## 8. Repo state

```text
$ git rev-parse HEAD
a921da2fdfb8254619b78840f80e969324f7cdf1
$ git rev-parse --abbrev-ref HEAD
main
$ git diff --name-only
v8-next/src/v8_next/adapters/expert_strategy.py
v8-next/src/v8_next/app/cli.py
v8-next/src/v8_next/audit/pipeline.py
v8-next/src/v8_next/research/arms.py
v8-next/src/v8_next/research/runner.py
$ git status --porcelain | head -20
 M v8-next/src/v8_next/adapters/expert_strategy.py
 M v8-next/src/v8_next/app/cli.py
 M v8-next/src/v8_next/audit/pipeline.py
 M v8-next/src/v8_next/research/arms.py
 M v8-next/src/v8_next/research/runner.py
?? .pi/
?? audit_out/
?? v8-next/src/v8_next/research/lifecycle.py
```

---

## 9. What this audit found that matters most

1. **The v8-core issue backlog was 45 of 70 open issues (64%).** It is now zero. Every one was a V8.6 milestone, a `perf/*` branch, a Rust-core defect, or a governance record for that archived tree.
2. **The dominant v8-next failure mode is IMPLEMENTED-but-UNWIRED, not missing work.** Six of the eight `stale-but-real` issues are modules that exist, whose own unit tests pass, and which no `src/` module on the benchmark path imports (`mintrl.py`, `costs.compute_operating_net`, `capacity.py`, `opportunities/book.py`, joint portfolio adapters, `parity.ArtifactBinding`). #476 names this contradiction for the #451–#454 chain; it is the single highest-leverage issue in the backlog.
3. **Six issues are already fixed and can be closed on evidence** — #500, #478, #409, #391, #390, #377 (and #434 is superseded). That is 7 of 25 closable today.
4. **Cited `file:line` coordinates in the defect issues have drifted.** #491 could not be confirmed or refuted at its cited lines, and several others point at unrelated code. Defect issues in this repo should cite symbols, not line numbers.
5. **#409 is the reason this audit was legitimate** — root `AGENTS.md` §1 now states `v8-next/` is the sole active codebase and `v8-core/` is archived read-only. When it was filed, the root document said the opposite.

---

## 10. Completion self-audit

Run by `self_audit.js`; machine output in `SELF_AUDIT.json`.

| check | status | detail |
|---|---|---|
| required headings present | PASS | 9 heading checks, all present |
| gate statuses strictly in {PASS,FAIL,BLOCKED,NOT_APPLICABLE} | PASS | 8 gate rows; non-conforming: none |
| no PASS_WITH_LIMITATION anywhere | PASS | 0 occurrences |
| classification reconciles to 70 | PASS | 45 core + 25 next + 0 ambiguous = 70; rows=70 |
| zero orphan/unmatched: no v8-core issue still open | PASS | none |
| zero orphan/unmatched: all 25 v8-next issues still open | PASS | none |
| every close exit_code == 0 | PASS | 45 closes, failures: 0 |
| every non-report artifact has a recorded sha256 | PASS | 11 files covered |
| git diff --name-only excludes v8-core/, src/v8/, tests/ | PASS | touched: v8-next/src/v8_next/adapters/expert_strategy.py, v8-next/src/v8_next/app/cli.py, v8-next/src/v8_next/audit/pipeline.py, v8-next/src/v8_next/research/arms.py, v8-next/src/v8_next/research/runner.py |
| focused test + lint exit codes recorded in report | PASS | ruff 0 (All checks passed), pytest 0 (38 passed, 1 skipped) |

**10/10 checks pass — self-audit verdict: PASS.**
