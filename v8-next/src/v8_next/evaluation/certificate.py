"""V8 Evidence Dashboard & Policy Certificate (D-153, D-152 §5).

Enforces:
- Epistemic separation between Research Capability, Robustness, and Capital Projection.
- Multiplicative Readiness Index:
  Readiness = (Cap / 100) * EvidenceMultiplier * (Robustness / 100) * (Economic / 100) * 100
- Binary Robustness Seal & Hard Gate Vector verification.
- Multi-population evidence topology (12-month quad tape as single diagnostic cell).
- Terminal ASCII and HTML certificate rendering.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from v8_next.evaluation.benchmark_receipt import (
    BenchmarkReceipt,
    GateState,
    ReadinessStatus,
)


def _render(value: float | None, digits: int = 1) -> str:
    """A missing measurement renders as MISSING, never as a zero."""
    return "MISSING" if value is None else f"{value:.{digits}f}"


class PolicyCertificate(BaseModel):
    """Canonical D-153 Policy Certificate and Evidence Dashboard."""

    model_config = ConfigDict(frozen=True)

    policy_id: str
    receipt_id: str
    status: str
    authority_verdict: str
    gates: list[tuple[str, str]]
    #: ``None`` wherever the measurement does not exist (NX08.R2). The previous
    #: defaults (robustness 50.0, economic 60.0) were fabricated inputs to the
    #: readiness formula and are gone: a missing factor now makes the readiness
    #: index missing instead of quietly producing a number.
    research_capability_score: float | None
    evidence_multiplier: float | None
    minerva_robustness_score: float | None
    robustness_seal_status: str
    economic_score: float | None
    readiness_index: float | None
    quad_tape_role: str
    derivation: dict[str, Any] | None = None
    missing_measurements: tuple[str, ...] = ()
    readiness_upper_bound: float | None = None
    minerva: Any | None = None
    monte_carlo: Any | None = None

    @classmethod
    def generate(
        cls,
        receipt: BenchmarkReceipt,
        projection: Any | None = None,
        minerva: Any | None = None,
    ) -> PolicyCertificate:
        """Generates a PolicyCertificate from evaluated benchmark artifacts."""
        raw_cap = receipt.capability_score
        cap_score = (
            None if raw_cap is None else round(min(100.0, max(0.0, raw_cap)), 1)
        )
        raw_coverage = receipt.coverage_factor
        evidence_multiplier = (
            None
            if raw_coverage is None
            else round(min(1.0, max(0.10, raw_coverage)), 2)
        )

        # Robustness: no default. Without a Minerva run there is no robustness
        # measurement, and the seal says so.
        seal_status = "SEAL_DENIED_NO_MINERVA_RUN"
        rob_score: float | None = None
        if minerva is not None:
            rob_score = getattr(minerva, "effective_score", None)
            seal_status = getattr(minerva, "seal_status", "SEAL_DENIED_NO_MINERVA_RUN")

        # Economic: no default in a diagnostic cell. A missing projection stays
        # missing instead of being scored 60.0.
        economic_score: float | None = None
        if projection is not None:
            economic_score = getattr(projection, "economic_score", None)

        # Multiplicative Readiness Index, evaluated only over factors that exist.
        factors: dict[str, float | None] = {
            "research_capability_score": cap_score,
            "evidence_multiplier": evidence_multiplier,
            "minerva_robustness_score": rob_score,
            "economic_score": economic_score,
        }
        missing = tuple(name for name, value in factors.items() if value is None)
        readiness_index: float | None = None
        readiness_upper_bound: float | None = None
        if not missing:
            # narrowed by "not missing": every factor exists, so the formula is
            # evaluated over real measurements only
            assert cap_score is not None
            assert evidence_multiplier is not None
            assert rob_score is not None
            assert economic_score is not None
            readiness_index = round(
                (cap_score / 100.0)  # type: ignore[operator]
                * evidence_multiplier  # type: ignore[operator]
                * (rob_score / 100.0)  # type: ignore[operator]
                * (economic_score / 100.0)  # type: ignore[operator]
                * 100.0,
                1,
            )
            # upper bound derived from the same formula: capability at its ceiling
            readiness_upper_bound = round(
                1.0
                * evidence_multiplier  # type: ignore[operator]
                * (rob_score / 100.0)  # type: ignore[operator]
                * (economic_score / 100.0)  # type: ignore[operator]
                * 100.0,
                1,
            )
        derivation = {
            "formula": "capability * evidence_multiplier * robustness * economic / 100**2",
            "transform_version": "readiness-v2-missing-aware",
            "raw_measurements": {
                "capability_score": receipt.capability_score,
                "coverage_factor": receipt.coverage_factor,
                "minerva_effective_score": rob_score,
                "projection_economic_score": economic_score,
            },
            "denominator": 100.0**2,
            "weights": {name: 1.0 for name in factors},
            "binding": {
                "receipt_digest": receipt.receipt_digest,
                "digest_version": receipt.digest_version,
                "gate_vector": {
                    field: getattr(receipt.gates, field).value
                    for field in sorted(receipt.gates.__class__.model_fields)
                },
            },
            "missing_measurements": list(missing),
        }

        verdict = receipt.gates.readiness()
        if verdict.status == ReadinessStatus.HardFailure:
            status = "STATUS: BLOCKED (hard gate failure)"
            authority_verdict = "VERDICT: BLOCKED (hard gate failure)"
        elif verdict.status == ReadinessStatus.Certified:
            status = "STATUS: Research Candidate Ready For Review NOT Production Approved"
            if receipt.gates.g9_live_realization == GateState.PASS:
                if receipt.gates.g8_prospective_shadow == GateState.PASS:
                    authority_verdict = "VERDICT: SUPPORTED_EDGE (Live venue fills settled & StatutoryClaimRecord registered)"
                else:
                    authority_verdict = "VERDICT: READY_NOT_CLAIMED (StatutoryClaimRecord registered; human review required for live capital)"
            else:
                authority_verdict = "VERDICT: NO_ECONOMIC_CLAIM (diagnostic instrument only; no economic authority may be derived)"
        else:
            status = "STATUS: NO_ECONOMIC_CLAIM (Research Candidate, NOT Production Approved)"
            authority_verdict = "VERDICT: NO_ECONOMIC_CLAIM (diagnostic instrument only; no economic authority may be derived)"

        quad_tape_role = "HISTORICAL DIAGNOSTIC CELL (Non-universal evaluation fold)"

        gates = [
            (
                f"{ev.descriptor.canonical_id}::{ev.descriptor.vector_field}",
                ev.state.value,
            )
            for ev in verdict.evaluations
        ]

        return cls(
            policy_id=receipt.policy_id,
            receipt_id=receipt.receipt_digest,
            status=status,
            authority_verdict=authority_verdict,
            gates=gates,
            research_capability_score=cap_score,
            evidence_multiplier=evidence_multiplier,
            minerva_robustness_score=rob_score,
            robustness_seal_status=seal_status,
            economic_score=economic_score,
            readiness_index=readiness_index,
            quad_tape_role=quad_tape_role,
            derivation=derivation,
            missing_measurements=missing,
            readiness_upper_bound=readiness_upper_bound,
            minerva=minerva,
            monte_carlo=None,
        )

    def render_ascii(self) -> str:
        """Renders clean terminal ASCII certificate matching D-153 Rust reference."""

        def bar(val: float, max_val: float) -> str:
            pct = min(1.0, max(0.0, val / max_val))
            filled = int(round(pct * 30.0))
            empty = 30 - filled
            return f"[{'|' * filled}{'.' * empty}]"

        lines = [
            "======================================================================",
            "               V8 EVIDENCE DASHBOARD & POLICY CERTIFICATE             ",
            "======================================================================",
            f"Policy Target:  {self.policy_id}",
            f"Receipt Digest: {self.receipt_id}",
            f"Final Verdict:  {self.status}",
            f"Authority:      {self.authority_verdict}",
            "----------------------------------------------------------------------",
            "0. HARD GATE VECTOR G0-G9 (non-compensable, D-152 §5):",
        ]
        for gate_name, state in self.gates:
            lines.append(f"   {gate_name:<58} [{state}]")
        lines.extend(
            [
                "----------------------------------------------------------------------",
                "1. RESEARCH CAPABILITY SCORE (Infrastructure & Integrity):",
                f"   Score: {_render(self.research_capability_score)} / 100  {bar(self.research_capability_score or 0.0, 100.0)}",
                f"   Evidence Multiplier: {_render(self.evidence_multiplier, 2)}",
                "----------------------------------------------------------------------",
                "2. ECONOMIC EVIDENCE & MINERVA ROBUSTNESS (arXiv:2608.23808):",
                f"   Minerva Score:  {_render(self.minerva_robustness_score)} / 100  {bar(self.minerva_robustness_score or 0.0, 100.0)}",
                f"   Robustness Seal: {self.robustness_seal_status}",
                f"   Evidence Topology: {self.quad_tape_role}",
                "----------------------------------------------------------------------",
                "3. RISK-ADJUSTED CAPITAL PROJECTION ($1,000 Initial, 1-Year Horizon):",
                "   [Underpowered sample or diagnostic run: extreme percentiles suppressed]",
                "----------------------------------------------------------------------",
                f"READINESS INDEX: {_render(self.readiness_index)} / 100",
                "Formula: Cap ({cap}) * Evidence ({ev}) * Robustness ({rob}) * Economic ({eco}) / 100^2".format(
                    cap=_render(self.research_capability_score),
                    ev=_render(self.evidence_multiplier, 2),
                    rob=_render(self.minerva_robustness_score),
                    eco=_render(self.economic_score),
                ),
                f"Missing measurements: {', '.join(self.missing_measurements) if self.missing_measurements else 'none'}",
                "======================================================================",
                "",
            ]
        )
        return "\n".join(lines)
