"""Data contracts for the V8 research base."""

from .base import Record
from .claim import Claim, Verification
from .enums import (
    AssumptionStatus,
    DiscoveryChannel,
    EpistemicAct,
    EvidenceLabel,
    FindingStatus,
    ImpactRelation,
    LineageRelation,
    MODALITY_RANK,
    MarkStatus,
    ModelTier,
    Modality,
    NodeType,
    OntologyOperation,
    PriorityClass,
    ProposalKind,
    QueueName,
    ReadMode,
    ReadPurpose,
    RereadTrigger,
    RunStatus,
    TaskStatus,
)
from .finding import Finding
from .mark import Mark
from .navigation import NavigationMemory
from .ontology import Concept, ConceptProposal, OntologyAnnotation, SchemaChange
from .receipt import ReadReceipt
from .reread import RereadTask
from .source import NON_INDEPENDENT_RELATIONS, LineageEdge, Source
from .structure import DocumentNode, EvidenceSpan
from .v8_impact import ResearchProposal, V8Assumption, V8Impact

__all__ = [
    "AssumptionStatus",
    "Claim",
    "Concept",
    "ConceptProposal",
    "DiscoveryChannel",
    "DocumentNode",
    "EpistemicAct",
    "EvidenceLabel",
    "EvidenceSpan",
    "Finding",
    "FindingStatus",
    "ImpactRelation",
    "LineageEdge",
    "LineageRelation",
    "MODALITY_RANK",
    "Mark",
    "MarkStatus",
    "Modality",
    "ModelTier",
    "NON_INDEPENDENT_RELATIONS",
    "NavigationMemory",
    "NodeType",
    "OntologyAnnotation",
    "OntologyOperation",
    "PriorityClass",
    "ProposalKind",
    "QueueName",
    "ReadMode",
    "ReadPurpose",
    "ReadReceipt",
    "Record",
    "RereadTask",
    "RereadTrigger",
    "ResearchProposal",
    "RunStatus",
    "SchemaChange",
    "Source",
    "TaskStatus",
    "V8Assumption",
    "V8Impact",
    "Verification",
]
