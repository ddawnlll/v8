//! 14 System-Level Robustness Metrics Vector (D-147, D-149, M3).
//!
//! Evaluates the full-system performance across parameterized stress environments.

use serde::{Deserialize, Serialize};

/// 14-dimensional system robustness vector.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SystemRobustnessVector {
    pub scenario_failure_fraction: f64,
    pub tail_capture_efficiency: f64,
    pub friction_retention_ratio: f64,
    pub recovery_horizon_bars: usize,
    pub max_adverse_excursion_pct: f64,
    pub ruin_margin_pct: f64,
    pub slippage_fragility_score: f64,
    pub turnover_efficiency: f64,
    pub capital_utilization_pct: f64,
    pub funding_drag_ratio: f64,
    pub regime_stability_score: f64,
    pub habitat_selectivity_score: f64,
    pub expert_displacement_rate: f64,
    pub cashflow_discrepancy_usdt: f64,
}

impl SystemRobustnessVector {
    /// Invariant: Cashflow discrepancy must be zero for valid double-entry reconciliation.
    pub fn is_double_entry_reconciled(&self) -> bool {
        self.cashflow_discrepancy_usdt.abs() < 1e-6
    }
}
