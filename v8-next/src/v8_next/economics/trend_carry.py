"""Daily trend + funding-carry + cross-sectional momentum portfolio over UM perpetuals.

Three literature-grounded sleeves on a daily (UTC) panel of perpetual closes and
realised funding settlements:

* ``trend`` — time-series momentum (Moskowitz/Ooi/Pedersen 2012): per instrument the
  mean of ``sign(trailing return)`` over 20/60/120 days, long/short.
* ``carry`` — cross-sectional funding carry (Koijen et al. 2018 carry, applied to perp
  funding): rank instruments by trailing 7-day realised funding, short the richest,
  long the cheapest; rebalanced weekly.
* ``xs_momentum`` — cross-sectional momentum: rank by trailing 60-day return.

Each sleeve is inverse-volatility scaled; the portfolio is the equal mean of the three
sleeves after each sleeve is scaled to a common volatility measured on the declared
in-sample window only. Weights decided with data through the close of day ``t`` earn
day ``t + lag`` returns and pay that day's funding; turnover pays a declared per-unit
cost. Nothing here reads a wall clock or data after the decision bar.

The output is a simulated return series, not venue cash settlement, and carries no
economic-claim authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]

TREND_LOOKBACKS: tuple[int, ...] = (20, 60, 120)
CARRY_LOOKBACK = 7
CARRY_REBALANCE_DAYS = 7
XS_MOMENTUM_LOOKBACK = 60
MIN_HISTORY_DAYS = 60
MIN_CROSS_SECTION = 6
VOL_SPAN = 30
SLEEVE_TARGET_VOL = 0.20
PER_NAME_CAP = 0.5
DAYS_PER_YEAR = 365


@dataclass(frozen=True)
class Panel:
    """Aligned daily panel; rows are UTC days, columns instruments."""

    day_ns: NDArray[np.int64]
    instruments: tuple[str, ...]
    close: Array
    funding: Array  # summed realised funding rate settled during the day; 0 when none

    def __post_init__(self) -> None:
        t, n = self.close.shape
        if self.funding.shape != (t, n) or len(self.day_ns) != t or len(self.instruments) != n:
            raise ValueError("panel arrays are not aligned")
        if np.any(np.diff(self.day_ns) <= 0):
            raise ValueError("panel days must be strictly increasing")

    @property
    def returns(self) -> Array:
        r = np.full_like(self.close, np.nan)
        r[1:] = self.close[1:] / self.close[:-1] - 1
        return r

    @property
    def valid(self) -> NDArray[np.bool_]:
        has = np.isfinite(self.close)
        return has & (np.cumsum(has, axis=0) >= MIN_HISTORY_DAYS)


def trailing_return(close: Array, n: int) -> Array:
    out = np.full_like(close, np.nan)
    out[n:] = close[n:] / close[:-n] - 1
    return out


def trailing_mean(x: Array, n: int) -> Array:
    out = np.full_like(x, np.nan)
    cs = np.cumsum(x, axis=0)
    out[n:] = (cs[n:] - cs[:-n]) / n
    return out


def ewm_vol(returns: Array, span: int = VOL_SPAN) -> Array:
    """Annualised EWMA volatility using returns through day ``t`` only."""
    r = np.nan_to_num(returns)
    alpha = 2 / (span + 1)
    var = np.zeros_like(r)
    var[0] = r[0] ** 2
    for t in range(1, len(r)):
        var[t] = (1 - alpha) * var[t - 1] + alpha * r[t] ** 2
    return np.sqrt(var * DAYS_PER_YEAR)


def xs_rank(x: Array, valid: NDArray[np.bool_], min_names: int = MIN_CROSS_SECTION) -> Array:
    """Per-day cross-sectional rank mapped to [-1, 1]; NaN when too few names."""
    out = np.full_like(x, np.nan)
    for t in range(len(x)):
        m = valid[t] & np.isfinite(x[t])
        k = int(m.sum())
        if k >= min_names:
            out[t, m] = x[t, m].argsort().argsort() / (k - 1) * 2 - 1
    return out


def vol_scale(signal: Array, vol: Array, valid: NDArray[np.bool_]) -> Array:
    live = valid & np.isfinite(signal) & (vol > 0)
    n = live.sum(axis=1, keepdims=True).clip(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(live, signal * SLEEVE_TARGET_VOL / np.sqrt(n) / vol, 0.0)
    return np.clip(np.nan_to_num(w), -PER_NAME_CAP, PER_NAME_CAP)


def hold(weights: Array, every: int) -> Array:
    """Rebalance only every ``every`` days; hold the last decided weights between."""
    out = weights.copy()
    for t in range(1, len(out)):
        if t % every:
            out[t] = out[t - 1]
    return out


def trend_weights(panel: Panel) -> Array:
    votes = np.stack([np.sign(trailing_return(panel.close, lb)) for lb in TREND_LOOKBACKS])
    counted = np.isfinite(votes).sum(axis=0)
    sig = np.where(counted > 0, np.nansum(votes, axis=0) / counted.clip(1), np.nan)
    return vol_scale(sig, ewm_vol(panel.returns), panel.valid)


def carry_weights(panel: Panel) -> Array:
    sig = -xs_rank(trailing_mean(panel.funding, CARRY_LOOKBACK), panel.valid)
    return hold(vol_scale(sig, ewm_vol(panel.returns), panel.valid), CARRY_REBALANCE_DAYS)


def xs_momentum_weights(panel: Panel) -> Array:
    sig = xs_rank(trailing_return(panel.close, XS_MOMENTUM_LOOKBACK), panel.valid)
    return vol_scale(sig, ewm_vol(panel.returns), panel.valid)


SLEEVES = {
    "trend": trend_weights,
    "carry": carry_weights,
    "xs_momentum": xs_momentum_weights,
}


@dataclass(frozen=True)
class Simulation:
    net: Array
    gross: Array
    funding: Array
    cost: Array
    turnover: Array
    held: Array = field(repr=False)


def simulate(panel: Panel, weights: Array, *, cost_per_turnover: float, lag: int = 1) -> Simulation:
    """``weights[t]`` is decided at close ``t``; it is held over day ``t + lag``.

    Long positions pay positive funding. Turnover is the sum of absolute weight
    changes of the held book and pays ``cost_per_turnover`` (fee + slippage).
    """
    if lag < 1:
        raise ValueError("lag must be at least one day: no same-bar execution")
    w = np.nan_to_num(weights)
    held = np.zeros_like(w)
    held[lag:] = w[:-lag]
    r = np.nan_to_num(panel.returns)
    gross = (held * r).sum(axis=1)
    funding = -(held * panel.funding).sum(axis=1)
    turnover = np.abs(np.diff(np.vstack([np.zeros((1, w.shape[1])), held]), axis=0)).sum(axis=1)
    cost = cost_per_turnover * turnover
    return Simulation(gross + funding - cost, gross, funding, cost, turnover, held)


def portfolio_weights(
    panel: Panel,
    in_sample: NDArray[np.bool_],
    *,
    cost_per_turnover: float,
    sleeves: tuple[str, ...] = ("trend", "carry", "xs_momentum"),
) -> tuple[Array, dict[str, float]]:
    """Equal mean of sleeves, each scaled to ``SLEEVE_TARGET_VOL`` on ``in_sample`` only."""
    total = np.zeros_like(panel.close)
    scales: dict[str, float] = {}
    for name in sleeves:
        w = SLEEVES[name](panel)
        sd = float(simulate(panel, w, cost_per_turnover=cost_per_turnover).net[in_sample].std())
        if not sd > 0:
            raise ValueError(f"sleeve {name} has no in-sample variation")
        scales[name] = SLEEVE_TARGET_VOL / (sd * np.sqrt(DAYS_PER_YEAR))
        total += w * scales[name]
    return total / len(sleeves), scales


def summary(daily: Array) -> dict[str, float]:
    """Annualised arithmetic Sharpe, Lo (2002) iid standard error, drawdown, CAGR."""
    n = len(daily)
    mu, sd = float(daily.mean()), float(daily.std(ddof=1))
    sr_d = mu / sd if sd > 0 else float("nan")
    equity = np.cumprod(1 + daily)
    peak = np.maximum.accumulate(np.concatenate([[1.0], equity]))[1:]
    return {
        "days": n,
        "sharpe_annualised": sr_d * np.sqrt(DAYS_PER_YEAR),
        "sharpe_se_annualised": float(np.sqrt((1 + 0.5 * sr_d**2) / n) * np.sqrt(DAYS_PER_YEAR)),
        "mean_return_annualised": mu * DAYS_PER_YEAR,
        "volatility_annualised": sd * np.sqrt(DAYS_PER_YEAR),
        "cagr": float(equity[-1] ** (DAYS_PER_YEAR / n) - 1),
        "max_drawdown": float((equity / peak - 1).min()),
        "hit_rate_days": float((daily > 0).mean()),
    }
