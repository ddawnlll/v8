# V8 Autonomous Build — Status Report (Session 2)

**Session:** runbook steps 0-5, Phase 1 on real data + `v8_slice_001`
preregistration
**Date (UTC):** 2026-08-01
**Prepared by:** V8-build-agent (autonomous session 2)
**Read this first** (runbook step 7): this report is the operator's only
required reading. RUNLOG.md holds the full per-step evidence. This file is a
session artifact (overwritten from session 1); it is not corpus and does not
perturb the monograph probe.

---

## Summary

All 5 session-2 steps are **DONE**. Phase 1 was executed on real data
(BTCUSDT 1h, 2026-04..06), the decision-ledger + DATASET_SPEC §5
materializations were built and run, and the `v8_slice_001` preregistration
was written, adversarially reviewed, and amended. No contract under `docs/`
was edited; the monograph probe is byte-identical to the session-2 baseline
(`ea5b770528fb07931ff08801e4704a4fefca3586d88da1277a75311ccb075def`) at every
step. The suite grew 42 -> 50 tests.

**Gates held at every step:** pytest green, non-decreasing count;
monograph probe byte-identical; no forbidden component names in new code; no
wall clock in `src/v8/`; one explicit-file-list commit per step.

**Forbidden scope respected:** no router, learned scorer, ranker, learned/RL
execution, online learning, or event-driven clock mode was created. The
experiment `v8_slice_001` was **not** run, the frozen holdout was **not**
downloaded or opened, and no profitability language or economic claim appears
anywhere (verdict stays `NO_ECONOMIC_CLAIM`; rules 8-9, 12).

## Steps

### Step 0 — Pre-flight (new baseline) — DONE
- Evidence: pytest `42 passed`; probe rebuild -> **new baseline**
  `ea5b770528fb07931ff08801e4704a4fefca3586d88da1277a75311ccb075def` (31
  sections — the session-1 hash `65eef39f…` is stale after operator closure
  `76ef874`); TR probe `2c5b973a…`; clean tree; Session-2 header opened in
  RUNLOG.
- Commit: `3436248` `v8-step-0: session-2 preflight …`.

### Step 1 — Tooling deps + data.py path — DONE
- Evidence: `uv pip install -e ".[tooling]"` -> polars 1.43.1, pyarrow
  25.0.0, pandera[polars], duckdb 1.5.5; pytest `46 passed` (+4 offline
  tooling-path tests); `tools/data.py build/verify/audit` on BTCUSDT 1h
  2026-06 -> VERIFIED / PASS / PASS (720 rows, duplicate PKs 0).
- OPEN_PIN (operator): register the D-037 tooling admission decision
  (heavy deps admitted for Phase-1 parquet materialization; decision path
  stays stdlib-only, O-009).
- Commit: `a9bd373` `v8-step-1: …`.

### Step 2 — Real tape: download + PIT tape + audit — DONE
- Evidence: `data.py build` (2026-04-01..2026-07-01, BTCUSDT 1h, klines,
  `--keep-raw`) -> VERIFIED, 3 archives, 2184 rows, verify/audit PASS;
  `vision_backfill` (no `--download`, consuming data.py's verified archives)
  -> JSONL PIT tape, 2184 rows, audit
  `{"monotonic": true, "payload_hashes_ok": true, "row_count": 2184,
  "venue_gaps": 0}`; re-run idempotent (0 appended), tape hash stable
  `8b12707e0d89f2a955d2badccf9f278267c0e086`; lab PIT replay + build_state on
  real data OK. Universe NOT extended (O-011).
- Commit: `5304289` `v8-step-2: …`.

### Step 3 — Materializations + lab on real tape — DONE
- Evidence: pytest `50 passed` (+4: decision-ledger states, birth snapshot,
  materializer roundtrip, fail-closed hash mismatch). Code: lab persists the
  MarketState decision ledger (`states.jsonl`, bound into ledger_hash);
  DETECTED transitions carry the immutable birth snapshot
  (`CandidateRegistry.apply(extra=…)`); new `tools/materialize_views.py`
  writes the five DATASET_SPEC §5 parquet views with DuckDB from a pinned
  manifest, failing closed on live code/data hash mismatch. Real-tape run
  (pinned manifest `manifest_dev.json`, code_hash `6a2b024e…`, data_hash
  `8b12707e…`): views {market_states 2184, candidate_birth 713,
  candidate_trigger 706, candidate_outcomes 713, execution_trajectories
  2900}, ledger_hash `2c1e0fd8…`, verdict `NO_ECONOMIC_CLAIM`. Determinism:
  two fresh runs -> equal ledger + states hashes. O-017 baseline:
  n_executed 256, n_portfolio_rejected 360 (all EXISTING_EXPOSURE_CONFLICT),
  mask vetoes 90 (all FUNDING_WINDOW), execution_share = 0.4156; executed vs
  portfolio-rejected net_R KS = 0.073.
- OPEN_PIN (carry-forward): D-027 verdict gating (execution_share +
  divergence stat + ATTRIBUTION_UNSAFE_* verdicts in LabReport) is
  unimplemented in code; thresholds are preregistered (§15 of the
  preregistration); the code gate lands with the Phase-4 experiment runner.
- Commit: `8c10730` `v8-step-3: …`.

### Step 4 — v8_slice_001 preregistration document — DONE
- Evidence: `docs/PREREGISTRATION_V8_SLICE_001.md` written with all
  HYPOTHESIS_LAB_PROTOCOL hypothesis-record fields; O-017 thresholds proposed
  pre-holdout from the Step-3 baseline (execution_share floor 0.25 = 60% of
  observed 0.4156; KS divergence threshold 0.20 ≈ 2.7× observed 0.073).
  Adversarial verification workflow (4 read-only critics) -> AMEND; 1 blocker
  + 7 warnings incorporated: two-month frozen OOS (≥1,400 bars) now satisfies
  the §12 minimum; 9-bar label-horizon extension pinned (unobservable
  episodes RIGHT_CENSORED); Bonferroni-only α_f=0.025 with percentile one-sided
  CI; EMA periods + parameter provenance declared; cost locked; block-size
  rule operationalized; ledger_hash reclassified as derived output;
  candidate_trigger 706 added; mask-veto exclusion cited by principle.
  Experiment not run; holdout not opened.
- Commit: `c2e64fd` `v8-step-4: …`.

### Step 5 — Status report — DONE
- This file; summary appended to RUNLOG.md; commit `v8-step-5: status report`.

## Deviations and fixes (complete list)

| Step | What | Resolution |
|---|---|---|
| 1 | Heavy deps absent; `data.py` hard-exited at import | D-037 admission: `uv pip install -e ".[tooling]"`; `tooling` extra added to pyproject (decision path stays stdlib-only) |
| 3 | DATASET_SPEC §1 layer 2: MarketState not persisted | Lab writes `states.jsonl` (one record per bar); bound into ledger_hash |
| 3 | CANDIDATE_LIFECYCLE_SPEC §1: no immutable birth record | DETECTED transition carries expert/geometry/state birth fields via `apply(extra=…)`, merged before append |
| 3 | Materializations could silently go stale | `materialize_views.py` fails closed on live code/data hash mismatch |
| 4 | Preregistration §12 vs §13 OOS-window contradiction (review blocker) | OOS re-declared as the first two published months after 2026-07-01 (≥1,400 bars) |
| 4 | Label-horizon at holdout end unaddressed (review warning) | 9-bar extension pinned; RIGHT_CENSORED rule declared |
| 4 | Unpinned FDR/CI procedure (review warning) | Bonferroni-only; percentile one-sided CI (2.5th percentile) |
| 4 | Missing EMA periods / provenance; provisional cost label; block-size rule; ledger_hash classification; candidate_trigger count; mask-veto citation (review warnings) | All incorporated into the frozen document |

## Open pins (unresolved, operator action)

1. **Register the D-037 tooling admission** (Step 1): polars/pyarrow/
   pandera[polars]/duckdb installed and declared in the `tooling` extra for
   Phase-1 parquet materialization; decision path unchanged.
2. **D-027 verdict gating in code** (carry-forward): `LabReport` does not yet
   compute `execution_share`/divergence or emit `ATTRIBUTION_UNSAFE_*`
   verdicts; thresholds are preregistered for `v8_slice_001` (§15) and the
   gate lands with the Phase-4 experiment runner.
3. **Operator approval of `v8_slice_001`** (preregistration §16): (a) ratify
   the O-017 thresholds (share 0.25, KS 0.20); (b) at experiment time record
   the frozen-holdout tape hash before any evaluation; (c) provide an
   authority receipt before any economic verdict.
4. **Session-1 OPEN_PIN (data.py reuse) — RESOLVED** by operator closure
   `76ef874` (D-037) and this session's admission.

## Unfinished steps

**None.** All session-2 steps 0-5 are DONE within the 2-hour wall clock.
Phase-1 DoD is met for the dev window (tape loads, audit passes, tape hash
reproducible, materializations built); Phase 4 is *preregistered*, not run —
the frozen holdout is declared and untouched.

## Session artifact

- `RUNLOG.md` (repo root): full per-step entries with commands, output tails,
  fixes, commits, gates (Session 1 + Session 2 sections).
- Session-2 commits: `3436248` (0), `a9bd373` (1), `5304289` (2),
  `8c10730` (3), `c2e64fd` (4), and `v8-step-5: status report`.
- Derived artifacts (gitignored, reproducible): `research/tape/btcusdt-1h-
  2026-q2/` — dataset/ (verified parquet + manifest/audit), raw/ (archives +
  checksums), tape/ (JSONL PIT tape + source.json), views/ (five §5 parquet
  views + views_manifest.json), manifest_dev.json.
