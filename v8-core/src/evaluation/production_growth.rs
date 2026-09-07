// QUARANTINE (W2 / V8.6 Phase 1): test-only surface, sole consumer is
// v8-core/tests/production_growth_contract.rs. Growth requires authority
// (`needs:authority`); do not wire into production gates.
//! Production Growth Contract & LGNG Geometric Growth Algebra (D-147, D-149, M0_CLOSED, M2).
//!
//! Enforces:
//! 1. Long-Horizon Geometric Net Growth (LGNG):
//!    LGNG = (1 / T) * sum(ln(1 + delta_equity_after_cost / equity_prior))
//! 2. Anti-Target-Chasing Rule (Rule 3, 44): Weekly/calendar target shortfalls
//!    CANNOT alter entry/exit decision thresholds, expand risk budgets, or force trades.
//! 3. Deterministic PGC schema with strict `INCOMPLETE_ECONOMICS` fail-closed semantics.

use serde::{Deserialize, Serialize};

/// Canonical error for economic calculation failures.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ProductionGrowthError {
    IncompleteEconomics(&'static str),
    MaxDrawdownExceeded { current_pct: f64, max_allowed_pct: f64 },
    NegativeGrowthRate { lgng: f64 },
    TargetChasingDetected(&'static str),
}

impl std::fmt::Display for ProductionGrowthError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::IncompleteEconomics(msg) => write!(f, "INCOMPLETE_ECONOMICS: {msg}"),
            Self::MaxDrawdownExceeded { current_pct, max_allowed_pct } => {
                write!(f, "MAX_DRAWDOWN_EXCEEDED: current {current_pct:.2}% exceeds max {max_allowed_pct:.2}%")
            }
            Self::NegativeGrowthRate { lgng } => write!(f, "NEGATIVE_GROWTH_RATE: LGNG is {lgng:.6}"),
            Self::TargetChasingDetected(msg) => write!(f, "TARGET_CHASING_DETECTED: {msg}"),
        }
    }
}

impl std::error::Error for ProductionGrowthError {}

/// Deterministic Production Growth Contract (PGC).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProductionGrowthContract {
    pub initial_balance_usdt: f64,
    pub risk_fraction_per_trade: f64,
    pub max_leverage: u32,
    pub max_concurrency: usize,
    pub max_heat: f64,
    pub max_allowed_drawdown_pct: f64,
    pub taker_fee_rate: f64,
    pub slippage_margin_rate: f64,
    pub minimum_required_lgng: f64,
}

impl Default for ProductionGrowthContract {
    fn default() -> Self {
        Self {
            initial_balance_usdt: 1000.0,
            risk_fraction_per_trade: 0.005,
            max_leverage: 10,
            max_concurrency: 3,
            max_heat: 0.05,
            max_allowed_drawdown_pct: 15.0,
            taker_fee_rate: 0.0005,
            slippage_margin_rate: 0.0002,
            minimum_required_lgng: 0.0,
        }
    }
}

impl ProductionGrowthContract {
    /// Computes Long-Horizon Geometric Net Growth (LGNG) over a series of after-cost equity states.
    /// Invariant: Missing equity observations fail closed to IncompleteEconomics.
    pub fn compute_lgng(&self, equity_curve: &[f64]) -> Result<f64, ProductionGrowthError> {
        if equity_curve.len() < 2 {
            return Err(ProductionGrowthError::IncompleteEconomics(
                "EQUITY_CURVE_TOO_SHORT_FOR_LGNG",
            ));
        }

        let mut sum_log_growth = 0.0;
        let mut peak_equity = equity_curve[0];
        let mut max_dd_pct = 0.0;

        for i in 1..equity_curve.len() {
            let prev = equity_curve[i - 1];
            let curr = equity_curve[i];

            if prev <= 0.0 || curr <= 0.0 {
                return Err(ProductionGrowthError::IncompleteEconomics(
                    "NON_POSITIVE_EQUITY_ENCOUNTERED",
                ));
            }

            // Drawdown tracking
            if curr > peak_equity {
                peak_equity = curr;
            } else {
                let dd_pct = (peak_equity - curr) / peak_equity * 100.0;
                if dd_pct > max_dd_pct {
                    max_dd_pct = dd_pct;
                }
            }

            let period_return = (curr - prev) / prev;
            let log_growth = (1.0 + period_return).ln();
            sum_log_growth += log_growth;
        }

        if max_dd_pct > self.max_allowed_drawdown_pct {
            return Err(ProductionGrowthError::MaxDrawdownExceeded {
                current_pct: max_dd_pct,
                max_allowed_pct: self.max_allowed_drawdown_pct,
            });
        }

        let t = (equity_curve.len() - 1) as f64;
        let lgng = sum_log_growth / t;

        Ok(lgng)
    }

    /// Evaluates anti-target-chasing invariant: ensures decision thresholds are invariant to calendar shortfalls.
    pub fn verify_anti_target_chasing(
        &self,
        base_decision_threshold: f64,
        shortfall_pct: f64,
        adjusted_decision_threshold: f64,
    ) -> Result<(), ProductionGrowthError> {
        if (adjusted_decision_threshold - base_decision_threshold).abs() > 1e-9 {
            return Err(ProductionGrowthError::TargetChasingDetected(
                "DECISION_THRESHOLD_MUTATED_DUE_TO_CALENDAR_TARGET_SHORTFALL",
            ));
        }
        Ok(())
    }
}
