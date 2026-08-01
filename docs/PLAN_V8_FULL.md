# V8 Full-Program Build Plan

**Status:** PROVISIONAL_DECISION (D-040, owner, 2026-08-01).

The v0.1-only framing is retired: the program target is the full 8-phase
roadmap with the evidence gates intact (`V8_CONSTITUTION` rules 5-6, 12, 14).
This file is a planning artifact (like `STATUS_REPORT.md`), not a monograph
section — it is not in `build_monograph.py` NAMES. Registering it as a
monograph section would require a TR mirror; the plan lives here to keep the
monograph build symmetric.

## Decision

- The roadmap (`docs/ROADMAP.md`) is the full program: Phases 0-7.
- "v0.1 = Phase 0-4 foundation" is a version label, not a program boundary.
  Each phase that admits a component bumps the version.
- Gates never move: Phases 5 and 7 are built **only when their evidence gate
  passes** — a preregistered, costed, frozen-OOS comparison, never a calendar
  date. `tests/test_decision_path_purity.py` keeps enforcing the absence of
  gated components in the decision path; any sprint must keep it green.
- The Phase-4 verdict stays `NO_ECONOMIC_CLAIM` until the holdout tape hash is
  recorded at download time and an authority receipt exists (rules 8-9, 12).

## Build order

### Decision record (done in this pass)

- `D-040` registered in `docs/decisions/DECISION_REGISTER.md`.
- `docs/CHANGELOG.md` entry; `docs/ROADMAP.md` versioning line updated.
- `docs/PLAN_V8_FULL.md` created (this file).

### Sprint A — Phase 4 critical path (buildable now)

1. `tools/run_experiment.py` — `v8_slice_001` runner: reads and validates the
   preregistration fields, loads the frozen holdout tape, fails closed if the
   holdout does not exist, runs both pilot experts against the no-trade
   baseline on frozen chronological OOS, applies family-level multiplicity
   control.
2. D-027 verdict gating — `LabReport` gains `execution_share` floor 0.25,
   population-divergence KS ≤ 0.20, `ATTRIBUTION_UNSAFE_*` flags and the
   automated verdict (thresholds ratified O-017).
3. Holdout tape hash recorded at download time + authority-receipt guard; a
   run without both never produces an economic verdict.
4. Tests: runner determinism, gate fail-closed, golden re-pin.

### Sprint B — Phase 2/3 completion

5. Full feature graph — five feature groups (trend, volatility, location,
   participation, response) with `requires:` declarations; per-feature
   lineage hashes; PIT tests (future rejection, bar-not-closed, revision
   replay).
6. `liquidity_sweep_reclaim_v1` + end-to-end lifecycle state machine;
   backlog experts (`breakout_retest`, `capitulation`) enter the registry as
   `DATA_BLOCKED` until derivatives tape.

### Sprint C — Phase 6 ops and hardening

7. Data-quality monitoring (schema checks, staleness/gap alerts), structured
   logging, CI with golden-backtest regression, fail-closed tests, simulation
   authority certification renewal path (`OPERATIONS_SPEC` §1), shadow/paper
   status automation.

### Data-blocked (not writable until external dependencies land)

- **Derivatives tape** — unlocks the two `DATA_BLOCKED` backlog experts
  (Sprint B item 6).
- **Holdout window** (first two published months after 2026-07-01) — the real
  `v8_slice_001` run; its outcome opens or permanently closes Phases 5 and 7.

## Definition of done per phase (unchanged from ROADMAP)

| Phase | DoD |
|---|---|
| 0 | Slice tests green; monographs build byte-identically (DONE 2026-08-01) |
| 1 | BTCUSDT 1h tape loads; audit passes; tape hash reproducible |
| 2 | Features on real data; state hashes reproducible |
| 3 | Experts run on real tape; contract tests green |
| 4 | Pipeline correctness on real data; first after-cost OOS estimates produced — not claims |
| 5 | Each component beats its immediately simpler baseline on frozen OOS, or is rejected |
| 6 | Operator tests green; certification record updated |
| 7 | Every learned component enters through the ExpertContract + a registry decision; no online mutation (rule 15) |

## Hard rules (from `AGENT_RUNBOOK` / constitution, still binding)

- Spec freeze on the corpus except this plan's own entries: the operator owns
  `docs/` edits; session artifacts stay in `STATUS_REPORT.md` / `RUNLOG.md`.
- One moving part at a time; complexity budget is a hard cap (rule 14).
- No experiment run, no frozen-OOS opening, no `--amend`, no `git add -A`.
- Determinism: no wall clock inside replay; the three clocks are never
  collapsed.
