"""Run manifests: the pause/resume contract.

A resource limit may produce PAUSED_RESOURCE_LIMIT; it may never produce
COMPLETE (constitution rule 16). This module is where that guarantee is
enforced in code, not left to caller discipline.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..contracts.base import Record
from ..contracts.enums import RESOURCE_STATUSES, RunStatus
from ..ids import derive_id
from ..store.store import ResearchStore


@dataclasses.dataclass
class RunManifest(Record):
    KIND: ClassVar[str] = "run_manifest"

    run_id: str
    status: RunStatus = RunStatus.RUNNING
    pending_task_ids: list[str] = dataclasses.field(default_factory=list)
    completed_task_ids: list[str] = dataclasses.field(default_factory=list)
    unresolved_critical_reread_ids: list[str] = dataclasses.field(default_factory=list)
    tokens_spent: int = 0
    token_budget: int = 0
    notes: str = ""
    started_at: str = ""
    updated_at: str = ""

    @staticmethod
    def make_id(run_label: str, started_at: str) -> str:
        return derive_id("RUN", run_label, started_at)


class BudgetExceeded(Exception):
    pass


def check_budget(manifest: RunManifest) -> None:
    if manifest.token_budget and manifest.tokens_spent >= manifest.token_budget:
        raise BudgetExceeded(
            f"run {manifest.run_id} spent {manifest.tokens_spent}/{manifest.token_budget} tokens"
        )


def pause(manifest: RunManifest, status: RunStatus, note: str, updated_at: str = "") -> RunManifest:
    """Resource conditions may only ever route here, never to COMPLETE."""
    if status == RunStatus.COMPLETE:
        raise ValueError("pause() cannot be called with RunStatus.COMPLETE")
    manifest.status = status
    manifest.notes = note
    manifest.updated_at = updated_at
    return manifest


def try_complete(manifest: RunManifest, updated_at: str = "") -> RunManifest:
    """The only path to COMPLETE, and it refuses if anything critical is open.

    This is the code-level guarantee behind "epistemic criteria determine
    whether the research is complete": completion requires an empty pending
    queue and an empty unresolved-critical list, checked here rather than
    trusted from a caller's summary.
    """
    if manifest.pending_task_ids:
        return pause(
            manifest,
            RunStatus.PAUSED_RESOURCE_LIMIT,
            f"{len(manifest.pending_task_ids)} tasks still pending",
            updated_at,
        )
    if manifest.unresolved_critical_reread_ids:
        return pause(
            manifest,
            RunStatus.PAUSED_HUMAN_REVIEW,
            f"{len(manifest.unresolved_critical_reread_ids)} unresolved critical rereads",
            updated_at,
        )
    manifest.status = RunStatus.COMPLETE
    manifest.updated_at = updated_at
    return manifest


def load_or_create(store: ResearchStore, run_id: str, token_budget: int = 0) -> RunManifest:
    for manifest in store.read(RunManifest):
        if manifest.run_id == run_id:
            return manifest
    return RunManifest(run_id=run_id, token_budget=token_budget)


def save(store: ResearchStore, manifest: RunManifest) -> None:
    store.append(manifest)


def is_resource_pause(manifest: RunManifest) -> bool:
    return manifest.status in RESOURCE_STATUSES
