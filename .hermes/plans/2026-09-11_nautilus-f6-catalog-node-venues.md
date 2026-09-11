# NT-F6 (#405) — parquet catalog + BacktestNode parity + venue #2 + sandbox

Status: implemented on `main`. Every number below is from a real run on this
machine; anything not measured is named as such.

## What was built

| Surface | Change |
|---|---|
| `v8_next/adapters/catalog_tape.py` | Writes the real quad tape (instruments + 1h EXTERNAL bars, optional trade ticks from the verified archives) into a run-scoped `ParquetDataCatalog`, keyed by a run id derived from the tape hash + window + legs. `catalog_inventory()` reads the catalog **back** (per-type row counts, identifiers, first/last `ts_event`) and digests it — a reader can prove what the catalog holds instead of trusting the writer. |
| `v8_next/adapters/node_backtest.py` | Runs the same portfolio backtest through `BacktestNode` + `BacktestRunConfig` + `BacktestVenueConfig` + `BacktestDataConfig`, reusing `execution_models.resolve_profile` and `ExpertEnsembleStrategy`. Strategy attachment is `node.build()` → `node.add_strategy(run_config_id, strategy)` → `node.run()` (this build's `BacktestEngineConfig` has no `strategies` field). |
| `v8_next/adapters/okx_capture.py` | Venue #2 (OKX) public data adapter: verified raw capture of instruments/klines/trades with per-artifact sha256 + request/receive clocks, `historical_pit_status: UNKNOWN`, `claim_status: NO_ECONOMIC_CLAIM`, and an explicit OKX → Nautilus instrument mapping (`BTC-USDT-SWAP` → `BTCUSDT-PERP.OKX`). |
| `v8_next/app/sandbox.py` | Bounded `Environment.SANDBOX` session: live public Binance market data + the Nautilus **sandbox execution client** (simulated fills), recording every quote/trade, the full order lifecycle, the fill price/liquidity side, and digests of both journals. Fails closed with the exact error if the venue is unreachable. |

## Measured evidence

Catalog + node parity on the real quad tape (120 real 1h bars × 4 legs):

| quantity | value |
|---|---|
| catalog run id | `4228023b3bca8069` |
| bars written / read back | 480 / 480 |
| catalog window (ts_event) | `1751331600000000000` … `1751760000000000000` (= tape end_ns span) |
| catalog build wall time | **0.063 s** |
| node run wall time | **0.091 s** |
| node fill signature | `f396a2faa0e270f3fc523471a2067d8908b9094b5afa2ac1c447e8779b717ce8` |
| direct-engine fill signature | **identical** — same 5 fills, same opened positions |
| node determinism (2 runs) | identical `fill_signature` + `opened_positions` |
| funding through the catalog | `ABSENT_NO_CATALOG_WRITER_FOR_FUNDING_RATE_UPDATE` — named, not faked |

Venue #2 (OKX, captured 2026-09-11): 300 1H candles (2026-08-27 → 2026-09-11),
400 trades, instrument mapping `BTC-USDT-SWAP` → `BTCUSDT-PERP.OKX`,
`claim_status = NO_ECONOMIC_CLAIM`.

Sandbox: **blocked, named** — `v8_next/app/sandbox.py` builds a real SANDBOX
session (live public Binance data + the Nautilus sandbox execution client, one
instrument-minimum probe order to exercise the execution path), but this
`nautilus-trader` build cannot start the sandbox exec client from Python:

```
NotImplementedError: No execution factory extractor registered for 'SANDBOX'
```

Measured with both client names (`SANDBOX` and the venue name `BINANCE`), and the
adapter package in `.venv` is a thin re-export of the compiled
`nautilus_trader._libnautilus.sandbox` with no Python-side registration hook. The
module therefore fails closed and writes
`research/tape/sandbox-*/blocked.json`:

```json
{"status": "BLOCKED_SANDBOX_EXEC_CLIENT_UNAVAILABLE",
 "blocker": "NotImplementedError: No execution factory extractor registered for 'SANDBOX'",
 "retry_condition": "a nautilus-trader build whose exec-factory registry exposes the sandbox adapter, or a documented registration call for it"}
```

No session record is written with zero data, and nothing claims simulated
execution ran. Live *data* ingestion is independently proven by the F1 capture
path (`stream.py` subscribes quotes + trades on a `LiveNode`), so the missing half
is specifically the simulated-execution client.

## Live reconciliation design (explicit F6 deliverable)

What would be compared against a real venue account, field by field, when
reconciliation is authorised (G8 is `UNRUN_NO_VENUE_ACCOUNT` today — this is the
design, not a claim that it ran):

1. **Order identity**: our `client_order_id` ↔ venue order id, per order; a
   missing venue id for an order we believe we sent is a hard failure
   (`ORDER_NOT_ACKNOWLEDGED`), not a warning.
2. **Fill identity**: venue trade id + `ts_event` + price + quantity + fee
   currency, matched one-to-one against our fill records; the comparison reports
   unmatched-on-either-side counts rather than netting them out.
3. **Position state**: venue position size/entry price vs our account state at
   the same clock, with a tolerance derived from the instrument's size step
   (never a hand-picked epsilon).
4. **Cash**: venue wallet balance vs our MARGIN account balance, split by
   currency; funding/commission lines compared as their own categories so a
   funding difference cannot hide inside a fill difference.
5. **Timing**: venue `ts_event` vs our `ts_init` per event, reported as a
   distribution (p50/p95/max) so latency is visible, not averaged away.
6. **Failure modes named up front**: `MISSING_VENUE_FILL`, `PHANTOM_VENUE_FILL`,
   `SIZE_MISMATCH`, `PRICE_MISMATCH`, `FEE_CURRENCY_MISMATCH`,
   `POSITION_DRIFT`, `BALANCE_DRIFT`, `STALE_RECON_WINDOW`. Each publishes the
   observed values; none is smoothed into a percentage.
7. **Authority**: reconciliation is read-only against the venue. It produces a
   receipt; it does not modify orders, balances, or positions, and it mints no
   economic claim (Rule 12).

## Verification

```sh
cd v8-next
.venv/bin/python -m pytest -q tests/test_catalog_f6.py -s     # 8 passed
```

Mechanics tests cover run-id determinism/sensitivity, the OKX instrument mapping
and the raw-payload row accounting; evaluative tests cover catalog-vs-tape
inventory, catalog build determinism, direct-vs-node fill parity, node
determinism, and the venue #2 capture. The evaluative ones skip when the tape or
the capture is absent.

## Honest limits

* Funding does **not** travel through the catalog: this build has no writer for
  `FundingRateUpdate`, so the node path publishes
  `ABSENT_NO_CATALOG_WRITER_FOR_FUNDING_RATE_UPDATE` instead of a zero. A node run
  is therefore **not** equivalent to the direct path on funding settlement; the
  parity claim above is scoped to prices/fills/positions.
* Trade ticks are optional in the catalog and were not used for the parity run
  (the direct path's window has no in-window archive trades).
* Venue #2 is data-only. There is no OKX order path, no account, and no
  reconciliation run — by design, not by omission.
* The sandbox session proves the execution path against live prices; it is not a
  paper-trading record and carries no capital authority.
