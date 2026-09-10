# Shadow / Live Data Spec (D-152 §5, D-153)

Status: canonical. Separate fixture from live venue evidence. Synthetic fixtures must never be counted as live fills.

## 1. Live Venue Fills (G8)

Format: `artifacts/shadow_fills.jsonl` — one JSON object per line, UTF-8, LF terminated.

Per-record fields (required):
- `fill_id: str` — venue fill/execution identifier (unique)
- `instrument: str` — e.g. `BTCUSDT` (matches tape instrument without suffix)
- `price: number` — fill price (finite >0)
- `qty: number | string` — fill quantity (finite >0, string form allowed but must parse)
- `side: str` — `BUY` | `SELL`
- `venue_time_ns: int` — venue match time (ns since epoch, int)
- `order_id: str` — venue order identifier

Optional but recommended: `commission`, `commission_asset`, `realized_pnl` (informational; engine accounting is not derived from these).

Source: venue private REST `GET /fapi/v1/userTrades` (or equivalent USD-M `GET /fapi/v1/order` fills) + user-data stream `TRADE_LITE` / `ORDER_TRADE_UPDATE` for real-time shadow capture. Only data obtained with an authenticated venue account is accepted. No public endpoint yields fills.

Command (requires `BINANCE_API_KEY` + `BINANCE_API_SECRET` env):
```sh
# Example: fetch last 7d of venue-settled trades for one symbol (private, requires API key)
uv run --project v8-next python -m v8_next.adapters.shadow_ingest fetch \
  --symbol BTCUSDT --start-ms 1751328000000 --end-ms 1751932800000 \
  --out artifacts/shadow_fills.jsonl

# Offline verification / reconciliation (no credentials, deterministic):
uv run --project v8-next python -m v8_next.adapters.shadow_ingest verify \
  --fills artifacts/shadow_fills.jsonl --check-account artifacts/shadow_account.json

# Quad tape funding stream (public, real venue funding records bundled in quad tape):
uv run --project v8-next python -c "from v8_next.adapters.funding_history import quad_funding_summary; print(quad_funding_summary('research/tape/quad-1h-12m/tape.jsonl', limit=500))"
```

If the command cannot run (no venue account, no credentials, no network), the record is documented as inaccessible and the gate reports:

```
mode: UNRUN_NO_VENUE_ACCOUNT
reason: venue private fills require BINANCE_API_KEY; no file at artifacts/shadow_fills.jsonl
expected_command: uv run --project v8-next python -m v8_next.adapters.shadow_ingest fetch --symbol BTCUSDT --out artifacts/shadow_fills.jsonl
fixture_ref: tests/ do not count as live; fixture paths contain tests/ or fixtures/ or are passed with source=fixture
```

Inaccessible handling: `shadow_ingest.ingest_status(path)` returns `UNRUN_NO_VENUE_ACCOUNT` when file absent/empty or credentials absent; `FIXTURE_NOT_LIVE` when path is under `tests/`/`fixtures/` or caller marks `source=fixture`; `LIVE_VENUE_SETTLED` only on validated non-fixture file with ≥1 well-formed record and passing `account_reconciliation` against the engine `AccountState` snapshot.

## 2. Quad Funding Stream (public, real)

Format: `research/tape/quad-1h-12m/tape.jsonl` — jsonl with fields `channel`, `instrument`, `event_time`, `payload`.

Funding record (`channel == "funding"`):
```json
{"channel":"funding","instrument":"BTCUSDT","event_time":1751328000000000000,"payload":{"funding_rate":1.05e-05,"funding_time_ms":1751328000000,"funding_interval_hours":8.0,"markPrice":"107087.3",...}}
```

Source: Binance USD-M public `GET /fapi/v1/fundingRate` (fundingRate + markPrice at settlement) and `GET /fapi/v1/premiumIndex` (nextFundingTime), bundled per 1h bar in the quad tape by the capture job. Original fetch commands:

```sh
# Public (no auth): history used to build the tape (one page per symbol):
curl "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1751328000000&endTime=1751932800000&limit=1000"
curl "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
# Tape build verification: count funding rows in the committed artifact
cat research/tape/quad-1h-12m/tape.jsonl | grep '"channel":"funding"' | wc -l
python3 -c "from v8_next.adapters.funding_history import quad_funding_summary; print(quad_funding_summary('research/tape/quad-1h-12m/tape.jsonl'))"
```

Feeding to engine: every in-window funding row becomes a native `MarkPriceUpdate` + `FundingRateUpdate` at `funding_time_ms` via `v8_next.adapters.funding_history.quad_funding_to_mad_updates` and `v8_next.adapters.portfolio_backtest.run_portfolio_backtest(..., funding=rows)`. Rows outside the backtest window are excluded, never extrapolated.

Inaccessible: if `research/tape/quad-1h-12m/tape.jsonl` absent, funding is `MISSING` and must not be zero-filled; receipt marks `funding_cost=None` and `limitations` includes `FUNDING_TAPE_MISSING`.

## 3. Reconciliation (G8 live)

Real `AccountState` comparison (`v8_next.adapters.engine_state.economic_state` vs `v8_next.adapters.shadow_ingest.reconcile_shadow_account`): commissions, balances, position counts and funding are compared against the engine `account` dict (keyed by `balance_total`, `positions`, `orders`). Fixture files and empty stubs fail reconciliation with `FIXTURE_NOT_LIVE`.

## 4. Fixture rule

Any file under `v8-next/tests/` or `v8-next/tests/fixtures/` or whose path contains `fixture` or whose caller passes `source="fixture"` is never counted as live, even if well-formed. `evaluate_g8_live_realization(..., fixture=True)` returns `FIXTURE_NOT_LIVE`.
