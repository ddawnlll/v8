"""v8research: the orchestrator entry point.

The orchestrator schedules independent work, inspects coverage/cost reports,
creates reread tasks, and can pause and resume a run. It may not invent
evidence, mark exhaustion as completion, spawn unlimited agents, rewrite
findings, or bypass audit quotas -- this module is deliberately thin, calling
into `ingest`/`discovery`/`verification`/`v8map`/`scheduler` rather than
reimplementing any of their logic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts.enums import ModelTier, NodeType
from .contracts.source import Source
from .discovery.chapter_worker import chapter_findings_as_marks, synthesize_chapter
from .discovery.contradiction_scan import mark_contradictions, select_contradiction_candidates
from .discovery.cross_reference import cross_reference_tasks
from .discovery.outlier_scan import select_outlier_candidates
from .discovery.random_audit import sample_audit
from .discovery.rarity_scan import select_rarity_candidates
from .discovery.union import union_marks
from .index.embeddings import EmbeddingIndex
from .index.lexical_rarity import RarityIndex
from .ingest.lineage import LineageGraph, detect_edition_families
from .llm.registry import ModelRegistry
from .scheduler.accounting import accounting_report
from .scheduler.pause_resume import load_or_create, save, try_complete
from .scheduler.runner import map_document, mark_node
from .store.store import ResearchStore
from .verification.claim_extractor import extract_claims
from .verification.entailment import verify_claim
from .verification.evidence_aligner import align_evidence
from .verification.source_independence import materialize_finding
from .contracts.finding import Finding
from .contracts.mark import Mark
from .contracts.structure import DocumentNode
from .reading.receipts import ReceiptLog
from .reading.executor import execute_rereads
from .contracts.reread import RereadTask
from .contracts.enums import TaskStatus


def registry_for(args: argparse.Namespace) -> ModelRegistry:
    """Build the explicitly selected offline or paid-provider registry."""
    if not getattr(args, "live", False):
        return ModelRegistry.offline()
    from .llm.anthropic_client import AnthropicClient

    registry = ModelRegistry()
    registry.register(
        ModelTier.SMALL,
        AnthropicClient(model_id=args.small_model, tier=ModelTier.SMALL),
    )
    registry.register(
        ModelTier.STRONG,
        AnthropicClient(model_id=args.strong_model, tier=ModelTier.STRONG),
    )
    return registry


def cmd_ingest(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    receipts = ReceiptLog(store)
    registry = registry_for(args)
    client = registry.get(ModelTier.SMALL)

    path = Path(args.file)
    title = args.title or path.stem
    source = Source(source_id=Source.make_id(title, args.edition), source_version="", title=title, edition=args.edition)
    result = map_document(
        source, str(path), store=store, receipts=receipts, client=client, run_id=args.run_id, navigate=not args.skip_navigation
    )
    print(json.dumps({
        "source_id": result.source.source_id,
        "nodes": len(result.nodes),
        "navigations": len(result.navigations),
    }, indent=2))
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    receipts = ReceiptLog(store)
    registry = registry_for(args)
    client = registry.get(ModelTier.SMALL)

    nodes = [n for n in store.read(DocumentNode) if n.source_id == args.source_id]
    if not nodes:
        print(f"no nodes found for source {args.source_id}", file=sys.stderr)
        return 1
    sections = [n for n in nodes if n.node_type == NodeType.SECTION]
    texts = {n.node_id: store.get_text(n.node_id) for n in sections}

    all_marks: list[Mark] = []

    # Channel A
    for node in sections:
        all_marks.extend(mark_node(node, store=store, receipts=receipts, client=client, run_id=args.run_id))

    # Channel B
    for chapter in [n for n in nodes if n.node_type == NodeType.CHAPTER]:
        children = [c for c in chapter.ordered_child_ids if c in texts]
        chapter_text = " ".join(texts[c] for c in children)
        if not chapter_text.strip():
            continue
        synthesis = synthesize_chapter(chapter, chapter_text, store=store, receipts=receipts, client=client, run_id=args.run_id)
        all_marks.extend(chapter_findings_as_marks(synthesis, args.source_id))

    # Channels C, D: local detection surfaces candidates (audit trail only in this CLI pass).
    rarity = RarityIndex()
    embeddings = EmbeddingIndex()
    for node in sections:
        rarity.add(node.node_id, texts[node.node_id])
        embeddings.add(node.node_id, texts[node.node_id])
    rarity_candidates = select_rarity_candidates(rarity, [n.node_id for n in sections])
    outlier_candidates = select_outlier_candidates(embeddings)

    # Channel E
    xref_tasks = cross_reference_tasks(nodes, created_by_run=args.run_id)
    for task in xref_tasks:
        store.append(task)

    # Channel F
    audit_samples = sample_audit(sections, run_id=args.run_id)

    # Channel G
    contradiction_nodes = select_contradiction_candidates(texts)
    for node_id in contradiction_nodes:
        node = next(n for n in sections if n.node_id == node_id)
        all_marks.extend(
            mark_contradictions(node, texts[node_id], store=store, receipts=receipts, client=client, run_id=args.run_id)
        )

    merged, report = union_marks(all_marks)
    for mark in merged:
        store.append(mark)

    print(json.dumps({
        "marks_before_union": report.input_count,
        "marks_after_union": report.output_count,
        "exact_merges": report.exact_merges,
        "near_merges": report.near_merges,
        "rarity_candidates": len(rarity_candidates),
        "outlier_candidates": len(outlier_candidates),
        "cross_reference_tasks": len(xref_tasks),
        "random_audit_samples": len(audit_samples),
        "contradiction_candidate_nodes": len(contradiction_nodes),
    }, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    receipts = ReceiptLog(store)
    registry = registry_for(args)
    extractor = registry.get(ModelTier.SMALL)
    verifier = registry.verifier_for(extractor.model_id)

    nodes = {n.node_id: n for n in store.read(DocumentNode) if n.source_id == args.source_id}
    sources = store.read(Source)
    lineage_edges = detect_edition_families(sources)
    graph = LineageGraph(lineage_edges)

    findings: list[Finding] = []
    for node_id, node in nodes.items():
        if node.node_type != NodeType.SECTION:
            continue
        text = store.get_text(node_id)
        if not text.strip():
            continue
        claims = extract_claims(node, text, store=store, receipts=receipts, client=extractor, run_id=args.run_id)
        for claim in claims:
            claim, span = align_evidence(claim, node, text)
            store.append(claim)
            verification = verify_claim(
                claim, span, node, store=store, receipts=receipts, client=verifier, run_id=args.run_id
            )
            store.append(verification)
            finding = materialize_finding(
                claim.normalized_claim, [claim], [verification], lineage_graph=graph
            )
            if finding is not None:
                store.append(finding)
                findings.append(finding)

    print(json.dumps({
        "claims_extracted": store.count("claim"),
        "verifications": store.count("verification"),
        "findings_materialized": len(findings),
        "verified": sum(1 for f in findings if f.status == "VERIFIED"),
    }, indent=2))
    return 0


def cmd_reread(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    receipts = ReceiptLog(store)
    registry = registry_for(args)
    client = registry.get(ModelTier.SMALL)
    nodes = {
        node.node_id: node
        for node in store.read(DocumentNode)
        if node.source_id == args.source_id
    }
    tasks = [task for task in store.read(RereadTask) if task.created_by_run == args.run_id]
    if not tasks:
        tasks = [task for task in store.read(RereadTask) if any(nid in nodes for nid in task.target_node_ids)]
    report = execute_rereads(
        tasks,
        nodes_by_id=nodes,
        store=store,
        receipts=receipts,
        client=client,
        run_id=args.run_id,
    )
    print(json.dumps(report.__dict__, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    receipts = ReceiptLog(store)
    nodes = store.read(DocumentNode)
    node_tokens = {n.node_id: n.token_estimate for n in nodes}
    report = accounting_report(
        receipts,
        node_tokens,
        mark_count=store.count("mark"),
        verified_finding_count=sum(1 for f in store.read(Finding) if f.status == "VERIFIED"),
    )
    print(json.dumps(report, indent=2))
    return 0


def cmd_materialize(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    written = store.materialize()
    print(json.dumps(written, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = ResearchStore(args.workspace)
    manifest = load_or_create(store, args.run_id)
    tasks = store.read(RereadTask)
    open_tasks = [
        task for task in tasks if task.status in {TaskStatus.OPEN, TaskStatus.IN_PROGRESS}
    ]
    manifest.pending_task_ids = [task.reread_id for task in open_tasks]
    manifest.unresolved_critical_reread_ids = [
        task.reread_id for task in tasks if task.is_critical and task.status not in {
            TaskStatus.RESOLVED,
            TaskStatus.PARTIALLY_RESOLVED,
            TaskStatus.UNRESOLVABLE_IN_SOURCE,
            TaskStatus.REQUIRES_EXTERNAL_SOURCE,
            TaskStatus.DUPLICATE_QUESTION,
            TaskStatus.ABANDONED_LOW_VALUE,
            TaskStatus.FAILED,
        }
    ]
    manifest = try_complete(manifest)
    save(store, manifest)
    print(json.dumps({"run_id": manifest.run_id, "status": manifest.status}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="v8research")
    parser.add_argument("--workspace", default="./v8research_workspace")
    parser.add_argument("--run-id", dest="run_id", default="RUN-LOCAL")
    parser.add_argument("--live", action="store_true", help="use Anthropic API; incurs provider cost")
    parser.add_argument("--small-model", default="claude-sonnet-4-20250514")
    parser.add_argument("--strong-model", default="claude-opus-4-20250514")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="parse a source and build its navigation memory")
    p_ingest.add_argument("file")
    p_ingest.add_argument("--title")
    p_ingest.add_argument("--edition")
    p_ingest.add_argument("--skip-navigation", action="store_true")
    p_ingest.set_defaults(func=cmd_ingest)

    p_discover = sub.add_parser("discover", help="run all seven discovery channels for one source")
    p_discover.add_argument("source_id")
    p_discover.set_defaults(func=cmd_discover)

    p_verify = sub.add_parser("verify", help="extract, align, and verify claims for one source")
    p_verify.add_argument("source_id")
    p_verify.set_defaults(func=cmd_verify)

    p_reread = sub.add_parser("reread", help="execute bounded open reread tasks for one source")
    p_reread.add_argument("source_id")
    p_reread.set_defaults(func=cmd_reread)

    p_report = sub.add_parser("report", help="print the cost/coverage accounting report")
    p_report.set_defaults(func=cmd_report)

    p_materialize = sub.add_parser("materialize", help="rebuild Parquet tables from the JSONL authority")
    p_materialize.set_defaults(func=cmd_materialize)

    p_status = sub.add_parser("status", help="check/refresh a run's terminal status")
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
