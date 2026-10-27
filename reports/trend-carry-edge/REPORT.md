# Trend + funding-carry + XS-momentum study (NO_ECONOMIC_CLAIM)

Data: 3108 Binance Vision archives, 2020-01-01 → 2026-09-30, 20 UM perpetuals; archive-set sha256 `78f321e2b377ea1b…`.

| window | Sharpe ± SE | ann. return | vol | CAGR | max DD | days |
|---|---|---|---|---|---|---|
| full | +1.13 ± 0.39 | +14.5% | 12.8% | +14.7% | -17.8% | 2405 |
| in-sample 2020–2023 | +1.10 ± 0.51 | +13.4% | 12.2% | +13.5% | -17.8% | 1401 |
| post-design 2024+ | +1.17 ± 0.60 | +16.0% | 13.6% | +16.3% | -7.9% | 1004 |
| 2020 | +1.48 ± 1.09 | +14.2% | 9.6% | +14.7% | -8.1% | 306 |
| 2021 | +2.66 ± 1.00 | +36.6% | 13.8% | +42.9% | -8.1% | 365 |
| 2022 | -0.27 ± 1.00 | -3.4% | 12.3% | -4.0% | -13.9% | 365 |
| 2023 | +0.51 ± 1.00 | +6.2% | 12.2% | +5.6% | -9.0% | 365 |
| 2024 | +0.67 ± 1.00 | +9.2% | 13.8% | +8.6% | -7.9% | 366 |
| 2025 | +1.64 ± 1.00 | +20.5% | 12.5% | +21.8% | -7.4% | 365 |
| 2026 | +1.29 ± 1.16 | +19.2% | 14.9% | +19.8% | -6.8% | 273 |

Bootstrap 95% CI of Sharpe (circular block 20d): full [0.37797910013659014, 1.8315638381398927], post-design [0.11848627882734757, 2.228198072166796].
Positive months: 49/79. BTC beta -0.046. Mean daily turnover 0.137.
Annual components: price +15.5%, funding +2.5%, cost -3.5%.

## Stress
| window | Sharpe ± SE | ann. return | vol | CAGR | max DD | days |
|---|---|---|---|---|---|---|
| cost_x2 | +0.86 ± 0.39 | +11.0% | 12.8% | +10.7% | -21.2% | 2405 |
| cost_x3 | +0.59 ± 0.39 | +7.5% | 12.8% | +6.9% | -24.6% | 2405 |
| lag_2_days | +0.86 ± 0.39 | +11.2% | 12.9% | +10.9% | -21.4% | 2405 |
| cost_x2_post_design | +0.88 ± 0.60 | +12.0% | 13.6% | +11.7% | -8.7% | 1004 |

## Sleeves
| sleeve | IS Sharpe | post-design Sharpe |
|---|---|---|
| trend | +0.71 | +0.72 |
| carry | +0.20 | +1.53 |
| xs_momentum | +0.98 | -0.03 |

Sleeve correlation (trend, carry, xs_momentum): [[1.0, 0.063, 0.049], [0.063, 1.0, 0.063], [0.049, 0.063, 1.0]]

## Multiple-testing diagnostics over the registered family
Family size 33 (every explored variant).
- DSR confidence `full_portfolio_trend_carry_xsmom_all`: 0.0288 (expected max null annualised SR 1.87, family 33)
- DSR confidence `full_portfolio_trend_carry_xsmom_excluding_sign_mirrors`: 0.8787 (expected max null annualised SR 0.68, family 31)
- DSR confidence `full_portfolio_trendlong_carrydaily_all`: 0.2613 (expected max null annualised SR 1.87, family 33)
- DSR confidence `full_portfolio_trendlong_carrydaily_excluding_sign_mirrors`: 0.9936 (expected max null annualised SR 0.68, family 31)
- DSR confidence `post_design_portfolio_trend_carry_xsmom_all`: 0.0524 (expected max null annualised SR 2.17, family 33)
- DSR confidence `post_design_portfolio_trend_carry_xsmom_excluding_sign_mirrors`: 0.4120 (expected max null annualised SR 1.31, family 31)
- DSR confidence `post_design_portfolio_trendlong_carrydaily_all`: 0.2951 (expected max null annualised SR 2.17, family 33)
- DSR confidence `post_design_portfolio_trendlong_carrydaily_excluding_sign_mirrors`: 0.8241 (expected max null annualised SR 1.31, family 31)
- White reality check p (full): 0.0625
- White reality check p (post_design): 0.42
- CSCV PBO: 0.14285714285714285

## In-sample-best variant: `portfolio_trendlong_carrydaily` (BTC beta +0.082)
| window | Sharpe ± SE | ann. return | vol | CAGR | max DD | days |
|---|---|---|---|---|---|---|
| 2020 | +1.84 ± 1.09 | +24.6% | 13.4% | +26.8% | -8.9% | 306 |
| 2021 | +3.57 ± 1.01 | +65.5% | 18.4% | +89.2% | -10.2% | 365 |
| 2022 | -1.44 ± 1.00 | -13.5% | 9.3% | -13.0% | -18.3% | 365 |
| 2023 | +0.53 ± 1.00 | +7.6% | 14.3% | +6.8% | -10.9% | 365 |
| 2024 | +2.78 ± 1.00 | +46.2% | 16.6% | +56.5% | -9.3% | 366 |
| 2025 | +1.01 ± 1.00 | +13.1% | 12.9% | +13.0% | -8.9% | 365 |
| 2026 | +1.44 ± 1.16 | +17.6% | 12.2% | +18.4% | -6.0% | 273 |

## Family
| variant | full SR | IS SR | post-design SR |
|---|---|---|---|
| buy_hold_volscaled | +0.74 | +0.95 | +0.46 |
| carry_lb14_rb1 | +0.96 | +0.52 | +1.59 |
| carry_lb14_rb14 | +0.52 | +0.43 | +0.64 |
| carry_lb14_rb3 | +0.96 | +0.59 | +1.46 |
| carry_lb14_rb7 | +0.91 | +0.66 | +1.28 |
| carry_lb30_rb1 | +0.89 | +0.52 | +1.39 |
| carry_lb30_rb14 | +0.51 | +0.28 | +0.83 |
| carry_lb30_rb3 | +0.93 | +0.55 | +1.41 |
| carry_lb30_rb7 | +0.93 | +0.63 | +1.32 |
| carry_lb3_rb1 | +0.66 | +0.74 | +0.54 |
| carry_lb3_rb14 | +0.54 | +0.71 | +0.27 |
| carry_lb3_rb3 | +0.69 | +0.79 | +0.56 |
| carry_lb3_rb7 | +0.86 | +0.81 | +0.94 |
| carry_lb7_rb1 | +0.95 | +0.62 | +1.40 |
| carry_lb7_rb14 | +0.45 | +0.16 | +0.88 |
| carry_lb7_rb3 | +0.92 | +0.50 | +1.44 |
| carry_lb7_rb7 | +0.75 | +0.20 | +1.53 |
| portfolio_trend_carry | +1.01 | +0.64 | +1.49 |
| portfolio_trend_carry_xsmom | +1.13 | +1.10 | +1.17 |
| portfolio_trendlong_carry | +1.47 | +1.15 | +1.94 |
| portfolio_trendlong_carrydaily | +1.63 | +1.46 | +1.86 |
| tsmom_ens_long | +1.26 | +1.39 | +1.09 |
| tsmom_ens_ls | +0.71 | +0.71 | +0.72 |
| tsmom_ls_lb10 | +0.27 | +0.54 | -0.11 |
| tsmom_ls_lb120 | +0.49 | +0.59 | +0.37 |
| tsmom_ls_lb20 | +0.65 | +0.68 | +0.61 |
| tsmom_ls_lb60 | +0.52 | +0.37 | +0.72 |
| xsmom_lb14 | +0.51 | +0.72 | +0.21 |
| xsmom_lb30 | +0.29 | +0.84 | -0.48 |
| xsmom_lb60 | +0.53 | +0.98 | -0.03 |
| xsmom_lb7 | +0.31 | +0.71 | -0.22 |
| xsrev_lb1 | -3.12 | -3.12 | -3.13 |
| xsrev_lb3 | -2.07 | -2.25 | -1.81 |

## Limitations
- Universe chosen with present-day knowledge (survivorship bias).
- Fees/slippage are a declared assumption; fills at the daily close; no book data.
- Post-design window was observed during design (not a sealed holdout).
- Simulated constant-capital returns; not venue cash settlement. NO_ECONOMIC_CLAIM.
