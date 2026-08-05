"""Random-audit miss rate and completion-gate checks.

Saturation alone cannot compensate for failed random-audit recall (spec) --
this module is what makes that failure visible rather than assumed away by a
high mark count.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..discovery.random_audit import AuditSample, miss_rate


@dataclass
class CompletionGateResult:
    passed: bool
    failures: list[str]


def check_mandatory_coverage(
    *,
    sources_ingested: int,
    sources_total: int,
    chapters_with_navigation: int,
    chapters_total: int,
) -> list[str]:
    failures = []
    if sources_ingested < sources_total:
        failures.append(
            f"structural ingestion incomplete: {sources_ingested}/{sources_total} sources"
        )
    if chapters_with_navigation < chapters_total:
        failures.append(
            f"navigation coverage incomplete: {chapters_with_navigation}/{chapters_total} chapters"
        )
    return failures


def check_discovery_recall(
    audited: list[AuditSample], missed_node_ids: set[str], threshold: float
) -> list[str]:
    report = miss_rate(audited, missed_node_ids)
    if report["miss_rate"] > threshold:
        return [
            f"random audit miss rate {report['miss_rate']} exceeds pilot threshold {threshold} "
            f"(uncertainty ±{report['uncertainty']})"
        ]
    return []


def check_resolution(unresolved_critical_ids: list[str]) -> list[str]:
    if unresolved_critical_ids:
        return [f"{len(unresolved_critical_ids)} unresolved CRITICAL rereads remain"]
    return []


def completion_gate(
    *,
    coverage_failures: list[str],
    recall_failures: list[str],
    resolution_failures: list[str],
) -> CompletionGateResult:
    """COMPLETE requires every preregistered gate to pass; a report may not
    hide unresolved critical rereads behind a summary (cheap test #13) -- the
    failures list is returned in full, not truncated.
    """
    failures = [*coverage_failures, *recall_failures, *resolution_failures]
    return CompletionGateResult(passed=not failures, failures=failures)
