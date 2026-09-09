"""Self-verifying Benchmark Receipt and Append-Only Ledger (D-153 §3, Issue #328).

Epistemic Invariant:
    receipt_digest = H(canonical_encode(all_authority_relevant_fields))
    Ledger maintains a cryptographic hash chain: entry_hash = H(parent_hash || receipt_digest).
    Any mutation at rest, sequence gap, or tampering is detected and fails closed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict

from v8_next.evaluation.parity import ArtifactBinding

RECEIPT_DIGEST_VERSION = "v8.5-digest-v2"


class GateState(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    DEFEATED = "DEFEATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING = "MISSING"

    def is_pass(self) -> bool:
        return self == GateState.PASS

    def is_failure(self) -> bool:
        return self in (GateState.BLOCKED, GateState.DEFEATED)

    def failure_class(self) -> str | None:
        if self in (GateState.PASS, GateState.NOT_APPLICABLE):
            return None
        if self in (GateState.BLOCKED, GateState.DEFEATED):
            return "HardFailure"
        if self == GateState.UNKNOWN:
            return "InsufficientEvidence"
        return "MissingEvidence"


@dataclass(frozen=True)
class GateDescriptor:
    index: int
    canonical_id: str
    vector_field: str
    requirement: str
    source_clause: str


GATE_DESCRIPTORS: tuple[GateDescriptor, ...] = (
    GateDescriptor(
        index=0,
        canonical_id="G0ConstitutionalIntegrity",
        vector_field="g0_identity",
        requirement="RequiredBlocking",
        source_clause="G0 constitutional/causal integrity (PIT, ChronosGate, determinism, ledger conservation, receipt integrity, non-escalation, synthetic isolation, claim typing): hard fail blocks all.",
    ),
    GateDescriptor(
        index=1,
        canonical_id="G1MeasurementIdentity",
        vector_field="g1_causal_pit",
        requirement="RequiredBlocking",
        source_clause="G1 measurement identity (estimand, data role, lineage, search lineage, cost/execution/world versions, burn marking): hard fail blocks inference.",
    ),
    GateDescriptor(
        index=2,
        canonical_id="G2HistoricalDiagnostic",
        vector_field="g2_determinism_ledger",
        requirement="Required",
        source_clause="G2 historical diagnostic court: outcome is diagnostic state, promotion NONE.",
    ),
    GateDescriptor(
        index=3,
        canonical_id="G3ScenarioRobustness",
        vector_field="g3_benchmark_coverage",
        requirement="Required",
        source_clause="G3 scenario coverage & behavioral robustness: unknown stays unknown.",
    ),
    GateDescriptor(
        index=4,
        canonical_id="G4SyntheticFalsification",
        vector_field="g4_structural_robustness",
        requirement="Required",
        source_clause="G4 adversarial/synthetic falsification: PASS mints nothing; FAIL is passport-scoped.",
    ),
    GateDescriptor(
        index=5,
        canonical_id="G5SelectionControl",
        vector_field="g5_statistical_credibility",
        requirement="Required",
        source_clause="G5 selection control: WRC + genuine DSR + SPA remain the active burden ... keeps G5 at NO_ECONOMIC_CLAIM.",
    ),
    GateDescriptor(
        index=6,
        canonical_id="G6FrozenOOSReplication",
        vector_field="g6_protected_oos",
        requirement="Required",
        source_clause="G6 frozen-OOS replication: PASS = bounded replication only.",
    ),
    GateDescriptor(
        index=7,
        canonical_id="G7ProspectiveShadow",
        vector_field="g7_generalization",
        requirement="Required",
        source_clause="G7 prospective shadow succession: `EvaluationEpoch` forward evidence, survival/drift/drawdown, e-process state.",
    ),
    GateDescriptor(
        index=8,
        canonical_id="G8LiveRealization",
        vector_field="g8_prospective_shadow",
        requirement="Required",
        source_clause="G8 live realization: venue-settled fills/costs/settlement/deviation/capacity/incidents. Historical/synthetic never substitutes.",
    ),
    GateDescriptor(
        index=9,
        canonical_id="G9Certificate",
        vector_field="g9_live_realization",
        requirement="Required",
        source_clause="G9 certificate: non-scalar `ProductionEvidenceCertificate` + profile conclusion; scalar collapse forbidden.",
    ),
)


class ReadinessStatus(StrEnum):
    Certified = "READY_NOT_CLAIMED"
    HardFailure = "BLOCKED"
    InsufficientEvidence = "NO_ECONOMIC_CLAIM"


@dataclass(frozen=True)
class GateEvaluation:
    descriptor: GateDescriptor
    state: GateState

    def holds(self) -> bool:
        return self.state in (GateState.PASS, GateState.NOT_APPLICABLE)


@dataclass(frozen=True)
class ReadinessVerdict:
    evaluations: tuple[GateEvaluation, ...]
    status: ReadinessStatus
    failing_positions: tuple[int, ...]
    hard_failures: tuple[int, ...]
    evidence_gaps: tuple[int, ...]

    def status_string(self) -> str:
        return self.status.value


class GateVector(BaseModel):
    model_config = ConfigDict(frozen=True)

    g0_identity: GateState = GateState.MISSING
    g1_causal_pit: GateState = GateState.MISSING
    g2_determinism_ledger: GateState = GateState.MISSING
    g3_benchmark_coverage: GateState = GateState.MISSING
    g4_structural_robustness: GateState = GateState.MISSING
    g5_statistical_credibility: GateState = GateState.MISSING
    g6_protected_oos: GateState = GateState.MISSING
    g7_generalization: GateState = GateState.MISSING
    g8_prospective_shadow: GateState = GateState.MISSING
    g9_live_realization: GateState = GateState.MISSING

    def evaluated_gates(self) -> list[GateEvaluation]:
        ordered_fields = [
            self.g0_identity,
            self.g1_causal_pit,
            self.g2_determinism_ledger,
            self.g3_benchmark_coverage,
            self.g4_structural_robustness,
            self.g5_statistical_credibility,
            self.g6_protected_oos,
            self.g7_generalization,
            self.g8_prospective_shadow,
            self.g9_live_realization,
        ]
        return [
            GateEvaluation(descriptor=GATE_DESCRIPTORS[i], state=ordered_fields[i])
            for i in range(10)
        ]

    def all_pass(self) -> bool:
        return all(g.holds() for g in self.evaluated_gates())

    def readiness(self) -> ReadinessVerdict:
        evals = self.evaluated_gates()
        failing: list[int] = []
        hard: list[int] = []
        gaps: list[int] = []

        for ev in evals:
            if ev.holds():
                continue
            failing.append(ev.descriptor.index)
            f_class = ev.state.failure_class()
            if f_class == "HardFailure":
                hard.append(ev.descriptor.index)
            else:
                gaps.append(ev.descriptor.index)

        if hard:
            status = ReadinessStatus.HardFailure
        elif not failing:
            status = ReadinessStatus.Certified
        else:
            status = ReadinessStatus.InsufficientEvidence

        return ReadinessVerdict(
            evaluations=tuple(evals),
            status=status,
            failing_positions=tuple(failing),
            hard_failures=tuple(hard),
            evidence_gaps=tuple(gaps),
        )


class BenchmarkReceipt(BaseModel):
    """Self-verifying cryptographic benchmark receipt."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    policy_id: str
    digest_version: str = RECEIPT_DIGEST_VERSION
    capability_score: float
    coverage_factor: float = 0.60
    gates: GateVector
    artifact_bindings: tuple[ArtifactBinding, ...] = ()
    computed_at_timestamp_ns: int
    receipt_digest: str = ""

    @classmethod
    def create(
        cls,
        case_id: str,
        policy_id: str,
        capability_score: float,
        gates: GateVector,
        computed_at_timestamp_ns: int,
        coverage_factor: float = 0.60,
        artifact_bindings: Sequence[ArtifactBinding] = (),
    ) -> BenchmarkReceipt:
        sorted_bindings = sorted(artifact_bindings, key=lambda b: (b.role, b.path))
        bindings_canon = [
            [b.role, b.sha256_hex, b.bytes] for b in sorted_bindings
        ]
        canon = [
            "BenchmarkReceipt",
            RECEIPT_DIGEST_VERSION,
            case_id,
            policy_id,
            round(capability_score, 8),
            round(coverage_factor, 4),
            [getattr(gates, f).value for f in sorted(gates.__class__.model_fields)],
            bindings_canon,
            computed_at_timestamp_ns,
        ]
        digest = hashlib.sha256(json.dumps(canon, separators=(",", ":")).encode()).hexdigest()

        return cls(
            case_id=case_id,
            policy_id=policy_id,
            digest_version=RECEIPT_DIGEST_VERSION,
            capability_score=capability_score,
            coverage_factor=coverage_factor,
            gates=gates,
            artifact_bindings=tuple(sorted_bindings),
            computed_at_timestamp_ns=computed_at_timestamp_ns,
            receipt_digest=digest,
        )

    def verify(self) -> tuple[bool, str]:
        """Recompute cryptographic digest and verify against attached artifacts."""
        # 1. Recompute digest
        sorted_bindings = sorted(self.artifact_bindings, key=lambda b: (b.role, b.path))
        bindings_canon = [
            [b.role, b.sha256_hex, b.bytes] for b in sorted_bindings
        ]
        canon = [
            "BenchmarkReceipt",
            self.digest_version,
            self.case_id,
            self.policy_id,
            round(self.capability_score, 8),
            round(self.coverage_factor, 4),
            [getattr(self.gates, f).value for f in sorted(self.gates.__class__.model_fields)],
            bindings_canon,
            self.computed_at_timestamp_ns,
        ]
        expected_digest = hashlib.sha256(json.dumps(canon, separators=(",", ":")).encode()).hexdigest()
        if expected_digest != self.receipt_digest:
            return False, f"DIGEST_TAMPERED: expected {expected_digest}, stored {self.receipt_digest}"

        # 2. Check artifact bindings on disk
        for b in self.artifact_bindings:
            ok, err = b.verify()
            if not ok:
                return False, f"ARTIFACT_TAMPERED: [{b.role}] {err}"

        return True, "OK"


class LedgerEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence_number: int
    parent_entry_hash: str
    receipt: BenchmarkReceipt
    entry_hash: str

    @classmethod
    def create(
        cls,
        sequence_number: int,
        parent_entry_hash: str,
        receipt: BenchmarkReceipt,
    ) -> LedgerEntry:
        canon = [
            sequence_number,
            parent_entry_hash,
            receipt.receipt_digest,
        ]
        entry_hash = hashlib.sha256(json.dumps(canon, separators=(",", ":")).encode()).hexdigest()
        return cls(
            sequence_number=sequence_number,
            parent_entry_hash=parent_entry_hash,
            receipt=receipt,
            entry_hash=entry_hash,
        )


class BenchmarkLedger:
    """Append-only cryptographically chained benchmark ledger."""

    GENESIS_HASH = "0" * 64

    def __init__(self, entries: list[LedgerEntry] | None = None) -> None:
        self._entries: list[LedgerEntry] = list(entries) if entries else []

    @property
    def entries(self) -> list[LedgerEntry]:
        return list(self._entries)

    def append(self, receipt: BenchmarkReceipt) -> LedgerEntry:
        ok, err = receipt.verify()
        if not ok:
            raise ValueError(f"Cannot append unverified receipt: {err}")

        seq = len(self._entries)
        parent_hash = self._entries[-1].entry_hash if self._entries else self.GENESIS_HASH
        entry = LedgerEntry.create(seq, parent_hash, receipt)
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> tuple[bool, str]:
        """Verify append-only chain integrity."""
        expected_parent = self.GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.sequence_number != i:
                return False, f"SEQUENCE_GAP: entry {i} has seq {entry.sequence_number}"
            if entry.parent_entry_hash != expected_parent:
                return False, f"BROKEN_CHAIN: entry {i} parent_hash mismatch"

            # Check receipt self-verification
            ok, err = entry.receipt.verify()
            if not ok:
                return False, f"ENTRY_RECEIPT_INVALID at {i}: {err}"

            # Check entry hash
            canon = [entry.sequence_number, entry.parent_entry_hash, entry.receipt.receipt_digest]
            recomputed = hashlib.sha256(json.dumps(canon, separators=(",", ":")).encode()).hexdigest()
            if recomputed != entry.entry_hash:
                return False, f"ENTRY_HASH_TAMPERED at {i}"

            expected_parent = entry.entry_hash

        return True, "OK"

    def save_jsonl(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for entry in self._entries:
                f.write(entry.model_dump_json() + "\n")

    @classmethod
    def load_jsonl(cls, path: Path | str) -> BenchmarkLedger:
        p = Path(path)
        if not p.is_file():
            return cls([])
        entries = []
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(LedgerEntry.model_validate_json(line))
        return cls(entries)

    def __len__(self) -> int:
        return len(self._entries)
