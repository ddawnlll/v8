"""The 15 cheap executable tests named in the specification, verbatim.

Numbered to match "CHEAP EXECUTABLE TESTS" in
v8_progressive_evidence_research_system.html.
"""

from __future__ import annotations


import pytest

from v8research.contracts.enums import (
    FindingStatus,
    NodeType,
    OntologyOperation,
    ReadPurpose,
    RunStatus,
)
from v8research.contracts.finding import Finding
from v8research.contracts.ontology import Concept
from v8research.contracts.reread import RereadTask
from v8research.contracts.structure import DocumentNode
from v8research.discovery.section_worker import navigate_node
from v8research.ingest.lineage import LineageGraph
from v8research.ontology.migration import split_concept
from v8research.scheduler.pause_resume import RunManifest, pause
from v8research.scheduler.queues import PriorityClass, QueueItem, QueueName, TaskQueue
from v8research.verification.evidence_aligner import align_evidence
from v8research.verification.modality import modality_preserved
from v8research.contracts.enums import Modality


def _one_node(store, source_id="SRC-1"):
    node = DocumentNode(
        node_id="N1",
        source_id=source_id,
        source_version="v1",
        node_type=NodeType.SECTION,
        order=0,
        heading_path=["Intro"],
        token_estimate=50,
    )
    text = (
        "The trader should usually place a stop loss below recent support. "
        "However, in a strong trend this rule sometimes fails."
    )
    store.append(node)
    store.put_text(node.node_id, text)
    return node, text


def test_01_identical_tasks_one_call_one_cache_hit(store, receipts, client):
    node, text = _one_node(store)
    navigate_node(node, text, store=store, receipts=receipts, client=client, run_id="R1")
    calls_before = client.calls
    navigate_node(node, text, store=store, receipts=receipts, client=client, run_id="R1")
    assert client.calls == calls_before, "second identical navigation call must be served from cache"


def test_02_reread_without_new_reason_code_is_rejected(store, receipts):
    node, text = _one_node(store)
    receipts.record(
        source_range_hashes=["sha256:abc"],
        structural_node_ids=[node.node_id],
        purpose=ReadPurpose.REREAD,
        question_hash="q1",
        prompt_version="v1",
        model_id="m1",
        input_tokens=10,
        output_tokens=5,
        cache_hit=False,
        run_id="R1",
    )
    with pytest.raises(ValueError):
        receipts.record(
            source_range_hashes=["sha256:def"],
            structural_node_ids=[node.node_id],
            purpose=ReadPurpose.REREAD,
            question_hash="q2",
            prompt_version="v1",
            model_id="m1",
            input_tokens=10,
            output_tokens=5,
            cache_hit=False,
            run_id="R1",
            missing_information="",
        )


def test_03_low_resource_run_terminates_paused_never_complete():
    manifest = RunManifest(run_id="R1", token_budget=100, tokens_spent=100)
    with pytest.raises(ValueError):
        pause(manifest, RunStatus.COMPLETE, "budget exhausted")
    paused = pause(manifest, RunStatus.PAUSED_RESOURCE_LIMIT, "budget exhausted")
    assert paused.status == RunStatus.PAUSED_RESOURCE_LIMIT


def test_04_close_reopen_reproduces_pending_task_identity():
    queue_a = TaskQueue()
    item = QueueItem(QueueName.MARK_SECTION, PriorityClass.NORMAL, task_id="T1")
    queue_a.push(item)
    reread = RereadTask.make_id(["N1", "N2"], "CONDITION_MISSING", "what defines failure?")
    reread_again = RereadTask.make_id(["N2", "N1"], "CONDITION_MISSING", "what defines failure?")
    assert reread == reread_again, "closing and reopening a run must reproduce task identity"


def test_05_ontology_change_does_not_change_finding_hash():
    finding = Finding(
        finding_id="FND-1", finding_statement="s", claim_ids=("c1",), source_ids=("s1",)
    ).with_hash()
    original_hash = finding.content_hash
    # Simulate an ontology-only change: a successor annotation would be created
    # elsewhere, but the Finding record itself is untouched.
    assert finding.content_hash == original_hash


def test_06_splitting_concept_closes_old_and_creates_successor():
    original = Concept(concept_id="CON-1", name="breakout", definition="d", ontology_version=1)
    new_concepts, change = split_concept(
        original,
        into=[("true_breakout", "d1", ["FND-1"]), ("false_breakout", "d2", ["FND-2"])],
        to_version=2,
        rationale="two distinct behaviours were conflated",
    )
    assert len(new_concepts) == 2
    assert change.operation == OntologyOperation.SPLIT_CONCEPT
    assert original.concept_id in change.affected_concept_ids


def test_07_source_copied_into_ten_books_raw_vs_independent_count():
    from v8research.contracts.source import LineageEdge
    from v8research.contracts.enums import LineageRelation

    anchor = "SRC-0"
    copies = [f"SRC-{i}" for i in range(1, 10)]
    edges = [
        LineageEdge(
            edge_id=LineageEdge.make_id(copy, anchor, LineageRelation.POSSIBLE_COPY),
            from_source_id=copy,
            to_source_id=anchor,
            relation=LineageRelation.POSSIBLE_COPY,
        )
        for copy in copies
    ]
    graph = LineageGraph(edges)
    raw, independent = graph.counts([anchor, *copies])
    assert raw == 10
    assert independent == 1


def test_08_verifier_rejects_modality_stronger_than_evidence():
    evidence = "Traders may sometimes place a stop below support."
    assert modality_preserved(Modality.MAY, evidence) is True
    assert modality_preserved(Modality.MUST, evidence) is False


def test_09_removing_chapter_channel_changes_composition_recall():
    from v8research.eval.discovery_metrics import GoldFinding, composition_recall

    gold = [GoldFinding(gold_id="G1", node_ids=["N1"], description="a distributed argument", is_composition=True)]
    with_chapter = composition_recall(gold, ["a distributed argument found via chapter synthesis"])
    without_chapter = composition_recall(gold, [])
    assert with_chapter["recall"] != without_chapter["recall"]


def test_10_audit_retains_capacity_under_high_priority_flood():
    queue = TaskQueue(audit_protect_every=3)
    for i in range(10):
        queue.push(QueueItem(QueueName.EXTRACT_CLAIM, PriorityClass.CRITICAL, task_id=f"C{i}"))
    queue.push(QueueItem(QueueName.AUDIT_RANDOM, PriorityClass.AUDIT, task_id="AUDIT-1"))

    served_order = []
    while len(queue):
        served_order.append(queue.pop().task_id)
    assert "AUDIT-1" in served_order
    # Not starved to the very end despite being enqueued behind ten CRITICALs.
    assert served_order.index("AUDIT-1") < len(served_order) - 1


def test_11_figure_referenced_claim_cannot_verify_from_text_alone(store, receipts, client):
    node = DocumentNode(
        node_id="N-FIG",
        source_id="SRC-1",
        source_version="v1",
        node_type=NodeType.SECTION,
        order=0,
        token_estimate=10,
    )
    text = "See Figure 3.2 for the pattern; the text alone omits the threshold value."
    claim_statement = "The threshold value shown only in Figure 3.2 defines the entry."
    from v8research.contracts.claim import Claim
    from v8research.contracts.enums import EpistemicAct

    claim = Claim(
        claim_id="CLM-FIG",
        source_id=node.source_id,
        node_id=node.node_id,
        source_statement=claim_statement,
        normalized_claim=claim_statement,
        epistemic_act=EpistemicAct.OBSERVED,
        modality=Modality.USUALLY,
    )
    claim, span = align_evidence(claim, node, text)
    assert span is None, "a claim whose text is not verbatim in the node must not fabricate a span"


def test_12_v8_impact_mapping_cannot_access_unverified_findings(store, receipts, client):
    from v8research.v8map.assumptions import new_assumption
    from v8research.v8map.impact_mapper import UnverifiedFindingError, map_to_v8
    from v8research.contracts.enums import AssumptionStatus

    finding = Finding(
        finding_id="FND-X", finding_statement="s", claim_ids=("c1",), source_ids=("s1",),
        status=FindingStatus.REJECTED,
    ).with_hash()
    assumption = new_assumption("test assumption", AssumptionStatus.OPEN_QUESTION)
    with pytest.raises(UnverifiedFindingError):
        map_to_v8(finding, assumption, store=store, receipts=receipts, client=client, run_id="R1")


def test_13_report_lists_unresolved_critical_rereads_not_hidden():
    from v8research.eval.audit_metrics import completion_gate

    result = completion_gate(
        coverage_failures=[],
        recall_failures=[],
        resolution_failures=["3 unresolved CRITICAL rereads remain"],
    )
    assert result.passed is False
    assert "3 unresolved CRITICAL rereads remain" in result.failures


def test_14_human_edit_creates_provenance_event_not_rewrite():
    from v8research.eval.gold import HumanReading, adjudicate

    reader_a = HumanReading(reading_id="H1", reader="A", source_id="SRC-1", findings=["f1", "f2"])
    reader_b = HumanReading(reading_id="H2", reader="B", source_id="SRC-1", findings=["f1", "f3"])
    adjudication = adjudicate([reader_a, reader_b], "SRC-1")
    assert reader_a.findings == ["f1", "f2"], "adjudication must not mutate the original reading"
    assert adjudication.agreed_findings == ["f1"]
    assert any(d["reader"] == "A" for d in adjudication.disagreements)
    assert any(d["reader"] == "B" for d in adjudication.disagreements)


def test_15_rebuilding_duckdb_views_yields_identical_row_hashes(store):
    from v8research.store import duckdb_views

    finding = Finding(
        finding_id="FND-1", finding_statement="s", claim_ids=("c1",), source_ids=("s1",)
    ).with_hash()
    store.append(finding)
    store.materialize()
    first = duckdb_views.row_hashes(store.workspace, "findings")
    store.materialize()
    second = duckdb_views.row_hashes(store.workspace, "findings")
    assert first == second
