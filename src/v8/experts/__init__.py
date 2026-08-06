"""Pilot expert registry (EXPERT_PROTOCOL sections 2-3).

One file per behavior family under this package; the registry re-exports the
admitted pilot set so consumers keep `from v8.experts import ...`.

D-042: families admitted in the handbook+evidence extraction round; each is
a self-gating hypothesis with frozen variants_evaluated (D-044) and an honest
search_universe_size (D-046). DATA_BLOCKED families (open_interest) have code
that self-gates to NO_HABITAT until a derivatives tape provides the feature.
"""
from __future__ import annotations

from .base import Expert
from .trend_pullback import TrendPullbackExpert
from .failed_breakout import FailedBreakoutExpert
from .liquidity_sweep_reclaim import LiquiditySweepReclaimExpert
from .failed_breakout_2b import FailedBreakout2BExpert
from .trend_pullback_depth import TrendPullbackDepthExpert
from .range_breakout_1to1 import RangeBreakout1To1Expert
from .candlestick_reversal import CandlestickReversalExpert
from .rsi_stoch_reversion import RsiStochReversionExpert
from .macd_stoch_trend import MacdStochTrendExpert
from .divergence_12_setups import Divergence12SetupsExpert
from .bollinger_breakout import BollingerBreakoutExpert
from .bollinger_reversion import BollingerReversionExpert
from .donchian_breakout import DonchianBreakoutExpert
from .breakout_retest import BreakoutRetestExpert
from .fib_retracement_continuation import FibRetracementContinuationExpert
from .fib_projection_reversal import FibProjectionReversalExpert
from .pattern_measuring_objective import PatternMeasuringObjectiveExpert
from .volume_confirmed_breakout import VolumeConfirmedBreakoutExpert
from .volume_climax_reversal import VolumeClimaxReversalExpert
from .obv_adl_regime import ObvAdlRegimeExpert
from .ichimoku_cloud import IchimokuCloudExpert
from .floor_trader_pivot import FloorTraderPivotExpert
from .market_profile_value_area import MarketProfileValueAreaExpert
from .gap_exhaustion import GapExhaustionExpert
from .open_interest_divergence import OpenInterestDivergenceExpert
from .funding_crowding_reversal import FundingCrowdingReversalExpert
from .pandf_breakout import PandfBreakoutExpert

__all__ = [
    'Expert',
    'TrendPullbackExpert', 'FailedBreakoutExpert', 'LiquiditySweepReclaimExpert',
    'FailedBreakout2BExpert', 'TrendPullbackDepthExpert', 'RangeBreakout1To1Expert',
    'CandlestickReversalExpert', 'RsiStochReversionExpert', 'MacdStochTrendExpert',
    'Divergence12SetupsExpert', 'BollingerBreakoutExpert', 'BollingerReversionExpert',
    'DonchianBreakoutExpert', 'BreakoutRetestExpert',
    'FibRetracementContinuationExpert', 'FibProjectionReversalExpert',
    'PatternMeasuringObjectiveExpert', 'VolumeConfirmedBreakoutExpert',
    'VolumeClimaxReversalExpert', 'ObvAdlRegimeExpert', 'IchimokuCloudExpert',
    'FloorTraderPivotExpert', 'MarketProfileValueAreaExpert', 'GapExhaustionExpert',
    'OpenInterestDivergenceExpert', 'FundingCrowdingReversalExpert',
    'PandfBreakoutExpert',
]
