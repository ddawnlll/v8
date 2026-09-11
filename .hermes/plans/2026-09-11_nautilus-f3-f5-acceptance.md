# F3/F4/F5 acceptance measurements (issues #402, #403, #404)

Run on the real BTC tape (120 real 1h bars). Command:

```sh
cd v8-next && .venv/bin/python -m pytest -q tests/test_execution_phase_acceptance.py -s
```

## F3 (#402) — order variety, maker/taker readable

LIMIT vs MARKET entry, raw fill rows (`liquidity_side`, commission):

| entry | fills | maker | taker | maker ratio | fee charged | fee if all taker | rebate effect |
|---|---|---|---|---|---|---|---|
| LIMIT | 2 | 0 | 2 | **0.0** | 1.086154 USDT | 1.086154 USDT | **0.000000** |
| MARKET | 2 | 0 | 2 | 0.0 | 1.086154 USDT | 1.086154 USDT | 0.000000 |

Measured finding: on **bar** data the ensemble's limit entry is marketable (it is
priced at the decision close), so it takes liquidity — the maker path cannot
appear here. The maker path is measured where it can exist, against the real
captured book (F2, `test_l2_book_f2.py`): MAKER fills at 76767.70 with count 3
(`queue_position=False`) vs 1 (`queue_position=True`).
Remaining gap: an explicit `STOP_MARKET` entry type + per-order emulation
(`emulation_trigger`) is not implemented yet.

## F4 (#403) — TWAP slicing, measured

| algo | fills | TWAP children | shortfall_bps_mean | samples |
|---|---|---|---|---|
| NONE (single parent) | 2 | 0 | -0.001822 | 1 |
| TWAP, 4 slices | **8** | 3 | -0.001822 | 1 |

Measured finding: slicing turns 2 fills into 8 and emits the child sequence
`TWAP_CHILD_2/4, 3/4, 4/4` in order. The **published shortfall metric does not
move**, because `execution_telemetry` samples one fill per *position*, not per
child order — with a single position the sliced and single-print runs reference
the same opening fill. That is a limitation of the metric, stated rather than
averaged away.

## F5 (#404) — the brake, proven

| configuration | decision action | opened | fills |
|---|---|---|---|
| default (flat 0.010 BTC) | `SUBMITTED_BRACKET_MARKET_BUY_0.010` | 1 | 2 |
| `max_notional_per_order=50` (certain breach) | **`DENIED_MAX_NOTIONAL`** | **0** | **0** |
| `max_notional_per_order=100000` | `SUBMITTED_...` | 1 | 2 |
| `risk_fraction=0.01` | `SUBMITTED_BRACKET_MARKET_BUY_0.045` | 1 | 2 |

So the cap engages on a breach and releases above it, and risk-fraction sizing
actually reaches the engine (0.045 BTC vs 0.010 flat on the same bar).

Two defects found and fixed while measuring:

1. **The denial reason was overwritten.** `max_notional_per_order` set
   `action = "DENIED_MAX_NOTIONAL"` and zeroed the size, and then the
   below-minimum check replaced it with `BELOW_MIN_QUANTITY` — so the brake fired
   but the ledger could not show *why*, and a risk denial was indistinguishable
   from an unusable size. The size-symptom label now only applies when no other
   decision was recorded.
2. **Risk-fraction sizing was inert in-engine.** `_account_equity` called
   `portfolio.account()` with no argument, which raises (`venue or account_id must
   be provided`) and was swallowed, so every sized run failed closed as
   `RISK_SIZING_NO_STOP_OR_EQUITY`. The venue is read from `instrument.id.venue`
   (`CryptoPerpetual` exposes no `venue` attribute in this build) and the balance
   falls back to a quote-currency lookup. Before: `RISK_SIZING_NO_STOP_OR_EQUITY`,
   0 positions. After: `0.045 BTC`, 1 position.

## Supporting change

`run_expert_strategy_backtest` now returns `fill_records` / `fill_report_type`.
Without the raw rows the maker/taker split and the commission per fill were
unreachable from this path, which is what made the F3 acceptance unmeasurable.

## Suite

`837 passed` (0 failed) after these changes, from `v8-next/`.
