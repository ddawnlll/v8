# #491 evidence — closed campaign exit leg booked into `equity_mtm`

PR [#503](https://github.com/ddawnlll/v8/pull/503) · branch `codex/issue-491-exit-leg-mark` · commit `822b1a3`

Claim re-derived **before** any code was written (`491_rederivation.md`): the original audit had
returned `NOT_IDENTIFIABLE` because the issue's cited lines had drifted ~450 lines. Re-derived by
symbol, verdict `CONFIRMED`.

## Gate 1 (the issue's exact synthetic campaign) — orchestrator's own probe

`probe_491.py`, my own fixture, calling the real builders (not the branch's tests):

```
main    strategy  equity_mtm [1000.0, 1005.0, 1005.0]  equity [1000.0, 1007.5, 1010.0]  drift 2.5  FAIL
main    portfolio equity_mtm [1000.0, 1005.0, 1005.0]  equity [1000.0, 1007.5, 1010.0]  drift 2.5  FAIL
branch  strategy  equity_mtm [1000.0, 1005.0, 1010.0]  equity [1000.0, 1005.0, 1010.0]  drift 0.0  PASS
branch  portfolio equity_mtm [1000.0, 1005.0, 1010.0]  equity [1000.0, 1005.0, 1010.0]  drift 0.0  PASS
```

Exact, no tolerance, and the pre-fix numbers are byte-identical to the ones the issue reported.

## Branch regression tests

`tests/test_equity_exit_leg_491.py`, 6 nodes:

| against | result |
|---|---|
| clean `main@a921da2` (test file copied into the baseline checkout) | **6 failed**, `KeyError: 'exit_leg_identity'` |
| branch | **6 passed** in 0.60s |

The tests assert the numeric curve (`ser["equity_mtm"] == [1000.0, 1005.0, 1010.0]`,
`reconciliation_adjustment_per_bar == 0.0`), not merely the presence of a new field.

## The change

- `strategy_series_from_engine`: `exit_step += qd * (px - closes[i - 1])` on the close event,
  accumulated before `qty = 0.0`, and added to the bar's equity append.
  `px` is the engine's `avg_px_close` or the documented bar-close proxy already counted in
  `bar_close_proxy_exits` — measured, never imputed.
- `portfolio_series_from_engine`: same booking before `live.pop` / `prev_mtm.pop`, with
  `step_pnl = exit_step` seeding the per-bar loop.
- New `_graft_residual_identity(...)` publishes `EXPLAINED_BY_EXCLUDED_COSTS` /
  `UNEXPLAINED_RESIDUAL` / `NOT_MEASURED` with `EQUITY_MTM_IDENTITY_ATOL = 0.05`, replacing the
  graft's previously *assumed* meaning with an asserted one. The uniform `drift` amortisation itself
  is untouched (the issue declares it out of scope).

Full suite on the branch: **1013 passed, 9 skipped** (baseline 1007 + 6 new). `ruff` clean.

## R3 — DELIVERED: re-published path statistics with the pre/post delta

Same tape, same window, same producer command; pre on clean `main@a921da2`, post on this branch. The
tape is a real 4-leg Binance Vision rebuild for 2025-07-01..2025-07-22 (`tools/vision_backfill.py
--download`), not hand-made.

| metric | curve | pre (a921da2) | post (#503) | delta |
|---|---|---|---|---|
| max_drawdown | portfolio_P | -0.00685479 | -0.0111552 | **-0.00430037** |
| sharpe_per_bar | portfolio_P | 0.0261244 | 0.0214807 | -0.0046438 |
| sharpe_ci_low | portfolio_P | -3.92949 | -7.68435 | -3.75485 |
| sharpe_ci_high | portfolio_P | 8.87372 | 9.52036 | 0.646644 |
| tail_mean_5pct | portfolio_P | -0.00122618 | -0.0014057 | -0.000179522 |
| max_drawdown | portfolio_PE | -0.00348082 | -0.00631568 | **-0.00283486** |
| sharpe_per_bar | portfolio_PE | 0.0273587 | 0.0184964 | -0.00886235 |
| sharpe_ci_low | portfolio_PE | -3.78728 | -9.13766 | -5.35038 |
| sharpe_ci_high | portfolio_PE | 9.17939 | 8.82988 | -0.349506 |
| tail_mean_5pct | portfolio_PE | -0.000562839 | -0.000692763 | -0.000129924 |

`excess_vs_primary` unchanged to 1e-13 on both curves. Drawdown roughly doubles and Sharpe falls: the
pre-fix path was flattening the exits it never marked. `claim_status` is `NO_ECONOMIC_CLAIM` in both
runs — a measurement correction, not a claim. Artifacts: `e2e/491_pre/`, `e2e/491_post/`,
`E2E_EVIDENCE.md`.

Known limit stated plainly: the strategy-path residual identity passes `funding=None` because that
builder is not fed funding events in this scope (documented since #436); the portfolio builder carries
funding explicitly. One window is one window — this is direction and magnitude, not a distribution.

## Known adjacent defect (not in scope, recorded so it is not lost)

Both builders iterate `for i in range(1, n)` over `events`, so an event stamped on **bar index 0** is
never applied — `pair_positions` pairs it, `events[0]` is populated, and nothing reads index 0. In my
first probe attempt this silently flattened a whole campaign into the drift graft. Deserves its own
card.

---

# R2 — PARTIAL, and the earlier "PASS" was wrong

Two defects, both found by the fifth audit, both real:

1. **The identity never reached the receipt.** The builders computed `exit_leg_identity` and
   `published_cost_reconciliation()` silently dropped it — 0 occurrences in the economic receipt, the
   forensic HTML and the markdown report. Fixed in `77f6576`: it is published with each curve, and
   `test_published_cost_reconciliation_carries_the_exit_leg_identity` fails on the previous commit
   (`KeyError`) and passes now.

2. **The equality does not hold on real data.** Running the producer on a real 4-leg Binance Vision
   tape (2025-07-01..2025-07-22) yields `491_identity_states.txt`:

```
portfolio_P    state=UNEXPLAINED_RESIDUAL  gap=37.4161 expected=31.6111 unexplained= 5.8050
portfolio_PE   state=UNEXPLAINED_RESIDUAL  gap=39.5225 expected=17.0185 unexplained=22.5040
               terms: commission 22.2224 / 12.4283, funding -4.2792 / -2.2184,
                      open_unrealized 13.6679 / 6.8085, tolerance 0.05
```

So R2's requirement — "the graft residual is fees + funding by construction" — is **not achieved** on a
real window; 5.81 and 22.50 USDT remain unexplained. The engine balances on actual fills and on funding
charged against notional, while the mark path marks open positions at bar close and closed ones at
`avg_px_close`; on this window that difference is not reducible to commission + funding + open
unrealized.

What *is* correct, and is now both implemented and published, is the issue's own §14 Canonical Failure
Semantics: "a residual not explainable by fees + funding publishes a named non-reconciling state
instead of a graft that presents it as cost." That is exactly what the receipt now carries.

**Corrected verdict: #491 = PARTIAL — R1, R3 and R4 delivered; R2 fails its equality and is published
as a named non-reconciling state.** PR #503 therefore says `Refs #491 — do not close on merge`. The
synthetic 3-bar gate still passes exactly (`[1000, 1005, 1010]`, drift 0.0, both builders), and the
synthetic test's docstring now says plainly that the synthetic equality is not evidence about the real
residual.

---

# R2 — why the equality cannot be met on the data available here

A second measurement (smoke profile, 336 bars, same tape) reproduces the pattern:

```
portfolio_P   cost_basis=MISMATCH  UNEXPLAINED_RESIDUAL  gap 5.3856  expected 1.6798  unexplained  3.7058
portfolio_PE  cost_basis=MISMATCH  UNEXPLAINED_RESIDUAL  gap 20.8995 expected 1.6502  unexplained 19.2493
```

In both windows the run's own closed loop is already `cost_basis: MISMATCH`
(`closed_loop_terms.residual_usdt` -0.407 / -0.203 on the benchmark window). R2's equality is an
identity on `balance_total`; when the engine's closed loop does not itself reconcile on the window, the
identity's premise is false and no term bookkeeping can make the residual equal fees + funding.

So the honest ordering is:

1. the closed loop must reach `VERIFIED_ENGINE` on a window before R2's equality can be asserted at
   all, and it does not on any window this checkout can build;
2. until then, the correct behaviour — which is implemented and published — is the issue's §14 named
   non-reconciling state carrying the unexplained magnitude.

This is recorded as a blocker, not as a pass. Artifacts: `e2e/491_smoke/`, `491_identity_states.txt`.
