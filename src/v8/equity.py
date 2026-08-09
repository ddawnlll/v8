"""Deterministic equity-curve risk state (OPEN_DECISIONS O-016; RM-06).

The drawdown-conditioned sizing challenger vs fixed-fractional risk: a pure
function of the realized episode sequence, never a learned component and never
fitted to the dev window. All thresholds are DECLARED numeric literals taken
from the book (RM-06, Ch29.2): at -30% drawdown size is halved and stop_r
doubled; at -50% both repeat (quarter / quadruple). Because every band pairs
size x stop_r with reciprocal multipliers (0.5*2 == 0.25*4 == 1), the product
size*stop_r — and therefore the D-023 heat invariant and the maximum % risk
per trade — is exactly preserved. The bands are frozen here like the O-017
thresholds: any change is a preregistered comparison on frozen OOS, never an
edit.

Equity is ADDITIVE fixed-fractional of the INITIAL account (RM-15: fixed
sizing of original capital has linear expectancy and no sequence asymmetry;
compounding is deliberately not implemented, D-025 fractional-Kelly cap only).
One R at full size moves equity by `risk_per_trade` of the initial account, so
the account is worth `100 / risk_per_trade` trade units (RM-07).

Placement in the decision path: RiskGate reads `size_multiplier` /
`stop_multiplier` for heat accounting and the lab feeds `on_episode_closed`
from realized net_r in episode order. Because size*stop_r is invariant, the
drawdown ladder never changes an admission decision — it is pure sizing, and
its evidence lives in the equity/report diagnostics, not in the R-ledger. The
risk-of-ruin Monte-Carlo is REPORT-ONLY (seed-explicit stdlib RNG; never part
of the decision path or any hash).
"""
from __future__ import annotations

import math
import random

# Frozen drawdown bands (RM-06): (drawdown <= band, size multiplier,
# stop_r multiplier). Deeper bands override shallower ones; the product of the
# multipliers is 1.0 at every band, preserving size*stop_r exactly. Declared
# from the book pre-holdout — never fitted, never tuned (O-017 method).
DRAWDOWN_BANDS: tuple[tuple[float, float, float], ...] = (
    (-0.30, 0.5, 2.0),
    (-0.50, 0.25, 4.0),
)

# Risk-of-ruin Monte-Carlo (RM-07): fixed, seed-explicit, report-only.
RISK_OF_RUIN_N_SIMS = 10_000
RISK_OF_RUIN_SEED = 7


def trade_units_for(risk_per_trade: float) -> float:
    """Trade-unit budget (RM-07): 100% / %risk per trade. With risk_per_trade
    a FRACTION, %risk = risk_per_trade * 100, so trade_units = 1/risk_per_trade:
    1% risk (0.01) -> 100 opportunities; 20% risk (0.20) -> 5. The account can
    absorb `trade_units` full-size -1R episodes before ruin."""
    if not 0.0 < risk_per_trade < 1.0:
        raise ValueError(f'risk_per_trade must be in (0, 1), got {risk_per_trade!r}')
    return 1.0 / risk_per_trade


class RiskState:
    """Running normalized equity from realized net_r, fed in episode order.

    Deterministic: a pure function of the ordered (net_r, size) series the lab
    feeds at position close. Initial equity is normalized to 1.0; every
    realized episode books `net_r * size * risk_per_trade` additively.
    """

    def __init__(self, risk_per_trade: float = 0.01,
                 bands: tuple[tuple[float, float, float], ...] = DRAWDOWN_BANDS,
                 initial_equity: float = 1.0):
        if not 0.0 < risk_per_trade < 1.0:
            raise ValueError(f'risk_per_trade must be in (0, 1), got {risk_per_trade!r}')
        if not initial_equity > 0:
            raise ValueError(f'initial_equity must be > 0, got {initial_equity!r}')
        if not bands:
            raise ValueError('drawdown bands must not be empty')
        self.risk_per_trade = float(risk_per_trade)
        self.bands = tuple(sorted(bands))        # deepest drawdown band first
        self.initial_equity = float(initial_equity)
        self._equity = self.initial_equity
        self._peak = self.initial_equity
        # One entry per realized episode: (net_r, size, equity_after, drawdown_after).
        self._events: list[tuple[float, float, float, float]] = []

    def trade_units(self) -> float:
        return trade_units_for(self.risk_per_trade)

    def drawdown(self) -> float:
        """Current peak-to-trough drawdown on the equity curve (<= 0)."""
        if self._peak <= 0:
            return -1.0
        return self._equity / self._peak - 1.0

    def size_multiplier(self) -> float:
        """f(dd): {1, 1/2, 1/4} at the -30%/-50% bands (RM-06)."""
        dd = self.drawdown()
        for band_dd, size_mult, _stop in self.bands:
            if dd <= band_dd:
                return size_mult
        return 1.0

    def stop_multiplier(self) -> float:
        """g(dd): {1, 2, 4} at the -30%/-50% bands (RM-06). f*g == 1 always."""
        dd = self.drawdown()
        for band_dd, _size, stop_mult in self.bands:
            if dd <= band_dd:
                return stop_mult
        return 1.0

    def on_episode_closed(self, net_r: float, size: float = 1.0) -> None:
        """Book one realized episode (position closed, net_r in R).

        Additive fixed-fractional of the INITIAL account (RM-15): no
        compounding, no sequence asymmetry, linear expectancy. `size` is the
        effective size the position was admitted at (RiskGate drawdown
        scaling already applied), so halving size halves the equity impact of
        every R.
        """
        if not math.isfinite(net_r):
            raise ValueError(f'net_r must be finite, got {net_r!r}')
        if not size > 0:
            raise ValueError(f'size must be > 0, got {size!r}')
        self._equity += net_r * size * self.risk_per_trade
        self._peak = max(self._peak, self._equity)
        self._events.append((net_r, size, self._equity, self.drawdown()))

    # --- report diagnostics (all deterministic from the event series) -------

    def final_equity(self) -> float:
        return self._equity

    def max_drawdown(self) -> float:
        """Deepest peak-to-trough on the equity curve (<= 0; 0.0 when empty)."""
        return min((e[3] for e in self._events), default=0.0)

    def risk_of_ruin(self, n_sims: int = RISK_OF_RUIN_N_SIMS,
                     seed: int = RISK_OF_RUIN_SEED) -> float | None:
        """P(ruin) by Monte-Carlo over the realized episode sequence (RM-07).

        REPORT-ONLY: seed-explicit stdlib RNG, never the decision path, never
        part of any hash. Each simulated life starts at the trade-unit budget
        (100/risk_per_trade), samples realized (net_r, size) episodes with
        replacement, and books the additive fixed-fractional balance; ruin is
        balance <= 0 at any point (the book's "an early loss streak can
        exhaust the unit budget even at a 50% win rate"). None when no episode
        was realized.
        """
        if not self._events:
            return None
        rng = random.Random(seed)
        series = [(e[0], e[1]) for e in self._events]
        n = len(series)
        budget = self.trade_units()
        ruined = 0
        for _ in range(n_sims):
            balance = budget
            # One C-level `choices` draw per sim instead of n Python-level
            # `choice` calls: same with-replacement distribution, same seed
            # determinism (report-only — no value is pinned), ~10x faster on
            # the profiled 10k x n episode path. The ruin check still walks
            # the drawn life and breaks at the first balance <= 0.
            for net_r, size in rng.choices(series, k=n):
                balance += net_r * size
                if balance <= 0.0:
                    ruined += 1
                    break
        return ruined / n_sims
