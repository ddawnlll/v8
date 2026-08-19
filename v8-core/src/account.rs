//! Financial Account State, Margin Management, VIP Fee Tiers, and Wallet Updates.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §3.3, §6, Decisions D-109, D-110.

use serde::{Deserialize, Serialize};

/// Margin mode (Cross vs Isolated).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MarginMode {
    Cross,
    Isolated,
}

/// VIP fee level (VIP0 to VIP9).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FeeTier {
    Vip0,
    Vip1,
    Vip2,
    Vip3,
    Vip4,
    Vip5,
    Vip6,
    Vip7,
    Vip8,
    Vip9,
}

impl FeeTier {
    /// Base maker/taker fee rates per Binance VIP schedule.
    pub fn rates(&self) -> (f64, f64) {
        match self {
            FeeTier::Vip0 => (0.0002, 0.0005),
            FeeTier::Vip1 => (0.00016, 0.0004),
            FeeTier::Vip2 => (0.00014, 0.00035),
            FeeTier::Vip3 => (0.00012, 0.00032),
            FeeTier::Vip4 => (0.00010, 0.00030),
            FeeTier::Vip5 => (0.00008, 0.00027),
            FeeTier::Vip6 => (0.00006, 0.00024),
            FeeTier::Vip7 => (0.00004, 0.00021),
            FeeTier::Vip8 => (0.00002, 0.00018),
            FeeTier::Vip9 => (0.00000, 0.00015),
        }
    }
}

/// Financial Account State at decision epoch t.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AccountState {
    pub wallet_balance_usdt: f64,
    pub unrealized_pnl_usdt: f64,
    pub initial_margin_usdt: f64,
    pub margin_mode: MarginMode,
    pub fee_tier: FeeTier,
    pub bnb_discount: bool,
}

impl AccountState {
    /// Constructs a new account with specified initial USDT balance.
    pub fn new(initial_balance: f64) -> Self {
        Self {
            wallet_balance_usdt: initial_balance,
            unrealized_pnl_usdt: 0.0,
            initial_margin_usdt: 0.0,
            margin_mode: MarginMode::Isolated,
            fee_tier: FeeTier::Vip0,
            bnb_discount: false,
        }
    }

    /// Total Account Equity: E_t = Wallet_Balance + Unrealized_PnL.
    pub fn equity_usdt(&self) -> f64 {
        self.wallet_balance_usdt + self.unrealized_pnl_usdt
    }

    /// Available Balance for new order margin: E_t - Initial_Margin.
    pub fn available_balance_usdt(&self) -> f64 {
        (self.equity_usdt() - self.initial_margin_usdt).max(0.0)
    }

    /// Current margin utilization ratio in percentage.
    pub fn margin_utilization_pct(&self) -> f64 {
        let equity = self.equity_usdt();
        if equity <= 0.0 {
            100.0
        } else {
            ((self.initial_margin_usdt / equity) * 100.0).clamp(0.0, 100.0)
        }
    }

    /// Effective fee rate (applying BNB discount if active: 10% off).
    pub fn effective_fee_rate(&self, is_maker: bool) -> f64 {
        let (maker, taker) = self.fee_tier.rates();
        let base = if is_maker { maker } else { taker };
        if self.bnb_discount {
            base * 0.90
        } else {
            base
        }
    }

    /// Locks collateral for an opened position.
    pub fn lock_margin(&mut self, margin: f64) -> Result<(), String> {
        if margin < 0.0 {
            return Err("Margin must be non-negative".to_string());
        }
        if margin > self.available_balance_usdt() + 1e-9 {
            return Err(format!(
                "Insufficient available balance: required {:.4} USDT, available {:.4} USDT",
                margin,
                self.available_balance_usdt()
            ));
        }
        self.initial_margin_usdt += margin;
        Ok(())
    }

    /// Releases collateral on position closure.
    pub fn release_margin(&mut self, margin: f64) {
        self.initial_margin_usdt = (self.initial_margin_usdt - margin).max(0.0);
    }

    /// Credits or debits realized gross market PnL.
    pub fn apply_realized_pnl(&mut self, pnl: f64) {
        self.wallet_balance_usdt += pnl;
    }

    /// Deducts trading commissions.
    pub fn deduct_fee(&mut self, fee: f64) {
        self.wallet_balance_usdt -= fee;
    }

    /// Applies 8-hour funding rate cashflow (+ received, - paid).
    pub fn apply_funding(&mut self, funding: f64) {
        self.wallet_balance_usdt += funding;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_margin_locking_and_equity() {
        let mut acct = AccountState::new(1000.0);
        assert_eq!(acct.equity_usdt(), 1000.0);
        assert_eq!(acct.available_balance_usdt(), 1000.0);

        // Lock 200 USDT margin
        acct.lock_margin(200.0).expect("Margin lock should succeed");
        assert_eq!(acct.initial_margin_usdt, 200.0);
        assert_eq!(acct.available_balance_usdt(), 800.0);
        assert_eq!(acct.margin_utilization_pct(), 20.0);

        // Release 200 USDT margin
        acct.release_margin(200.0);
        assert_eq!(acct.initial_margin_usdt, 0.0);
        assert_eq!(acct.available_balance_usdt(), 1000.0);
    }

    #[test]
    fn test_margin_exhaustion_rejection() {
        let mut acct = AccountState::new(100.0);
        let res = acct.lock_margin(150.0);
        assert!(res.is_err());
    }
}
