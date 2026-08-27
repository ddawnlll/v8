//! Friction Retention Curves & Fee/Slippage Sensitivity (D-147, D-149, M2).
//!
//! Models gross-to-net retention across variable taker commission schedules and market impact.

use serde::{Deserialize, Serialize};

/// Friction retention measurement.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FrictionRetentionProfile {
    pub gross_market_pnl: f64,
    pub taker_fees: f64,
    pub funding_cost: f64,
    pub slippage_cost: f64,
    pub net_pnl: f64,
    pub friction_retention_ratio: f64,
}

impl FrictionRetentionProfile {
    /// Computes retention profile from gross PnL and friction components.
    pub fn compute(gross_pnl: f64, taker_fees: f64, funding: f64, slippage: f64) -> Self {
        let total_friction = taker_fees + funding + slippage;
        let net_pnl = gross_pnl - total_friction;
        let friction_retention_ratio = if gross_pnl > 0.0 {
            net_pnl / gross_pnl
        } else {
            0.0
        };

        Self {
            gross_market_pnl: gross_pnl,
            taker_fees,
            funding_cost: funding,
            slippage_cost: slippage,
            net_pnl,
            friction_retention_ratio,
        }
    }
}
