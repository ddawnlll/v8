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
from v8_next.adapters.captured_market import load_candles
from v8_next.adapters.economic_paper import EconomicPaperAdapter
from v8_next.adapters.engine_state import economic_state, reconcile_replay
from v8_next.adapters.native_tape import build_engine
from v8_next.app.observe import initialize, observe_capture
from v8_next.domain.campaign import PaperCampaign
from v8_next.domain.config import PaperConfig
from v8_next.domain.market import frame_at
from v8_next.economics.controller import InstrumentConstraints
from v8_next.evaluation.store import ResearchStore, canonical
from v8_next.risk.admission import RiskLimits


def replay_account(
    manifests: list[Path], config: dict[str, str], *, observer: str | None = None
) -> dict[str, Any]:
    parsed = PaperConfig.model_validate(config)
    selected_observer = observer if observer is not None else parsed.observer_policy
    if not manifests:
        raise ValueError("no prospective captures")
    quotes = []
    frames = {}
    for manifest in manifests:
        verify(manifest)
        metadata = json.loads(manifest.read_text())
        artifact = next(a for a in metadata["artifacts"] if a["path"] == "quote.json")
        row = json.loads((manifest.parent / "quote.json").read_text())
        if row["symbol"] != "BTCUSDT":
            raise ValueError("initial paper scope is BTCUSDT")
        received = int(artifact["received_time_ns"])
        event = int(row["time"]) * 1_000_000
        if event > received:
            raise ValueError("venue clock ahead of local receipt; clock qualification required")
        if Decimal(row["bidPrice"]) > Decimal(row["askPrice"]):
            raise ValueError("crossed quote")
        candles = load_candles(manifest)
        known = tuple(replace(c, available_ns=c.received_ns) for c in candles)
        frames[received] = frame_at("BTCUSDT-PERP.BINANCE", received, known)
        quotes.append(
            QuoteTick(
                InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
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
        metadata = json.loads((manifests[0].parent / "instruments.json").read_text())
        instrument = next(i for i in metadata["symbols"] if i["symbol"] == "BTCUSDT")
        filters = {f["filterType"]: f for f in instrument["filters"]}
        lot = filters["MARKET_LOT_SIZE"]
        strategy = EconomicPaperAdapter(
            frames,
            RiskLimits(
                Decimal(1),
                Decimal(config["max_exposure_fraction"]),
                Decimal(config["max_notional"]),
                0,
            ),
            InstrumentConstraints(
                Decimal(lot["stepSize"]),
                Decimal(lot["minQty"]),
                Decimal(lot["maxQty"]),
                Decimal(filters["MIN_NOTIONAL"]["notional"]),
            ),
            Decimal(config["max_notional"]),
            observer=selected_observer,
            grammar=parsed.grammar_policy,
            campaign_policy=parsed.campaign_policy,
        )
        engine.add_strategy(strategy)
        engine.add_data(quotes)
        engine.run()
        state = economic_state(engine, Venue("BINANCE"), Currency.from_str("USDT"))
        state["quote_count"] = len(quotes)
        state["campaign_status"] = "NO_VERIFIED_CALIBRATION"
        state["economic_decisions"] = strategy.decisions
        state["campaigns"] = [
            c.to_record() for c in strategy.campaigns
        ]
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


def step(run: Path, config: dict[str, str], *, replay_only: bool = False) -> dict[str, Any]:
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


def _step_locked(run: Path, config: dict[str, str], *, replay_only: bool) -> dict[str, Any]:
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
        prior_campaigns = tuple(
            PaperCampaign.from_record(c)
            for c in recovered["campaigns"]
        )
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
                funding_start_ms=int(str(frozen["frozen_ns"])) // 1_000_000,
            )
        )
    if not manifests:
        raise ValueError("no captured session to replay")
    for manifest in manifests:
        observe_capture(run, manifest, frozen)
    state = replay_account(manifests, config)
    campaigns = tuple(
        PaperCampaign.from_record(c) for c in state["campaigns"]
    )
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--maker-fee", type=Decimal, required=True)
    parser.add_argument("--taker-fee", type=Decimal, required=True)
    parser.add_argument("--initial-balance", type=Decimal, required=True)
    parser.add_argument("--max-notional", type=Decimal, required=True)
    parser.add_argument("--max-exposure-fraction", type=Decimal, required=True)
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args()
    config = {
        "maker_fee": str(args.maker_fee),
        "taker_fee": str(args.taker_fee),
        "initial_balance": str(args.initial_balance),
        "max_notional": str(args.max_notional),
        "max_exposure_fraction": str(args.max_exposure_fraction),
    }
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
