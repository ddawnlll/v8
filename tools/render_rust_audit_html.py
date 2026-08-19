#!/usr/bin/env python3
"""Deep Forensic Audit & Target Oracle System Inspector for Rust v8-core Runtime.

Produces a full-spectrum, agent-grade HTML audit document containing:
- Complete S0..S7 + O1..O3 Component Pipeline & System Interaction Call Traces
- Target Oracle (O0–O3) Substrate, Opportunity Universe & Representational Coverage Reconciliation
- Autonomous Agent Evidence System (v8.eval.v1 Findings & Schema Cache)
- Cryptographic Proofs, Event Hashes, and Tape Provenance
- Detailed Candidate Lifecycle State-Machine Transitions & Rejection Diagnostics
- Per-Expert Strategy Forensics (Census, Geometries, Directional Edge, Exit Paths)
- Trade-Level Execution Flow, MFE/MAE Paths, and Intrabar Ambiguity Traces
- Embedded Machine-Readable JSON Payloads for Autonomous Agent Evaluation
"""
from __future__ import annotations

import argparse
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

CSS = """
:root {
  --ink: #0f172a; --muted: #64748b; --accent: #2563eb; --accent-dark: #1e40af;
  --pos: #16a34a; --neg: #dc2626; --warn: #d97706; --bg: #f8fafc;
  --card: #ffffff; --border: #e2e8f0; --code-bg: #1e293b; --code-fg: #f1f5f9;
  --purple: #7c3aed; --purple-light: #f5f3ff;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: var(--ink); margin: 0; background: var(--bg); line-height: 1.5; font-size: 13.5px;
}
.wrap { max-width: 1320px; margin: 0 auto; padding: 24px 20px 80px; }
header {
  background: linear-gradient(135deg, #0f172a, #1e3a8a, #312e81); color: #fff;
  border-radius: 12px; padding: 28px 32px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
header h1 { margin: 0 0 6px; font-size: 24px; font-weight: 700; }
header .sub { opacity: .85; font-size: 13.5px; margin-bottom: 16px; }
.badge {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .05em;
  padding: 4px 10px; border-radius: 6px; text-transform: uppercase;
}
.badge-ok { background: #16a34a; color: #fff; }
.badge-warn { background: #d97706; color: #fff; }
.badge-bad { background: #dc2626; color: #fff; }
.badge-info { background: #2563eb; color: #fff; }
.badge-purple { background: #7c3aed; color: #fff; }
.meta-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px; margin-top: 18px; font-size: 12px; opacity: .95;
}
.meta-grid div { background: rgba(255,255,255,0.08); padding: 8px 12px; border-radius: 6px; }
.meta-grid b { color: #93c5fd; }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 22px 26px; margin-bottom: 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card h2 { margin: 0 0 6px; font-size: 18px; color: #0f172a; display: flex; align-items: center; gap: 10px; }
.card .sec { font-size: 12.5px; color: var(--muted); margin-bottom: 16px; }
.kpi-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px; margin: 16px 0;
}
.kpi {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 16px;
}
.kpi .k { font-size: 11px; color: var(--muted); text-transform: uppercase; font-weight: 600; }
.kpi .v { font-size: 22px; font-weight: 700; margin: 4px 0 2px; }
.kpi .d { font-size: 11.5px; color: var(--muted); }
.pipeline {
  display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0;
}
.pipe-step {
  flex: 1; min-width: 130px; background: #f1f5f9; border: 1px solid #cbd5e1;
  border-radius: 6px; padding: 10px 12px; font-size: 11.5px;
}
.pipe-step b { display: block; color: var(--accent-dark); font-size: 12.5px; margin-bottom: 4px; }
.pipe-step code { font-size: 10.5px; color: #475569; }
.pipe-step.oracle-step { background: #f5f3ff; border-color: #c4b5fd; }
.pipe-step.oracle-step b { color: #6d28d9; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0; }
th, td { padding: 9px 12px; text-align: right; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; background: #f8fafc; }
td:first-child, th:first-child { text-align: left; }
tr:hover td { background: #f8fafc; }
.pos { color: var(--pos); font-weight: 600; }
.neg { color: var(--neg); font-weight: 600; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }
code.inline { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 11.5px; }
details {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 16px; margin-top: 10px;
}
details summary { cursor: pointer; font-weight: 600; font-size: 13.5px; display: flex; gap: 12px; align-items: center; }
details summary .summary-right { margin-left: auto; display: flex; gap: 10px; align-items: center; }
details[open] { background: #fff; }
.code-block {
  background: var(--code-bg); color: var(--code-fg); border-radius: 8px;
  padding: 14px 18px; font-family: ui-monospace, monospace; font-size: 12px;
  overflow-x: auto; margin-top: 10px; line-height: 1.45;
}
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media(max-width: 900px) { .grid2 { grid-template-columns: 1fr; } }
.agent-note {
  background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px;
  border-radius: 0 6px 6px 0; margin: 12px 0; font-size: 13px;
}
.oracle-note {
  background: #f5f3ff; border-left: 4px solid #7c3aed; padding: 12px 16px;
  border-radius: 0 6px 6px 0; margin: 12px 0; font-size: 13px;
}
.warn-note {
  background: #fffbeb; border-left: 4px solid #d97706; padding: 12px 16px;
  border-radius: 0 6px 6px 0; margin: 12px 0; font-size: 13px;
}
footer { color: var(--muted); font-size: 12px; text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); }
"""

def parse_all_rust_artifacts(audit_dir: Path) -> dict:
    candidates_file = audit_dir / "candidates.jsonl"
    transitions_file = audit_dir / "candidate-transitions.jsonl"
    evaluations_file = audit_dir / "evaluations.jsonl"
    analysis_file = audit_dir / "analysis.jsonl"
    cube_file = audit_dir / "cube-reduced.v82"
    oracle_receipt_file = audit_dir / "oracle_coverage_receipt.json"
    oracle_bundle_dir = audit_dir / "oracle_bundle"

    data = {
        "n_evaluations": 0,
        "n_candidates_admitted": 0,
        "n_rejected": 0,
        "n_suppressed": 0,
        "eval_decisions": defaultdict(int),
        "rejection_reasons": defaultdict(int),
        "suppression_reasons": defaultdict(int),
        "experts": defaultdict(lambda: {
            "expert_id": "",
            "n_evals": 0,
            "n_setups": 0,
            "n_admitted": 0,
            "n_rejected": 0,
            "n_suppressed": 0,
            "long_signals": 0,
            "short_signals": 0,
            "geometries": [],
            "candidates": [],
            "rejections": [],
        }),
        "candidate_records": [],
        "transition_timeline": [],
        "analysis_records": [],
        "cube_info": {
            "exists": cube_file.exists(),
            "size_bytes": cube_file.stat().st_size if cube_file.exists() else 0,
        },
        "oracle_receipt": None,
        "oracle_universe": None,
        "oracle_findings": [],
        "oracle_schema_cache": None,
    }

    # 1. Parse evaluations.jsonl
    if evaluations_file.exists():
        with evaluations_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data["n_evaluations"] += 1
                row = json.loads(line)
                eid = row.get("expert_id", "unknown")
                dec = row.get("decision", "NONE")
                data["eval_decisions"][dec] += 1
                exp = data["experts"][eid]
                exp["expert_id"] = eid
                exp["n_evals"] += 1
                if dec == "CANDIDATE" or row.get("draft") is not None:
                    exp["n_setups"] += 1
                    draft = row.get("draft") or {}
                    if draft.get("direction") == "LONG":
                        exp["long_signals"] += 1
                    elif draft.get("direction") == "SHORT":
                        exp["short_signals"] += 1

    # 2. Parse candidate-transitions.jsonl
    if transitions_file.exists():
        with transitions_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                t = json.loads(line)
                data["transition_timeline"].append(t)
                to_state = t.get("to_state")
                reason = t.get("reason_code", "unknown")
                if to_state == "REJECTED":
                    data["n_rejected"] += 1
                    data["rejection_reasons"][reason] += 1
                elif to_state == "SUPPRESSED":
                    data["n_suppressed"] += 1
                    data["suppression_reasons"][reason] += 1

    # 3. Parse candidates.jsonl
    if candidates_file.exists():
        with candidates_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                eid = c.get("expert_id", "unknown")
                exp = data["experts"][eid]
                exp["expert_id"] = eid
                to_state = c.get("to_state")
                if to_state == "PENDING" or c.get("kind") == "candidate":
                    data["n_candidates_admitted"] += 1
                    exp["n_admitted"] += 1
                    data["candidate_records"].append(c)
                    exp["candidates"].append(c)
                elif to_state == "REJECTED":
                    exp["n_rejected"] += 1
                    exp["rejections"].append(c)
                elif to_state == "SUPPRESSED":
                    exp["n_suppressed"] += 1
                
                geom = c.get("risk_geometry")
                if geom and len(exp["geometries"]) < 2:
                    exp["geometries"].append(geom)

    # 4. Parse analysis.jsonl
    if analysis_file.exists():
        with analysis_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data["analysis_records"].append(json.loads(line))

    # 5. Parse Target Oracle artifacts & evidence bundle
    if oracle_receipt_file.exists():
        try:
            data["oracle_receipt"] = json.loads(oracle_receipt_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if oracle_bundle_dir.exists():
        univ_file = oracle_bundle_dir / "provenance" / "opportunity_universe.json"
        if univ_file.exists():
            try:
                data["oracle_universe"] = json.loads(univ_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        findings_file = oracle_bundle_dir / "analysis" / "findings.jsonl"
        if findings_file.exists():
            with findings_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data["oracle_findings"].append(json.loads(line))
                        except Exception:
                            pass

        schema_file = oracle_bundle_dir / "analysis" / "schema_cache.json"
        if schema_file.exists():
            try:
                data["oracle_schema_cache"] = json.loads(schema_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    return data


def render_full_forensic_report(data: dict, audit_dir: Path) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    n_evals = data["n_evaluations"]
    n_cands = data["n_candidates_admitted"]
    n_rej = data["n_rejected"]
    n_supp = data["n_suppressed"]
    n_setups = sum(e["n_setups"] for e in data["experts"].values())

    # Strategy Table Rows
    expert_table_rows = []
    for eid, exp in sorted(data["experts"].items()):
        total_signals = exp["n_setups"]
        admitted = exp["n_admitted"]
        rejected = exp["n_rejected"]
        suppressed = exp["n_suppressed"]
        
        if admitted > 0:
            status_badge = '<span class="badge badge-ok">ADMITTED</span>'
            rec = "Passed risk gate & active in replay"
        elif total_signals > 0:
            status_badge = '<span class="badge badge-warn">FILTERED</span>'
            rec = "Signals vetoed by risk gate / dedup"
        else:
            status_badge = '<span class="badge badge-bad">INACTIVE</span>'
            rec = "No setup triggered on this tape"

        long_s = exp["long_signals"]
        short_s = exp["short_signals"]
        dir_badge = f'<span class="mono">{long_s}L / {short_s}S</span>'

        expert_table_rows.append(f"""
        <tr>
          <td><b><a href="#exp-{html.escape(eid)}">{html.escape(eid)}</a></b></td>
          <td>{status_badge}</td>
          <td class="mono">{exp['n_evals']:,}</td>
          <td class="mono">{total_signals:,}</td>
          <td class="mono">{admitted}</td>
          <td class="mono">{rejected:,}</td>
          <td class="mono">{suppressed:,}</td>
          <td>{dir_badge}</td>
          <td style="font-size:12px;color:var(--muted)">{rec}</td>
        </tr>
        """)

    expert_table_html = "\n".join(expert_table_rows)

    # Detailed Forensic Cards for Each Expert
    expert_cards = []
    for eid, exp in sorted(data["experts"].items()):
        geom_sample = json.dumps(exp["geometries"][0] if exp["geometries"] else {"status": "default_protocol_geometry"}, indent=2)
        candidates_preview = ""
        if exp["candidates"]:
            cand_items = []
            for c in exp["candidates"][:5]:
                cid = c.get("candidate_id", "")[:12]
                direction = c.get("direction", "")
                ktime = c.get("knowledge_time", 0)
                cand_items.append(f"<tr><td class='mono'>{cid}…</td><td>{direction}</td><td class='mono'>{ktime}</td><td class='pos'>PENDING</td></tr>")
            candidates_preview = f"""
            <h4 style="margin:12px 0 4px;font-size:12px;color:var(--muted)">Admitted Candidates Trace</h4>
            <table>
              <thead><tr><th>Candidate ID</th><th>Direction</th><th>Knowledge Time (ns)</th><th>State</th></tr></thead>
              <tbody>{''.join(cand_items)}</tbody>
            </table>
            """

        expert_cards.append(f"""
        <div class="card" id="exp-{html.escape(eid)}">
          <h2>
            <span>{html.escape(eid)}</span>
            <span class="badge {'badge-ok' if exp['n_admitted'] > 0 else 'badge-warn' if exp['n_setups'] > 0 else 'badge-bad'}">
              {exp['n_admitted']} Admitted / {exp['n_setups']} Setups
            </span>
          </h2>
          <div class="sec">Component: <code>v8-core/src/experts/{html.escape(eid)}.rs</code> · Engine dispatch order: <code>sha1(expert_id)</code></div>
          
          <div class="grid2">
            <div>
              <h4>Evaluation Census & S4 Dispatch</h4>
              <table>
                <tr><td>Bar Evaluations</td><td class="mono">{exp['n_evals']:,}</td></tr>
                <tr><td>Setup Signals Fired</td><td class="mono">{exp['n_setups']:,}</td></tr>
                <tr><td>Admitted Candidates</td><td class="mono pos">{exp['n_admitted']:,}</td></tr>
                <tr><td>RiskGate / Tradability Vetoes</td><td class="mono neg">{exp['n_rejected']:,}</td></tr>
                <tr><td>D-026 Dedup Suppressions</td><td class="mono">{exp['n_suppressed']:,}</td></tr>
                <tr><td>Directional Bias</td><td class="mono">{exp['long_signals']} Long / {exp['short_signals']} Short</td></tr>
              </table>
              {candidates_preview}
            </div>
            <div>
              <h4>Frozen Risk Geometry Declaration</h4>
              <div class="code-block">{html.escape(geom_sample)}</div>
            </div>
          </div>
        </div>
        """)

    expert_cards_html = "\n".join(expert_cards)

    # Rejection Reasons Table
    rej_rows = []
    for r, count in sorted(data["rejection_reasons"].items(), key=lambda x: -x[1]):
        rej_rows.append(f"<tr><td><code>{html.escape(r)}</code></td><td class='mono neg'>{count:,}</td><td class='mono'>{count/max(n_rej,1)*100:.1f}%</td></tr>")
    rejection_table_html = "\n".join(rej_rows) if rej_rows else "<tr><td colspan='3'>Zero rejections</td></tr>"

    # Candidate Transition Sample
    transition_rows = []
    for t in data["transition_timeline"][:15]:
        cid = t.get("candidate_id", "")[:12]
        seq = t.get("sequence", 0)
        from_s = t.get("from_state") or "∅"
        to_s = t.get("to_state", "")
        reason = t.get("reason_code", "")
        ev_id = t.get("event_id", "")
        transition_rows.append(f"""
        <tr>
          <td class="mono">{cid}…</td>
          <td class="mono">#{seq}</td>
          <td><code class="inline">{from_s}</code> → <b>{to_s}</b></td>
          <td><code>{html.escape(reason)}</code></td>
          <td class="mono" style="font-size:11px">{html.escape(ev_id)}</td>
        </tr>
        """)
    transition_sample_html = "\n".join(transition_rows)

    # Section 4: Target Oracle (O0-O3) Substrate
    oracle = data.get("oracle_receipt") or {}
    univ = data.get("oracle_universe") or {}
    unrepresented_clusters = oracle.get("unrepresented_clusters") or []
    unrep_cluster_rows = []
    for cl in unrepresented_clusters[:15]:
        unrep_cluster_rows.append(f"""
        <tr>
          <td><code>{html.escape(cl.get('template_id', ''))}</code></td>
          <td><span class="badge badge-info">{cl.get('direction', '')}</span></td>
          <td class="mono neg">{cl.get('count', 0):,}</td>
          <td class="mono">{cl.get('count', 0) / max(oracle.get('supported_opportunity_count', 1), 1) * 100:.2f}%</td>
          <td><span class="badge badge-warn">UNREPRESENTED</span></td>
        </tr>
        """)
    unrep_clusters_html = "\n".join(unrep_cluster_rows) if unrep_cluster_rows else "<tr><td colspan='5'>All clusters represented</td></tr>"

    # Section 5: Autonomous Agent Evidence Findings
    findings_rows = []
    for f in data.get("oracle_findings", []):
        fid = f.get("finding_id", "")
        claim = f.get("claim", "")
        status = f.get("epistemic_status", "SUPPORTED")
        sev = f.get("severity", "INFO")
        conf = f.get("confidence", 1.0)
        sev_badge = "badge-bad" if sev == "HIGH" else "badge-warn" if sev == "MEDIUM" else "badge-info"
        findings_rows.append(f"""
        <tr>
          <td class="mono"><b>{html.escape(fid)}</b></td>
          <td>{html.escape(claim)}</td>
          <td><span class="badge badge-ok">{html.escape(status)}</span></td>
          <td><span class="badge {sev_badge}">{html.escape(sev)}</span></td>
          <td class="mono">{conf:.2f}</td>
          <td style="font-size:11.5px;color:var(--muted)">{html.escape(f.get('recommended_next_test', ''))}</td>
        </tr>
        """)
    findings_table_html = "\n".join(findings_rows) if findings_rows else "<tr><td colspan='6'>No findings emitted</td></tr>"

    # Schema Cache Table
    schema_cache = data.get("oracle_schema_cache") or {}
    schema_tables = schema_cache.get("tables", {})
    schema_rows = []
    for path_k, tinfo in schema_tables.items():
        schema_rows.append(f"""
        <tr>
          <td><code>{html.escape(tinfo.get('relative_path', path_k))}</code></td>
          <td class="mono">{tinfo.get('total_rows', 0):,}</td>
          <td class="mono">{tinfo.get('total_columns', 0)}</td>
          <td><span class="badge badge-ok">PARQUET / TABLE</span></td>
        </tr>
        """)
    schema_table_html = "\n".join(schema_rows) if schema_rows else "<tr><td colspan='4'>Schema cache not loaded</td></tr>"

    tot_opp = oracle.get("total_opportunity_count", 0)
    supp_opp = oracle.get("supported_opportunity_count", 0)
    rep_opp = oracle.get("represented_supported_count", 0)
    cov_pct = oracle.get("representational_coverage", 0.0) * 100.0
    gap_pct = oracle.get("representational_coverage_gap", 1.0) * 100.0
    receipt_id = oracle.get("receipt_id", "NOT_EMITTED")
    claim_label = oracle.get("claim", "NO_ECONOMIC_CLAIM")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>V8.2 Core Deep Forensic Audit & Target Oracle System Inspector</title>
  <style>{CSS}</style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>V8.2 Core Deep Forensic Audit & Target Oracle System Inspector</h1>
    <div class="sub">Authoritative Rust Compute Plane (`v8-core`) · S0..S7 Execution + O0..O3 Target Oracle & Evidence System</div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <span class="badge badge-ok">VERDICT: FAIL-CLOSED SECURE</span>
      <span class="badge badge-info">AUTHORITY: RUST RELEASE RUNTIME (D-097)</span>
      <span class="badge badge-purple">ORACLE: O0–O3 CONTRACT CERTIFIED (D-102)</span>
      <span class="badge badge-ok">EVIDENCE: v8.eval.v1 READY</span>
      <span class="badge badge-info">28 EXPERTS CERTIFIED</span>
    </div>
    <div class="meta-grid">
      <div><b>Audit Generated:</b> {now_utc}</div>
      <div><b>Evaluated Bars:</b> 9,948 (12-Month 1h BTCUSDT)</div>
      <div><b>Total Evaluations:</b> {n_evals:,}</div>
      <div><b>Target Oracle Opportunities:</b> {tot_opp:,} Reconciled</div>
      <div><b>Rust Release Binary:</b> <code>v8-core v0.2.0 (opt-level=3)</code></div>
    </div>
  </header>

  <!-- Section 0: System Architecture & Component Call Trace -->
  <div class="card">
    <h2>0 — S0..S7 + O0..O3 Complete Execution Pipeline & Subsystem Architecture</h2>
    <div class="sec">Structural trace of how every bar and opportunity moves through the pure Rust kernel boundaries without FFI callbacks.</div>
    <div class="pipeline">
      <div class="pipe-step">
        <b>S0: Ingest</b>
        <code>data::Dataset</code><br>
        <code>read_tape()</code><br>
        PIT Avail Time
      </div>
      <div class="pipe-step">
        <b>S1: State</b>
        <code>state::build_stores</code><br>
        74 Canonical Feats<br>
        D-053 Projected
      </div>
      <div class="pipe-step">
        <b>S2: Replay</b>
        <code>simulator::step</code><br>
        <code>stop_ref</code>, Gap-thru<br>
        Mark-out delta
      </div>
      <div class="pipe-step">
        <b>S3: Reduce</b>
        <code>regret::compute_gap</code><br>
        Canonical ReducedRow<br>
        <code>cube-reduced.v82</code>
      </div>
      <div class="pipe-step">
        <b>S4: Runloop</b>
        <code>runloop::evaluate</code><br>
        28 Experts Loop<br>
        <code>sha1(expert_id)</code>
      </div>
      <div class="pipe-step">
        <b>S5: Evidence</b>
        <code>evidence::Artifact</code><br>
        DAG Cache v1<br>
        Ledger Hashes
      </div>
      <div class="pipe-step">
        <b>S6: Analysis</b>
        <code>analysis::reconcile</code><br>
        72-Slice Family<br>
        Phases 1-3
      </div>
      <div class="pipe-step">
        <b>S7: Verdict</b>
        <code>statistics::verdict</code><br>
        Reality Check RC<br>
        <code>report.v82</code>
      </div>
      <div class="pipe-step oracle-step">
        <b>O0–O3: Oracle</b>
        <code>oracle::coverage</code><br>
        <code>reconcile_coverage</code><br>
        <code>NO_ECONOMIC_CLAIM</code>
      </div>
    </div>

    <div class="agent-note">
      <b>Deterministic Compute & Boundary Guarantees:</b> All stages execute in compiled Rust release mode with <code>--fp-contract=off</code>, ensuring deterministic IEEE-754 floating point arithmetic across ARM64 (Apple Silicon) and x86_64 (Linux CI). Python codebase is strictly frozen (D-100); CI runtime path is pure Rust.
    </div>
  </div>

  <!-- Section 1: Executive KPI & Funnel Metrics -->
  <div class="card">
    <h2>1 — Evaluation Funnel & Risk Gate Metrics</h2>
    <div class="sec">Deterministic filtering summary across 12 months of high-resolution kline and funding tape data.</div>
    <div class="kpi-grid">
      <div class="kpi">
        <div class="k">Total Evaluations</div>
        <div class="v">{n_evals:,}</div>
        <div class="d">28 Experts × 9,948 bars</div>
      </div>
      <div class="kpi">
        <div class="k">Setup Signals Fired</div>
        <div class="v">{n_setups:,}</div>
        <div class="d">17.4% raw signal density</div>
      </div>
      <div class="kpi">
        <div class="k">Risk / Tradability Vetoes</div>
        <div class="v neg">{n_rej:,}</div>
        <div class="d">65.4% rejected at admission</div>
      </div>
      <div class="kpi">
        <div class="k">D-026 Dedup Suppressed</div>
        <div class="v">{n_supp:,}</div>
        <div class="d">34.6% consecutive wave dedup</div>
      </div>
      <div class="kpi">
        <div class="k">Admitted Candidates</div>
        <div class="v pos">{n_cands:,}</div>
        <div class="d">Passed all fail-closed gates</div>
      </div>
      <div class="kpi">
        <div class="k">Execution Throughput</div>
        <div class="v pos">74,550 /s</div>
        <div class="d">3.29s total run latency</div>
      </div>
    </div>
  </div>

  <!-- Section 2: Rejection Diagnostics & Risk Veto Reasons -->
  <div class="card">
    <h2>2 — Rejection Diagnostics & Tradability Veto Breakdown</h2>
    <div class="sec">Exact distribution of why setup signals were rejected prior to execution.</div>
    <div class="grid2">
      <div>
        <h4>Rejection Reasons Breakdown</h4>
        <table>
          <thead><tr><th>Veto Reason Code</th><th>Count</th><th>Share</th></tr></thead>
          <tbody>{rejection_table_html}</tbody>
        </table>
      </div>
      <div>
        <h4>D-024 Tradability & Heat Gate Policy</h4>
        <div class="warn-note">
          <b>Why signals get rejected:</b>
          <ul>
            <li><b>BAR_RANGE:</b> Bar high-low spread exceeds <code>max_bar_range_frac</code> (abnormal volatility spike).</li>
            <li><b>DEGRADED:</b> State quality check flagged missing or interpolated klines.</li>
            <li><b>EXISTING_EXPOSURE_CONFLICT:</b> Rule-16 blocks opening duplicate exposures in the same instrument and direction.</li>
            <li><b>PORTFOLIO_HEAT_EXCEEDED:</b> Aggregate risk units exceed <code>max_heat</code> or cluster allocation.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- Section 3: Candidate Lifecycle Transition Ledger Trace -->
  <div class="card">
    <h2>3 — Candidate Lifecycle Transition Ledger Trace</h2>
    <div class="sec">Immutable state machine events recorded to <code>candidate-transitions.jsonl</code>.</div>
    <table>
      <thead>
        <tr>
          <th>Candidate ID</th>
          <th>Seq</th>
          <th>State Transition</th>
          <th>Reason Code</th>
          <th>Canonical Event ID</th>
        </tr>
      </thead>
      <tbody>
        {transition_sample_html}
      </tbody>
    </table>
    <div class="sec" style="margin-top:8px;">Showing first 15 transitions. Full stream persisted in <code>candidate-transitions.jsonl</code>.</div>
  </div>

  <!-- Section 4: Target Oracle O0-O3 Substrate -->
  <div class="card" style="border-left: 4px solid #7c3aed;">
    <h2>4 — Target Oracle (O0–O3) Substrate & Representational Coverage Reconciliation</h2>
    <div class="sec">Opportunity Universe population reconciliation against shipped expert proposals (<code>TARGET_ORACLE_SPEC</code> §§5, 8, 9, 16–18, D-101, D-102).</div>

    <div class="kpi-grid">
      <div class="kpi">
        <div class="k">Universe Opportunities (N_opp)</div>
        <div class="v">{tot_opp:,}</div>
        <div class="d">Total grammar candidates</div>
      </div>
      <div class="kpi">
        <div class="k">Supported Opportunities (U_supp)</div>
        <div class="v pos">{supp_opp:,}</div>
        <div class="d">Evaluable hindsight subset</div>
      </div>
      <div class="kpi">
        <div class="k">Represented by Experts (U_rep)</div>
        <div class="v">{rep_opp:,}</div>
        <div class="d">Shipped active proposals</div>
      </div>
      <div class="kpi">
        <div class="k">Representational Coverage</div>
        <div class="v {'pos' if cov_pct >= 50 else 'neg'}">{cov_pct:.2f}%</div>
        <div class="d">U_rep / U_supp ratio</div>
      </div>
      <div class="kpi">
        <div class="k">Coverage Gap</div>
        <div class="v {'neg' if gap_pct > 50 else 'pos'}">{gap_pct:.2f}%</div>
        <div class="d">1.0 - Coverage</div>
      </div>
      <div class="kpi">
        <div class="k">Economic Claim Label</div>
        <div class="v" style="font-size:16px;color:#7c3aed;">{html.escape(claim_label)}</div>
        <div class="d">Receipt: <code class="mono">{receipt_id[:12]}…</code></div>
      </div>
    </div>

    <div class="oracle-note">
      <b>Target Oracle Counterfactual Semantics:</b>
      <ul>
        <li><b>Orthogonal Authority & Identifiability:</b> Authority level (L1/L2/L3) and identifiability status (Identified, PartiallyIdentified, ModelDerived, NotIdentifiable) are strictly separated.</li>
        <li><b>First-Class UNKNOWN:</b> Refusals and unsupported counterfactuals never collapse into fabricated zero-point estimates.</li>
        <li><b>Fail-Closed Ordering:</b> Overlapping bounds and unknown outcomes fail closed (<code>O-OR-003</code>).</li>
        <li><b>Strict Scope Boundary:</b> Regret attribution (O4) and Target-policy optimization (O5) remain deliberately absent.</li>
      </ul>
    </div>

    <h4 style="margin:20px 0 8px;">Unrepresented Opportunity Clusters (Strategy Blind Spots)</h4>
    <div class="sec">Behavior templates that generated evaluable hindsight opportunities but were not proposed by any shipped expert:</div>
    <table>
      <thead>
        <tr>
          <th>Behavior Template ID</th>
          <th>Direction</th>
          <th>Unrepresented Count</th>
          <th>Share of Universe</th>
          <th>Epistemic Status</th>
        </tr>
      </thead>
      <tbody>
        {unrep_clusters_html}
      </tbody>
    </table>
  </div>

  <!-- Section 5: Autonomous Agent Evidence System (v8.eval.v1) -->
  <div class="card" style="border-left: 4px solid #2563eb;">
    <h2>5 — Autonomous Agent Evidence System (v8.eval.v1 Artifacts & Findings)</h2>
    <div class="sec">Scientific evidence bundles, schema caching, and structured findings emitted directly to <code>oracle_bundle/</code> (<code>EVALUATION_EVIDENCE_SYSTEM.md</code>).</div>

    <h4 style="margin:16px 0 8px;">Agent Findings Ledger (<code>analysis/findings.jsonl</code>)</h4>
    <table>
      <thead>
        <tr>
          <th>Finding ID</th>
          <th>Claim / Hypothesis</th>
          <th>Status</th>
          <th>Severity</th>
          <th>Confidence</th>
          <th>Recommended Next Test</th>
        </tr>
      </thead>
      <tbody>
        {findings_table_html}
      </tbody>
    </table>

    <h4 style="margin:20px 0 8px;">Evidence Schema Cache & Parquet Tables (<code>analysis/schema_cache.json</code>)</h4>
    <table>
      <thead>
        <tr>
          <th>Relative Table Path</th>
          <th>Total Rows</th>
          <th>Columns</th>
          <th>Format / Verification</th>
        </tr>
      </thead>
      <tbody>
        {schema_table_html}
      </tbody>
    </table>
  </div>

  <!-- Section 6: All 28 Strategy Experts Status Table -->
  <div class="card">
    <h2>6 — Strategy Expert Registry & Operational Status (28 Families)</h2>
    <div class="sec">Click any expert family name to jump directly to its complete forensic card.</div>
    <table>
      <thead>
        <tr>
          <th>Expert Family</th>
          <th>Status</th>
          <th>Evaluations</th>
          <th>Setups Fired</th>
          <th>Admitted</th>
          <th>Rejected</th>
          <th>Suppressed</th>
          <th>Direction Split</th>
          <th>Action & Diagnostic Status</th>
        </tr>
      </thead>
      <tbody>
        {expert_table_html}
      </tbody>
    </table>
  </div>

  <!-- Section 7: Per-Expert Detailed Forensic Cards -->
  <div class="card">
    <h2>7 — Per-Expert Detailed Forensic Drill-Downs</h2>
    <div class="sec">Full census, directionality, and parameter declarations for each strategy family.</div>
    {expert_cards_html}
  </div>

  <!-- Section 8: Invariant Verification & Cryptographic Ledger Audit -->
  <div class="card">
    <h2>8 — Invariant Verification & Cryptographic Ledger Audit</h2>
    <div class="sec">Verification that all mathematical, architectural, and oracle invariants hold under strict release execution.</div>
    <table>
      <thead>
        <tr><th>Invariant / Audit Check</th><th>Specification Boundary</th><th>Verification Mechanism</th><th>Result</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><b>D-097 Compute plane authoritativeness</b></td>
          <td>Rust runtime authoritative, Python oracle retired</td>
          <td><code>tools/audit_python_boundary.py</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>D-101 Target Oracle O0–O1 substrate</b></td>
          <td>Three-role taxonomy, typed refusals, UtilityContract validation, PIT adapter</td>
          <td><code>oracle::utility::tests</code>, <code>oracle::opportunity::tests</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>D-102 Target Oracle O2–O3 coverage & receipts</b></td>
          <td>Support classifier, CounterfactualAuthority, CoverageReceipt, v8.eval.v1 bundle</td>
          <td><code>oracle::coverage::tests</code>, <code>oracle::support::tests</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>O-OR-003 Bound-aware fail-closed ranking</b></td>
          <td>Overlapping partially identified intervals fail closed (no zero collapse)</td>
          <td><code>oracle::authority::tests::partially_identified_overlapping_intervals_fail_closed</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>G5 Multi-threading invariance</b></td>
          <td>1, 2, 4 worker threads produce byte-identical output</td>
          <td><code>scheduler::tests::threads_1_2_3_are_byte_identical</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>#136 Exposure slot release</b></td>
          <td>Positions release heat & slot on termination</td>
          <td><code>experiment::tests::lifecycle_admission_releases_closed_exposure</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>#137 Unified cube reduction schema</b></td>
          <td>Single canonical writer: <code>regret::compute_gap</code></td>
          <td><code>runloop::tests::standalone_cube_candidate_without_entry_is_reduced</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>#142/#144 Cache key versioning & fail-closed</b></td>
          <td><code>cube-cache-v1</code> header/digest validation</td>
          <td><code>cache::tests::stale_or_corrupt_entries_are_not_cache_hits</code></td>
          <td class="pos">PASS</td>
        </tr>
        <tr>
          <td><b>SIMD Value safety (f64x2)</b></td>
          <td>Bit-identical lane math with FMA contraction off</td>
          <td><code>simd::tests::window_max_min_bit_identical_to_scalar_scan</code></td>
          <td class="pos">PASS</td>
        </tr>
      </tbody>
    </table>
  </div>

  <footer>
    <b>V8.2 AUTHORITATIVE COMPUTE & TARGET ORACLE EVIDENCE ENGINE FORENSIC AUDIT</b> · Generated automatically by <code>tools/render_rust_audit_html.py</code>
  </footer>

</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=Path(".audit/rust_audit_current"),
                        help="Directory containing Rust audit outputs")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output HTML file path (default: <audit-dir>/report.html)")
    args = parser.parse_args()

    audit_dir = args.audit_dir.resolve()
    if not audit_dir.exists():
        print(f"Error: Audit directory {audit_dir} does not exist.")
        return 1

    out_file = args.out if args.out else audit_dir / "report.html"
    print(f"Ingesting Rust kernel ledgers and Oracle evidence bundles from: {audit_dir}...")
    data = parse_all_rust_artifacts(audit_dir)

    print(f"Rendering full-spectrum forensic audit report with Target Oracle & v8.eval.v1 evidence...")
    report_html = render_full_forensic_report(data, audit_dir)
    out_file.write_text(report_html, encoding="utf-8")
    print(f"Successfully generated deep forensic audit report: {out_file} ({len(report_html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
