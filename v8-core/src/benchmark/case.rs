//! BenchmarkCase and BenchmarkVersion Contracts (D-153 Section 31).
//!
//! A BenchmarkCase specifies what to evaluate and how.
//! It is distinct from an AssuranceCase (which specifies what must be proven for readiness).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::benchmark::types::{CapabilityDomain, EvaluationPopulation};

/// Benchmark Version identifier and hash
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct BenchmarkVersion {
    pub name: String,
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
    pub spec_hash: String,
}

impl BenchmarkVersion {
    pub fn new_v8_5() -> Self {
        Self {
            name: "V8.5-D153".to_string(),
            major: 8,
            minor: 5,
            patch: 0,
            spec_hash: "sha256:d153_benchmark_fabric_v8_5".to_string(),
        }
    }
}

/// Target policy representation under evaluation
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PolicyTarget {
    pub policy_id: String,
    pub commit_hash: String,
    pub binary_digest: String,
    pub family: String,
}

/// A Benchmark Case specification
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkCase {
    pub case_id: String,
    pub version: BenchmarkVersion,
    pub target: PolicyTarget,
    pub target_domains: Vec<CapabilityDomain>,
    pub allowed_populations: Vec<EvaluationPopulation>,
    pub max_compute_budget_sec: u64,
    pub case_hash: String,
}

impl BenchmarkCase {
    pub fn new(
        case_id: String,
        version: BenchmarkVersion,
        target: PolicyTarget,
        target_domains: Vec<CapabilityDomain>,
        allowed_populations: Vec<EvaluationPopulation>,
        max_compute_budget_sec: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(case_id.as_bytes());
        hasher.update(version.spec_hash.as_bytes());
        hasher.update(target.policy_id.as_bytes());
        hasher.update(target.commit_hash.as_bytes());
        hasher.update(target.binary_digest.as_bytes());
        for d in &target_domains {
            hasher.update(d.as_str().as_bytes());
        }
        for p in &allowed_populations {
            hasher.update(format!("{:?}", p).as_bytes());
        }
        hasher.update(&max_compute_budget_sec.to_le_bytes());
        let case_hash = format!("{:x}", hasher.finalize());

        Self {
            case_id,
            version,
            target,
            target_domains,
            allowed_populations,
            max_compute_budget_sec,
            case_hash,
        }
    }
}
