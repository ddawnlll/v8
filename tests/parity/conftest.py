"""Session-scoped fixtures for the V8.2 parity harness.

Builds the compute-plane binary once per session and pins the V8.0 oracle tree
hash, so every parity report is anchored to an immutable oracle
(PARITY_AND_IDENTITY_SPEC §7.5 oracle-freeze check).
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
V8_CORE = REPO_ROOT / "v8-core"
BINARY = V8_CORE / "target" / "release" / "v8-core"


@pytest.fixture(scope="session")
def v8_core_binary() -> Path:
    """The release binary, built once per session."""
    if not BINARY.is_file():
        subprocess.run(["cargo", "build", "--release"], cwd=V8_CORE, check=True,
                       capture_output=True, text=True)
    assert BINARY.is_file(), f"v8-core binary missing at {BINARY}"
    return BINARY


@pytest.fixture(scope="session")
def oracle_tree_hash() -> str:
    """`git rev-parse HEAD:src/v8` — the frozen oracle's tree hash. Every
    parity result records it; if src/v8 moves, every recorded result is
    invalidated (PARITY_AND_IDENTITY_SPEC §7.5)."""
    out = subprocess.run(["git", "rev-parse", "HEAD:src/v8"], cwd=REPO_ROOT,
                         check=True, capture_output=True, text=True)
    return out.stdout.strip()


def source_hash_of(path: Path) -> str:
    """sha1 hex of a file's bytes (used to pin the reader itself)."""
    return hashlib.sha1(path.read_bytes()).hexdigest()
