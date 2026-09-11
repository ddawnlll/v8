# NT-F1 (#400) — TradeTick capture + aggressor-aware, trade-driven fill

Status: implemented on `main`, measured on the real quad tape. `NO_ECONOMIC_CLAIM`:
this is execution *semantics* evidence, not venue-truth fills.

## What was built

| Surface | Change |
|---|---|
| `v8_next/adapters/trade_tape.py` | `trades_from_pages` (REST aggTrades pages, pre-existing) + `trades_from_dump`: streaming reader for the public daily aggTrades archives, tolerating headered and headerless files; window restriction with out-of-window accounting; unreadable aggressor flag or row is dropped and counted, never guessed. |
| `v8_next/adapters/binance_capture.py` | `capture_agg_trades_dump`: downloads daily archives **and verifies them against the venue's own `.CHECKSUM`** before storing; `agg_trades_dump_stats` measures rows / time span / flag coverage with the same reader the backtest uses; `validate_dump_capture` re-verifies integrity + provenance; CLI `--agg-trades-dump-day YYYY-MM-DD` (repeatable). |
| `v8_next/app/stream.py` | Live capture now subscribes trades and records `trades.jsonl` (venue price/size/aggressor/trade id + event/received clocks); a trade without a readable aggressor side or with impossible clocks fails the session instead of being recorded. Session `result.json` gains `trade_count`, `trades_sha256`, `trade_capture_scope`. |
| `v8_next/adapters/portfolio_backtest.py` | `run_portfolio_backtest(..., trades=...)` feeds TradeTicks into the shared account (pre-existing uncommitted work, kept) and publishes `trades_fed`. |

Aggressor mapping is the venue's own `m` flag (`isBuyerMaker`): `true` → the
resting side was the buyer → aggressor **SELL**; `false` → aggressor **BUY**.
Nothing is inferred from price or size.

## Measured evidence (real tape, not synthetic)

Bar tape: `research/tape/quad-1h-12m` (120 real 1h bars, 2025-07-01 → 07-06, four legs).
Trade feed: `research/tape/btcusdt-agg-trades-2025-07` + `ethusdt-agg-trades-2025-07`,
downloaded from `data.binance.vision` daily aggTrades archives and verified against
the venue's signed checksums; measured window 2025-07-03T10:00–18:00Z.

| | bar-only | bar + real trades |
|---|---|---|
| trades fed | 0 | **1,219,880** (BTC 512,717 + ETH 707,163) |
| fills | 5 | 5 |
| fill signature | `f396a2fa…` | `e4263182…` |
| measured shortfall (bps mean) | **0.000404** (3 samples) | **0.016434** (3 samples) |
| BTC entry | bar boundary `11:00:00.000` @ 109794.72 | real print `10:00:00.263` @ **109894.62** |
| ETH entry | bar boundary `15:00:00.000` @ 2593.98 | real print `15:00:00.061` @ **2623.77** |

Reading of the numbers:

* With trades present the entry no longer waits for the next bar to close: it
  fills at the **first venue print after the decision** (263 ms and 61 ms after
  the decision bar) at the price that actually printed (fill = print + at most
  one price increment from `OneTickSlippageFillModel`).
* Both runs execute twice; the two trade-fed runs are bit-identical
  (`fill_signature` and `opened_positions` equal), so the trade path is
  deterministic.
* Shortfall rises 0.000404 → 0.016434 bps on the same window because the fill is
  now referenced to the price that traded instead of a bar close one hour later.
  The delta is a measurement of the *reference change*, not a venue claim.

## Verification

```sh
cd v8-next
.venv/bin/python -m pytest -q tests/test_trades_f1.py -s   # 10 passed, prints the table above
.venv/bin/python -m pytest -q tests/test_execution_integration.py tests/test_execution_models.py \
    tests/test_stream.py tests/test_stream_replay.py tests/test_stream_run.py tests/test_capture_integrity.py
```

The evaluative test skips (never synthesises) when the bar tape or the archive
capture is absent; the archive reader, checksum refusal and malformed-day
handling are covered by mechanics tests that need neither.

## Honest limits

* Archive dumps carry **no** historical point-in-time availability: the capture
  manifest records `historical_pit_status: UNKNOWN` and a null
  `historical_available_time_ns`, exactly like the REST capture path.
* Only the 2025-07-03 10:00–18:00Z window was measured (it contains the two
  entries this 120-bar tape produces). Trades outside it are counted as
  `out_of_window`, not extrapolated.
* ETH archives were captured for 07-03/07-04 only; the reader takes whatever
  verified archives are present in the directory.
* Simulated fills remain modelled execution assumptions (`MODELLED_EXECUTION_ASSUMPTION_NOT_VENUE_TRUTH`);
  venue reconciliation is #379/#385 territory (G8 `UNRUN_NO_VENUE_ACCOUNT`).
