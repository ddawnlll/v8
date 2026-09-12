"""Proving-ground contracts (MECHANICS ONLY where synthetic).

Worlds are synthetic by design (correctness evidence, AF-T12), so the bars
below are seed-pinned generator output — no assertion carries economic or
evaluative weight. All receipts carry NO_ECONOMIC_CLAIM. The real-tape
battery rule is untouched: nothing here scores edge, gates, or PnL.
"""

from __future__ import annotations

import pytest

from v8_next.evaluation.proving_battery import run_battery
from v8_next.system_proving.run import (
    FILL_PROFILE,
    SystemProvingGroundRunner,
    engine_smoke,
    fill_profile_digest,
)
from v8_next.world.foundry import build_world
from v8_next.world.spec import (
    SYNTHETIC_TAG_PREFIX,
    SyntheticPopulation,
    WorldFamily,
    WorldSpec,
)


def _spec(**overrides: object) -> WorldSpec:
    base: dict[str, object] = {
        "family": WorldFamily.STATIONARY_BOOTSTRAP,
        "population": SyntheticPopulation.SYNTHETIC_DEV,
        "symbol": "BTCUSDT",
        "n_bars": 60,
        "base_price": 50000.0,
        "volatility_annualized": 0.65,
        "jump_frequency": 12.0,
        "jump_mean": -0.015,
        "jump_std": 0.03,
        "seed": 453,
    }
    base.update(overrides)
    return WorldSpec(**base)  # type: ignore[arg-type]


def test_world_is_deterministic_per_seed() -> None:
    once, twice = build_world(_spec()), build_world(_spec())
    assert once.receipt_digest == twice.receipt_digest
    assert once.world_id == twice.world_id
    other = build_world(_spec(seed=454))
    assert other.receipt_digest != once.receipt_digest


def test_world_population_never_mixes_with_research() -> None:
    world = build_world(_spec())
    assert world.population_tag.startswith(SYNTHETIC_TAG_PREFIX)
    assert world.population_tag not in ("observed-research", "protected-holdout")
    assert world.as_dict()["claim"] == "NO_ECONOMIC_CLAIM"


def test_unported_family_is_refused_not_substituted() -> None:
    with pytest.raises(ValueError, match="FAMILY_NOT_PORTED"):
        build_world(_spec(family=WorldFamily.LEARNED_GENERATIVE_WORLD))


def test_empty_world_is_refused() -> None:
    with pytest.raises(ValueError, match="WORLD_SPEC_EMPTY"):
        _spec(n_bars=0)


def test_full_chain_exercises_af_t12_and_conserves() -> None:
    world = build_world(_spec(n_bars=120))
    receipt = SystemProvingGroundRunner.run_full_chain("p", world, 10000.0, 453)
    assert receipt.exercises_full_pipeline is True
    assert receipt.attribution.verify_conservation()
    assert receipt.metrics.is_double_entry_reconciled()
    assert receipt.as_dict()["world_id"] == world.world_id


def test_double_run_digest_equal() -> None:
    world = build_world(_spec(n_bars=120))
    first = SystemProvingGroundRunner.run_full_chain("p", world, 10000.0, 453)
    second = SystemProvingGroundRunner.run_full_chain("p", world, 10000.0, 453)
    assert first.receipt_digest == second.receipt_digest


def test_slippage_lane_is_seed_pinned_and_modelled() -> None:
    assert FILL_PROFILE["column"] == "MODELLED"
    assert FILL_PROFILE["model"] == "ProbabilisticFillModel"
    assert fill_profile_digest(453) == fill_profile_digest(453)
    assert fill_profile_digest(453) != fill_profile_digest(454)


def test_engine_smoke_runs_synthetic_without_venue_fetch() -> None:
    binding = engine_smoke("BTCUSDT")
    assert binding.engine == "BacktestEngine"
    assert binding.venue == "SYNTH"
    assert binding.fill_model == "ProbabilisticFillModel"


def test_battery_report_is_fail_closed_and_named() -> None:
    report = run_battery(n_bars=60)
    assert report["claim"] == "NO_ECONOMIC_CLAIM"
    assert report["double_run_digest_equal"] is True
    assert report["af_t12_exercised"] is True
    names = [f["finding"] for f in report["fault_findings"]]  # type: ignore[union-attr]
    assert "FAULT_DETECTED_CLOSE_MUTATION" in names
    assert "MISSING_MARK_BOOK" in names
