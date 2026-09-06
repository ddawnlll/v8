//! MinervaScore Robustness Engine & Binary Robustness Seal (arXiv:2608.23808).
//!
//! Enforces:
//! - Aggregation of DSR, PBO, SPA, MinTRL, and Regime Stability signed margins.
//! - Non-compensable Binary Robustness Seal: score >= 80 and certification
//!   strictly requires passing all 5 underlying validation gates.
//! - Gate failure hard-caps the effective robustness score below 80 and denies the seal.
//! - Post-selection certification only (never an optimization target).
//! - PRUDEX-Compass (TMLR 2023) 6-axis profile mapping.

use serde::{Deserialize, Serialize};
use crate::benchmark::types::GateState;

/// Signed Margins from Academic Thresholds (arXiv:2608.23808)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MinervaMargins {
    /// Deflated Sharpe Ratio margin: DSR - 0.95 (positive is PASS)
    pub dsr_margin: f64,
    /// Probability of Backtest Overfitting margin: 0.50 - PBO (positive is PASS)
    pub pbo_margin: f64,
    /// Superior Predictive Ability p-value margin: 0.05 - p_SPA (positive is PASS)
    pub spa_margin: f64,
    /// Minimum Track Record Length margin: actual_length_days - min_trl_days (positive is PASS)
    pub min_trl_margin: f64,
    /// Regime Stability margin: worst_regime_return_bps - regime_floor_bps (positive is PASS)
    pub regime_stability_margin: f64,
}

/// Hard validation gates for Minerva robustness
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MinervaGateVector {
    pub dsr_gate: GateState,
    pub pbo_gate: GateState,
    pub spa_gate: GateState,
    pub min_trl_gate: GateState,
    pub regime_stability_gate: GateState,
}

impl MinervaGateVector {
    pub fn all_passed(&self) -> bool {
        self.dsr_gate.is_pass()
            && self.pbo_gate.is_pass()
            && self.spa_gate.is_pass()
            && self.min_trl_gate.is_pass()
            && self.regime_stability_gate.is_pass()
    }

    pub fn failed_gate_count(&self) -> usize {
        let gates = [
            &self.dsr_gate,
            &self.pbo_gate,
            &self.spa_gate,
            &self.min_trl_gate,
            &self.regime_stability_gate,
        ];
        gates.iter().filter(|g| !g.is_pass()).count()
    }
}

/// PRUDEX-Compass Profile (TMLR 2023)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrudexCompass {
    pub profitability: f64,  // P: Annualized return / Profit factor
    pub risk: f64,           // R: Drawdown resistance / CVaR
    pub universality: f64,   // U: Cross-asset & regime breadth
    pub diversity: f64,      // D: Strategy decorrelation
    pub reliability: f64,    // E: Statistical credibility (DSR / SPA)
    pub explainability: f64, // X: Structural simplicity / Parameter stability
}

impl Default for PrudexCompass {
    fn default() -> Self {
        Self {
            profitability: 0.0,
            risk: 0.0,
            universality: 0.0,
            diversity: 0.0,
            reliability: 0.0,
            explainability: 0.0,
        }
    }
}

/// Minerva Robustness Outcome
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MinervaRobustness {
    /// Raw mathematical score before non-compensable gating (0.0 .. 100.0)
    pub raw_score: f64,
    /// Effective score: hard-capped strictly below 80.0 if any gate fails
    pub effective_score: f64,
    /// Binary Robustness Seal: granted ONLY if all 5 gates pass AND effective_score >= 80.0
    pub seal_granted: bool,
    /// Human-readable status of the robustness seal
    pub seal_status: String,
    /// Gate vector evaluation
    pub gate_vector: MinervaGateVector,
    /// Detailed signed margins
    pub margins: MinervaMargins,
    /// PRUDEX-Compass profile mapping
    pub prudex_compass: PrudexCompass,
}

pub struct MinervaEvaluator;

impl MinervaEvaluator {
    /// Evaluates raw backtest metrics into a Minerva Robustness profile.
    ///
    /// Parameters:
    /// - `dsr`: Deflated Sharpe Ratio (expected >= 0.95)
    /// - `pbo`: Probability of Backtest Overfitting (expected < 0.50)
    /// - `spa_p_value`: Hansen SPA p-value (expected <= 0.05)
    /// - `actual_track_days`: Evaluated track record length in days
    /// - `min_trl_days`: Bailey / López de Prado minimum required track record days
    /// - `worst_regime_return_bps`: Worst sub-regime realized return in bps
    /// - `regime_floor_bps`: Acceptable drawdown/return floor in worst regime (e.g. -1500 bps = -15%)
    /// - `prudex`: Optional PRUDEX-Compass profile
    pub fn evaluate(
        dsr: f64,
        pbo: f64,
        spa_p_value: f64,
        actual_track_days: f64,
        min_trl_days: f64,
        worst_regime_return_bps: f64,
        regime_floor_bps: f64,
        prudex: Option<PrudexCompass>,
    ) -> MinervaRobustness {
        // Calculate signed margins
        let dsr_margin = dsr - 0.95;
        let pbo_margin = 0.50 - pbo;
        let spa_margin = 0.05 - spa_p_value;
        let min_trl_margin = actual_track_days - min_trl_days;
        let regime_stability_margin = worst_regime_return_bps - regime_floor_bps;

        // Individual gates (non-compensable)
        let dsr_gate = if dsr >= 0.95 { GateState::Pass } else { GateState::Blocked };
        let pbo_gate = if pbo < 0.50 { GateState::Pass } else { GateState::Blocked };
        let spa_gate = if spa_p_value <= 0.05 { GateState::Pass } else { GateState::Blocked };
        let min_trl_gate = if actual_track_days >= min_trl_days { GateState::Pass } else { GateState::Blocked };
        let regime_stability_gate = if worst_regime_return_bps >= regime_floor_bps { GateState::Pass } else { GateState::Blocked };

        let gate_vector = MinervaGateVector {
            dsr_gate,
            pbo_gate,
            spa_gate,
            min_trl_gate,
            regime_stability_gate,
        };

        // Normalize each margin to a [0.0, 1.0] sub-score
        // DSR: 0.95 -> 0.80, 0.99 -> 1.0, 0.50 -> 0.0
        let dsr_norm = ((dsr - 0.50) / 0.50).clamp(0.0, 1.0);
        // PBO: 0.0 -> 1.0, 0.50 -> 0.60, 1.0 -> 0.0
        let pbo_norm = ((1.0 - pbo) / 1.0).clamp(0.0, 1.0);
        // SPA: 0.0 -> 1.0, 0.05 -> 0.80, 0.50 -> 0.0
        let spa_norm = if spa_p_value <= 0.05 {
            0.80 + 0.20 * (1.0 - (spa_p_value / 0.05))
        } else {
            0.80 * (1.0 - ((spa_p_value - 0.05) / 0.95)).max(0.0)
        };
        // MinTRL: actual / min_trl, clamped to [0.0, 1.0]
        let min_trl_norm = if min_trl_days > 0.0 {
            (actual_track_days / min_trl_days).min(1.5) / 1.5
        } else {
            0.5
        };
        // Regime: margin relative to span (e.g. 2000 bps)
        let regime_norm = ((worst_regime_return_bps - regime_floor_bps + 2000.0) / 4000.0).clamp(0.0, 1.0);

        // Raw harmonic mean of the 5 robustness dimensions
        let weights = [0.25, 0.25, 0.20, 0.15, 0.15];
        let norms = [dsr_norm, pbo_norm, spa_norm, min_trl_norm, regime_norm];
        
        let mut inv_sum = 0.0;
        let mut w_sum = 0.0;
        for (i, &w) in weights.iter().enumerate() {
            let val = norms[i].max(0.01);
            inv_sum += w / val;
            w_sum += w;
        }
        let raw_harmonic = (w_sum / inv_sum).clamp(0.0, 1.0);
        let raw_score = (raw_harmonic * 100.0).round();

        // NON-COMPENSABLE HARD GATING:
        // If ANY gate fails:
        // 1. Seal is strictly DENIED
        // 2. Effective score is capped below 80.0 (maximum 79.0, or penalized further)
        let all_passed = gate_vector.all_passed();
        let (effective_score, seal_granted, seal_status) = if all_passed {
            if raw_score >= 80.0 {
                (raw_score, true, "SEAL_GRANTED: All 5 validation gates passed with score >= 80".into())
            } else {
                (raw_score, false, format!("SEAL_DENIED_SCORE_TOO_LOW: All gates passed but raw score ({:.0}) < 80", raw_score))
            }
        } else {
            // Cap at 79.0 or scale down by failed gate count
            let failed_count = gate_vector.failed_gate_count().max(1);
            let penalty_factor = (5.0 - failed_count as f64) / 5.0;
            let capped = raw_score.min(79.0) * penalty_factor;
            let status = format!(
                "SEAL_DENIED_GATE_FAILURE: {} of 5 hard gates failed (score capped to {:.0})",
                failed_count, capped
            );
            (capped.round(), false, status)
        };

        MinervaRobustness {
            raw_score,
            effective_score,
            seal_granted,
            seal_status,
            gate_vector,
            margins: MinervaMargins {
                dsr_margin,
                pbo_margin,
                spa_margin,
                min_trl_margin,
                regime_stability_margin,
            },
            prudex_compass: prudex.unwrap_or_default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_minerva_all_pass_seal_granted() {
        let rob = MinervaEvaluator::evaluate(
            0.98,   // DSR >= 0.95
            0.15,   // PBO < 0.50
            0.015,  // SPA <= 0.05
            365.0,  // Actual days
            180.0,  // MinTRL days
            150.0,  // Worst regime bps
            -500.0, // Floor bps
            None,
        );

        assert!(rob.gate_vector.all_passed());
        assert!(rob.raw_score >= 80.0);
        assert!(rob.seal_granted);
        assert_eq!(rob.seal_status, "SEAL_GRANTED: All 5 validation gates passed with score >= 80");
        assert!(rob.effective_score >= 80.0);
    }

    #[test]
    fn test_minerva_single_gate_failure_denies_seal_and_caps_score() {
        // High DSR, low PBO, but SPA fails (p=0.12 > 0.05)
        let rob = MinervaEvaluator::evaluate(
            0.99,
            0.10,
            0.12,   // FAILS SPA gate!
            365.0,
            180.0,
            200.0,
            -500.0,
            None,
        );

        assert!(!rob.gate_vector.all_passed());
        assert!(!rob.seal_granted);
        assert!(rob.effective_score < 80.0);
        assert!(rob.seal_status.starts_with("SEAL_DENIED_GATE_FAILURE"));
    }

    #[test]
    fn test_minerva_pbo_failure_denies_seal() {
        let rob = MinervaEvaluator::evaluate(
            0.96,
            0.65,   // FAILS PBO gate (0.65 >= 0.50)
            0.02,
            365.0,
            180.0,
            100.0,
            -500.0,
            None,
        );

        assert!(!rob.seal_granted);
        assert!(rob.effective_score < 80.0);
    }
}
