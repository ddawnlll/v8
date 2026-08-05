"""Navigation memory: a cheap map of where information may live.

The gist is deliberately short. Navigation memory that grows into a summary
becomes a lossy substitute for evidence, which is exactly the failure the
MAP stage exists to avoid.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..ids import derive_id
from .base import Record

MAX_GIST_CHARS = 240


@dataclasses.dataclass
class NavigationMemory(Record):
    KIND: ClassVar[str] = "navigation_memory"

    navigation_id: str
    node_id: str
    source_id: str
    gist: str
    salient_terms_verbatim: list[str] = dataclasses.field(default_factory=list)
    named_entities: list[str] = dataclasses.field(default_factory=list)
    processes_observed: list[str] = dataclasses.field(default_factory=list)
    examples_present: bool = False
    exceptions_present: bool = False
    tables_figures_present: bool = False
    internal_references: list[str] = dataclasses.field(default_factory=list)
    possible_dependencies: list[str] = dataclasses.field(default_factory=list)
    navigation_uncertainties: list[str] = dataclasses.field(default_factory=list)
    read_receipt_id: str | None = None

    def __post_init__(self) -> None:
        if len(self.gist) > MAX_GIST_CHARS:
            self.gist = self.gist[:MAX_GIST_CHARS].rstrip()

    @staticmethod
    def make_id(node_id: str) -> str:
        return derive_id("NAV", node_id)
