"""Executable observations only; not a declaration of full expert migration."""

from collections.abc import Callable

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, Stance, observe_squeeze
from v8_next.experts.breakouts import observe_failed_breakout, observe_volume_breakout
from v8_next.experts.donchian import observe_donchian
from v8_next.experts.reversion import observe_bollinger_reversion, observe_rsi_reversion
from v8_next.experts.trend import observe_trend_depth, observe_trend_pullback

Observer = Callable[[CausalFrame, Opportunity | None], Stance]
OBSERVERS: tuple[Observer, ...] = (
    observe_squeeze,
    observe_donchian,
    observe_bollinger_reversion,
    observe_rsi_reversion,
    observe_failed_breakout,
    observe_volume_breakout,
    observe_trend_pullback,
    observe_trend_depth,
)


def observe_all(frame: CausalFrame, opportunity: Opportunity | None) -> tuple[Stance, ...]:
    """Inspect existing opportunities; adding observers cannot create episodes."""
    return tuple(observer(frame, opportunity) for observer in OBSERVERS)
