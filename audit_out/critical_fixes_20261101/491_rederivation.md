# #491 re-derivation — does a closed campaign's exit leg enter `equity_mtm`?

**Verdict: `CONFIRMED`**

Base: `main` @ `a921da2fdfb8254619b78840f80e969324f7cdf1` · read-only (probe lives outside `v8-next/`, imports the real builders)
Reproduce: `cd v8-next && uv run python ../audit_out/critical_fixes_20261101/probe_491.py`

The prior audit marked this `NOT_IDENTIFIABLE` because the issue's cited coordinates
(`economic_benchmark.py:3149-3155`, `:3402-3429`, `:3602-3609`) had drifted. Re-deriving
**by symbol** resolves it: the code is where the issue says it is, under new line numbers.

## 1. The builders, by symbol (current lines)

| symbol | current line | issue's line | drift |
|---|---|---|---|
| `strategy_series_from_engine` | 2646 | 3134 | −488 |
| `portfolio_series_from_engine` | 2981 | 3402 | −421 |
| `pair_positions` | 1893 | — | — |
| `metrics_for_curve` | 3379 | — | — |

## 2. The dropped mark — `strategy_series_from_engine`

The close event zeroes the position *before* the exit price is ever used as a mark
(`economic_benchmark.py:2856-2860`):

```python
            else:
                qty = 0.0
                # #397: the exit leg pays the same fee on its own notional and
                # is therefore turnover, not a free close.
                turnover += abs(qd) * px / capital
                exit_turnover += abs(qd) * px / capital
                exit_fills += 1
        mtm = qty * (closes[i] - avg) if qty != 0.0 else 0.0
        equity.append(equity[-1] + mtm)
```

`qty = 0.0` ⇒ `mtm = 0.0` on the exit bar. The exit price is **measured and available** —
it is parsed at `:2804-2812` into `exit_price` (from `avg_px_close`, with the documented
bar-close proxy fallback and the `engine_priced_exits` / `bar_close_proxy_exits` counters) —
and is then used only for `turnover`/`exit_fills`. No `qd * (exit_px − prev_close)` ever
reaches `step_pnl`. This is exactly the issue's claim, verbatim.

The residual is then smeared (`:2871-2875`):

```python
    drift = (balance_total - equity[-1]) / max(1, n - 1)
    adj = [equity[0]]
    for i in range(1, n):
        adj.append(adj[-1] + (equity[i] - equity[i - 1]) + drift)
```

with the declared meaning still asserting the residual is "commissions + rounding"
(`:2865-2870`), which the dropped exit leg falsifies.

## 3. The dropped mark — `portfolio_series_from_engine`

Same defect, different route (`:3117-3138`): on a close event both the position and its
mark are popped before the per-bar loop can mark it.

```python
                live.pop(inst, None)
                prev_mtm.pop(inst, None)
```

and the MTM loop only accumulates what is still in `live`:

```python
        step_pnl = 0.0
        for inst, qd in live.items():
            mtm = qd * closes[inst][i]
            step_pnl += mtm - prev_mtm.get(inst, 0.0)
            prev_mtm[inst] = mtm
```

So the exit bar contributes `0` for that instrument. The identical uniform graft follows at
`:3263-3265`.

## 4. Reproduction — the issue's own gate 1, run on current `main`

The issue specifies: one campaign, entry 100 @ bar 1, close 110 @ bar 2, closes 100/105/120,
`taker_fee=0`, `capital=1000` ⇒ expect `equity_mtm == [1000.0, 1005.0, 1010.0]`,
`adjustment == 0.0`.

Real output from `probe_491.py` (no tolerance, no mocks of the builders):

```
--- strategy_series_from_engine
  equity_mtm    : [1000.0, 1005.0, 1005.0]
  equity        : [1000.0, 1007.5, 1010.0]
  drift/bar     : 2.5
  terminal gap  : 5.0
  exit leg P&L missing from the mark (bar 2) : 5.0
  truth         : [1000.0, 1005.0, 1010.0]
  ISSUE GATE 1  : FAIL
--- portfolio_series_from_engine
  equity_mtm    : [1000.0, 1005.0, 1005.0]
  equity        : [1000.0, 1007.5, 1010.0]
  drift/bar     : 2.5
  terminal gap  : 5.0
  exit leg P&L missing from the mark (bar 2) : 5.0
  truth         : [1000.0, 1005.0, 1010.0]
  ISSUE GATE 1  : FAIL
```

Byte-for-byte the numbers the issue reported (`[1000, 1005, 1005]`, `[1000, 1007.5, 1010]`,
drift `2.5`, gap `5.0`) — reproduced independently on `a921da2`, in **both** builders.
The `+5` exit leg is re-injected as `+2.5` on *every* bar, including the bar before the
position existed.

## 5. Incidental finding (not part of #491, worth its own card)

The first probe attempt put the open event on bar index 0. It was silently dropped: both
builders iterate `for i in range(1, n)` over `events`, so **any event stamped on the first
bar is never applied** — `pair_positions` pairs it fine, `events[0]` is populated, and then
nothing reads index 0. The whole campaign's P&L became drift. Not in scope here; noted so
it is not lost.

## 6. Consequence for the goal

`CONFIRMED` ⇒ task `fix-491` is unblocked and must ship a PR. Required end state per the
issue: book the exit segment at the engine's `avg_px_close` (fallback: the documented
bar-close proxy, already counted in `bar_close_proxy_exits`) **before** the position leaves
the mark book, in both builders; then assert the residual identity
`equity_mtm[-1] == balance_total + commissions_excluded + funding_excluded` in the receipt.
