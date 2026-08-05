from __future__ import annotations

import dataclasses

from v8research.contracts.enums import DiscoveryChannel, NodeType
from v8research.contracts.finding import Finding
from v8research.contracts.mark import Mark
from v8research.contracts.receipt import ReadReceipt
from v8research.contracts.reread import RereadTask
from v8research.contracts.structure import DocumentNode
from v8research.ids import derive_id


def test_derive_id_is_order_independent_and_deterministic():
    a = derive_id("X", ["b", "a"], 1)
    b = derive_id("X", ["b", "a"], 1)
    c = derive_id("X", ["a", "b"], 1)
    assert a == b
    assert a != c  # only sorted-at-call-site inputs are order independent


def test_reread_task_id_ignores_target_order():
    q = "what defines this?"
    a = RereadTask.make_id(["N2", "N1"], "CONDITION_MISSING", q)
    b = RereadTask.make_id(["N1", "N2"], "CONDITION_MISSING", q)
    assert a == b


def test_finding_is_frozen_and_successor_gets_new_hash():
    finding = Finding(
        finding_id="FND-1", finding_statement="s", claim_ids=("c1",), source_ids=("s1",)
    ).with_hash()
    try:
        finding.finding_statement = "changed"
        assert False, "Finding must be immutable"
    except dataclasses.FrozenInstanceError:
        pass
    successor = finding.superseded_by("revised statement")
    assert successor.finding_version == 2
    assert successor.supersedes_finding_id == finding.finding_id
    assert successor.content_hash != finding.content_hash


def test_mark_merge_channels_is_additive_not_destructive():
    left = Mark(
        mark_id="M1", node_id="N1", source_id="S1", span_refs=[], verbatim_anchor="a",
        why_marked="w", open_codes=["x"], discovery_channels=[DiscoveryChannel.SECTION_LLM],
    )
    right = Mark(
        mark_id="M1", node_id="N1", source_id="S1", span_refs=[], verbatim_anchor="a",
        why_marked="w", open_codes=["y"], discovery_channels=[DiscoveryChannel.RANDOM_AUDIT],
    )
    left.merge_channels(right)
    assert set(left.open_codes) == {"x", "y"}
    assert set(left.discovery_channels) == {DiscoveryChannel.SECTION_LLM, DiscoveryChannel.RANDOM_AUDIT}


def test_store_append_only_last_write_wins_on_collapse(store):
    node = DocumentNode(
        node_id="N1", source_id="S1", source_version="v1", node_type=NodeType.SECTION, order=0,
        heading_path=["A"],
    )
    store.append(node)
    revised = DocumentNode(
        node_id="N1", source_id="S1", source_version="v1", node_type=NodeType.SECTION, order=0,
        heading_path=["A", "Revised"],
    )
    store.append(revised)
    assert store.count("document_node") == 2
    collapsed = store.read(DocumentNode)
    assert len(collapsed) == 1
    assert collapsed[0].heading_path == ["A", "Revised"]


def test_receipt_cache_key_depends_on_all_five_components():
    base = dict(
        source_range_hashes=["h1"], purpose="MARKING", question_hash="q1",
        prompt_version="p1", model_id="m1",
    )
    same = ReadReceipt.make_id(**base)
    assert ReadReceipt.make_id(**base) == same
    for field, new_value in [
        ("purpose", "NAVIGATION"), ("question_hash", "q2"),
        ("prompt_version", "p2"), ("model_id", "m2"),
    ]:
        changed = dict(base)
        changed[field] = new_value
        assert ReadReceipt.make_id(**changed) != same, f"{field} must affect receipt identity"
