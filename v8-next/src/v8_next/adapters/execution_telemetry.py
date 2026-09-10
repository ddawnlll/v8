"""Execution telemetry: turn a Nautilus fills report into measured evidence.

Kept separate from the engine adapters so both the single-instrument D-153
runner and the multi-asset portfolio backtest measure execution the same way
and cannot drift apart.

Honesty rules encoded here:
  * a value that cannot be parsed stays ``None`` -- never a placeholder;
  * non-finite floats (the engine emits ``nan`` slippage on some rows) become
    ``None`` so a receipt stays strictly JSON-serialisable;
  * amounts in different currencies are never summed together;
  * shortfall compares a fill only against the decision of the SAME instrument,
    because comparing legs compares different price scales.
"""

from __future__ import annotations

import re
from typing import Any

from v8_next.adapters.execution_models import ExecutionProfile, profile_summary

#: Fill-report columns that carry execution semantics. The set is intersected
#: with the columns the engine actually emitted, so a Nautilus version that
#: renames a column cannot silently produce an all-identical signature.
SIGNATURE_COLUMNS = (
    "instrument_id",
    "side",
    "quantity",
    "filled_qty",
    "last_px",
    "avg_px",
    "slippage",
    "commissions",
    "liquidity_side",
    "position_id",
    "order_list_id",
    "venue_order_id",
    "trade_id",
    "ts_event",
    "ts_init",
    "ts_last",
)


def as_float(value: Any) -> float | None:
    """Convert a ledger/report value to a finite float, or None. Never guesses."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def json_safe(value: Any) -> Any:
    """JSON-safe scalar: pandas timestamps become epoch ns, non-finite floats None."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    if type(value).__name__ == "Timestamp" and hasattr(value, "value"):
        return int(value.value)
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return str(value)


def money_amounts(value: Any) -> dict[str, float]:
    """Parse Nautilus money values into ``{currency: summed amount}``.

    The fills report carries commissions as ``["0.49407624 USDT"]``; custom fee
    models can surface ``Money(0.5, USDT)`` instead. Both are accepted, and
    amounts in different currencies are never summed together.
    """
    out: dict[str, float] = {}
    if value is None or isinstance(value, bool):
        return out
    if isinstance(value, (list, tuple)):
        for item in value:
            for currency, amount in money_amounts(item).items():
                out[currency] = out.get(currency, 0.0) + amount
        return out
    if isinstance(value, (int, float)):
        if value != value:
            return out
        out[""] = float(value)
        return out
    text = str(value)
    for amount, currency in re.findall(r"([-+]?[0-9]*\.?[0-9]+)\s+([A-Za-z]{2,10})\b", text):
        try:
            parsed = float(amount)
        except ValueError:
            continue
        out[currency.upper()] = out.get(currency.upper(), 0.0) + parsed
    for amount, currency in re.findall(
        r"Money\(\s*([-+]?[0-9]*\.?[0-9]+)\s*,\s*([A-Za-z]{2,10})", text
    ):
        try:
            parsed = float(amount)
        except ValueError:
            continue
        out[currency.upper()] = out.get(currency.upper(), 0.0) + parsed
    return out


def native_fill_records(engine: Any) -> tuple[list[dict[str, Any]], str]:
    """Normalise the engine's order-fills report into JSON-safe records.

    NautilusTrader 2.0.0rc4 returns a pandas DataFrame rather than a declared
    stub type, so the shape is probed at runtime and reported verbatim instead
    of being assumed.
    """
    try:
        report = engine.generate_order_fills_report()
    except Exception as exc:  # pragma: no cover - engine-level failure
        return [], f"UNAVAILABLE:{type(exc).__name__}"
    if report is None:
        return [], "NONE"
    records: list[dict[str, Any]] = []
    try:
        if hasattr(report, "to_dicts"):
            records = [dict(r) for r in report.to_dicts()]
        elif hasattr(report, "to_dict"):
            try:
                raw = report.to_dict("records")
                records = [dict(r) for r in raw]
            except TypeError:
                records = [dict(report.to_dict())]
        elif isinstance(report, (list, tuple)):
            records = [dict(r) for r in report if isinstance(r, dict)]
    except Exception:  # pragma: no cover - defensive
        return [], f"UNPARSABLE:{type(report).__name__}"
    safe = [{str(key): json_safe(value) for key, value in rec.items()} for rec in records]
    return safe, type(report).__name__


def fill_signature(records: list[dict[str, Any]]) -> str:
    """Identity of executed fills: instrument/side/qty/price/cost/time, sorted.

    Price, slippage and commission columns are part of the identity on purpose:
    a signature that ignores them cannot detect that two profiles filled at
    different prices, which is exactly what an execution claim depends on.
    """
    import hashlib as _hl
    import json as _js

    if not records:
        return _hl.sha256(b'{"columns":[],"rows":[]}').hexdigest()
    available = set(records[0])
    pick = [c for c in SIGNATURE_COLUMNS if c in available]
    if not pick:  # unknown schema: fall back to every column, still deterministic
        pick = sorted(available)
    rows = sorted(tuple(str(r.get(k, "")) for k in pick) for r in records)
    payload = _js.dumps({"columns": pick, "rows": rows}, sort_keys=True)
    return _hl.sha256(payload.encode()).hexdigest()


#: A fill and the decision bar that authorised it must describe the same price
#: series. A larger ratio means they do not, so the pair is rejected instead of
#: being averaged into a friction metric.
MAX_REFERENCE_RATIO = 1.5


def execution_telemetry(
    profile: ExecutionProfile,
    fill_records: list[dict[str, Any]],
    fill_report_type: str,
    opened: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure execution quality from fills versus the decision price.

    Implementation shortfall is the signed cost of the fill against the close of
    the decision bar that authorised it: positive means the fill was adverse
    (paid above for a buy, sold below for a sell). Order lifetime comes from the
    engine's own fill rows, because bar execution stamps fills at the bar
    boundary and therefore cannot show modelled order latency.
    """
    # Decisions are matched per instrument: comparing a fill against the last
    # decision of a *different* leg compares BTC against AVAX and yields a
    # nonsense shortfall (observed as -2.4e6 bps before this was fixed).
    per_instrument: dict[str, list[tuple[int, Any]]] = {}
    for d in decisions:
        inst = str(d.get("instrument_id", ""))
        per_instrument.setdefault(inst, []).append(
            (int(d.get("decision_ns", 0) or 0), d.get("close"))
        )
    for rows in per_instrument.values():
        rows.sort(key=lambda r: r[0])

    slippage_bps: list[float] = []
    latencies: list[int] = []
    unmatched = 0
    cross_series = 0
    for pos in opened:
        side = str(pos.get("side", "")).upper()
        fill_px = as_float(pos.get("avg_px_open"))
        if fill_px is None or fill_px <= 0:
            unmatched += 1
            continue
        event_ns = int(pos.get("event_ns", 0) or 0)
        rows = per_instrument.get(str(pos.get("instrument_id", "")), [])
        prior = [r for r in rows if r[0] <= event_ns]
        if not prior:
            unmatched += 1
            continue
        ref_ns, ref_close = prior[-1]
        ref_px = as_float(ref_close)
        if ref_px is None or ref_px <= 0:
            unmatched += 1
            continue
        # A fill and its authorising decision bar must describe the same price
        # series. A ratio outside MAX_REFERENCE_RATIO means they do not -- this
        # happens when a single-instrument configuration is fed a multi-asset
        # tape, which produced a -5.8e7 bps "shortfall" before this guard.
        # Such pairs are rejected and counted, never averaged into the metric.
        if max(fill_px, ref_px) / min(fill_px, ref_px) > MAX_REFERENCE_RATIO:
            cross_series += 1
            continue
        sign = 1.0 if side.startswith("B") else -1.0
        slippage_bps.append(sign * (fill_px - ref_px) / ref_px * 1e4)
        latencies.append(event_ns - ref_ns)

    commission_totals: dict[str, float] = {}
    for rec in fill_records:
        for key in rec:
            if "commission" in key.lower():
                for currency, amount in money_amounts(rec[key]).items():
                    commission_totals[currency] = commission_totals.get(currency, 0.0) + amount

    order_lifetime: list[int] = []
    for rec in fill_records:
        start, end = rec.get("ts_init"), rec.get("ts_last")
        if isinstance(start, int) and isinstance(end, int) and end >= start:
            order_lifetime.append(end - start)

    configured_latency = sum(
        (
            profile.base_latency_nanos,
            profile.insert_latency_nanos,
            profile.update_latency_nanos,
            profile.cancel_latency_nanos,
        )
    )
    block = profile_summary(profile)
    block.update(
        {
            "fill_signature": fill_signature(fill_records),
            "fills_count": len(fill_records),
            "fills_report_type": fill_report_type,
            "slippage_samples": len(slippage_bps),
            "slippage_unmatched_positions": unmatched,
            "slippage_rejected_cross_series": cross_series,
            "slippage_bps_mean": (
                round(sum(slippage_bps) / len(slippage_bps), 6) if slippage_bps else None
            ),
            "slippage_bps_max": round(max(slippage_bps), 6) if slippage_bps else None,
            "slippage_bps_min": round(min(slippage_bps), 6) if slippage_bps else None,
            "decision_to_position_event_ns_mean": (
                int(sum(latencies) / len(latencies)) if latencies else None
            ),
            "decision_to_position_event_ns_max": max(latencies) if latencies else None,
            "order_to_fill_ns_mean": (
                int(sum(order_lifetime) / len(order_lifetime)) if order_lifetime else None
            ),
            "order_to_fill_ns_max": max(order_lifetime) if order_lifetime else None,
            "configured_latency_nanos": configured_latency,
            "latency_observability": (
                "BAR_EXECUTION_STAMPS_FILLS_AT_BAR_TIME"
                if configured_latency > 0 and not any(latencies)
                else "MEASURED_ORDER_LIFETIME"
                if order_lifetime
                else "NOT_OBSERVABLE"
            ),
            "commission_totals_by_currency": {
                cur: round(amt, 10) for cur, amt in sorted(commission_totals.items())
            },
            "commission_total": (
                round(next(iter(commission_totals.values())), 10)
                if len(commission_totals) == 1
                else None
            ),
        }
    )
    return block
