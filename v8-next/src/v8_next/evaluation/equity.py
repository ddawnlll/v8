"""Diagnostic fixed-capital returns from complete native bar equity marks."""

from decimal import Decimal
from typing import Any

from v8_next.evaluation.alignment import IntervalLoss


def equity_losses(
    marks: list[dict[str, Any]], *, capital: Decimal, computed_ns: int
) -> tuple[IntervalLoss, ...]:
    """Negative equity increments / fixed initial capital, not compounded returns.

    First mark is the starting valuation, never an invented pre-data balance.
    Historical callback clocks are modeled; availability is computation time.
    No risk-free subtraction is implied, so these are not DSR excess returns.
    """
    if not capital.is_finite() or capital <= 0 or len(marks) < 2:
        raise ValueError("positive capital and at least two equity marks required")
    values = []
    times = []
    for mark in marks:
        if mark["phase"] != "PRE_STRATEGY_BAR_CALLBACK" or mark["currency"] != "USDT":
            raise ValueError("incompatible equity valuation convention")
        end = mark["end_ns"]
        observed = mark["observed_ns"]
        if (
            type(end) is not int
            or type(observed) is not int
            or not 0 <= end <= observed <= computed_ns
        ):
            raise ValueError("invalid equity observation chronology")
        cash, pnl, equity = (Decimal(mark[k]) for k in ("cash", "unrealized_pnl", "equity"))
        if not all(v.is_finite() for v in (cash, pnl, equity)) or cash + pnl != equity:
            raise ValueError("unreconciled or nonfinite equity mark")
        if not mark["source_hash"]:
            raise ValueError("missing equity source identity")
        times.append(end)
        values.append(equity)
    duration = times[1] - times[0]
    if duration <= 0 or any(b - a != duration for a, b in zip(times, times[1:], strict=False)):
        raise ValueError("missing, repeated or irregular equity boundary")
    return tuple(
        IntervalLoss(times[i - 1], times[i], computed_ns, -(values[i] - values[i - 1]) / capital)
        for i in range(1, len(times))
    )
