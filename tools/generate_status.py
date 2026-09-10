#!/usr/bin/env python3
"""Generate site/status.json + artifacts/status.json for the V8 status app.

Honesty contract (issue #395): NO published metric may be a silent rescale of
another. Capacity and gates come from the benchmark ledger. Readiness is ONLY
published when the real policy certificate artifact provides it; otherwise the
field is absent (never recomputed from cap).
"""

import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ARTIFACTS = ROOT / "artifacts"
BULLETIN = ROOT / "artifacts" / "bulletin.md"
LEDGER = ROOT / "artifacts" / "benchmarks" / "benchmark_ledger.jsonl"
CERT_REPORT = ROOT / "artifacts" / "benchmarks" / "forensic_report.html"
KANBAN_DB = Path.home() / ".hermes" / "kanban" / "boards" / "v8" / "kanban.db"


def _iso(ts):
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def read_bulletin():
    if not BULLETIN.exists():
        return {"raw": "", "last_update": ""}
    txt = BULLETIN.read_text(encoding="utf-8", errors="ignore")
    return {"raw": txt[:6000], "last_update": _iso(BULLETIN.stat().st_mtime)}


def read_ledger():
    """Capacity + gate vector from the append-only benchmark ledger (real, persisted)."""
    out = {"cap": None, "gates": {}, "history": [], "count": 0, "last_entry": ""}
    if not LEDGER.exists():
        return out
    try:
        lines = [ln for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
        history = []
        for line in lines:
            try:
                j = json.loads(line)
                r = j.get("receipt", j)
                cap = r.get("capability_score")
                gates = r.get("gates", {}) or {}
                ts = r.get("computed_at_timestamp_ns") or 0
                history.append({
                    "cap": cap,
                    "gates": gates,
                    "ts": _iso(ts / 1e9) if ts > 1e12 else "",
                    "entry_hash": str(j.get("entry_hash", ""))[:8],
                })
            except Exception:
                continue
        last = history[-1] if history else {}
        out.update({
            "cap": last.get("cap"),
            "gates": last.get("gates", {}),
            "history": history,
            "count": len(lines),
            "last_entry": last.get("entry_hash", ""),
        })
    except Exception as e:
        out["error"] = str(e)
    return out


def read_readiness():
    """Readiness index from the real policy certificate render.

    Returns None-valued fields when the certificate artifact is absent/unparsable.
    Never derives readiness from capacity.
    """
    res: dict[str, object] = {
        "readiness": None,
        "capability": None,
        "robustness": None,
        "source": None,
        "source_mtime": None,
    }
    if not CERT_REPORT.exists():
        return res
    try:
        html = CERT_REPORT.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return res
    m = re.search(r"Readiness\s*Index.*?hero-score\">\s*([0-9]+(?:\.[0-9]+)?)\s*<", html, re.S | re.I)
    if not m:
        return res
    res["readiness"] = float(m.group(1))
    c = re.search(r"Capability:\s*([0-9]+(?:\.[0-9]+)?)\s*\|\s*Robustness:\s*([0-9]+(?:\.[0-9]+)?)", html)
    if c:
        res["capability"] = float(c.group(1))
        res["robustness"] = float(c.group(2))
    res["source"] = str(CERT_REPORT.relative_to(ROOT))
    res["source_mtime"] = _iso(CERT_REPORT.stat().st_mtime)
    return res


def read_kanban():
    if not KANBAN_DB.exists():
        return {"running": [], "ready": [], "blocked": [], "done": 0, "recent_done": []}
    try:
        con = sqlite3.connect(str(KANBAN_DB))
        cur = con.cursor()

        def q(status, lim=5):
            cur.execute(
                "SELECT id, title, datetime(created_at,'localtime') FROM tasks "
                "WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, lim),
            )
            return [{"id": r[0], "title": r[1], "at": r[2]} for r in cur.fetchall()]

        running, ready, blocked = q("running"), q("ready"), q("blocked")
        cur.execute("SELECT count(*) FROM tasks WHERE status='done'")
        done = cur.fetchone()[0]
        cur.execute(
            "SELECT id, title, datetime(completed_at,'localtime') FROM tasks "
            "WHERE status='done' ORDER BY completed_at DESC LIMIT 5"
        )
        recent_done = [{"id": r[0], "title": r[1], "at": r[2]} for r in cur.fetchall()]
        con.close()
        return {"running": running, "ready": ready, "blocked": blocked, "done": done, "recent_done": recent_done}
    except Exception as e:
        return {"running": [], "ready": [], "blocked": [], "done": 0, "error": str(e)}


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ledger = read_ledger()
    readiness = read_readiness()
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bulletin": read_bulletin(),
        "ledger": ledger,
        "readiness": readiness,
        "kanban": read_kanban(),
        "server_status": "up",
        "worker_status": "up" if KANBAN_DB.exists() else "unknown",
    }
    j = json.dumps(data, indent=2, ensure_ascii=False)
    (SITE / "status.json").write_text(j, encoding="utf-8")
    (ARTIFACTS / "status.json").write_text(j, encoding="utf-8")
    src = readiness["source"] or "absent (not published)"
    print(
        f"Wrote status.json | cap={ledger.get('cap')} "
        f"readiness={readiness['readiness']} (source: {src}) "
        f"history={len(ledger.get('history', []))} pts"
    )


if __name__ == "__main__":
    main()
