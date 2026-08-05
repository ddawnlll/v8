# V8 Agent Runbook — autonomous build contract (Phase 0-3)

**Status:** PROVISIONAL_DECISION. This is the execution contract for a
time-boxed autonomous coding session (target: ~2 hours) that builds the V8
research runtime from Phase 0 to Phase 3. It is a construction plan, not a
research plan: **no experiment is run, no frozen holdout is opened, and no
economic claim is produced or asserted.** Gated components are forbidden
(`V8_CONSTITUTION` rules 6, 14).

Read order for the agent: `CLAUDE.md` -> this runbook -> the owning contract
of the step you are on -> `IMPLEMENTATION_LAYOUT.md` -> the code. `site/*` is
**generated** — never hand-edit it; rebuild it and prove byte-identity.

## 0. Hard rules (violating any of these ends the session)

1. **Spec freeze:** never edit anything under `docs/` except appending to
   `RUNLOG.md` (repo root) and writing `docs/STATUS_REPORT.md` in the final
   step. Contracts, registers, and this runbook are read-only inputs. If a
   contract is ambiguous, record it in RUNLOG as an `OPEN_PIN` and implement
   the runbook's pinned interpretation — do not invent a new one.
2. **Forbidden components:** router, learned scorer, ranker, learned/RL
   execution, online learning, event-driven clock mode. Do not create files
   or parameters for them (rules 6, 14; `OPEN_DECISIONS` O-004/005/006/008).
3. **No experiment runs:** do not open frozen OOS, do not run `v8_slice_001`,
   do not claim or imply profitability. All runs use synthetic tape or the
   Phase-1 tape for **pipeline correctness only** (rule 10).
4. **Determinism:** no wall clock in `src/v8/` (`time.`, `datetime.now`);
   integer nanosecond clocks; `sha1_hex` for every hash
   (`PERSISTENCE_REPLAY_SPEC` §4).
5. **Decision path is stdlib-only:** `numpy` may be touched only in
   `simtruth/` and research tooling; never in the decision path.
6. **Tests are the contract probes:** never weaken, delete, or skip an
   existing test to make it pass. A gate failure is a code bug — fix the
   code, keep the test.
7. **Commit protocol:** one commit per step, immediately after its gate
   passes: `git add <explicit file list>` then
   `git commit -m "v8-step-N: <summary>"`. Never `--amend`, never force-push,
   never `git add -A`. Every step must end with a commit.
8. **Timebox:** each step has a timebox (wall clock). If a step exceeds 2x
   its timebox, mark it `BLOCKED` in RUNLOG with evidence, stop working on
   it, and continue with the next independent step. The session ends with
   `docs/STATUS_REPORT.md` regardless of how many steps finished.

## 1. Pre-flight gate (before any code)

```bash
.venv/bin/python -m pytest tests -q          # must be 15 passed
.venv/bin/python tools/build_monograph.py --lang en --docs docs --out /tmp/v8_index_probe.html
shasum -a 256 /tmp/v8_index_probe.html site/index.html   # must be identical
```

Record both hashes and the test count in `RUNLOG.md` as the baseline row.
The baseline commit already exists (operator-taken as `v8-step-0: initial
commit`); verify it and a clean tree:

```bash
git log --oneline -1        # expect the operator baseline commit
git status --short          # expect an empty output (clean tree)
```

If unexpected diffs appear, record them as a `DEVIATION` in RUNLOG and commit
them with an explicit file list before starting Step 1.

**Gate:** tests green, probe rebuild byte-identical, tree clean.

## 2. Steps

Every step ends with: pytest green, monograph probe rebuild byte-identical
to baseline (proves no contract changed), RUNLOG entry, commit.

### Step 1 — D-026: episode_key anchored to setup_anchor_event_id (40 min)

**Owns:** `src/v8/marketstate.py`, `src/v8/schema.py`, `src/v8/lifecycle.py`,
`src/v8/lab.py`, `src/v8/experts/*`, `tests/test_vertical_slice.py`.
**Spec:** CANDIDATE_LIFECYCLE_SPEC §1 (key formula, D-026) and §5 (key
stability test); IMPLEMENTATION_LAYOUT §4 divergence row 1.

Pinned interpretation (implement exactly, do not redesign):

- `MarketState` gains a `history` feature group: per symbol, the last 32
  closed bars as a tuple of `(event_id, open, high, low, close)` with
  per-bar `ema_fast`/`ema_slow`, computed by `build_state` (it already has
  the series). Feature name `{sym}.history`, `feature_version='v2'`.
- `CandidateDraft` gains `setup_anchor_event_id: str`.
- `setup_anchor_event_id` is defined as **the `event_id` of the first closed
  bar of the current consecutive run in which the Expert's setup predicate
  holds** — found by scanning `history` from newest to oldest for the newest
  bar where the predicate is false; the anchor is the next bar after it. If
  no false bar exists in the window, the anchor is the oldest bar in the
  window (documented bound: anchors older than 32 bars are unstable; the
  suppression window of 6 bars is far inside it).
- `episode_key(expert_id, expert_version, instrument, direction,
  setup_anchor_event_id, geometry_version)` — **no birth timestamp**. Update
  `lifecycle.py` and every caller in `lab.py`.
- `CandidateRegistry.is_duplicate(key)` returns True iff the key already
  produced a `DETECTED` episode; the time-window parameter is removed
  (anchor equality subsumes it; keeping both would double-suppress).
  Suppressed repeats are logged `SUPPRESSED_DUPLICATE` exactly as today.
- Both pilot Experts implement their predicate per history bar (trend
  pullback: `ema_fast > ema_slow and close < ema_slow`; failed breakout:
  `close < prior_high` with per-bar prior high) and set the anchor on every
  emitted draft.

**New tests:** (a) key stability — one unchanged setup on two consecutive
decision clocks yields the same `episode_key`; (b) a fresh setup (new anchor
event) yields a different key; (c) a repeat inside the window is logged
`SUPPRESSED_DUPLICATE`, not dropped. **Gate:** all pass; existing
`test_episode_key_deterministic_and_dedup_window` updated to the new
signature (its assertion intent — determinism + dedup — is preserved).

### Step 2 — Funding settlement in the canonical simulator (30 min)

**Owns:** `src/v8/simulator.py`, `src/v8/schema.py`, `src/v8/lab.py`,
`tests/test_vertical_slice.py`.
**Spec:** SIMULATION_TRUTH_SPEC §3 event order #5 (`SETTLEMENT_BEFORE_ORDERS`)
and §4 required goldens (funding exactly on start/end boundaries; full-tape
vs window replay).

Pinned interpretation:

- `ExperimentManifest` gains `funding_rate_r: float = 0.0` and
  `funding_hours: int = 8`. The funding schedule is a versioned venue input;
  boundaries are integer hours UTC divisible by `funding_hours` (default:
  00/08/16 UTC).
- The simulator settles **before** any order event of a bar whose decision
  clock crosses a boundary while the position is held: `net_r` is reduced by
  `funding_rate_r` per settlement, a distinct ledger event `funding_settled`
  is appended, and the position record counts settlements. Longs pay when
  the rate is positive (sign-adjusted by direction).
- Golden tests: (a) a hold spanning exactly one boundary books exactly one
  `funding_settled` and `net_r` is reduced by `funding_rate_r`; (b) a hold
  starting or ending exactly on a boundary settles exactly once; (c)
  window-replay of a hold equals full-tape replay for the same window;
  (d) `funding_rate_r = 0.0` leaves today's numbers byte-identical
  (simulator hash bumped to `canonical-sim-v4` regardless, since the policy
  changed).

**Gate:** all golden tests pass; `test_stop_out_is_exactly_minus_one_r`
etc. still pass.

### Step 3 — D-024 mechanical tradability mask (20 min)

**Owns:** `src/v8/marketstate.py`, `src/v8/schema.py`, `src/v8/lab.py`,
`src/v8/risk.py`, `tests/test_vertical_slice.py`.
**Spec:** CANDIDATE_LIFECYCLE_SPEC §6 item 3 (D-024).

Pinned interpretation:

- Manifest constants (no fitting, no leakage): `max_bar_range_frac: float =
  0.05`, `funding_window_bars: int = 1`.
- A candidate is vetoed at admission with
  `reason_code = TRADABILITY_MASK_VETO` (kept counterfactual,
  `NOT_EXECUTED`) when any of: `(high-low)/close > max_bar_range_frac` on the
  entry bar (detail `BAR_RANGE`); `StateQuality == DEGRADED` at decision time;
  entry bar within `funding_window_bars` of a funding boundary.
- The mask is data-plane, not a regime filter: implemented as deterministic
  vetoes in `RiskGate`-adjacent admission logic (lab), adding no degrees of
  freedom and no learned component.

**New tests:** veto fires on a spread-tail bar; veto fires in a funding
window; vetoed candidates keep a `NOT_EXECUTED` counterfactual outcome;
thresholds at defaults do not veto the synthetic baseline run.

### Step 4 — Phase 1 data plane: vision_backfill.py + tape audit (30 min)

**Owns:** `tools/vision_backfill.py` (new), `tools/data.py` (reuse),
`tests/test_tape_audit.py` (new).
**Spec:** FEED_INGESTION_SPEC §5 (Vision layout, checksums, idempotency),
§4 (gaps, duplicates); ROADMAP Phase 1.

Pinned interpretation:

- `tools/vision_backfill.py`: CLI `--symbol BTCUSDT --interval 1h --month
  2025-01 --out <dir>`; downloads `BTCUSDT-1h-2025-01.zip` + `.CHECKSUM`
  from `data.binance.vision`, verifies the checksum, unzips, and converts
  the CSV to a PIT tape (JSONL) **reusing `tools/data.py`'s row-building
  logic** (import it; do not fork it).
- Audit mode (`--audit`): monotonicity of `(event_time, available_time,
  venue_sequence)`, gap detection on the venue sequence, row counts and
  payload hashes vs source checksums; report, exit non-zero on violation.
- Idempotency: a second run over the same output dir must not duplicate rows
  (inbox dedup already exists in `store.py`); the audit compares pre/post
  hashes.
- Network is never required by tests: offline tests use a tiny fixture zip
  with a `.CHECKSUM`; the download path is exercised only with an explicit
  `--download` flag.

**Gate:** offline audit tests pass; double-run idempotency test passes.
(Real download is out of the gate; it is a manual operator step.)

### Step 5 — Phase 2 state engine: feature groups + lineage (20 min)

**Owns:** `src/v8/marketstate.py`, `src/v8/schema.py`, `tests/`.
**Spec:** MARKET_STATE_CONTRACT §2/§5; DATASET_SPEC §1/§5; ROADMAP Phase 2.

Pinned interpretation:

- Feature groups `trend, volatility, location, participation, response` with
  `requires:` declarations; every emitted feature carries
  `feature_version` and joins a lineage hash (already present — extend to
  the new `history` group and to per-group tags).
- PIT tests on real tape (Phase-1 output if present, else synthetic):
  future rejection, bar-not-closed exclusion, revision replay (as-of rebuild
  reproduces the prior state hash).
- Materialization scripts (parquet views, DATASET_SPEC §5) are **deferred**:
  O-009 keeps the smallest engine (JSONL) at slice scale; do not add
  DuckDB/parquet dependencies in this session.

**Gate:** PIT tests pass; state hashes reproducible across two builds.

### Step 6 — Phase 3 expert metadata + registry (20 min)

**Owns:** `src/v8/experts/*`, `docs/EXPERTS_REGISTRY.yaml` (new),
`tests/`.
**Spec:** EXPERT_PROTOCOL §1 (ontology fields), §4 (status lifecycle);
ROADMAP Phase 3; constitution rule 13.

Pinned interpretation:

- `Expert` base gains `mechanism_family_id`, `behavior_family_id`,
  `variant_id`; both pilots declare them (trend pullback:
  mechanism `trend_continuation`, behavior `pullback_in_trend`; failed
  breakout: mechanism `liquidity_vacuum_reentry`, behavior
  `failed_breakout_reentry`; `variant_id = 'a'`).
- `docs/EXPERTS_REGISTRY.yaml`: one entry per pilot with the four ids,
  status `FORMALIZED`, owning spec reference, and the status vocabulary
  (PROPOSED -> FORMALIZED -> SCREENING -> REPLICATION -> SHADOW ->
  PROMOTED; REJECTED/MERGED/QUARANTINED/DATA_BLOCKED).
- Experts run on the Phase-1 tape (if present) or synthetic tape; contract
  tests green. No registry experiment is registered and nothing is
  promoted.

**Gate:** registry YAML parses; contract tests green.

### Step 7 — Status report (10 min)

Write `docs/STATUS_REPORT.md`: per step (DONE/BLOCKED/SKIPPED), evidence
commands and outputs, commit hashes, every deviation and fix, the open
pins, and a ranked list of unfinished steps. Append the same summary to
`RUNLOG.md`. Commit `v8-step-7: status report`. **This report is the
operator's only required reading.**

## 3. Ownership map (responsibility)

| File family | Built by | Guarded by |
|---|---|---|
| `src/v8/schema.py`, `marketstate.py` | Step 1, 3, 5 | PIT + key-stability + mask tests |
| `src/v8/lifecycle.py` (episode identity) | Step 1 | key-stability + dedup tests |
| `src/v8/experts/*` | Step 1, 6 | contract tests + registry parse |
| `src/v8/simulator.py` | Step 2 | funding goldens + existing R goldens |
| `src/v8/risk.py`, `lab.py` (admission) | Step 3 | mask veto tests |
| `tools/vision_backfill.py`, `tools/data.py` | Step 4 | offline audit + idempotency tests |
| `tests/*` | every step | pytest gate |
| `docs/EXPERTS_REGISTRY.yaml` | Step 6 | YAML parse test |

## 4. Gate checklist (every step)

1. `.venv/bin/python -m pytest tests -q` — all green, count >= previous.
2. Monograph probe rebuild byte-identical to baseline hash (proves `docs/`
   untouched): `shasum -a 256 /tmp/v8_index_probe.html`.
3. No forbidden component names appear in new code (`router|scorer|ranker|RL`).
4. No wall clock in `src/v8/`.
5. RUNLOG entry written; commit created with `v8-step-N` message.

## 5. Pinned implementation decisions (D-034/035/036)

These interpretations are registered in `DECISION_REGISTER.md` and are
PROVISIONAL. The agent implements them; it does not revisit them. Any
discovery that contradicts a contract must be reported as an `OPEN_PIN` in
RUNLOG, not silently resolved.

## 6. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** runnable vertical-slice gates are the
  audit's demanded response (`PROJECT_EVIDENCE_AUDIT` §2); the V7 funding
  boundary defect was caught only by differential replay
  (`PROJECT_EVIDENCE_AUDIT` §2).
- **DESIGN_INFERENCE:** the step order, gates, commit protocol, and pinned
  interpretations are V8 choices that make an autonomous session auditable;
  nothing here is an economic claim.
