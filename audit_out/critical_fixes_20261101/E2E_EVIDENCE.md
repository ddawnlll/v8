# End-to-end evidence — real producer runs on a real venue tape

All three artefacts below come from `v8_next.app.portfolio` itself, never from hand-edited JSON.

## Tape provenance

The canonical tapes (`research/tape/quad-1h-12m`, `btcusdt-1h-12m`) are absent from this checkout,
so a real one was built with the shipped tool from sha256-verified Binance Vision archives:

```
uv run --project v8-next python tools/vision_backfill.py \
    --symbol {BTCUSDT,ETHUSDT,SOLUSDT,AVAXUSDT} --interval 1h --month 2025-07 \
    --channel {kline,funding} --out <tmp>/<symbol> --download
# 4 legs x 744 bars = 2976 kline rows, plus 372 funding rows (2025-07), merged in
# chronological order so both channel shapes are inside polars' schema-infer window.
```

- merged tape: `e2e/quad-1h-2025-07_tape.jsonl` sha256 `5905f47673c1bbd49519b1360ee41ba6f6a2280571970848f53ee390749938b5`
- window: 2025-07-01 .. 2025-07-22, `--profile benchmark` — the same window the committed
  `docs/evidence/v87/NX02/bound_receipt_after.json` records (`period_start_ns 1751331600000000000`).

## #477 R4 — the canonical bound receipt re-taken through its own producer

Receipt `e2e/477_post/economic_receipt_54709848.json` sha256 `2dd26474c33a0f0541c73e1849f95735b1315e5e63609cd18615c394dc2401da`.

| entry | committed receipt (pre-fix) | re-taken receipt (post-fix) |
|---|---|---|
| thr 1% | `MEASURED_LINEAR_BOUND`, **no `status` key** | `PROJECTED_LINEAR_BOUND`, `UNRESOLVED` / `OBSERVED_FILLS_AT_OTHER_SCALE` |
| thr 5% | `MEASURED_LINEAR_BOUND`, no `status` | `PROJECTED_LINEAR_BOUND`, `UNRESOLVED` |
| thr 10% | `MEASURED_LINEAR_BOUND`, no `status` | `PROJECTED_LINEAR_BOUND`, `UNRESOLVED` |
| k=0.1 / 0.5 / 1.0 | `HYPOTHETICAL_SCENARIO`, no `status` | `NO_ECONOMIC_CLAIM` / `HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED` |

Observed `capacity_scenarios[*].status` in this run, read from the emitted receipt:

- `PROJECTED_LINEAR_BOUND` → status=`UNRESOLVED` reason=`OBSERVED_FILLS_AT_OTHER_SCALE`
- `PROJECTED_LINEAR_BOUND` → status=`UNRESOLVED` reason=`OBSERVED_FILLS_AT_OTHER_SCALE`
- `PROJECTED_LINEAR_BOUND` → status=`UNRESOLVED` reason=`OBSERVED_FILLS_AT_OTHER_SCALE`
- `HYPOTHETICAL_SCENARIO` → status=`NO_ECONOMIC_CLAIM` reason=`HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED`
- `HYPOTHETICAL_SCENARIO` → status=`NO_ECONOMIC_CLAIM` reason=`HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED`
- `HYPOTHETICAL_SCENARIO` → status=`NO_ECONOMIC_CLAIM` reason=`HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED`

**6 of 6 entries carry a contract status** — gate 2 of #477 now passes on a real emitted receipt,
not just on a re-derivation. `claim_status` stays `NO_ECONOMIC_CLAIM`.

## #495 gates 2 and 3 — the canonical receipt publishes the renamed cell *with its basis*

Ledger entry `e2e/495_post/benchmark_ledger.jsonl` sha256 `797b32023aa2166d1a197d46c9159acb1d446fd944615d4046fc1b2360c3c97d`.

- gate keys: `['g3_scenario_robustness']` → `['BLOCKED']`
- `g3_benchmark_coverage` present anywhere in the entry: `False`
- `g3_scenario_robustness_basis` present: `True`
- basis state: `BLOCKED`; regimes: `['Bear Crash', 'Bull Trend', 'Chop/Range', 'High-Vol Spill']`
- per-regime measurements carried: `['bars', 'max_drawdown', 'return_variance', 'trades']`

The state is `BLOCKED`, not `PASS`: every regime recorded `trades: 0`, so the resolver fails closed.
That is the point — R3 requires the *measured inputs* to travel with whatever state is published, and
a reader can now reproduce the BLOCKED verdict from the receipt alone instead of guessing at a bare cell.

Dashboard: `site/app.html` no longer asks for the pre-rename key (see `494fcbc`); it reads
`g3_scenario_robustness` and keeps `g3_benchmark_coverage` only as a fallback for stored ledgers.

## #491 R3 — re-published path statistics with the pre/post delta

Same tape, same window, same command; pre = clean `main@a921da2` (`economic_receipt_8f7c0e85.json`),
post = branch `codex/issue-491-exit-leg-mark` (`economic_receipt_359137b6.json`).

| metric | curve | pre (a921da2) | post (#503) | delta |
|---|---|---|---|---|
| max_drawdown | portfolio_P | -0.00685479 | -0.0111552 | -0.00430037 |
| sharpe_per_bar | portfolio_P | 0.0261244 | 0.0214807 | -0.0046438 |
| sharpe_ci_low | portfolio_P | -3.92949 | -7.68435 | -3.75485 |
| sharpe_ci_high | portfolio_P | 8.87372 | 9.52036 | 0.646644 |
| tail_mean_5pct | portfolio_P | -0.00122618 | -0.0014057 | -0.000179522 |
| excess_vs_primary | portfolio_P | -0.308018 | -0.308018 | -8.28226e-14 |
| max_drawdown | portfolio_PE | -0.00348082 | -0.00631568 | -0.00283486 |
| sharpe_per_bar | portfolio_PE | 0.0273587 | 0.0184964 | -0.00886235 |
| sharpe_ci_low | portfolio_PE | -3.78728 | -9.13766 | -5.35038 |
| sharpe_ci_high | portfolio_PE | 9.17939 | 8.82988 | -0.349506 |
| tail_mean_5pct | portfolio_PE | -0.000562839 | -0.000692763 | -0.000129924 |
| excess_vs_primary | portfolio_PE | -0.31179 | -0.31179 | -2.55351e-14 |

Drawdown roughly doubles in magnitude and Sharpe falls on both curves: the pre-fix path was
flattening the exits that were never marked. `claim_status` is `NO_ECONOMIC_CLAIM` in both runs —
this is a measurement correction, not a claim.

## What this does *not* prove

- The tape is real but **not** the canonical `quad-1h-12m` 12-month file; it is a 4-leg, one-month
  rebuild of the same venue data for the same July-2025 window. Numbers are not comparable to the
  committed canonical receipts, and nothing here is offered as one.
- The #491 delta is one window. It shows direction and magnitude, not a distribution.

## Addendum — the #491 residual identity on this same window

The auditor was right that the identity must be checked on real data, not only synthetically. With the
identity now published (`77f6576`), the same receipt reports:

```
portfolio_P    UNEXPLAINED_RESIDUAL  unexplained= 5.8050 USDT  (tolerance 0.05)
portfolio_PE   UNEXPLAINED_RESIDUAL  unexplained=22.5040 USDT  (tolerance 0.05)
```

So R2's "residual = fees + funding by construction" is **not achieved** on a real window, and #491 is
reported as PARTIAL. What the fix does deliver is the issue's §14 behaviour: the unexplained remainder
is published by name with its magnitude instead of being smeared into the graft as if it were cost.
Raw output: `491_identity_states.txt`; receipt: `e2e/491_post_identity/`.
