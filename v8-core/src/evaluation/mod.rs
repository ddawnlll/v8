//! V8 Evaluation Evidence System (v8.eval.v1).
//!
//! W2 (V8.6 Phase 1) disposition: the `EvaluationEngine` orchestrator and its
//! seven supporting surfaces (`manifest`, `statistics`, `surfaces`, `paths`,
//! `regression`, `html_report`, `deployment_case`) had zero production
//! consumers and were moved to `v8-core/attic/evaluation/` (BEHAVIOR_PRESERVING
//! move; bundle gate verified byte-identical). This module now only re-exports
//! the live evidence surfaces wired by `oracle/coverage.rs` plus the two row
//! carriers with live external consumers (`BarRow`: `audit/full_audit.rs`,
//! `main.rs`, `evaluation/allegory.rs`; `CandidateRow`: `evaluation/allegory.rs`;
//! `TradeRow`: `kaizen/{diagnosis,validation}.rs`, `evaluation/allegory.rs`).

#![allow(dead_code)]

pub mod agents;
pub mod allegory;
pub mod authority_surface;
pub mod falsification;
pub mod friction;
pub mod lineage;
pub mod multiple_testing;
pub mod production_growth;
pub mod regime_cube;
pub mod schema_cache;
pub mod scope;
pub mod temporal;

#[derive(Debug, Clone)]
pub struct BarRow {
    pub timestamp_ns: i64,
    pub symbol: String,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    pub funding_rate: f64,
}

#[derive(Debug, Clone)]
pub struct CandidateRow {
    pub candidate_id: String,
    pub birth_bar: usize,
    pub birth_ts_ns: i64,
    pub symbol: String,
    pub expert_id: String,
    pub direction: String,
    pub entry_price: f64,
    pub stop_price: f64,
    pub target_price: f64,
    pub risk_r: f64,
    pub expiry_bar: usize,
    pub episode_key: String,
}

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
