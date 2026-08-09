# Audit-fix results — 2026-08-07

Before → after on the SAME dev window (real tape `btcusdt-1h-12m`, first 2500
bars, all 27 experts, `round_trip_cost_r=0.07`). Baseline: `.audit/BASELINE.md`.
Fixed-tree evidence: `.audit/repro/out/N.fixed.json` (one per issue).

## Headline economics

| metric | pre-fix | post-fix | delta |
|---|---|---|---|
| executed n | 895 | 845 | −50 (selectivity) |
| executed mean net_R | −0.1155 | **−0.0929** | **+0.0226R (+19.6% less negative)** |
| executed win rate | 45.3% | **46.9%** | +1.6 pt |
| executed total R | −103.4 | **−78.5** | **+24.9R (+24.1% less loss)** |
| FEASIBILITY note (w_min vs realized) | absent | present | new surfacing |

The system stays net-negative: cost dominance (#61) is structural — 0.07R cost
at a ~1×ATR barrier — and the fixes improved the quality of what executes
without changing the barrier scale (explicitly not an optimization pass). The
report now SAYS this (RM-11 feasibility note).

**Bright spot:** the 75 executed positions whose drafts declare a structural
stop (`stop_ref`) are **positive**: mean **+0.131R**, win rate **53.3%**, total
**+9.83R**. The structural-stop subset is the best-performing population in the
system — the direction the barrier-scale fixes point at.

## Per-issue fix verification

| # | claim | fixed | key before → after |
|---|---|---|---|
| 61 | cost ≫ edge | surfaced | cost sweep unchanged (deliberately); FEASIBILITY note now in report; cost/edge 10.9× recorded (D-063, O-025) |
| 62 | no trigger predicate | ✅ | candlestick TRIGGERED 27 → 18 (only close-confirmed); executed 4 → 2; no candidate enters without close-beyond-trigger |
| 63 | stop not structural | ✅ | step() uses stop_ref (33/33 drafts fire at stop_ref; 14/33 have a wider-than-ATR structural stop); stop-ref subset n=75 mean **+0.131R** win 53.3% |
| 64 | RR/expiry hardcoded | gate surfaced | geometry NOT swept (D-062); w_min 0.528 vs realized 0.469; gap narrowed 7.57 → 5.94 pt; FEASIBILITY note |
| 65 | preconditions 2/10 | recorded | O-024 registered; setup inflation unchanged (challenger decision, rule 12) |
| 66 | dead invalidation | ✅ | 6 no-ref experts: **7 → 140 invalidations** (~20×; 0.34% → 6.77% of drafts); terminal INVALIDATED 2346 → 2476 |
| 67 | trigger_ref inert | ✅ | PHASE 2 consumes trigger_ref; trigger-predicate violations 2/4 → **0/2** |
| 68 | alphabetical race | ✅ | contended slots alphabetical share **97.4% → 43.8%** (134/306); adverse selection **1.83× → 1.50×**; executed redistributed (bollinger_breakout 258 → 169) |
| 69 | threshold below cost | surfaced | cost 0.125 → 0 executed + FEASIBILITY note (was silent rejection) |
| 70 | invariants unenforced | ✅ | target_r≤0 / stop_r≤0 / expiry<1 fail closed (ValueError); bollinger Setup 3 RR=0.5 breakeven 69% documented (D-061) |
| 71 | gap asymmetry | recorded | conservatism budget 3.30R documented in SIMULATION_TRUTH_SPEC; semantics unchanged (deliberate) |
| 72 | synth gaps | ✅ | continuous variant gap_frac **73% → 3.7%** (real 0.6%); legacy default byte-identical (golden green) |

## Verification state

- Verify workflow (`.audit/repro/workflow_verify.js`): **12/12 issues fixed=True,
  0 agent errors**. Every claim re-run on the fixed tree and the delta measured
  (evidence `.audit/repro/out/N.fixed.json`).
- Full test suite: **686 passed** (was 674) — 12 new regression tests in
  `tests/test_audit_fixes.py` + the contention tie-break test rewritten.
- Golden regression: re-pinned `6c33bc5d…` → `699ae060…`; data_hash,
  candidate_count (15), terminal_distribution UNCHANGED.
- Determinism: two identical lab runs produce identical ledgers
  (hash `522d2960…` twice); every measurement is reproducible via
  `.audit/repro/repro_N.py` (fixed seeds, no wall clock).
- Monographs rebuilt (EN `site/index.html`, TR `site/tr.html`).

## Honest limitations

- The economics are still net-negative — cost dominance (#61) is not "fixed",
  it is measured and surfaced. The feasibility notes now state it explicitly;
  the structural-stop subset (+0.13R) is the evidence for the barrier-scale
  direction (D-062's structural targets, not a wider R).
- #65's precondition gaps remain (registered as O-024, challenger-gated).
- #71's gap asymmetry stays (conservative by design; budget documented).
- #72's legacy synth default stays gap-y (D-064 defers the flip for a
  scheduled 30-file re-pin).
- The candlestick `trigger_ref`/`trigger_side` entry contract has one pilot;
  other literature families' triggers (sweep-reclaim, retest, pullback) are
  not yet declared.
