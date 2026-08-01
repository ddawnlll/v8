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
