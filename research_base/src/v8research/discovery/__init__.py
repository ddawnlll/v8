"""Independent discovery channels A-G."""

from .chapter_worker import ChapterSynthesis, chapter_findings_as_marks, recall_gap, synthesize_chapter
from .contradiction_scan import has_contradiction_signal, mark_contradictions, select_contradiction_candidates
from .cross_reference import cross_reference_tasks
from .outlier_scan import select_dense_representatives, select_outlier_candidates
from .random_audit import AuditSample, miss_rate, sample_audit, stratify
from .rarity_scan import RarityCandidate, select_rarity_candidates, terminology_drift_report
from .section_worker import mark_section, navigate_node
from .union import UnionReport, union_marks

__all__ = [
    "AuditSample",
    "ChapterSynthesis",
    "RarityCandidate",
    "UnionReport",
    "chapter_findings_as_marks",
    "cross_reference_tasks",
    "has_contradiction_signal",
    "mark_contradictions",
    "mark_section",
    "miss_rate",
    "navigate_node",
    "recall_gap",
    "sample_audit",
    "select_contradiction_candidates",
    "select_dense_representatives",
    "select_outlier_candidates",
    "select_rarity_candidates",
    "stratify",
    "synthesize_chapter",
    "terminology_drift_report",
    "union_marks",
]
