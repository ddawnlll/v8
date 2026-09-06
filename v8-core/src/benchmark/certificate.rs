//! V8 Evidence Dashboard & Policy Certificate (D-153).
//!
//! Enforces:
//! - Epistemic separation between Research Capability, Robustness, and Capital Projection.
//! - Multiplicative Readiness Index:
//!   Readiness = (Cap / 100) * EvidenceMultiplier * (Robustness / 100) * (Economic / 100) * 100
//! - Binary Robustness Seal & Hard Gate Vector verification.
//! - Multi-population evidence topology (12-month quad tape as single diagnostic cell).
//! - Terminal ASCII and HTML certificate rendering.

use serde::{Deserialize, Serialize};
use crate::benchmark::minerva::MinervaRobustness;
use crate::benchmark::projection::{CapitalOutcomeProjection, MonteCarloFutureResult};
use crate::benchmark::receipt::BenchmarkReceipt;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PolicyCertificate {
    pub policy_id: String,
    pub receipt_id: String,
    pub status: String,
    pub research_capability_score: f64,
    pub evidence_multiplier: f64,
    pub minerva_robustness_score: f64,
    pub robustness_seal_status: String,
    pub economic_score: f64,
    pub readiness_index: f64,
    pub quad_tape_role: String,
    pub minerva: Option<MinervaRobustness>,
    pub monte_carlo: Option<MonteCarloFutureResult>,
}

impl PolicyCertificate {
    /// Generates a PolicyCertificate from evaluated benchmark artifacts.
    pub fn generate(
        receipt: &BenchmarkReceipt,
        projection: Option<&CapitalOutcomeProjection>,
    ) -> Self {
        let cap_score = (receipt.composite_capability_score * 100.0).clamp(0.0, 100.0);
        let evidence_multiplier = receipt.coverage_factor.clamp(0.10, 1.0);

        let minerva = receipt.minerva_robustness.clone();
        let (rob_score, seal_granted, seal_status) = match minerva.as_ref() {
            Some(m) => (m.effective_score, m.seal_granted, m.seal_status.clone()),
            None => (50.0, false, "SEAL_DENIED_NO_MINERVA_RUN".into()),
        };

        // Derive economic score from projection or receipt observations (0.0 .. 100.0)
        let economic_score = if let Some(proj) = projection {
            if let Some(ref mc) = proj.monte_carlo_futures {
                // Derived from median return, ruin penalty, and drawdown
                let ret_score = ((mc.p50_return_pct + 20.0) / 40.0).clamp(0.0, 1.0);
                let ruin_safety = (1.0 - (mc.risk_of_ruin_pct / 100.0)).clamp(0.0, 1.0);
                ((ret_score * 0.60 + ruin_safety * 0.40) * 100.0).round()
            } else if let Some(median_band) = proj.outcome_bands.iter().find(|b| (b.percentile - 0.50).abs() < 0.01) {
                ((median_band.return_bps / 500.0).clamp(0.0, 1.0) * 100.0).round()
            } else {
                60.0
            }
        } else {
            60.0
        };

        // Multiplicative Readiness Index:
        // Readiness = (Cap / 100) * EvidenceMultiplier * (Rob / 100) * (Econ / 100) * 100
        let readiness = (cap_score / 100.0)
            * evidence_multiplier
            * (rob_score / 100.0)
            * (economic_score / 100.0)
            * 100.0;

        let is_production_approved = readiness >= 80.0
            && seal_granted
            && receipt.projection_grade.allows_forward_probability()
            && receipt.gate_vector.all_passed();

        let status = if is_production_approved {
            "STATUS: Production Ready".to_string()
        } else {
            "STATUS: Research Candidate NOT Production Approved".to_string()
        };

        let quad_tape_role = "HISTORICAL DIAGNOSTIC CELL (Non-universal evaluation fold)".to_string();

        let monte_carlo = projection.and_then(|p| p.monte_carlo_futures.clone());

        Self {
            policy_id: receipt.policy_id.clone(),
            receipt_id: receipt.receipt_id.clone(),
            status,
            research_capability_score: cap_score,
            evidence_multiplier,
            minerva_robustness_score: rob_score,
            robustness_seal_status: seal_status,
            economic_score,
            readiness_index: (readiness * 10.0).round() / 10.0,
            quad_tape_role,
            minerva,
            monte_carlo,
        }
    }

    /// Renders clean terminal ASCII certificate matching user specifications.
    pub fn render_ascii(&self) -> String {
        let bar = |val: f64, max: f64| -> String {
            let pct = (val / max).clamp(0.0, 1.0);
            let filled = (pct * 30.0).round() as usize;
            let empty = 30 - filled;
            format!("[{}{}]", "|".repeat(filled), ".".repeat(empty))
        };

        let mut out = String::new();
        out.push_str("======================================================================\n");
        out.push_str("               V8 EVIDENCE DASHBOARD & POLICY CERTIFICATE             \n");
        out.push_str("======================================================================\n");
        out.push_str(&format!("Policy Target:  {}\n", self.policy_id));
        out.push_str(&format!("Receipt Digest: {}\n", self.receipt_id));
        out.push_str(&format!("Final Verdict:  {}\n", self.status));
        out.push_str("----------------------------------------------------------------------\n");

        out.push_str("1. RESEARCH CAPABILITY SCORE (Infrastructure & Integrity):\n");
        out.push_str(&format!("   Score: {:>5.1} / 100  {}\n", self.research_capability_score, bar(self.research_capability_score, 100.0)));
        out.push_str(&format!("   Evidence Multiplier: {:.2}\n", self.evidence_multiplier));
        out.push_str("----------------------------------------------------------------------\n");

        out.push_str("2. ECONOMIC EVIDENCE & MINERVA ROBUSTNESS (arXiv:2608.23808):\n");
        out.push_str(&format!("   Minerva Score:  {:>5.1} / 100  {}\n", self.minerva_robustness_score, bar(self.minerva_robustness_score, 100.0)));
        out.push_str(&format!("   Robustness Seal: {}\n", self.robustness_seal_status));
        
        if let Some(ref m) = self.minerva {
            out.push_str("   Validation Gates:\n");
            out.push_str(&format!("     DSR Gate:    [{:>4}] (Margin: {:+.3})\n", m.gate_vector.dsr_gate.as_str(), m.margins.dsr_margin));
            out.push_str(&format!("     PBO Gate:    [{:>4}] (Margin: {:+.3})\n", m.gate_vector.pbo_gate.as_str(), m.margins.pbo_margin));
            out.push_str(&format!("     SPA Gate:    [{:>4}] (Margin: {:+.3})\n", m.gate_vector.spa_gate.as_str(), m.margins.spa_margin));
            out.push_str(&format!("     MinTRL Gate: [{:>4}] (Margin: {:+.1} days)\n", m.gate_vector.min_trl_gate.as_str(), m.margins.min_trl_margin));
            out.push_str(&format!("     Regime Gate: [{:>4}] (Margin: {:+.1} bps)\n", m.gate_vector.regime_stability_gate.as_str(), m.margins.regime_stability_margin));
        }

        out.push_str(&format!("   Evidence Topology: {}\n", self.quad_tape_role));
        out.push_str("----------------------------------------------------------------------\n");

        out.push_str("3. RISK-ADJUSTED CAPITAL PROJECTION ($1,000 Initial, 1-Year Horizon):\n");
        if let Some(ref mc) = self.monte_carlo {
            out.push_str(&format!("   10,000 Monte Carlo Futures (Horizon: {} trades):\n", mc.horizon_trades));
            out.push_str(&format!("     P5:   ${:>7.2}  ({:>+6.1}%)\n", mc.p5_terminal_usd, mc.p5_return_pct));
            out.push_str(&format!("     P25:  ${:>7.2}  ({:>+6.1}%)\n", mc.p25_terminal_usd, mc.p25_return_pct));
            out.push_str(&format!("     P50:  ${:>7.2}  ({:>+6.1}%) [Median]\n", mc.p50_terminal_usd, mc.p50_return_pct));
            out.push_str(&format!("     P75:  ${:>7.2}  ({:>+6.1}%)\n", mc.p75_terminal_usd, mc.p75_return_pct));
            out.push_str(&format!("     P95:  ${:>7.2}  ({:>+6.1}%)\n", mc.p95_terminal_usd, mc.p95_return_pct));
            let worst_usd = mc.initial_capital_usd * (1.0 + mc.worst_scenario_return_pct / 100.0);
            let best_usd = mc.initial_capital_usd * (1.0 + mc.best_scenario_return_pct / 100.0);
            out.push_str(&format!("     Worst: ${:>7.2} ({:>+6.1}%)  Best: ${:>7.2} ({:>+6.1}%)\n", worst_usd, mc.worst_scenario_return_pct, best_usd, mc.best_scenario_return_pct));
            out.push_str(&format!("     Risk of Ruin (Drawdown >= 30%): {:.1}%\n", mc.risk_of_ruin_pct));
            out.push_str(&format!("   Notice: {}\n", mc.conditional_notice));
        } else {
            out.push_str("   [Underpowered sample or diagnostic run: extreme percentiles suppressed]\n");
        }

        out.push_str("----------------------------------------------------------------------\n");
        out.push_str(&format!("READINESS INDEX: {:>5.1} / 100\n", self.readiness_index));
        out.push_str(&format!(
            "Formula: Cap ({:.1}) * Evidence ({:.2}) * Robustness ({:.1}) * Economic ({:.1}) / 100^2\n",
            self.research_capability_score, self.evidence_multiplier, self.minerva_robustness_score, self.economic_score
        ));
        out.push_str("======================================================================\n");

        out
    }
}
