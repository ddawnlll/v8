//! Portfolio State, Open Positions, Contingent Orders, Exposure Limits, and Portfolio Heat.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §3.4, §6.2, Decisions D-110.

use serde::{Deserialize, Serialize};

/// Order type representation for contingent and active orders.
#[allow(dead_code)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
    StopMarket,
    TakeProfitMarket,
}

/// Active open order in the exchange order queue.
#[allow(dead_code)]
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OpenOrder {
    pub order_id: String,
    pub candidate_id: String,
    pub symbol: String,
    pub order_type: OrderType,
    pub price: f64,
    pub quantity: f64,
    pub reduce_only: bool,
}

/// Active open perpetual position.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OpenPosition {
    pub position_id: String,
    pub candidate_id: String,
    pub symbol: String,
    pub direction: String, // "LONG" or "SHORT"
    pub entry_price: f64,
    pub quantity: f64,
    pub initial_margin_usdt: f64,
    pub isolated_margin_usdt: f64,
    pub leverage: u32,
    pub entry_time: i64,
    pub stop_loss_price: f64,
    pub take_profit_price: Option<f64>,
    pub liquidation_price: f64,
    pub cum_funding_usdt: f64,
}

impl OpenPosition {
    /// Computes mark-to-market unrealized PnL in USDT.
    pub fn unrealized_pnl(&self, current_price: f64) -> f64 {
        if self.direction == "LONG" {
            (current_price - self.entry_price) * self.quantity
        } else {
            (self.entry_price - current_price) * self.quantity
        }
    }

    /// Nominal risk in USDT (distance to protective stop loss * quantity).
    pub fn nominal_risk_usdt(&self) -> f64 {
        (self.entry_price - self.stop_loss_price).abs() * self.quantity
    }
}

/// Dynamic Portfolio State at decision epoch t.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PortfolioState {
    pub positions: Vec<OpenPosition>,
    pub open_orders: Vec<OpenOrder>,
    pub maintenance_margin_usdt: f64,
    pub portfolio_heat_r: f64,
    pub max_concurrency: usize,
    pub max_heat_limit: f64,
}

impl PortfolioState {
    pub fn new(max_concurrency: usize, max_heat_limit: f64) -> Self {
        Self {
            positions: Vec::new(),
            open_orders: Vec::new(),
            maintenance_margin_usdt: 0.0,
            portfolio_heat_r: 0.0,
            max_concurrency,
            max_heat_limit,
        }
    }

    /// Total notional exposure across all positions at current prices.
    #[allow(dead_code)]
    pub fn total_notional(&self, current_price: f64) -> f64 {
        self.positions.iter().map(|p| p.quantity * current_price).sum()
    }

    /// Total floating unrealized PnL across active positions.
    pub fn total_unrealized_pnl(&self, current_price: f64) -> f64 {
        self.positions.iter().map(|p| p.unrealized_pnl(current_price)).sum()
    }

    /// Total dollar risk locked in protective stops.
    pub fn total_nominal_risk_usdt(&self) -> f64 {
        self.positions.iter().map(|p| p.nominal_risk_usdt()).sum()
    }

    /// Updates portfolio heat metric (sum of stop risks divided by equity).
    pub fn update_portfolio_heat(&mut self, equity: f64) {
        if equity <= 0.0 {
            self.portfolio_heat_r = 1.0;
        } else {
            self.portfolio_heat_r = self.total_nominal_risk_usdt() / equity;
        }
    }

    /// Checks if a new candidate position is admissible under concurrency and heat limits.
    #[allow(dead_code)]
    pub fn can_admit_position(&self, additional_risk_usdt: f64, equity: f64) -> Result<(), &'static str> {
        if self.positions.len() >= self.max_concurrency {
            return Err("CAPITAL_CONSTRAINT_REJECTION");
        }
        if equity > 0.0 {
            let next_heat = (self.total_nominal_risk_usdt() + additional_risk_usdt) / equity;
            if next_heat > self.max_heat_limit + 1e-9 {
                return Err("PORTFOLIO_HEAT_EXCEEDED");
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_position_unrealized_pnl() {
        let pos_long = OpenPosition {
            position_id: "pos_1".into(),
            candidate_id: "c_1".into(),
            symbol: "BTCUSDT".into(),
            direction: "LONG".into(),
            entry_price: 50_000.0,
            quantity: 0.1,
            initial_margin_usdt: 500.0,
            isolated_margin_usdt: 500.0,
            leverage: 10,
            entry_time: 1000,
            stop_loss_price: 49_000.0,
            take_profit_price: Some(52_000.0),
            liquidation_price: 45_000.0,
            cum_funding_usdt: 0.0,
        };

        // Long PnL at 51,000 = (51000 - 50000) * 0.1 = +100 USDT
        assert_eq!(pos_long.unrealized_pnl(51_000.0), 100.0);
        // Nominal risk = (50000 - 49000) * 0.1 = 100 USDT
        assert_eq!(pos_long.nominal_risk_usdt(), 100.0);
    }
}
