import hashlib
import json

import pytest

from v8_next.app.evaluate import evaluate
from v8_next.evaluation.store import ResearchStore, canonical


def test_evaluator_reports_registry_without_claiming_adjustment(tmp_path):
    policy = {"test_only": True}
    digest = hashlib.sha256(canonical(policy).encode()).hexdigest()
    (tmp_path / "policy.json").write_text(json.dumps({"policy": policy, "policy_hash": digest}))
    store = ResearchStore(tmp_path / "research.sqlite")
    try:
        store.register_trial("baseline", "family", digest, "test-data", "DEVELOPMENT", 1)
        store.register_trial("observer", "family", digest, "test-data", "DEVELOPMENT", 1)
        store.burn_holdout("family", "held-out", 2)
        report = evaluate(tmp_path)
        assert report["research_lineage"]["registered_family_sizes"] == {"family": 2}
        assert report["research_lineage"]["holdout_burns"] == [
            {"lineage": "family", "dataset_hash": "held-out", "burned_ns": 2}
        ]
        assert report["research_lineage"]["multiplicity_adjustment"] is None
        assert report["claim_status"] == "NO_ECONOMIC_CLAIM"
        store.register_trial("foreign", "family", "other-policy", "test-data", "DEVELOPMENT", 3)
        with pytest.raises(ValueError, match="trial belongs"):
            evaluate(tmp_path)
    finally:
        store.close()
