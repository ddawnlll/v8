# Swing performance review — bounded 128-bar decision frames

Owner-reactivated v8-next scope (see `v8-next/AGENTS.md` 2026-09-11 correction).
No strategy, execution, sizing, funding or reconciliation semantics changed.
No economic claim. Synthetic data only in MECHANICS ONLY unit tests.

## Modified files

- `v8-next/src/v8_next/adapters/swing_engine.py` — bounded fast path restricted
  to the proven `plain_swing` / `range-breakout-48-v1` / `squeeze:baseline:v2`
  combination (`SWING_FRAME_WINDOW_BARS = 128`, `_fast_path_eligible()`,
  `_decision_frame()` with exact `frame_at` fallback; `on_bar()` latches
  continuity, regular duration, foreign instrument, late/missing availability
  and duplicate starts permanently).
- `v8-next/tests/test_swing_engine_perf.py` — production-path parity/causality
  regressions (11 tests, no duplicated algorithm, no vacuous asserts).
- `v8-next/tools/swing_perf_review.py` — tracked reproduction candidate.
- `artifacts/swing-performance-review/` — original profiling tooling + raw
  outputs preserved on disk (git-ignored): `measure_swing.py`,
  `compare_swing.py`, `decision_scaling.py`, `bounded_parity.py`,
  `baseline-*.summary.json`, `optimized-*.summary.json`, `parity-*.json`,
  `bounded-parity-*.json`. Only small summaries/hashes are quoted here; large
  event logs are not copied into tracked docs.
- This report: `docs/evidence/swing-performance-review/report.md`.

Unrelated owner changes preserved (no reset/stash/revert/commit/push/merge).

## Method (fixed config, explicit timeouts)

- Tape: `research/tape/multi-1h-4y/tape.jsonl` (real Binance capture).
- Instrument: `BTCUSDT` → `BTCUSDT-PERP.BINANCE`, 1-hour bars.
- Policy: `plain_swing` (`range-breakout-48-v1` + `squeeze:baseline:v2`),
  identity `sha256:1b33f661…9f0d5`.
- Warmup: declared `POLICY_REQUIRED_BARS[range-breakout-48-v1] = 49` bars,
  same for baseline and optimized.
- Windows: `2025-01-01..2025-02-01` (744 bars) and `..2025-04-01` (2160 bars);
  optional bounded 12-month trial `..2026-01-01` (8760 bars) to tighten scaling.
- Timeout budget: 60 s per trial (120 s max); all trials completed well inside
  (max ~12 s for the ungated 12-month full-history probe). No timeout occurred;
  reported honestly as `timed_out: false`.
- Split timers: `load_s` (tape scan) vs `engine_s` (Nautilus `run_swing_engine`)
  vs `report_s`; no source hashing inside timed sections.
- Peak RSS via `resource.getrusage(RUSAGE_SELF).ru_maxrss` with platform units
  (`bytes (macOS ru_maxrss)` here); MiB derived.
- Parity: `compare_swing.py` normalizes only volatile ids
  (`client_order_id`, `*_client_order_id`, `bracket_leg_filled`, `position_id`);
  all bar-bound timestamps (`decision_ns`, `entry_bar_ns`, `expires_ns`,
  `timeout_ns`) and economic content compared strictly.

Reproduction via the tracked candidate (from repo root):

```sh
v8-next/.venv/bin/python v8-next/tools/swing_perf_review.py \
  --start-utc 2025-01-01 --end-utc 2025-02-01 \
  --out artifacts/swing-performance-review --label repro-1mo
v8-next/.venv/bin/python v8-next/tools/swing_perf_review.py \
  --start-utc 2025-01-01 --end-utc 2025-04-01 \
  --out artifacts/swing-performance-review --label repro-3mo
v8-next/.venv/bin/python -m pytest v8-next/tests/test_swing_engine_perf.py \
  v8-next/tests/test_causality.py v8-next/tests/test_swing_baseline_nx06.py -q
v8-next/.venv/bin/python -m ruff check \
  v8-next/src/v8_next/adapters/swing_engine.py \
  v8-next/tests/test_swing_engine_perf.py v8-next/tools/swing_perf_review.py
```

Original audit scripts remain under `artifacts/swing-performance-review/`
(`measure_swing.py`, `bounded_parity.py`, `compare_swing.py`) for full
event-level comparison; the tracked tool above reproduces the small summaries.

## Baseline vs optimized — gated engine (Nautilus `run_swing_engine`)

Same inputs, identical outputs (parity `True`; `parity-*.json` preserved in
artifacts; summaries below, not full event logs).

| window | bars | baseline engine | optimized engine | decisions | campaigns | fills/closed | peak RSS (MiB) |
|---|---|---|---|---|---|---|---|
| 1 mo | 744 | 0.297 s | 0.548 s* | 23/23 | 3/3 | 5/2 both | 419.8 / 418.6 |
| 3 mo | 2160 | 0.194 s | 0.154 s | 23/23 | 3/3 | 6/2 both | 493.9 / 505.6 |
| 12 mo (optional) | 8760 | 0.300 s | 0.246 s | 23/23 | 3/3 | 6/2 both | 500.9 / 490.5 |

`*` 1-mo optimized rerun variance (import + venue setup; earlier runs
0.249 s / 0.149 s / 0.158 s). Absolute gated savings remain 0.05–0.15 s and sit
near run-to-run variance. No 2–5 minute gated speedup is claimed or measured.

Important caveat: after January the engine is stuck in
`CLOSING_TIMEOUT_EXPIRED` (existing bracketless semantics, deliberately not
fixed here), so almost no new decisions occur for months. The tiny gated
durations therefore do NOT establish full four-year backtest runtime; they only
show the measured Jan-2025 regime stays <1 s either way. Crowded regimes with
frequent decision attempts approach the ungated decision-plane cost below,
where the bound matters.

## Decision-plane worst case (ungated `frame_at + swing_signal` every bar)

This isolates the named hotspot
(`_try_open: frame_at(..., tuple(self.seen))` rebuilding growing history +
`CausalFrame.df` rebuild + full-history rolling + O(n) continuity/duration
scans each bar). It is a decision-only microbenchmark, NOT a complete economic
backtest (no Nautilus venue, fills, accounting or reporting).

| bars | full-history | bounded-128 | speedup | decisions | mismatches |
|---|---|---|---|---|---|
| 744 | 0.097 s | 0.023 s | 4.2× | 42/42 | 0 |
| 2160 | 0.772 s | 0.072 s | 10.7× | 123/123 | 0 |
| 8760 | 12.011 s | 0.406 s | 29.6× | 477/477 | 0 |

Tape verified `continuous=True`, single duration `3_600_000_000_000 ns`.
Per-call cost grows ~linearly with history; cumulative is ~quadratic
(exponent ~1.8–1.9).

## Four-year decision-only ESTIMATE (not a backtest time — not measured)

Four years hourly ≈ 35,064 bars. Decision-only extrapolation from measured
scaling; explicitly NOT complete economic backtest time (excludes venue
simulation, order lifecycle, position accounting, reconciliation and reporting,
whose scaling was not measured for four years here).

- Full-history decision-only (quadratic from 12 mo):
  `12.011 s × (35064/8760)² ≈ 192 s ≈ 3.2 min`, roughly 150–230 s given
  exponent 1.8–1.9 plus rerun variance. ESTIMATE.
- Bounded-128 decision-only (linear, rate ~0.041–0.046 ms/bar):
  `≈1.5 s`, roughly 1.5 ± 0.4 s. ESTIMATE.
- Gated Nautilus engine for 35 k bars cannot be established from the stuck
  Jan-2025 regime; linear venue-overhead guess (~1 s) would be misleading in
  crowded regimes. Not claimed.

No full 4-year multi-policy research was launched.

## Why 128 is a conservative documented bound (not universal)

128 is proven only for the exact `plain_swing` / `range-breakout-48-v1` /
`squeeze:baseline:v2` combination (49-bar grammar, 69-bar squeeze baseline
warmup, 73 worst-case for m2/m3, 14-bar span; all reads confined to the last
73; 128 is the next power of two above). It is NOT an empirically universal
guarantee: `_fast_path_eligible()` forces every other grammar/protection
combination (including `causal_trend`) onto the unchanged exact path, and any
change to policy dependencies requires revisiting the bound, the guard and the
tests together. Global latched guards (foreign instrument, late/missing
availability, duplicate starts, gaps, irregular durations) force exact fallback
permanently, so a bad old candle outside the tail can never be hidden; a naive
tail that slides past such history would look continuous while the exact frame
is gapped/raising, and the implementation deliberately avoids that.

## Tests (production path, no duplicated algorithm)

- `test_swing_engine_perf.py` (11 tests) calls
  `SwingEngineStrategy.on_bar` / `_decision_frame` directly:
  proven-lookback cover; plain_swing bounded parity; causal_trend exactness
  beyond 128 bars (fails pre-guard); foreign/late old-candle exactness (fail
  tail-only); gap/duplicate-error/irregular-duration exactness; sequential
  no-future-data; real-tape sequential parity (200 bars) and truncation-boundary
  seamlessness. No `assert … or True`.
- Verified the three load-bearing regressions fail on pre-fix logic (naive
  128-truncation gives 128-continuous vs exact 199/200-gapped/200-exact).
- `pytest test_swing_engine_perf + test_causality + test_swing_baseline_nx06`:
  expected ~29 passed. `test_perf_hot_paths + test_swing_costs`: 24 passed.
- `ruff check` on engine, tests and tracked tool: passed.
- `mypy` on new tests + tracked tool: clean. `mypy` on `swing_engine.py`
  reports one pre-existing error in untouched `_instrument`
  (`Any | None` vs `CryptoPerpetual`); not introduced here.

## Independent re-measurement (second measurer)

Re-measured on the same machine by a different process with a different sampling
method: the first N bars of the tape (744 / 2160 / 8760) rather than calendar
windows, two alternating runs, median reported, load average recorded
(`3.47 4.00 4.25` — a busy machine, so wall clock is read against that load and
the load-independent result is the mismatch count).

| bars | full-history | bounded-128 | speedup | decisions | mismatches |
|---|---|---|---|---|---|
| 744 | 0.099 s | 0.023 s | 4.4x | 40 | 0 |
| 2160 | 0.689 s | 0.057 s | 12.0x | 93 | 0 |
| 8760 | 11.275 s | 0.220 s | 51.2x | 324 | 0 |

The parity claim holds under an independent implementation of the comparison
(every decision compared field by field, no normalization applied): **0
mismatches at every size**. The shapes agree with the original run — the
full-history path grows super-linearly (0.099 -> 0.689 -> 11.275 s for
2.9x/4.05x more bars) while the bounded path stays near-linear. Absolute
speedups differ between the two measurings because the decision density differs
between "first N bars of the tape" and the calendar windows; the direction,
the mismatch count and the scaling are the load-bearing parts.

Verification run alongside this review: full suite `1107 passed`, `ruff` clean,
`mypy` clean on the new test and tool. One vacuous assertion
(`assert x is not None or x is None`) was removed from the parity test during
the review; it asserted nothing either way.

## Limitations

- Gated speedup small in absolute terms here; decision-only speedup
  (4→11→30×) is load-bearing only where decision attempts are frequent.
- Peak RSS unchanged (tape + Nautilus dominate); CPU-only change.
- Single instrument (`BTCUSDT`), single proven policy (`plain_swing`), hourly
  bars; all else exact-but-slow via guard.
- No time-parallelization (shared capital would break causality); no GPU.
- Synthetic fixtures only in MECHANICS ONLY unit tests, never as
  performance/economic evidence. Closing-state stickiness intentionally
  unfixed in this patch.
