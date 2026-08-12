"""S4 gate (in progress) — CandidateBuffer + ExpertPlane.

The full S4 gate is candidate-population parity: the candidates/evaluations/
outcomes values bit-identical to the Python lab on the fixture set. This
suite exercises the ExpertPlane port incrementally — the evaluate() drafts
must match the Python lab's per-bar evaluations bit-for-bit before the
lifecycle/admission loop can be meaningfully compared.

The PORTED set is read from the binary's `registry` subcommand (each expert
module carries its own PORTED flag), so ports only ever touch their own module
file and this harness never hand-maintains the list. `--expert <id>` filters
to one expert (used by the per-port agents and the integration loop).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

from . import runner
from .runner import ParityFailure

REPO_ROOT = runner.REPO_ROOT

# expert_id -> Python class (frozen oracle; EXPERT_PROTOCOL §3).
EXPERT_CLASSES = {
    "bollinger_breakout": "BollingerBreakoutExpert",
    "bollinger_reversion": "BollingerReversionExpert",
    "breakout_retest": "BreakoutRetestExpert",
    "candlestick_reversal": "CandlestickReversalExpert",
    "divergence_12_setups": "Divergence12SetupsExpert",
    "donchian_breakout": "DonchianBreakoutExpert",
    "failed_breakout": "FailedBreakoutExpert",
    "failed_breakout_2b": "FailedBreakout2BExpert",
    "fib_projection_reversal": "FibProjectionReversalExpert",
    "fib_retracement_continuation": "FibRetracementContinuationExpert",
    "fib_rsi_bb_confluence": "FibRsiBbConfluenceExpert",
    "floor_trader_pivot": "FloorTraderPivotExpert",
    "funding_crowding_reversal": "FundingCrowdingReversalExpert",
    "gap_exhaustion": "GapExhaustionExpert",
    "ichimoku_cloud": "IchimokuCloudExpert",
    "liquidity_sweep_reclaim": "LiquiditySweepReclaimExpert",
    "macd_stoch_trend": "MacdStochTrendExpert",
    "market_profile_value_area": "MarketProfileValueAreaExpert",
    "obv_adl_regime": "ObvAdlRegimeExpert",
    "open_interest_divergence": "OpenInterestDivergenceExpert",
    "pandf_breakout": "PandfBreakoutExpert",
    "pattern_measuring_objective": "PatternMeasuringObjectiveExpert",
    "range_breakout_1to1": "RangeBreakout1To1Expert",
    "rsi_stoch_reversion": "RsiStochReversionExpert",
    "trend_pullback": "TrendPullbackExpert",
    "trend_pullback_depth": "TrendPullbackDepthExpert",
    "volume_climax_reversal": "VolumeClimaxReversalExpert",
    "volume_confirmed_breakout": "VolumeConfirmedBreakoutExpert",
}


def _registry(binary: Path) -> dict[str, bool]:
    """{expert_id: ported} straight from the binary (single source of truth)."""
    proc = subprocess.run([str(binary), "registry"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"registry subcommand failed: {proc.stderr}")
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    return {r["expert_id"]: r["ported"] for r in out["registry"]}


def _ported(binary: Path) -> list[str]:
    return sorted(e for e, p in _registry(binary).items() if p)


def _pilots(expert_ids: list[str]):
    import v8.experts as ex
    return [getattr(ex, EXPERT_CLASSES[eid])() for eid in expert_ids]


def _run_lab(tmp_path, rows, expert_ids):
    lab = Lab(tmp_path)
    lab.ingest(rows)
    tape = lab.tape_log.replay_tape()
    bars = sorted([r for r in tape if r.channel == "kline"
                   and r.payload.get("closed") is True],
                  key=lambda r: r.available_time)
    manifest = ExperimentManifest(
        experiment_id="s4", code_hash="", data_hash="",
        universe=("SOLUSDT",), start_ns=bars[0].available_time,
        end_ns=bars[-1].available_time)
    lab.run(manifest, _pilots(expert_ids))
    # evaluations.jsonl: {knowledge_time, expert_id, applicability, decision,
    #                      draft}
    evals = {}
    for line in (tmp_path / "evaluations.jsonl").read_text().splitlines():
        rec = json.loads(line)
        evals[(rec["knowledge_time"], rec["expert_id"])] = rec
    return lab, bars, evals


def _rust_evals(v8_core_binary, tmp_path, bars, cases):
    """Batch evaluate-check; returns {case_key: result}."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    tape = runner.write_tape(bars, tmp_path / "tape.jsonl")
    req = {"tape_path": str(tape), "universe": ["SOLUSDT"],
           "cases": [{"expert_id": e, "bar_index": b} for e, b in cases],
           "history_depth": 32}
    req_path = tmp_path / "req.json"
    req_path.write_text(json.dumps(req))
    proc = subprocess.run([str(v8_core_binary), "evaluate-check", str(req_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ParityFailure(f"evaluate-check failed: {proc.stderr}")
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    return {(r["expert_id"], r["bar_index"]): r for r in out["results"]}


def _target_experts(binary: Path, request) -> list[str]:
    """--expert <id> narrows to one; otherwise all ported experts."""
    only = request.config.getoption("--expert")
    ported = _ported(binary)
    if only:
        assert only in ported, (
            f"--expert {only} is not ported; ported={ported}")
        return [only]
    return ported


def test_registry_complete(v8_core_binary):
    reg = _registry(v8_core_binary)
    assert len(reg) == 28, f"registry has {len(reg)} entries, expected 28"
    missing = set(EXPERT_CLASSES) - set(reg)
    assert not missing, f"registry missing experts: {missing}"


def test_drafts_match_python_evaluations(v8_core_binary, tmp_path, request):
    experts = _target_experts(v8_core_binary, request)
    rows = make_synthetic_tape(seed=7, n_bars=120, continuous=True)
    lab, bars, evals = _run_lab(tmp_path / "lab", rows, experts)
    rust_all = _rust_evals(v8_core_binary, tmp_path / "rust",
                           bars, [(e, i) for i in range(len(bars))
                                  for e in experts])
    checked = 0
    for bar_idx, bar in enumerate(bars):
        t_ns = bar.available_time
        for eid in experts:
            py = evals.get((t_ns, eid))
            rust = rust_all[(eid, bar_idx)]
            assert rust["decision"] == py["decision"], (
                f"{eid} bar {bar_idx}: decision py={py['decision']} rust={rust['decision']}")
            if py["decision"] == "CANDIDATE":
                pd = py["draft"]
                rd = rust["draft"]
                assert rd["direction"] == pd["direction"], (
                    f"{eid} bar {bar_idx}: direction py={pd['direction']} rust={rd['direction']}")
                assert rd["birth_time"] == pd["birth_time"], (
                    f"{eid} bar {bar_idx}: birth_time")
                assert rd["risk_geometry"] == pd["risk_geometry"], (
                    f"{eid} bar {bar_idx}: geometry py={pd['risk_geometry']} "
                    f"rust={rd['risk_geometry']}")
                assert rust["setup_fingerprint"] == pd.get("setup_fingerprint"), (
                    f"{eid} bar {bar_idx}: fingerprint py={pd.get('setup_fingerprint')} "
                    f"rust={rust['setup_fingerprint']}")
                checked += 1
    assert checked > 0, "no candidate bars in fixture"


def test_anchors_match(v8_core_binary, tmp_path, request):
    """The D-026 setup_anchor_event_id must match on every candidate bar."""
    experts = _target_experts(v8_core_binary, request)
    rows = make_synthetic_tape(seed=7, n_bars=120, continuous=True)
    lab, bars, evals = _run_lab(tmp_path / "lab", rows, experts)
    rust_all = _rust_evals(v8_core_binary, tmp_path / "rust",
                           bars, [(e, i) for i in range(len(bars))
                                  for e in experts])
    checked = 0
    for bar_idx, bar in enumerate(bars):
        t_ns = bar.available_time
        for eid in experts:
            py = evals.get((t_ns, eid))
            rust = rust_all[(eid, bar_idx)]
            if py and py["decision"] == "CANDIDATE":
                assert rust["decision"] == "CANDIDATE", f"{eid} bar {bar_idx}"
                assert rust["draft"]["direction"] == py["draft"]["direction"]
                py_anchor = py["draft"].get("setup_anchor_event_id")
                assert py_anchor is not None, f"{eid} bar {bar_idx}: no py anchor"
                assert rust["setup_anchor_event_id"] == py_anchor, (
                    f"{eid} bar {bar_idx}: anchor py={py_anchor} "
                    f"rust={rust['setup_anchor_event_id']}")
                checked += 1
    assert checked > 0, "no candidate bars in fixture"
