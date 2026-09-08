import hashlib

import pytest

from v8_next.app.trial import run_trial
from v8_next.domain.config import PaperConfig
from v8_next.evaluation.store import ResearchStore


def test_development_trial_cannot_consume_registered_holdout(tmp_path):
    manifest = tmp_path / "holdout.json"
    manifest.write_text("{}")
    store = ResearchStore(tmp_path / "research.sqlite")
    policy = PaperConfig(
        maker_fee="0",
        taker_fee="0",
        initial_balance="1000",
        max_notional="100",
        max_exposure_fraction=".1",
    )
    try:
        store.register_trial(
            "protected",
            "f",
            "policy",
            hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "HOLDOUT",
            1,
        )
        with pytest.raises(ValueError, match="protected holdout"):
            run_trial(manifest, policy, store, "f")
        assert store.family_size("f") == 1
    finally:
        store.close()


def test_callback_failure_is_retained_even_if_native_engine_logs_it():
    from v8_next.adapters.historical_trial import HistoricalTrial

    class Failing(HistoricalTrial):
        def process_bar(self, bar):
            raise ValueError("missing source")

    policy = PaperConfig(
        maker_fee="0",
        taker_fee="0",
        initial_balance="1000",
        max_notional="100",
        max_exposure_fraction=".1",
    )
    trial = Failing((), policy)
    with pytest.raises(ValueError, match="missing source"):
        trial.on_bar(None)
    assert trial.failure == "ValueError: missing source"
    trial.on_bar(None)
    assert not trial.decisions
