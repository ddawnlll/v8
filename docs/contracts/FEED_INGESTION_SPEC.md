# V8 Feed and Ingestion Specification

**Status:** PROVISIONAL_DECISION. This is the research-only data intake contract.
It defines how raw market evidence enters the canonical store. It deliberately
contains no order path: V8 research ingests market data, never sends orders.

## 1. Scope and invariant

A **VenueAdapter** is the only component that touches an external data source.
It has one interface, `subscribe(feeds) -> TapeWriter`, and one responsibility:
convert venue payloads into validated tape rows with three distinct clocks. No
other component may reference a venue endpoint, symbol string, or protocol
detail.

The first concrete adapter is **Binance USDT-M perpetual futures** (`binance-um`
v1). It is chosen because the project evidence corpus and brief examples
(SOLUSDT, funding, liquidation) are Binance-shaped; the adapter contract itself
is venue-agnostic so a second venue must not change any consumer.

**LOCKED_INVARIANT — research-only ingestion:** the adapter may emit tape rows,
venue sequence state, and reconciliation records. It must never emit an order,
an allocation, or a live signal. A capability boundary, not a convention: the
adapter package has no credentials, no account scope, and no signing path.

## 2. Tape row contract

Every stored raw fact is one immutable `TapeRow`:

```
source, channel, instrument,
event_time,        # venue transaction time (e.g. aggTrade T, kline close time)
available_time,    # earliest time a configured consumer could have seen this version
ingested_time,     # local NTP-synced arrival time
venue_sequence,    # venue-provided ordering key, or provider fallback + quality flag
payload, payload_hash, schema_version
```

Rules:

- The three clocks are never collapsed. `ingested_time` is never a proxy for
  availability (`MARKET_STATE_CONTRACT` §1).
- Dedup key is `(source, channel, venue_event_id)`; klines dedupe by open time,
  aggTrades/trades by trade ID, depth by `(U,u)` window, forceOrders by order ID.
- Replay ordering is `(event_time, available_time, venue_sequence)`, never
  ingestion order. Ties break deterministically by
  `(venue, channel, sequence, received_sequence)`.
- For Binance UM: futures timestamps are milliseconds (spot switched to
  microseconds 2025-01-01); the adapter must normalize to integer nanoseconds
  and record the source unit in `schema_version`.

## 3. Feeds and their PIT semantics

| Feed | Stream / endpoint | PIT rules for consumers |
|---|---|---|
| Klines | `{s}@kline_{interval}` (250 ms) | Only **closed** klines (`x:true`) are consumable; open klines are re-sent repeatedly and must be dropped. Bar usable at `bar_available_time = close_time + feed_latency + aggregation_latency`. |
| Aggregated trades | `{s}@aggTrade` (100 ms) | Per-trade facts; volume/flow features use these, not kline volume alone. |
| Book | `{s}@depth{levels}@{speed}` diff + partial depth | Drop diff events with `u < lastUpdateId`; resync via REST snapshot on sequence discontinuity. `bookTicker` has no sequence and is not a full tape. |
| Mark price / funding | `{s}@markPrice@{1s\|3s}` | Carry `r` (last funding rate) and `T` (next funding time); the applicable funding rate at boundary `t` is only knowable from the markPrice stream — this is the PIT-correct funding source. |
| Force orders | `!forceOrder@arr` (1000 ms) | Order **snapshots**, not executions; dedupe by order ID and count only filled quantity. |
| Funding history | `GET /fapi/v1/fundingRate` | Since the 2025-09 dynamic-interval change some symbols fund on 1h/2h/4h; `fundingInfo` lists non-8h symbols. The funding schedule is versioned venue input, not assumed 8h. |
| Open interest | `GET /futures/data/openInterestHist` | Hourly period-start snapshots; API covers only the last 30 days — long history comes from Vision `metrics` dumps. Point-in-time per period, not tick-level. |

## 4. Gap and duplication discipline

- **Gaps:** WebSocket drops events on disconnect. On reconnect, backfill the
  gap via REST (`klines` by open time, `aggTrades` by `fromId`), then verify
  continuity of the venue sequence before resuming.
- **Duplicates:** reconnect can re-deliver events; dedupe by the keys in §2 and
  never count a duplicate as new volume or a new trade.
- **Survivorship:** `exchangeInfo` lists only live symbols; Vision archives keep
  delisted pairs (e.g. UST). Build the historical universe from listing/delisting
  dates so delisted instruments remain present before their end time
  (`DATASET_SPEC` §3).

## 5. Backfill and reconciliation

- **Vision archive** (`data.binance.vision`): monthly/daily zips of one CSV plus
  a `.CHECKSUM`, naming `BTCUSDT-1h-2025-01.zip`; daily files lag ~1 day,
  monthly files release the first Monday of the following month. Download with
  the official scripts (`binance-public-data`) or a checksum-verified clone.
- **Idempotency:** a backfill is a parameterized reprocess of a time range over
  an already-validated pipeline — it must be safe to run twice and produce
  identical stored rows and hashes. Post-backfill audit compares row counts,
  payload hashes, and summary stats against the pre-backfill baseline.
- **Reconciliation:** continuous comparison of the live stream against REST
  pagination and, where available, a second provider. Divergence beyond the
  declared tolerance is an **incident**, not a curiosity (`OPERATIONS_SPEC`).

## 6. Cheap executable tests

1. Inject a tape row with `available_time = D + 1ns`; the ingest must fail.
2. Feed a kline with `x:false`; it must never reach the OHLC feature path.
3. Re-deliver the same aggTrade ID; the store must contain exactly one row.
4. Inject a gap in the `fromId` sequence; the adapter must emit a gap record
   and refuse to resume until the backfill verifies.
5. Run a Vision backfill twice; both runs must produce identical row hashes.
6. Corrupt one payload (checksum mismatch); ingest must fail closed.

## 7. Evidence and citations

- **LITERATURE_SUPPORTED:** Binance UM REST market-data endpoints, weights, and
  limits: [Binance UM futures REST market data](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).
- **LITERATURE_SUPPORTED:** Binance UM WebSocket streams and update speeds:
  [Binance UM futures WS market streams](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/ws-streams/market).
- **LITERATURE_SUPPORTED:** Vision archive layout and release cadence:
  [data.binance.vision](https://data.binance.vision), [download scripts](https://github.com/binance/binance-public-data).
- **LITERATURE_SUPPORTED:** funding rate mechanics and dynamic intervals:
  [Binance funding rate FAQ](https://www.binance.com/en/support/faq/detail/360033525031).
- **DESIGN_INFERENCE:** the three-clock tape row, research-only boundary, and
  the backfill/reconciliation gates are V8 choices that make the requirements
  above testable. No source is cited as proof that any feed yields an edge.
