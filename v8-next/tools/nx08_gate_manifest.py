#!/usr/bin/env python
"""NX08 (#429) — dump the canonical gate map and the scoring/coverage artifacts.

Everything written here is read back from the live objects (the descriptor table,
GateVector, the resolvers, the scoring module and the certificate generator), so
the manifest is a measurement of the code rather than a transcription of it. The
gate map is written with its own consistency check result: if the map did not match
GateVector, the manifest would say so instead of hiding it.

Usage (from the repository root):

    uv run --project v8-next --extra dev --extra research \\
        python v8-next/tools/nx08_gate_manifest.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from v8_next.evaluation.benchmark_receipt import (
    GATE_DESCRIPTORS,
    BenchmarkReceipt,
    GateVector,
)
from v8_next.evaluation.certificate import PolicyCertificate
from v8_next.evaluation.gate_registry import gate_registry, validate_registry
from v8_next.evaluation.scoring import (
    LEGACY_FIXED_COVERAGE_FACTOR,
    derive_coverage,
    domain_measurement_statuses,
    dual_scoring,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measured_coverage_example() -> dict[str, object]:
    """Coverage for a run with trades, a run without trades, and an empty run."""
    cases: dict[str, object] = {}
    for label, (bars, trades, abstain) in {
        "traded_run": (744, 31, 0.05),
        "abstained_run": (744, 0, 1.0),
        "no_data_run": (0, 0, 0.0),
    }.items():
        coverage = derive_coverage(
            domain_measurement_statuses(total_bars=bars, total_trades=trades, abstain_rate=abstain)
        )
        cases[label] = {"inputs": {"bars": bars, "trades": trades, "abstain_rate": abstain}, **coverage}
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--out", default="docs/evidence/v87/NX08")
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    )
    out_dir = (repo_root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = gate_registry()
    gate_manifest = {
        "gate_count": len(registry),
        "gate_vector_fields": list(GateVector.model_fields),
        "descriptor_count": len(GATE_DESCRIPTORS),
        "consistency_problems": validate_registry(),
        "gates": [entry.as_dict() for entry in registry],
        "source": "evaluation/gate_registry.py derived from benchmark_receipt.GATE_DESCRIPTORS",
    }
    gate_path = out_dir / "gate_manifest.json"
    gate_path.write_text(json.dumps(gate_manifest, indent=2, sort_keys=True) + "\n")

    receipt = BenchmarkReceipt.create(
        case_id="NX08-MANIFEST",
        policy_id="pol_28_expert_ensemble",
        capability_score=42.0,
        coverage_factor=0.5,
        gates=GateVector(),
        computed_at_timestamp_ns=1_000,
        scoring_versions=dual_scoring([0.01, -0.02, 0.03, 0.005] * 10, 60, 6, 0.2),
    )
    certificate = PolicyCertificate.generate(receipt)
    scoring_manifest = {
        "legacy_fixed_coverage_factor": LEGACY_FIXED_COVERAGE_FACTOR,
        "coverage_cases": measured_coverage_example(),
        "dual_scoring_record": receipt.scoring_versions,
        "certificate": {
            "research_capability_score": certificate.research_capability_score,
            "evidence_multiplier": certificate.evidence_multiplier,
            "minerva_robustness_score": certificate.minerva_robustness_score,
            "economic_score": certificate.economic_score,
            "readiness_index": certificate.readiness_index,
            "readiness_upper_bound": certificate.readiness_upper_bound,
            "missing_measurements": list(certificate.missing_measurements),
            "robustness_seal_status": certificate.robustness_seal_status,
            "derivation": certificate.derivation,
        },
        "receipt_digest": receipt.receipt_digest,
        "receipt_verifies": receipt.verify()[0],
        "scoring_versions_not_in_digest": True,
        "economic_claim": "NONE",
        "g7_default_state": {
            "reason": "PSEUDO_PROSPECTIVE_HISTORICAL_WINDOW_NOT_ACCEPTED is returned when no "
            "shadow_stream is declared (NX08.R4)",
        },
        "evidence_class": (
            "MANIFEST OF MEASURED CODE: derived from the live registry, scoring module and "
            "certificate generator; no score target, no PASS"
        ),
    }
    scoring_path = out_dir / "scoring_manifest.json"
    scoring_path.write_text(json.dumps(scoring_manifest, indent=2, sort_keys=True) + "\n")

    print(f"[NX08] gates={len(registry)} problems={validate_registry()}")
    print(f"[NX08] readiness_index={certificate.readiness_index} missing={list(certificate.missing_measurements)}")
    print(f"[NX08] gate_manifest    sha256:{_sha256(gate_path)}")
    print(f"[NX08] scoring_manifest sha256:{_sha256(scoring_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
