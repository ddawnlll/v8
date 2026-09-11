# Epic #399 — NautilusTrader infrastructure transition: phase plan

Owner objective: phases F1–F6 (#400–#405) all land on `main`, each independently
closable, each with deterministic tests plus a measurement on the real tape.
Installed authority: `nautilus-trader==2.0.0rc4` (verified API surface below).

Discipline held throughout: deterministic test + hash-bound run + fail-closed.
A value that cannot be measured is published absent with a named reason — never
as zero, never as a placeholder.

## Ordering and why

```
F1 #400 TradeTick + aggressor fill ──► F2 #401 L2/L3 book ──► F3 #402 order variety + emulator
                                                                      │
                                                                      ▼
                                                              F4 #403 TWAP/VWAP
F5 #404 RiskEngine + margin (independent of F1–F4; touches the account/venue config)
F6 #405 catalog/BacktestNode + sandbox + venue #2 (independent; wraps a completed run)
```

* F2 before F3: a passive/maker fill needs a book with displayed depth to fill
  against; without depth the maker path is another inert knob.
* F3 before F4: child-order slicing (TWAP) only means something once LIMIT/STOP
  orders and an emulator exist to slice into.
* F5/F6 have no prerequisite inside the chain, but both touch
  `portfolio_backtest.py`'s venue/account construction, so they land after the
  F1–F4 execution-surface edits to avoid rewriting the same call sites twice.

## Per-phase contract

| Phase | Deliverable | Acceptance (machine-checked) |
|---|---|---|
| F1 #400 | TradeTick capture (REST pages + signed daily archives + live `stream.py`), `trades=` feed into the shared account | real bar tape: bar-only vs bar+trade produce different fills stamped at real prints; two trade-fed runs bit-identical. **DONE — see `2026-09-11_nautilus-f1-trade-execution.md`** |
| F2 #401 | L2 capture (depth snapshot/diff) → `OrderBookDelta` feed, `BookType.L2_MBP` venue profile | same L2 feed → same `fill_signature`; `queue_position` / `liquidity_consumption` **change** the signature (they were published as `inert_knobs_without_depth_data`) |
| F3 #402 | LIMIT/STOP_MARKET (+ emulator) order generation, maker/taker split visible in the fill report | same feed → same fill set; maker fill ratio and rebate effect reported as numbers |
| F4 #403 | `ExecutionAlgorithm` (TWAP) child-order slicing, selectable as a profile parameter | same plan → same child fill sequence; sliced vs single-print implementation shortfall difference with numbers |
| F5 #404 | NT `RiskEngine` limits bound to the account + margin model (`StandardMarginModel`/`LeveragedMarginModel`), swap/rollover cost | same run → same risk-decision sequence; a limit-breach scenario shows the brake engaging, with the run that proves it |
| F6 #405 | `ParquetDataCatalog` + `BacktestNode`/`BacktestRunConfig` batch run, sandbox mode, ≥1 additional venue adapter (data) + live-reconciliation design | deterministic test: same data from the catalog → same result hash; batch run time + sandbox/live data-match report |

## API surface verified present in 2.0.0rc4

`nautilus_trader.trading.ExecutionAlgorithm` (+ `ExecutionAlgorithmConfig`),
`execution.OrderEmulatorConfig`, `risk.RiskEngineConfig` + `risk.FixedRiskSizer`,
`model.StandardMarginModel` / `model.LeveragedMarginModel`,
`model.OrderBookDelta` / `OrderBookDeltas` / `OrderBookDepth10` / `BookType`,
`persistence.ParquetDataCatalog` + `OrderBookDeltaDataWrangler` / `BarDataWrangler`,
`backtest.BacktestNode` / `BacktestRunConfig` / `BacktestDataConfig` /
`BacktestVenueConfig`, `backtest.CfdSwapModule`, adapters `sandbox`, `bybit`,
`okx`, `binance`, `tardis`.

## Dedup / reference discipline

These issues are **referenced, not closed** by this epic — they own adjacent
questions and must not be double-counted as this work:

* **#379** venue fills / latency / shortfall reconciliation (venue truth, G8) —
  F3's maker/taker split and F6's reconciliation design feed it; they do not
  satisfy it.
* **#380** funding accuracy — untouched here; F5's swap/margin cost is a *modelled*
  cost, distinct from funding settling from a real tape row.
* **#381** P+E execution semantics — F1–F4 change the execution layer under both
  curves; no P/P+E verdict semantics are touched.
* **#382** capacity / L2 impact — F2 converts the depth-conditioned measurement
  from "inert" to "measurable"; the capacity conclusion stays #382's.
* **#385** venue-cost calibration — F1–F4 produce *measured model* friction, not
  calibrated venue cost; #385 consumes them.
* **#398** `ExecutionFidelity` constant 0.50 — the clip/reference defect stays a
  separate defect; no scoring change is made inside this epic.
* **#396/#397/#394/#395** reporting defects — untouched.

Rule: a phase may cite a reference issue's measurement as an *input*; it may not
mark that issue resolved.
