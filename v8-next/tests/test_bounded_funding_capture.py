import io
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from v8_next.adapters.binance_capture import capture


@pytest.mark.parametrize("saturated", [False, True])
def test_explicit_funding_window_does_not_accept_saturated_response(
    tmp_path, monkeypatch, saturated
):
    urls = []

    def request(url, timeout):
        urls.append(url)
        if "exchangeInfo" in url:
            payload = {"symbols": [{"symbol": "BTCUSDT"}]}
        elif "fundingRate" in url:
            payload = [{"symbol": "BTCUSDT", "fundingTime": 10}] * (1000 if saturated else 1)
        else:
            payload = []
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr("v8_next.adapters.binance_capture.urlopen", request)
    monkeypatch.setattr("v8_next.adapters.binance_capture.time.time_ns", lambda: 20_000_000)
    target = tmp_path / "capture"
    if saturated:
        with pytest.raises(ValueError, match="truncated"):
            capture(target, funding_start_ms=5)
        assert not (target / "manifest.json").exists()
    else:
        manifest = capture(target, funding_start_ms=5)
        assert manifest.is_file()
    funding_url = next(url for url in urls if "fundingRate" in url)
    query = parse_qs(urlsplit(funding_url).query)
    assert query == {
        "symbol": ["BTCUSDT"],
        "startTime": ["5"],
        "endTime": ["20"],
        "limit": ["1000"],
    }
