"""Receipt-qualified warmup observations triggered by native quotes."""

import hashlib
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from v8_next.adapters.captured_market import load_candles
from v8_next.domain.market import Candle, frame_at
from v8_next.economics.grammar import POLICIES, grammar_opportunity
from v8_next.evaluation.store import canonical
from v8_next.experts.catalog import observe_all


class StreamObservations:
    def __init__(self, manifests: tuple[Path, ...], grammar: str) -> None:
        if grammar not in POLICIES:
            raise ValueError("unknown stream grammar")
        self.grammar = grammar
        self.candles: dict[str, tuple[Candle, ...]] = {}
        self.source_hashes = sorted(hashlib.sha256(p.read_bytes()).hexdigest() for p in manifests)
        self.emitted: set[tuple[str, str, int | None]] = set()
        for path in manifests:
            bars = load_candles(path)
            if not bars or bars[0].instrument_id in self.candles:
                raise ValueError("empty or duplicate stream warmup instrument")
            self.candles[bars[0].instrument_id] = tuple(
                replace(c, available_ns=c.received_ns) for c in bars
            )

    def add_closed_candle(self, candle: Candle) -> bool:
        """Caller supplies a verified closed-bar source; never infer close from a quote."""
        hour = 3600 * 10**9
        if (
            candle.end_ns - candle.start_ns != hour
            or candle.start_ns % hour != 0
            or candle.available_ns != candle.received_ns
            or candle.received_ns < candle.end_ns
            or not candle.source_hash
        ):
            raise ValueError("unqualified live closed candle")
        previous = self.candles.get(candle.instrument_id, ())
        for existing in previous:
            if existing.start_ns == candle.start_ns:
                fields = ("end_ns", "open", "high", "low", "close", "volume")
                if any(getattr(existing, key) != getattr(candle, key) for key in fields):
                    raise ValueError("live candle revision requires explicit policy")
                return False  # Keep the original receipt/availability on reconnect replay.
        if previous and candle.start_ns != previous[-1].end_ns:
            raise ValueError("live candle gap or backwards update")
        self.candles[candle.instrument_id] = (*previous, candle)
        return True

    def observe(self, instrument: str, received_ns: int) -> dict[str, Any] | None:
        frame = frame_at(instrument, received_ns, self.candles.get(instrument, ()))
        status = "READY"
        if not frame.candles:
            status = "WARMUP_UNAVAILABLE"
        elif not frame.continuous:
            status = "WARMUP_GAP"
        elif received_ns >= frame.candles[-1].end_ns + 3600 * 10**9:
            status = "NEXT_CLOSED_BAR_REQUIRED"
        latest_end = frame.candles[-1].end_ns if frame.candles else None
        key = (instrument, status, latest_end)
        if key in self.emitted:
            return None
        opportunity = grammar_opportunity(frame, self.grammar) if status == "READY" else None
        stances = observe_all(frame, opportunity) if status == "READY" else ()
        result = dict(
            instrument_id=instrument,
            decision_ns=received_ns,
            warmup_status=status,
            grammar=self.grammar,
            latest_closed_bar_ns=latest_end,
            candle_source_hashes=sorted({c.source_hash for c in frame.candles}),
            capture_manifest_hashes=self.source_hashes,
            opportunity=asdict(opportunity) if opportunity else None,
            stances=[asdict(s) for s in stances],
            claim_status="NO_ECONOMIC_CLAIM",
            admission_status="UNVERIFIED_CALIBRATION",
            scope="STREAM_WARMUP_OBSERVATION_NOT_EXECUTION",
        )
        # Ensure serializability before marking emitted.
        canonical(result)
        self.emitted.add(key)
        return result
