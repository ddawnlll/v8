"""Prospective capture and bounded native paper replay. No private execution."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import logging
import os
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from nautilus_trader.model import Currency, InstrumentId, Price, Quantity, QuoteTick, Venue

from v8_next.adapters.accounting_replay import replay_frozen_campaigns
from v8_next.adapters.binance_capture import capture, verify
from v8_next.adapters.captured_market import (
    load_account_ratio,
    load_candles,
    load_open_interest,
    load_settled_funding,
)
from v8_next.adapters.economic_paper import EconomicPaperAdapter
from v8_next.adapters.engine_state import economic_state, reconcile_replay
from v8_next.adapters.native_tape import build_engine, capture_native_inputs
from v8_next.app.observe import initialize, observe_capture
from v8_next.domain.campaign import PaperCampaign
from v8_next.domain.config import PaperConfig
from v8_next.domain.market import CausalFrame, frame_at
from v8_next.domain.positioning import PositioningReading
from v8_next.economics.controller import InstrumentConstraints
from v8_next.economics.decisions import UtilityInputs
from v8_next.evaluation.store import ResearchStore, canonical
from v8_next.risk.admission import RiskLimits


def replay_account(
    manifests: list[Path], config: dict[str, Any], *, observer: str | None = None
) -> dict[str, Any]:
    parsed = PaperConfig.model_validate(config)
    selected_observer = observer if observer is not None else parsed.observer_policy
    if not manifests:
        raise ValueError("no prospective captures")
    quotes = []
    frames: dict[int | tuple[str, int], CausalFrame] = {}
    positioning_readings: list[PositioningReading] = []
    instrument_manifests: dict[str, Path] = {}
    for manifest in manifests:
        verify(manifest)
        metadata = json.loads(manifest.read_text())
        artifact = next(a for a in metadata["artifacts"] if a["path"] == "quote.json")
        row = json.loads((manifest.parent / "quote.json").read_text())
        if row["symbol"] not in {"BTCUSDT", "ETHUSDT"}:
            raise ValueError("paper scope is BTCUSDT/ETHUSDT")
        instrument_id = row["symbol"] + "-PERP.BINANCE"
        instrument_manifests.setdefault(instrument_id, manifest)
        received = int(artifact["received_time_ns"])
        event = int(row["time"]) * 1_000_000
        if event > received:
            raise ValueError("venue clock ahead of local receipt; clock qualification required")
        if Decimal(row["bidPrice"]) > Decimal(row["askPrice"]):
            raise ValueError("crossed quote")
        if parsed.funding_max_age_ns is not None:
            positioning_readings.extend(
                load_settled_funding(manifest, max_age_ns=parsed.funding_max_age_ns)
            )
        if parsed.open_interest_max_age_ns is not None:
            positioning_readings.extend(
                load_open_interest(manifest, max_age_ns=parsed.open_interest_max_age_ns)
            )
        if parsed.account_ratio_period is not None and parsed.account_ratio_max_age_ns is not None:
            positioning_readings.extend(
                load_account_ratio(
                    manifest,
                    period=parsed.account_ratio_period,
                    max_age_ns=parsed.account_ratio_max_age_ns,
                )
            )
        candles = load_candles(manifest)
        known = tuple(replace(c, available_ns=c.received_ns) for c in candles)
        key = (instrument_id, received)
        if key in frames:
            raise ValueError("duplicate paper instrument receipt")
        frames[key] = frame_at(instrument_id, received, known)
        quotes.append(
            QuoteTick(
                InstrumentId.from_str(instrument_id),
                Price.from_str(row["bidPrice"]),
                Price.from_str(row["askPrice"]),
                Quantity.from_str(row["bidQty"]),
                Quantity.from_str(row["askQty"]),
                event,
                received,
            )
        )
    engine, _ = build_engine(
        manifests[0],
        Decimal(config["maker_fee"]),
        Decimal(config["taker_fee"]),
        Decimal(config["initial_balance"]),
        historical_data=False,
    )
    try:
        constraints_by_instrument = {}
        for index, (instrument_id, manifest) in enumerate(instrument_manifests.items()):
            if index:
                _, native_instrument, _, _ = capture_native_inputs(
                    manifest, parsed.maker_fee, parsed.taker_fee
                )
                engine.add_instrument(native_instrument)
            metadata = json.loads((manifest.parent / "instruments.json").read_text())
            symbol = instrument_id.split("-")[0]
            instrument = next(i for i in metadata["symbols"] if i["symbol"] == symbol)
            filters = {f["filterType"]: f for f in instrument["filters"]}
            lot = filters["MARKET_LOT_SIZE"]
            constraints_by_instrument[instrument_id] = InstrumentConstraints(
                Decimal(lot["stepSize"]),
                Decimal(lot["minQty"]),
                Decimal(lot["maxQty"]),
                Decimal(filters["MIN_NOTIONAL"]["notional"]),
            )
        calibration_provider = None
        if parsed.calibration_source_run is not None:
            source_run_path = Path(parsed.calibration_source_run)

            def calibration_provider(
                opportunity: Any, decision_ns: int
            ) -> tuple[UtilityInputs, bool]:
                from v8_next.evaluation.calibration import inspect_calibration_source

                inspection = inspect_calibration_source(source_run_path, decision_ns)
                if not inspection.get("eligible_for_utility", False):
                    return (
                        UtilityInputs(None, None, None, None, None, None, None),
                        False,
                    )
                return (
                    UtilityInputs(
                        gross_edge=inspection.get("gross_edge"),
                        fees=None,
                        spread=None,
                        slippage=None,
                        funding_cost=None,
                        uncertainty=inspection.get("uncertainty"),
                        calibration_receipt=None,
                    ),
                    True,
                )

        strategy = EconomicPaperAdapter(
            frames,
            RiskLimits(
                Decimal(1),
                Decimal(config["max_exposure_fraction"]),
                Decimal(config["max_notional"]),
                0,
            ),
            constraints_by_instrument,
            Decimal(config["max_notional"]),
            calibration=calibration_provider,
            observer=selected_observer,
            grammar=parsed.grammar_policy,
            campaign_policy=parsed.campaign_policy,
            stop_budget=parsed.stop_budget,
            positioning_readings=tuple(positioning_readings),
        )
        engine.add_strategy(strategy)
        quotes.sort(key=lambda q: (q.ts_init, str(q.instrument_id), q.ts_event))
        engine.add_data(quotes)
        engine.run()
        if strategy.callback_failure is not None:
            raise ValueError(f"paper callback failed: {strategy.callback_failure}")
        state = economic_state(engine, Venue("BINANCE"), Currency.from_str("USDT"))
        state["quote_count"] = len(quotes)
        state["instruments"] = sorted(instrument_manifests)
        state["campaign_status"] = "NO_VERIFIED_CALIBRATION"
        state["economic_decisions"] = strategy.decisions
        state["campaigns"] = [c.to_record() for c in strategy.campaigns]
        state["campaign_observations"] = strategy.campaign_observations(state)
        state["funding_status"] = (
            "UNVERIFIED_ONLINE_FUNDING"
            if state["positions"]
            else "NO_EXPOSURE_IN_SESSION_NO_FUNDING_LIABILITY"
        )
        state["limitations"] = [
            "sampled_REST_quotes_not_continuous_execution_feed",
            "positive_campaign_and_online_funding_integration_pending",
        ]
        return state
    finally:
        engine.dispose()


def step(run: Path, config: dict[str, Any], *, replay_only: bool = False) -> dict[str, Any]:
    """One local writer per session; the OS releases the lock on process exit."""
    PaperConfig.model_validate(config)
    run.mkdir(parents=True, exist_ok=True)
    with (run / ".paper.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("paper session already has an active writer") from error
        try:
            return _step_locked(run, config, replay_only=replay_only)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _step_locked(run: Path, config: dict[str, Any], *, replay_only: bool) -> dict[str, Any]:
    parsed = PaperConfig.model_validate(config)
    frozen = initialize(run, config)
    manifests = sorted(run.glob("capture-*/manifest.json"))
    checkpoint = run / "paper-state.json"
    if checkpoint.exists():
        saved = json.loads(checkpoint.read_text())
        if saved["policy_hash"] != frozen["policy_hash"]:
            raise ValueError("paper checkpoint belongs to another policy")
        prior_paths = [(run / name).resolve() for name in saved["manifests"]]
        if any(not path.is_relative_to(run.resolve()) for path in prior_paths):
            raise ValueError("paper checkpoint source escapes run")
        if len(set(prior_paths)) != len(prior_paths):
            raise ValueError("duplicate paper checkpoint source")
        for path, expected in zip(prior_paths, saved["manifest_hashes"], strict=True):
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("paper capture manifest changed")
        recovered = replay_account(prior_paths, config)
        reconcile_replay(saved["native_state"], recovered)
        prior_campaigns = tuple(PaperCampaign.from_record(c) for c in recovered["campaigns"])
        reconcile_replay(
            saved["revised_accounting"],
            replay_frozen_campaigns(
                prior_paths,
                prior_campaigns,
                config,
                int(saved["revised_accounting"]["accounting_as_of_ns"]),
            ),
        )
    if not replay_only:
        manifests.append(
            capture(
                run / f"capture-{time.time_ns()}",
                # Retain all session liabilities and the pre-session settled
                # observation window. Receipt-time gating still applies.
                funding_start_ms=max(
                    0, int(str(frozen["frozen_ns"])) - (parsed.funding_max_age_ns or 0)
                )
                // 1_000_000,
                include_open_interest=parsed.open_interest_max_age_ns is not None,
                account_ratio_period=parsed.account_ratio_period,
            )
        )
    if not manifests:
        raise ValueError("no captured session to replay")
    for manifest in manifests:
        observe_capture(run, manifest, frozen)
    state = replay_account(manifests, config)
    campaigns = tuple(PaperCampaign.from_record(c) for c in state["campaigns"])
    cutoff = max(
        int(a["received_time_ns"])
        for p in manifests
        for a in json.loads(p.read_text())["artifacts"]
    )
    revised_accounting = replay_frozen_campaigns(manifests, campaigns, config, cutoff)
    store = ResearchStore(run / "research.sqlite")
    try:
        for observation in state["campaign_observations"]:
            store.record_campaign_observation(observation["campaign_id"], cutoff, observation)
    finally:
        store.close()
    result = {
        "policy_hash": frozen["policy_hash"],
        "manifests": [str(p.relative_to(run)) for p in manifests],
        "manifest_hashes": [hashlib.sha256(p.read_bytes()).hexdigest() for p in manifests],
        "native_state": state,
        "revised_accounting": revised_accounting,
    }
    temporary = run / "paper-state.tmp"
    with temporary.open("w") as output:
        output.write(canonical(result) + "\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(checkpoint)
    directory = os.open(run, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return result


def load_policy_config(path: Path) -> dict[str, Any]:
    """Economic choices only; CLI account/fee assumptions cannot be overridden."""
    policy = json.loads(path.read_text())
    allowed = {
        "observer_policy",
        "grammar_policy",
        "campaign_policy",
        "stop_budget",
        "funding_max_age_ns",
        "open_interest_max_age_ns",
        "account_ratio_period",
        "account_ratio_max_age_ns",
        "calibration_source_run",
    }
    if not isinstance(policy, dict) or set(policy) - allowed:
        raise ValueError("policy config must contain only economic policy fields")
    return dict(policy)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--maker-fee", type=Decimal, required=True)
    parser.add_argument("--taker-fee", type=Decimal, required=True)
    parser.add_argument("--initial-balance", type=Decimal, required=True)
    parser.add_argument("--max-notional", type=Decimal, required=True)
    parser.add_argument("--max-exposure-fraction", type=Decimal, required=True)
    parser.add_argument(
        "--policy-config", type=Path, help="JSON economic policy selection and freshness"
    )
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args()
    config: dict[str, Any] = {
        "maker_fee": str(args.maker_fee),
        "taker_fee": str(args.taker_fee),
        "initial_balance": str(args.initial_balance),
        "max_notional": str(args.max_notional),
        "max_exposure_fraction": str(args.max_exposure_fraction),
    }
    if args.policy_config is not None:
        config.update(load_policy_config(args.policy_config))
    PaperConfig.model_validate(config)
    started = time.perf_counter()
    try:
        result = step(args.run_directory, config, replay_only=args.replay_only)
    except Exception as error:
        logging.error(
            json.dumps(
                {
                    "event": "PAPER_STEP_FAILED",
                    "time_ns": time.time_ns(),
                    "error_type": type(error).__name__,
                    "wall_seconds": time.perf_counter() - started,
                }
            )
        )
        raise
    logging.info(
        json.dumps(
            {
                "event": "PAPER_STEP_COMPLETED",
                "time_ns": time.time_ns(),
                "wall_seconds": time.perf_counter() - started,
                "capture_count": len(result["manifests"]),
                "order_count": len(result["native_state"]["orders"]),
                "position_count": len(result["native_state"]["positions"]),
                "funding_status": result["native_state"]["funding_status"],
            }
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
