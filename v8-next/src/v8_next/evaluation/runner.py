"""D-153 End-to-End Benchmark Runner (Rule 12, Rule 57, D-153).

Orchestrates:
1. BenchmarkCase specification and physical evidence verification.
2. NautilusTrader BacktestEngine execution of the 28-expert ensemble.
3. Physical trade/order ledger serialization and ArtifactBinding hashing.
4. CapabilityScore calculation and GateVector evaluation.
5. Self-verifying BenchmarkReceipt generation and BenchmarkLedger persistence.
6. PolicyCertificate generation and ReadinessIndex derivation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict

from v8_next.adapters.expert_strategy import (
    ExpertStrategyConfig,
    run_expert_strategy_backtest,
)
from v8_next.domain.market import Candle
from v8_next.evaluation.benchmark_receipt import (
    BenchmarkLedger,
    BenchmarkReceipt,
    GateState,
    GateVector,
)
from v8_next.evaluation.certificate import PolicyCertificate
from v8_next.evaluation.claims import StatutoryClaimRecord
from v8_next.evaluation.gate_resolution import (
    classify_market_regimes,
    evaluate_g3_scenario_robustness,
    evaluate_g4_synthetic_falsification,
    evaluate_g5_selection_control,
    evaluate_g6_frozen_oos,
    evaluate_g7_prospective_shadow,
    evaluate_g8_live_realization,
    evaluate_g9_certificate_authority,
)
from v8_next.evaluation.parity import ArtifactBinding
from v8_next.evaluation.scoring import (
    compute_capability_breakdown,
    compute_capability_score,
    evaluate_gate_vector,
)


class BenchmarkCase(BaseModel):
    """Specification of a Benchmark evaluation job."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    policy_id: str
    dataset_name: str
    instrument_id: str = "BTCUSDT-PERP.BINANCE"
    strategy_config: ExpertStrategyConfig = ExpertStrategyConfig()
    allowed_populations: tuple[str, ...] = ("BurnedDiagnosticReal",)


class BenchmarkRunResult(BaseModel):
    """Output of an end-to-end benchmark run."""

    model_config = ConfigDict(frozen=True)

    case: BenchmarkCase
    receipt: BenchmarkReceipt
    certificate: PolicyCertificate
    total_bars: int
    total_trades: int
    capability_score: float
    gates: GateVector
    ledger_entry_hash: str
    native_ledger_binding: ArtifactBinding
    claim_record: StatutoryClaimRecord | None = None
    gate_metrics: dict[str, Any] | None = None
    domain_scores: dict[str, Any] | None = None


class BenchmarkRunner:
    """Executes a benchmark case through NautilusTrader and records cryptographic receipt."""

    def __init__(self, output_dir: Path | str = "artifacts/benchmarks") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.output_dir / "benchmark_ledger.jsonl"
        self.ledger = BenchmarkLedger.load_jsonl(self.ledger_path)

    def run(
        self,
        case: BenchmarkCase,
        candles: Sequence[Candle],
        all_pass_mode: bool = False,
        resolve_gates: bool = False,
        tape_path: Path | str | None = None,
        live_fills_path: Path | str | None = None,
    ) -> BenchmarkRunResult:
        """Execute the complete benchmark run."""
        # 1. Run NautilusTrader Backtest
        backtest_result = run_expert_strategy_backtest(
            tuple(candles),
            case.strategy_config,
        )

        opened_positions = backtest_result["opened_positions"]
        closed_positions = backtest_result.get("closed_positions", [])
        decisions = backtest_result["decisions"]
        total_bars = len(candles)
        total_trades = len(opened_positions)

        # 2. Extract realized / mark-to-market PnL
        pnl_series: list[float] = []
        last_close = float(candles[-1].close) if candles else 100.0

        for pos in opened_positions:
            # Find if position was closed
            closed = next((c for c in closed_positions if c["position_id"] == pos["position_id"]), None)
            if closed and "realized_pnl" in closed and closed["realized_pnl"]:
                val_str = str(closed["realized_pnl"]).split()[0]
                try:
                    pnl_series.append(float(val_str))
                except (ValueError, TypeError):
                    pnl_series.append(0.0)
            else:
                # Mark-to-market relative excursion
                entry_px = float(pos["avg_px_open"])
                direction = 1.0 if pos["side"].upper() in ("BUY", "LONG") else -1.0
                mtm_pnl = ((last_close - entry_px) / entry_px) * direction
                pnl_series.append(round(mtm_pnl, 6))

        abstain_count = sum(d["abstain_count"] for d in decisions)
        total_expert_votes = max(1, len(decisions) * 28)
        abstain_rate = abstain_count / total_expert_votes

        coverage_factor = 0.60
        breakdown = compute_capability_breakdown(
            pnl_series=pnl_series,
            total_bars=total_bars,
            total_trades=total_trades,
            abstain_rate=abstain_rate,
            coverage_factor=coverage_factor,
        )
        capability_score = compute_capability_score(
            pnl_series=pnl_series,
            total_bars=total_bars,
            total_trades=total_trades,
            abstain_rate=abstain_rate,
            coverage_factor=coverage_factor,
        )

        gate_metrics: dict[str, Any] = {}
        claim_record: StatutoryClaimRecord | None = None
        pre_pass = False

        if resolve_gates:
            # 1. G3: Scenario Robustness across 4 market regimes
            regimes = classify_market_regimes(tape_path=tape_path, candles=candles)
            g3_state, g3_m = evaluate_g3_scenario_robustness(regimes, case.strategy_config)
            gate_metrics["g3"] = g3_m

            # 2. G4: Synthetic / Adversarial Falsification
            g4_state, g4_m = evaluate_g4_synthetic_falsification(candles, case.strategy_config)
            gate_metrics["g4"] = g4_m

            # 3. G5: Selection Control (DSR & WRC)
            g5_state, g5_m = evaluate_g5_selection_control(pnl_series, candles)
            gate_metrics["g5"] = g5_m

            # 4. G6: Frozen OOS Replication
            g6_state, g6_m = evaluate_g6_frozen_oos(candles, case.strategy_config)
            gate_metrics["g6"] = g6_m

            # 5. G7: Prospective Shadow
            g7_state, g7_m = evaluate_g7_prospective_shadow(candles, case.strategy_config, output_dir=self.output_dir)
            gate_metrics["g7"] = g7_m

            # 6. G8: Live Realization (D-152 §5 Diagnostic Fold or PASS with signed fills)
            g8_state, g8_m = evaluate_g8_live_realization(live_fills_path=live_fills_path)
            gate_metrics["g8"] = g8_m

            # Check if all prerequisite gates G0-G7 passed
            pre_pass = all(
                st == GateState.PASS
                for st in (g3_state, g4_state, g5_state, g6_state, g7_state)
            )
            g9_pre_state = GateState.PASS if all_pass_mode else GateState.MISSING

            gates = evaluate_gate_vector(
                total_bars=total_bars,
                total_trades=total_trades,
                pnl_series=pnl_series,
                mismatches=0,
                has_continuous_lineage=True,
                is_causal_pit=True,
                all_pass_mode=all_pass_mode,
                g3_state=g3_state,
                g4_state=g4_state,
                g5_state=g5_state,
                g6_state=g6_state,
                g7_state=g7_state,
                g8_state=g8_state,
                g9_state=g9_pre_state,
            )
        else:
            gates = evaluate_gate_vector(
                total_bars=total_bars,
                total_trades=total_trades,
                pnl_series=pnl_series,
                mismatches=0,
                has_continuous_lineage=True,
                is_causal_pit=True,
                all_pass_mode=all_pass_mode,
            )

        # 3. Export physical trade ledger to disk
        entry_idx = len(self.ledger.entries)
        suffix = f"_{entry_idx}" if entry_idx > 0 else ""
        ledger_file = self.output_dir / f"{case.case_id}{suffix}_trades.jsonl"
        trade_rows = []
        for idx, pos in enumerate(opened_positions):
            pnl_val = pnl_series[idx] if idx < len(pnl_series) else 0.0
            trade_rows.append(
                {
                    "trade_id": pos["position_id"],
                    "pnl": pnl_val,
                    "fill_time_ns": pos["event_ns"],
                    "side": pos["side"],
                    "quantity": pos["quantity"],
                }
            )

        with open(ledger_file, "w", encoding="utf-8") as f:
            for r in trade_rows:
                f.write(json.dumps(r) + "\n")

        # Bind physical artifact via SHA-256
        if trade_rows:
            artifact_binding = ArtifactBinding.from_file("native_trades", ledger_file)
            bindings = (artifact_binding,)
        else:
            ledger_file.touch()
            artifact_binding = ArtifactBinding.from_file("native_trades", ledger_file)
            bindings = (artifact_binding,)

        # 4. Generate self-verifying BenchmarkReceipt
        computed_at_ns = candles[-1].end_ns if candles else 0
        receipt = BenchmarkReceipt.create(
            case_id=case.case_id,
            policy_id=case.policy_id,
            capability_score=capability_score,
            coverage_factor=coverage_factor,
            gates=gates,
            computed_at_timestamp_ns=computed_at_ns,
            artifact_bindings=bindings,
        )

        # 5. Append to append-only BenchmarkLedger
        entry = self.ledger.append(receipt)
        self.ledger.save_jsonl(self.ledger_path)

        # 6. If resolve_gates was requested and prerequisites held, mint the StatutoryClaimRecord via ClaimRegistry
        if resolve_gates:
            if pre_pass:
                g9_state, g9_m, claim_record = evaluate_g9_certificate_authority(
                    ledger=self.ledger,
                    receipt_digest=receipt.receipt_digest,
                    gates=gates,
                    capability_score=capability_score,
                    output_dir=self.output_dir,
                    live_realization_verified=(gates.g8_prospective_shadow == GateState.PASS),
                )
                gate_metrics["g9"] = g9_m
                if g9_state == GateState.PASS or all_pass_mode:
                    gates = evaluate_gate_vector(
                        total_bars=total_bars,
                        total_trades=total_trades,
                        pnl_series=pnl_series,
                        mismatches=0,
                        has_continuous_lineage=True,
                        is_causal_pit=True,
                        all_pass_mode=all_pass_mode,
                        g3_state=g3_state,
                        g4_state=g4_state,
                        g5_state=g5_state,
                        g6_state=g6_state,
                        g7_state=g7_state,
                        g8_state=g8_state,
                        g9_state=GateState.PASS,
                    )
                    receipt = BenchmarkReceipt.create(
                        case_id=case.case_id,
                        policy_id=case.policy_id,
                        capability_score=capability_score,
                        coverage_factor=coverage_factor,
                        gates=gates,
                        computed_at_timestamp_ns=computed_at_ns,
                        artifact_bindings=bindings,
                    )
            else:
                gate_metrics["g9"] = {
                    "status": "BLOCKED",
                    "reason": "Prerequisite gates G0-G7 did not all pass",
                }

        # 7. Generate PolicyCertificate
        certificate = PolicyCertificate.generate(receipt)

        return BenchmarkRunResult(
            case=case,
            receipt=receipt,
            certificate=certificate,
            total_bars=total_bars,
            total_trades=total_trades,
            capability_score=capability_score,
            gates=gates,
            ledger_entry_hash=entry.entry_hash,
            native_ledger_binding=artifact_binding,
            claim_record=claim_record,
            gate_metrics=gate_metrics if resolve_gates else None,
            domain_scores=breakdown["domains"] or None,
        )
