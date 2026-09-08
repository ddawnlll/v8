import pytest
from pydantic import ValidationError

from v8_next.app.paper import step


@pytest.mark.parametrize(
    "key,value",
    [
        ("maker_fee", "NaN"),
        ("taker_fee", "-1"),
        ("initial_balance", "0"),
        ("max_notional", "Infinity"),
        ("max_exposure_fraction", "1.01"),
        ("enable_live", "true"),
    ],
)
def test_invalid_api_config_cannot_create_run(tmp_path, key, value):
    config = {
        "maker_fee": "0",
        "taker_fee": "0",
        "initial_balance": "10000",
        "max_notional": "100",
        "max_exposure_fraction": "0.1",
        key: value,
    }
    run = tmp_path / "must-not-exist"
    with pytest.raises(ValidationError):
        step(run, config)
    assert not run.exists()
