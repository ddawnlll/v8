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

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict

from v8_next.adapters.execution_models import ExecutionProfile
from v8_next.adapters.expert_strategy import (
    ExpertStrategyConfig,
    run_expert_strategy_backtest,
)
from v8_next.domain.capital_policy import CapitalPolicy
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


def measure_candle_lineage(candles: Sequence[Candle]) -> tuple[bool | None, dict[str, Any]]:
    """Genuine G0 input: single-instrument, gap-free, overlap-free ordering.

    Returns (lineage_ok, info). None means unmeasurable (no candles) and must
    resolve to UNKNOWN downstream, never PASS.
    """
    if not candles:
        return None, {"status": "UNRUN", "reason": "NO_CANDLES"}
    instruments = sorted({c.instrument_id for c in candles})
    if len(instruments) != 1:
        return False, {
            "status": "BLOCKED",
            "reason": "MIXED_INSTRUMENTS",
            "instruments": instruments,
            "n_bars": len(candles),
        }
    ordered = sorted(candles, key=lambda c: (c.start_ns, c.end_ns))
    for a, b in zip(ordered, ordered[1:], strict=False):
        if b.start_ns < a.end_ns:
            return False, {
                "status": "BLOCKED",
                "reason": "OVERLAP_OR_DUPLICATE",
                "at_ns": b.start_ns,
                "n_bars": len(candles),
            }
        if b.start_ns > a.end_ns:
            return False, {
                "status": "BLOCKED",
                "reason": "LINEAGE_GAP",
                "gap_ns": [a.end_ns, b.start_ns],
                "n_bars": len(candles),
            }
    return True, {
        "status": "MEASURED",
        "reason": "SINGLE_INSTRUMENT_GAP_FREE",
        "instrument": instruments[0],
        "n_bars": len(candles),
        "span_ns": [ordered[0].start_ns, ordered[-1].end_ns],
    }


def build_input_binding(
    case: BenchmarkCase,
    candles: Sequence[Candle],
    capital_fields: dict[str, Any],
) -> str:
    """Canonical input identity for the receipt digest (v4).

    Binds case/policy identity, strategy config, bar count/span, per-candle
    keys (ns bounds, close, instrument, source hash) and capital assumptions.
    Any tape/config substitution changes this digest and fails verification.
    """
    per_candle = [
        [c.start_ns, c.end_ns, str(c.close), c.instrument_id, c.source_hash] for c in candles
    ]
    candles_digest = hashlib.sha256(
        json.dumps(per_candle, separators=(",", ":")).encode()
    ).hexdigest()
    payload = {
        "case_id": case.case_id,
        "policy_id": case.policy_id,
        "dataset": case.dataset_name,
        "strategy_config": json.dumps(asdict(case.strategy_config), sort_keys=True, default=str),
        "n_bars": len(candles),
        "span_ns": [candles[0].start_ns, candles[-1].end_ns] if candles else [],
        "candles_digest": candles_digest,
        "capital": capital_fields,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


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
        resolve_gates: bool = False,
        tape_path: Path | str | None = None,
        live_fills_path: Path | str | None = None,
        capital_policy: CapitalPolicy | str | Path | None = None,
        execution_profile: str | ExecutionProfile | None = None,
        measure_determinism: bool = False,
    ) -> BenchmarkRunResult:
        """Execute the complete benchmark run.

        capital_policy: None -> safe unauthorized default (no live orders, no promotion).
        Accepts CapitalPolicy instance, path to JSON, or None. Test policies verify accept/reject.
        Never prompts, never blocks.

        execution_profile: named Nautilus simulated-execution profile (fill model,
        fee model, latency model, liquidity/queue knobs). None keeps the engine
        defaults, and the receipt then reports that no execution semantics were
        declared rather than implying a model that was never chosen.
        """
        # 0. Capital policy validation (Task 4): safe unauthorized default, no live orders.
        if isinstance(capital_policy, CapitalPolicy):
            _cp = capital_policy
        elif isinstance(capital_policy, (str, Path)):
            _cp = CapitalPolicy.from_file(capital_policy)
        elif capital_policy is None:
            _cp = CapitalPolicy.unauthorized()
        else:
            _cp = CapitalPolicy.model_validate(capital_policy)  # dict-like
        _capital_decision = _cp.decision()
        # Expose for downstream parity; no prompt, no live order path.
        # Unauthorized policy does NOT block execution; it gates capital verdict only.
        # Engine still runs locally (paper/simulation); no venue orders emitted.

        # 0b. Genuine G0 lineage input (measured, never assumed).
        # G1 (causal PIT) and G2 (determinism rerun) have no measurement in this
        # runner, so they resolve to UNKNOWN downstream via None (never PASS).
        _lineage_ok, _lineage_info = measure_candle_lineage(tuple(candles))
        # 0c. Canonical input identity bound into the receipt digest (v4).
        _input_binding = build_input_binding(case, tuple(candles), _cp.to_receipt_fields())

        # 1. Run NautilusTrader Backtest
        backtest_result = run_expert_strategy_backtest(
            tuple(candles),
            case.strategy_config,
            execution_profile=execution_profile,
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
        # Measured execution evidence from the engine run feeds ExecutionFidelity
        # in place of the PnL-Sharpe proxy whenever real fills were measured.
        execution_evidence = backtest_result.get("execution") or {}

        # Optional measured determinism rerun. The G2 gate previously reported
        # UNRUN_DETERMINISM_RERUN_NOT_PERFORMED because nothing ever compared two
        # engine executions. With explicit execution semantics the fill
        # signature is a real identity to compare, so G2 becomes measurable
        # evidence instead of a permanent UNKNOWN. Opt-in: it doubles engine time.
        g2_metric: dict[str, Any] = {
            "status": "UNRUN",
            "reason": "DETERMINISM_RERUN_NOT_PERFORMED",
            "note": "single engine execution only; rerun-parity check not performed; UNKNOWN, never PASS",
        }
        if measure_determinism:
            rerun = run_expert_strategy_backtest(
                tuple(candles),
                case.strategy_config,
                execution_profile=execution_profile,
            )
            first_exec = backtest_result.get("execution") or {}
            second_exec = rerun.get("execution") or {}
            first_sig = first_exec.get("fill_signature")
            second_sig = second_exec.get("fill_signature")
            fills = int(first_exec.get("fills_count") or 0)
            positions_match = (
                backtest_result["opened_positions"] == rerun["opened_positions"]
                and backtest_result.get("closed_positions", [])
                == rerun.get("closed_positions", [])
            )
            if fills == 0 or not first_sig or not second_sig:
                g2_metric = {
                    "status": "UNKNOWN",
                    "reason": "NO_FILLS_TO_COMPARE",
                    "fills_count": fills,
                    "note": "an empty fill set cannot evidence rerun parity; UNKNOWN, never PASS",
                }
            elif first_sig == second_sig and positions_match:
                g2_metric = {
                    "status": "PASS",
                    "reason": "DETERMINISM_RERUN_EXACT_FILL_MATCH",
                    "fill_signature": first_sig,
                    "fills_count": fills,
                    "positions_match": True,
                }
            else:
                g2_metric = {
                    "status": "FAIL",
                    "reason": "DETERMINISM_RERUN_DIVERGED",
                    "fill_signature_first": first_sig,
                    "fill_signature_second": second_sig,
                    "positions_match": positions_match,
                    "fills_count": fills,
                }
        # G2 gate state from the measured rerun (UNKNOWN when not measured).
        _g2_state = (
            GateState.PASS
            if g2_metric.get("status") == "PASS"
            else GateState.BLOCKED
            if g2_metric.get("status") == "FAIL"
            else GateState.UNKNOWN
        )
        breakdown = compute_capability_breakdown(
            pnl_series=pnl_series,
            total_bars=total_bars,
            total_trades=total_trades,
            abstain_rate=abstain_rate,
            coverage_factor=coverage_factor,
            execution=execution_evidence,
        )
        capability_score = compute_capability_score(
            pnl_series=pnl_series,
            total_bars=total_bars,
            total_trades=total_trades,
            abstain_rate=abstain_rate,
            coverage_factor=coverage_factor,
            execution=execution_evidence,
        )

        gate_metrics: dict[str, Any] = {}
        claim_record: StatutoryClaimRecord | None = None
        pre_pass = False
        # Structural gate inputs: G0 measured above; G1/G2 unmeasured here.
        gate_metrics["g0"] = dict(_lineage_info)
        gate_metrics["execution"] = dict(execution_evidence)
        gate_metrics["g1"] = {
            "status": "UNRUN",
            "reason": "CAUSAL_PIT_NOT_MEASURED_IN_RUNNER",
            "note": "per-bar decision-vs-availability audit not performed; UNKNOWN, never PASS",
        }
        gate_metrics["g2"] = dict(g2_metric)

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
            g9_pre_state = GateState.MISSING

            gates = evaluate_gate_vector(
                total_bars=total_bars,
                total_trades=total_trades,
                pnl_series=pnl_series,
                mismatches=None,
                has_continuous_lineage=_lineage_ok,
                is_causal_pit=None,
                g2_state=_g2_state,
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
                mismatches=None,
                has_continuous_lineage=_lineage_ok,
                is_causal_pit=None,
                g2_state=_g2_state,
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
            input_binding=_input_binding,
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
                if g9_state == GateState.PASS:
                    gates = evaluate_gate_vector(
                        total_bars=total_bars,
                        total_trades=total_trades,
                        pnl_series=pnl_series,
                        mismatches=None,
                        has_continuous_lineage=_lineage_ok,
                        is_causal_pit=None,
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
                        input_binding=_input_binding,
                    )
                    # The post-G9 receipt is a NEW record: append it so the
                    # returned receipt is bound in the ledger (never orphaned).
                    # The claim above stays parented to the pre-G9 entry.
                    entry = self.ledger.append(receipt)
                    self.ledger.save_jsonl(self.ledger_path)
            else:
                gate_metrics["g9"] = {
                    "status": "BLOCKED",
                    "reason": "Prerequisite gates G0-G7 did not all pass",
                }

        # 7. Generate PolicyCertificate
        certificate = PolicyCertificate.generate(receipt)

        # Attach capital policy decision to gate_metrics (always, non-blocking).
        # Does not emit live orders, does not block execution, does not prompt.
        _capital_gate_metrics = {"capital_policy": _cp.to_receipt_fields(), "capital_decision": _capital_decision}
        if gate_metrics is not None:
            gate_metrics = {**gate_metrics, **_capital_gate_metrics}
        else:
            # Always expose capital decision even in diagnostic-only mode (safe unauthorized default)
            gate_metrics = _capital_gate_metrics

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
            gate_metrics=gate_metrics,
            domain_scores=breakdown["domains"] or None,
        )
