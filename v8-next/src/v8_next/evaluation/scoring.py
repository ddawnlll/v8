"""D-153 / D-152 Capability Scoring & Gate Authority Evaluation (Rule 12, 31, 57).

Computes multidimensional capability scores via penalized harmonic mean
and evaluates G0-G9 hard-gates directly per D-152 §5 and D-153 §74-80.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

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


#: Declared diagnostic convention (NOT a calibration): a mean absolute
#: implementation shortfall of this many basis points scores zero execution
#: fidelity, and a measured shortfall of zero scores the top of the domain's
#: declared [0.0, 1.0] range. Published with every score so the convention is
#: auditable and can be replaced by a calibrated reference once one exists.
EXECUTION_FIDELITY_REFERENCE_BPS = 10.0

#: The measured statistic the convention above is declared over: the mean
#: *magnitude* of the per-fill implementation shortfall, published by
#: ``v8_next.adapters.execution_telemetry.execution_telemetry``. The signed mean
#: is deliberately NOT used: adverse and favourable fills cancel in it, so a
#: window whose fills all deviated can still average to ~0 bps.
EXECUTION_FIDELITY_SHORTFALL_FIELD = "slippage_bps_abs_mean"


def _execution_fidelity(
    sharpe_proxy: float,
    execution: Mapping[str, Any] | None,
) -> tuple[float, str, float | None]:
    """ExecutionFidelity from measured shortfall when it exists, else the proxy.

    The previous value was a rescaled PnL Sharpe that contained no execution
    information at all. Measured implementation shortfall is preferred; when no
    fills were measured the proxy is retained and its source published, so a
    score is never silently attributed to execution evidence it does not have.

    Declared measured mapping: ``1 - shortfall_bps / EXECUTION_FIDELITY_REFERENCE_BPS``
    clipped to the domain's declared [0.0, 1.0] range. The measured branch is
    therefore neither floored at nor capped by the proxy's undeclared
    [0.05, 0.50] band, which is what made every run publish a constant 0.50:
    0 bps must publish 1.0, and the 10 bps reference must publish 0.0. The third
    element is the shortfall value the score was computed from (None when the
    proxy was used), so the mapping stays auditable in the published breakdown.
    """
    if execution:
        samples = execution.get("slippage_samples") or 0
        shortfall_bps = execution.get(EXECUTION_FIDELITY_SHORTFALL_FIELD)
        if not isinstance(shortfall_bps, (int, float)):
            # A block persisted before the magnitude statistic existed still
            # carries measured evidence; |signed mean| is the same quantity minus
            # the cancellation between favourable and adverse fills.
            shortfall_bps = execution.get("slippage_bps_mean")
        if samples > 0 and isinstance(shortfall_bps, (int, float)):
            measured = abs(float(shortfall_bps))
            fidelity = 1.0 - measured / EXECUTION_FIDELITY_REFERENCE_BPS
            return (
                float(np.clip(fidelity, 0.0, 1.0)),
                "MEASURED_IMPLEMENTATION_SHORTFALL",
                measured,
            )
    return (
        float(np.clip(sharpe_proxy * 0.25 + 0.10, 0.05, 0.50)),
        "PNL_SHARPE_PROXY",
        None,
    )


def compute_capability_breakdown(
    pnl_series: list[float],
    total_bars: int,
    total_trades: int,
    abstain_rate: float,
    coverage_factor: float = 0.60,
    execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Per-domain capability breakdown for loop engineering.

    Returns {domain: {score, band_low, band_high, weight, sample_size}} plus
    the aggregate. An agent asking 'why did I stall at 8.8' reads this, not
    the scalar. Empty/underpowered input yields empty domains (never zeros
    disguised as measurements).
    """
    calc = CapabilityScoreCalculator.monograph_v1()
    if not pnl_series or total_trades == 0:
        return {
            "domains": {},
            "aggregate": 0.0,
            "coverage_factor": coverage_factor,
            "execution_fidelity_source": "NO_TRADES",
            "execution_fidelity_reference_bps": EXECUTION_FIDELITY_REFERENCE_BPS,
            "execution_fidelity_shortfall_bps": None,
        }

    arr = np.array(pnl_series, dtype=np.float64)
    std = float(np.std(arr)) if len(arr) > 1 else 0.01
    mean = float(np.mean(arr))
    sharpe_proxy = (mean / std) if std > 1e-9 else 0.5

    exec_val, exec_source, exec_shortfall_bps = _execution_fidelity(sharpe_proxy, execution)
    op_val = float(np.clip(1.0 - abstain_rate * 0.3, 0.10, 0.60))
    def_val = 0.15 if total_trades >= 1 else 0.01
    micro_val = float(np.clip(0.10 + (total_bars / 500.0) * 0.10, 0.05, 0.30))

    raw = {
        CapabilityDomain.ExecutionFidelity: (exec_val, 0.8, 1.2, total_trades),
        CapabilityDomain.OperationalSimplicity: (op_val, 0.8, 1.2, total_bars),
        CapabilityDomain.DefeaterResistance: (def_val, 0.7, 1.3, total_trades),
        CapabilityDomain.MicrostructureInvariance: (micro_val, 0.75, 1.25, total_bars),
    }
    domain_scores = {
        domain: BoundedScore(
            value=v,
            lower_diagnostic_band=v * lo,
            upper_diagnostic_band=v * hi,
            sample_size=n,
            effective_sample_size=float(n),
        )
        for domain, (v, lo, hi, n) in raw.items()
    }
    score = calc.calculate_aggregate_with_coverage(
        domain_scores=domain_scores,
        coverage_factor=coverage_factor,
        hard_invariants_passed=True,
    )
    domains: dict[str, Any] = {}
    for domain, bs in domain_scores.items():
        domains[domain.value] = {
            "score": round(bs.value * 100.0, 1),
            "band_low": round(bs.lower_diagnostic_band * 100.0, 1),
            "band_high": round(bs.upper_diagnostic_band * 100.0, 1),
            "weight": calc.domain_weights.get(domain, 0.10),
            "sample_size": bs.sample_size,
        }
    return {
        "domains": domains,
        "aggregate": round(score, 1),
        "coverage_factor": coverage_factor,
        "execution_fidelity_source": exec_source,
        "execution_fidelity_reference_bps": EXECUTION_FIDELITY_REFERENCE_BPS,
        # The measured input the ExecutionFidelity score was computed from, so a
        # reader can check the published score against the declared mapping
        # instead of trusting that the domain was bound to execution evidence.
        "execution_fidelity_shortfall_bps": (
            round(exec_shortfall_bps, 6) if exec_shortfall_bps is not None else None
        ),
    }


def compute_capability_score(
    pnl_series: list[float],
    total_bars: int,
    total_trades: int,
    abstain_rate: float,
    coverage_factor: float = 0.60,
    execution: Mapping[str, Any] | None = None,
) -> float:
    """Compute multidimensional CapabilityScore in [0.0, 100.0] per D-153 §76."""
    breakdown = compute_capability_breakdown(
        pnl_series=pnl_series,
        total_bars=total_bars,
        total_trades=total_trades,
        abstain_rate=abstain_rate,
        coverage_factor=coverage_factor,
        execution=execution,
    )
    return float(breakdown["aggregate"])


def evaluate_gate_vector(
    total_bars: int,
    total_trades: int,
    pnl_series: list[float],
    mismatches: int | None = 0,
    has_continuous_lineage: bool | None = True,
    is_causal_pit: bool | None = True,
    has_data_gaps: bool = False,
    g2_state: GateState | None = None,
    g3_state: GateState | None = None,
    g4_state: GateState | None = None,
    g5_state: GateState | None = None,
    g6_state: GateState | None = None,
    g7_state: GateState | None = None,
    g8_state: GateState | None = None,
    g9_state: GateState | None = None,
) -> GateVector:
    """Evaluate G0-G9 hard gates per D-152 §5 and D-153 specifications.

    Unmeasured structural inputs (None) resolve to UNKNOWN, never PASS:
    no gate may certify what was not empirically established.
    """
    # G0 Identity: verified lineage and no data gaps.
    # None (unmeasured) resolves to UNKNOWN, never PASS.
    if has_continuous_lineage is None:
        g0 = GateState.UNKNOWN
    else:
        g0 = GateState.PASS if (has_continuous_lineage and not has_data_gaps) else GateState.BLOCKED

    # G1 Causal PIT: strict point-in-time causation (None -> UNKNOWN).
    if is_causal_pit is None:
        g1 = GateState.UNKNOWN
    else:
        g1 = GateState.PASS if is_causal_pit else GateState.BLOCKED

    # G2 Determinism Ledger: zero non-deterministic mismatches (None -> UNKNOWN).
    # A measured rerun-parity state, when supplied, wins over the mismatch count:
    # the rerun compares two real engine executions, which is direct evidence.
    if g2_state is not None:
        g2 = g2_state
    elif mismatches is None:
        g2 = GateState.UNKNOWN
    else:
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
