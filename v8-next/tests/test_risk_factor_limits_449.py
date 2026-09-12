"""#449 — every declared risk limit is measured against the record, or named UNMEASURED.

The defect: ``risk_factor()`` published ``RESPECTED`` / factor 1.0 while every ``max_drawdown``
slot it read was ``null`` -- the numeric filter at the comparison site dropped the nulls, so
the declared ``max_drawdown: -0.25`` limit had no code path that could ever breach it, and
``max_fee_drag_vs_gross`` / ``max_exposure`` were consulted by no code at all. The same P2
artifact publishes ``max_adverse_excursion_pct`` 96.32 (``causal_trend``) and 100.83
(``plain_swing``) -- under ``families`` (plural) and in *percent* -- invisible to a reader
that looks for ``family`` (singular) and compares fractions. A record that reaches ruin was
published as limits-respected.

Evidence class: mechanics / arithmetic. The fixture artifacts written here are test-local and
labelled ``MECHANICS ONLY``: they carry zero evaluative weight and never enter
``docs/evidence``. The two assertions that read the real repository artifacts read them
read-only (they are the frozen P2 evidence) and skip when the artifacts are absent. No
assertion here mints an economic claim, no threshold is moved, and no return is asserted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from v8_next.app.readiness import BASELINE_REL, PILLAR_ARTIFACTS, RISK_LIMITS, risk_factor

#: MECHANICS ONLY: the label every fixture written by this file carries.
MECHANICS_ONLY = "MECHANICS ONLY: test-local arithmetic fixture, zero evaluative weight"

REAL_P2 = PILLAR_ARTIFACTS["P2_paper_trade_4y"]

STATUS_VOCABULARY = {"RESPECTED", "BREACH", "UNMEASURED"}


def _artifact(tmp_path: Path, name: str, payload: dict[str, Any]) -> tuple[Path, list[str]]:
    """Write one labelled MECHANICS ONLY fixture and return (repo_root, rel paths)."""
    rel = f"tests_local/{name}"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"claim_status": "NO_ECONOMIC_CLAIM", "evidence_class": MECHANICS_ONLY, **payload}
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    return tmp_path, [rel]


def _repo_root() -> Path:
    """The repository root, located from this file; skipped when the evidence is absent."""
    for parent in Path(__file__).resolve().parents:
        if (parent / REAL_P2[2]).is_file():
            return parent
    pytest.skip(f"the P2 paper-trade evidence is absent at {REAL_P2[2]}")


def _excursion_artifact(
    tmp_path: Path, name: str, excursion_pct: float, *, exposure: Any = None
) -> tuple[Path, list[str]]:
    """A one-policy paper-trade record publishing a percentage adverse excursion."""
    families: dict[str, Any] = {
        "causal_trend": {
            "fee_cost_return_sum": -0.02,
            "gross_return_sum": 0.5,
            "robustness_vector": {"max_adverse_excursion_pct": excursion_pct},
        }
    }
    payload: dict[str, Any] = {"families": families}
    if exposure is not None:
        payload["exposure"] = exposure
    return _artifact(tmp_path, name, payload)


def test_a_record_whose_drawdown_slots_are_all_null_is_never_respected(tmp_path: Path) -> None:
    """F1: null drawdown slots may not add up to a respected limit."""
    root, rels = _artifact(
        tmp_path,
        "null_drawdowns.json",
        {
            "family": {
                "causal_trend": {
                    "totals_by_slippage_fraction": {
                        "0.0": {
                            "max_drawdown": None,
                            "net_return_measured_only_sum": -0.029,
                            "fee_cost_return_sum": -0.027,
                            "gross_return_sum": 0.044,
                        }
                    }
                }
            }
        },
    )
    result = risk_factor(root, rels)

    assert result["status"] != "RESPECTED"
    assert result["factor"] == 0.0
    assert result["metrics"]["causal_trend.slippage_0.0.max_drawdown"] is None

    drawdown = result["limit_assessments"]["max_drawdown"]
    assert drawdown["status"] == "UNMEASURED"
    assert drawdown["observations"] == []
    assert drawdown["breaches"] == []
    assert any(line.startswith("max_drawdown:") for line in result["unmeasured"])
    assert any("max_adverse_excursion_pct" in line for line in result["unmeasured"])
    # F3: the absent source is named -- no number is invented for it
    assert result["breaches"] == []


def test_a_percentage_excursion_is_normalised_before_the_fraction_comparison(
    tmp_path: Path,
) -> None:
    """A2/F2: 96.32 % is compared as 0.9632 against -0.25 and breaches by name."""
    root, rels = _excursion_artifact(tmp_path, "excursion_9632.json", 96.32, exposure=0.4)
    result = risk_factor(root, rels)

    assert result["status"] == "BREACH"
    assert result["factor"] == 0.0

    drawdown = result["limit_assessments"]["max_drawdown"]
    assert drawdown["status"] == "BREACH"
    row = drawdown["observations"][0]
    assert row["published"] == 96.32
    assert row["unit"] == "percent"
    assert row["measured"] == pytest.approx(0.9632)
    assert "max_adverse_excursion_pct" in row["source"]

    breach = drawdown["breaches"][0]
    assert "max_drawdown 0.96320000 beyond -0.25" in breach
    assert "max_adverse_excursion_pct" in breach
    assert breach in result["breaches"]

    # the two other declared limits were measured on the same record and respected
    assert result["limit_assessments"]["max_fee_drag_vs_gross"]["status"] == "RESPECTED"
    assert result["limit_assessments"]["max_exposure"]["status"] == "RESPECTED"


def test_a_tenth_is_respected_only_after_the_unit_is_normalised(tmp_path: Path) -> None:
    """A2: 10.0 % is 0.10 as a fraction -- respected; compared raw it would breach."""
    root, rels = _excursion_artifact(tmp_path, "excursion_10.json", 10.0, exposure=0.4)
    result = risk_factor(root, rels)

    drawdown = result["limit_assessments"]["max_drawdown"]
    assert drawdown["status"] == "RESPECTED"
    assert drawdown["observations"][0]["measured"] == pytest.approx(0.10)
    assert result["status"] == "RESPECTED"
    assert result["factor"] == 1.0
    assert result["breaches"] == []
    assert result["unmeasured"] == []


def test_the_fee_drag_limit_is_compared_not_merely_read(tmp_path: Path) -> None:
    """A3: the fee-drag limit has a consumer -- a real ratio breaches it by name."""
    root, rels = _artifact(
        tmp_path,
        "fee_drag.json",
        {
            "families": {
                "plain_swing": {
                    "fee_cost_return_sum": -1.2,
                    "gross_return_sum": 0.5,
                    "robustness_vector": {"max_adverse_excursion_pct": 5.0},
                }
            },
            "exposure": 0.4,
        },
    )
    result = risk_factor(root, rels)

    fee_drag = result["limit_assessments"]["max_fee_drag_vs_gross"]
    assert fee_drag["status"] == "BREACH"
    assert fee_drag["observations"][0]["measured"] == pytest.approx(2.4)
    assert any("max_fee_drag_vs_gross" in line for line in result["breaches"])
    assert result["status"] == "BREACH"
    assert result["factor"] == 0.0


def test_every_declared_limit_is_evaluated_or_named_unmeasured(tmp_path: Path) -> None:
    """A3: no declared limit is silently unconsulted."""
    root, rels = _excursion_artifact(tmp_path, "limits.json", 5.0)
    result = risk_factor(root, rels)

    assert set(result["limit_assessments"]) == set(RISK_LIMITS)
    for name, row in result["limit_assessments"].items():
        assert row["status"] in STATUS_VOCABULARY
        assert row["limit"] == RISK_LIMITS[name]
        assert row["source"]
        if row["status"] == "UNMEASURED":
            assert any(line.startswith(f"{name}:") for line in result["unmeasured"])
            assert row["observations"] == []
        else:
            assert row["observations"], f"{name} has a verdict with no measurement behind it"

    # this record publishes no exposure at all: the limit is named, never assumed respected
    exposure = result["limit_assessments"]["max_exposure"]
    assert exposure["status"] == "UNMEASURED"
    assert any(line.startswith("max_exposure:") for line in result["unmeasured"])
    # ...and the factor is therefore 0.0 even though nothing breached
    assert result["breaches"] == []
    assert result["status"] == "UNMEASURED"
    assert result["factor"] == 0.0


def test_no_record_at_all_is_missing(tmp_path: Path) -> None:
    """The module contract is kept: no record is MISSING, not a silent zero on a limit."""
    result = risk_factor(tmp_path, ["docs/evidence/v87-r3/PAPER_4Y/paper_trade_4y.json"])

    assert result["status"] == "MISSING"
    assert result["factor"] == 0.0
    assert result["metrics"] == {}
    assert set(result["limit_assessments"]) == set(RISK_LIMITS)


def test_the_real_p2_record_is_never_reported_as_limits_respected() -> None:
    """A1: the frozen four-year record reaches ruin; the audit may not say RESPECTED."""
    result = risk_factor(_repo_root(), list(REAL_P2))

    assert result["status"] != "RESPECTED"
    assert result["factor"] == 0.0
    assert result["breaches"]

    drawdown = result["limit_assessments"]["max_drawdown"]
    assert drawdown["status"] == "BREACH"
    assert any("max_adverse_excursion_pct" in row["source"] for row in drawdown["observations"])
    assert max(row["measured"] for row in drawdown["observations"]) > abs(RISK_LIMITS["max_drawdown"])
    assert any("96.32" in str(row["published"]) for row in drawdown["observations"])
    assert any("100.82" in str(row["published"]) for row in drawdown["observations"])

    # the exposure limit has no source in this artifact set: named, not assumed
    assert result["limit_assessments"]["max_exposure"]["status"] == "UNMEASURED"
    assert any(line.startswith("max_exposure:") for line in result["unmeasured"])


def test_the_published_baseline_names_every_limit_and_its_verdict() -> None:
    """A4: the republished baseline carries the breach/unmeasured limit by name."""
    root = _repo_root()
    path = root / BASELINE_REL
    if not path.is_file():
        pytest.skip(f"no published baseline at {BASELINE_REL}")
    baseline = json.loads(path.read_text())

    assert baseline["claim_status"] == "NO_ECONOMIC_CLAIM"
    limits = baseline["risk_limits"]
    assert set(limits["assessments"]) == set(RISK_LIMITS)
    assert limits["status"] in STATUS_VOCABULARY
    for name, row in limits["assessments"].items():
        assert row["status"] in STATUS_VOCABULARY
        assert row["limit"] == RISK_LIMITS[name]
        assert row["source"]
    # the record breaches the drawdown limit and publishes no exposure: the baseline says so
    assert limits["status"] != "RESPECTED"
    assert baseline["risk_factor"] == 0.0
    assert any("max_drawdown" in line for line in limits["breaches"])
    assert any(line.startswith("max_exposure:") for line in limits["unmeasured"])
