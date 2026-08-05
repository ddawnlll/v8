from __future__ import annotations

from pathlib import Path

import pytest

from v8research.llm.echo import EchoClient
from v8research.reading.receipts import ReceiptLog
from v8research.store.store import ResearchStore


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "ws"


@pytest.fixture
def store(workspace: Path) -> ResearchStore:
    return ResearchStore(workspace)


@pytest.fixture
def receipts(store: ResearchStore) -> ReceiptLog:
    return ReceiptLog(store)


@pytest.fixture
def client() -> EchoClient:
    return EchoClient()


@pytest.fixture
def sample_book_path() -> Path:
    path = Path(
        "/Users/hootie/src/v8/research/text/"
        "61_external_trading-and-exchanges-market-microstructure-for-practitioners-draft.txt"
    )
    if not path.exists():
        pytest.skip("sample corpus text not present in this checkout")
    return path
