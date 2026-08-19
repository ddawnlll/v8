//! V8 Evaluation Evidence System — Manifest & Validity Gates (v8.eval.v1 §5, §22).
//!
//! Entry gateway, cryptographic receipt, accounting conservation invariants,
//! and fail-closed hard validity gates in pure Rust.

use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::path::Path;

pub const SCHEMA_VERSION: &str = "v8.eval.v1";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DatasetMetadata {
    pub instrument: String,
    pub timeframe: String,
    pub raw_bars: usize,
    pub warmup_bars: usize,
    pub eligible_bars: usize,
    pub start_utc: String,
    pub end_utc: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FunnelConservation {
    pub evaluations: usize,
    pub setups_triggered: usize,
    pub deduplicated: usize,
    pub vetoed_risk_capacity: usize,
    pub admitted_trades: usize,
    pub invariant_holds: bool,
    pub accounting_equation: String,
}

impl FunnelConservation {
    pub fn new(
        evaluations: usize,
        setups_triggered: usize,
        deduplicated: usize,
        vetoed_risk_capacity: usize,
        admitted_trades: usize,
    ) -> Self {
        let expected = deduplicated + vetoed_risk_capacity + admitted_trades;
        let invariant_holds = setups_triggered == expected;
        let accounting_equation = format!(
            "{setups_triggered} == {deduplicated} (dedup) + {vetoed_risk_capacity} (veto) + {admitted_trades} (admitted)"
        );
        Self {
            evaluations,
            setups_triggered,
            deduplicated,
            vetoed_risk_capacity,
            admitted_trades,
            invariant_holds,
            accounting_equation,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ValidityGates {
    pub temporal_leakage: String,
    pub accounting_conservation: String,
    pub determinism_replay: String,
    pub simd_scalar_parity: String,
    pub thread_parity: String,
    pub overall_validity: String,
}

impl ValidityGates {
    pub fn evaluate(
        temporal_leakage: bool,
        accounting_mismatch: bool,
        nondeterministic_replay: bool,
        simd_divergence: bool,
        thread_divergence: bool,
    ) -> Self {
        let is_invalid = temporal_leakage
            || accounting_mismatch
            || nondeterministic_replay
            || simd_divergence
            || thread_divergence;

        Self {
            temporal_leakage: if temporal_leakage { "FAIL" } else { "PASS" }.to_string(),
            accounting_conservation: if accounting_mismatch { "FAIL" } else { "PASS" }.to_string(),
            determinism_replay: if nondeterministic_replay { "FAIL" } else { "PASS" }.to_string(),
            simd_scalar_parity: if simd_divergence { "FAIL" } else { "PASS" }.to_string(),
            thread_parity: if thread_divergence { "FAIL" } else { "PASS" }.to_string(),
            overall_validity: if is_invalid { "INVALID_RUN" } else { "VALID" }.to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SummaryMetrics {
    pub gross_expectancy_R: f64,
    pub net_expectancy_R: f64,
    pub total_trades: usize,
    pub sharpe_ratio: f64,
    pub max_drawdown_R: f64,
    pub win_rate_pct: f64,
    pub profit_factor: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ArtifactsSummary {
    pub root_dir: String,
    pub total_size_bytes: u64,
    pub file_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EvaluationManifest {
    pub schema: String,
    pub run_id: String,
    pub timestamp_utc: String,
    pub git_commit: Option<String>,
    pub binary_hash: Option<String>,
    pub tape_hash: String,
    pub config_hash: String,
    pub dataset: DatasetMetadata,
    pub funnel_conservation: FunnelConservation,
    pub validity_gates: ValidityGates,
    pub economic_verdict: String,
    pub summary_metrics: SummaryMetrics,
    pub critical_findings: Vec<String>,
    pub artifacts: ArtifactsSummary,
}

impl EvaluationManifest {
    pub fn save(&self, path: &Path) -> io::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(path, json)
    }

    pub fn load(path: &Path) -> io::Result<Self> {
        let content = fs::read_to_string(path)?;
        serde_json::from_str(&content)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }
}
