from decimal import Decimal as D

from v8_next.domain.market import Candle, CausalFrame
from v8_next.domain.positioning import PositioningReading
from v8_next.economics.regime import observe_regime


def frame(volumes: list[int]) -> CausalFrame:
    return CausalFrame(
        "BTC",
        100,
        tuple(
            Candle("BTC", i, i + 1, D(1), D(1), D(1), D(1), D(v), i + 1, i + 1, "source")
            for i, v in enumerate(volumes)
        ),
    )


def test_volume_window_and_missingness():
    assert observe_regime(frame([10] * 19)).volume is None
    assert observe_regime(frame([0] * 20)).volume is None
    assert observe_regime(frame([10] * 20)).volume == "NormalVolume"
    assert observe_regime(frame([10] * 19 + [20])).volume == "VolumeExpansion"
    assert observe_regime(frame([10] * 19 + [1])).volume == "VolumeDrought"
    # Older volume cannot influence the declared 20-bar window.
    assert observe_regime(frame([999] + [10] * 20)).volume_ratio == "1"
    original = frame([10] * 21)
    gap = CausalFrame("BTC", 100, original.candles[:10] + original.candles[11:])
    assert observe_regime(gap).volume is None


def test_funding_knowledge_expiry_and_thresholds():
    for rate, expected in [
        ("0.00015", "CrowdedLong"),
        ("-0.00015", "CrowdedShort"),
        ("0", "NeutralFunding"),
    ]:
        reading = PositioningReading(
            "BTC", "settled_funding_rate", D(rate), 90, 95, 100, 110, "hash"
        )
        result = observe_regime(frame([]), readings=(reading,))
        assert result.funding == expected
        assert result.trend is None and result.volatility is None
        assert result.habitat_status == "UNQUALIFIED"
        assert observe_regime(CausalFrame("BTC", 99, ()), readings=(reading,)).funding is None
        assert observe_regime(CausalFrame("BTC", 110, ()), readings=(reading,)).funding is None
    assert observe_regime(frame([])).funding is None
