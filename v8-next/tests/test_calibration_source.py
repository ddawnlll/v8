import hashlib
import json

import pytest

from v8_next.evaluation import calibration


def test_forged_campaign_checkpoint_rejected_before_accounting(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    (tmp_path / "policy.json").write_text(json.dumps({"policy": {"paper_config": {}}}))
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
