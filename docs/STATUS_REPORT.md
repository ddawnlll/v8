# V8 Autonomous Build — Status Report (Session 3)

**Session:** complete all phases except Phase 4 (operator-owned)
**Date (UTC):** 2026-08-01
**Prepared by:** V8-build-agent (autonomous session 3)
**Read this first** (runbook step 7): this report is the operator's only
required reading. RUNLOG.md holds the full per-step evidence. This file is a
session artifact; it is not corpus and does not perturb the monograph probe.

---
**Follow-up (2026-08-06, adversarial audit + evidence-quality kaizen):** an
adversarial audit of the 27 expert families against their hypotheses and the
Handbook of Technical Analysis found and fixed three implementation bugs, one
methodological defect (D-052), and registered the version discipline for the
changed families (O-023/D-053). Five commits (`e8400bc`, `d923f39`, `2fd12b8`,
`566fcd8`, `cdcee12`); 628/628 tests pass; working tree clean.

- **Bug fixes (code now matches its own hypothesis):** failed_breakout two-step
  gate (Ch7.3 p228 breakout leg — the old gate fired on a plain downtrend);
  marketstate `_fib_levels` origin-based extensions (Ch10.5.1/10.5.2 — every
  level was one impulse-range off); volume_climax detection-bar anchor (distinct
  climaxes no longer collapse); fib swing-guard removal (gated on the wrong,
  significance-filtered pair).
- **D-052:** block-bootstrap block-size was bar-counts applied to an
  episode-indexed series; at block >= n the bootstrap collapsed to a point
  mass (`ci_lower == mu_hat`) and rejected H0 by construction. Now an
  n-adaptive episode-unit rate with a fail-closed non-degeneracy invariant and
  a stable tail index. Verified on the pinned baseline: spurious H0 rejections
  1 -> 0 (`obv_adl_regime` +0.0150 -> -0.3067).
- **Corrected dev-window picture (in-sample, not a claim):** with the fixes,
  NO family with n >= 30 shows a positive detrended lower bound. The previous
  "top-5 positive detR" table was substantially an artifact of the
  failed_breakout gate + negative drift + rule-16 exposure crowding (e.g.
  failed_breakout detrended +1.9 -> -10.2, liquidity_sweep +6.1 -> -6.3 once
  the spurious SHORTs stopped blocking its exposure slot). Verdict stays
  NO_ECONOMIC_CLAIM.
- **Version discipline (O-023/D-053):** failed_breakout stays v1
  (bug-completion, strict subset 369 -> 76); volume_climax and fib_projection
  are v2 challengers (the fixes add episodes a v1 gate could not produce);
  prereg §4 amended to the fixed failed_breakout predicate (legal pre-holdout).
- **Open decisions recorded:** O-022 (rule-16 exposure coupling means family
  results are not independent), O-023 (version discipline).
- **Operator action unchanged but now with amended prereg:** run `v8_slice_001`
  per the amended prereg when the frozen holdout (first two published months
  after 2026-07-01) is available. The prereg §4 amendment is pre-holdout and
  legal (§16); the holdout is still untouched and unopened.
- **OOS pipeline validated end-to-end (2026-08-06):** `tools/vision_backfill.py`
  downloaded the real 2026-07 archive from data.binance.vision, checksum-
  verified it, converted it to the PIT tape (744 1h klines + 93 funding rows,
  schema byte-identical to the dev tape), sorted and audited clean (0 gaps, 0
  duplicates), and its `tape_hash` (`3d59aa07…`) matches the runner's own
  `sha1_hex(AppendOnlyLog(...).read())` exactly — so the frozen manifest's
  `data_hash` can be taken from the backfill. The 2026-08 archive is NOT yet
  published (HTTP 404 on 2026-08-06), so the §13 two-month holdout (>= 1,400
  bars) cannot be assembled; July alone is 744 bars. When August publishes
  (expected ~early September, the ~1-month Vision publication lag), the
  experiment-time flow is: backfill both months into one tape -> record
  `tape_hash` as `data_hash` in the frozen manifest (`experiment_id
  v8_slice_001`, `universe ["BTCUSDT"]`, `interval 1h`, `start_ns` =
  HOLDOUT_ANCHOR_NS) -> run `tools/run_experiment.py --manifest <manifest>`.

**Follow-up (2026-08-01, full-program push D-040/D-042): Phases 1-4 CODE is
now 100% written.** The remaining Phase-4 work is the experiment RUN, which is
gated on the frozen holdout existing (prereg §13) — not on code.

- **Phase 2 (complete):** per-feature `input_lineage_hash` + `calculation_time`
  on every emitted feature; `FEATURE_GRAPH_VERSION`; `MarketState.provenance`
  {raw_manifest_hash, feature_graph_version, code_version}. Five groups remain
  declared with `requires:`. Suite goldens re-pinned (deliberate).
- **Phase 3 (complete):** `liquidity_sweep_reclaim_v1` third pilot (D-042);
  `breakout_retest`/`capitulation` registered DATA_BLOCKED until derivatives
  tape. Dev materialization re-pinned with 3 pilots (ledger `40d4f23a…`).
- **Phase 4 (code complete, run gated):** D-027 attribution-validity gating in
  `LabReport` (`execution_share` 0.25 / KS ≤ 0.20, stdlib-pure KS, verified
  against §15 diagnostics); `tools/run_experiment.py` (`v8_slice_001` runner:
  frozen-manifest validation, holdout hash recorded-before-evaluation, block
  bootstrap + Bonferroni, authority-first). The runner fails closed on an
  absent holdout — the experiment will be run when the first two published
  months after 2026-07-01 exist.
- Suite: 148 tests green; monograph rebuilt (32 sections).

---

## Summary

All phases except **Phase 4** are complete or explicitly blocked-by-design:

| Phase | Status | Where |
|---|---|---|
| 0 — Foundation | **DONE** | session 1 (corpus, contracts, slice) |
| 1 — Data plane | **DONE** (dev window) | session 2 (data.py + vision_backfill + tape + audit + materializations) |
| 2 — State engine | **DONE** | session 1-2 (feature groups, lineage, PIT) |
| 3 — Pilot experts | **DONE** | session 1 (registry, metadata, EXPERTS_REGISTRY.yaml) |
| 4 — First program gate | **OPERATOR-OWNED** | preregistration `v8_slice_001` RATIFIED 2026-08-01; experiment NOT run, frozen holdout NOT opened |
| 5 — Gated components | **BLOCKED BY DESIGN** | rule 12: never built without a surviving family from Phase 4; absence enforced as contract probes |
| 6 — Ops and hardening | **DONE** | this session (monitoring, observability, CI + golden regression, certification, status automation) |
| 7 — Learning plane | **BLOCKED BY DESIGN** | rule 12: only after certified edge; absence enforced as contract probes |

Session-3 gates held at every step: pytest green, non-decreasing count (50 →
80); monograph probe byte-identical to the session-3 baseline
`bc207925d828280de4b7b8d02d359b2f79da70ba58144cc9360b3ed059ba4c45`; no
forbidden component names in new `src/v8/`/`tools/` code; no wall clock in
`src/v8/`; one explicit-file-list commit per step.

## Session-3 steps

### Step 0 — Re-baseline — DONE
- Probe re-based to `bc207925…` (32 sections; operator closure commits
  `v8-step-10/11/12` promoted the ratified preregistration into the
  monograph); 50 tests; clean tree.
- Commit: `6e20a54`.

### Step 1 — Data-quality monitoring + structured observability — DONE
- `tools/monitor_tape.py`: FEED_INGESTION_SPEC §2 schema validation,
  integrity audit **reused** from `vision_backfill.audit_tape` (not forked),
  staleness alerting with injectable `--now`, structured JSON with
  `experiment_id`, fail-closed exits. Real-tape smoke: 2184 rows, verdict OK.
- Commit: `467bfcd`.

### Step 2 — Golden-backtest regression + CI — DONE
- `tests/test_golden_backtest.py`: pins ledger/data/states hashes, candidate
  count, terminal distribution (any decision-path refactor fails loudly,
  PERSISTENCE_REPLAY_SPEC §4). `.github/workflows/ci.yml`: pytest (incl.
  golden) + monograph byte-identity probe; injection-safe.
- Commit: `c0a72fa`.

### Step 3 — Certification record + artifact status + purity probes — DONE
- `research/certification/simulation_authority_certification_v1.json`:
  FAIL / BLOCKED / live unreachable (D-022). `tools/artifact_status.py`:
  research→shadow→paper→live with adjacent gates and required evidence.
  `tests/test_decision_path_purity.py`: the decision path is stdlib-only,
  clock-free, and contains no gated component (Phase 5/7 absence enforced as
  a property, not a convention).
- Commit: `6cc05d1`.

### Step 4 — Hardening from adversarial Phase-6 review — DONE
- Review workflow (3 read-only reviewers): 0 blockers, 20 warnings, all
  actionable ones fixed: monitor fail-closed on empty/missing tapes, bool
  timestamps rejected, CI `sha256sum`, and the **latent divergence** where
  `ExperimentManifest.fill_policy` was declared but ignored — the simulator
  now validates it (unsupported policies fail closed; single-code-path
  property of OPERATIONS_SPEC §1). 13 new tests (80 total).
- Commit: `5a4aa28`.

### Step 5 — Status report — DONE
- This file; commit `v8-step-5: status report`.

## Deviations and fixes (session 3)

| Item | Resolution |
|---|---|
| Monitor staleness crashed on empty tapes | Structured violation, fail-closed JSON |
| Monitor `--schema` failed open on empty tapes | Rejects with "cannot evaluate" |
| Bool passed the int-timestamp check | `type(x) is int` |
| Missing tape → bare traceback | Structured FileNotFoundError report |
| CI `shasum` (BSD) | `sha256sum` (portable) |
| `fill_policy` declared but ignored by the simulator | Wired through the manifest; unsupported → ValueError (fail closed); default byte-identical (golden unchanged) |
| OPERATIONS_SPEC items with no deliverable (conscious deviations) | Feed reconciliation N/A (single locked feed); CI lint/typecheck not configured (pytest + golden + probe at research scale); store-unreachable mid-run not simulated (local disk store); rollback/kill-switch N/A until shadow/paper exist (gated); counters/gauges minimal (JSON report, "do not over-invest") |

## Session 4 — Bugfix pass (2026-08-01)

A multi-modal bug hunt (4 finders + per-finding adversarial verification; 31
agents) returned 27 findings, 22 confirmed (1 critical, 5 high, 9 medium,
7 low), 5 refuted. All critical/high/medium code bugs were fixed in
`v8-bugfix` commits `a104652` + `3f9eae9`:

- **CRITICAL** — `vision_backfill` silently dropped corrected archives: a
  re-downloaded zip with revised bars (same open times) was deduped away
  while provenance recorded the new checksum. Now per-month provenance +
  fail-closed revision detection (`check_archive_revision`).
- **HIGH** — Phase-1a rejection counterfactual entered one bar late, biasing
  the D-027 rejected population; now mirrors the executed path (entry at the
  would-be fill bar).
- **HIGH** — `audit_tape` provenance checks failed open; source.json is now
  required and recorded archives must exist and match their sha.
- **LOW-wiring** — the D-024 DEGRADED veto was dead code; `build_state` now
  emits DEGRADED state quality when any feature is DEGRADED.
- **MEDIUM** — `data.py` no longer aborts on a geo-blocked exchangeInfo
  endpoint (degrades with a warning).
- Test gaps closed: materializer content assertions, funding end-to-end
  through `lab.run`, D-024 exact-boundary non-veto, non-vacuous purity tests,
  main-path corrupt-zip, plan_archives count. Golden bumped consciously
  (ledger `0d37dd96…`; data/tape hash unchanged).

**New open pins (operator/registry decision):**
- **D-026 anchor drift for >32-bar setups** — the key changes every bar and
  dedup silently never fires (documented in D-034 but violates the
  CANDIDATE_LIFECYCLE_SPEC §1 key-stability invariant). Not mechanically
  fixed; needs a registry decision on window/anchor semantics.
- **Detection-bar invalidation gap** — invalidation is never evaluated on the
  detection bar; no contract pins the window; a fix must be expert-aware.

## Open pins / operator actions

1. **Phase 4 (operator):** run `v8_slice_001` per the RATIFIED preregistration
   when the frozen holdout (first two published months after 2026-07-01) is
   available; record the holdout tape hash before any evaluation; provide an
   authority receipt before any economic verdict. Do not open the holdout
   before then.
2. **Phase 5 / 7 (blocked by design, rule 12):** the gated components
   (router, learned scorer, ranker, learned/RL execution, online learning)
   and the learning plane are never built without Phase-4 surviving-family
   evidence / certified edge; their absence is enforced by
   `tests/test_decision_path_purity.py`. Nothing was built for them.
3. **D-027 verdict gating in code** (carry-forward): `execution_share` +
   divergence + `ATTRIBUTION_UNSAFE_*` verdicts in `LabReport` land with the
   Phase-4 experiment runner; thresholds are preregistered (share 0.25,
   KS 0.20) and ratified.
4. **Golden maintenance:** updating `test_golden_backtest.py` goldens is a
   deliberate, reviewed act (PERSISTENCE_REPLAY_SPEC §4).

## Unfinished steps

None within the "all phases except Phase 4" scope. Phase 6 DoD is met
(operator tests green — 80 passed; certification record FAIL/BLOCKED
updated). Phase 5 and 7 are not unfinished work but gated, by design, on
evidence only Phase 4 can produce.
