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


class PolicyCertificate(BaseModel):
    """Canonical D-153 Policy Certificate and Evidence Dashboard."""

    model_config = ConfigDict(frozen=True)

    policy_id: str
    receipt_id: str
    status: str
    authority_verdict: str
    gates: list[tuple[str, str]]
    research_capability_score: float
    evidence_multiplier: float
    minerva_robustness_score: float
    robustness_seal_status: str
    economic_score: float
    readiness_index: float
    quad_tape_role: str
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
        cap_score = round(min(100.0, max(0.0, receipt.capability_score)), 1)
        evidence_multiplier = round(min(1.0, max(0.10, receipt.coverage_factor)), 2)

        rob_score = 50.0
        seal_status = "SEAL_DENIED_NO_MINERVA_RUN"
        if minerva is not None:
            rob_score = getattr(minerva, "effective_score", 50.0)
            seal_status = getattr(minerva, "seal_status", "SEAL_DENIED_NO_MINERVA_RUN")

        # Economic score defaults to 60.0 in diagnostic cell if no projection
        economic_score = 60.0
        if projection is not None:
            economic_score = getattr(projection, "economic_score", 60.0)

        # Multiplicative Readiness Index
        readiness = (
            (cap_score / 100.0)
            * evidence_multiplier
            * (rob_score / 100.0)
            * (economic_score / 100.0)
            * 100.0
        )
        readiness_index = round(readiness, 1)

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
                f"   Score: {self.research_capability_score:>5.1f} / 100  {bar(self.research_capability_score, 100.0)}",
                f"   Evidence Multiplier: {self.evidence_multiplier:.2f}",
                "----------------------------------------------------------------------",
                "2. ECONOMIC EVIDENCE & MINERVA ROBUSTNESS (arXiv:2608.23808):",
                f"   Minerva Score:  {self.minerva_robustness_score:>5.1f} / 100  {bar(self.minerva_robustness_score, 100.0)}",
                f"   Robustness Seal: {self.robustness_seal_status}",
                f"   Evidence Topology: {self.quad_tape_role}",
                "----------------------------------------------------------------------",
                "3. RISK-ADJUSTED CAPITAL PROJECTION ($1,000 Initial, 1-Year Horizon):",
                "   [Underpowered sample or diagnostic run: extreme percentiles suppressed]",
                "----------------------------------------------------------------------",
                f"READINESS INDEX: {self.readiness_index:>5.1f} / 100",
                f"Formula: Cap ({self.research_capability_score:.1f}) * Evidence ({self.evidence_multiplier:.2f}) * Robustness ({self.minerva_robustness_score:.1f}) * Economic ({self.economic_score:.1f}) / 100^2",
                "======================================================================",
                "",
            ]
        )
        return "\n".join(lines)
