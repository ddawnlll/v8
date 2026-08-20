//! Shared v8.eval.v1 support records used by Target Oracle coverage and Kaizen.
//!
//! This module deliberately does not define an autonomous evaluation, verdict,
//! or economic-authority plane.

pub mod agents;
pub mod authority_surface;
pub mod lineage;
pub mod schema_cache;
pub mod temporal;

#[derive(Debug, Clone)]
pub struct TradeRow {
    pub trade_id: String,
    pub candidate_id: String,
    pub symbol: String,
    pub expert_id: String,
    pub direction: String,
    pub entry_ts_ns: i64,
    pub exit_ts_ns: i64,
    pub entry_price: f64,
    pub exit_price: f64,
    pub gross_r: f64,
    pub net_r: f64,
    pub fee_paid: f64,
    pub slippage_paid: f64,
    pub funding_paid: f64,
    pub exit_reason: String,
    pub duration_bars: usize,
    pub mfe_r: f64,
    pub mae_r: f64,
}
