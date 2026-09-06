//! BenchmarkReceipt and Cryptographic Binding (D-153 Section 111).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use crate::benchmark::case::BenchmarkCase;
use crate::benchmark::observation::MetricObservation;
use crate::benchmark::types::{CapabilityDomain, GateVector, ProjectionGrade};

/// Minimal defeater summary for benchmark reporting (D-153 §44)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MinimalDefeaterSummary {
    pub family: String,
    pub plausibility_distance: f64,
    pub peak_drawdown_pct: f64,
    pub failure_predicate: String,
    pub defeater_receipt_id: Option<String>,
}

/// Per-domain evaluation result
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DomainEvaluationResult {
    pub domain: CapabilityDomain,
    pub raw_score: f64,
    pub calibrated_score: f64,
    pub lower_bound: f64,
    pub upper_bound: f64,
    pub sample_count: usize,
    pub passed_hard_invariants: bool,
    pub failure_reasons: Vec<String>,
}

/// Cryptographically sealed benchmark receipt (D-153 §45, §111)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkReceipt {
    pub receipt_id: String,
    pub case_hash: String,
    pub policy_id: String,
    pub domain_results: HashMap<CapabilityDomain, DomainEvaluationResult>,
    pub composite_capability_score: f64,
    pub gate_vector: GateVector,
    pub coverage_factor: f64,
    pub observations: Vec<MetricObservation>,
    pub nearest_defeater: Option<MinimalDefeaterSummary>,
    pub minerva_robustness: Option<crate::benchmark::minerva::MinervaRobustness>,
    pub projection_grade: ProjectionGrade,
    pub evaluation_duration_sec: f64,
    pub evaluated_at_timestamp_ns: u64,
    pub receipt_digest: String,
}

impl BenchmarkReceipt {
    pub fn generate(
        case: &BenchmarkCase,
        domain_results: HashMap<CapabilityDomain, DomainEvaluationResult>,
        composite_score: f64,
        duration_sec: f64,
        timestamp_ns: u64,
    ) -> Self {
        Self::generate_with_context(
            case,
            domain_results,
            composite_score,
            GateVector::default(),
            1.0,
            Vec::new(),
            None,
            None,
            ProjectionGrade::GradeU,
            duration_sec,
            timestamp_ns,
        )
    }

    #[allow(clippy::too_many_arguments)]
    pub fn generate_with_context(
        case: &BenchmarkCase,
        domain_results: HashMap<CapabilityDomain, DomainEvaluationResult>,
        composite_score: f64,
        gate_vector: GateVector,
        coverage_factor: f64,
        observations: Vec<MetricObservation>,
        nearest_defeater: Option<MinimalDefeaterSummary>,
        minerva_robustness: Option<crate::benchmark::minerva::MinervaRobustness>,
        projection_grade: ProjectionGrade,
        duration_sec: f64,
        timestamp_ns: u64,
    ) -> Self {
        let receipt_id = format!("bm_rcpt_{}_{}", case.case_id, timestamp_ns);
        let mut hasher = Sha256::new();
        hasher.update(receipt_id.as_bytes());
        hasher.update(case.case_hash.as_bytes());
        hasher.update(case.target.policy_id.as_bytes());
        hasher.update(&composite_score.to_le_bytes());
        hasher.update(&coverage_factor.to_le_bytes());
        hasher.update(&duration_sec.to_le_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        hasher.update(projection_grade.as_str().as_bytes());

        // Deterministic domain results hashing
        let mut sorted_domains: Vec<_> = domain_results.keys().cloned().collect();
        sorted_domains.sort_by_key(|d| d.as_str());
        for d in sorted_domains {
            if let Some(res) = domain_results.get(&d) {
                hasher.update(d.as_str().as_bytes());
                hasher.update(&res.calibrated_score.to_le_bytes());
                hasher.update(&[res.passed_hard_invariants as u8]);
            }
        }

        for obs in &observations {
            hasher.update(obs.metric_id.as_bytes());
            hasher.update(&obs.raw_value.to_le_bytes());
            hasher.update(&obs.normalized_score.to_le_bytes());
        }

        if let Some(ref def) = nearest_defeater {
            hasher.update(def.family.as_bytes());
            hasher.update(&def.plausibility_distance.to_le_bytes());
        }

        if let Some(ref minerva) = minerva_robustness {
            hasher.update(&minerva.effective_score.to_le_bytes());
            hasher.update(&[minerva.seal_granted as u8]);
        }

        let receipt_digest = format!("{:x}", hasher.finalize());

        Self {
            receipt_id,
            case_hash: case.case_hash.clone(),
            policy_id: case.target.policy_id.clone(),
            domain_results,
            composite_capability_score: composite_score,
            gate_vector,
            coverage_factor,
            observations,
            nearest_defeater,
            minerva_robustness,
            projection_grade,
            evaluation_duration_sec: duration_sec,
            evaluated_at_timestamp_ns: timestamp_ns,
            receipt_digest,
        }
    }
}
