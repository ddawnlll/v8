"""Content-addressed caches for repeatable research evaluations.

The canonical Lab remains the authority and still performs a full replay on a
cache miss.  This module only handles a proven-identical *complete* run: the
cache key binds the tape, manifest, expert set, decision-path code, tooling,
and risk-admission policy.  A hit restores the immutable ledgers byte-for-byte
and never fabricates a report from a partial run.
"""
from __future__ import annotations

import json
import inspect
import os
import pickle
import shutil
from dataclasses import fields
from pathlib import Path

from .schema import LabReport, sha1_hex


CACHE_VERSION = "lab-complete-v1"
STATE_CACHE_VERSION = "marketstate-materialized-v1"
LEDGER_FILES = (
    "candidates.jsonl",
    "evaluations.jsonl",
    "outcomes.jsonl",
    "states.jsonl",
    "manifest.json",
    "report.json",
)


def _expert_identity(experts) -> tuple[tuple, ...]:
    """Return only frozen configuration fields; source bytes bind separately."""
    return tuple(sorted((
        type(ex).__module__,
        type(ex).__qualname__,
        getattr(ex, "expert_id", ""),
        getattr(ex, "version", ""),
        getattr(ex, "variant_id", ""),
        tuple(getattr(ex, "requires", ()) or ()),
        tuple(getattr(ex, "intervals", ()) or ()),
        repr(getattr(ex, "depth", 32)),
    ) for ex in experts))


def cache_key(*, tape_hash: str, manifest_dict: dict, experts,
              code_hash: str, tooling_hash: str,
              risk_config_hash: str) -> str:
    """Build a content key for a complete Lab result."""
    return sha1_hex({
        "cache_version": CACHE_VERSION,
        "tape_hash": tape_hash,
        "manifest": manifest_dict,
        "experts": _expert_identity(experts),
        "code_hash": code_hash,
        "tooling_hash": tooling_hash,
        "risk_config_hash": risk_config_hash,
    })


def state_cache_key(*, tape_hash: str, universe: tuple[str, ...],
                    base_interval: str, intervals: tuple[str, ...],
                    depths: dict[str, int], state_code_hash: str) -> str:
    """Key the state materialization independently of Expert source bytes."""
    return sha1_hex({
        "cache_version": STATE_CACHE_VERSION,
        "tape_hash": tape_hash,
        "universe": universe,
        "base_interval": base_interval,
        "intervals": intervals,
        "depths": tuple(sorted(depths.items())),
        "state_code_hash": state_code_hash,
    })


def expert_eval_cache_key(*, state_key: str, expert,
                          state_code_hash: str) -> str:
    """Key one Expert's evaluation stream independently of other Experts."""
    source_file = inspect.getsourcefile(type(expert))
    source_hash = sha1_hex(Path(source_file).read_bytes().hex()) \
        if source_file else "unknown-source"
    return sha1_hex({
        "cache_version": "expert-evaluations-v1",
        "state_key": state_key,
        "state_code_hash": state_code_hash,
        "source_hash": source_hash,
        "identity": _expert_identity([expert]),
    })


class CompleteRunCache:
    """Store and restore complete Lab artifacts under a content key."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _dir(self, key: str) -> Path:
        return self.root / key

    def has(self, key: str) -> bool:
        path = self._dir(key)
        return path.is_dir() and all((path / name).is_file()
                                     for name in LEDGER_FILES)

    def save(self, key: str, store_dir: Path) -> None:
        destination = self._dir(key)
        if self.has(key):
            return
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f".{key}.tmp"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(parents=True)
        try:
            for name in LEDGER_FILES:
                source = store_dir / name
                if not source.is_file():
                    raise ValueError(f"cannot cache incomplete Lab run: {source}")
                shutil.copyfile(source, temporary / name)
            temporary.replace(destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def restore(self, key: str, store_dir: Path) -> LabReport:
        source_dir = self._dir(key)
        if not self.has(key):
            raise KeyError(key)
        for name in LEDGER_FILES:
            if name == "manifest.json":
                # The caller already owns the ingested tape and run directory;
                # manifest/report are still restored as self-description.
                pass
            target = store_dir / name
            target.unlink(missing_ok=True)
            try:
                # Same-filesystem hardlinks make restore metadata-only.  The
                # append-only log detaches on a later mutation, so the cache
                # inode remains immutable even if a caller reuses the object.
                os.link(source_dir / name, target)
            except OSError:
                # Cache and store may live on different filesystems.
                shutil.copyfile(source_dir / name, target)
        payload = json.loads((store_dir / "report.json").read_text())
        allowed = {f.name for f in fields(LabReport)}
        return LabReport(**{k: v for k, v in payload.items() if k in allowed})


class StateMaterializationCache:
    """Persist canonical MarketState objects without JSON parse overhead."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "states"

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.pkl"

    def load(self, key: str):
        path = self._path(key)
        if not path.is_file():
            return None
        with path.open("rb") as fh:
            return pickle.load(fh)

    def save(self, key: str, states: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        if path.is_file():
            return
        temporary = self.root / f".{key}.tmp"
        with temporary.open("wb") as fh:
            pickle.dump(states, fh, protocol=pickle.HIGHEST_PROTOCOL)
        temporary.replace(path)


class ExpertEvaluationCache:
    """Persist one complete ExpertEvaluation stream per Expert."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "evaluations"

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.pkl"

    def load(self, key: str):
        path = self._path(key)
        if not path.is_file():
            return None
        with path.open("rb") as fh:
            return pickle.load(fh)

    def save(self, key: str, evaluations: list) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        if path.is_file():
            return
        temporary = self.root / f".{key}.tmp"
        with temporary.open("wb") as fh:
            pickle.dump(evaluations, fh, protocol=pickle.HIGHEST_PROTOCOL)
        temporary.replace(path)
