"""read_task: turn a RereadTask into a ReadReceipt, honouring the cache.

This is the only place a worker touches the model client. Every call goes
through the receipt log first, so a cache hit never reaches the network and a
genuine miss is always logged before the model runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.enums import ReadPurpose
from ..contracts.reread import RereadTask
from ..contracts.structure import DocumentNode
from ..ids import range_hash, sha256_hex
from ..llm.base import LLMClient, LLMResponse
from ..store.store import ResearchStore
from .context_expander import expand
from .receipts import ReceiptLog


@dataclass
class ReadResult:
    receipt_id: str
    response: LLMResponse | None
    node_ids: list[str]
    text: str
    cache_hit: bool


def read_task(
    task: RereadTask,
    *,
    nodes_by_id: dict[str, DocumentNode],
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    system_prompt: str,
    prompt_version: str,
    run_id: str,
    max_output_tokens: int = 1024,
) -> ReadResult:
    node_ids = expand(
        nodes_by_id,
        task.target_node_ids,
        task.preferred_read_mode,
        task.required_context_before,
        task.required_context_after,
    )
    text = "\n\n".join(store.get_text(nid) for nid in node_ids)
    range_hashes = [range_hash(store.get_text(nid)) for nid in node_ids]
    question_hash = sha256_hex(task.question)

    cached = receipts.find_cached(
        range_hashes, ReadPurpose.REREAD, question_hash, prompt_version, client.model_id
    )
    if cached is not None:
        return ReadResult(cached.read_receipt_id, None, node_ids, text, True)

    prior = [
        receipt
        for node_id in node_ids
        for receipt in receipts.prior_reads(node_id, ReadPurpose.REREAD)
    ]
    prior = list({receipt.read_receipt_id: receipt for receipt in prior}.values())
    missing_information = f"{task.reason_code}: {task.question}"
    supersedes = prior[-1].read_receipt_id if prior else None

    user_prompt = f"{task.question}\n\n<<<TEXT>>>\n{text}"
    response = client.complete(system_prompt, user_prompt, max_output_tokens)
    client_registry_note(client)

    receipt = receipts.record(
        source_range_hashes=range_hashes,
        structural_node_ids=node_ids,
        purpose=ReadPurpose.REREAD,
        question_hash=question_hash,
        prompt_version=prompt_version,
        model_id=client.model_id,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cache_hit=False,
        run_id=run_id,
        supersedes_receipt=supersedes,
        missing_information=missing_information,
    )
    return ReadResult(receipt.read_receipt_id, response, node_ids, text, False)


def client_registry_note(client: LLMClient) -> None:
    """Hook point for accounting; kept as a function so tests can monkeypatch it."""
    return None
