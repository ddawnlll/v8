"""#494 — the DSR subject is declared by the pinned plan, never chosen at run time.

Two ways of naming a subject without declaring one were rejected:

* the alphabetically first variant — arbitrary, and a rename silently moves the
  authority condition onto a different strategy;
* the best-realized-excess variant — selected on the evaluated outcome, which is
  exactly the selection the deflated Sharpe exists to correct for.

So the plan may declare ``dsr_subject`` and the estimator must use it; a plan
that declares none leaves the estimator BLOCKED (``MISSING_DSR_SUBJECT``), which
mints no confidence, no edge verdict, and no power vocabulary. Nothing in this
file asserts which variant *should* be the subject: that is an owner decision,
recorded in the plan, not in this code.
"""

from __future__ import annotations

import pytest

from v8_next.evaluation import economic_benchmark as eb
from v8_next.evaluation.statistics_plan import StatisticsPlan, g5_plan


class _Available:
    def for_estimator(self, _name: str) -> None:
        return None


@pytest.fixture
def estimator(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Record every DSR call so a blocked path can be shown not to have made one."""

    captured: dict[str, object] = {}

    def fake_dsr(losses, *, plan, **kwargs):
        captured["selected"] = plan.selected_variant
        captured["registered"] = plan.registered_variants
        return {
            "verdict": "COMPUTED",
            "selected_variant": plan.selected_variant,
            "dsr_confidence": 0.5,
            "selected_sharpe_nonannualized": 0.1,
        }

    monkeypatch.setattr(eb, "estimator_availability", lambda: _Available())
    monkeypatch.setattr(
        "v8_next.evaluation.deflated_sharpe.deflated_sharpe_diagnostic", fake_dsr
    )
    monkeypatch.setattr(
        "v8_next.evaluation.overfitting.pbo_diagnostic",
        lambda *args, **kwargs: {"verdict": "COMPUTED"},
    )
    monkeypatch.setattr(
        "v8_next.evaluation.inference.spa_diagnostic",
        lambda *args, **kwargs: {"verdict": "COMPUTED", "pvalues": {}},
    )
    return captured


def _curves() -> dict[str, list[float]]:
    return {
        "baseline": [10000.0 + (i % 5) for i in range(100)],
        # a_weak sorts first and ends with the lowest excess.
        "a_weak": [10000.0 + (i % 7) for i in range(100)],
        "b_mid": [10000.0 + 0.5 * i + (i % 3) for i in range(100)],
        "z_best": [10000.0 + 2.0 * i + (i % 4) for i in range(100)],
    }


def _end_ns() -> list[int]:
    return [i * 1_000_000 for i in range(100)]


def _plan(**kwargs) -> StatisticsPlan:
    base = dict(
        family="selection-test",
        pinned_ns=1,
        block_size=5,
        reps=10,
        seed=1,
        effective_independent_trials=4.0,
    )
    base.update(kwargs)
    return g5_plan(**base)


def test_no_declared_subject_blocks_the_estimator(estimator) -> None:
    """Absent a pinned subject the DSR does not run, so it cannot grant authority."""
    stats = eb.run_statistics(_curves(), _end_ns(), "baseline", plan=_plan())

    dsr = stats["dsr"]
    assert dsr["verdict"] == "BLOCKED"
    assert dsr["reason"] == "MISSING_DSR_SUBJECT"
    assert dsr["required_field"] == "statistics_plan.dsr_subject"
    assert "dsr_confidence" not in dsr
    assert "selected_sharpe_nonannualized" not in dsr
    assert dsr["detail"]
    assert dsr["registered_variants"] == ["a_weak", "b_mid", "z_best"]
    assert stats["dsr_subject_source"] == "UNPINNED"
    assert "selected" not in estimator, "the estimator was called without a declared subject"


def test_declared_subject_is_used_even_when_another_variant_has_higher_excess(
    estimator,
) -> None:
    """The outcome may not move the subject: a declared weak variant stays the subject."""
    plan = _plan(dsr_subject="a_weak")
    stats = eb.run_statistics(_curves(), _end_ns(), "baseline", plan=plan)

    assert estimator["selected"] == "a_weak"
    assert stats["dsr"]["selected_variant"] == "a_weak"
    assert stats["dsr"]["verdict"] == "COMPUTED"
    assert stats["dsr"]["selected_variant_source"] == "PINNED_PLAN"
    assert stats["dsr_subject_source"] == "PINNED_PLAN"
    # the best realized excess is still published -- as a descriptive statistic,
    # not as the subject of the authority condition
    z_best_excess = (10000.0 + 2.0 * 99 + (99 % 4)) / 10000.0 - 1.0 - (
        (10000.0 + (99 % 5)) / 10000.0 - 1.0
    )
    assert stats["variant_excess_vs_baseline"] == pytest.approx(z_best_excess)


def test_declared_subject_outside_the_family_is_blocked_by_name(estimator) -> None:
    unknown = eb.run_statistics(
        _curves(), _end_ns(), "baseline", plan=_plan(dsr_subject="not_registered")
    )
    assert unknown["dsr"]["verdict"] == "BLOCKED"
    assert unknown["dsr"]["reason"] == "DSR_SUBJECT_NOT_IN_FAMILY"
    assert unknown["dsr"]["registered_variants"] == ["a_weak", "b_mid", "z_best"]

    baseline = eb.run_statistics(
        _curves(), _end_ns(), "baseline", plan=_plan(dsr_subject="baseline")
    )
    assert baseline["dsr"]["verdict"] == "BLOCKED"
    assert baseline["dsr"]["reason"] == "DSR_SUBJECT_IS_BASELINE"

    assert "selected" not in estimator


def test_plan_identity_covers_the_subject_and_leaves_old_pins_alone() -> None:
    undeclared = _plan()
    declared = _plan(dsr_subject="z_best")
    other = _plan(dsr_subject="b_mid")

    assert undeclared.identity() != declared.identity()
    assert declared.identity() != other.identity()
    assert declared.identity() == _plan(dsr_subject="z_best").identity()

    # a plan that declares no subject keeps the identity it had before the field
    # existed, so no stored pin has to be rewritten
    assert "dsr_subject" not in undeclared.as_dict()
    assert declared.as_dict()["dsr_subject"] == "z_best"
    assert undeclared.as_dict()["identity"] == undeclared.identity()


def test_a_pinned_plan_round_trip_keeps_the_subject() -> None:
    """A stored plan reloads with its subject, and a pre-field plan reloads unpinned."""
    declared = _plan(dsr_subject="b_mid")
    stored = {k: v for k, v in declared.as_dict().items() if k != "identity"}
    stored["authority_conditions"] = tuple(stored["authority_conditions"])
    stored["diagnostics"] = tuple(stored["diagnostics"])
    reloaded = StatisticsPlan(**stored)
    assert reloaded.dsr_subject == "b_mid"
    assert reloaded.identity() == declared.identity()
    assert reloaded.pinned(7).dsr_subject == "b_mid"

    # a payload written before the field existed still loads, with no subject
    legacy = {k: v for k, v in _plan().as_dict().items() if k != "identity"}
    legacy["authority_conditions"] = tuple(legacy["authority_conditions"])
    legacy["diagnostics"] = tuple(legacy["diagnostics"])
    assert StatisticsPlan(**legacy).dsr_subject is None


def test_a_declared_subject_cannot_be_blank() -> None:
    with pytest.raises(ValueError, match="blank"):
        _plan(dsr_subject="   ")


def test_statistic_states_declare_blocked() -> None:
    assert "BLOCKED" in eb.STATISTIC_STATES


# --------------------------------------------------------------------------- #
# The published verdict may not read past a blocked authority condition.
# --------------------------------------------------------------------------- #


def _verdicts(stats: dict[str, object]) -> eb.EvidenceVerdicts:
    return eb.build_verdicts(
        chrono_ok=True,
        chrono_note="OK",
        leak_probe=None,
        excess=0.02,
        excess_ci=(-0.05, 0.07),
        stats=stats,
        mix={"incremental_net": 0.0},
        cost_basis_ok=True,
        funding_missing=False,
        live_fills_present=False,
        parity_ok=True,
    )


def test_blocked_dsr_cannot_be_laundered_into_an_edge_verdict() -> None:
    stats = {
        "dsr": {
            "verdict": "BLOCKED",
            "reason": "MISSING_DSR_SUBJECT",
            "registered_variants": ["a_weak", "b_mid", "z_best"],
        },
        "pbo": {"verdict": "COMPUTED"},
        # a diagnostic that on its own would have fired the SPA edge rule
        "spa": {"verdict": "COMPUTED", "pvalues": {"consistent": 0.001}},
        "variant_excess_vs_baseline": 0.02,
    }
    v = _verdicts(stats)

    assert v.statistical == "INCONCLUSIVE"
    assert "MISSING_DSR_SUBJECT" in v.statistical_note
    assert "SUPPORTS_EDGE" not in v.statistical
    assert "UNDERPOWERED" not in v.statistical_note
    assert "UNSUPPORTED" not in v.statistical_note


def test_blocked_authority_is_not_reported_as_underpowered() -> None:
    stats = {
        "dsr": {"verdict": "BLOCKED", "reason": "MISSING_DSR_SUBJECT"},
        "pbo": {"verdict": "UNDERPOWERED", "reason": "too few intervals"},
        "spa": {"verdict": "UNSUPPORTED", "reason": "degenerate variance"},
    }
    v = _verdicts(stats)

    assert v.statistical == "INCONCLUSIVE"
    assert "MISSING_DSR_SUBJECT" in v.statistical_note
    assert "UNDERPOWERED" not in v.statistical
