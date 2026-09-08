"""Revalue frozen paper campaigns using only final funding known at the cutoff."""

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from nautilus_trader.model import Currency, InstrumentId, Price, Quantity, QuoteTick, Venue

from v8_next.adapters.binance_capture import verify
from v8_next.adapters.campaign import PaperCampaignAdapter
from v8_next.adapters.engine_state import economic_state
from v8_next.adapters.native_tape import build_engine
from v8_next.adapters.settlements import final_funding, missing_announced_settlements
from v8_next.domain.campaign import PaperCampaign


def replay_frozen_campaigns(
    manifests: list[Path],
    campaigns: tuple[PaperCampaign, ...],
    config: dict[str, str],
    accounting_as_of_ns: int,
) -> dict[str, Any]:
    """No observers, calibration, allocator or economic callbacks run here.

    This is a revised simulated accounting view, not a replacement of historical
    decisions or their knowledge state. It does not establish complete funding
    coverage beyond the final settlement records actually supplied by the venue.
    """
    quotes = []
    for manifest in manifests:
        verify(manifest)
        metadata = json.loads(manifest.read_text())
        artifact = next(a for a in metadata["artifacts"] if a["path"] == "quote.json")
        received = int(artifact["received_time_ns"])
        if received > accounting_as_of_ns:
            continue
        row = json.loads((manifest.parent / "quote.json").read_text())
        if row["symbol"] != "BTCUSDT":
            raise ValueError("unsupported accounting instrument")
        event = int(row["time"]) * 10**6
        if event > received or Decimal(row["bidPrice"]) > Decimal(row["askPrice"]):
            raise ValueError("invalid quote clocks or spread")
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
    if not quotes:
        raise ValueError("no quotes known by accounting cutoff")
    quotes.sort(key=lambda q: q.ts_init)
    if any(
        c.decision_ns < quotes[0].ts_init or c.decision_ns > accounting_as_of_ns for c in campaigns
    ):
        raise ValueError("campaign outside captured accounting window")
    settlements = final_funding(
        manifests, quotes[0].ts_init, accounting_as_of_ns, accounting_as_of_ns
    )
    engine, _ = build_engine(
        manifests[0],
        Decimal(config["maker_fee"]),
        Decimal(config["taker_fee"]),
        Decimal(config["initial_balance"]),
        historical_data=False,
    )
    try:
        engine.add_strategy(PaperCampaignAdapter(campaigns))
        engine.add_data(quotes)
        for settlement in settlements:
            mark, funding = settlement.execution_replay_events(accounting_as_of_ns)
            engine.add_data([mark])
            engine.add_data([funding])
        engine.run()
        result = economic_state(engine, Venue("BINANCE"), Currency.from_str("USDT"))
        result["view"] = "REVISED_SIMULATED_ACCOUNTING_FROZEN_DECISIONS"
        result["accounting_as_of_ns"] = accounting_as_of_ns
        result["settlement_sources"] = [
            {**asdict(s), "rate": str(s.rate), "mark_price": str(s.mark_price)} for s in settlements
        ]
        result["funding_coverage"] = "OBSERVED_FINAL_RECORDS_ONLY_NOT_COMPLETENESS_CERTIFIED"
        missing = missing_announced_settlements(
            manifests, settlements, quotes[0].ts_init, accounting_as_of_ns
        )
        result["missing_announced_settlements"] = list(missing) if missing is not None else None
        if missing:
            result["funding_coverage"] = "INCOMPLETE_ANNOUNCED_SETTLEMENT_MISSING"
        return result
    finally:
        engine.dispose()
