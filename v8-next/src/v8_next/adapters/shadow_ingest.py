"""Shadow / live ingest and reconciliation.

Public funding rows are in the quad tape (see funding_history.quad_funding_summary).
Private venue fills require an authenticated account; absent credentials => UNRUN.

Fixture files are never counted as live fills.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

FIXTURE_MARKERS = ("tests/", "fixtures", "fixture")

# Canonical live path (relative to repo root). Callers may pass an override.
DEFAULT_SHADOW_FILLS = Path("artifacts/shadow_fills.jsonl")


def is_fixture_path(p: Path | str) -> bool:
    s = str(p).replace("\\", "/").lower()
    return any(m.lower() in s for m in FIXTURE_MARKERS)


def load_shadow_fills(
    path: Path | str,
    *,
    source: str = "live",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load and validate shadow fills file.

    Returns (records, meta). Meta contains mode, reason, sha256, validation details.
    Fixture source is never LIVE_VENUE_SETTLED.
    """
    p = Path(path)
    if source == "fixture" or is_fixture_path(p):
        return [], {
            "mode": "FIXTURE_NOT_LIVE",
            "reason": f"fixture path not counted as live: {p}",
            "path": str(p),
            "fixture_guard": True,
        }
    if not p.exists() or p.stat().st_size == 0:
        return [], {
            "mode": "UNRUN_NO_VENUE_ACCOUNT",
            "reason": f"no venue account / no file at {p}",
            "expected_command": (
                "uv run --project v8-next python -m v8_next.adapters.shadow_ingest fetch "
                "--symbol BTCUSDT --out artifacts/shadow_fills.jsonl  # requires BINANCE_API_KEY"
            ),
            "path": str(p),
        }
    content = p.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    lines = [ln for ln in content.decode("utf-8").splitlines() if ln.strip()]
    if not lines:
        return [], {"mode": "UNRUN_NO_VENUE_ACCOUNT", "reason": "empty fills file", "path": str(p), "sha256": sha}
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for i, ln in enumerate(lines):
        rec_errors: list[str] = []
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: json error {e}")
            continue
        # Minimal schema check; presence of fill_id + instrument + price + qty
        if not isinstance(rec, dict):
            errors.append(f"line {i}: not an object")
            continue
        for k in ("fill_id", "instrument", "price", "qty"):
            if k not in rec:
                rec_errors.append(f"line {i}: missing {k}")
        # Type sanity (price/qty finite)
        try:
            price = float(rec.get("price", 0))
            qty = float(str(rec.get("qty", 0)))
            if not (price > 0 and qty > 0):
                rec_errors.append(f"line {i}: nonpositive price/qty")
        except (ValueError, TypeError):
            rec_errors.append(f"line {i}: bad price/qty type")
            continue
        if rec_errors:
            errors.extend(rec_errors)
        elif rec.get("fill_id") and rec.get("instrument"):
            records.append(rec)
    if errors and not records:
        return [], {"mode": "MALFORMED_SHADOW_FILE", "reason": "; ".join(errors[:3]), "path": str(p), "sha256": sha}
    # At least one well-formed record required for live
    valid = [r for r in records if all(k in r for k in ("fill_id", "instrument", "price", "qty"))]
    if not valid:
        return [], {"mode": "UNRUN_NO_VENUE_ACCOUNT", "reason": "no valid fill records", "path": str(p), "sha256": sha, "errors": errors}
    return valid, {"mode": "LIVE_VENUE_SETTLED", "fills_count": len(valid), "path": str(p), "sha256": sha, "errors": errors[:5]}


def ingest_status(
    path: Path | str | None = None,
    *,
    source: str = "live",
) -> dict[str, Any]:
    """Return ingest status dict without raising. Used by G8 and CLI."""
    p = Path(path) if path is not None else DEFAULT_SHADOW_FILLS
    if source == "fixture" or is_fixture_path(p):
        return {
            "mode": "FIXTURE_NOT_LIVE",
            "status": "FIXTURE_NOT_LIVE",
            "reason": "fixture not counted as live",
            "path": str(p),
            "fixture_guard": True,
            "format": "jsonl per docs/contracts/SHADOW_LIVE_DATA_SPEC.md",
            "source": "venue private REST GET /fapi/v1/userTrades (requires BINANCE_API_KEY)",
            "command": "uv run --project v8-next python -m v8_next.adapters.shadow_ingest fetch --symbol BTCUSDT --out artifacts/shadow_fills.jsonl",
        }
    if not p.exists() or p.stat().st_size == 0:
        return {
            "mode": "UNRUN_NO_VENUE_ACCOUNT",
            "status": "UNRUN_NO_VENUE_ACCOUNT",
            "reason": "no venue account / no file",
            "path": str(p),
            "format": "jsonl per docs/contracts/SHADOW_LIVE_DATA_SPEC.md",
            "source": "venue private REST GET /fapi/v1/userTrades (requires BINANCE_API_KEY)",
            "command": "uv run --project v8-next python -m v8_next.adapters.shadow_ingest fetch --symbol BTCUSDT --out artifacts/shadow_fills.jsonl",
            "funding_note": "public funding is in research/tape/quad-1h-12m/tape.jsonl (channel=funding); see funding_history.quad_funding_summary",
        }
    _, meta = load_shadow_fills(p, source=source)
    return {**meta, "status": meta.get("mode"), "format": "jsonl per docs/contracts/SHADOW_LIVE_DATA_SPEC.md",
            "source": "venue private REST GET /fapi/v1/userTrades", "command": "uv run --project v8-next python -m v8_next.adapters.shadow_ingest verify --fills artifacts/shadow_fills.jsonl"}


def reconcile_shadow_account(
    fills: list[dict[str, Any]],
    account: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare shadow fills against engine AccountState (economic_state).

    Returns comparison dict; raises only on programmatic misuse, otherwise returns
    a status field. No fixture is ever reconciled as PASS.
    """
    if account is None:
        return {"reconciled": False, "reason": "NO_ACCOUNT_SNAPSHOT", "mode": "UNRUN_NO_VENUE_ACCOUNT"}
    # Basic reconciliation: count and notional sanity vs orders/positions
    # AccountState has keys: balance_total, positions, orders
    required = {"balance_total", "positions", "orders"}
    if not required <= set(account.keys()):
        return {"reconciled": False, "reason": "ACCOUNT_INPUTS_UNAVAILABLE", "account_keys": sorted(account.keys())}
    # Derive engine fill count: orders with FILLED
    engine_fills = [o for o in account.get("orders", []) if o.get("status") == "FILLED"]
    shadow_count = len(fills)
    engine_count = len(engine_fills)
    # A non-empty shadow file is not evidence of reconciliation.  Counts must
    # close exactly; otherwise the execution remains unproven and no P&L claim
    # is emitted.  The previous ``or shadow_count > 0`` path treated any
    # captured fill as reconciled even when the native account had zero fills.
    matched = shadow_count == engine_count
    return {
        "reconciled": matched,
        "status": "RECONCILED_DIAGNOSTIC" if matched else "EXECUTION_UNPROVEN",
        "shadow_fills": shadow_count,
        "engine_filled_orders": engine_count,
        "account_currency": account.get("currency"),
        "note": (
            "shadow and native fill counts match; venue cash settlement and monetary parity remain unproven"
            if matched
            else "shadow/native fill counts diverge; venue execution remains unproven"
        ),
        "claim_status": "NO_ECONOMIC_CLAIM",
    }


def decompose_fill_shortfall(fills: list[dict[str, Any]]) -> dict[str, Any]:
    """Decompose only physically supplied fill marks; missing pieces stay absent.

    Records may carry ``model_price``, ``reference_mid``, ``side_sign`` and
    ``fee``.  The loader intentionally accepts older minimal capture rows for
    compatibility, but those rows cannot produce a fabricated zero shortfall.
    """
    if not fills:
        return {
            "status": "DATA_BLOCKED",
            "model_vs_fill": None,
            "adverse_selection": None,
            "fees": None,
            "claim_status": "NO_ECONOMIC_CLAIM",
        }
    model_drag = 0.0
    adverse = 0.0
    fees = 0.0
    model_available = True
    mid_available = True
    fee_available = True
    for row in fills:
        qty = float(row["qty"])
        price = float(row["price"])
        side = float(row.get("side_sign", 1.0))
        if side not in {-1.0, 1.0} or qty <= 0 or not all(
            math.isfinite(value) for value in (qty, price, side)
        ):
            raise ValueError("invalid fill shortfall inputs")
        if row.get("model_price") is None:
            model_available = False
        else:
            model_drag += (price - float(row["model_price"])) * qty * side
        if row.get("reference_mid") is None:
            mid_available = False
        else:
            adverse += (price - float(row["reference_mid"])) * qty * side
        if row.get("fee") is None:
            fee_available = False
        else:
            fees += float(row["fee"])
    return {
        "status": "NO_ECONOMIC_CLAIM",
        "model_vs_fill": model_drag if model_available else None,
        "adverse_selection": adverse if mid_available else None,
        "fees": fees if fee_available else None,
        "claim_status": "NO_ECONOMIC_CLAIM",
    }


def summarize_fill_latency(fills: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize latency only when submit and venue timestamps are captured.

    ``venue_time_ns`` is the settlement-side timestamp from the live-fill
    contract.  A separate ``submit_time_ns`` is required; elapsed wall time
    cannot be reconstructed from venue fills alone.
    """
    latencies_ms: list[float] = []
    for row in fills:
        submit_ns = row.get("submit_time_ns")
        venue_ns = row.get("venue_time_ns")
        if submit_ns is None or venue_ns is None:
            return {
                "status": "DATA_BLOCKED",
                "samples": len(latencies_ms),
                "latency_ms": None,
                "claim_status": "NO_ECONOMIC_CLAIM",
                "reason": "submit_time_ns and venue_time_ns are required",
            }
        try:
            submit = float(submit_ns)
            venue = float(venue_ns)
        except (TypeError, ValueError):
            return {
                "status": "MALFORMED_LATENCY_EVIDENCE",
                "samples": len(latencies_ms),
                "latency_ms": None,
                "claim_status": "NO_ECONOMIC_CLAIM",
                "reason": "latency timestamps must be numeric",
            }
        latency_ms = (venue - submit) / 1_000_000.0
        if not math.isfinite(latency_ms) or latency_ms < 0:
            return {
                "status": "MALFORMED_LATENCY_EVIDENCE",
                "samples": len(latencies_ms),
                "latency_ms": None,
                "claim_status": "NO_ECONOMIC_CLAIM",
                "reason": "venue timestamp precedes submit timestamp",
            }
        latencies_ms.append(latency_ms)
    if not latencies_ms:
        return {
            "status": "DATA_BLOCKED",
            "samples": 0,
            "latency_ms": None,
            "claim_status": "NO_ECONOMIC_CLAIM",
            "reason": "no venue fills",
        }
    ordered = sorted(latencies_ms)
    midpoint = len(ordered) // 2
    median = ordered[midpoint] if len(ordered) % 2 else (ordered[midpoint - 1] + ordered[midpoint]) / 2
    return {
        "status": "OBSERVED_DIAGNOSTIC",
        "samples": len(ordered),
        "latency_ms": {
            "mean": sum(ordered) / len(ordered),
            "median": median,
            "min": ordered[0],
            "max": ordered[-1],
        },
        "claim_status": "NO_ECONOMIC_CLAIM",
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Shadow ingest helper")
    sub = ap.add_subparsers(dest="cmd")
    p_fetch = sub.add_parser("fetch", help="fetch venue fills (requires BINANCE_API_KEY)")
    p_fetch.add_argument("--symbol", required=True)
    p_fetch.add_argument("--out", type=Path, default=DEFAULT_SHADOW_FILLS)
    p_fetch.add_argument("--start-ms", type=int, default=None)
    p_fetch.add_argument("--end-ms", type=int, default=None)

    p_verify = sub.add_parser("verify", help="verify local shadow file")
    p_verify.add_argument("--fills", type=Path, default=DEFAULT_SHADOW_FILLS)
    p_verify.add_argument("--check-account", type=Path, default=None)

    p_check = sub.add_parser("check", help="ingest status")
    p_check.add_argument("path", nargs="?", type=Path, default=DEFAULT_SHADOW_FILLS)

    args = ap.parse_args()
    if args.cmd == "fetch":
        import os

        if not os.environ.get("BINANCE_API_KEY"):
            print(json.dumps({"mode": "UNRUN_NO_VENUE_ACCOUNT", "reason": "BINANCE_API_KEY not set", "path": str(args.out)}, indent=2))
            raise SystemExit(2)
        # Real fetch would call private REST here; stub documents the requirement
        print(json.dumps({"error": "private fetch requires venue credentials; documented in docs/contracts/SHADOW_LIVE_DATA_SPEC.md"}, indent=2))
        raise SystemExit(2)
    elif args.cmd == "verify":
        fills, meta = load_shadow_fills(args.fills)
        print(json.dumps(meta, indent=2))
        if args.check_account and args.check_account.exists():
            acct = json.loads(args.check_account.read_text())
            print(json.dumps(reconcile_shadow_account(fills, acct), indent=2))
        raise SystemExit(0 if meta.get("mode") == "LIVE_VENUE_SETTLED" else 1)
    else:
        status = ingest_status(getattr(args, "path", DEFAULT_SHADOW_FILLS))
        print(json.dumps(status, indent=2))
        raise SystemExit(0)


if __name__ == "__main__":
    main()
