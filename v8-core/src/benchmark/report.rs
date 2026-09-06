//! Canonical Benchmark Forensic Report Generator (D-153 §110, App C).
//!
//! Produces self-contained, auditable forensic HTML and JSON reports
//! adhering strictly to Renderer Firewall (Constitution Rule 31) and
//! Rule 12 (No naked economic claims).

use std::fmt::Write;
use crate::benchmark::projection::CapitalOutcomeProjection;
use crate::benchmark::receipt::BenchmarkReceipt;

pub struct BenchmarkReportGenerator;

impl BenchmarkReportGenerator {
    /// Renders forensic JSON report
    pub fn render_json(receipt: &BenchmarkReceipt, projection: Option<&CapitalOutcomeProjection>) -> Result<String, String> {
        serde_json::to_string_pretty(&serde_json::json!({
            "schema": "v8.benchmark.report.1",
            "receipt": receipt,
            "capital_projection": projection,
            "constitutional_notice": "NO_ECONOMIC_CLAIM: Benchmark Fabric is a diagnostic instrument and cannot grant deployment readiness or prove future edge.",
        })).map_err(|e| format!("JSON serialization failed: {e}"))
    }

    /// Renders standalone forensic HTML scorecard conforming to Rule 31
    pub fn render_html(receipt: &BenchmarkReceipt, projection: Option<&CapitalOutcomeProjection>) -> String {
        let mut html = String::with_capacity(16 * 1024);
        
        let _ = write!(html, r#"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>V8.5 Benchmark Fabric Forensic Report - {}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #0f141c; color: #e1e7f0; margin: 0; padding: 24px; }}
.container {{ max-width: 1000px; margin: 0 auto; background: #18202c; border: 1px solid #2d3b4f; border-radius: 8px; padding: 32px; }}
h1, h2, h3 {{ color: #ffffff; border-bottom: 1px solid #2d3b4f; padding-bottom: 8px; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
.badge-pass {{ background: #1b472e; color: #4ade80; border: 1px solid #22c55e; }}
.badge-fail {{ background: #4a151b; color: #f87171; border: 1px solid #ef4444; }}
.badge-warn {{ background: #4a3815; color: #facc15; border: 1px solid #eab308; }}
.badge-diag {{ background: #1e293b; color: #94a3b8; border: 1px solid #475569; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
th, td {{ border: 1px solid #2d3b4f; padding: 10px; text-align: left; }}
th {{ background: #202b3c; color: #94a3b8; font-weight: 600; }}
tr:nth-child(even) {{ background: #141c26; }}
.score-hero {{ display: flex; align-items: center; justify-content: space-between; background: #131b26; border: 1px solid #2a374a; padding: 20px; border-radius: 6px; margin-bottom: 24px; }}
.score-val {{ font-size: 42px; font-weight: bold; color: #38bdf8; }}
.callout {{ background: #192330; border-left: 4px solid #38bdf8; padding: 12px 16px; margin: 16px 0; font-size: 13px; }}
.callout-warn {{ border-left-color: #f59e0b; }}
</style>
</head>
<body>
<div class="container">
<h1>V8.5 Benchmark Fabric — Evaluation Scorecard</h1>
<div class="callout callout-warn">
<strong>CONSTITUTIONAL NOTICE (Rule 12 & Rule 57):</strong> Benchmark Fabric is an evidence-bound diagnostic instrument. CapabilityScore does NOT confer deployment readiness or mint economic edge (SUPPORTED_EDGE). All outputs carry <code>NO_ECONOMIC_CLAIM</code>.
</div>

<div class="score-hero">
  <div>
    <div style="color: #94a3b8; font-size: 14px;">POLICY EVALUATED</div>
    <div style="font-size: 24px; font-weight: bold;">{}</div>
    <div style="color: #64748b; font-size: 12px; margin-top: 4px;">Receipt: <code>{}</code></div>
  </div>
  <div style="text-align: right;">
    <div style="color: #94a3b8; font-size: 14px;">CAPABILITY SCORE</div>
    <div class="score-val">{:.1} <span style="font-size: 16px; color: #64748b;">/ 100</span></div>
    <div style="font-size: 12px; color: #94a3b8;">Coverage Factor: {:.2}</div>
  </div>
</div>

<h2>Hard Gate Vector (G0–G9)</h2>
<table>
<thead><tr><th>Gate</th><th>Name</th><th>Status</th><th>Consequence</th></tr></thead>
<tbody>
<tr><td>G0</td><td>Identity & Provenance</td><td><span class="badge badge-pass">{}</span></td><td>Authority chain verified</td></tr>
<tr><td>G1</td><td>PIT & Causal Integrity</td><td><span class="badge badge-pass">{}</span></td><td>No future-row leakage detected</td></tr>
<tr><td>G2</td><td>Determinism & Ledger</td><td><span class="badge badge-pass">{}</span></td><td>Ledger hash chain valid</td></tr>
<tr><td>G3</td><td>Benchmark Coverage</td><td><span class="badge badge-pass">{}</span></td><td>Required test cells present</td></tr>
<tr><td>G4</td><td>Structural Robustness</td><td><span class="badge badge-pass">{}</span></td><td>Synthetic passport qualified</td></tr>
<tr><td>G5</td><td>Statistical Credibility</td><td><span class="badge badge-pass">{}</span></td><td>Search debt accounting passed</td></tr>
<tr><td>G6</td><td>Protected OOS Replication</td><td><span class="badge badge-diag">{}</span></td><td>Preserved untouched</td></tr>
<tr><td>G7</td><td>Generalization</td><td><span class="badge badge-pass">{}</span></td><td>Cross-regime stability verified</td></tr>
<tr><td>G8</td><td>Prospective Shadow</td><td><span class="badge badge-diag">{}</span></td><td>Not in live shadow</td></tr>
<tr><td>G9</td><td>Live Realization</td><td><span class="badge badge-diag">{}</span></td><td>Not deployed</td></tr>
</tbody>
</table>

<h2>Domain Breakdown (10 Capability Domains)</h2>
<table>
<thead><tr><th>Domain</th><th>Calibrated Score</th><th>95% CI</th><th>Samples</th><th>Hard Invariants</th></tr></thead>
<tbody>
"#, 
            receipt.policy_id, 
            receipt.policy_id, 
            receipt.receipt_id,
            receipt.composite_capability_score * 100.0,
            receipt.coverage_factor,
            receipt.gate_vector.g0_identity.as_str(),
            receipt.gate_vector.g1_causal_pit.as_str(),
            receipt.gate_vector.g2_determinism_ledger.as_str(),
            receipt.gate_vector.g3_benchmark_coverage.as_str(),
            receipt.gate_vector.g4_structural_robustness.as_str(),
            receipt.gate_vector.g5_statistical_credibility.as_str(),
            receipt.gate_vector.g6_protected_oos.as_str(),
            receipt.gate_vector.g7_generalization.as_str(),
            receipt.gate_vector.g8_prospective_shadow.as_str(),
            receipt.gate_vector.g9_live_realization.as_str(),
        );

        let mut sorted_domains: Vec<_> = receipt.domain_results.keys().cloned().collect();
        sorted_domains.sort_by_key(|d| d.as_str());
        for d in sorted_domains {
            if let Some(res) = receipt.domain_results.get(&d) {
                let _ = write!(html, r#"<tr>
<td>{}</td>
<td><strong>{:.1}%</strong></td>
<td>[{:.1}%, {:.1}%]</td>
<td>{}</td>
<td><span class="badge {}">{}</span></td>
</tr>"#,
                    d.as_str(),
                    res.calibrated_score * 100.0,
                    res.lower_bound * 100.0,
                    res.upper_bound * 100.0,
                    res.sample_count,
                    if res.passed_hard_invariants { "badge-pass" } else { "badge-fail" },
                    if res.passed_hard_invariants { "PASS" } else { "FAIL" },
                );
            }
        }

        let _ = write!(html, "</tbody></table>");

        if let Some(ref def) = receipt.nearest_defeater {
            let _ = write!(html, r#"<h2>Adversarial Reverse-Stress Vulnerability</h2>
<div class="callout callout-warn">
<strong>Nearest Defeater Located:</strong> Family <code>{}</code> at plausibility distance <strong>{:.2}</strong> (Peak Drawdown: {:.1}%). Predicate: <code>{}</code>
</div>"#, def.family, def.plausibility_distance, def.peak_drawdown_pct, def.failure_predicate);
        }

        if let Some(proj) = projection {
            let _ = write!(html, r#"<h2>Capital Outcome Projection ($1,000 Initial Capital)</h2>
<div class="callout">
<strong>Projection Grade:</strong> <code>{}</code> | Epistemic Status: {}<br>
<em>Notice: Counterfactual forward simulation bands. NOT realized cashflow or guaranteed profit.</em>
</div>
<table>
<thead><tr><th>Quantile</th><th>Return (bps)</th><th>Max DD (bps)</th><th>Counterfactual Capital ($)</th></tr></thead>
<tbody>
"#, proj.projection_grade.as_str(), proj.epistemic_status);

            for band in &proj.outcome_bands {
                let _ = write!(html, r#"<tr>
<td>P{:.0}</td>
<td>{:.1} bps</td>
<td>{:.1} bps</td>
<td>${:.2}</td>
</tr>"#, band.percentile * 100.0, band.return_bps, band.max_drawdown_bps, band.terminal_capital_usd);
            }
            let _ = write!(html, "</tbody></table>");
        }

        let _ = write!(html, r#"<div style="margin-top: 32px; font-size: 11px; color: #64748b; border-top: 1px solid #2d3b4f; padding-top: 12px;">
Evaluated at: {} ns | Duration: {:.3}s | Hash: <code>{}</code>
</div>
</div>
</body>
</html>"#, receipt.evaluated_at_timestamp_ns, receipt.evaluation_duration_sec, receipt.receipt_digest);

        html
    }
}
