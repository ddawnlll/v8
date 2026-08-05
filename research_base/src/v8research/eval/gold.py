"""Human reference process artifacts.

Reader A / Reader B / adjudication / missed-finding challenge round. Human
output is a reference process, not infallible ground truth -- disagreements
are preserved, not collapsed to a single answer.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..contracts.base import Record
from ..ids import derive_id


@dataclasses.dataclass
class HumanReading(Record):
    KIND: ClassVar[str] = "human_reading"

    reading_id: str
    reader: str
    source_id: str
    findings: list[str] = dataclasses.field(default_factory=list)
    rationale: str = ""

    @staticmethod
    def make_id(reader: str, source_id: str) -> str:
        return derive_id("HREAD", reader, source_id)


@dataclasses.dataclass
class Adjudication(Record):
    KIND: ClassVar[str] = "adjudication"

    adjudication_id: str
    source_id: str
    reading_ids: list[str]
    agreed_findings: list[str] = dataclasses.field(default_factory=list)
    disagreements: list[dict] = dataclasses.field(default_factory=list)
    missed_finding_challenge: list[str] = dataclasses.field(default_factory=list)

    @staticmethod
    def make_id(source_id: str, reading_ids: list[str]) -> str:
        return derive_id("ADJ", source_id, sorted(reading_ids))


def adjudicate(readings: list[HumanReading], source_id: str) -> Adjudication:
    """Union agreed findings, keep disagreements as data, not as a tiebreak."""
    if len(readings) < 2:
        raise ValueError("adjudication requires at least two independent readings")
    all_findings = [set(r.findings) for r in readings]
    agreed = sorted(set.intersection(*all_findings)) if all_findings else []
    disagreements = []
    for reading in readings:
        unique_to_reader = set(reading.findings) - set(agreed)
        if unique_to_reader:
            disagreements.append({"reader": reading.reader, "unique_findings": sorted(unique_to_reader)})
    return Adjudication(
        adjudication_id=Adjudication.make_id(source_id, [r.reading_id for r in readings]),
        source_id=source_id,
        reading_ids=[r.reading_id for r in readings],
        agreed_findings=agreed,
        disagreements=disagreements,
    )
