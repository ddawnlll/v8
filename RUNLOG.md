# V8 Autonomous Build — Runlog

Session artifact, not corpus. Filled by the build agent per `docs/AGENT_RUNBOOK.md`.
Every step gets an entry: status, evidence, fixes, commit. The operator reads
this file and `docs/STATUS_REPORT.md`.

## Format

```markdown
## Step N — <title> — <DONE | BLOCKED | SKIPPED>
- started: <UTC> finished: <UTC>
- files touched: <paths>
- evidence: <command> -> <output tail>
- fixes / deviations: <what broke and how it was fixed>
- commit: <short hash> `v8-step-N: ...`
- gate: pytest=<pass count> monograph=byte-identical?<yes/no> forbidden-scan=clean?
```

## Step 0 — Baseline — DONE
- started: 2026-08-01T02:34:00Z finished: 2026-08-01T02:35:40Z
- files touched: (none — verification only; RUNLOG.md filled)
- evidence: `.venv/bin/python -m pytest tests -q` -> `15 passed in 0.27s`;
  `.venv/bin/python tools/build_monograph.py --lang en --docs docs --out /tmp/v8_index_probe.html` ->
  `wrote /tmp/v8_index_probe.html: sections=30 papers=60 words=46331`;
  `shasum -a 256 /tmp/v8_index_probe.html site/index.html` ->
  `65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a  /tmp/v8_index_probe.html`
  `65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a  site/index.html`
  (byte-identical);
  `git log --oneline -1` -> `5962982 v8-step-0: initial commit — corpus + Phase 2 vertical slice (15 tests green, monograph reproducible)`;
  `git status --short` -> empty (clean tree)
- fixes / deviations: none. No DEVIATION; no extra commit created (baseline
  commit operator-taken; RUNLOG.md rides in the Step 1 commit per commit protocol).
- commit: 5962982 `v8-step-0: initial commit` (operator-taken baseline; RUNLOG.md
  baseline row committed with Step 1)
- gate: pytest=15 monograph=byte-identical?yes forbidden-scan=clean?yes (no new
  code yet) tree-clean?yes

## Step 1 — D-026: episode_key anchored to setup_anchor_event_id — DONE
- started: 2026-08-01T02:36:00Z finished: 2026-08-01T02:47:00Z
- files touched: src/v8/schema.py, src/v8/marketstate.py, src/v8/lifecycle.py,
  src/v8/experts/base.py, src/v8/experts/trend_pullback.py,
  src/v8/experts/failed_breakout.py, src/v8/lab.py, tests/test_vertical_slice.py,
  RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `18 passed in 0.22s`
  (baseline 15; +3 new tests: key stability across consecutive clocks, fresh
  setup new key, repeat logged SUPPRESSED_DUPLICATE);
  monograph probe -> `shasum 65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a`
  (byte-identical, `uniq -c` = `2`);
  forbidden-scan `grep -rniE 'router|scorer|rank(er|ing)?|\bRL\b'` -> hits only in
  pre-existing files (risk.py:13 comment, schema.py/simtruth docstrings); risk.py
  confirmed untouched via `git diff --name-only`.
- fixes / deviations: (1) latent bug exposed: `suppressed_duplicate` append in
  lab.py lacked `source`/`event_id`, crashing AppendOnlyLog dedup inbox
  (`KeyError: 'source'`); fixed by adding both keys, event_id unique per clock
  (`{cid}:suppressed:{as_of}`). Code fix, not a test change. (2) `_geometry_version`
  in lab.py hashes risk_geometry excluding data-dependent `atr_ref` so a stable
  setup keeps its key across clocks. (3) crafted test tape verified numerically
  against build_state EMA (run A bars 60-61 anchor SOLUSDT:61; run B bars 67-69
  anchor SOLUSDT:68) — bar indices in tests are the verified ones.
- commit: 4f34abe `v8-step-1: D-026 setup-anchored episode key (history group, setup_anchor_event_id, time-free dedup)`
- gate: pytest=18 monograph=byte-identical?yes forbidden-scan=clean?yes (new code
  only; pre-existing mentions in risk.py/simtruth) wall-clock=clean?yes

## Step 2 — Funding settlement in canonical simulator — DONE
- started: 2026-08-01T02:48:00Z finished: 2026-08-01T02:58:00Z
- files touched: src/v8/schema.py, src/v8/simulator.py, src/v8/lab.py,
  tests/test_vertical_slice.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `22 passed in 0.36s`
  (18 -> 22; +4 funding goldens); monograph probe byte-identical
  (65eef39f...); forbidden-scan CLEAN in changed files; wall-clock scan CLEAN
  (only pre-existing docstring mentions).
- fixes / deviations: (1) test-only fix — `startswith(sha1 of v4 tag)` was a
  bogus assertion (hash is of the full tuple); replaced with exact expected
  v4 hash `sha1(('canonical-sim-v4', 'FILL_AT_BAR_CLOSE', 0.07, 0.0, 8))` and
  `!= v3`. (2) Semantics pinned in code: open interval at the start boundary
  (hold starting exactly on a boundary not double-settled) and closed at the
  end (hold ending exactly on one settles exactly once — V7 terminal-boundary
  defect). (3) `bar_time` param on `step()`/`times` on `run()`: None = no
  funding, preserving byte-identity for time-less callers and for
  `funding_rate_r=0.0` (golden d).
- commit: 760e6cc `v8-step-2: funding settlement in canonical simulator (SETTLEMENT_BEFORE_ORDERS, boundary goldens, sim hash v4)`
- gate: pytest=22 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

## Step 3 — D-024 mechanical tradability mask — DONE
- started: 2026-08-01T03:00:00Z finished: 2026-08-01T03:02:55Z
- files touched: src/v8/schema.py, src/v8/risk.py, src/v8/lab.py,
  tests/test_vertical_slice.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `26 passed in 0.42s`
  (22 -> 26; +4 mask tests: spread-tail veto, funding-window veto,
  DEGRADED-state veto, defaults-don't-veto-SPREAD/DEGRADED-on-baseline);
  monograph probe -> `shasum 65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a`
  (byte-identical, `uniq -c` = 2);
  forbidden-scan `grep -niE 'router|scorer|rank(er|ing)?|\bRL\b'` over changed
  files -> no matches;
  wall-clock scan over changed files -> no matches (only vendored
  simtruth/ docstring false-positives remain, pre-existing).
- fixes / deviations: (1) INTERPRETATION of pinned test (d): with 1h bars and
  an 8h funding period some bar of any hourly tape is always within
  funding_window_bars of a boundary, so "thresholds at defaults do not veto
  the synthetic baseline run" is implemented as *no SPREAD/DEGRADED vetoes* on
  the seed-7 run; funding-window vetoes on that tape are a deterministic
  epoch-alignment artifact (FIXED_EPOCH % 8h = 7.108h puts every bar i%8==0
  within 1h of a boundary). (2) Funding-window semantics pinned against the
  Step-2 open-interval golden: the bar ending EXACTLY on a boundary enters
  after that settlement (fill > B) and is NOT vetoed; only bars with
  0 < B - close <= funding_window_bars*interval are (settlement books on the
  first post-entry step). (3) RUNLOG rows for steps 0-2 sat uncommitted in the
  tree (written by the prior session after the step-2 commit); they ride in
  this commit with the step-3 row — content unchanged, no new commits created.
- commit: (below) `v8-step-3: D-024 mechanical tradability mask (manifest constants, RiskGate-adjacent veto, NOT_EXECUTED counterfactuals)`
- gate: pytest=26 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

## Step 4 — Phase 1 data plane: vision_backfill.py + tape audit — DONE
- started: 2026-08-01T03:03:30Z finished: 2026-08-01T03:08:30Z
- files touched: tools/vision_backfill.py (new), tests/test_tape_audit.py (new),
  RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `33 passed in 0.44s`
  (26 -> 33; +7 offline tape-audit tests: checksum+three-clocks,
  header-tolerated, corrupt checksum/zip fail-closed, double-run idempotency,
  clean audit, venue-gap audit, payload-corruption audit);
  CLI smoke (offline, fixture zip in --out): run1 `wrote 6 rows (skipped 0
  duplicates); tape_hash=9f122b90...`, run2 `wrote 0 rows (skipped 6
  duplicates)` + identical tape_hash (idempotent), `--audit`
  `{"monotonic": true, "payload_hashes_ok": true, "row_count": 6,
  "venue_gaps": 0}`;
  lab compatibility: `AppendOnlyLog.replay_tape()` over the produced
  tape.jsonl -> 6 rows, tape hash unchanged (TapeRow(**r) replay safe);
  monograph probe byte-identical (65eef39..., uniq -c = 2);
  forbidden-scan over the two new files -> no matches;
  wall-clock scan -> only a docstring false-positive (`open time.`), no clock
  reads (rule scopes to src/v8/ anyway; this is tools/).
- fixes / deviations: OPEN_PIN + DEVIATION: the runbook pins "reuse
  tools/data.py's row-building logic (import it; do not fork it)", but
  tools/data.py raises SystemExit at import time without
  polars/pandera/pyarrow/duckdb (none installed), and O-009 + runbook step 5
  forbid adding those dependencies this session. vision_backfill.py therefore
  mirrors data.py's DOCUMENTED contracts as stdlib code — kline column order
  + ms->ns conversion (from _normalize_kline_archive) and the checksum file
  contract (from _parse_checksum_file/_sha256_file) — cited in the module
  docstring and inline; the mapping is the same contract, not a new format.
  JSONL rows carry exactly the TapeRow fields (store.replay_tape does
  TapeRow(**r)); payload_hash + schema_version live inside payload.
  Real download is operator-only (--download); never required by tests.
- commit: (below) `v8-step-4: Phase 1 data plane — vision_backfill.py (Vision monthly klines -> PIT tape JSONL, checksum-verified, idempotent) + offline tape audit`
- gate: pytest=33 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

## Step 5 — Phase 2 state engine: feature groups + lineage — DONE
- started: 2026-08-01T03:09:30Z finished: 2026-08-01T03:13:00Z
- files touched: src/v8/schema.py, src/v8/marketstate.py,
  tests/test_vertical_slice.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `37 passed in 0.46s`
  (33 -> 37; +4 tests: feature-group declaration+tagging+reproducible state
  hash, lineage binds feature_version, validate_feature_groups fails closed on
  an undeclared group, revision replay reproduces the prior state hash);
  monograph probe byte-identical (65eef39..., uniq -c = 2);
  forbidden-scan over changed files -> no matches;
  wall-clock scan over changed src/v8/ files -> no matches.
- fixes / deviations: none beyond the pinned interpretation. FEATURE_GROUPS
  declares the five Phase-2 ontology groups plus a `raw` base layer (close —
  the five ontology groups need a data-plane root to require) and the D-026
  `history` group; `requires:` is a frozen declaration, not a per-state
  guarantee (a short tape emits history before the 20-bar EMA warmup has
  produced trend; that is allowed). Lineage formula extended to
  (value, max_input_available_time, group, feature_version) — every dependent
  hash (state_id, evaluation records, ledger) changes with a re-tag or
  re-version, by design. Materialization (parquet views, DATASET_SPEC 5)
  deferred per O-009; PIT tests run on synthetic tape because no Phase-1 tape
  exists in the session (offline-only).
- commit: (below) `v8-step-5: Phase 2 state engine — feature groups (trend/volatility/location/participation/response/history) with requires declarations, group+version in lineage hash, revision-replay PIT test`
- gate: pytest=37 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

## Step 6 — Phase 3 expert metadata + registry — DONE
- started: 2026-08-01T03:13:30Z finished: 2026-08-01T03:18:00Z
- files touched: src/v8/experts/base.py, src/v8/experts/trend_pullback.py,
  src/v8/experts/failed_breakout.py, docs/EXPERTS_REGISTRY.yaml (new),
  tests/test_expert_registry.py (new), pyproject.toml, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `42 passed in 0.53s`
  (37 -> 42; +5 registry tests: YAML parses with vocabulary + required keys,
  YAML matches code projection, pilot ontology ids, requires audited against
  consumption, pilots run on synthetic tape);
  monograph probe byte-identical (65eef39..., uniq -c = 2) — CONFIRMED even
  with docs/EXPERTS_REGISTRY.yaml present, because build_monograph.py's NAMES
  list does not include it (only CLAIMS/EXPERIMENT_REGISTRY.yaml are in the
  monograph);
  forbidden-scan over all changed/new files -> no matches;
  wall-clock scan over changed src/v8/ -> no matches.
- fixes / deviations: NOTE — creating docs/EXPERTS_REGISTRY.yaml is authorized
  by the runbook itself (step 6 owns list: "docs/EXPERTS_REGISTRY.yaml (new)")
  and by the ownership map; hard rule 1's docs/ freeze covers editing existing
  corpus files, and the probe byte-identity gate confirms no monograph section
  changed. ENVIRONMENT — the "registry YAML parses" gate needs a real YAML
  parser; the venv had no pip and pyyaml was absent, so `uv pip install
  --python .venv/bin/python pyyaml` (6.0.3) was run and `pyyaml>=6` added to
  the dev extra in pyproject.toml (documented, decision path stays
  stdlib-only). Experts run on synthetic tape; no Phase-1 tape exists and no
  registry experiment is registered; nothing promoted.
- commit: (below) `v8-step-6: Phase 3 expert metadata + registry (mechanism/behavior/variant ids, docs/EXPERTS_REGISTRY.yaml, code-registry consistency + consumption audit tests)`
- gate: pytest=42 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

## Step 7 — Status report — DONE
- started: 2026-08-01T03:18:30Z finished: 2026-08-01T03:21:00Z
- files touched: docs/STATUS_REPORT.md (new), RUNLOG.md
- evidence: final gate sweep `.venv/bin/python -m pytest tests -q` -> `42 passed`;
  monograph probe byte-identical (65eef39..., uniq -c = 2) even with
  docs/STATUS_REPORT.md present (not in the build NAMES list);
  forbidden-scan over changed files -> no matches;
  wall-clock scan -> no matches.
- fixes / deviations: none. docs/STATUS_REPORT.md is the runbook-owned final
  artifact (step 7); its presence does not change the probe, proving no
  corpus section was touched.
- commit: (below) `v8-step-7: status report`
- gate: pytest=42 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

# ══════════════════════════════════════════════════════════════════════════
# SESSION 2 — Phase 1 on real data + v8_slice_001 preregistration
# Start: 2026-08-01T03:22Z. Contract: session-1 runbook hard rules verbatim.
# ══════════════════════════════════════════════════════════════════════════

## Session 2 — Step 0 — Pre-flight baseline — DONE
- started: 2026-08-01T03:22:10Z finished: 2026-08-01T03:24:10Z
- files touched: RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `42 passed in 0.50s`
  (session-1 count preserved); probe rebuild — NEW BASELINE (corpus changed at
  operator closure 76ef874): `.venv/bin/python tools/build_monograph.py --lang
  en --docs docs --out /tmp/v8_index_probe.html` ->
  `wrote /tmp/v8_index_probe.html: sections=31 papers=60 words=46763`;
  `shasum -a 256 /tmp/v8_index_probe.html site/index.html` ->
  `ea5b770528fb07931ff08801e4704a4fefca3586d88da1277a75311ccb075def` (both —
  site/index.html is current with the operator-closed corpus; the session-1
  hash 65eef39f… is stale by design, 31 sections now after EXPERTS_REGISTRY
  was added to the monograph at closure); TR probe ->
  `2c5b973ac9c59e807b2a6fb4715b392d725e24ee1d6d6295e45aed553eb44409`;
  `git log --oneline -3` -> `69c7a83 v8-step-9: session-2 goal prompt`,
  `76ef874 v8-step-8: operator closure — close divergence rows, register
  D-037, EXPERTS_REGISTRY in monograph (31 sections)`;
  `git status --short` -> clean tree.
- fixes / deviations: none. New EN probe baseline = ea5b7705… replaces the
  stale session-1 65eef39f… for all byte-identity gates this session.
- commit: (below) `v8-step-0: session-2 preflight — new probe baseline ea5b7705…, 42 tests green, clean tree`
- gate: pytest=42 monograph=baseline-reset?yes (ea5b7705…) tree-clean?yes

## Session 2 — Step 1 — Tooling deps + data.py path — DONE
- started: 2026-08-01T03:24:20Z finished: 2026-08-01T03:29:00Z
- files touched: pyproject.toml, tests/test_data_pipeline.py (new), RUNLOG.md
- evidence: `uv pip install --python .venv/bin/python -e ".[tooling]"` ->
  installed polars 1.43.1, pyarrow 25.0.0, pandera[polars], duckdb 1.5.5
  (import check PASS); `.venv/bin/python -m pytest tests -q` -> `46 passed in
  0.96s` (42 -> 46; +4 offline tooling-path tests: plan_archives monthly URL,
  partial-boundary daily cadence, checksum-file contract, sha256);
  monograph probe byte-identical to the session-2 baseline
  (ea5b770528fb07931ff08801e4704a4fefca3586d88da1277a75311ccb075def,
  uniq -c = 2);
  data.py exercise on one small month (BTCUSDT 1h, 2026-06-01..2026-07-01):
  `tools/data.py build --symbols BTCUSDT --start 2026-06-01 --end 2026-07-01
  --out /tmp/v8_dp_build --interval 1h --data-types klines --no-exchange-info`
  -> `status VERIFIED`, 1 archive (37239 B), 720 rows, 1 parquet (50596 B);
  `verify --dataset-dir` -> `verdict PASS`; `audit --dataset-dir` ->
  `verdict PASS` (duckdb-1.5.5, 720 rows, duplicate_primary_keys 0).
- fixes / deviations: none. `--keep-raw` on the Step-2 build retains the zips
  AND their `.CHECKSUM` siblings in the raw cache (confirmed on the 3-month
  window build), so vision_backfill can consume them without `--download`
  (no new download code).
- OPEN_PIN (operator action): register the D-037 admission decision — heavy
  tooling deps (polars/pyarrow/pandera[polars]/duckdb) are now installed in
  the venv and declared as the `tooling` extra in pyproject.toml for Phase-1
  parquet materialization (DATASET_SPEC section 5). The decision path
  (`src/v8/` minus `simtruth/`) remains stdlib-only (O-009); no test or
  contract depends on the new deps except the pure planning/checksum helpers.
- commit: (below) `v8-step-1: session-2 tooling admission — polars/pyarrow/pandera/duckdb via uv + pyproject tooling extra, data.py build/verify/audit PASS on BTCUSDT 1h 2026-06, 4 offline pipeline tests`
- gate: pytest=46 monograph=byte-identical?yes (ea5b7705…)
  forbidden-scan=clean?yes wall-clock=clean?yes (no src/v8/ change)

## Session 2 — Step 2 — Real tape: download + PIT tape + audit — DONE
- started: 2026-08-01T03:29:20Z finished: 2026-08-01T03:34:00Z
- files touched: research/tape/btcusdt-1h-2026-q2/ (gitignored derived
  artifacts — dataset/, raw/, tape/), RUNLOG.md
- evidence (mapping recorded — lab store stays JSONL, IMPLEMENTATION_LAYOUT):
  1) `tools/data.py build --symbols BTCUSDT --start 2026-04-01 --end
     2026-07-01 --out research/tape/btcusdt-1h-2026-q2/dataset --raw-cache
     research/tape/btcusdt-1h-2026-q2/raw --interval 1h --data-types klines
     --no-exchange-info --keep-raw` -> VERIFIED, 3 archives (112172 B), 2184
     rows, 1 parquet (139543 B); `verify` -> PASS; `audit` (duckdb-1.5.5) ->
     PASS, duplicate_primary_keys 0. data.py does the download + SHA-256
     checksum verification; --keep-raw retains the zips AND .CHECKSUM.
  2) `tools/vision_backfill.py --symbol BTCUSDT --interval 1h --month
     {2026-04,2026-05,2026-06} --out research/tape/btcusdt-1h-2026-q2/tape`
     (no --download; consumes data.py's verified archives) -> tape.jsonl.
     Exact row mapping: source=binance-um, channel=kline,
     event_time=close_time_ms*1e6, available_time=event_time+1s,
     ingested_time=available_time, venue_sequence=open_time_ms//interval_ms,
     event_id=BTCUSDT:1h:{open_time_ms}, payload {open,high,low,close,volume,
     open_time_ms,close_time_ms,quote_asset_volume,number_of_trades,
     closed:True,payload_hash,schema_version=binance-um-v1-ms}.
  3) `--audit` -> {"monotonic": true, "payload_hashes_ok": true,
     "row_count": 2184, "venue_gaps": 0}.
  4) Idempotency/reproducibility: re-run of all three months -> `wrote 0 rows
     (skipped 720/744/720 duplicates)`; tape hash stable:
     run1 = run2 = `8b12707e0d89f2a955d2badccf9f278267c0e086`.
  5) Lab PIT sanity: `AppendOnlyLog.replay_tape()` -> 2184 rows, venue_sequence
     contiguous across the month boundary; `build_state(rows, last_available,
     ('BTCUSDT',))` -> all 7 features (close, ema_fast, ema_slow, atr,
     prior_high, prior_low, history), lineage c30637ffbb4f28850cf9d7a7a9a15863de1219a6.
  Universe NOT extended (O-011 gate): single locked symbol BTCUSDT.
  Scope: dev window 2026-04-01..2026-07-01 (3 recent months; 2026-07 not yet
  published on Vision as of 2026-08-01).
- fixes / deviations: none. Tests never touched the network; all the above is
  operator/agent data production from verified public archives.
- commit: (below) `v8-step-2: session-2 real tape — BTCUSDT 1h 2026-04..06 via data.py (verified) + vision_backfill JSONL PIT tape, audit clean, idempotent, tape hash 8b12707e…`
- gate: pytest=46 monograph=byte-identical?yes (ea5b7705…)
  forbidden-scan=clean?yes wall-clock=clean?yes (no src/v8/ change)

## Session 2 — Step 3 — Materializations + lab on real tape — DONE
- started: 2026-08-01T03:35:00Z finished: 2026-08-01T03:42:00Z
- files touched: src/v8/lab.py (states decision ledger + birth snapshot +
  ledger-hash composition), src/v8/lifecycle.py (CandidateRegistry.apply gains
  `extra` merged into the append-only record before write),
  tools/materialize_views.py (new, DATASET_SPEC 5 DuckDB views),
  tests/test_vertical_slice.py (+2), tests/test_materialize_views.py (new, +2),
  RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `50 passed in 1.78s`
  (46 -> 50; +4: decision-ledger states persisted + reproducible hashes, birth
  snapshot on DETECTED, materializer writes all five views with correct row
  counts, fail-closed on data-hash mismatch);
  monograph probe byte-identical (ea5b7705…, uniq -c = 2);
  forbidden-scan over changed files -> no matches; wall-clock scan -> none.
  REAL-TAPE RUN (pinned manifest research/tape/btcusdt-1h-2026-q2/manifest_dev.json:
  experiment_id=v8-dev-2026q2-btcusdt, code_hash=6a2b024e…, data_hash=
  8b12707e…, universe=BTCUSDT, 1h, round_trip_cost_r=0.07, funding_rate_r=0.0,
  funding_hours=8, mask defaults, no authority receipt):
  `tools/materialize_views.py --manifest … --store /tmp/v8_real_store` ->
  rows {market_states: 2184, candidate_birth: 713, candidate_trigger: 706,
  candidate_outcomes: 713, execution_trajectories: 2900}, ledger_hash
  2c1e0fd8…, verdict NO_ECONOMIC_CLAIM, code/data hashes matched live.
  Determinism: two fresh lab runs -> ledger_hash equal, states.hash equal.
  O-017 accounting (D-027 portfolio-state rejections only): n_executed=256,
  n_portfolio_rejected=360 (all EXISTING_EXPOSURE_CONFLICT; PORTFOLIO_HEAT
  0), other rejections: TRADABILITY_MASK_VETO=90 (all detail FUNDING_WINDOW —
  spread/DEGRADED never fired on real BTCUSDT 1h), excess_cost=0.
  execution_share = 256/(256+360) = 0.4156. Outcomes: MATURE 234,
  NOT_EXECUTED 450, RIGHT_CENSORED 29. Population divergence (two-sample KS,
  executed vs portfolio-rejected net_R, numpy): n=256/360, means +0.0519/
  +0.0184, std 0.891/0.942, KS = 0.073.
- fixes / deviations: (1) DATASET_SPEC 1 layer 2 requires MarketState in the
  decision ledger — the lab did not persist states; added states.jsonl (one
  record per bar) and bound it into ledger_hash. (2) CANDIDATE_LIFECYCLE_SPEC
  1 requires an immutable BirthSnapshot — the lab recorded none; the DETECTED
  transition now carries expert_id/version, instrument, direction,
  setup_anchor_event_id, geometry_version, state_id via
  CandidateRegistry.apply(extra=…), merged before append so it is immutable.
  (3) Materializer fails closed on live code/data hash mismatch (compile-once
  discipline). Scope not extended beyond the locked baseline: same two pilots,
  same geometry/costs, universe unchanged (O-011).
- OPEN_PIN (carry-forward): D-027 verdict GATING (LabReport.execution_share +
  divergence stat + ATTRIBUTION_UNSAFE_* verdicts) remains unimplemented in
  code; this session measured and preregisters the thresholds (Step 4) but the
  code gate lands with the Phase-4 experiment runner.
- commit: (below) `v8-step-3: session-2 materializations — decision-ledger states + birth snapshot, tools/materialize_views.py (DuckDB parquet views from pinned manifest), real-tape run 2184 states/713 candidates, determinism + O-017 baseline (execution_share 0.416, KS 0.073)`
- gate: pytest=50 monograph=byte-identical?yes (ea5b7705…)
  forbidden-scan=clean?yes wall-clock=clean?yes

## Session 2 — Step 4 — v8_slice_001 preregistration document — DONE
- started: 2026-08-01T03:42:30Z finished: 2026-08-01T03:49:00Z
- files touched: docs/PREREGISTRATION_V8_SLICE_001.md (new, runbook-owned
  artifact), RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `50 passed` (unchanged;
  no code touched); monograph probe byte-identical (ea5b7705…, uniq -c = 2)
  with the new docs file present (PREREGISTRATION_V8_SLICE_001.md is not in
  build_monograph.py's NAMES list); forbidden-scan: no code changed this step.
- process: document written with ALL HYPOTHESIS_LAB_PROTOCOL hypothesis-record
  fields (formal null/alternative; economic mechanism; behavior + detection
  rule; universe as-of; data/source manifest; clocks; geometry + costs;
  dependence unit; primary metric; test; minimum coverage; dev/frozen
  partitions; rejection consequence) + O-017 proposal. Then an adversarial
  verification workflow (4 read-only critics, 273k tokens) returned
  verdict=AMEND: 1 blocker + 7 warnings, all precision/consistency, no
  factual error. ALL incorporated:
  (1) BLOCKER fixed — section 13 now declares the frozen OOS as the first TWO
  published months strictly after 2026-07-01 (>=1,400 bars), satisfying
  section 12's 2-month minimum; single-month definition removed.
  (2) Label-horizon at the OOS end pinned: 9-bar extension (8 expiry + 1
  entry) fetched with the holdout, part of the frozen tape, hashed before any
  evaluation; unobservable episodes RIGHT_CENSORED, never silently excluded.
  (3) Test procedure pinned: Bonferroni-only (alpha_f=0.025), percentile
  one-sided CI (2.5th percentile lower bound); FDR alternative removed.
  (4) EMA periods (5/20), prior-high window 32, ATR 14 stated; parameter
  provenance declared (frozen pre-dev, no search performed, no undisclosed
  variants).
  (5) round_trip_cost_r locked for this experiment (not revisable
  post-verdict).
  (6) Block size operationalized (24h default; 168h if |lag-1 autocorr| > 0.10
  on the OOS sample; mechanical rule, fixed here).
  (7) ledger_hash reclassified as a derived run output (views_manifest.json),
  not an input-manifest field; candidate_trigger 706 added to view counts.
  (8) TRADABILITY_MASK_VETO exclusion cited to D-027's principle.
- O-017 proposal (set pre-holdout from the Step-3 baseline, never after a
  verdict): execution_share floor = 0.25 (60% of observed 0.4156);
  population-divergence threshold = two-sample KS on net_R <= 0.20 (~2.7x the
  observed dev-window KS 0.073). Verdict rules per D-027.
- fixes / deviations: none beyond the review-driven amendments above. The
  experiment was NOT run and the frozen holdout was NOT downloaded/opened;
  the doc states this explicitly in three places.
- commit: (below) `v8-step-4: session-2 v8_slice_001 preregistration — all HYPOTHESIS_LAB_PROTOCOL fields, O-017 thresholds (share 0.25 / KS 0.20) from dev baseline, adversarial review incorporated, holdout declared never opened`
- gate: pytest=50 monograph=byte-identical?yes (ea5b7705…)
  forbidden-scan=clean?yes (no code change) wall-clock=clean?yes

## Session 2 — Step 5 — Status report — DONE
- started: 2026-08-01T03:50:00Z finished: 2026-08-01T03:52:30Z
- files touched: docs/STATUS_REPORT.md (overwritten for session 2 — session
  artifact, not corpus), RUNLOG.md
- evidence: final gate sweep `.venv/bin/python -m pytest tests -q` -> `50
  passed`; monograph probe byte-identical (ea5b7705…, uniq -c = 2) with both
  runbook-owned docs artifacts present (STATUS_REPORT + PREREGISTRATION are
  not in build_monograph.py's NAMES list); forbidden-scan over changed files
  -> no matches; wall-clock scan -> no matches.
- fixes / deviations: none. All session-2 steps 0-5 DONE; no BLOCKED/SKIPPED.
- commit: (below) `v8-step-5: status report`
- gate: pytest=50 monograph=byte-identical?yes (ea5b7705…)
  forbidden-scan=clean?yes wall-clock=clean?yes

# ══════════════════════════════════════════════════════════════════════════
# SESSION 3 — complete all phases except Phase 4 (operator takes Phase 4)
# Directive: "complete all other phases, ignore phase 4". Phase 4 (first
# program gate) is operator-owned; preregistration v8_slice_001 is RATIFIED.
# Phases 5 (gated components) and 7 (learning plane) are gated on Phase-4
# evidence / certified edge (rule 12) and are BLOCKED BY DESIGN — their
# absence is enforced as contract probes, nothing is built for them.
# Phase 6 (ops and hardening) is the build scope of this session.
# ══════════════════════════════════════════════════════════════════════════

## Session 3 — Step 0 — Re-baseline — DONE
- started: 2026-08-01T03:55:00Z finished: 2026-08-01T03:56:30Z
- files touched: RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `50 passed in 1.73s`
  (unchanged); probe rebuild — NEW BASELINE (operator closure commits
  v8-step-10/11/12 promoted the ratified preregistration into the monograph):
  `wrote /tmp/v8_index_probe.html: sections=32 papers=60 words=50374`;
  `shasum -a 256 /tmp/v8_index_probe.html site/index.html` ->
  `bc207925d828280de4b7b8d02d359b2f79da70ba58144cc9360b3ed059ba4c45` (both —
  site is current; the session-2 hash ea5b7705… is stale by design, 32
  sections now); `git log --oneline -3` -> 16563c1 (v8-step-12: dataset v0.1,
  D-039), a7eb4ef (v8-step-11: ratify O-017, promote preregistration), 91aea06
  (v8-step-10: session-2 closure, D-038); `git status --short` -> clean tree.
- fixes / deviations: none. Baseline for all session-3 byte-identity gates =
  bc207925d828280de4b7b8d02d359b2f79da70ba58144cc9360b3ed059ba4c45.
- commit: (below) `v8-step-0: session-3 re-baseline — probe bc207925…, 50 tests, clean tree`
- gate: pytest=50 monograph=baseline-reset?yes (bc207925…) tree-clean?yes

## Session 3 — Step 1 — Data-quality monitoring + structured observability — DONE
- started: 2026-08-01T05:05:00Z finished: 2026-08-01T05:09:00Z
- files touched: tools/monitor_tape.py (new), tests/test_monitor_tape.py (new),
  RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `55 passed in 1.63s`
  (50 -> 55; +5 monitor tests: clean-tape schema+structured JSON, schema
  violations detected, staleness with injected now, exit codes, audit reuse);
  monograph probe byte-identical (bc207925…, uniq -c = 2);
  forbidden-scan over changed files -> no matches;
  wall-clock scan -> no matches in src/v8/ (the monitor's `time.time_ns()` is
  an ops tool in tools/, not the decision path — OPERATIONS_SPEC staleness
  alerting requires a reference clock; tests inject --now and never touch it);
  real-tape smoke: `tools/monitor_tape.py --tape
  research/tape/btcusdt-1h-2026-q2/tape --schema --experiment-id
  v8-dev-2026q2-btcusdt` ->
  {"audit": {"monotonic": true, "payload_hashes_ok": true, "row_count": 2184,
  "venue_gaps": 0}, "rows": 2184, "schema_problems": [], "verdict": "OK"},
  exit 0.
- fixes / deviations: (1) test fixture initially lacked payload_hash, so the
  REUSED audit correctly flagged it — fixture made contract-compliant (audit
  reuse is the point; no fork). (2) monitor needed repo-root on sys.path for
  the `tools.` package import under CLI runs. (3) tools/ time.time_ns() is a
  documented ops-tool clock (staleness needs "now"); the no-wall-clock rule
  covers src/v8/ only, and tests inject --now.
- commit: (below) `v8-step-1: session-3 ops — tools/monitor_tape.py (schema + audit reuse + staleness, structured JSON, fail-closed) + 5 offline tests`
- gate: pytest=55 monograph=byte-identical?yes (bc207925…)
  forbidden-scan=clean?yes wall-clock=src/v8-clean?yes

## Session 3 — Step 2 — Golden-backtest regression + CI — DONE
- started: 2026-08-01T05:09:30Z finished: 2026-08-01T05:12:30Z
- files touched: tests/test_golden_backtest.py (new),
  .github/workflows/ci.yml (new), RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `56 passed` (55 -> 56;
  +1 golden regression: pins ledger_hash eb3c62de…, data_hash 1c41077b…,
  states_hash c2e4255b…, candidate_count 24, terminal_distribution
  {CLOSED 13, INVALIDATED 1, REJECTED 10}, verdict NO_ECONOMIC_CLAIM, plus
  the identical-fresh-run replay assertion);
  monograph probe byte-identical (bc207925…, uniq -c = 2);
  forbidden-scan over new files -> no matches;
  CI workflow (.github/workflows/ci.yml): uv + python 3.11, install
  `-e ".[dev,tooling]"`, pytest (includes the golden regression), monograph
  byte-identity check; no untrusted input interpolation (injection-safe).
  The golden is pinned from the code as of 2026-08-01 (D-026 keys, funding v4,
  D-024 mask, decision-ledger states, birth snapshots) — updating it is a
  deliberate act, per PERSISTENCE_REPLAY_SPEC section 4.
- fixes / deviations: none. lint/typecheck are not configured in this repo
  (no linter tooling); the CI DoD is satisfied by tests + golden regression +
  probe identity, matching OPERATIONS_SPEC section 4's "lint, typecheck, and
  tests ... plus a golden-backtest regression" at research scale.
- commit: (below) `v8-step-2: session-3 ops — golden-backtest regression (pinned ledger/state hashes, candidate counts) + GitHub Actions CI (pytest, golden, monograph byte-identity)`
- gate: pytest=56 monograph=byte-identical?yes (bc207925…)
  forbidden-scan=clean?yes wall-clock=clean?yes

## Session 3 — Step 3 — Certification record + artifact status + purity probes — DONE
- started: 2026-08-01T05:12:30Z finished: 2026-08-01T05:16:00Z
- files touched: research/certification/simulation_authority_certification_v1.json
  (new record), tools/artifact_status.py (new), tests/test_artifact_status.py
  (new), tests/test_decision_path_purity.py (new), RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `67 passed in 2.14s`
  (56 -> 67; +6 artifact-status tests, +5 decision-path-purity tests);
  monograph probe byte-identical (bc207925…, uniq -c = 2);
  forbidden-scan: src/v8/ + tools/ completely CLEAN; the only hits in new code
  are tests/test_decision_path_purity.py's own assertion regexes (lines 3,
  25-26, 60) which NAME the forbidden components precisely to assert their
  absence — the enforcement probe, not a component (documented exception);
  certification CLI: `tools/artifact_status.py` -> exit 0 with
  {certification FAIL, autopilot_permission BLOCKED, live_reachable false}.
- fixes / deviations: none. Phase-5/7 positioning: the gated components
  (router, learned scorer, ranker, learned/RL execution, online learning) and
  the learning plane are BLOCKED BY DESIGN on Phase-4 evidence / certified
  edge (rule 12) — nothing was built for them; instead their ABSENCE is now a
  contract probe (test_decision_path_purity.py) so they cannot be half-built
  by accident. The certification record (FAIL/BLOCKED) matches OPERATIONS_SPEC
  section 1 and D-022.
- commit: (below) `v8-step-3: session-3 ops — simulation authority certification record (FAIL/BLOCKED), artifact status lifecycle (research->shadow->paper->live gates), decision-path purity probes (stdlib-only, clock-free, no gated components)`
- gate: pytest=67 monograph=byte-identical?yes (bc207925…)
  forbidden-scan=clean?yes (src/v8+tools; purity test names terms to forbid them)
  wall-clock=clean?yes

## Session 3 — Step 4 — Hardening fixes from adversarial Phase-6 review — DONE
- started: 2026-08-01T05:16:30Z finished: 2026-08-01T05:20:00Z
- files touched: tools/monitor_tape.py, src/v8/simulator.py, src/v8/lab.py,
  tools/artifact_status.py, .github/workflows/ci.yml, tests/test_monitor_tape.py,
  tests/test_artifact_status.py, tests/test_decision_path_purity.py,
  tests/test_vertical_slice.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `80 passed in 2.17s`
  (67 -> 80; +13 review-driven tests); monograph probe byte-identical
  (bc207925…, uniq -c = 2); golden regression STILL PASSES (the
  fill_policy default is byte-identical: sim hash unchanged);
  forbidden-scan over src/v8 + tools + .github -> no matches;
  wall-clock scan over src/v8 -> no matches.
- process: adversarial Phase-6 review workflow (3 read-only reviewers, 236k
  tokens) -> 0 blockers, 20 warnings. ALL actionable warnings fixed:
  (1) monitor staleness crashed (KeyError) on empty tapes — now a structured
      violation (fail closed, JSON well-formed);
  (2) monitor --schema failed OPEN on empty/channel-less tapes — now rejects
      ('cannot evaluate');
  (3) bool passed the int-timestamp dtype check (isinstance) — now
      type(x) is int;
  (4) missing tape died with a traceback — now a structured FileNotFoundError
      report;
  (5) CI shasum -> sha256sum (portability);
  (6) LATENT DIVERGENCE FIXED: ExperimentManifest.fill_policy was declared
      but the simulator ignored it silently — CanonicalSimulator now
      validates fill_policy (SUPPORTED_FILL_POLICIES = FILL_AT_BAR_CLOSE) and
      the lab wires manifest.fill_policy through; an unsupported policy fails
      closed instead of a hash claiming fill semantics the stepper does not
      implement (OPERATIONS_SPEC section 1 single-code-path property);
  (7) artifact_status.main(cert_path) injectable — the PASS+GRANTED fail-open
      side is now tested; full no-op/unknown-current/demotion matrix and the
      renewed-authority positive half covered;
  (8) dead purity assertion removed; audit-key + audit-fail-closed +
      dir-as-tape + experiment_id-propagation monitor tests added.
  OPERATIONS_SPEC items with no deliverable, recorded as conscious
  deviations (NOT buildable at this stage): feed reconciliation (single
  locked feed binance-um, O-011); CI lint/typecheck (no linter configured —
  pytest + golden + probe per research scale); store-unreachable mid-run
  abort (local disk store, not simulated); rollback/kill-switch mechanism
  (no live/shadow system exists yet — gated); counters/gauges layer (JSON
  report carries gauge-like fields; 'do not over-invest' caveat).
- fixes / deviations: the fill_policy wiring is a src/v8 change made under
  Phase-6 hardening; it is contract-aligned (the manifest field existed,
  unused — a tracked divergence), default byte-identical (golden unchanged).
- commit: (below) `v8-step-4: session-3 hardening — review-driven fixes (monitor fail-closed paths, bool-dtype, missing-tape JSON, CI sha256sum), fill_policy enforcement (manifest input, fail-closed), artifact-status positive-half tests, 13 new tests`
- gate: pytest=80 monograph=byte-identical?yes (bc207925…)
  forbidden-scan=clean?yes (src/v8+tools+.github) wall-clock=clean?yes

## Session 3 — Step 5 — Status report — DONE
- started: 2026-08-01T05:20:30Z finished: 2026-08-01T05:22:30Z
- files touched: docs/STATUS_REPORT.md (overwritten for session 3 — session
  artifact, not corpus), RUNLOG.md
- evidence: final gate sweep `.venv/bin/python -m pytest tests -q` -> `80
  passed`; monograph probe byte-identical (bc207925…, uniq -c = 2) with the
  session-3 status report present; forbidden-scan over changed files -> clean;
  wall-clock scan -> clean.
- fixes / deviations: none. All session-3 steps 0-5 DONE.
- commit: (below) `v8-step-5: status report`
- gate: pytest=80 monograph=byte-identical?yes (bc207925…)
  forbidden-scan=clean?yes wall-clock=clean?yes

## Session 4 — Bugfix pass: critical/high confirmed bugs — DONE
- started: 2026-08-01T05:45:00Z finished: 2026-08-01T06:03:00Z
- process: multi-modal bug-hunt workflow (4 finders + per-finding adversarial
  verification; 31 agents, 2.75M tokens) over the decision path, tools,
  data plane and tests -> 27 findings, 22 CONFIRMED (1 critical, 5 high,
  9 medium, 7 low), 5 refuted. All critical/high/medium CODE bugs fixed;
  two design-level items recorded as OPEN_PINs; low test-coverage gaps closed.
- FIXED (code):
  (1) CRITICAL — vision_backfill silently dropped corrected/re-downloaded
      archives: the (source,event_id=open-time) dedup kept superseded bars
      while provenance recorded the NEW zip sha. Now source.json is per-month
      provenance (archives: [{month, zip_sha256}]) and check_archive_revision
      FAILS CLOSED before any write when a recorded month is re-run with a
      different zip (a corrected archive must be rebuilt in a fresh dir).
  (2) HIGH — Phase 1a rejection counterfactual entered one bar after the
      would-be fill (sim.run(bars[i+1:]) instead of bars[i:]), simulating a
      DIFFERENT trade for every vetoed/risk-rejected candidate and biasing
      the D-027/O-014 rejected population. Both Phase 1a sites now pass
      from_idx=i (entry at bars[i].close, inspected bars[i+1:]), mirroring
      the executed path. (Phase-2 excess-cost site left at i+1 — correct.)
  (3) HIGH — audit_tape provenance checks failed OPEN without source.json;
      now source.json is REQUIRED and every recorded archive's zip must exist
      and match its recorded sha (fail-closed per OPERATIONS_SPEC 5). Also
      detects duplicated (source,event_id) rows.
  (4) LOW-but-wiring — D-024 DEGRADED veto was unreachable: build_state
      hardcoded MarketState.quality='COMPLETE'. Now quality=DEGRADED when any
      feature is DEGRADED (MARKET_STATE_CONTRACT 4); quality is metadata and
      does not enter lineage/state hashes, but the bar-0 state records change
      (they carry the quality field) -> states/golden hashes bumped.
  (5) MEDIUM — data.py historical builds aborted when the exchangeInfo
      endpoint is geo-blocked (HTTP 451 on this machine). The fetch now
      degrades to a warning snapshot and the build continues (symbol universe
      comes from --symbols; the tape/hashes are unaffected).
- FIXED (tests): materializer tests now assert view CONTENT (features_json
  contains real features, birth rows carry expert/instrument/anchor, outcomes
  carry hashes, trajectories are legal transitions); funding integration
  through lab.run is now tested end-to-end (crafted tape: SHORT held across
  the 40h boundary books +0.01 with a positive rate); D-024 exact-boundary
  non-veto pinned; thesis test no longer self-referential; purity tests fail
  (not vacuous) on an empty decision path; plan_archives pins 17 daily
  archives; corrupt-zip tested through main(); double-run fail-closed guard
  (previous fix) retained.
- OPEN_PIN (operator/registry decision): D-026 episode key drifts for setups
  lasting >32 bars — with no false bar in the sliding 32-bar window the
  anchor is the window's oldest bar, so the key changes every bar and dedup
  silently never fires (confirmed: 21 distinct episodes from one continuous
  setup). Documented in D-034 as a bound, but it violates the
  CANDIDATE_LIFECYCLE_SPEC 1 absolute key-stability invariant. NOT fixed
  mechanically: a correct fix needs a registry decision on the history-window
  or anchor semantics; a wrong quick fix would be worse. Until then the
  behavior is known and the lab output stays deterministic.
- OPEN_PIN (contract ambiguity): trigger/invalidation is never evaluated on
  the detection bar itself (lab Phase 2 checks birth_idx == i-1 only), so a
  candidate whose invalidation predicate held AT BIRTH can still trigger and
  execute. No contract pins the invalidation window; a fix must be
  expert-aware (failed_breakout's detection-bar high > prior_high is
  inherent to the setup). Recorded, not silently changed.
- NOTED (no code change): prior_high/prior_low stamp the last bar's
  availability (conservative upper bound, no leakage — hash churn not
  justified); marketstate revision-replay mixing (unreachable through the
  real pipeline: store dedup + vision_backfill revision guard prevent
  coexisting revisions); AppendOnlyLog dedup conflating fact identity (same
  root as (1), handled at the ingestion layer).
- GOLDEN: consciously bumped (ledger 0d37dd96…, states 6cc0e25c…) because
  (2) changes rejected-candidate outcomes and (4) changes bar-0 state
  records; data_hash (tape hash) unchanged. Documented in
  tests/test_golden_backtest.py.
- commit: (below) `v8-bugfix: critical/high confirmed fixes — vision_backfill archive-revision fail-closed + per-month provenance + strict audit, Phase-1a counterfactual entry fix, DEGRADED state quality, data.py geo-block degrade, 22-finding bug hunt verified`
- gate: pytest=86 monograph=byte-identical?yes (bc207925…)
  forbidden-scan=clean?yes wall-clock=clean?yes

## Session 5 — Step 0 — Record D-085 fast-cache module — DONE
- started: 2026-08-11T00:00:00Z finished: 2026-08-11
- files touched: src/v8/fast.py, tests/test_fast_cache.py, src/v8/lab.py, src/v8/store.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> 800 passed in 74.55s; monograph probe rebuild byte-identical
- fixes / deviations: none — this is a recording commit, not a code change. The four files were sitting untracked/modified in the tree despite D-085 already admitting `fast.py` in the register (2026-08-11 corpus commit 4a1eb11). They form one coherent unit: `store.py` `lazy_index` + copy-on-write hardlink detach is what `CompleteRunCache.restore` relies on; `lab.py` wires the three caches behind `cache_dir`. Taken as a single commit referencing D-085.
- commit: (below) `v8-step: S0-commit D-085 fast-cache module (fast.py + lazy_index/COW store + lab cache wiring)`
- gate: pytest=800 monograph=byte-identical forbidden-scan=clean wall-clock=clean

## Session 5 — Step 1 — S0 parity harness + Dataset ingest — DONE
- started: 2026-08-11 finished: 2026-08-11
- files touched: v8-core/ (workspace: Cargo.toml, .cargo/config.toml, src/{main,hash,data,evidence,jsonx}.rs), tools/v82_reader.py, tests/parity/{__init__,conftest,runner,test_parity_s0}.py, reports/parity/S0.md, docs/CHANGELOG.md, docs/decisions/DECISION_REGISTER.md, site/{index,tr}.html
- evidence: `cargo test` -> 23 passed; `.venv/bin/python -m pytest tests/parity/test_parity_s0.py -q` -> 16 passed (G1..G6); `.venv/bin/python -m pytest tests -q` -> 816 passed (was 800; count rose, nothing regressed); monograph probe rebuild byte-identical (0f5230ea…); oracle tree hash pinned 184fb934…
- fixes / deviations: none — gate evidence in reports/parity/S0.md. The lenient tape parser (jsonx.rs) exists because CPython json.dumps emits NaN/Infinity as bare literals strict JSON rejects; the G6 message comparison normalizes float rendering (the one documented runtime divergence, PERFORMANCE_AUDIT_V82 §8) while requiring category + row identity exact. No speed claim; S0 is correctness.
- commit: (below) `v8-step: S0 parity harness + Dataset ingest`
- gate: pytest=816 cargo-test=23 monograph=byte-identical oracle-tree=184fb934…

## Session 5 — Step 2 — S1 FeatureStore + StateView — DONE
- started: 2026-08-11 finished: 2026-08-11
- files touched: v8-core/src/state.rs (new), v8-core/src/main.rs (features subcommand), tests/parity/test_parity_s1.py (new), reports/parity/S1.md (new), docs/CHANGELOG.md, docs/decisions/DECISION_REGISTER.md, site/{index,tr}.html
- evidence: `cargo test` -> 24 passed (fsum battery incl.); `.venv/bin/python -m pytest tests/parity/test_parity_s1.py -q` -> 9 passed; `.venv/bin/python -m pytest tests -q` -> 825 passed (was 816; nothing regressed); monograph probe rebuild byte-identical (6c0e9ac9…); oracle tree hash pinned 184fb934…
- fixes / deviations: three CPython 3.14 portability discoveries, all pinned by Rust unit tests and recorded in D-088: (1) sum() is compensated summation (_PyFloat_Fsum), not a left fold — state::fsum is a verbatim port incl. the special final fold + half-even tie fix; (2) x**2 is libm pow(x,2.0) ≠ x*x on some values, and LLVM folds pow(x,2.0)->x*x in release — black_box keeps the libm call (G5); (3) x**0.5 is libm pow(x,0.5) ≠ sqrt(x) on some values — std_pop finishes with powf(0.5). Also fixed two usize underflows (i - period + 1) that panic in debug.
- commit: (below) `v8-step: S1 FeatureStore + StateView`
- gate: pytest=825 cargo-test=24 monograph=byte-identical oracle-tree=184fb934…

## Session 5 — Step 3 — S2 Predicate IR + ReplayKernel — DONE
- started: 2026-08-11 finished: 2026-08-11
- files touched: v8-core/src/experts/{mod,predicate}.rs (new), v8-core/src/simulator.rs (new), v8-core/Cargo.toml (float_roundtrip), tools/predicate_ir.py (new), tests/parity/test_parity_s2.py (new), reports/parity/S2.md (new), docs/CHANGELOG.md, docs/decisions/DECISION_REGISTER.md, site/{index,tr}.html
- evidence: `cargo test` -> 24 passed; `.venv/bin/python -m pytest tests/parity/test_parity_s2.py -q` -> 6 passed (E1/E2/E3 738-point grid, E5, E4 replay parity on the candidate population, G4, G5, G6); `.venv/bin/python -m pytest tests -q` -> 831 passed (was 825); monograph probe byte-identical; oracle tree 184fb934…
- fixes / deviations: (1) serde_json default float parser not correctly rounded — "0.9632136759338213" parses 1 ulp low, breaking geometry parity; enabled float_roundtrip. (2) fail-open semantics not uniform — added the `guard` node for whole-condition fail-open (trend_pullback_depth, rsi_stoch variant b, bollinger_reversion close pre-check, gap_exhaustion either-ref); fib_rsi_bb prior_low_ref valid-form is GTE (boundary holds) vs 3sd GT.
- commit: (below) `v8-step: S2 predicate IR + ReplayKernel`
- gate: pytest=831 cargo-test=24 monograph=byte-identical oracle-tree=184fb934…

## Session 5 — Step 4 — S3 CubeReducer + streaming regret — DONE
- started: 2026-08-11 finished: 2026-08-11
- files touched: v8-core/src/regret.rs (new), v8-core/src/main.rs (cube subcommand), tests/parity/test_parity_s3.py (new), reports/parity/S3.md (new), docs/CHANGELOG.md, docs/decisions/DECISION_REGISTER.md, site/{index,tr}.html
- evidence: `cargo test` -> 24 passed; `.venv/bin/python -m pytest tests/parity/test_parity_s3.py -q` -> 5 passed (reduced tables == Python Phase-0 evaluator on every BOUND candidate; gap>=0; manifest structure; G4; G5; G6); `.venv/bin/python -m pytest tests -q` -> 836 passed (was 831); monograph probe byte-identical; oracle tree 184fb934…
- fixes / deviations: compute_gap's actual-cell-not-OK branch must set actual_utility=None (the Python RegretRecord does), not the cell's value — fixed.
- commit: (below) `v8-step: S3 CubeReducer + streaming regret`
- gate: pytest=836 cargo-test=24 monograph=byte-identical oracle-tree=184fb934…

## Session 5 — Step 5 — Status report — DONE
- started: 2026-08-11 finished: 2026-08-11
- files touched: docs/STATUS_REPORT.md (rewritten for this session)
- summary: S0-S3 complete and committed (f6c1909, 926965f, 3a23ef8, 8851fad), each with its parity gate evidenced in reports/parity/. S4 (CandidateBuffer + ExpertPlane, the 28 evaluate() ports) and S5 (EvidenceStore + DAG cache) remain — S4 is the largest stage and was not started mid-session. Cross-stage determinism findings LOCKED for the remaining stages (fsum, powf, float_roundtrip, guard, GTE boundary). Full suite 836 passed; oracle tree 184fb934….
- commit: (below) `v8-step: status report`
- gate: pytest=836 cargo-test=24 monograph=byte-identical

## Session 5 — Step 6 — S4 ExpertPlane port: candidate machinery + pilots — IN PROGRESS (clean checkpoint)
- started: 2026-08-11 finished: 2026-08-11
- files touched: v8-core/src/candidate.rs (new), v8-core/src/experts/port.rs (new), v8-core/src/experts/mod.rs, v8-core/src/state.rs (history_bars), v8-core/src/main.rs (evaluate-check), tests/parity/test_parity_s4.py (new), docs/STATUS_REPORT.md
- evidence: `cargo test` -> 24 passed; `.venv/bin/python -m pytest tests/parity/test_parity_s4.py -q` -> 2 passed (pilot draft parity: every bar's Rust draft matches the Python lab's evaluations — decision/direction/birth_time/risk_geometry/anchor); `.venv/bin/python -m pytest tests -q` -> 838 passed (was 836)
- status: S4 is IN PROGRESS. The candidate machinery (episode_key, registry, lifecycle transitions, ExposureBook, RiskGate, tradability mask) and the evaluate-port framework (find_setup_anchor + FeatMap) are built; the 3 pilots are ported and proven. Remaining: 25 more evaluate() ports + the full per-bar loop (Phases 1a/1b/2/3) + the population-parity harness. The S4 gate (candidate population parity) is NOT yet claimed.
- commit: (below) `v8-step: S4 ExpertPlane port (candidate machinery + pilot evaluate ports)`
- gate: pytest=838 cargo-test=24 monograph=byte-identical
