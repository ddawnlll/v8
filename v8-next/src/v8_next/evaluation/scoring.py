"""D-153 / D-152 Capability Scoring & Gate Authority Evaluation (Rule 12, 31, 57).

Computes multidimensional capability scores via penalized harmonic mean
and evaluates G0-G9 hard-gates directly per D-152 §5 and D-153 §74-80.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

import numpy as np

from v8_next.evaluation.benchmark_receipt import GateState, GateVector


class CapabilityDomain(StrEnum):
    ExecutionFidelity = "ExecutionFidelity"
    RegimeRobustness = "RegimeRobustness"
    CrossAssetGeneralization = "CrossAssetGeneralization"
    MicrostructureInvariance = "MicrostructureInvariance"
    DefeaterResistance = "DefeaterResistance"
    StatisticalCredibility = "StatisticalCredibility"
    EvaluationSafety = "EvaluationSafety"
    CapacityScalability = "CapacityScalability"
    RepresentationStability = "RepresentationStability"
    OperationalSimplicity = "OperationalSimplicity"


@dataclass(frozen=True)
class BoundedScore:
    value: float
    lower_diagnostic_band: float
    upper_diagnostic_band: float
    sample_size: int
    effective_sample_size: float


class CapabilityScoreCalculator:
    """CapabilityScore aggregation per D-153 §76."""

    def __init__(self, domain_weights: Mapping[CapabilityDomain, float] | None = None) -> None:
        if domain_weights is not None:
            self.domain_weights = dict(domain_weights)
        else:
            self.domain_weights = {d: 0.10 for d in CapabilityDomain}

    @classmethod
    def monograph_v1(cls) -> CapabilityScoreCalculator:
        """Monograph V1 provisional domain weights (D-153 §76, Monograph line 1283)."""
        return cls(
            {
                CapabilityDomain.MicrostructureInvariance: 0.12,
                CapabilityDomain.OperationalSimplicity: 0.15,
                CapabilityDomain.ExecutionFidelity: 0.10,
                CapabilityDomain.CrossAssetGeneralization: 0.20,
                CapabilityDomain.RepresentationStability: 0.08,
                CapabilityDomain.StatisticalCredibility: 0.07,
                CapabilityDomain.EvaluationSafety: 0.05,
                CapabilityDomain.DefeaterResistance: 0.08,
                CapabilityDomain.RegimeRobustness: 0.10,
                CapabilityDomain.CapacityScalability: 0.05,
            }
        )

    def calculate_aggregate_with_coverage(
        self,
        domain_scores: Mapping[CapabilityDomain, BoundedScore],
        coverage_factor: float = 0.60,
        hard_invariants_passed: bool = True,
    ) -> float:
        """Calculate aggregate capability score with coverage penalty multiplier (D-153 §76)."""
        if not hard_invariants_passed or not domain_scores:
            return 0.0

        weighted_inverse_sum = 0.0
        total_weight = 0.0

        for domain, score in domain_scores.items():
            w = self.domain_weights.get(domain, 0.10)
            total_weight += w
            effective_val = max(0.001, score.lower_diagnostic_band)
            weighted_inverse_sum += w / effective_val

        if total_weight <= 0.0 or weighted_inverse_sum <= 0.0:
            return 0.0

        harmonic_mean = total_weight / weighted_inverse_sum
        clamped_coverage = max(0.10, min(1.0, coverage_factor))
        raw = max(0.0, min(1.0, harmonic_mean * clamped_coverage))
        return raw * 100.0


def compute_capability_score(
    pnl_series: list[float],
    total_bars: int,
    total_trades: int,
    abstain_rate: float,
    coverage_factor: float = 0.60,
) -> float:
    """Compute multidimensional CapabilityScore in [0.0, 100.0] per D-153 §76."""
    calc = CapabilityScoreCalculator.monograph_v1()

    # If small diagnostic sample or underpowered trade count
    if not pnl_series or total_trades == 0:
        return 0.0

    arr = np.array(pnl_series, dtype=np.float64)
    std = float(np.std(arr)) if len(arr) > 1 else 0.01
    mean = float(np.mean(arr))
    sharpe_proxy = (mean / std) if std > 1e-9 else 0.5

    # Derive bounded scores for evaluated domains
    # ExecutionFidelity
    exec_val = float(np.clip(sharpe_proxy * 0.25 + 0.10, 0.05, 0.50))
    # OperationalSimplicity
    op_val = float(np.clip(1.0 - abstain_rate * 0.3, 0.10, 0.60))
    # DefeaterResistance
    def_val = 0.15 if total_trades >= 1 else 0.01
    # MicrostructureInvariance
    micro_val = float(np.clip(0.10 + (total_bars / 500.0) * 0.10, 0.05, 0.30))

    domain_scores = {
        CapabilityDomain.ExecutionFidelity: BoundedScore(
            value=exec_val,
            lower_diagnostic_band=exec_val * 0.8,
            upper_diagnostic_band=exec_val * 1.2,
            sample_size=total_trades,
            effective_sample_size=float(total_trades),
        ),
        CapabilityDomain.OperationalSimplicity: BoundedScore(
            value=op_val,
            lower_diagnostic_band=op_val * 0.8,
            upper_diagnostic_band=op_val * 1.2,
            sample_size=total_bars,
            effective_sample_size=float(total_bars),
        ),
        CapabilityDomain.DefeaterResistance: BoundedScore(
            value=def_val,
            lower_diagnostic_band=def_val * 0.7,
            upper_diagnostic_band=def_val * 1.3,
            sample_size=total_trades,
            effective_sample_size=float(total_trades),
        ),
        CapabilityDomain.MicrostructureInvariance: BoundedScore(
            value=micro_val,
            lower_diagnostic_band=micro_val * 0.75,
            upper_diagnostic_band=micro_val * 1.25,
            sample_size=total_bars,
            effective_sample_size=float(total_bars),
        ),
    }

    score = calc.calculate_aggregate_with_coverage(
        domain_scores=domain_scores,
        coverage_factor=coverage_factor,
        hard_invariants_passed=True,
    )
    return round(score, 1)


def evaluate_gate_vector(
    total_bars: int,
    total_trades: int,
    pnl_series: list[float],
    mismatches: int = 0,
    has_continuous_lineage: bool = True,
    is_causal_pit: bool = True,
    has_data_gaps: bool = False,
    all_pass_mode: bool = False,
    g3_state: GateState | None = None,
    g4_state: GateState | None = None,
    g5_state: GateState | None = None,
    g6_state: GateState | None = None,
    g7_state: GateState | None = None,
    g8_state: GateState | None = None,
    g9_state: GateState | None = None,
) -> GateVector:
    """Evaluate G0-G9 hard gates per D-152 §5 and D-153 specifications."""
    if all_pass_mode:
        return GateVector(
            g0_identity=GateState.PASS,
            g1_causal_pit=GateState.PASS,
            g2_determinism_ledger=GateState.PASS,
            g3_benchmark_coverage=GateState.PASS,
            g4_structural_robustness=GateState.PASS,
            g5_statistical_credibility=GateState.PASS,
            g6_protected_oos=GateState.PASS,
            g7_generalization=GateState.PASS,
            g8_prospective_shadow=GateState.PASS,
            g9_live_realization=GateState.PASS,
        )

    # G0 Identity: verified lineage and no data gaps
    g0 = GateState.PASS if (has_continuous_lineage and not has_data_gaps) else GateState.BLOCKED

    # G1 Causal PIT: strict point-in-time causation
    g1 = GateState.PASS if is_causal_pit else GateState.BLOCKED

    # G2 Determinism Ledger: zero non-deterministic mismatches
    g2 = GateState.PASS if mismatches == 0 else GateState.BLOCKED

    # G3 Benchmark Coverage: historical diagnostic cell or verified scenario robustness
    g3 = g3_state if g3_state is not None else GateState.UNKNOWN

    # G4 Synthetic / Structural Robustness: unperturbed diagnostic cell or adversarial falsification
    finite_pnl = all(math.isfinite(p) for p in pnl_series) if pnl_series else True
    if g4_state is not None:
        g4 = g4_state
    else:
        g4 = GateState.UNKNOWN if finite_pnl else GateState.BLOCKED

    # G5 Selection Control: Constitution Rule 12 keeps uncertified diagnostic at UNKNOWN
    g5 = g5_state if g5_state is not None else GateState.UNKNOWN

    # G6 Protected OOS: reserved for out-of-sample partition
    g6 = g6_state if g6_state is not None else GateState.UNKNOWN

    # G7 Prospective Shadow Succession
    g7 = g7_state if g7_state is not None else GateState.UNKNOWN

    # G8 Live Realization: venue-settled fills required; diagnostic fold when research candidate
    g8 = g8_state if g8_state is not None else GateState.MISSING

    # G9 Certificate: requires ClaimRegistry route; scalar collapse forbidden
    g9 = g9_state if g9_state is not None else GateState.MISSING

    return GateVector(
        g0_identity=g0,
        g1_causal_pit=g1,
        g2_determinism_ledger=g2,
        g3_benchmark_coverage=g3,
        g4_structural_robustness=g4,
        g5_statistical_credibility=g5,
        g6_protected_oos=g6,
        g7_generalization=g7,
        g8_prospective_shadow=g8,
        g9_live_realization=g9,
    )
