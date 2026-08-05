import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "research/pipeline_v2/tools/p4_integrity_audit.py"
    spec = importlib.util.spec_from_file_location("p4_integrity_audit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _artifacts():
    full = {
        "ledger": {"book_0001": {"round": 8, "claims_processed": 2, "corroborations": 1}},
        "rounds_ledger": [{"round": 8, "books": ["book_0001"], "claims_gated": 2}],
        "rounds_executed": [8],
        "corroborations": [{"claim_ref": "book_0001::a"}],
        "generic_count": 1,
        "dropped": [],
        "counts": {"corroborations": 1, "generic": 1, "dropped_unreferencable": 0},
    }
    checkpoint = {
        "processed_books": ["book_0001"],
        "books_processed_total": 1,
        "corroborations_total": 1,
        "generic_total": 1,
        "dropped_unreferencable": 0,
        "note": "1 corr + 1 generic + 0 dropped = 2 claims",
    }
    return full, checkpoint


def test_consistent_artifacts_pass():
    full, checkpoint = _artifacts()
    result = _module().audit(full, checkpoint)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_stale_checkpoint_fails_even_when_counts_are_nonzero():
    full, checkpoint = _artifacts()
    checkpoint["books_processed_total"] = 10
    checkpoint["processed_books"] = [f"book_{i:04d}" for i in range(1, 11)]
    result = _module().audit(full, checkpoint)
    assert result["status"] == "FAIL"
    assert any("processed_books" in error for error in result["errors"])


def test_duplicate_claim_refs_are_observed_without_dropping_records():
    full, checkpoint = _artifacts()
    full["ledger"]["book_0001"]["claims_processed"] = 3
    full["ledger"]["book_0001"]["corroborations"] = 2
    full["corroborations"].append({"claim_ref": "book_0001::a"})
    full["counts"]["corroborations"] = 2
    checkpoint["corroborations_total"] = 2
    checkpoint["note"] = "2 corr + 1 generic + 0 dropped = 3 claims"
    result = _module().audit(full, checkpoint)
    assert result["status"] == "PASS"
    assert result["observed"]["duplicate_claim_refs"] == ["book_0001::a"]
