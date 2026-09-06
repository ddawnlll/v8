//! Data-backed benchmark execution boundary (D-153, Rule 12).
//!
//! A benchmark receipt is an economic-facing artifact. The runner therefore
//! refuses to synthesize observations, dates, scores, gates, or statistical
//! receipts. A registered evaluator may be added behind the physical evidence
//! contract once its inputs and authority receipt are available.

use std::fs;
use std::path::Path;

use crate::benchmark::case::BenchmarkCase;
use crate::benchmark::population::{CpcvPartitioner, WalkForwardPartitioner};
use crate::benchmark::receipt::BenchmarkReceipt;
use crate::benchmark::scoring::CapabilityScoreCalculator;

pub struct BenchmarkRunner {
    pub score_calculator: CapabilityScoreCalculator,
    pub walk_forward_partitioner: WalkForwardPartitioner,
    pub cpcv_partitioner: CpcvPartitioner,
}

impl Default for BenchmarkRunner {
    fn default() -> Self {
        Self {
            score_calculator: CapabilityScoreCalculator::monograph_v1(),
            walk_forward_partitioner: WalkForwardPartitioner::new(
                4,
                true,
                0.70,
                3_600_000_000_000,
                86_400_000_000_000,
            ),
            cpcv_partitioner: CpcvPartitioner::new(
                6,
                2,
                3_600_000_000_000,
                86_400_000_000_000,
            ),
        }
    }
}

impl BenchmarkRunner {
    pub fn new() -> Self {
        Self::default()
    }

    /// Validate the declared physical inputs and refuse to materialize a
    /// receipt until the registered evaluator has consumed them.
    pub fn run_benchmark(&self, case: &BenchmarkCase) -> Result<BenchmarkReceipt, String> {
        if case.case_id.trim().is_empty() || case.case_hash.trim().is_empty() {
            return Err("BLOCKED_INVALID_BENCHMARK_CASE".to_string());
        }

        let evidence = case
            .evidence
            .as_ref()
            .ok_or_else(|| "DATA_BLOCKED_NO_VERIFIED_BENCHMARK_EVIDENCE".to_string())?;
        if evidence.artifact_paths.is_empty() {
            return Err("DATA_BLOCKED_EMPTY_BENCHMARK_EVIDENCE_MANIFEST".to_string());
        }

        for raw_path in &evidence.artifact_paths {
            let path = Path::new(raw_path);
            if !path.is_file() {
                return Err(format!("DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT:{raw_path}"));
            }
            if path.extension().and_then(|ext| ext.to_str()) == Some("parquet") {
                crate::parquet_artifact::verify_parquet(path).map_err(|error| {
                    format!("DATA_BLOCKED_INVALID_PARQUET_ARTIFACT:{raw_path}:{error}")
                })?;
            } else {
                fs::metadata(path).map_err(|error| {
                    format!("DATA_BLOCKED_UNREADABLE_BENCHMARK_ARTIFACT:{raw_path}:{error}")
                })?;
            }
        }

        Err("BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED".to_string())
    }
}
