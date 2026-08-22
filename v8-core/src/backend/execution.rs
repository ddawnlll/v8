//! Execution Backend & Venue Physics Instrument (D-132, Rule 34, PH2-003A.4).
//!
//! Enforces:
//! 1. Passive physics device trait (ExecutionBackend).
//! 2. Demotion from autonomous decision maker to execution simulator.
//! 3. Cryptographic ExecutionReceipt with double-entry cashflow conservation.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use crate::authority::{Authority, EvidenceAuthority, DecisionAuthority, RealizationStatus};
use crate::hash::Canon;

/// Contextual market microstructure parameters passed into the execution backend.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MarketContext {
    pub symbol: String,
    pub timestamp_utc: i64,
    pub best_bid: f64,
    pub best_ask: f64,
    pub funding_rate: f64,
    pub fee_maker_bps: f64,
    pub fee_taker_bps: f64,
}

/// An execution intent sent from the portfolio layer to the execution backend.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BackendExecutionIntent {
    pub campaign_id: String,
    pub symbol: String,
    pub direction: String,
    pub notional_size: f64,
    pub is_taker: bool,
    pub authority: Authority,
}

/// Cryptographic receipt generated upon physical or simulated execution completion.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExecutionReceipt {
    pub receipt_id: String,
    pub backend_name: String,
    pub campaign_id: String,
    pub symbol: String,
    pub fill_price: f64,
    pub executed_notional: f64,
    pub fee_paid: f64,
    pub funding_incurred: f64,
    pub slippage_incurred: f64,
    pub settled_cashflow_delta: f64,
    pub timestamp_utc: i64,
    pub authority: Authority,
}

impl ExecutionReceipt {
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("ExecutionReceipt");
        c.push_str(&self.backend_name);
        c.push_str(&self.campaign_id);
        c.push_str(&self.symbol);
        c.push_f64(self.fill_price);
        c.push_f64(self.executed_notional);
        c.push_f64(self.fee_paid);
        c.push_f64(self.funding_incurred);
        c.push_f64(self.slippage_incurred);
        c.push_f64(self.settled_cashflow_delta);
        c.push_i64(self.timestamp_utc);
        c.push_str(&format!("{:?}", self.authority));
        c.finish_blake3_hex()
    }
}

/// Execution Backend Error.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExecutionBackendError {
    InsufficientAuthority(String),
    LiquidityExhausted(String),
    MarginExceeded(String),
}

impl std::fmt::Display for ExecutionBackendError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InsufficientAuthority(s) => write!(f, "EXECUTION_BACKEND_ERROR: Insufficient authority: {s}"),
            Self::LiquidityExhausted(s) => write!(f, "EXECUTION_BACKEND_ERROR: Liquidity exhausted: {s}"),
            Self::MarginExceeded(s) => write!(f, "EXECUTION_BACKEND_ERROR: Margin exceeded: {s}"),
        }
    }
}

impl std::error::Error for ExecutionBackendError {}

/// The Canonical Execution Backend Trait (Rule 34).
/// Passive laboratory instrument modeling venue execution physics (fees, funding, margin, slippage).
pub trait ExecutionBackend: Send + Sync {
    fn backend_name(&self) -> &'static str;

    fn execute(
        &self,
        intent: &BackendExecutionIntent,
        market: &MarketContext,
    ) -> Result<ExecutionReceipt, ExecutionBackendError>;
}

/// Reference Binance USDⓈ-M Execution Physics Backend.
pub struct BinanceUsdmExecutionBackend {
    pub default_slippage_bps: f64,
}

impl BinanceUsdmExecutionBackend {
    pub fn new(default_slippage_bps: f64) -> Self {
        Self { default_slippage_bps }
    }
}

impl Default for BinanceUsdmExecutionBackend {
    fn default() -> Self {
        Self { default_slippage_bps: 2.5 }
    }
}

impl ExecutionBackend for BinanceUsdmExecutionBackend {
    fn backend_name(&self) -> &'static str {
        "binance-usdm-physics-backend"
    }

    fn execute(
        &self,
        intent: &BackendExecutionIntent,
        market: &MarketContext,
    ) -> Result<ExecutionReceipt, ExecutionBackendError> {
        // Enforce Portfolio Authorization Gate
        if intent.authority.decision < DecisionAuthority::PortfolioAuthorized {
            return Err(ExecutionBackendError::InsufficientAuthority(
                "Execution backend requires PortfolioAuthorized decision authority".to_string(),
            ));
        }

        let is_long = intent.direction == "LONG" || intent.direction == "Long";
        let mid_price = (market.best_bid + market.best_ask) / 2.0;
        let slippage_rate = self.default_slippage_bps / 10_000.0;

        let fill_price = if is_long {
            market.best_ask * (1.0 + slippage_rate)
        } else {
            market.best_bid * (1.0 - slippage_rate)
        };

        let fee_rate = if intent.is_taker {
            market.fee_taker_bps / 10_000.0
        } else {
            market.fee_maker_bps / 10_000.0
        };

        let fee_paid = intent.notional_size * fee_rate;
        let funding_incurred = intent.notional_size * (market.funding_rate / 10_000.0);
        let slippage_incurred = intent.notional_size * (fill_price - mid_price).abs() / mid_price;

        let mut receipt = ExecutionReceipt {
            receipt_id: String::new(),
            backend_name: self.backend_name().to_string(),
            campaign_id: intent.campaign_id.clone(),
            symbol: intent.symbol.clone(),
            fill_price,
            executed_notional: intent.notional_size,
            fee_paid,
            funding_incurred,
            slippage_incurred,
            settled_cashflow_delta: -fee_paid - funding_incurred,
            timestamp_utc: market.timestamp_utc,
            authority: Authority::new(
                EvidenceAuthority::Observed,
                DecisionAuthority::ExecutionAuthorized,
                RealizationStatus::Simulated,
            ),
        };
        receipt.receipt_id = receipt.compute_id();

        Ok(receipt)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_execution_backend_fails_without_portfolio_authority() {
        let backend = BinanceUsdmExecutionBackend::default();
        let intent = BackendExecutionIntent {
            campaign_id: "camp_001".to_string(),
            symbol: "BTCUSDT".to_string(),
            direction: "LONG".to_string(),
            notional_size: 10_000.0,
            is_taker: true,
            authority: Authority::counterfactual_diagnostic(), // Missing portfolio authority!
        };
        let market = MarketContext {
            symbol: "BTCUSDT".to_string(),
            timestamp_utc: 1_000_000,
            best_bid: 60_000.0,
            best_ask: 60_001.0,
            funding_rate: 1.0,
            fee_maker_bps: 2.0,
            fee_taker_bps: 5.0,
        };

        let res = backend.execute(&intent, &market);
        assert!(matches!(res, Err(ExecutionBackendError::InsufficientAuthority(_))));
    }

    #[test]
    fn test_execution_backend_produces_valid_receipt_under_authority() {
        let backend = BinanceUsdmExecutionBackend::default();
        let intent = BackendExecutionIntent {
            campaign_id: "camp_001".to_string(),
            symbol: "BTCUSDT".to_string(),
            direction: "LONG".to_string(),
            notional_size: 10_000.0,
            is_taker: true,
            authority: Authority::portfolio_authorized(
                EvidenceAuthority::Observed,
                RealizationStatus::Simulated,
            ),
        };
        let market = MarketContext {
            symbol: "BTCUSDT".to_string(),
            timestamp_utc: 1_000_000,
            best_bid: 60_000.0,
            best_ask: 60_001.0,
            funding_rate: 1.0,
            fee_maker_bps: 2.0,
            fee_taker_bps: 5.0,
        };

        let receipt = backend.execute(&intent, &market).unwrap();
        assert_eq!(receipt.backend_name, "binance-usdm-physics-backend");
        assert_eq!(receipt.receipt_id, receipt.compute_id());
        assert!(receipt.fee_paid > 0.0);
        assert!(receipt.executed_notional == 10_000.0);
    }
}
