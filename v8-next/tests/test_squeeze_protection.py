from decimal import Decimal as D

from v8_next.domain.market import Candle, CausalFrame
from v8_next.economics.decisions import Opportunity
from v8_next.economics.protection import protection_at


def test_squeeze_uses_source_range_geometry_and_macro_expiry():
    bars = []
    for i in range(69):
        close = D(100 + (10 if i % 2 else -10)) if i < 20 else D(100) + D(i) / 100
        bars.append(
            Candle(
                "BTC",
                i,
                i + 1,
                close,
                close + D(".001"),
                close - D(".001"),
                close,
                D(3 if i == 68 else 1),
                i + 1,
                i + 1,
                "test-only",
            )
        )
    frame = CausalFrame("BTC", 69, tuple(bars))
    opportunity = Opportunity("s", "btc", "BTC", "LONG", 69, 1000)
    result = protection_at(frame, opportunity, "squeeze:baseline:v2", D(".001"))
    assert result is not None
    assert result.stop_price == bars[-1].close - D(".004")
    assert result.target_price == bars[-1].close + D(".008")
    assert result.expires_ns == 69 + 336
