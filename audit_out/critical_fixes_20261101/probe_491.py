"""Re-derivation probe for #491 — does a closed campaign's exit leg enter equity_mtm?

Read-only: imports the real builders, feeds them the exact campaign the issue
specifies, prints equity_mtm / published equity / drift. Writes nothing into the repo.

Gate from the issue (verbatim):
  one campaign, entry 100 @ bar 1, close 110 @ bar 2, closes 100/105/120,
  taker_fee=0, capital=1000
  expected equity_mtm == [1000.0, 1005.0, 1010.0], adjustment == 0.0
  observed today  equity_mtm == [1000.0, 1005.0, 1005.0], drift == 2.5
"""

from v8_next.evaluation.economic_benchmark import (
    BarView,
    portfolio_series_from_engine,
    strategy_series_from_engine,
)

CLOSES = [100.0, 105.0, 120.0]
END_NS = [1_000, 2_000, 3_000]
CAPITAL = 1000.0
QTY = 1.0
ENTRY_PX = 100.0
EXIT_PX = 110.0

bars = [BarView(end_ns=ns, open=c, high=c, low=c, close=c) for ns, c in zip(END_NS, CLOSES)]

open_pos = {
    "instrument_id": "BTCUSDT",
    "position_id": "P-1",
    "quantity": QTY,
    "side": "LONG",
    "avg_px_open": ENTRY_PX,
    "event_ns": END_NS[1],
}
close_pos = {
    "instrument_id": "BTCUSDT",
    "position_id": "P-1",
    "quantity": QTY,
    "side": "LONG",
    "avg_px_open": ENTRY_PX,
    "avg_px_close": EXIT_PX,
    "realized_pnl": f"{QTY * (EXIT_PX - ENTRY_PX):.6f} USDT",
    "event_ns": END_NS[2],
}

# 1000 + 1*(110-100) = 1010 with taker_fee=0
BALANCE = CAPITAL + QTY * (EXIT_PX - ENTRY_PX)
engine_result = {
    "opened_positions": [open_pos],
    "closed_positions": [close_pos],
    "account": {"balance_total": f"{BALANCE:.6f} USDT", "positions": []},
}
EXPECTED = [1000.0, 1005.0, 1010.0]


def report(name, mtm, eq, drift):
    gap = eq[-1] - mtm[-1]
    exit_leg = QTY * (EXIT_PX - CLOSES[1])
    print(f"--- {name}")
    print(f"  equity_mtm    : {[round(x, 6) for x in mtm]}")
    print(f"  equity        : {[round(x, 6) for x in eq]}")
    print(f"  drift/bar     : {round(drift, 6)}")
    print(f"  terminal gap  : {round(gap, 6)}")
    print(f"  exit leg P&L missing from the mark (bar 2) : {round(exit_leg, 6)}")
    print(f"  truth         : {EXPECTED}")
    ok = [round(x, 6) for x in mtm] == EXPECTED and abs(drift) < 1e-12
    print(f"  ISSUE GATE 1  : {'PASS' if ok else 'FAIL'}")
    return ok


s = strategy_series_from_engine(engine_result, bars, capital=CAPITAL, taker_fee=0.0)
g1 = report("strategy_series_from_engine", s["equity_mtm"], s["equity"], s["reconciliation_adjustment_per_bar"])

p = portfolio_series_from_engine(
    engine_result,
    {"BTCUSDT": CLOSES},
    END_NS,
    capital=CAPITAL,
    taker_fee=0.0,
)
g2 = report("portfolio_series_from_engine", p["equity_mtm"], p["equity"], p["reconciliation_adjustment_per_bar"])

print()
print("VERDICT:", "CONFIRMED — the exit leg is missing from both mark paths, and the terminal gap "
      "is smeared as a uniform per-bar drift." if not (g1 and g2) else "REFUTED — both gates pass on current main.")
