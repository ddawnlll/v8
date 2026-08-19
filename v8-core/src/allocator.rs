//! Physical Risk Budget Allocator, Lot Discretization, Concurrency Gating,
//! and Canonical Rejection Emission.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §6, Decisions D-108, D-109.

use crate::account::AccountState;
use crate::portfolio::PortfolioState;
use crate::venue::VenueContract;
use serde::{Deserialize, Serialize};

/// Canonical Typed Rejection Taxonomy (VENUE_AND_CAPITAL_SIMULATION_SPEC §6.2, D-108).
#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AllocationRejectionReason {
    INSUFFICIENT_AVAILABLE_BALANCE,
    MIN_NOTIONAL_REJECTED,
    QUANTITY_ROUNDS_TO_ZERO,
    MARGIN_LIMIT_EXCEEDED,
    LEVERAGE_CONSTRAINT,
    PORTFOLIO_HEAT_EXCEEDED,
    CAPITAL_CONSTRAINT_REJECTION,
    ISOLATED_MARGIN_ONLY,
    INVALID_GEOMETRY,
}

impl AllocationRejectionReason {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::INSUFFICIENT_AVAILABLE_BALANCE => "INSUFFICIENT_AVAILABLE_BALANCE",
            Self::MIN_NOTIONAL_REJECTED => "MIN_NOTIONAL_REJECTED",
            Self::QUANTITY_ROUNDS_TO_ZERO => "QUANTITY_ROUNDS_TO_ZERO",
            Self::MARGIN_LIMIT_EXCEEDED => "MARGIN_LIMIT_EXCEEDED",
            Self::LEVERAGE_CONSTRAINT => "LEVERAGE_CONSTRAINT",
            Self::PORTFOLIO_HEAT_EXCEEDED => "PORTFOLIO_HEAT_EXCEEDED",
            Self::CAPITAL_CONSTRAINT_REJECTION => "CAPITAL_CONSTRAINT_REJECTION",
            Self::ISOLATED_MARGIN_ONLY => "ISOLATED_MARGIN_ONLY",
            Self::INVALID_GEOMETRY => "INVALID_GEOMETRY",
        }
    }
}

/// Approved and validated legal order request ready for exchange simulation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LegalOrderRequest {
    pub candidate_id: String,
    pub symbol: String,
    pub direction: String,
    pub quantity: f64,
    pub entry_price: f64,
    pub stop_loss_price: f64,
    pub take_profit_price: Option<f64>,
    pub initial_margin_usdt: f64,
    pub isolated_margin_usdt: f64,
    pub leverage: u32,
    pub expiry_bars: usize,
    pub nominal_risk_usdt: f64,
}

/// Physical Risk Budget Allocator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskBudgetAllocator {
    pub risk_fraction: f64,
    pub policy_max_leverage: u32,
    pub max_concurrency: usize,
    pub max_heat: f64,
}

impl Default for RiskBudgetAllocator {
    fn default() -> Self {
        Self {
            risk_fraction: 0.005, // 0.5% risk per trade default (D-109)
            policy_max_leverage: 10,
            max_concurrency: 3,
            max_heat: 0.05, // 5% max heat
        }
    }
}

impl RiskBudgetAllocator {
    pub fn new(risk_fraction: f64, policy_max_leverage: u32, max_concurrency: usize, max_heat: f64) -> Self {
        Self {
            risk_fraction,
            policy_max_leverage,
            max_concurrency,
            max_heat,
        }
    }

    /// Evaluates candidate geometry against venue contract and account state.
    pub fn allocate(
        &self,
        candidate_id: &str,
        symbol: &str,
        direction: &str,
        raw_entry_price: f64,
        raw_stop_loss_price: f64,
        raw_take_profit_price: Option<f64>,
        expiry_bars: usize,
        contract: &VenueContract,
        account: &AccountState,
        portfolio: &PortfolioState,
    ) -> Result<LegalOrderRequest, AllocationRejectionReason> {
        // 1. Check concurrency capacity
        if portfolio.positions.len() >= self.max_concurrency {
            return Err(AllocationRejectionReason::CAPITAL_CONSTRAINT_REJECTION);
        }

        // 2. Validate price delta to stop
        let delta_p_stop = (raw_entry_price - raw_stop_loss_price).abs();
        if delta_p_stop <= 1e-9 {
            return Err(AllocationRejectionReason::INVALID_GEOMETRY);
        }

        let equity = account.equity_usdt();
        if equity <= 0.0 {
            return Err(AllocationRejectionReason::INSUFFICIENT_AVAILABLE_BALANCE);
        }

        // 3. Compute nominal risk budget B_USDT = Equity * f_risk
        let risk_budget_usdt = equity * self.risk_fraction;

        // 4. Raw quantity Q_raw = B_USDT / ΔP_stop
        let raw_qty = risk_budget_usdt / delta_p_stop;

        // 5. Lot-step discretization
        let step_size = contract.lot_size_filter.step_size;
        if raw_qty < step_size / 2.0 {
            return Err(AllocationRejectionReason::QUANTITY_ROUNDS_TO_ZERO);
        }

        let eff_qty = contract.discretize_quantity(raw_qty);
        if eff_qty < step_size {
            return Err(AllocationRejectionReason::QUANTITY_ROUNDS_TO_ZERO);
        }

        // 6. Price discretization
        let eff_entry_price = contract.discretize_price(raw_entry_price);
        let eff_stop_loss = contract.discretize_price(raw_stop_loss_price);
        let eff_take_profit = raw_take_profit_price.map(|tp| contract.discretize_price(tp));

        // 7. Notional & Min Notional Check
        let notional = eff_entry_price * eff_qty;
        if notional < contract.min_notional {
            return Err(AllocationRejectionReason::MIN_NOTIONAL_REJECTED);
        }

        // 8. Leverage Brackets
        let bracket = contract.bracket_for_notional(notional);
        if notional > bracket.notional_cap {
            return Err(AllocationRejectionReason::MARGIN_LIMIT_EXCEEDED);
        }

        let leverage = self.policy_max_leverage.min(bracket.max_leverage);
        if leverage == 0 {
            return Err(AllocationRejectionReason::LEVERAGE_CONSTRAINT);
        }

        // 9. Initial Margin Check
        let initial_margin = contract.initial_margin(notional, leverage);
        if initial_margin > account.available_balance_usdt() + 1e-9 {
            return Err(AllocationRejectionReason::INSUFFICIENT_AVAILABLE_BALANCE);
        }

        // 10. Portfolio Heat Check
        let nominal_risk = eff_qty * (eff_entry_price - eff_stop_loss).abs();
        if portfolio.can_admit_position(nominal_risk, equity).is_err() {
            return Err(AllocationRejectionReason::PORTFOLIO_HEAT_EXCEEDED);
        }

        Ok(LegalOrderRequest {
            candidate_id: candidate_id.to_string(),
            symbol: symbol.to_string(),
            direction: direction.to_string(),
            quantity: eff_qty,
            entry_price: eff_entry_price,
            stop_loss_price: eff_stop_loss,
            take_profit_price: eff_take_profit,
            initial_margin_usdt: initial_margin,
            isolated_margin_usdt: initial_margin,
            leverage,
            expiry_bars,
            nominal_risk_usdt: nominal_risk,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_allocator_step_size_rounding() {
        let alloc = RiskBudgetAllocator::default();
        let contract = VenueContract::binance_btcusdt_perpetual();
        let acct = AccountState::new(100.0); // 100 USDT equity -> 0.50 USDT risk budget
        let port = PortfolioState::new(3, 0.05);

        // Entry 60000, Stop 50000 -> ΔP = 10000. Q_raw = 0.50 / 10000 = 0.00005 BTC < 0.0005 (step/2) -> rounds to zero
        let res = alloc.allocate(
            "c1", "BTCUSDT", "LONG", 60_000.0, 50_000.0, None, 8, &contract, &acct, &port,
        );
        assert_eq!(res.unwrap_err(), AllocationRejectionReason::QUANTITY_ROUNDS_TO_ZERO);
    }

    #[test]
    fn test_allocator_min_notional_rejection() {
        let alloc = RiskBudgetAllocator::default();
        let contract = VenueContract::binance_btcusdt_perpetual();
        let acct = AccountState::new(1000.0); // 1000 USDT equity -> 5.0 USDT risk budget
        let port = PortfolioState::new(3, 0.05);

        // Entry 2000, Stop 1000 -> ΔP = 1000. Q_raw = 5.0 / 1000 = 0.005 BTC.
        // Notional = 0.005 * 2000 = 10.0 USDT >= 5.0 -> Admitted
        let res = alloc.allocate(
            "c1", "BTCUSDT", "LONG", 2000.0, 1000.0, None, 8, &contract, &acct, &port,
        );
        assert!(res.is_ok());

        // Entry 800, Stop 100 -> ΔP = 700. Q_raw = 5.0 / 700 = 0.00714 -> Q_eff = 0.007.
        // Notional = 0.007 * 800 = 5.6 USDT >= 5.0 -> Admitted
        let res2 = alloc.allocate(
            "c2", "BTCUSDT", "LONG", 800.0, 100.0, None, 8, &contract, &acct, &port,
        );
        assert!(res2.is_ok());

        // Entry 400, Stop 100 -> ΔP = 300. Q_raw = 5.0 / 300 = 0.0166 -> Q_eff = 0.016.
        // Notional = 0.016 * 400 = 6.4 >= 5.0.
        // What if Entry 3000, Stop 1000 -> ΔP = 2000. Q_raw = 5.0 / 2000 = 0.0025 -> Q_eff = 0.002.
        // Notional = 0.002 * 3000 = 6.0 USDT.
        // If Entry 4000, Stop 1000 -> ΔP = 3000. Q_raw = 5.0 / 3000 = 0.00166 -> Q_eff = 0.001.
        // Notional = 0.001 * 4000 = 4.0 USDT < 5.0 USDT -> MIN_NOTIONAL_REJECTED
        let res3 = alloc.allocate(
            "c3", "BTCUSDT", "LONG", 4000.0, 1000.0, None, 8, &contract, &acct, &port,
        );
        assert_eq!(res3.unwrap_err(), AllocationRejectionReason::MIN_NOTIONAL_REJECTED);
    }
}
