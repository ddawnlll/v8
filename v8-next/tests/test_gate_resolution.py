"""Comprehensive Tests for G3-G9 Gate Resolution Battery (Rule 12, Rule 30, Rule 57).

Validates:
1. G3: Scenario Robustness across 4 market regimes (Bull Trend, Bear Crash, Chop/Range, High-Vol Spill).
2. G4: Synthetic / Adversarial Falsification with execution shocks & bracket stop-loss.
3. G5: Selection Control via Deflated Sharpe Ratio (DSR) & White's Reality Check (WRC).
4. G6: Frozen Out-of-Sample (OOS) Replication with performance retention >= 60%.
5. G7: Prospective Shadow Succession with causal e-process martingale & drift tracking.
6. G8: Live Realization (D-152 §5 Diagnostic Fold NOT_APPLICABLE in research, PASS with signed fills).
7. G9: Central ClaimRegistry verification of ledger hash chain & StatutoryClaimRecord issuance.
8. End-to-end BenchmarkRunner execution with resolve_gates=True.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from v8_next.adapters.expert_strategy import ExpertStrategyConfig
from v8_next.domain.market import Candle
from v8_next.evaluation.benchmark_receipt import (
    BenchmarkLedger,
    BenchmarkReceipt,
    GateState,
    GateVector,
    ReadinessStatus,
)
from v8_next.evaluation.claims import StatutoryClaimClass
from v8_next.evaluation.gate_resolution import (
    DEFAULT_TAPE_PATH,
    classify_market_regimes,
    evaluate_g3_scenario_robustness,
    evaluate_g4_synthetic_falsification,
    evaluate_g5_selection_control,
    evaluate_g6_frozen_oos,
    evaluate_g7_prospective_shadow,
    evaluate_g8_live_realization,
    evaluate_g9_certificate_authority,
    load_tape_candles,
)
from v8_next.evaluation.runner import BenchmarkCase, BenchmarkRunner


@pytest.fixture
def real_candles() -> list[Candle]:
    """Load a slice of real tape candles for fast unit test execution."""
    if not DEFAULT_TAPE_PATH.exists():
        pytest.skip(f"Real tape not found at {DEFAULT_TAPE_PATH}")
    return load_tape_candles(DEFAULT_TAPE_PATH, limit=120)


def test_load_tape_candles_real_data():
    """Verify loading real Binance 1h klines with Polars."""
    if not DEFAULT_TAPE_PATH.exists():
        pytest.skip("Real tape not found")
    candles = load_tape_candles(DEFAULT_TAPE_PATH, limit=50)
    assert len(candles) == 50
    assert candles[0].instrument_id == "BTCUSDT-PERP.BINANCE"
    assert candles[0].open > 0
    assert candles[0].close > 0
    assert candles[0].end_ns > candles[0].start_ns


def test_classify_market_regimes_4_partitions(real_candles: list[Candle]):
    """Verify market regime classification into Bull, Bear, Chop, High-Vol."""
    regimes = classify_market_regimes(candles=real_candles, slice_length=20)
    expected_regimes = {"Bull Trend", "Bear Crash", "Chop/Range", "High-Vol Spill"}
    assert set(regimes.keys()) == expected_regimes
    for name, c_list in regimes.items():
        assert len(c_list) > 0, f"Regime {name} has no candles"


def test_g3_scenario_robustness(real_candles: list[Candle]):
    """G3: honest sample floors — empty regimes fail closed with named reason."""
    regimes = classify_market_regimes(candles=real_candles, slice_length=25)
    cfg = ExpertStrategyConfig(min_support_quorum=1, max_contradiction_tolerance=28)
    state, metrics = evaluate_g3_scenario_robustness(regimes, cfg)
    assert metrics["max_drawdown_limit"] == 0.10
    assert metrics["min_trades_per_regime"] == 1
    assert len(metrics["regimes"]) == 4
    if metrics["empty_regimes"]:
        assert state == GateState.BLOCKED
        assert "INSUFFICIENT_REGIME_TRADES" in metrics["reason"]
        for name in metrics["empty_regimes"]:
            assert metrics["regimes"][name]["trades"] == 0
    else:
        assert metrics["min_regime_trades"] >= 1
        assert state == GateState.PASS
        assert metrics["passed"] is True
        assert metrics["max_observed_drawdown"] <= 0.10
        assert metrics["max_observed_variance"] <= 0.20


def test_g4_synthetic_falsification_adversarial_shock(real_candles: list[Candle]):
    """G4: survival without shocked executions fails closed (vacuous PASS banned)."""
    cfg = ExpertStrategyConfig(
        min_support_quorum=1,
        max_contradiction_tolerance=28,
        bracket_stop_pct=Decimal("0.02"),
    )
    state, metrics = evaluate_g4_synthetic_falsification(real_candles, cfg)
    assert metrics["min_closed_trades"] == 2
    if metrics["closed_trades"] < 2:
        assert state == GateState.BLOCKED
        assert "INSUFFICIENT_SHOCK_SAMPLE" in metrics["reason"]
    else:
        assert metrics["account_survived"] is True
        assert metrics["final_equity"] >= 7000.0
        assert state == GateState.PASS


def test_g5_selection_control_dsr_and_wrc():
    """G5: Verify DSR >= 0.95 and p <= 0.05 under Rule 12 multiple testing."""
    pnls = [0.03, 0.025, 0.04, 0.01, 0.035, 0.02, 0.05, 0.015, 0.03, 0.045] * 3
    state, metrics = evaluate_g5_selection_control(pnls, num_trials=4)
    assert state == GateState.PASS
    assert metrics["passed"] is True
    assert metrics["dsr_confidence"] >= 0.95
    assert metrics["adjusted_bonferroni_pvalue"] <= 0.05
    assert metrics["own_sample_count"] == 30
    assert metrics["sample_source"] == "own_track"


def test_g6_frozen_oos_replication(real_candles: list[Candle]):
    """G6: profit retention, not balance ratio — unprofitable legs fail closed."""
    cfg = ExpertStrategyConfig(min_support_quorum=1, max_contradiction_tolerance=28)
    state, metrics = evaluate_g6_frozen_oos(real_candles, cfg, min_retention_ratio=0.60)
    assert "is_profit" in metrics and "oos_profit" in metrics
    if state == GateState.BLOCKED:
        assert metrics["reason"] is not None
        assert any(
            code in metrics["reason"]
            for code in ("NO_IS_EDGE_TO_RETAIN", "PROFIT_RETENTION_BREACH", "OOS_BLOWUP")
        )
    else:
        assert metrics["passed"] is True
        assert metrics["is_profit"] > 0
        assert metrics["retention_ratio"] >= 0.60
        assert metrics["oos_final_balance"] >= 8000.0


def test_g7_prospective_shadow_streaming(tmp_path: Path, real_candles: list[Candle]):
    """G7: Verify causal e-process martingale and drift logging to disk."""
    out_dir = tmp_path / "shadow"
    state, metrics = evaluate_g7_prospective_shadow(real_candles, output_dir=out_dir)
    assert state == GateState.PASS
    assert metrics["passed"] is True
    assert 0.01 <= metrics["final_e_process"] < 20.0
    assert metrics["final_drift"] < 0.15
    log_file = Path(metrics["log_path"])
    assert log_file.is_file()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0


def test_g8_live_realization_modes(tmp_path: Path):
    """G8: Verify D-152 §5 Diagnostic Fold (NOT_APPLICABLE) and live fills (PASS)."""
    # 1. Candidate / Research phase without live venue
    state, metrics = evaluate_g8_live_realization(live_fills_path=None)
    assert state == GateState.NOT_APPLICABLE
    assert metrics["mode"] == "DIAGNOSTIC_FOLD"

    # 2. Live venue settled fills
    fills_file = tmp_path / "fills.jsonl"
    fills_file.write_text(
        json.dumps({"fill_id": "F-001", "instrument": "BTCUSDT", "price": 105000, "qty": 0.01}) + "\n"
    )
    state_live, metrics_live = evaluate_g8_live_realization(live_fills_path=fills_file)
    assert state_live == GateState.PASS
    assert metrics_live["mode"] == "LIVE_VENUE_SETTLED"
    assert metrics_live["fills_count"] == 1


def test_g9_claim_registry_and_certificate_authority(tmp_path: Path):
    """G9: ClaimRegistry verifies ledger hash chain and issues signed StatutoryClaimRecord."""
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = BenchmarkLedger.load_jsonl(ledger_path)

    gates_ready = GateVector(
        g0_identity=GateState.PASS,
        g1_causal_pit=GateState.PASS,
        g2_determinism_ledger=GateState.PASS,
        g3_benchmark_coverage=GateState.PASS,
        g4_structural_robustness=GateState.PASS,
        g5_statistical_credibility=GateState.PASS,
        g6_protected_oos=GateState.PASS,
        g7_generalization=GateState.PASS,
        g8_prospective_shadow=GateState.NOT_APPLICABLE,
        g9_live_realization=GateState.MISSING,
    )

    receipt = BenchmarkReceipt.create(
        case_id="BC-TEST-G9",
        policy_id="pol_test",
        capability_score=75.0,
        gates=gates_ready,
        computed_at_timestamp_ns=1000,
    )
    ledger.append(receipt)

    state, metrics, claim = evaluate_g9_certificate_authority(
        ledger=ledger,
        receipt_digest=receipt.receipt_digest,
        gates=gates_ready,
        capability_score=75.0,
        output_dir=tmp_path,
        live_realization_verified=False,
    )

    assert state == GateState.PASS
    assert claim is not None
    assert claim.claim_class == StatutoryClaimClass.ReadyNotClaimed
    assert claim.verify_signature() is True
    assert metrics["signature_verified"] is True


def test_end_to_end_benchmark_runner_resolved_gates(tmp_path: Path):
    """End-to-end: honest fail-closed chain on real tape (no vacuous PASS).

    On the current tape the policy barely fires, so G3/G4/G6 fail closed with
    named reasons, G5 discloses its regime-fallback source, no claim is minted
    and the certificate stays BLOCKED. The test pins the honesty machinery
    (reasons, disclosure, no-claim), not tape-dependent counts.
    """
    if not DEFAULT_TAPE_PATH.exists():
        pytest.skip("Real tape not found")
    candles = load_tape_candles(DEFAULT_TAPE_PATH, limit=500)
    case = BenchmarkCase(
        case_id="BC-INTEGRATION-01",
        policy_id="pol_28_ensemble",
        dataset_name="BTCUSDT-1H",
        strategy_config=ExpertStrategyConfig(min_support_quorum=1, max_contradiction_tolerance=28),
    )

    runner = BenchmarkRunner(output_dir=tmp_path / "benchmarks")
    result = runner.run(
        case,
        candles,
        resolve_gates=True,
    )

    # Structural gates hold on real data
    assert result.gates.g0_identity == GateState.PASS
    assert result.gates.g1_causal_pit == GateState.PASS
    assert result.gates.g2_determinism_ledger == GateState.PASS

    # Thin-sample gates fail closed with named reasons
    gm = result.gate_metrics or {}
    for gname, reason_code in (
        ("g3", "INSUFFICIENT_REGIME_TRADES"),
        ("g4", "INSUFFICIENT_SHOCK_SAMPLE"),
        ("g6", None),
    ):
        state = getattr(result.gates, {"g3": "g3_benchmark_coverage", "g4": "g4_structural_robustness", "g6": "g6_protected_oos"}[gname])
        assert state == GateState.BLOCKED, f"{gname} must fail closed on thin samples"
        assert gm[gname]["reason"] is not None
        if reason_code is not None:
            assert reason_code in gm[gname]["reason"]
    assert gm["g6"]["reason"] is not None

    # G5 discloses its sample source; G7 holds its window; G8 stays out of scope
    assert gm["g5"]["sample_source"] in ("own_track", "regime_fallback")
    assert gm["g5"]["own_sample_count"] <= result.total_trades + len(candles)
    assert result.gates.g7_generalization == GateState.PASS
    assert result.gates.g8_prospective_shadow == GateState.NOT_APPLICABLE

    # No claim minted; certificate fails closed; ledger verifies
    assert result.claim_record is None
    verdict = result.gates.readiness()
    assert verdict.status == ReadinessStatus.HardFailure
    assert "BLOCKED" in result.certificate.status
    assert "NO_ECONOMIC_CLAIM" in result.certificate.authority_verdict or "BLOCKED" in result.certificate.authority_verdict
    chain_ok, _ = runner.ledger.verify_chain()
    assert chain_ok is True
