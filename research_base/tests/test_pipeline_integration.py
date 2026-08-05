from __future__ import annotations

import json
from pathlib import Path

from v8research.cli import main


def _output(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_cli_runs_the_complete_offline_pipeline(tmp_path: Path, capsys) -> None:
    book = tmp_path / "book.txt"
    paragraph = (
        "A market mechanism converts orders into executed trades. "
        "The mechanism depends on liquidity, queue priority, and displayed depth. "
        "This paragraph is deliberately repeated so the parser keeps the section "
        "as a meaningful unit rather than discarding a short fragment.\n"
    )
    body = (
        "CHAPTER 1\n"
        "1.1 Mechanism\n"
        + paragraph * 6
        + "\n1.2 Qualification\n"
        + paragraph * 5
        + "The same mechanism can fail when liquidity disappears. "
        "See Figure 1 for the threshold and Chapter 1 for the surrounding argument.\n"
    )
    book.write_text(body, encoding="utf-8")
    workspace = tmp_path / "workspace"

    assert main(["--workspace", str(workspace), "ingest", str(book)]) == 0
    ingest = _output(capsys)
    source_id = ingest["source_id"]
    assert ingest["nodes"] >= 2
    assert ingest["navigations"] >= 1

    assert main(["--workspace", str(workspace), "discover", source_id]) == 0
    discovery = _output(capsys)
    assert discovery["marks_after_union"] > 0
    assert discovery["cross_reference_tasks"] >= 1

    assert main(["--workspace", str(workspace), "status"]) == 0
    pending_status = _output(capsys)
    assert pending_status["status"] == "PAUSED_RESOURCE_LIMIT"

    assert main(["--workspace", str(workspace), "reread", source_id]) == 0
    reread = _output(capsys)
    assert reread["attempted"] >= 1

    assert main(["--workspace", str(workspace), "verify", source_id]) == 0
    verification = _output(capsys)
    assert verification["claims_extracted"] > 0
    assert verification["verifications"] == verification["claims_extracted"]

    assert main(["--workspace", str(workspace), "materialize"]) == 0
    materialized = _output(capsys)
    assert materialized["document_node"] >= 2
    assert materialized["read_receipt"] > 0

    assert main(["--workspace", str(workspace), "status"]) == 0
    status = _output(capsys)
    assert status["status"] == "COMPLETE"
