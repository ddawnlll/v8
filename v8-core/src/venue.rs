//! Binance USDⓈ-M Venue Contract, Order Filters, Leverage Brackets,
//! Isolated Margin Liquidation Model, and Multidimensional Execution Authority Profile.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §§3–5, Decisions D-111, D-114.

use serde::{Deserialize, Serialize};

/// Price filter configuration (PRICE_FILTER).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PriceFilter {
    pub min_price: f64,
    pub max_price: f64,
    pub tick_size: f64,
}

impl PriceFilter {
    pub fn new(min_price: f64, max_price: f64, tick_size: f64) -> Self {
        Self {
            min_price,
            max_price,
            tick_size,
        }
    }

    /// Discretizes intended price to venue tick size: floor(P / tickSize) * tickSize.
    pub fn discretize(&self, price: f64) -> f64 {
        if self.tick_size <= 0.0 {
            return price;
        }
        let ticks = (price / self.tick_size).floor();
        let rounded = ticks * self.tick_size;
        let precision = self.tick_precision();
        round_to_precision(rounded, precision)
    }

    fn tick_precision(&self) -> usize {
        if self.tick_size >= 1.0 {
            0
        } else {
            let s = format!("{:.8}", self.tick_size);
            let s = s.trim_end_matches('0');
            s.split('.').nth(1).map(|d| d.len()).unwrap_or(0)
        }
    }
}

/// Lot size filter configuration (LOT_SIZE).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LotSizeFilter {
    pub min_qty: f64,
    pub max_qty: f64,
    pub step_size: f64,
}

impl LotSizeFilter {
    pub fn new(min_qty: f64, max_qty: f64, step_size: f64) -> Self {
        Self {
            min_qty,
            max_qty,
            step_size,
        }
    }

    /// Discretizes intended quantity to venue step size: floor(Q / stepSize) * stepSize.
    pub fn discretize(&self, qty: f64) -> f64 {
        if self.step_size <= 0.0 {
            return qty;
        }
        let steps = (qty / self.step_size).floor();
        let rounded = steps * self.step_size;
        let precision = self.step_precision();
        round_to_precision(rounded, precision)
    }

    fn step_precision(&self) -> usize {
        if self.step_size >= 1.0 {
            0
        } else {
            let s = format!("{:.8}", self.step_size);
            let s = s.trim_end_matches('0');
            s.split('.').nth(1).map(|d| d.len()).unwrap_or(0)
        }
    }
}

/// Helper function to round float to specific decimal places.
fn round_to_precision(val: f64, precision: usize) -> f64 {
    let factor = 10_f64.powi(precision as i32);
    (val * factor).round() / factor
}

/// Tiered leverage and maintenance margin bracket (Binance USDⓈ-M Bracket Rules).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LeverageBracket {
    pub tier: usize,
    pub notional_cap: f64,
    pub max_leverage: u32,
    pub maint_margin_rate: f64,
    pub cum_offset: f64,
}

/// Fee schedule for maker/taker orders.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FeeSchedule {
    pub maker_rate: f64,
    pub taker_rate: f64,
}

impl Default for FeeSchedule {
    fn default() -> Self {
        // VIP0 default fee rates: 0.02% maker, 0.05% taker
        Self {
            maker_rate: 0.0002,
            taker_rate: 0.0005,
        }
    }
}

/// Versioned Binance USDⓈ-M Venue Contract.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VenueContract {
    pub venue_id: String,
    pub symbol: String,
    pub price_filter: PriceFilter,
    pub lot_size_filter: LotSizeFilter,
    pub min_notional: f64,
    pub market_lot_size: f64,
    pub leverage_brackets: Vec<LeverageBracket>,
    pub fee_schedule: FeeSchedule,
}

impl VenueContract {
    /// Factory for authoritative Binance BTCUSDT perpetual contract rules.
    pub fn binance_btcusdt_perpetual() -> Self {
        Self::for_symbol("BTCUSDT")
    }

    /// Factory for symbol-specific perpetual contract rules.
    pub fn for_symbol(symbol: &str) -> Self {
        match symbol {
            "SOLUSDT" => Self {
                venue_id: "binance_usdm_v1".to_string(),
                symbol: "SOLUSDT".to_string(),
                price_filter: PriceFilter::new(0.01, 100_000.0, 0.01),
                lot_size_filter: LotSizeFilter::new(0.01, 100_000.0, 0.01),
                min_notional: 5.0,
                market_lot_size: 1000.0,
                leverage_brackets: vec![
                    LeverageBracket { tier: 1, notional_cap: 50_000.0, max_leverage: 75, maint_margin_rate: 0.0065, cum_offset: 0.0 },
                    LeverageBracket { tier: 2, notional_cap: 250_000.0, max_leverage: 50, maint_margin_rate: 0.0100, cum_offset: 875.0 },
                ],
                fee_schedule: FeeSchedule::default(),
            },
            "ETHUSDT" => Self {
                venue_id: "binance_usdm_v1".to_string(),
                symbol: "ETHUSDT".to_string(),
                price_filter: PriceFilter::new(0.01, 100_000.0, 0.01),
                lot_size_filter: LotSizeFilter::new(0.001, 10_000.0, 0.001),
                min_notional: 5.0,
                market_lot_size: 100.0,
                leverage_brackets: vec![
                    LeverageBracket { tier: 1, notional_cap: 50_000.0, max_leverage: 100, maint_margin_rate: 0.0050, cum_offset: 0.0 },
                    LeverageBracket { tier: 2, notional_cap: 250_000.0, max_leverage: 75, maint_margin_rate: 0.0065, cum_offset: 375.0 },
                ],
                fee_schedule: FeeSchedule::default(),
            },
            _ => Self {
                venue_id: "binance_usdm_v1".to_string(),
                symbol: "BTCUSDT".to_string(),
                price_filter: PriceFilter::new(0.1, 1_000_000.0, 0.1),
                lot_size_filter: LotSizeFilter::new(0.001, 1_000.0, 0.001),
                min_notional: 5.0,
                market_lot_size: 100.0,
                leverage_brackets: vec![
                    LeverageBracket {
                        tier: 1,
                        notional_cap: 50_000.0,
                        max_leverage: 125,
                        maint_margin_rate: 0.0040,
                        cum_offset: 0.0,
                    },
                    LeverageBracket {
                        tier: 2,
                        notional_cap: 250_000.0,
                        max_leverage: 100,
                        maint_margin_rate: 0.0050,
                        cum_offset: 50.0,
                    },
                    LeverageBracket {
                        tier: 3,
                        notional_cap: 1_000_000.0,
                        max_leverage: 50,
                        maint_margin_rate: 0.0100,
                        cum_offset: 1_300.0,
                    },
                    LeverageBracket {
                        tier: 4,
                        notional_cap: 5_000_000.0,
                        max_leverage: 20,
                        maint_margin_rate: 0.0250,
                        cum_offset: 16_300.0,
                    },
                    LeverageBracket {
                        tier: 5,
                        notional_cap: 10_000_000.0,
                        max_leverage: 10,
                        maint_margin_rate: 0.0500,
                        cum_offset: 141_300.0,
                    },
                ],
                fee_schedule: FeeSchedule::default(),
            },
        }
    }

    /// Discretizes price according to contract price filter.
    pub fn discretize_price(&self, price: f64) -> f64 {
        self.price_filter.discretize(price)
    }

    /// Discretizes quantity according to contract lot size filter.
    pub fn discretize_quantity(&self, qty: f64) -> f64 {
        self.lot_size_filter.discretize(qty)
    }

    /// Checks if nominal order value meets min notional requirement (e.g. 5.0 USDT).
    pub fn check_min_notional(&self, price: f64, qty: f64) -> bool {
        (price * qty) >= self.min_notional
    }

    /// Finds the corresponding leverage bracket for a given notional position size.
    pub fn bracket_for_notional(&self, notional: f64) -> &LeverageBracket {
        for b in &self.leverage_brackets {
            if notional <= b.notional_cap {
                return b;
            }
        }
        self.leverage_brackets.last().unwrap()
    }

    /// Calculates required initial margin in USDT for a given notional and leverage.
    pub fn initial_margin(&self, notional: f64, leverage: u32) -> f64 {
        if leverage == 0 {
            notional
        } else {
            notional / (leverage as f64)
        }
    }

    /// Calculates required maintenance margin in USDT: Notional * MMR_k - cum_k.
    pub fn maintenance_margin(&self, notional: f64) -> f64 {
        let bracket = self.bracket_for_notional(notional);
        (notional * bracket.maint_margin_rate - bracket.cum_offset).max(0.0)
    }

    /// Computes cryptographic contract identity hash for identifiability verification (D-113).
    pub fn contract_hash(&self) -> String {
        use sha1::{Digest, Sha1};
        let mut hasher = Sha1::new();
        hasher.update(self.venue_id.as_bytes());
        hasher.update(self.symbol.as_bytes());
        hasher.update(self.min_notional.to_le_bytes());
        hasher.update(self.price_filter.tick_size.to_le_bytes());
        hasher.update(self.lot_size_filter.step_size.to_le_bytes());
        hasher.update(self.fee_schedule.maker_rate.to_le_bytes());
        hasher.update(self.fee_schedule.taker_rate.to_le_bytes());
        format!("{:x}", hasher.finalize())
    }
}

/// Isolated Margin Liquidation Model.
pub struct LiquidationModel;

impl LiquidationModel {
    /// Exact Isolated Margin Liquidation Price formulation (Invariant 4.1).
    ///
    /// Long:  P_liq = (P_entry * Q - Margin + cum_k) / (Q * (1 - MMR_k))
    /// Short: P_liq = (P_entry * Q + Margin - cum_k) / (Q * (1 + MMR_k))
    pub fn calculate_isolated_liquidation_price(
        direction: &str,
        entry_price: f64,
        quantity: f64,
        isolated_margin: f64,
        bracket: &LeverageBracket,
    ) -> f64 {
        if quantity <= 0.0 {
            return 0.0;
        }
        let mmr = bracket.maint_margin_rate;
        let cum = bracket.cum_offset;

        if direction == "LONG" {
            let numerator = entry_price * quantity - isolated_margin + cum;
            let denominator = quantity * (1.0 - mmr);
            if denominator <= 0.0 {
                0.0
            } else {
                (numerator / denominator).max(0.0)
            }
        } else {
            let numerator = entry_price * quantity + isolated_margin - cum;
            let denominator = quantity * (1.0 + mmr);
            if denominator <= 0.0 {
                0.0
            } else {
                (numerator / denominator).max(0.0)
            }
        }
    }

    /// Evaluates if bar prices breach liquidation threshold.
    pub fn is_liquidated(direction: &str, liq_price: f64, bar_high: f64, bar_low: f64) -> bool {
        if liq_price <= 0.0 {
            return false;
        }
        if direction == "LONG" {
            bar_low <= liq_price
        } else {
            bar_high >= liq_price
        }
    }
}

/// Multidimensional Execution Authority Profile (VENUE_AND_CAPITAL_SIMULATION_SPEC §5.1, D-114).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MarketPathFidelity {
    Bar,
    SubBar1m,
    AggTrades,
    L2OrderBook,
}

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum VenueRuleFidelity {
    Generic,
    BinanceUsdM_Versioned,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FillAuthority {
    Canonical,
    AggressiveObserved,
    PassiveModelled,
    Live,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ImpactAuthority {
    None,
    ExogenousPowerLaw,
    CalibratedReactive,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AccountAuthority {
    Unconstrained,
    CapitalConstrained,
    LiveShadow,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum IdentifiabilityStatus {
    Identified,
    PartialInterval,
    ModelDerived,
    Unknown,
}

/// 6-Axis Execution Authority Profile.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ExecutionAuthorityProfile {
    pub market_path: MarketPathFidelity,
    pub venue_rules: VenueRuleFidelity,
    pub fill_authority: FillAuthority,
    pub impact_authority: ImpactAuthority,
    pub account_authority: AccountAuthority,
    pub identifiability: IdentifiabilityStatus,
}

impl ExecutionAuthorityProfile {
    /// Authoritative default profile for Binance USDⓈ-M Capital Simulation.
    pub fn binance_usdm_capital_sim() -> Self {
        Self {
            market_path: MarketPathFidelity::Bar,
            venue_rules: VenueRuleFidelity::BinanceUsdM_Versioned,
            fill_authority: FillAuthority::Canonical,
            impact_authority: ImpactAuthority::None,
            account_authority: AccountAuthority::CapitalConstrained,
            identifiability: IdentifiabilityStatus::Identified,
        }
    }
}

/// Dynamic Venue State at decision epoch t.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VenueState {
    pub contract: VenueContract,
    pub mark_price: f64,
    pub funding_rate: f64,
    pub next_funding_time: i64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lot_size_discretization() {
        let contract = VenueContract::binance_btcusdt_perpetual();
        let raw_qty = 0.12389;
        let eff_qty = contract.discretize_quantity(raw_qty);
        assert!((eff_qty - 0.123).abs() < 1e-9);

        let small_qty = 0.0004;
        let zero_qty = contract.discretize_quantity(small_qty);
        assert_eq!(zero_qty, 0.0);
    }

    #[test]
    fn test_price_tick_discretization() {
        let contract = VenueContract::binance_btcusdt_perpetual();
        let raw_price = 65432.189;
        let eff_price = contract.discretize_price(raw_price);
        assert!((eff_price - 65432.1).abs() < 1e-9);
    }

    #[test]
    fn test_min_notional_filter() {
        let contract = VenueContract::binance_btcusdt_perpetual();
        // 0.001 BTC at 4000 USDT = 4.0 USDT < 5.0 USDT -> false
        assert!(!contract.check_min_notional(4000.0, 0.001));
        // 0.001 BTC at 6000 USDT = 6.0 USDT >= 5.0 USDT -> true
        assert!(contract.check_min_notional(6000.0, 0.001));
    }

    #[test]
    fn test_liquidation_price_isolated() {
        let contract = VenueContract::binance_btcusdt_perpetual();
        let bracket = contract.bracket_for_notional(10_000.0); // Tier 1

        // LONG: Entry 10000, Qty 1.0, Margin 1000 (10x leverage)
        // P_liq = (10000 * 1 - 1000 + 0) / (1 * (1 - 0.004)) = 9000 / 0.996 = 9036.144578...
        let liq_long = LiquidationModel::calculate_isolated_liquidation_price(
            "LONG", 10000.0, 1.0, 1000.0, bracket,
        );
        assert!((liq_long - 9036.144578313253).abs() < 1e-5);

        // SHORT: Entry 10000, Qty 1.0, Margin 1000 (10x leverage)
        // P_liq = (10000 * 1 + 1000 - 0) / (1 * (1 + 0.004)) = 11000 / 1.004 = 10956.175298...
        let liq_short = LiquidationModel::calculate_isolated_liquidation_price(
            "SHORT", 10000.0, 1.0, 1000.0, bracket,
        );
        assert!((liq_short - 10956.17529880478).abs() < 1e-5);
    }
}
