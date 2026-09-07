//! Canonical Benchmark Forensic Report Generator (D-153 §110, App C; #328).
//!
//! Produces self-contained, auditable forensic HTML and JSON reports
//! adhering strictly to Renderer Firewall (Constitution Rule 31) and
//! Rule 12 (No naked economic claims).
//!
//! # Reports accept only verified receipts (#328 R2)
//!
//! Both renderers take [`VerifiedReceipt`], which has exactly one constructor
//! ([`VerifiedReceipt::verify`]) that recomputes the digest from contents and
//! requires it to match. There is no `From<BenchmarkReceipt>` and no
//! `assume_verified` escape hatch, so a report cannot be produced from an
//! unverified receipt without deleting a `?`. The report also stamps the digest
//! it verified, so a reader can check the artifact against the ledger row it
//! came from instead of trusting prose.
//!
//! A report can also *lower* status but never raise it: the rendered verdict is
//! the firewall's, and [`VerifiedReceipt::unverified`] downgrades an unverified
//! receipt to `UNVERIFIED` rather than refusing to render, because a silently
//! missing report is how an unverified claim becomes a remembered clean one.

use std::fmt::Write;
use crate::benchmark::certificate::PolicyCertificate;
use crate::benchmark::projection::CapitalOutcomeProjection;
use crate::benchmark::receipt::{BenchmarkReceipt, ReceiptVerificationError};

/// A receipt whose digest has been recomputed from its own contents and found
/// to match. Required by every renderer.
#[derive(Debug, Clone, PartialEq)]
pub struct VerifiedReceipt {
    receipt: BenchmarkReceipt,
    /// Digest recomputed at verification time. Stamped into the report.
    recomputed_digest: String,
    artifact_warnings: Vec<String>,
}

impl VerifiedReceipt {
    /// Recompute-and-compare, then optionally check bound artifacts on disk.
    ///
    /// When `check_artifacts` is true a bound artifact that is present but
    /// disagrees is a hard failure (Rule 5). A bound artifact that is merely
    /// absent from this machine is recorded in
    /// [`VerifiedReceipt::artifact_warnings`] rather than rejected: the receipt's
    /// digest already commits to the declared hash, so absence is an environment
    /// condition, not evidence about the ledger bytes. Silently passing an
    /// unverifiable artifact would be the actual Rule 5 violation, so the
    /// warning is surfaced in the report.
    pub fn verify(
        receipt: &BenchmarkReceipt,
        check_artifacts: bool,
    ) -> Result<Self, ReceiptVerificationError> {
        receipt.verify()?;
        let recomputed_digest = receipt.compute_digest()?;
        let mut out = Self {
            receipt: receipt.clone(),
            recomputed_digest,
            artifact_warnings: Vec::new(),
        };
        if check_artifacts {
            out.verify_artifacts()?;
        }
        Ok(out)
    }

    fn verify_artifacts(&mut self) -> Result<(), ReceiptVerificationError> {
        for binding in &self.receipt.artifacts {
            match binding.verify_file() {
                Ok(()) => {}
                Err(e) if e.is_missing_file() => self.artifact_warnings.push(e.to_string()),
                Err(e) => return Err(ReceiptVerificationError::Artifact(e)),
            }
        }
        Ok(())
    }

    /// Environment conditions found while checking bound artifacts.
    pub fn artifact_warnings(&self) -> &[String] {
        &self.artifact_warnings
    }

    pub fn receipt(&self) -> &BenchmarkReceipt {
        &self.receipt
    }

    /// The digest this report was built on, i.e. the recomputed one.
    pub fn digest(&self) -> &str {
        &self.recomputed_digest
    }

    /// `true` when the stored digest equalled the recomputed digest.
    pub fn digest_matches_stored(&self) -> bool {
        self.receipt.receipt_digest == self.recomputed_digest
    }

    /// A single-line verification stamp for report surfaces.
    pub fn verification_stamp(&self) -> String {
        format!(
            "{}:{}",
            self.receipt.digest_version, self.recomputed_digest
        )
    }
}

// Deliberately absent, and this comment is the guard against re-adding them:
//   impl From<BenchmarkReceipt> for VerifiedReceipt
//   impl VerifiedReceipt { fn assume_verified(...) }
// Either one would make "reports accept only verified receipts" a convention
// instead of a type constraint.

pub struct BenchmarkReportGenerator;

impl BenchmarkReportGenerator {
    /// Render forensic JSON for an already-verified receipt.
    pub fn render_json(
        verified: &VerifiedReceipt,
        projection: Option<&CapitalOutcomeProjection>,
    ) -> Result<String, String> {
        let receipt = verified.receipt();
        let cert = PolicyCertificate::generate(receipt, projection);
        serde_json::to_string_pretty(&serde_json::json!({
            "schema": "v8.benchmark.report.3",
            "verification": {
                "receipt_digest_verified": verified.digest(),
                "digest_version": receipt.digest_version,
                "digest_matches_stored": verified.digest_matches_stored(),
                "artifact_bindings": receipt.artifacts,
                "artifact_warnings": verified.artifact_warnings(),
                "provenance": receipt.provenance,
            },
            "receipt": receipt,
            "policy_certificate": cert,
            "capital_projection": projection,
            "constitutional_notice": "NO_ECONOMIC_CLAIM: Benchmark Fabric is a diagnostic instrument and cannot grant deployment readiness or prove future edge.",
        })).map_err(|e| format!("JSON serialization failed: {e}"))
    }

    /// Render forensic JSON from a raw receipt, verifying first.
    ///
    /// Returns `Err` rather than rendering: this is the entry point a CLI uses
    /// when it has only a file, and an unverifiable receipt must not be turned
    /// into a polished document that reads like evidence.
    pub fn render_json_verifying(
        receipt: &BenchmarkReceipt,
        projection: Option<&CapitalOutcomeProjection>,
    ) -> Result<String, String> {
        let verified = VerifiedReceipt::verify(receipt, true)
            .map_err(|e| format!("REPORT_BLOCKED_RECEIPT_UNVERIFIED: {e}"))?;
        Self::render_json(&verified, projection)
    }

    /// Render standalone forensic HTML scorecard conforming to Rule 31.
    pub fn render_html(
        verified: &VerifiedReceipt,
        projection: Option<&CapitalOutcomeProjection>,
    ) -> String {
        let receipt = verified.receipt();
        let cert = PolicyCertificate::generate(receipt, projection);
        let mut html = String::with_capacity(24 * 1024);
        
        let is_approved = cert.status.contains("Production Ready");
        let status_badge_class = if is_approved { "badge-pass" } else { "badge-fail" };

        let _ = write!(html, r#"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>V8.5 Benchmark Fabric Forensic Report - {}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #0f141c; color: #e1e7f0; margin: 0; padding: 24px; }}
.container {{ max-width: 1080px; margin: 0 auto; background: #18202c; border: 1px solid #2d3b4f; border-radius: 8px; padding: 32px; }}
h1, h2, h3 {{ color: #ffffff; border-bottom: 1px solid #2d3b4f; padding-bottom: 8px; margin-top: 28px; }}
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
.readiness-hero {{ background: #172338; border: 1px solid #3b82f6; border-radius: 6px; padding: 20px; margin: 20px 0; display: flex; justify-content: space-between; align-items: center; }}
.readiness-val {{ font-size: 48px; font-weight: bold; color: #60a5fa; }}
.callout {{ background: #192330; border-left: 4px solid #38bdf8; padding: 12px 16px; margin: 16px 0; font-size: 13px; }}
.callout-warn {{ border-left-color: #f59e0b; }}
.panel-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 16px 0; }}
.stat-card {{ background: #131b26; border: 1px solid #2a374a; padding: 16px; border-radius: 6px; text-align: center; }}
.stat-label {{ color: #94a3b8; font-size: 12px; margin-bottom: 6px; text-transform: uppercase; }}
.stat-num {{ font-size: 24px; font-weight: bold; color: #f1f5f9; }}
</style>
</head>
<body>
<div class="container">
<h1>V8.5 Benchmark Fabric — Evidence Dashboard & Policy Certificate</h1>

<div class="callout callout-warn">
<strong>CONSTITUTIONAL NOTICE (Rule 12 & Rule 57):</strong> Benchmark Fabric is an evidence-bound diagnostic instrument. CapabilityScore does NOT confer deployment readiness or mint economic edge (SUPPORTED_EDGE). All outputs carry <code>NO_ECONOMIC_CLAIM</code>.
</div>

<div class="callout">
<strong>SELF-VERIFICATION (#328):</strong> rendered from a receipt whose digest was <em>recomputed from its own contents</em> at render time, not read from storage.<br>
<code>verified_digest = {}</code><br>
<code>stored_digest_matches = {}</code> | <code>digest_generation = {}</code> | <code>artifact_bindings = {}</code>{}</div>

<div class="readiness-hero">
  <div>
    <div style="color: #94a3b8; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Policy Verdict & Certificate</div>
    <div style="font-size: 22px; font-weight: bold; margin: 6px 0;"><span class="badge {}">{}</span></div>
    <div style="color: #cbd5e1; font-size: 13px;">Target Policy: <strong>{}</strong> | Receipt: <code>{}</code></div>
    <div style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Topology: <em>{}</em></div>
  </div>
  <div style="text-align: right;">
    <div style="color: #94a3b8; font-size: 13px;">READINESS INDEX</div>
    <div class="readiness-val">{:.1} <span style="font-size: 18px; color: #94a3b8;">/ 100</span></div>
    <div style="font-size: 11px; color: #94a3b8;">Cap({:.0}) × Ev({:.2}) × Rob({:.0}) × Econ({:.0})</div>
  </div>
</div>

<div class="panel-grid">
  <div class="stat-card">
    <div class="stat-label">1. Research Capability</div>
    <div class="stat-num">{:.1} <span style="font-size: 14px; color: #64748b;">/ 100</span></div>
    <div style="color: #4ade80; font-size: 11px; margin-top: 4px;">Multiplier: {:.2}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">2. Minerva Robustness</div>
    <div class="stat-num">{:.1} <span style="font-size: 14px; color: #64748b;">/ 100</span></div>
    <div style="color: #38bdf8; font-size: 11px; margin-top: 4px;">Seal: {}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">3. Economic Evidence</div>
    <div class="stat-num">{:.1} <span style="font-size: 14px; color: #64748b;">/ 100</span></div>
    <div style="color: #facc15; font-size: 11px; margin-top: 4px;">Grade: {}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Risk of Ruin (MC)</div>
    <div class="stat-num">{:.1}%</div>
    <div style="color: #f87171; font-size: 11px; margin-top: 4px;">Equity &le; $700</div>
  </div>
</div>

<h2>Panel 1: Research Capability & Domain Decomposition</h2>
<p style="color: #94a3b8; font-size: 13px;">Evaluates infrastructure maturity, determinism, and research integrity. Strict harmonic mean aggregation.</p>
<table>
<thead><tr><th>Capability Domain</th><th>Calibrated Score</th><th>95% Confidence Interval</th><th>Samples</th><th>Hard Invariants</th></tr></thead>
<tbody>
"#,
            receipt.policy_id,
            verified.digest(),
            verified.digest_matches_stored(),
            receipt.digest_version,
            receipt.artifacts.len(),
            if verified.artifact_warnings().is_empty() {
                String::new()
            } else {
                let items: Vec<String> = verified
                    .artifact_warnings()
                    .iter()
                    .map(|w| format!("<li><code>{w}</code></li>"))
                    .collect();
                format!(
                    "<br><strong>Bound artifacts not verifiable on this host:</strong><ul>{}</ul>",
                    items.join("")
                )
            },
            status_badge_class,
            cert.status,
            receipt.policy_id,
            receipt.receipt_id,
            cert.quad_tape_role,
            cert.readiness_index,
            cert.research_capability_score,
            cert.evidence_multiplier,
            cert.minerva_robustness_score,
            cert.economic_score,
            cert.research_capability_score,
            cert.evidence_multiplier,
            cert.minerva_robustness_score,
            if cert.minerva.as_ref().map(|m| m.seal_granted).unwrap_or(false) { "GRANTED" } else { "DENIED" },
            cert.economic_score,
            receipt.projection_grade.as_str(),
            cert.monte_carlo.as_ref().map(|m| m.risk_of_ruin_pct).unwrap_or(0.0),
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

        // Panel 2: MinervaScore & Robustness
        let _ = write!(html, r#"<h2>Panel 2: Economic Evidence Profile & Minerva Robustness (arXiv:2608.23808)</h2>
<p style="color: #94a3b8; font-size: 13px;">Statistical reliability gates (DSR, PBO, SPA, MinTRL, Regime Stability). Non-compensable: gate failure strictly caps score below 80 and denies seal.</p>
"#);

        if let Some(ref m) = cert.minerva {
            let badge_for = |state: crate::benchmark::types::GateState| {
                if state.is_pass() { "badge-pass" } else { "badge-fail" }
            };

            let _ = write!(html, r#"<table>
<thead><tr><th>Validation Gate</th><th>Threshold Metric</th><th>Status</th><th>Signed Margin</th><th>Evaluation Rule</th></tr></thead>
<tbody>
<tr><td>DSR (Deflated Sharpe Ratio)</td><td>DSR &ge; 0.95 (Haircut for search trials)</td><td><span class="badge {}">{}</span></td><td>{:+.3}</td><td>Non-compensable</td></tr>
<tr><td>PBO (Overfitting Probability)</td><td>PBO &lt; 0.50 (Combinatorial CV)</td><td><span class="badge {}">{}</span></td><td>{:+.3}</td><td>Non-compensable</td></tr>
<tr><td>SPA (Superior Predictive Ability)</td><td>Hansen SPA p &le; 0.05</td><td><span class="badge {}">{}</span></td><td>{:+.3}</td><td>Non-compensable</td></tr>
<tr><td>MinTRL (Min Track Length)</td><td>Bailey / de Prado Track Length</td><td><span class="badge {}">{}</span></td><td>{:+.1} days</td><td>Non-compensable</td></tr>
<tr><td>Regime Stability</td><td>Worst sub-regime return floor</td><td><span class="badge {}">{}</span></td><td>{:+.1} bps</td><td>Non-compensable</td></tr>
</tbody>
</table>
<div class="callout">
<strong>PRUDEX-Compass Mapping (TMLR 2023):</strong> Profitability: {:.2} | Risk: {:.2} | Universality: {:.2} | Diversity: {:.2} | Reliability: {:.2} | Explainability: {:.2}
</div>
"#,
                badge_for(m.gate_vector.dsr_gate), m.gate_vector.dsr_gate.as_str(), m.margins.dsr_margin,
                badge_for(m.gate_vector.pbo_gate), m.gate_vector.pbo_gate.as_str(), m.margins.pbo_margin,
                badge_for(m.gate_vector.spa_gate), m.gate_vector.spa_gate.as_str(), m.margins.spa_margin,
                badge_for(m.gate_vector.min_trl_gate), m.gate_vector.min_trl_gate.as_str(), m.margins.min_trl_margin,
                badge_for(m.gate_vector.regime_stability_gate), m.gate_vector.regime_stability_gate.as_str(), m.margins.regime_stability_margin,
                m.prudex_compass.profitability,
                m.prudex_compass.risk,
                m.prudex_compass.universality,
                m.prudex_compass.diversity,
                m.prudex_compass.reliability,
                m.prudex_compass.explainability,
            );
        }

        // Panel 3: Capital Outcome Projection & Monte Carlo Futures
        let _ = write!(html, r#"<h2>Panel 3: Risk-Adjusted Capital Projection ($1,000 Baseline, 1-Year Horizon)</h2>
<div class="callout">
<strong>Epistemic Warning:</strong> Counterfactual historical forward simulation. NOT realized cashflow or future profit guarantee. Liquidity capacity capped at $100k.
</div>
"#);

        if let Some(ref mc) = cert.monte_carlo {
            let _ = write!(html, r#"<table>
<thead><tr><th>Quantile / Scenario</th><th>Simulated Horizon</th><th>Terminal Capital ($1,000 Start)</th><th>Return (%)</th><th>Significance</th></tr></thead>
<tbody>
<tr><td>P5 (Downside Tail)</td><td>{} trades</td><td><strong>${:.2}</strong></td><td>{:.1}%</td><td>Adverse tail draw</td></tr>
<tr><td>P25 (Lower Quartile)</td><td>{} trades</td><td><strong>${:.2}</strong></td><td>{:.1}%</td><td>Conservative expectation</td></tr>
<tr><td>P50 (Median Future)</td><td>{} trades</td><td><strong>${:.2}</strong></td><td>{:.1}%</td><td>Median central path</td></tr>
<tr><td>P75 (Upper Quartile)</td><td>{} trades</td><td><strong>${:.2}</strong></td><td>{:.1}%</td><td>Constructive regime path</td></tr>
<tr><td>P95 (Upside Tail)</td><td>{} trades</td><td><strong>${:.2}</strong></td><td>{:.1}%</td><td>Favorable tail draw</td></tr>
<tr style="background: #1e293b;"><td>Worst Realized Scenario</td><td>{} trades</td><td>${:.2}</td><td>{:.1}%</td><td>Worst Monte Carlo path</td></tr>
<tr style="background: #1e293b;"><td>Best Realized Scenario</td><td>{} trades</td><td>${:.2}</td><td>{:.1}%</td><td>Best Monte Carlo path</td></tr>
</tbody>
</table>
<div style="margin: 12px 0; font-size: 13px;">
  <strong>Risk of Ruin (&ge;30% Drawdown, Equity &le; $700):</strong> <span class="badge badge-warn">{:.1}%</span> | Simulations: <strong>{}</strong>
</div>
"#,
                mc.horizon_trades, mc.p5_terminal_usd, mc.p5_return_pct,
                mc.horizon_trades, mc.p25_terminal_usd, mc.p25_return_pct,
                mc.horizon_trades, mc.p50_terminal_usd, mc.p50_return_pct,
                mc.horizon_trades, mc.p75_terminal_usd, mc.p75_return_pct,
                mc.horizon_trades, mc.p95_terminal_usd, mc.p95_return_pct,
                mc.horizon_trades, (1000.0 * (1.0 + mc.worst_scenario_return_pct / 100.0)), mc.worst_scenario_return_pct,
                mc.horizon_trades, (1000.0 * (1.0 + mc.best_scenario_return_pct / 100.0)), mc.best_scenario_return_pct,
                mc.risk_of_ruin_pct,
                mc.n_simulations,
            );
        } else if let Some(proj) = projection {
            let _ = write!(html, r#"<table>
<thead><tr><th>Quantile</th><th>Return (bps)</th><th>Max DD (bps)</th><th>Counterfactual Capital ($)</th></tr></thead>
<tbody>
"#);
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

        if let Some(ref def) = receipt.nearest_defeater {
            let _ = write!(html, r#"<h2>Adversarial Reverse-Stress Defeater Boundary</h2>
<div class="callout callout-warn">
<strong>Nearest Defeater Located:</strong> Family <code>{}</code> at plausibility distance <strong>{:.2}</strong> (Peak Drawdown: {:.1}%). Predicate: <code>{}</code>
</div>"#, def.family, def.plausibility_distance, def.peak_drawdown_pct, def.failure_predicate);
        }

        let _ = write!(html, r#"<div style="margin-top: 32px; font-size: 11px; color: #64748b; border-top: 1px solid #2d3b4f; padding-top: 12px;">
Evaluated at: {} ns | Duration: {:.3}s | Verified digest: <code>{}</code>
</div>
</div>
</body>
</html>"#, receipt.evaluated_at_timestamp_ns, receipt.evaluation_duration_sec, verified.digest());

        html
    }

    /// Render forensic HTML from a raw receipt, verifying first.
    ///
    /// On an unverifiable receipt this returns HTML that says so in the verdict
    /// position instead of returning nothing. A missing report is how an
    /// unverified claim turns into a remembered clean one; a loudly UNVERIFIED
    /// report is not.
    pub fn render_html_verifying(
        receipt: &BenchmarkReceipt,
        projection: Option<&CapitalOutcomeProjection>,
    ) -> String {
        match VerifiedReceipt::verify(receipt, true) {
            Ok(verified) => Self::render_html(&verified, projection),
            Err(error) => Self::render_unverified(receipt, &error),
        }
    }

    /// Degenerate report for a receipt that failed verification: identity plus
    /// the failure, and nothing that could be mistaken for a score.
    fn render_unverified(receipt: &BenchmarkReceipt, error: &ReceiptVerificationError) -> String {
        format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>REPORT BLOCKED - {0}</title></head>
<body style="font-family: monospace; background: #0f141c; color: #e1e7f0; padding: 24px;">
<h1>REPORT BLOCKED: RECEIPT UNVERIFIED</h1>
<div style="border-left: 4px solid #ef4444; padding: 12px 16px; background: #192330;">
<strong>No capability score, certificate, or projection is rendered.</strong><br><br>
Policy: <code>{1}</code><br>
Receipt: <code>{0}</code><br>
Digest generation: <code>{2}</code><br>
Stored digest: <code>{3}</code><br>
Verification failure: <code>{4}</code>
</div>
<p style="color:#94a3b8; font-size: 12px;">A report must not be produced from a receipt whose digest
cannot be recomputed from its own contents (#328 R2). Re-run the evaluation or
restore the ledger row from an authoritative append-only copy.</p>
</body>
</html>"#,
            receipt.receipt_id,
            receipt.policy_id,
            receipt.digest_version,
            receipt.receipt_digest,
            error,
        )
    }
}
