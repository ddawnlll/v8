"""Run a frozen DEVELOPMENT policy experiment on captured real historical bars."""

import argparse
import hashlib
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from nautilus_trader.model import Currency, Venue

from v8_next.adapters.captured_market import load_candles
from v8_next.adapters.engine_state import economic_state
from v8_next.adapters.historical_trial import HistoricalTrial
from v8_next.adapters.native_tape import build_engine
from v8_next.adapters.stop_exposure import native_stop_exposure
from v8_next.app.observe import source_hash
from v8_next.domain.config import PaperConfig
from v8_next.evaluation.equity import equity_losses
from v8_next.evaluation.outcomes import observed_outcomes
from v8_next.evaluation.store import ResearchStore, canonical


def run_trial(
    manifest: Path, policy: PaperConfig, store: ResearchStore, family: str
) -> dict[str, Any]:
    return _run_trial(manifest, policy, store, family, "DEVELOPMENT")


def _run_trial(
    manifest: Path,
    policy: PaperConfig,
    store: ResearchStore,
    family: str,
    role: Literal["DEVELOPMENT", "HOLDOUT"],
) -> dict[str, Any]:
    if not family.strip():
        raise ValueError("explicit research family required")
    dataset_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if (
        role == "DEVELOPMENT"
        and store.db.execute(
            "SELECT 1 FROM trials WHERE dataset_hash=? AND role='HOLDOUT'", (dataset_hash,)
        ).fetchone()
    ):
        raise ValueError("protected holdout cannot be used as a development trial")
    frozen = {
        "config": policy.model_dump(mode="json"),
        "code_and_lock_hash": source_hash(),
        "execution_model": "NATIVE_OHLC_NEXT_BAR_CLOSE_TRIAL_V1",
        "role": role,
    }
    policy_hash = hashlib.sha256(canonical(frozen).encode()).hexdigest()
    trial_id = hashlib.sha256(canonical([family, dataset_hash, policy_hash]).encode()).hexdigest()
    existing = store.db.execute(
        "SELECT registered_ns FROM trials WHERE trial_id=?", (trial_id,)
    ).fetchone()
    registered = existing[0] if existing else time.time_ns()
    store.register_trial(trial_id, family, policy_hash, dataset_hash, role, registered)
    candles = load_candles(manifest)
    if any(c.instrument_id != "BTCUSDT-PERP.BINANCE" for c in candles):
        raise ValueError("initial historical trial scope is BTCUSDT")
    if not candles:
        raise ValueError("empty trial dataset")
    store.register_dataset_window(
        dataset_hash,
        "BTCUSDT-PERP.BINANCE",
        min(c.start_ns for c in candles),
        max(c.end_ns for c in candles),
    )
    engine, metadata = build_engine(
        manifest, policy.maker_fee, policy.taker_fee, policy.initial_balance
    )
    try:
        trial = HistoricalTrial(candles, policy)
        engine.add_strategy(trial)
        engine.run()
        if trial.failure is not None or trial.callback_failure is not None:
            raise ValueError(
                f"historical trial callback failed: {trial.failure or trial.callback_failure}"
            )
        state = economic_state(engine, Venue("BINANCE"), Currency.from_str("USDT"))
        pending_ids = frozenset(
            c.campaign_id
            for c in trial.campaigns
            if c.campaign_id not in trial.submitted | trial.expired | trial.invalidated
        )
        stop_exposure = native_stop_exposure(
            engine.cache,
            trial.campaigns,
            pending_campaigns=any(
                c.campaign_id not in trial.submitted | trial.expired | trial.invalidated
                for c in trial.campaigns
            ),
            observed_ns=candles[-1].end_ns,
            pending_ids=pending_ids,
        )
        computed_ns = time.time_ns()
        losses = equity_losses(
            trial.equity_marks, capital=policy.initial_balance, computed_ns=computed_ns
        )
        return {
            **metadata,
            "trial_id": trial_id,
            "family": family,
            "family_trial_count": store.family_size(family),
            "registered_ns": registered,
            "dataset_hash": dataset_hash,
            "policy_hash": policy_hash,
            "frozen_policy": frozen,
            "scope": "OFFLINE_COUNTERFACTUAL_POLICY_EXPERIMENT",
            "authority": "DIAGNOSTIC_ONLY",
            "calibration_eligible": False,
            "promotion_eligible": False,
            "account": state,
            "stop_exposure": {
                **asdict(stop_exposure),
                "open_and_reserved_risk": str(stop_exposure.open_and_reserved_risk),
            }
            if stop_exposure is not None
            else None,
            "equity_marks": trial.equity_marks,
            "computed_ns": computed_ns,
            "period_loss_definition": "NEGATIVE_EQUITY_CHANGE_OVER_FIXED_INITIAL_CAPITAL",
            "period_losses": [
                {
                    "start_ns": row.start_ns,
                    "end_ns": row.end_ns,
                    "available_ns": row.available_ns,
                    "loss": str(row.loss),
                }
                for row in losses
            ],
            "decisions": trial.decisions,
            "campaigns": [c.to_record() for c in trial.campaigns],
            "campaign_observations": trial.campaign_observations(state),
            "position_closures": list(trial.position_closures.values()),
            "outcomes": observed_outcomes(
                [c.to_record() for c in trial.campaigns],
                list(trial.position_closures.values()),
                state,
                policy.initial_balance,
            ),
            "funding_coverage": "OBSERVED_RECORDS_NOT_COMPLETENESS_CERTIFIED",
            "limitations": [
                "modeled_close_availability",
                "current_instrument_metadata",
                "native_OHLC_intrabar_path_assumption",
                "historical_spread_and_slippage_unmeasured",
                "generic_margin_no_venue_liquidation",
                "not_a_calibration_receipt",
            ],
        }
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--family", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("trial output already exists")
    policy = PaperConfig.model_validate_json(args.policy.read_text())
    store = ResearchStore(args.store)
    try:
        result = run_trial(args.manifest, policy, store, args.family)
        with args.output.open("x") as stream:
            stream.write(canonical(result) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
