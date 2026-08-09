# Audit repro baseline — 2026-08-07

Current working tree, before any fix. Every number is reproducible via
`.audit/repro/repro_N.py` (deterministic, no wall clock).

## Tree state

- HEAD: `8b7ac3a` v8-step: O-022 de-crowding response — gate selectivity, not retirement
- Code hash (decision path `src/v8/` minus `simtruth/`): `f422b3a5…`
- Uncommitted since HEAD: the state-builder fast path + store read cache
  (`lab.py`, `marketstate.py`, `store.py`) with `test_state_cache_identity.py`;
  golden test re-pinned to `6c33bc5d…`. **Full suite: 674 passed.**
- The issue-filed golden mismatch (`5be4e320` vs `6c33bc5d`) is STALE — the
  working tree golden test is green (`1 passed`), so issue #72's golden item is
  already resolved.

## Core economic baseline (real tape `btcusdt-1h-12m`, first 2500 bars, all 27 experts)

| population | n | mean net_R | win rate | total R |
|---|---|---|---|---|
| ALL SETUPS (offline, own geometry, lag=2, cost 0.07) | 8040 | **−0.0632** | 49.5% | −508.0 |
| ALL SETUPS (offline, 1R:1R override, cost 0.07) | 8040 | −0.0764 | 48.8% | −614.3 |
| ALL SETUPS (offline, 1R:1R, cost 0.00) | 8040 | −0.0064 | 49.7% | −51.5 |
| EXECUTED subset (through ExposureBook, cost 0.07) | 895 | **−0.1155** | 45.3% | −103.4 |
| EXECUTED subset (cost 0.00) | 895 | −0.0455 | 46.4% | −40.7 |

- Cost is a flat per-trade subtraction: mean(c) − mean(0) = −c exactly
  (verified −0.02/−0.04/−0.07). At shipped 0.07R, **91.6% of the all-setups
  mean loss is cost**; cost/raw-edge magnitude = **10.9×** (audit: 5.7×).
- Adverse selection: the executed subset is **1.83× worse** than the average
  setup (mechanism in #68).
- Note: the raw zero-cost edge is slightly negative on the current tree
  (−0.0064), not the audit's +0.0123 — cost is dominant, not sole.

## Per-issue reproduction verdict

| # | claim | verdict | headline evidence |
|---|---|---|---|
| 61 | cost ≫ edge | ✅ | cost/edge 10.9×; mean(c)−mean(0) = −c exactly |
| 62 | no trigger predicate | ✅ | 16/27 candlestick candidates triggered despite failing the book close-beyond-trigger test |
| 63 | stop = ATR multiple, not structural | ✅ | 33/33 drafts: |atr_stop − stop_ref| = 0.44R mean; 37.3% of executions have MAE > 1.0R |
| 64 | RR 1:1 + expiry 8 hardcoded | ✅ | 19/27 target_r=1.0; 27/27 expiry=8; w_min 52.8% vs realized 45.3% (7.6 pt gap) |
| 65 | preconditions 2/10 | ✅ | failed_breakout 2/10 conditions; 3.22 setups/bar |
| 66 | unbounded prior → dead invalidation | ✅ | 6 experts, 2067 drafts, **7 invalidation fires total (~0.3%)**; stale extremes (18 bars) |
| 67 | trigger_ref inert in runner | ✅ | 2/4 entered candidates violated the trigger predicate; trigger_ref in episode_key, no runner consumer |
| 68 | adverse selection + alphabetical race | ✅ | executed −0.1155 vs all −0.0632 (1.83×); **295/303 contended slots won by alphabetically-first expert (97.4%)**; top-2 alphabetical = 38% of executions |
| 69 | threshold below real cost | ✅ | 0.10R ≈ 4.8 bps < realistic taker 6 bps; at cost 0.125: **0 executed, 6209 excess_cost rejects** |
| 70 | geometry invariants unenforced | ✅ | target_r=−1 → endpoint=TARGET, net −1.07; stop_r=0 accepted; no validation in step/run |
| 71 | gap asymmetry | ✅ | −30 gap: STOP −3.07R; +30 gap: TARGET +0.93R (3.30R asymmetry); tape gap rate 0.6% |
| 72 | synth gaps unrealistic | ✅ | synth gap_frac 73.0% vs real 0.6%; open==prev_close 0% vs 51.7% |

## Mechanistic details captured

- **#68 contention**: alphabetical-first expert wins 97.4% of same-bar
  same-direction slot races. bollinger_breakout executes 25.9% of its signals
  vs volume_climax_reversal 5.5% — both more frequent AND preferentially
  admitted.
- **#67 identity**: removing trigger_ref from geometry changes episode_key for
  33/33 candlestick drafts (field is identity-bearing but behavior-inert).
- **#70**: 9 expert files guard their own geometry; simulator/lab/schema have
  zero guards. bollinger_reversion Setup 3 RR=0.5 → 69% breakeven win rate.
- **#71**: gap asymmetry is conservative-by-design (documented in simulator
  docstring); magnitude 3.30R on a synthetic +30/−30 gap.
- **#72**: golden test green on working tree; the audit's synth-bias claim
  (%40 ATR underestimate) was measured against the OLD tree.

## Test suite

`674 passed in 63.24s` on the working tree. `tests/test_golden_backtest.py` green.

## What "fixed" will be compared against

For each fix, the same repro script re-runs and the delta is reported. The
economic headline: executed-subset mean net_R / win rate / total R on the same
2500-bar window, plus the trigger funnel (#62), MAE>1R fraction (#63),
contended-slot neutrality (#68), and the synth continuity stats (#72).
