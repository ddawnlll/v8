"""#444 — a smoke window mints no published capability score.

Evidence classes:

* **mechanics** — the receipt-level rule: a receipt that declares a non-evidential
  window (``profile=smoke``, ``economic_evidence=false``) and carries a numeric
  capability score is refused by name
  (``NON_EVIDENTIAL_WINDOW_CAPABILITY_SCORE``) before any hash is recomputed; the
  same window may still record a run with no score; the class is bound *into* the
  digest, so it cannot be edited away after the number was minted.
* **evaluative** — on the real tape: the same command in its bar-count variant and
  in its UTC-bounded variant produces ledger entries that differ in **evidence
  class** (smoke / no score vs benchmark / scored) and not merely in bar count,
  and the smoke run's bound ledger receipt names its class (``grep -i smoke`` >= 1).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from v8_next.evaluation.benchmark_receipt import (
    NON_EVIDENTIAL_WINDOW_CAPABILITY_SCORE,
    RECEIPT_DIGEST_VERSION,
    BenchmarkLedger,
    BenchmarkReceipt,
    GateState,
    GateVector,
    WindowEvidence,
)
from v8_next.evaluation.run_window import WindowSpec

TAPE_DIR = Path("/Users/hootie/src/v8/research/tape/quad-1h-12m")
TAPE_FILE = TAPE_DIR / "tape.jsonl"
HOUR_MS = 3_600_000
#: Both variants consume this many bars: the discriminating variable is the
#: evidence class, not the length of the window (#444.R3).
WINDOW_BARS = 500


def _iso(ms: int) -> str:
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _smoke_window() -> WindowSpec:
    window = WindowSpec(tape_path="tape", profile="smoke", bars=WINDOW_BARS)
    window.validate()
    return window


def _bounded_window() -> WindowSpec:
    window = WindowSpec(
        tape_path="tape", profile="benchmark", start_ms=1_751_328_000_000,
        end_ms=1_751_328_000_000 + WINDOW_BARS * HOUR_MS,
    )
    window.validate()
    return window


def _receipt(
    tmp_path: Path,
    *,
    window: WindowSpec,
    capability_score: float | None,
    name: str = "trades.jsonl",
) -> BenchmarkReceipt:
    from v8_next.evaluation.parity import ArtifactBinding

    artifact = tmp_path / name
    artifact.write_text('{"trade_id":"t","pnl":1.0}\n')
    return BenchmarkReceipt.create(
        case_id="BC-444-SMOKE",
        policy_id="pol_444",
        capability_score=capability_score,
        gates=GateVector(g0_identity=GateState.PASS, g1_causal_pit=GateState.UNKNOWN),
        computed_at_timestamp_ns=1_700_000_000_000_000_000,
        artifact_bindings=(ArtifactBinding.from_file("native_trades", artifact),),
        input_binding="input-binding-444",
        window_evidence=WindowEvidence.from_window(window),
    )


# --------------------------------------------------------------------------- #
# mechanics
# --------------------------------------------------------------------------- #
def test_verify_refuses_capability_score_minted_by_a_non_evidential_window(
    tmp_path: Path,
) -> None:
    smoked = _receipt(tmp_path, window=_smoke_window(), capability_score=14.0)
    evidence = smoked.window_evidence
    assert evidence is not None
    assert evidence.profile == "smoke"
    assert evidence.evidence_class == "smoke"
    assert evidence.is_smoke is True
    assert evidence.economic_evidence is False

    ok, reason = smoked.verify()
    assert ok is False
    assert reason.startswith(NON_EVIDENTIAL_WINDOW_CAPABILITY_SCORE)
    assert "smoke" in reason and "14.0" in reason

    # the ledger refuses the same receipt: it cannot be appended at all
    with pytest.raises(ValueError, match=NON_EVIDENTIAL_WINDOW_CAPABILITY_SCORE):
        BenchmarkLedger().append(smoked)


def test_non_evidential_window_may_still_record_a_run_without_a_score(
    tmp_path: Path,
) -> None:
    record = _receipt(tmp_path, window=_smoke_window(), capability_score=None, name="rec.jsonl")
    ok, reason = record.verify()
    assert ok, reason
    ledger = BenchmarkLedger()
    entry = ledger.append(record)
    assert entry.receipt.capability_score is None
    assert ledger.verify_chain() == (True, "OK")


def test_evidential_window_still_mints_and_verifies(tmp_path: Path) -> None:
    """The evidence path is not weakened: a UTC-bounded benchmark keeps its score."""
    scored = _receipt(tmp_path, window=_bounded_window(), capability_score=14.0, name="bench.jsonl")
    evidence = scored.window_evidence
    assert evidence is not None
    assert evidence.evidence_class == "benchmark"
    assert evidence.economic_evidence is True
    assert evidence.is_smoke is False
    ok, reason = scored.verify()
    assert ok, reason
    assert BenchmarkLedger().append(scored).receipt.capability_score == 14.0


def test_window_class_is_bound_into_the_digest_and_cannot_be_edited_away(
    tmp_path: Path,
) -> None:
    record = _receipt(tmp_path, window=_smoke_window(), capability_score=None, name="bound.jsonl")
    assert record.digest_version == RECEIPT_DIGEST_VERSION
    assert record.verify()[0] is True

    # relabelling the window after the fact (smoke -> benchmark) is a digest tamper
    relabelled = record.model_copy(
        update={"window_evidence": WindowEvidence.from_window(_bounded_window())}
    )
    ok, reason = relabelled.verify_digest()
    assert ok is False
    assert reason.startswith("DIGEST_TAMPERED")

    # dropping the declaration entirely is a tamper too: a receipt cannot lose the
    # class it was minted under to escape the rule
    stripped = record.model_copy(update={"window_evidence": None})
    ok, reason = stripped.verify_digest()
    assert ok is False
    assert reason.startswith("DIGEST_TAMPERED")

    # and a forged class with a score is refused by name, not merely by hash
    forged = relabelled.model_copy(
        update={
            "capability_score": 14.0,
            "receipt_digest": _receipt(
                tmp_path, window=_smoke_window(), capability_score=14.0, name="forged.jsonl"
            ).receipt_digest,
        }
    )
    ok, reason = forged.verify()
    assert ok is False
    assert reason.startswith(NON_EVIDENTIAL_WINDOW_CAPABILITY_SCORE) or reason.startswith(
        "DIGEST_TAMPERED"
    )


# --------------------------------------------------------------------------- #
# evaluative — real tape
# --------------------------------------------------------------------------- #
def _window_bounds_ms() -> tuple[int, int]:
    """The tape's first bar and the open time one window-length later."""
    from v8_next.evaluation.multitape import load_multitape

    tape = load_multitape(TAPE_DIR, limit=WINDOW_BARS + 1)
    bars = tape.candles[tape.instruments[0]]
    assert len(bars) == WINDOW_BARS + 1
    return bars[0].start_ns // 1_000_000, bars[WINDOW_BARS].start_ns // 1_000_000


def _only_ledger_entry(out_dir: Path):
    ledger = BenchmarkLedger.load_jsonl(out_dir / "benchmark_ledger.jsonl")
    assert len(ledger.entries) == 1, "one run must append exactly one ledger entry"
    assert ledger.verify_chain() == (True, "OK")
    return ledger.entries[0]


def _only_manifest(out_dir: Path) -> dict:
    runs = [
        path
        for path in sorted((out_dir / "runs").glob("*.json"))
        if not path.name.endswith(".telemetry.json")
    ]
    assert len(runs) == 1
    return json.loads(runs[0].read_text())


def _economic_net_return(out_dir: Path) -> float:
    receipts = sorted(out_dir.glob("economic_receipt_*.json"))
    assert receipts, "the run bound no economic receipt"
    return float(json.loads(receipts[0].read_text())["metrics"]["portfolio_P"]["net_return"])


def test_smoke_and_utc_bounded_runs_differ_in_evidence_class(tmp_path: Path) -> None:
    from v8_next.app import portfolio as port_mod

    if not TAPE_FILE.is_file():
        pytest.skip(f"quad tape absent at {TAPE_FILE}")

    smoke_dir = tmp_path / "smoke"
    bounded_dir = tmp_path / "bounded"
    start_ms, end_ms = _window_bounds_ms()

    # (i) the bar-count variant: a smoke window, never a release benchmark
    assert (
        port_mod.main(
            [
                "--tape-path", str(TAPE_DIR),
                "--bars", str(WINDOW_BARS),
                "--output-dir", str(smoke_dir),
            ]
        )
        == 0
    )
    # (ii) the UTC-bounded variant of the same command over the same bars
    assert (
        port_mod.main(
            [
                "--tape-path", str(TAPE_DIR),
                "--start-utc", _iso(start_ms),
                "--end-utc", _iso(end_ms),
                "--output-dir", str(bounded_dir),
            ]
        )
        == 0
    )

    smoke = _only_ledger_entry(smoke_dir).receipt
    bounded = _only_ledger_entry(bounded_dir).receipt
    smoke_evidence = smoke.window_evidence
    bounded_evidence = bounded.window_evidence
    assert smoke_evidence is not None and bounded_evidence is not None

    # same data, same measured result: the runs consumed the same bars
    assert _economic_net_return(smoke_dir) == _economic_net_return(bounded_dir)
    assert _only_manifest(smoke_dir)["window"]["bars"] == WINDOW_BARS
    assert _only_manifest(bounded_dir)["window"]["bars"] is None
    assert _only_manifest(bounded_dir)["window"]["start_ms"] == start_ms

    # the difference is the evidence class, and it is carried on the receipt
    assert smoke_evidence.evidence_class == "smoke"
    assert smoke_evidence.is_smoke is True
    assert smoke_evidence.economic_evidence is False
    assert smoke.capability_score is None, "a smoke window must mint no capability score"

    assert bounded_evidence.evidence_class == "benchmark"
    assert bounded_evidence.economic_evidence is True
    assert bounded.capability_score is not None

    assert smoke_evidence.evidence_class != bounded_evidence.evidence_class
    assert smoke.digest_version == bounded.digest_version == RECEIPT_DIGEST_VERSION
    assert smoke.receipt_digest != bounded.receipt_digest

    # the class reaches the artifact the run bound, where a consumer can read it
    ledger_text = (smoke_dir / "benchmark_ledger.jsonl").read_text(encoding="utf-8").lower()
    assert ledger_text.count("smoke") >= 1
    assert _only_manifest(smoke_dir)["detail"]["evidence_class"] == "smoke"
    telemetry = sorted((smoke_dir / "runs").glob("*.telemetry.json"))
    assert len(telemetry) == 1
    assert json.loads(telemetry[0].read_text())["evidence_class"] == "smoke"
