"""S6 analysis plane — Python port of ``v8-core/src/analysis`` (D-091, COMPUTE_CORE_SPEC §6).

One module per concern, mirroring the Rust layout so a reader of either tree finds the same
names: ``outcome`` (the ten-field reconciliation surface), ``reconcile`` (the ledger
reconciliation plane), ``phases`` (regret phases 1-3) and ``veto_attribution`` (what the
funnel refused, and why).

Attribution always lands in the **seven canonical failure domains** of
``v8_next.system_proving.attribution`` — this package adds no eighth domain and no parallel
vocabulary.

``reconcile`` (the function) is deliberately not re-exported here: binding it to the package
would shadow the ``v8_next.analysis.reconcile`` submodule, so
``import v8_next.analysis.reconcile as m`` would hand back a function. Import it from the
submodule — ``from v8_next.analysis.reconcile import reconcile``.
"""

from v8_next.analysis.outcome import (
    RECONCILE_EXACT_FIELDS,
    RECONCILE_EXCLUDED_FIELDS,
    RECONCILE_FIELD_COUNT,
    RECONCILE_FLOAT_FIELDS,
    RECONCILE_TOLERANCE,
    OutcomeSurface,
    reconcile_surface,
)
from v8_next.analysis.reconcile import (
    BOUND,
    EVALUATOR_VERSION,
    MISMATCH_REASON_ENTRY_MISSING,
    MISMATCH_REASON_FIELD,
    RECONCILED,
    RECONCILIATION_FAILED,
    RECONCILIATION_NOT_MEASURED,
    UNBOUND_NO_DRAFT,
    CandidateSnapshot,
    ReconcileRequest,
    ReconciliationResult,
    assert_pit_lineage,
    build_snapshots,
    reconcile_actual_actions,
    reconciliation_artifact,
    reconciliation_summary,
)
from v8_next.analysis.veto_attribution import (
    ADMITTED_RISK_REASONS,
    CANDIDATE_REJECTION_REASONS,
    CANONICAL_VETO_REASONS,
    CLAIM,
    DIVERGENCES,
    RISK_GATE_REFUSAL_REASONS,
    AllocationRejectionReason,
    DedupRegretReport,
    RefusalStage,
    RefusedDecision,
    VetoAttributionRow,
    VetoAttributionSummary,
    compute_veto_attribution,
    refused_beside_lost,
)

__all__ = [
    "ADMITTED_RISK_REASONS",
    "BOUND",
    "CANONICAL_VETO_REASONS",
    "CANDIDATE_REJECTION_REASONS",
    "CLAIM",
    "DIVERGENCES",
    "EVALUATOR_VERSION",
    "MISMATCH_REASON_ENTRY_MISSING",
    "MISMATCH_REASON_FIELD",
    "RECONCILED",
    "RECONCILE_EXACT_FIELDS",
    "RECONCILE_EXCLUDED_FIELDS",
    "RECONCILE_FIELD_COUNT",
    "RECONCILE_FLOAT_FIELDS",
    "RECONCILE_TOLERANCE",
    "RECONCILIATION_FAILED",
    "RECONCILIATION_NOT_MEASURED",
    "RISK_GATE_REFUSAL_REASONS",
    "UNBOUND_NO_DRAFT",
    "AllocationRejectionReason",
    "CandidateSnapshot",
    "DedupRegretReport",
    "OutcomeSurface",
    "ReconcileRequest",
    "ReconciliationResult",
    "RefusalStage",
    "RefusedDecision",
    "VetoAttributionRow",
    "VetoAttributionSummary",
    "assert_pit_lineage",
    "build_snapshots",
    "compute_veto_attribution",
    "reconcile_actual_actions",
    "reconcile_surface",
    "reconciliation_artifact",
    "reconciliation_summary",
    "refused_beside_lost",
]
