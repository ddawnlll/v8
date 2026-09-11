# Economic Benchmark Coverage (PDF v8 Profesyonel Benchmark Arastirmasi)

Source: `docs/V8_Profesyonel_Benchmark_Arastirmasi.pdf` (sibling-placed copy of the
user-supplied research report). Each applicable recommendation maps to real code
and the canonical flow. Status is DONE, OPEN (software work remaining), or
BLOCKED_EXTERNAL (needs venue records, credentials, or a human capital decision).
No synthetic fallback is accepted anywhere below.

Canonical reproduction (`--extra research` is required: `scipy`/`arch` are
optional dependencies, and without them every estimator fails closed and
`statistical` degrades to `UNSUPPORTED` on a fresh sync):
`uv run --project v8-next --extra research python -m v8_next.app.cli benchmark-portfolio
--tape-path research/tape/quad-1h-12m --bars 385 --output-dir artifacts/portfolio-benchmark
--primary equal_weight`

## 1. Decision structure (no single Sharpe/DSR threshold)

| PDF recommendation | Code + flow | Status |
|---|---|---|
| Six separate outcomes (research validity, economic, statistical, portfolio, execution, capital) instead of one PASS | `evaluation/economic_benchmark.py::build_verdicts`; rendered in `economic_report_*.md` | DONE |
| Missing information is neither success nor loss | `INVALID`/`INCONCLUSIVE`/`UNDERPOWERED`/`UNRUN` states; `test_*_invalid_data*`, `test_*_failed_estimators*` | DONE |
| No copied corporate thresholds | No DSR/PBO cutoff gates; preregistered rules in `economic_benchmark.py` (`SPA_EDGE_ALPHA`, `DSR_EDGE_CONFIDENCE`, `EXCESS_CI_RULE`) | DONE |

## 2. Documented firm practices

| PDF lesson | Code + flow | Status |
|---|---|---|
| AQR: calibrate cost models on realized fills, no fixed bps | Fill-level commission attribution reconciled to engine totals (`portfolio_series_from_engine`, `cost_basis`) | DONE |
| Two Sigma: measure the expert's incremental portfolio change, not standalone Sharpe | Engine-level P vs P+E shared-account rerun (`adapters/portfolio_backtest.py`, `app/portfolio.py`) | DONE |
| Man AHL: netting, shared capital, rejected orders revalued in the union account | One MARGIN/NETTING account, `trade_signature` parity, canceled-order path preserved in engine records | DONE |
| Winton: declare the investment role up front | Pre-declared `--primary` (default `equal_weight`); role recorded in `RunIdentity` before any computation | DONE |

## 3. AlphaTrend controls (positive/negative/defect/ablation/ambiguous)

| Experiment | Code + flow | Status |
|---|---|---|
| Positive control (known effect, stated power) | `positive_control_known_effect` (SYNTHETIC_CONTROL labeled) | DONE |
| Negative control (shuffled link, costs kept) | `negative_control_shuffled`; must not declare a winner | DONE |
| Known defect (future leak, bad funding, zero-latency fills) | `detect_future_leak` probe; mark-proxy labeled; latency unmodeled pins execution to SIM_ONLY | DONE |
| Component ablation (same budget, on/off) | Contradiction-tolerance gate 28->0 at 50/50 sleeves, same per-leg budget | DONE |
| Ambiguous real idea (frozen hypothesis, untouched test) | Frozen family on fit region; `--start-bar` untouched OOS window (see §7) | DONE |

## 4. Reference selection (CFA-style, purpose-bound)

| Benchmark | Code + flow | Status |
|---|---|---|
| cash | `compute_multileg_family["cash"]` | DONE |
| buy-and-hold per leg | `bh_<RAW>` (costed entry) | DONE |
| equal-weight basket (primary default) | `equal_weight`, 1/N bought once, no rebalance fiction | DONE |
| trailing-only vol-targeted basket | `vol_target`, 48-bar trailing vol, capped leverage, turnover paid | DONE |
| simple fixed trend rule | `simple_trend`, 48-bar Donchian long/flat per leg | DONE |
| incumbent V8 | `portfolio_P` engine run | DONE |
| No future-vol scaling, no post-hoc benchmark choice | All benchmarks use causal inputs only; primary fixed before compute | DONE |

## 5. Portfolio accounting and cost

| PDF recommendation | Code + flow | Status |
|---|---|---|
| P vs P+E under the same allocator and risk budget | Same per-leg notional, 50/50 sleeves, one account (`portfolio_backtest.py`) | DONE |
| Funding signs kept; no double-counted costs | Dual-run funding measurement under identical trade signatures; realized embeds funding (isolated finding locked in `test_mechanics_funding_measured_not_gapped`); open-entry commissions corrected | DONE |
| Engine holding convention pinned | Positions opened at the boundary bar ARE held, closed at the boundary bar are NOT (`open<=`, `close>`); exact 4-decimal match over the OOS window; locked in `test_funding_holding_convention_matches_engine` | DONE |
| Operating expenses reported separately | `opex_monthly_usd` in identity; business-net note in report limitations | DONE |
| Breakeven extra cost (net excess / notional) | Retained in single-leg flow; portfolio flow uses participation bounds instead | DONE |

## 6. Statistics (DSR/PBO/SPA with real inputs)

| PDF recommendation | Code + flow | Status |
|---|---|---|
| Real family curves, explicit plans, candidate vs family separation | `run_statistics` on engine/analytic curves; `DSRPlan`/`CSCVPlan`/SPA block-reps-seed explicit | DONE |
| Computation success never mints inferential support | `COMPUTED` verdict label; `SUPPORTS_EDGE`/`SUPPORTS_UNDERPERFORMANCE` only via preregistered rules | DONE |
| No universal cutoffs | Rules carry their levels openly (`0.05`, `0.95`); levels are declared, not corporate standards | DONE |
| Chronological OOS kept separate; relabeled holdouts banned | Frozen `--start-bar` OOS window (§7); in-window slice labeled `OOS_SLICE` diagnostic only | DONE (fit) / rule below |
| PBO window rule | Interval count must satisfy n%4==0 and n>=8 (e.g. 385/4321 bars -> 16/180 intervals); otherwise PBO stays UNDERPOWERED with reason | DONE |
| Trend benchmarks are causal | 1-bar lookahead found (+963% artifact) and removed; decision for bar i uses closed bar i-1 only; `test_mechanics_trend_benchmark_is_causal` | DONE |
| Environment carries the research extra | `arch`/`scipy` pruned once by a bare `uv sync`; restored via `uv sync --project v8-next --locked --extra dev --extra research`; stats fail UNSUPPORTED without it, never silently | DONE |

## 7. Evidence length, dependence, live verification

| PDF recommendation | Code + flow | Status |
|---|---|---|
| Dependence-preserving inference (joint blocks, no IID trade counts) | Stationary/circular block bootstrap; joint-column SPA resampling; CSCV partitions | DONE |
| Shadow/live comparison log | `adapters/shadow_ingest.py` (canonical format, fixture guard, source+command); `build_shadow_section` in portfolio flow | DONE (code) / BLOCKED_EXTERNAL (no venue account, no fills file) |
| Account reconciliation | `reconcile_shadow_account`; engine closed-loop balance checks | DONE (engine) / BLOCKED_EXTERNAL (venue side) |
| Full accessible quad period + frozen OOS | Fit `--bars 4321` (bars 0-4320, Jul-Dec 2025); OOS `--start-bar 4380 --bars 4321` (Jan-Jun 2026, never touched during development which used bars 0-500) | DONE (runs below) |

## 8. D-156 / parity priorities (#322/#323/#329 as starting points, verified)

| Item | Finding | Status |
|---|---|---|
| #322 proxy-DSR ban | Economic fabric never consumes G5's arithmetic-offset family; DSR runs on engine reruns only | DONE |
| #323 registered evaluator | Evaluator runs end-to-end via `benchmark-portfolio`; receipt binds into ledger | DONE |
| #329 two ledgers + semantic mapping | Engine-trades + canonical-dataset bindings per run tag; closed-loop mapping check | DONE |

## 9. Capital decisions

| PDF recommendation | Code + flow | Status |
|---|---|---|
| Score never allocates money; separate risk budget + exit conditions | `domain/capital_policy.py` (single source): file-or-unauthorized governing flow, TEST accept-path evidence, missing/live/wrong-instrument REJECT | DONE (code) |
| Production authorization | Human-signed approval required; no approval artifact exists | BLOCKED_EXTERNAL (human decision) |

## Explicitly not claimed

- Measured slippage/impact capacity (only HYPOTHETICAL k-grid scenarios; §capacity).
- Venue settlement of any fill (no live records).
- Profitability or readiness (receipts stay NO_ECONOMIC_CLAIM).
