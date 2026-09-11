# NT-F2 (#401) — captured L2 book + measured activation of the depth knobs

Status: implemented and measured on **real captured venue data**. `NO_ECONOMIC_CLAIM`.

## What was built

| Surface | Change |
|---|---|
| `binance_capture.capture_depth` | Bounded public capture of BTCUSDT displayed depth (`/fapi/v1/depth`, 20 levels/side) into raw snapshots + manifest (per-file sha256, request/receive clocks, achieved vs requested span, `historical_pit_status: UNKNOWN`, `NO_ECONOMIC_CLAIM`), with a CLI switch. |
| `adapters/book_tape.py` | Snapshot series → deterministic `OrderBookDelta` sequence: each snapshot emits **CLEAR + top-N ADDs** (N = 10, documented: only the displayed touch is exercised, and a clear is required or vanished levels linger as phantom liquidity). Window restriction, drop-and-count accounting, one-sided snapshots flagged, `book_digest()` identity. |
| `portfolio_backtest.run_portfolio_backtest(..., book_deltas=..., book_type=L2_MBP)` | Feeds captured deltas into the shared account, opens the venue with the L2 book type, rejects deltas for instruments outside the run, and sets `depth_data_available=True` **only when it really fed a book** — the flag follows the data, not the caller's intent. |
| `execution_models.profile_summary` | The `inert_knobs_without_depth_data` claim is now conditional: with depth present the summary publishes `depth_dependent_knobs_active` + `depth_dependent_knobs_evidence = MEASURED_FILL_CHANGES_WITH_CAPTURED_L2_BOOK`; without depth the previous inert report is unchanged. |

## Measured evidence (real capture, 2026-09-11)

Capture: `research/tape/btcusdt-l2-20260911T0320Z` — 72 snapshots, 240 s,
`top-10 levels/side` → **1,512 deltas** (72 CLEAR + 1,440 ADD), digest
`5402935cf1731e31…`. Trades of the same window:
`research/tape/btcusdt-trades-20260911T0320Z` — 2,897 real aggTrades.

Probe: one limit order, live from 1 s into the window (so the real book/trade flow
passes it), account 1,000,000 USDT. **Every fill price is a captured book price**,
not a bar price.

**`liquidity_consumption`** — marketable limit at the opening ask + 1 tick, qty 5.0
(deliberately larger than the displayed size at the touch):

| setting | fills | first tranches |
|---|---|---|
| `liquidity_consumption=False` | **2** | 3.501 TAKER @76767.80, 1.499 MAKER @76767.81 |
| `liquidity_consumption=True` | **6** | 2.456 TAKER @76767.80, 0.026 @76767.81, 0.006 @76767.81 |

**`queue_position`** — passive limit resting at the opening bid while real trades
print through it:

| setting | fills | tranches |
|---|---|---|
| `queue_position=False` | **3** | 0.006, 0.001, 0.043 (all MAKER @76767.70) |
| `queue_position=True` | **1** | 0.050 (MAKER @76767.70) |

So on real captured depth the two knobs the profile used to publish as *inert*
now change the fill decomposition and the fill count. The bar-only claim is
untouched: with bar data and no book the same knobs still produce no difference
(see `tests/test_execution_integration.py`).

Determinism: the same capture digests identically across reads, and a repeated
knob configuration produces bit-identical fills.

## Verification

```sh
cd v8-next
.venv/bin/python -m pytest -q tests/test_l2_book_f2.py -s     # 8 passed
.venv/bin/python -m pytest -q tests/test_execution_integration.py tests/test_execution_models.py
```

## Honest limits

* The capture is **displayed aggregated levels** at poll instants (3 s interval),
  not a continuous change stream and not L3 order-level data. Between snapshots
  the book is stale by up to one interval; the CLEAR at each snapshot is what
  prevents that staleness from accumulating into phantom liquidity.
* Only the top 10 levels/side are materialised (`DEPTH_LEVEL_BOUND`); depth beyond
  that is counted in `levels_beyond_bound` and never extrapolated.
* The book window (2026-09-11) does not overlap the canonical bar tape
  (2025-07-01…06), so this phase measures the *knob semantics* on real depth, not
  a portfolio result. Capacity/impact conclusions remain #382's.
* A live SANDBOX execution session is out of reach on this build (see F6 report:
  `BLOCKED_SANDBOX_EXEC_CLIENT_UNAVAILABLE`).
