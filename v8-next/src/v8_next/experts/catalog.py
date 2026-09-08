"""Executable observations only; not a declaration of full expert migration."""

from collections.abc import Callable
from functools import partial

from v8_next.domain.market import CausalFrame
from v8_next.economics.decisions import Opportunity, Stance, observe_squeeze
from v8_next.experts.bollinger import observe_bollinger_breakout
from v8_next.experts.breakouts import observe_failed_breakout, observe_volume_breakout
from v8_next.experts.candlestick import VARIANTS, observe_candlestick
from v8_next.experts.donchian import observe_donchian
from v8_next.experts.gaps import observe_gap
from v8_next.experts.ichimoku import observe_ichimoku
from v8_next.experts.reclaim import observe_breakout_retest, observe_liquidity_reclaim
from v8_next.experts.reversion import observe_bollinger_reversion, observe_rsi_reversion
from v8_next.experts.trend import observe_trend_depth, observe_trend_pullback

Observer = Callable[[CausalFrame, Opportunity | None], Stance]
OBSERVERS: tuple[Observer, ...] = (
    observe_squeeze,
    observe_ichimoku,
    *(partial(observe_gap, variant=v) for v in ("a", "b", "c")),
    *(partial(observe_bollinger_breakout, variant=v) for v in ("a", "b", "c")),
    observe_candlestick,
    *(partial(observe_candlestick, variant=v) for v in VARIANTS),
    observe_donchian,
    observe_bollinger_reversion,
    observe_rsi_reversion,
    observe_failed_breakout,
    observe_volume_breakout,
    observe_trend_pullback,
    observe_trend_depth,
    observe_liquidity_reclaim,
    observe_breakout_retest,
    partial(observe_breakout_retest, variant="b"),
    partial(observe_breakout_retest, variant="c"),
)


def observe_all(frame: CausalFrame, opportunity: Opportunity | None) -> tuple[Stance, ...]:
    """Inspect existing opportunities; adding observers cannot create episodes."""
    return tuple(observer(frame, opportunity) for observer in OBSERVERS)
