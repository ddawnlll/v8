// Scope classification for the 70 open issues (scope-based criterion).
// v8-core  = subject/acceptance is about Rust code under v8-core/ (archived).
// v8-next  = subject/acceptance is about the active v8-next Python codebase.
// ambiguous= undeterminable from issue text -> NOT closed, listed for review.
const fs = require('fs');
const issues = require('./open_issues.json');
const byNum = new Map(issues.map(i => [i.number, i]));

// group definitions: verdict + rationale template + explicit membership
const V8CORE = {
  348: 'V8.6 M13 milestone: acceptance is consolidating canonical statistical methods inside the Rust core (`v8-core/src/statistics`).',
  349: 'V8.6 M12 milestone: acceptance is replacing custom HTML builders with one template engine in the Rust reporting core (`v8-core/src/report.rs`, `v8-core/templates`).',
  350: 'V8.6 M10 milestone: acceptance is delegating work scheduling to rayon in `v8-core/src/scheduler.rs` (Rust core, perf scope).',
  351: 'V8.6 M09 milestone: acceptance is delegating active CLI parsing to clap in `v8-core/src/main.rs` (Rust binary).',
  352: 'V8.6 M14 milestone: acceptance governs distribution delegation for `v8-core/src/world` synthetic data inside the Rust core.',
  353: 'V8.6 M01 milestone: acceptance is anchoring V8.6 migration authority for the `v8-core/` scope itself.',
  354: 'V8.6 M16 milestone: acceptance is wiring the trial-lineage/statistical receipt path through `v8-core/src/statistics/mod.rs` (Rust core).',
  355: 'V8.6 M17 milestone: acceptance is retiring superseded active Rust implementations after V8.6 acceptance, scoped to `v8-core/`.',
  356: 'W13 GPU/measurement-debt verdict: the object of the verdict is `backend/gpu.rs` in the Rust core and the V8.6 §21.1 metric set.',
  358: 'V8.6 M00 milestone: acceptance is preserving/reconciling the migration baseline for the `v8-core/` tree.',
  359: 'W16 branch audit: scope is the six `perf/*` deltas against `feat/d153-benchmark-fabric`, whose owning issues #332–#336 are all v8-core Rust branches.',
  360: 'W17 branch-merge verdicts: scope is `feat/d153-benchmark-fabric` + six `perf/*` branches for the Rust core; every unit under verdict is v8-core Rust code.',
  366: 'V8.6 M05 milestone: acceptance is transferring the Rust execution/account lifecycle in `v8-core/src/execution` to NautilusTrader.',
  367: 'V8.6 M04 milestone: acceptance is defining the versioned Rust execution boundary in `v8-core/src/execution`.',
  368: 'V8.6 M06 milestone: acceptance is binding historical venue facts in `v8-core/src/venue.rs` with fail-closed Rust conformance.',
  369: 'V8.6 M07 milestone: acceptance is making portfolio admission unavoidable in the Rust engine (`v8-core/src/portfolio.rs`).',
  370: 'V8.6 M02 milestone: acceptance is enforcing issue/PR traceability for the Rust `v8-core/src/bin` surface.',
  371: 'V8.6 M03 milestone: acceptance is routing the baseline through one causal S4 decision path in `v8-core/src/main.rs`.',
  372: 'V8.6 M08 milestone: acceptance is reconciling exactly-once engine cashflow in `v8-core/src/cashflow.rs` (Rust).',
  373: 'V8.6 M11 milestone: acceptance is moving production random streams in `v8-core/src/mt19937.rs` to versioned rand primitives (Rust dependency change).',
  374: 'V8.6 M15 milestone: acceptance is verifying serialization/digest ownership in `v8-core/src/hash.rs` (Rust).',
  375: 'V8.6 M18 milestone: acceptance is verifying complete V8.6 acceptance and publishing release evidence for the `v8-core/` tree.',
  318: 'D-118 f64-invariant ratification: acceptance is promoting the deterministic IEEE-754 computation contract that governs the Rust compute core (D-084/D-096, COMPUTE_SCHEDULING_SPEC); the sole comment ties it to V8.6 W12 (#355), a v8-core milestone.',
  330: 'D-153 authority reconciliation: acceptance is reconciling registration against the v8-core benchmark fabric, and its verification surface is `v8-core/tests/benchmark_fabric_adversarial.rs` + `v8-core/tests/d153_benchmark_fabric_sabotage.rs`.',
  394: 'Cashflow-ledger defect: both producing modules named in the issue are Rust core files (`v8-core/src/cashflow.rs`, `v8-core/src/usdm_sim.rs`); fixing it would require editing archived code.',
  255: 'V8.3 OOS succession experiment: acceptance is preregistering and executing the experiment through `v8-core/Cargo.toml`, `v8-core/src/evaluation/statistics.rs` and `v8-core/src/statistics/` (Rust execution).',
  256: 'Prospective shadow runner: acceptance is to "implement the smallest Rust-only runner" over `v8-core/src/evaluation/manifest.rs`, `paths.rs`, `v8-core/src/experiment.rs`.',
  257: 'V8.2/V8.3 succession authority: acceptance pins the incumbent/challenger and prospective shadow run belonging to the Rust V8.3 lineage (companion enforcement tickets #255/#256 are v8-core).',
  258: 'Audit-artifact canonicalization: acceptance is scoped to `v8-core/src/evidence.rs`, `evaluation/manifest.rs`, `lineage.rs`, `report.rs` — Rust core artifact writers.',
  319: 'Persistence hardening: acceptance is append-only ledgers/checkpoints in `v8-core/src/candidate.rs`, `cashflow.rs`, `checkpoint.rs`, `evidence.rs` (Rust core).',
  320: 'Synthetic-fallback removal: acceptance is removing synthetic fallbacks from `v8-core/src/usdm_sim/scenario_ruin.rs`, `benchmark/projection.rs`, `evaluation/falsification.rs` (Rust).',
  321: 'Parquet artifact defect: acceptance is replacing JSON-under-.parquet in `v8-core/src/usdm_sim/*`, `evaluation/regime_cube.rs` (Rust writers).',
  322: 'Statistical-kernel defect: acceptance is correcting DSR/PBO/SPA kernels in `v8-core/src/statistics`, `src/evaluation/statistics.rs`, `multiple_testing.rs` (Rust).',
  323: 'BenchmarkRunner defect: acceptance is making `v8-core/src/benchmark/runner.rs` data-backed instead of hardcoded (Rust).',
  324: 'Cache adapter implementation: acceptance is replacing the JSONL/HashMap CacheStore in `v8-core/src/cache.rs`, `evidence.rs` with a production storage adapter (Rust).',
  325: 'Quad-portfolio capital defect: acceptance is correcting the canonical four-asset diagnostic implemented in `v8-core/src/main.rs` (Rust CLI).',
  326: 'Receipt-digest defect: acceptance is binding BenchmarkReceipt/ledger digests to the full evidence surface of the Rust core receipt format.',
  327: 'Gate-vector defect: acceptance is enforcing the D-152 G0–G9 vector in `v8-core/src/claims.rs`, `benchmark/types.rs`, `runner.rs`, `certificate.rs` (Rust).',
  328: 'Self-verifying receipt defect: acceptance is cryptographic self-verification inside `v8-core/src/benchmark/receipt.rs`, `ledger.rs`, `types.rs` (Rust).',
  329: 'External-parity defect: acceptance is replacing fixed-vector parity with data-backed adapters in `v8-core/src/benchmark/external.rs`, `case.rs`, `observation.rs` (Rust).',
  332: 'PERF007: acceptance is a Cargo profile split, and the sole cited artifact is `v8-core/Cargo.toml`.',
  333: 'PERF008: acceptance is consolidating the integration harness under `v8-core/tests/` and `v8-core/Cargo.toml` (Rust build surface).',
  334: 'PERF009: acceptance is zero-allocation scratch buffering in `v8-core/src/statistics/reality_check.rs`, `detrended.rs` (Rust hot path).',
  335: 'PERF010: acceptance is eliminating per-bar heap allocation in `v8-core/src/state.rs`, `usdm_sim.rs`, `runloop.rs`, `experts/base.rs` (Rust runloop).',
  336: 'PERF011: acceptance is multi-core bootstrap/Monte-Carlo parallelism across `v8-core/src/statistics/reality_check.rs`, `benchmark/projection.rs`, `world/generator.rs`, `Cargo.toml` (Rust).',
};

const V8NEXT = {
  500: 'Canonical P+E receipt defect: every authority named is v8-next Python (`v8-next/src/v8_next/evaluation/economic_benchmark.py`, `app/portfolio.py`); no v8-core surface is involved.',
  495: 'G3 gate-cell defect: acceptance concerns `v8-next/src/v8_next/evaluation/benchmark_receipt.py`, `gate_registry.py`, `economic_benchmark.py`, `scoring.py` — active v8-next gate code.',
  494: 'DSR-subject defect: acceptance is a declared statistics-plan field in `v8-next/src/v8_next/evaluation/statistics_plan.py` + `gate_resolution.py`.',
  491: 'Equity-path defect: acceptance books closed-campaign exit legs into `v8-next/src/v8_next/evaluation/economic_benchmark.py` equity_mtm builders.',
  478: 'Ledger cost-verdict defect: acceptance concerns the canonical benchmark ledger produced by `v8-next/src/v8_next/app/readiness.py` / `evaluation/benchmark_receipt.py`.',
  477: 'Capacity-bound defect: acceptance routes the canonical path through `v8-next/src/v8_next/evaluation/capacity.py` swing contract.',
  476: 'Wiring gap: acceptance is about v8-next chain issues #451–#454 being unwired from the `v8-next benchmark` → BenchmarkReceipt → PolicyCertificate surface.',
  456: 'Port chain 7/7: the deliverable is `v8-next/src/v8_next/experts/` parity with the Rust expert set; the issue title itself scopes it to the v8-next port chain. (See scope note: presumes v8-core as reference.)',
  455: 'Port chain 6/7: the deliverable is v8-next benchmark/evaluation/research/temporal scoring closure; title scopes it to the v8-next port chain. (See scope note: presumes v8-core as reference.)',
  434: 'Merge-authority directive (D-163): a repo-wide governance announcement addressed to all agents/workers, with no v8-core code in scope; it governs how v8-next work is merged.',
  409: 'Product-boundary conflict: acceptance is to resolve the contradiction between root `AGENTS.md` ("v8-core/ is the ONLY active codebase") and `v8-next/AGENTS.md`; it is about which boundary is active, not about editing v8-core Rust code. (Repo-wide governance — see scope note.)',
  393: 'Economic-gate research: acceptance is the v8-next evidence program over `v8-next/src/v8_next/evaluation/{runner,gate_resolution,economic_benchmark,parity}.py`, explicitly preserving NO_ECONOMIC_CLAIM.',
  392: 'Gate-state resolution: acceptance turns v8-next benchmark UNKNOWN/MISSING states into evidence-backed outcomes in `v8-next/src/v8_next/evaluation/*`.',
  391: 'Ruff gate defect: acceptance is a clean Ruff gate for `v8-next` source/tests and `v8-next/pyproject.toml`.',
  390: 'DuckDB env defect: acceptance is pinning the DuckDB dependency for `v8-next/tests/test_store_models_and_duckdb.py` and `v8-next/uv.lock`.',
  389: 'Status-ledger defect: acceptance is a self-verifying ledger in `v8-next/src/v8_next/app/cli.py`, `evaluation/store.py`, `benchmark_receipt.py`.',
  385: 'Operating-net implementation: acceptance is the v8-next operating-net/venue-cost layer over `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `costs.py`, `report.py`.',
  384: 'Candidate-lifecycle binding: acceptance is v8-next economic evaluation consuming `v8-next/src/v8_next/opportunities/book.py`, `evaluation/outcomes.py`, `family.py`.',
  383: 'Two-ledger parity: acceptance is wiring `v8-next/src/v8_next/evaluation/parity.py` into the v8-next economic evaluator.',
  382: 'L2 capacity research: acceptance is measuring capacity in `v8-next/src/v8_next/evaluation/capacity.py` from real tick/L2/ADV data.',
  381: 'Joint P+E execution: acceptance is a single joint portfolio path in `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `adapters/portfolio_backtest.py`, `portfolio_equity.py`.',
  380: 'Funding finality: acceptance is funding cost in `v8-next/src/v8_next/adapters/funding_history.py`, `settlements.py` and the v8-next benchmark/paper paths.',
  379: 'Venue-fill reconciliation: acceptance is a venue-evidence path in `v8-next/src/v8_next/adapters/shadow_ingest.py` and `evaluation/parity.py`.',
  378: 'MinTRL estimator: acceptance is `v8-next/src/v8_next/evaluation/mintrl.py` / `inference.py` with tests in `v8-next/tests/test_mintrl.py`.',
  377: 'Protected OOS: acceptance is a one-shot chronological OOS workflow in `v8-next/src/v8_next/evaluation/forward_plan.py`, `family.py`, `store.py`.',
};

const SCOPE_NOTES = {
  456: 'Port-parity program presumes v8-core as the reference implementation; if v8-core is abandoned as a reference, this becomes NOT_APPLICABLE rather than closable-as-done.',
  455: 'Port-parity program presumes v8-core as the reference implementation; if v8-core is abandoned as a reference, this becomes NOT_APPLICABLE rather than closable-as-done.',
  409: 'Repo-wide governance, not v8-core code. Kept because its resolution defines the active boundary.',
  434: 'Repo-wide governance, not v8-core code. Kept because it governs merging v8-next work.',
  330: 'Governance record for the v8-core benchmark fabric — classified v8-core because its acceptance names v8-core test files as the verification surface.',
  318: 'Ratification record for a compute invariant — classified v8-core because the deciding comment places it inside V8.6 W12 (#355), a v8-core milestone.',
  356: 'Verdict record, not code — classified v8-core because the object of the verdict is `backend/gpu.rs` and V8.6 core metrics.',
  359: 'Audit record, not code — classified v8-core because every branch under audit is a v8-core Rust perf branch (#332–#336).',
  360: 'Verdict record, not code — classified v8-core because every merge unit under verdict is v8-core Rust code.',
};

const rows = [];
const nums = issues.map(i => i.number);
for (const n of nums) {
  const iss = byNum.get(n);
  const inCore = Object.prototype.hasOwnProperty.call(V8CORE, n);
  const inNext = Object.prototype.hasOwnProperty.call(V8NEXT, n);
  if (inCore === inNext) throw new Error('exactly one verdict required for #' + n);
  const verdict = inCore ? 'v8-core' : 'v8-next';
  const rationale = inCore ? V8CORE[n] : V8NEXT[n];
  rows.push({
    number: n,
    title: iss.title,
    labels: (iss.labels || []).map(l => l.name),
    verdict,
    rationale,
    scope_note: SCOPE_NOTES[n] || null,
    action: inCore ? 'CLOSE' : 'KEEP',
  });
}
rows.sort((a, b) => b.number - a.number);

const counts = rows.reduce((m, r) => (m[r.verdict] = (m[r.verdict] || 0) + 1, m), {});
const out = counts['v8-core'] + counts['v8-next'] + (counts.ambiguous || 0);
fs.writeFileSync('classification.json', JSON.stringify({ criterion: 'scope-based', counts, total: rows.length, reconciliation: out, rows }, null, 2));

const md = ['# Scope classification — 70 open issues', '',
  `criterion: subject/acceptance is about Rust code under \`v8-core/\` (path mentions alone do not count)`, '',
  `v8-core (CLOSE): ${counts['v8-core']} | v8-next (KEEP): ${counts['v8-next']} | ambiguous: ${counts.ambiguous || 0} | total: ${rows.length}`, '',
  '| # | verdict | action | title | rationale |', '|---|---|---|---|---|'];
for (const r of rows) md.push(`| ${r.number} | ${r.verdict} | ${r.action} | ${r.title.replace(/\|/g, '\\|')} | ${r.rationale.replace(/\|/g, '\\|')} |`);
fs.writeFileSync('CLASSIFICATION.md', md.join('\n') + '\n');
console.log(JSON.stringify(counts), 'total', rows.length, 'reconciles', out === 70);
