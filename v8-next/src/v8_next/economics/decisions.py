"""Small economic boundary: observations never carry order authority."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

import polars as pl

from v8_next.domain.market import CausalFrame


def numeric(value: object) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("expected finite numeric feature")
    return float(value)


class StanceKind(StrEnum):
    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    exposure_id: str
    instrument_id: str
    direction: str
    anchor_ns: int
    expires_ns: int
    grammar_version: str = "range-breakout-48-v1"
    identity_status: str = "CANONICAL"


@dataclass(frozen=True)
class Stance:
    observer_id: str
    dependency_group: str
    kind: StanceKind
    reason: str
    opportunity_id: str | None
    decision_ns: int
    behavior_family: str = "compression-breakout"
    mechanism_family: str = "volatility-expansion-hypothesis"
    version: str = "squeeze-observer-v1"
    variant_id: str = "baseline"


def opportunity_at(frame: CausalFrame) -> Opportunity | None:
    """Grammar is independent of observer identity and observation multiplicity.

    v1 treats each breakout candle as a discrete measurement episode. Its anchor
    is the closed market candle, never the clock on which an observer notices it.
    Only single-leg linear USD-M BTC exposure is initially supported.
    """
    if frame.instrument_id != "BTCUSDT-PERP.BINANCE":
        return None
    if not frame.continuous or len(frame.candles) < 49:
        return None
    history, current = frame.candles[-49:-1], frame.candles[-1]
    if current.close > max(c.high for c in history):
        direction = "LONG"
    elif current.close < min(c.low for c in history):
        direction = "SHORT"
    else:
        return None
    exposure = "BTC/USD:linear-perpetual"
    identity = json.dumps(
        ["range-breakout-48-v1", exposure, frame.instrument_id, direction, current.end_ns],
        separators=(",", ":"),
    )
    return Opportunity(
        hashlib.sha256(identity.encode()).hexdigest(),
        exposure,
        frame.instrument_id,
        direction,
        current.end_ns,
        current.end_ns + 336 * 3600 * 1_000_000_000,
    )


def observe_breakout_baseline(frame: CausalFrame, opportunity: Opportunity | None) -> Stance:
    """The frozen comparison omits only the compression filter, not admission."""
    return Stance(
        "range-breakout-baseline",
        "range-breakout-data",
        StanceKind.SUPPORT if opportunity else StanceKind.ABSTAIN,
        "GRAMMAR_BREAKOUT" if opportunity else "NO_OPPORTUNITY",
        opportunity.opportunity_id if opportunity else None,
        frame.decision_ns,
        mechanism_family="range-breakout-hypothesis",
        version="range-breakout-without-compression-v1",
    )


def observe_squeeze(
    frame: CausalFrame, opportunity: Opportunity | None, observer_id: str = "squeeze-swing"
) -> Stance:
    """Repo squeeze_swing economic hypothesis, with complete-window warmup.

    20-close population bandwidth, 50-bandwidth range, volume expansion,
    20-close efficiency. Full windows require 69 closes. Missing volume is not
    replaced with one; degenerate bandwidth/volume produces abstention.
    """
    kind = StanceKind.ABSTAIN
    reason = "NO_OPPORTUNITY"
    if not frame.continuous:
        reason = "SOURCE_GAP"
    elif len(frame.candles) < 69:
        reason = "WARMUP"
    elif opportunity is not None:
        values = pl.DataFrame(
            {
                "close": [float(c.close) for c in frame.candles],
                "volume": [float(c.volume) for c in frame.candles],
            }
        )
        features = values.with_columns(
            (4 * pl.col("close").rolling_std(20, ddof=0) / pl.col("close").rolling_mean(20)).alias(
                "bandwidth"
            ),
            pl.col("volume").rolling_mean(20).alias("volume_mean"),
        )
        bandwidths = features["bandwidth"].tail(50)
        lo, hi, latest = (numeric(v) for v in (bandwidths.min(), bandwidths.max(), bandwidths[-1]))
        volume_mean = numeric(features["volume_mean"][-1])
        close = values["close"].tail(20)
        path = numeric(close.diff().abs().sum())
        if hi <= lo or volume_mean <= 0 or path <= 0:
            reason = "DEGENERATE_FEATURE"
        elif (latest - lo) / (hi - lo) > 0.35:
            reason = "NO_COMPRESSION"
        elif numeric(values["volume"][-1]) / volume_mean < 1.30:
            reason = "NO_VOLUME_EXPANSION"
        elif abs(numeric(close[-1]) - numeric(close[0])) / path < 0.18:
            reason = "LOW_EFFICIENCY"
        else:
            kind, reason = StanceKind.SUPPORT, "COMPRESSION_BREAKOUT"
    return Stance(
        observer_id,
        "ohlcv-compression-v1",
        kind,
        reason,
        opportunity.opportunity_id if opportunity else None,
        frame.decision_ns,
    )


def reconcile(opportunity: Opportunity, stances: tuple[Stance, ...]) -> str:
    """No vote scores: correlated witnesses cannot manufacture confidence."""
    if any(s.opportunity_id != opportunity.opportunity_id for s in stances):
        raise ValueError("evidence belongs to another opportunity")
    groups: dict[str, set[StanceKind]] = {}
    for stance in stances:
        groups.setdefault(stance.dependency_group, set()).add(stance.kind)
    if any(StanceKind.CONTRADICT in kinds for kinds in groups.values()):
        return "CONTRADICTED"
    return (
        "SUPPORTED_OBSERVATION"
        if any(StanceKind.SUPPORT in kinds for kinds in groups.values())
        else "ABSTAIN"
    )


@dataclass(frozen=True)
class UtilityInputs:
    gross_edge: Decimal | None
    fees: Decimal | None
    spread: Decimal | None
    slippage: Decimal | None
    funding_cost: Decimal | None
    uncertainty: Decimal | None
    calibration_receipt: str | None

    def net(self) -> Decimal | None:
        items = (
            self.gross_edge,
            self.fees,
            self.spread,
            self.slippage,
            self.funding_cost,
            self.uncertainty,
        )
        if not self.calibration_receipt or any(v is None for v in items):
            return None
        values = tuple(v for v in items if v is not None)
        if any(not v.is_finite() for v in values):
            raise ValueError("non-finite utility input")
        if any(v < 0 for v in (values[1], values[2], values[3], values[5])):
            raise ValueError("negative friction or uncertainty")
        return values[0] - sum(values[1:], Decimal(0))


def utility_admission(inputs: UtilityInputs) -> str:
    value = inputs.net()
    if value is None:
        return "REJECTED_MISSING_CALIBRATION"
    return "UTILITY_ELIGIBLE" if value > 0 else "REJECTED_SUB_FRICTION"
