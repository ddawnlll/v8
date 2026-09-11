#!/usr/bin/env python3
"""Generate site/status.json + artifacts/status.json for the V8 status app.

Honesty contract (issue #395): NO published metric may be a silent rescale of
another. Capacity and gates come from the benchmark ledger. Readiness is ONLY
published when the real policy certificate artifact provides it; otherwise the
field is absent (never recomputed from cap).

Evidence class (#448): capacity/gates are published ONLY from a ledger entry whose
receipt declares an evidential window class (``window_evidence.economic_evidence``).
The class and the refusal are read through the canonical v8-next reader
(``BenchmarkLedger.publication``); this script never re-implements the rule. When no
entry declares the class, ``ledger.cap`` is ``null`` and ``publication_refusal`` names
the entry that was refused -- the recorded number stays in the ledger, it is not
published as capacity. Run it with the v8-next environment
(``uv run --project v8-next python tools/generate_status.py``) so that reader is
importable; without it the script fails closed with a named reason instead of
publishing a number.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ARTIFACTS = ROOT / "artifacts"
BULLETIN = ROOT / "artifacts" / "bulletin.md"
LEDGER = ROOT / "artifacts" / "benchmarks" / "benchmark_ledger.jsonl"
CERT_REPORT = ROOT / "artifacts" / "benchmarks" / "forensic_report.html"
KANBAN_DB = Path.home() / ".hermes" / "kanban" / "boards" / "v8" / "kanban.db"
#: the canonical class-aware ledger reader lives here (#448)
V8_NEXT_SRC = ROOT / "v8-next" / "src"
LEDGER_READER_UNAVAILABLE = "EVIDENCE_CLASS_READER_UNAVAILABLE"


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


def _ledger_reader():
    """The canonical class-aware ledger reader (#448), imported, never re-implemented.

    One source of truth for "which entry may publish a capability score": the rule lives
    in ``v8_next.evaluation.benchmark_receipt`` (``BenchmarkReceipt.
    declares_evidential_window`` / ``BenchmarkLedger.publication``) and the CLI reads the
    ledger through exactly this reader. A second copy of the rule here is what #448 was
    filed against, so there is none.
    """
    if str(V8_NEXT_SRC) not in sys.path:
        sys.path.insert(0, str(V8_NEXT_SRC))
    from v8_next.evaluation.benchmark_receipt import BenchmarkLedger

    return BenchmarkLedger


def _gate_states(receipt):
    return {field: getattr(receipt.gates, field).value for field in receipt.gates.__class__.model_fields}


def read_ledger():
    """Capacity + gate vector from the append-only benchmark ledger (real, persisted).

    #448: the published capacity and gate vector come from the most recent entry that
    declares an evidential window class. With no such entry the fields stay absent and
    ``publication_refusal`` names the entry and class that were refused.
    """
    out = {
        "cap": None,
        "gates": {},
        "history": [],
        "count": 0,
        "last_entry": "",
        "evidence_class": "",
        "publication_refusal": "",
    }
    if not LEDGER.exists():
        return out
    try:
        lines = [ln for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
        out["count"] = len(lines)
        reader = _ledger_reader()
        ledger = reader.load_jsonl(LEDGER)
    except (ImportError, OSError, ValueError) as e:
        # fail closed: without the canonical classifier nothing may be published as
        # capacity, and the reason is named rather than silently re-derived here
        out["error"] = f"{LEDGER_READER_UNAVAILABLE}: {e}"
        out["publication_refusal"] = out["error"]
        return out
    publication = ledger.publication()
    history = []
    for entry in ledger.entries:
        receipt = entry.receipt
        evidential = receipt.declares_evidential_window()
        ts = receipt.computed_at_timestamp_ns or 0
        history.append({
            # ``cap`` is the *published* field: null for an entry that may not publish a
            # number. Whether the entry recorded one is named by a flag, never by the
            # number itself (#448: a recorded value is not a published measurement).
            "cap": receipt.capability_score if evidential else None,
            "records_capability_score": receipt.capability_score is not None,
            "evidence_class": receipt.evidence_class(),
            "gates": _gate_states(receipt) if evidential else {},
            "ts": _iso(ts / 1e9) if ts > 1e12 else "",
            "entry_hash": entry.entry_hash[:8],
        })
    newest = ledger.entries[-1] if ledger.entries else None
    published = publication.entry.receipt if publication.entry is not None else None
    out.update({
        "cap": publication.capability_score,
        "gates": _gate_states(published) if published is not None else {},
        "history": history,
        "count": len(lines),
        "last_entry": "" if newest is None else newest.entry_hash[:8],
        "evidence_class": publication.evidence_class,
        "publication_refusal": publication.refusal_reason,
        "publication": publication.as_dict(),
    })
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
        f"class={ledger.get('evidence_class')} "
        f"readiness={readiness['readiness']} (source: {src}) "
        f"history={len(ledger.get('history', []))} pts"
    )
    if ledger.get("publication_refusal"):
        print(f"[!] capacity withheld: {ledger['publication_refusal']}")


if __name__ == "__main__":
    main()
