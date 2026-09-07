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

    /// Build a parity request from a case's *declared* artifacts (#329 R1, R2).
    ///
    /// The parity adapter is the one evaluator that can run today, because its
    /// inputs are two ledgers and a mapping rather than a registered scoring
    /// implementation. That makes the declaration gate load-bearing: without it,
    /// an operator could point the adapter at any two files and describe the
    /// result as parity evidence for the case, which is the #329 defect moved from
    /// the adapter to its caller.
    ///
    /// Both ledger paths must appear in `case.evidence.artifact_paths`; a path
    /// that is not declared is `DATA_BLOCKED`, and no comparison is attempted.
    pub fn parity_request(
        &self,
        case: &BenchmarkCase,
        mapping: crate::benchmark::parity::SemanticMapping,
        engine: crate::benchmark::parity::EngineVersion,
        native_ledger: &Path,
        reference_ledger: &Path,
        method_version: &str,
        computed_at_timestamp_ns: u64,
    ) -> Result<crate::benchmark::parity::ParityRequest, String> {
        let evidence = case
            .evidence
            .as_ref()
            .ok_or_else(|| "DATA_BLOCKED_NO_VERIFIED_BENCHMARK_EVIDENCE".to_string())?;

        let mut declared = Vec::new();
        for raw_path in &evidence.artifact_paths {
            let path = Path::new(raw_path);
            if !path.is_file() {
                return Err(format!("DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT:{raw_path}"));
            }
            declared.push(path.to_path_buf());
        }

        for (role, wanted) in [
            ("native", native_ledger),
            ("reference", reference_ledger),
        ] {
            let canonical = canonical_or_self(wanted);
            if !declared
                .iter()
                .any(|p| canonical_or_self(p) == canonical)
            {
                return Err(format!(
                    "DATA_BLOCKED_UNDECLARED_PARITY_ARTIFACT[{role}]: {:?} is not in                      the evidence manifest of case {}",
                    wanted, case.case_id
                ));
            }
        }

        let native_artifact = crate::benchmark::receipt::ArtifactBinding::from_file("native", native_ledger)?;
        let reference_artifact =
            crate::benchmark::receipt::ArtifactBinding::from_file("reference", reference_ledger)?;

        Ok(crate::benchmark::parity::ParityRequest {
            subject: crate::benchmark::parity::ParitySubject::from_case(case),
            mapping,
            engine,
            native_artifact,
            reference_artifact,
            method_version: method_version.to_string(),
            computed_at_timestamp_ns,
        })
    }
}

/// Resolve a path for comparison, falling back to the input when it does not
/// exist yet (the existence check happens against the declared list anyway).
fn canonical_or_self(path: &Path) -> std::path::PathBuf {
    fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf())
}
