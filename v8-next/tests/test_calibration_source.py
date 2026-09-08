import hashlib
import json

import pytest

from v8_next.evaluation import calibration


def test_forged_campaign_checkpoint_rejected_before_accounting(tmp_path, monkeypatch):
    monkeypatch.setattr(calibration, "source_hash", lambda: "fixture-runtime")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    (tmp_path / "policy.json").write_text(
        json.dumps({"policy": {"paper_config": {}, "code_and_lock_hash": "fixture-runtime"}})
    )
    (tmp_path / "paper-state.json").write_text(
        json.dumps(
            {
                "policy_hash": "test-policy",
                "manifests": ["manifest.json"],
                "manifest_hashes": [hashlib.sha256(manifest.read_bytes()).hexdigest()],
                "native_state": {"campaigns": [{"campaign_id": "forged"}]},
                "revised_accounting": {"accounting_as_of_ns": 10},
            }
        )
    )
    monkeypatch.setattr(calibration, "evaluate", lambda _: {"policy_hash": "test-policy"})
    monkeypatch.setattr(calibration, "replay_account", lambda *_: {"campaigns": []})

    def forbidden_accounting(*_):
        pytest.fail("forged decisions must not enter accounting replay")

    monkeypatch.setattr(calibration, "replay_frozen_campaigns", forbidden_accounting)
    with pytest.raises(ValueError, match="diverged"):
        calibration.inspect_calibration_source(tmp_path, 20)


@pytest.mark.parametrize("identity", [None, "different-runtime"])
def test_calibration_rejects_missing_or_changed_runtime_before_replay(
    tmp_path, monkeypatch, identity
):
    (tmp_path / "policy.json").write_text(json.dumps({"policy": {"code_and_lock_hash": identity}}))
    monkeypatch.setattr(calibration, "source_hash", lambda: "current-runtime")

    def forbidden(*args):
        pytest.fail("changed runtime must not recompute source evidence")

    monkeypatch.setattr(calibration, "evaluate", forbidden)
    monkeypatch.setattr(calibration, "replay_account", forbidden)
    with pytest.raises(ValueError, match="frozen runtime"):
        calibration.inspect_calibration_source(tmp_path, 20)


def test_open_outcomes_cannot_silently_disappear_from_calibration_sample():
    from v8_next.evaluation.calibration import outcome_sample_blockers

    blockers = outcome_sample_blockers([{"is_closed": True}, {"is_closed": False}], "UNQUALIFIED")
    assert "OPEN_OUTCOME_CENSORING_POLICY_REQUIRED" in blockers
    assert "FUNDING_COVERAGE_UNQUALIFIED" in blockers
    assert "STATISTICAL_METHOD_AND_TRIAL_FAMILY_REVIEW_REQUIRED" in blockers
    assert outcome_sample_blockers([], "COMPLETE")[0] == "NO_EXECUTED_OUTCOME_SAMPLE"
    assert outcome_sample_blockers([{"is_closed": True}], "COMPLETE") == [
        "STATISTICAL_METHOD_AND_TRIAL_FAMILY_REVIEW_REQUIRED"
    ]
