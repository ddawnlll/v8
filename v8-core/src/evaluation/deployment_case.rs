//! Deployment-Equivalent Real-Tape Experiment Boundaries (D-147, D-149, M2).
//!
//! Models full execution physics, taker fee structures, slippage bounds, and capital allocation.

use serde::{Deserialize, Serialize};

/// Detailed outcome receipt from a deployment-equivalent evaluation case.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DeploymentEquivalentReceipt {
    pub receipt_id: String,
    pub symbol: String,
    pub trades_admitted: usize,
    pub trades_rejected: usize,
    pub initial_balance_usdt: f64,
    pub gross_market_pnl_usdt: f64,
    pub total_fee_drag_usdt: f64,
    pub total_funding_usdt: f64,
    pub total_slippage_usdt: f64,
    pub net_realized_profit_usdt: f64,
    pub max_drawdown_pct: f64,
    pub win_rate_pct: f64,
    pub profit_factor: f64,
    pub lgng_score: f64,
}

impl DeploymentEquivalentReceipt {
    /// Returns true if after-cost net profitability and growth are strictly positive.
    pub fn is_production_viable(&self) -> bool {
        self.net_realized_profit_usdt > 0.0 && self.lgng_score > 0.0 && self.profit_factor > 1.0
    }
}
