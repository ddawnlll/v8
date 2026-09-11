"""D-153 Canonical Forensic Report Generator (Rule 12, Rule 31 Renderer Firewall).

Generates self-verifying, tamper-evident HTML and JSON forensic reports.
Constitutional Invariant:
    Accepts ONLY verified receipts. If receipt digest does not match its contents,
    or if bound physical artifacts on disk are missing/tampered, rendering fails closed
    or marks the status as BLOCKED / UNVERIFIED.
"""

from __future__ import annotations

from pathlib import Path

from v8_next.evaluation.benchmark_receipt import BenchmarkReceipt, GateEvaluation, GateState
from v8_next.evaluation.certificate import PolicyCertificate


def _v(value: float | None, digits: int = 1) -> str:
    """Render a certificate measurement; a missing one says MISSING, not 0."""
    if value is None:
        return "MISSING"
    return f"{value:.{digits}f}"


def _gate_decision(ev: GateEvaluation) -> str:
    """Rendered decision for one gate row (#435).

    The descriptor's ``requirement`` is what decides whether a state is admitted,
    so the report shows the decision explicitly: an established PASS, a
    NOT_APPLICABLE that the gate's own clause admits, or the named reason the gate
    is not established (e.g. ``REQUIRED_BLOCKING_GATE_UNEVALUATED``).
    """
    if ev.holds():
        if ev.state == GateState.PASS:
            return "ESTABLISHED"
        return "ADMITTED_NOT_APPLICABLE"
    return ev.refusal_reason() or ""


def generate_forensic_html_report(
    receipt: BenchmarkReceipt,
    output_path: Path | str,
) -> bool:
    """Render self-contained forensic HTML report adhering to Rule 31 Renderer Firewall."""
    # 1. Self-verification check (Renderer Firewall)
    is_valid, verify_msg = receipt.verify()
    cert = PolicyCertificate.generate(receipt)

    is_approved = "Ready For Review" in cert.status
    verdict_badge = "badge-pass" if is_approved else "badge-fail"
    verdict_text = cert.status if is_valid else f"BLOCKED ({verify_msg})"

    # 2. HTML template (matching D-153 Forensic standard)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>V8.5 Benchmark Fabric — Forensic Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
.container {{ max-width: 1040px; margin: 0 auto; background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 28px; }}
h1, h2 {{ color: #f8fafc; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
.callout {{ background: #0f172a; border-left: 4px solid #38bdf8; padding: 12px 16px; margin: 16px 0; font-size: 13px; }}
.callout-warn {{ border-left-color: #f59e0b; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 13px; }}
.badge-pass {{ background: #14532d; color: #4ade80; border: 1px solid #22c55e; }}
.badge-fail {{ background: #7f1d1d; color: #f87171; border: 1px solid #ef4444; }}
.badge-warn {{ background: #78350f; color: #fbbf24; border: 1px solid #d97706; }}
.badge-miss {{ background: #374151; color: #9ca3af; border: 1px solid #4b5563; }}
.hero {{ display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 20px; margin: 20px 0; }}
.hero-score {{ font-size: 42px; font-weight: bold; color: #38bdf8; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
th, td {{ border: 1px solid #334155; padding: 10px; text-align: left; }}
th {{ background: #0f172a; color: #94a3b8; }}
tr:nth-child(even) {{ background: #1e293b; }}
code {{ font-family: ui-monospace, monospace; background: #0f172a; padding: 2px 6px; border-radius: 4px; }}
</style>
</head>
<body>
<div class="container">
<h1>V8.5 Benchmark Fabric — Evidence Dashboard & Policy Certificate</h1>

<div class="callout callout-warn">
<strong>CONSTITUTIONAL NOTICE (Rule 12 & Rule 57):</strong> Benchmark Fabric is an evidence-bound diagnostic instrument. CapabilityScore does NOT confer deployment readiness or mint economic edge (<code>SUPPORTED_EDGE</code>). All outputs carry <code>NO_ECONOMIC_CLAIM</code>.
</div>

<div class="callout">
<strong>SELF-VERIFICATION (#328):</strong> Rendered from a receipt whose digest was <em>recomputed from its own contents</em> at render time.<br>
<code>verified_digest = {receipt.receipt_digest}</code><br>
<code>integrity_status = {verify_msg}</code> | <code>digest_version = {receipt.digest_version}</code> | <code>artifact_bindings = {len(receipt.artifact_bindings)}</code>
</div>

<div class="hero">
  <div>
    <div style="color: #94a3b8; font-size: 13px; text-transform: uppercase;">Policy Verdict & Status</div>
    <div style="margin: 8px 0;"><span class="badge {verdict_badge}">{verdict_text}</span></div>
    <div style="font-size: 13px;">Target Policy: <strong>{receipt.policy_id}</strong> | Case: <code>{receipt.case_id}</code></div>
    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">{cert.authority_verdict}</div>
  </div>
  <div style="text-align: right;">
    <div style="color: #94a3b8; font-size: 13px; text-transform: uppercase;">Readiness Index</div>
    <div class="hero-score">{_v(cert.readiness_index)} <span style="font-size: 16px; color: #94a3b8;">/ 100</span></div>
    <div style="font-size: 12px; color: #94a3b8;">Capability: {_v(cert.research_capability_score)} | Robustness: {_v(cert.minerva_robustness_score)}</div>
  </div>
</div>

<h2>Hard-Gate Verification Matrix (G0-G9 Non-Compensable)</h2>
<table>
<thead><tr><th>Gate ID</th><th>Canonical Gate Descriptor</th><th>Requirement</th><th>State</th><th>Decision</th></tr></thead>
<tbody>
"""
    for ev in receipt.gates.evaluated_gates():
        st = ev.state.value
        badge_cls = (
            "badge-pass"
            if st == "PASS"
            else ("badge-warn" if st == "UNKNOWN" else ("badge-miss" if st == "MISSING" else "badge-fail"))
        )
        gate_name = f"{ev.descriptor.canonical_id}::{ev.descriptor.vector_field}"
        html_content += f"""  <tr>
    <td><code>G{ev.descriptor.index}</code></td>
    <td><strong>{gate_name}</strong><br><small style="color: #94a3b8;">{ev.descriptor.source_clause}</small></td>
    <td><code>{ev.descriptor.requirement}</code></td>
    <td><span class="badge {badge_cls}">{st}</span></td>
    <td><code>{_gate_decision(ev)}</code></td>
  </tr>
"""

    html_content += f"""</tbody>
</table>

<h2>D-153 Multiplicative Readiness Components</h2>
<table>
<thead><tr><th>Component</th><th>Score / Value</th><th>Status</th><th>Notes</th></tr></thead>
<tbody>
  <tr>
    <td>Research Capability Score</td>
    <td><strong>{_v(cert.research_capability_score)} / 100</strong></td>
    <td><span class="badge badge-pass">EVALUATED</span></td>
    <td>Harmonic mean with uncertainty penalty (D-153 §76)</td>
  </tr>
  <tr>
    <td>Evidence Multiplier</td>
    <td><strong>{_v(cert.evidence_multiplier, 2)}</strong></td>
    <td><span class="badge badge-warn">PENALIZED</span></td>
    <td>Single diagnostic cell coverage penalty</td>
  </tr>
  <tr>
    <td>Minerva Robustness Score</td>
    <td><strong>{_v(cert.minerva_robustness_score)} / 100</strong></td>
    <td><span class="badge badge-fail">{cert.robustness_seal_status}</span></td>
    <td>arXiv:2608.23808 prudex evaluation</td>
  </tr>
  <tr>
    <td>Economic Projection Score</td>
    <td><strong>{_v(cert.economic_score)} / 100</strong></td>
    <td><span class="badge badge-warn">DIAGNOSTIC_DEFAULT</span></td>
    <td>Diagnostic cell default (no forward claims)</td>
  </tr>
</tbody>
</table>

<h2>Cryptographically Bound Physical Artifacts</h2>
<table>
<thead><tr><th>Role</th><th>Path</th><th>SHA-256 Digest</th><th>Bytes</th></tr></thead>
<tbody>
"""
    for b in receipt.artifact_bindings:
        html_content += f"""  <tr>
    <td><code>{b.role}</code></td>
    <td><code>{b.path}</code></td>
    <td><code>{b.sha256_hex[:16]}...{b.sha256_hex[-8:]}</code></td>
    <td>{b.bytes}</td>
  </tr>
"""
    html_content += """</tbody>
</table>

<h2>Economic Evidence Attachment</h2>
<table>
<thead><tr><th>Field</th><th>Value</th></tr></thead>
<tbody>
"""
    econ_digest = receipt.economic_evidence_digest or "(none attached)"
    econ_path = receipt.economic_receipt_path or "(none)"
    html_content += f"""  <tr>
    <td><code>economic_evidence_digest</code></td>
    <td><code>{econ_digest[:32]}...</code></td>
  </tr>
  <tr>
    <td><code>economic_receipt_path</code></td>
    <td><code>{econ_path}</code></td>
  </tr>
"""
    html_content += """</tbody>
</table>

<div style="margin-top: 32px; font-size: 11px; color: #64748b; border-top: 1px solid #334155; padding-top: 12px;">
V8.5 Benchmark Fabric Forensic Ledger & Certificate Firewall - Built in accordance with D-153 & D-152.
</div>
</div>
</body>
</html>"""

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_content, encoding="utf-8")
    return True
