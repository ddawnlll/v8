"""Channel G: contradiction and qualification search.

Not limited to explicit words like "however" -- a lexical prefilter widens the
candidate set (cheap, local), and the actual marking still goes through an LLM
pass using the specialised CONTRADICTION_SYSTEM prompt so implicit reversals
are not missed.
"""

from __future__ import annotations

import re

from ..contracts.enums import DiscoveryChannel
from ..contracts.mark import Mark
from ..contracts.structure import DocumentNode
from ..llm.base import LLMClient
from ..reading.receipts import ReceiptLog
from ..store.store import ResearchStore
from .prompts import CONTRADICTION_SYSTEM, PROMPT_VERSIONS
from .section_worker import mark_section

_SIGNAL = re.compile(
    r"\b(however|but|although|except|unless|caveat|caution|rarely|"
    r"in practice|contrary to|not always|fails? to|breaks? down|"
    r"no longer|used to|counterexample|overstated|oversimplif)\w*\b",
    re.I,
)


def has_contradiction_signal(text: str) -> bool:
    return bool(_SIGNAL.search(text))


def select_contradiction_candidates(
    node_texts: dict[str, str]
) -> list[str]:
    return [nid for nid, text in node_texts.items() if has_contradiction_signal(text)]


def mark_contradictions(
    node: DocumentNode,
    text: str,
    *,
    store: ResearchStore,
    receipts: ReceiptLog,
    client: LLMClient,
    run_id: str,
) -> list[Mark]:
    return mark_section(
        node,
        text,
        store=store,
        receipts=receipts,
        client=client,
        run_id=run_id,
        channel=DiscoveryChannel.CONTRADICTION,
        system_prompt=CONTRADICTION_SYSTEM,
        prompt_version=PROMPT_VERSIONS["contradiction"],
    )
