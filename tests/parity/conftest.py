"""Session-scoped fixtures for the V8.2 parity harness.

Builds the compute-plane binary once per session and pins the V8.0 oracle tree
hash, so every parity report is anchored to an immutable oracle
(PARITY_AND_IDENTITY_SPEC §7.5 oracle-freeze check).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
V8_CORE = REPO_ROOT / "v8-core"


def _binary_name(os_name: str) -> str:
    return "v8-core.exe" if os_name == "nt" else "v8-core"


BINARY = V8_CORE / "target" / "release" / _binary_name(os.name)


def pytest_addoption(parser):
    """Filter the S4 expert-parity tests to one expert (per-agent runs)."""
    parser.addoption("--expert", action="store", default=None,
                     help="only exercise this expert_id in test_parity_s4")


@pytest.fixture(scope="session")
def v8_core_binary() -> Path:
    """The release binary, built once per session (rebuilt when any source
    file is newer than it — a stale binary would silently test the previous
    registry state)."""
    newest_src = max(
        (p.stat().st_mtime for p in (V8_CORE / "src").rglob("*.rs")),
        default=0.0,
    )
    if not BINARY.is_file() or BINARY.stat().st_mtime < newest_src:
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
