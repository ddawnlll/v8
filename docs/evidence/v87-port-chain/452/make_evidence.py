"""#452 evidence producer: O1 episodes + coverage receipt on a real tape window.

Reads the real multi-asset tape (no synthetic bars), extracts O1 episodes over a bounded
BTCUSDT window, builds a one-template grammar universe at a real decision time, and
reconciles coverage against the shipped expert proposals visible in that window (none —
the receipt honestly records zero representation). All receipts NO_ECONOMIC_CLAIM.

Usage (from repo root):
    uv run --project v8-next python docs/evidence/v87-port-chain/452/make_evidence.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "v8-next" / "src"))

from v8_next.evaluation.multitape import load_multitape  # noqa: E402
from v8_next.experts.features import simple_atr_series  # noqa: E402
from v8_next.oracle import (  # noqa: E402
    AuthorityLevel,
    CandidateTemplate,
    Direction,
    InformationField,
    InformationSet,
    OpportunityGrammar,
    OpportunityUniverseVersion,
    OracleContext,
    OracleDefinition,
    OracleEpisodeExtractor,
    OracleRole,
    ParameterGrid,
    PredicateNode,
    PrimitiveDefinition,
    PrimitiveFamily,
    PrimitiveRegistry,
    SupportClassifier,
    TemplateRegistry,
    ValueRef,
    reconcile_coverage,
)

OUT_DIR = REPO_ROOT / "docs" / "evidence" / "v87-port-chain" / "452"
TAPE_REL = "research/tape/multi-1h-4y/tape.jsonl"
INSTRUMENT = "BTCUSDT"
LIMIT_BARS = 2000
HORIZON = 24


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tape = load_multitape(REPO_ROOT / TAPE_REL, limit=LIMIT_BARS)
    series = list(tape.candles[INSTRUMENT])
    highs = [float(c.high) for c in series]
    lows = [float(c.low) for c in series]
    closes = [float(c.close) for c in series]
    volumes = [float(c.volume) for c in series]
    atrs = simple_atr_series(highs, lows)
    # ATR is measured only from bar ATR_OFFSET onward; the O1 window starts there rather
    # than backfilling the warmup with fabricated values.
    ATR_OFFSET = len(highs) - len(atrs)
    assert ATR_OFFSET >= 0 and len(atrs) > HORIZON + 1
    highs, lows, closes, volumes = (
        highs[ATR_OFFSET:],
        lows[ATR_OFFSET:],
        closes[ATR_OFFSET:],
        volumes[ATR_OFFSET:],
    )

    definition = OracleDefinition(
        symbol=INSTRUMENT,
        horizon_bars=HORIZON,
        min_mfe_pct=0.02,
        max_mae_pct=0.01,
        min_rr_ratio=2.0,
        roundtrip_friction_bps=10.0,
        non_overlapping_policy=True,
    )
    frame = pl.DataFrame(
        {"high": highs, "low": lows, "close": closes, "volume": volumes, "atr": atrs}
    )
    episodes = OracleEpisodeExtractor.extract_episodes(definition, frame)
    for a, b in zip(episodes, episodes[1:]):
        assert a.exit_bar <= b.entry_bar, "O1 episodes must not overlap"

    o1_artifact = {
        "claim": "NO_ECONOMIC_CLAIM",
        "tape": {
            "path": TAPE_REL,
            "sha256": tape.tape_sha256,
            "bars": len(series),
            "atr_offset_bars": ATR_OFFSET,
        },
        "definition": {
            "definition_id": definition.definition_id,
            "symbol": definition.symbol,
            "horizon_bars": definition.horizon_bars,
            "min_mfe_pct": definition.min_mfe_pct,
            "max_mae_pct": definition.max_mae_pct,
            "min_rr_ratio": definition.min_rr_ratio,
            "non_overlapping_policy": True,
        },
        "episode_count": len(episodes),
        "directions": {
            "LONG": sum(1 for e in episodes if e.direction == "LONG"),
            "SHORT": sum(1 for e in episodes if e.direction == "SHORT"),
        },
        "episodes": [e.as_dict() for e in episodes],
    }
    (OUT_DIR / "o1_episodes_real_window.json").write_text(
        json.dumps(o1_artifact, indent=2, sort_keys=True) + "\n"
    )

    # Coverage: one-template grammar evaluated at a real decision time mid-window.
    # The level is derived from the real tape (below the decision-bar close, so the
    # universe is non-empty) and recorded in the artifact — a grammar parameter choice,
    # not a measurement.
    decision_idx = len(series) // 2
    decision_close = closes[decision_idx]
    level = float(int(decision_close // 1000) * 1000 - 1000)
    grammar = OpportunityGrammar(
        version="predicate-ir-v1",
        primitives=PrimitiveRegistry(
            version="registered-v1",
            primitives={
                "close": PrimitiveDefinition(
                    family=PrimitiveFamily.PRICE_RETURN, source_version="state-v1"
                )
            },
            allowed_operators=frozenset({"ABOVE"}),
        ),
        templates=TemplateRegistry(
            version="template-v1",
            templates=(
                CandidateTemplate(
                    template_id="close-above-level",
                    mechanism_family_id="price",
                    behavior_family_id="level",
                    habitat_predicate=PredicateNode.above("close", ValueRef.literal(level)),
                    setup_predicate=PredicateNode.above("close", ValueRef.literal(level)),
                    trigger_predicate=PredicateNode.above("close", ValueRef.literal(level)),
                    direction=Direction.LONG,
                    invalidation="stop-v1",
                    expiry="24bar",
                    risk_geometry={},
                    parameter_names=(),
                ),
            ),
        ),
        grid=ParameterGrid(grid_id="grid-452-evidence", values={}),
    )
    universe = OpportunityUniverseVersion(
        version="452-evidence-1",
        instrument_universe=[INSTRUMENT],
        timeframe_set=["1h"],
        information_contract_id="pit-452-evidence",
        primitive_registry_hash=grammar.primitives.identity(),
        predicate_ir_version=grammar.version,
        behavior_template_registry_hash=grammar.templates.identity(),
        parameter_grid_hash=grammar.grid.identity(),
        tradability_rule_id="detect-452-evidence",
        support_rule_id="canonical-l1-support-v1",
        authority_contract_id="l1-452-evidence",
        search_universe_size=grammar.search_universe_size(1, 1),
        complexity_budget=1,
        created_at=series[-1].start_ns,
        code_hash=hashlib.sha256(b"oracle-452-evidence").hexdigest(),
        execution_mode_id="canonical-l1",
    )
    universe.bind_identity()
    information = InformationSet(decision_time=decision_idx)
    information.insert(
        InformationField(
            name="close",
            value=closes[decision_idx],
            event_time=decision_idx,
            knowledge_time=decision_idx,
            availability_time=decision_idx,
            source_id="tape",
            source_version="multitape-v1",
        )
    )
    candidates = grammar.generate(universe, information)
    context = OracleContext(
        role=OracleRole.HINDSIGHT,
        authority=AuthorityLevel.L1,
        information_contract_id=universe.information_contract_id,
        opportunity_universe_id=universe.universe_id,
        utility_contract_id="utility-452-evidence",
        policy_class_id="policy-452-evidence",
        cost_model_id="cost-452-evidence",
        capacity_model_id="cap-452-evidence",
        environment_target_id="binance-usdt-perp-l1",
    )
    receipt, records = reconcile_coverage(
        universe,
        candidates,
        SupportClassifier.canonical_l1(),
        [],
        HORIZON,
        AuthorityLevel.L1,
        context,
        "lineage-452-evidence",
    )
    coverage_artifact = {
        "claim": "NO_ECONOMIC_CLAIM",
        "decision_bar": decision_idx,
        "decision_close": closes[decision_idx],
        "grammar_level": level,
        "grammar_level_note": "derived from the real tape (below the decision-bar close); "
        "a grammar parameter choice, not a measurement",
        "expert_proposals": [],
        "note": "no shipped expert proposals are visible at this decision time; "
        "the receipt records zero representation rather than a modeled estimate",
        "receipt": receipt.as_dict(),
        "eval_records": len(records),
    }
    (OUT_DIR / "coverage_receipt_real_window.json").write_text(
        json.dumps(coverage_artifact, indent=2, sort_keys=True) + "\n"
    )
    print(f"[452] episodes={len(episodes)} candidates={len(candidates)} "
          f"coverage={receipt.representational_coverage:.4f} "
          f"supported={receipt.supported_opportunity_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
