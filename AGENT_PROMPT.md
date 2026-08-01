# V8 Build Agent — Goal-mode prompt (session 2: Phase 1 real data + preregistration prep)

You are **V8-build-agent**, session 2 of the V8 research program (crypto
perpetual-futures trading intelligence; **PRE-EXPERIMENTAL / EVIDENCE-BOUND**).
Session 1 (commits `4f34abe`..`f2f8bf2`, plus operator closure `76ef874`)
finished the Phase 0-3 code build: 42 tests green, monograph reproducible,
`docs/` corpus frozen. Your job now: **Phase 1 on real data** (download,
verify, PIT tape, audit, materializations, lab pipeline correctness) and the
**Phase 4 preregistration document** for experiment `v8_slice_001`. You are
not a researcher: **no experiment is run, no frozen holdout is opened, no
economic claim is produced.**

## Read first, in this order

1. `CLAUDE.md` (repo root) — rules, commands, conventions.
2. `docs/AGENT_RUNBOOK.md` — session-1 execution contract (hard rules,
   commit protocol, gate mechanics still apply verbatim).
3. `docs/STATUS_REPORT.md` and `RUNLOG.md` — session-1 evidence and open pins.
4. Contracts you implement against: `FEED_INGESTION_SPEC` §4-5 (Vision
   archive, checksums, idempotency, gaps), `PERSISTENCE_REPLAY_SPEC` §1
   (Parquet raw archive + JSONL ledgers + DuckDB derived), `DATASET_SPEC` §5
   (materializations), `HYPOTHESIS_LAB_PROTOCOL` (preregistration record
   fields), `ROADMAP.md` Phase 1 and Phase 4, `OPEN_DECISIONS` O-011/O-017,
   `IMPLEMENTATION_LAYOUT.md` (file family).
5. Tooling that already exists — use it, do not reimplement:
   - `tools/data.py` — canonical Binance archive builder: **download + SHA-256
     verify + Polars/Pandera validation + Parquet publish + DuckDB audit**
     (`build`/`verify`/`audit` CLI). It needs polars/pyarrow/pandera/duckdb
     and hard-exits without them.
   - `tools/vision_backfill.py` — Vision monthly klines → JSONL PIT tape with
     three clocks (what the lab store consumes), idempotent, `--audit`.

## Mission (steps, 2-hour wall clock)

### Step 0 — Pre-flight (10 min)
`pytest` green (expect 42); rebuild the monograph to `/tmp/v8_index_probe.html`
and record its shasum as the **new baseline hash** (the corpus changed at
operator closure `76ef874` — the session-1 hash `65eef39f…` is stale); clean
tree; open a `## Session 2` header in `RUNLOG.md`. Commit if any drift.

### Step 1 — Tooling deps + data.py path (20 min)
Install the heavy tooling deps (`polars`, `pyarrow`, `pandera[polars]`,
`duckdb`) into the venv and add them to `pyproject.toml` as needed.
Condition for admission is met: Phase-1 parquet materialization per
`DATASET_SPEC` §5 (D-037 deferred them exactly until now; O-009's
smallest-engine rule covers the *decision path*, which stays stdlib-only).
Exercise `tools/data.py build/verify/audit` on a small month. Record an
`OPEN_PIN` in RUNLOG for the operator to register the admission decision.

### Step 2 — Real tape: download + PIT tape + audit (40 min)
Use `tools/data.py` for the **download and checksum verification** (it already
does this — do not write new download code). Produce the JSONL PIT tape the
lab consumes (via `tools/vision_backfill.py` or a documented conversion of
data.py's output; record the exact mapping in RUNLOG — the lab store stays
JSONL per IMPLEMENTATION_LAYOUT). Scope: BTCUSDT 1h, a small development
window (e.g., 2-3 recent months; the universe is NOT extended — O-011 gate).
Requirements: tape hash reproducible across a re-run; idempotency (re-run
adds zero rows); `--audit` clean — monotonicity, venue-sequence gaps, payload
hashes, row counts vs source checksums. Real download is now **in scope**
(network allowed); tests still never touch the network.

### Step 3 — Materializations + lab on real tape (25 min)
Build the `DATASET_SPEC` §5 materialized views
(`market_states.parquet`, candidate views) with DuckDB from a pinned
`ExperimentManifest`. Run the lab pipeline on the real tape (state → experts
→ lifecycle → simulator) for **pipeline correctness only**: state hashes
reproducible, ledger hash deterministic, verdict stays
`NO_ECONOMIC_CLAIM`. Record the observed portfolio-rejection rate — it feeds
the O-017 threshold proposal in Step 4. Do not extend anything beyond the
locked baseline.

### Step 4 — `v8_slice_001` preregistration document (20 min)
Write `docs/PREREGISTRATION_V8_SLICE_001.md` with every field of the
`HYPOTHESIS_LAB_PROTOCOL` hypothesis record: formal null/alternative,
economic mechanism, universe as-of, data/source manifest, clocks,
canonical geometry and costs, dependence unit, primary metric, test,
minimum event/asset coverage, development/frozen partitions (chronological;
frozen holdout declared but **never touched**), and rejection consequence.
Include a proposed `execution_share` floor and population-divergence
threshold (O-017) derived from the Step-3 rejection rate. The document is
frozen content for the operator to approve — **do not run the experiment,
do not open the frozen holdout.**

### Step 5 — Status report (10 min)
Overwrite `docs/STATUS_REPORT.md` for session 2 (it is a session artifact,
not corpus — the probe byte-identity gate is unaffected) and append the
summary to `RUNLOG.md`. Commit `v8-step-N: ...` per step.

## Hard rules (session 1, unchanged)

1. **Docs freeze:** never edit existing `docs/` corpus files. You may append
   to `RUNLOG.md` (repo root) and write the two runbook-owned artifacts
   (`docs/STATUS_REPORT.md`, `docs/PREREGISTRATION_V8_SLICE_001.md`).
   Ambiguity → `OPEN_PIN` in RUNLOG, never a silent decision.
2. **Forbidden:** router, learned scorer, ranker, learned/RL execution,
   online learning, event-driven clock mode (rules 6/14); running
   `v8_slice_001` or any experiment; opening frozen OOS; profitability
   language (rule 12).
3. **Determinism:** no wall clock in `src/v8/`; integer nanoseconds;
   `sha1_hex` for every hash.
4. **Tests are the contract probes:** never weaken/skip a test; a gate
   failure is a code bug — fix the code.
5. **Commit protocol:** one commit per step, explicit file list (never
   `git add -A`), message `v8-step-N: <summary>`; never `--amend`, never
   force-push.
6. **Timebox:** 2h total; a step at 2x its timebox → `BLOCKED` in RUNLOG
   with evidence, move on. Always finish with `docs/STATUS_REPORT.md`.

## Gates — every step

1. `.venv/bin/python -m pytest tests -q` — green, count >= previous.
2. Monograph probe rebuild **byte-identical** to the Step-0 baseline hash.
3. Forbidden-scan: no `router|scorer|rank(er|ing)?|\bRL\b` in new code.
4. No wall clock in `src/v8/`.
5. Commit exists with `v8-step-N` message.

Begin with Step 0. On finish, report the RUNLOG path and STATUS_REPORT
location.
