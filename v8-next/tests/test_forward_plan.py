import pytest

from v8_next.domain.config import PaperConfig
from v8_next.evaluation.forward_plan import ForwardPlan, freeze_forward_plan
from v8_next.evaluation.store import ResearchStore

HOUR = 3600 * 10**9


def plan():
    policy = PaperConfig(
        maker_fee=".001",
        taker_fee=".001",
        initial_balance="1000",
        max_notional="100",
        max_exposure_fraction=".1",
    )
    return ForwardPlan(
        instrument_id="BTCUSDT-PERP.BINANCE",
        start_ns=10 * HOUR,
        end_ns=20 * HOUR,
        policies={
            "a": policy,
            "b": policy.model_copy(update={"observer_policy": "breakout_baseline"}),
        },
        baseline="a",
        block_size=2,
        reps=99,
        seed=1,
    )


def test_freeze_uses_current_clock_and_is_immutable_after_restart(tmp_path, monkeypatch):
    path = tmp_path / "store.sqlite"
    monkeypatch.setattr("v8_next.evaluation.forward_plan.time.time_ns", lambda: HOUR)
    store = ResearchStore(path)
    digest = freeze_forward_plan(store, "planned", plan(), "code")
    store.close()
    store = ResearchStore(path)
    try:
        monkeypatch.setattr("v8_next.evaluation.forward_plan.time.time_ns", lambda: 11 * HOUR)
        assert freeze_forward_plan(store, "planned", plan(), "code") == digest
        assert store.db.execute("SELECT registered_ns FROM forward_plans").fetchone()[0] == HOUR
        with pytest.raises(ValueError, match="before"):
            freeze_forward_plan(store, "backdated", plan(), "code")
        with pytest.raises(ValueError, match="rewritten"):
            freeze_forward_plan(store, "planned", plan(), "changed-code")
    finally:
        store.close()


def test_invalid_family_and_time_plan_reject():
    payload = plan().model_dump()
    payload["baseline"] = "missing"
    with pytest.raises(ValueError):
        ForwardPlan.model_validate(payload)
    payload = plan().model_dump()
    payload["end_ns"] = payload["start_ns"]
    with pytest.raises(ValueError):
        ForwardPlan.model_validate(payload)
