# F6 (#405) addendum — live-capture sandbox replay, and an F2 hardening it exposed

Two things came out of finishing the sandbox bullet.

## 1. The upstream sandbox exec client is unusable on this build (re-verified)

```
NotImplementedError: No execution factory extractor registered for 'SANDBOX'
```

Measured four ways: client name `SANDBOX` and `BINANCE`, exec client added before
and after the Binance data client. The compiled library contains the sandbox
factory (`nautilus_sandbox::factory::SandboxExecutionClientFactory`, "Sandbox
registered message handlers for venue=") but the exec-factory registry has no
extractor entry for it, and the Python package is a thin re-export with no
registration hook. `app/sandbox.py` therefore fails closed with
`status: BLOCKED_SANDBOX_EXEC_CLIENT_UNAVAILABLE` + a `retry_condition`.

## 2. Live-capture replay delivers the bullet's substance

`app/sandbox_replay.py` records a bounded window of **live public** venue data and
replays exactly those bytes through simulated execution:

1. `capture_live_window()` — 60 s of displayed depth snapshots (3 s polls, 20 levels
   per side), every aggTrade of the same window, and the venue's 1h klines (which
   also carry the warmup), each through the existing verified capture paths.
2. `replay_capture()` — feeds the recorded klines, trades and book deltas into
   `BacktestEngine` with a named execution profile and one instrument-minimum
   probe order, then publishes a **data-match report** between what the venue sent
   and what the engine consumed.

Measured on the recorded session `research/tape/sandbox-replay-20260911T0500Z`:

| quantity | value |
|---|---|
| bars fed (closed only) | 499 (0 unclosed dropped on this session) |
| trades fed | 652 |
| book deltas fed | 399 |
| data match | `matched: true`, `mismatches: []` |
| probe fill | **1 fill, 76862.71, TAKER** |
| status | `REPLAY_COMPLETED_WITH_FILLS` |

## 3. Three engine behaviours measured while building it

These are not opinions — each was reproduced with the configurations named:

1. **With an L2 book configured, a MARKET order submitted from a bar or trade
   callback never executes.** Same run, same data: 2 fills without the book, 0
   with it (`run_portfolio_backtest`, single BTCUSDT leg, 120 real quad bars).
   Submitting the same order from a **book-delta callback** fills normally
   (76862.71 = the recorded book price).
2. **A LIMIT order is unaffected**: a marketable limit submitted from a bar
   callback fills against the book (this is what the F2 knob probes do).
3. **`generate_order_fills_report()` can come back empty for a run whose strategy
   observed a fill** (measured: 1 fill in the callback, 0 report rows, 1 order in
   the cache). The replay therefore records the callback evidence as primary and
   names the report discrepancy
   (`ENGINE_FILL_REPORT_EMPTY_WHILE_STRATEGY_OBSERVED_FILLS`) instead of
   presenting "no fills".

## 4. F2 hardening this exposed

Finding 1 means the F2 wiring could silently publish an empty run as
depth-exercised execution: with book deltas whose window does not overlap the bar
window, `run_portfolio_backtest` produced **0 fills** while the execution block
said `depth_data_available: True` and listed both knobs as **active**.

Fixed fail-closed: the book-window/bar-window overlap is computed, and
`depth_data_available` is only set when the windows actually overlap. Disjoint
runs now publish

```
"book_window_overlap": false,
"book_window_reason": "NO_OVERLAP_BETWEEN_CAPTURED_BOOK_AND_BAR_WINDOW",
"execution": { "depth_data_available": false,
               "depth_dependent_knobs_active": [],
               "inert_knobs_without_depth_data": ["liquidity_consumption","queue_position"] }
```

plus `bar_window_ns` / `book_window_ns` so a reader can see *why*. Pinned by
`tests/test_l2_book_f2.py::test_a_book_window_disjoint_from_the_bars_cannot_claim_active_knobs`
(measured: bar window 2025-07-01…06, book window 2026-09-11, fills 0, reason named).

## Verification

```sh
cd v8-next
.venv/bin/python -m pytest -q tests/test_sandbox_replay_f6.py -s   # 6 passed
.venv/bin/python -m pytest -q tests/test_l2_book_f2.py -s          # 9 passed
```

## Honest limits

* This is **not** NautilusTrader's SANDBOX environment. It is live data recorded
  and replayed through simulated execution, labelled as such
  (`mechanism: LIVE_CAPTURE_REPLAY_THROUGH_SIMULATED_EXECUTION`) with the upstream
  blocker recorded next to it.
* The replay window is 60 s of depth; the klines are hourly, so the probe order
  is driven by the recorded book, not by an hourly decision.
* Nothing here touches a venue account: `UNRUN_NO_VENUE_ACCOUNT` stays unresolved,
  and the artifact carries `NO_ECONOMIC_CLAIM` / `NONE_SIMULATED_EXECUTION_ONLY`.
