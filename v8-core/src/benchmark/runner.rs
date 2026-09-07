//! Data-backed benchmark execution boundary (D-153, Rule 12).
//!
//! A benchmark receipt is an economic-facing artifact. The runner therefore
//! refuses to synthesize observations, dates, scores, gates, or statistical
//! receipts. A registered evaluator may be added behind the physical evidence
//! contract once its inputs and authority receipt are available.

use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

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
    ///
    /// This is the OFFICIAL path: it stays blocked while the D-156 registered
    /// evaluator PIN is open. Development diagnostics use
    /// `run_benchmark_diagnostic`, which never mints a receipt.
    pub fn run_benchmark(&self, case: &BenchmarkCase) -> Result<BenchmarkReceipt, String> {
        if case.case_id.trim().is_empty() || case.case_hash.trim().is_empty() {
            return Err("BLOCKED_INVALID_BENCHMARK_CASE".to_string());
        }

        verify_evidence_artifacts(case)?;

        Err("BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED".to_string())
    }

    /// Development-only diagnostic success path (governance reset 2026-09-07).
    ///
    /// Validates the same physical evidence as the official path and reports
    /// the verified manifest plus case-hash integrity, WITHOUT minting a
    /// receipt, score, gate verdict, or economic claim. The output carries an
    /// explicit non-authoritative label; the registered-evaluator requirement
    /// continues to block only the official receipt/certificate path.
    pub fn run_benchmark_diagnostic(
        &self,
        case: &BenchmarkCase,
    ) -> Result<BenchmarkDiagnosticReport, String> {
        if case.case_id.trim().is_empty() || case.case_hash.trim().is_empty() {
            return Err("BLOCKED_INVALID_BENCHMARK_CASE".to_string());
        }

        let verified_artifacts = verify_evidence_artifacts(case)?;

        Ok(BenchmarkDiagnosticReport {
            case_id: case.case_id.clone(),
            case_hash: case.case_hash.clone(),
            case_hash_verified: case.verify_hash(),
            authority: DIAGNOSTIC_AUTHORITY.to_string(),
            receipt_minted: false,
            verified_artifacts,
            target_domains: case
                .target_domains
                .iter()
                .map(|d| d.as_str().to_string())
                .collect(),
            allowed_populations: case
                .allowed_populations
                .iter()
                .map(|p| format!("{p:?}"))
                .collect(),
            official_receipt_blocker: "BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED".to_string(),
        })
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
/// Authority label for development diagnostics: never a receipt, never a claim.
pub const DIAGNOSTIC_AUTHORITY: &str =
    "NON_AUTHORITATIVE / DEVELOPMENT_ONLY / NOT_FOR_ECONOMIC_CLAIM";

/// One physically verified evidence artifact (existence + byte size read from
/// disk; parquet payloads additionally pass `verify_parquet`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifiedArtifact {
    pub path: String,
    pub bytes: u64,
}

/// Development diagnostic output. Every number is read off the declared inputs
/// (disk metadata, case fields); nothing is scored, gated, or claimed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkDiagnosticReport {
    pub case_id: String,
    pub case_hash: String,
    pub case_hash_verified: bool,
    pub authority: String,
    pub receipt_minted: bool,
    pub verified_artifacts: Vec<VerifiedArtifact>,
    pub target_domains: Vec<String>,
    pub allowed_populations: Vec<String>,
    pub official_receipt_blocker: String,
}

/// Shared physical-evidence gate: every declared artifact must exist on disk
/// (parquet payloads must additionally verify). Returns the verified list
/// with byte sizes; any absence fails closed with a `DATA_BLOCKED_*` code.
fn verify_evidence_artifacts(case: &BenchmarkCase) -> Result<Vec<VerifiedArtifact>, String> {
    let evidence = case
        .evidence
        .as_ref()
        .ok_or_else(|| "DATA_BLOCKED_NO_VERIFIED_BENCHMARK_EVIDENCE".to_string())?;
    if evidence.artifact_paths.is_empty() {
        return Err("DATA_BLOCKED_EMPTY_BENCHMARK_EVIDENCE_MANIFEST".to_string());
    }

    let mut verified = Vec::new();
    for raw_path in &evidence.artifact_paths {
        let path = Path::new(raw_path);
        if !path.is_file() {
            return Err(format!(
                "DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT:{raw_path}"
            ));
        }
        if path.extension().and_then(|ext| ext.to_str()) == Some("parquet") {
            crate::parquet_artifact::verify_parquet(path).map_err(|error| {
                format!("DATA_BLOCKED_INVALID_PARQUET_ARTIFACT:{raw_path}:{error}")
            })?;
        }
        let bytes = fs::metadata(path)
            .map_err(|error| {
                format!("DATA_BLOCKED_UNREADABLE_BENCHMARK_ARTIFACT:{raw_path}:{error}")
            })?
            .len();
        verified.push(VerifiedArtifact {
            path: raw_path.clone(),
            bytes,
        });
    }
    Ok(verified)
}

fn canonical_or_self(path: &Path) -> std::path::PathBuf {
    fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::benchmark::case::{BenchmarkEvidenceManifest, BenchmarkVersion, PolicyTarget};
    use crate::benchmark::types::{CapabilityDomain, EvaluationPopulation};

    fn dev_case(artifact_paths: Vec<String>) -> BenchmarkCase {
        let mut case = BenchmarkCase::new(
            "dev-diagnostic-probe".to_string(),
            BenchmarkVersion::new_v8_5(),
            PolicyTarget {
                policy_id: "probe".to_string(),
                commit_hash: "local".to_string(),
                binary_digest: "local".to_string(),
                family: "probe".to_string(),
            },
            vec![CapabilityDomain::ExecutionFidelity],
            vec![EvaluationPopulation::BurnedDiagnosticReal],
            60,
        );
        case.evidence = Some(BenchmarkEvidenceManifest { artifact_paths });
        case
    }

    #[test]
    fn diagnostic_reports_verified_evidence_without_minting_receipt() {
        let path = std::env::temp_dir().join(format!("v8-bench-diag-{}.json", std::process::id()));
        let payload = b"{\"probe\":true}";
        std::fs::write(&path, payload).unwrap();
        let case = dev_case(vec![path.to_string_lossy().into_owned()]);
        let report = BenchmarkRunner::new()
            .run_benchmark_diagnostic(&case)
            .unwrap();
        std::fs::remove_file(&path).ok();
        assert!(report.case_hash_verified);
        assert!(!report.receipt_minted);
        assert_eq!(report.authority, DIAGNOSTIC_AUTHORITY);
        assert_eq!(report.verified_artifacts.len(), 1);
        assert_eq!(report.verified_artifacts[0].bytes, payload.len() as u64);
        assert_eq!(
            report.official_receipt_blocker,
            "BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED"
        );
    }

    #[test]
    fn diagnostic_fails_closed_on_missing_artifact() {
        let case = dev_case(vec!["/nonexistent/v8-bench-diag.json".to_string()]);
        let err = BenchmarkRunner::new()
            .run_benchmark_diagnostic(&case)
            .unwrap_err();
        assert!(err.starts_with("DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT:"));
    }

    #[test]
    fn official_receipt_path_stays_blocked() {
        let path = std::env::temp_dir().join(format!("v8-bench-off-{}.json", std::process::id()));
        std::fs::write(&path, b"{}").unwrap();
        let case = dev_case(vec![path.to_string_lossy().into_owned()]);
        let err = BenchmarkRunner::new().run_benchmark(&case).unwrap_err();
        std::fs::remove_file(&path).ok();
        assert_eq!(err, "BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED");
    }
}
