//! Canonical Benchmark Ontology and Types (D-153).
//!
//! Enforces ontological separation:
//! - BenchmarkCase != AssuranceCase
//! - BenchmarkProfile != PolicyEvidenceProfile
//! - CapabilityScore != Readiness
//! - Hard Gates (G0-G9) cannot be averaged away

use serde::{Deserialize, Serialize};

/// Ten explicit benchmark capability domains (Rule 57.5)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CapabilityDomain {
    ExecutionFidelity,
    RegimeRobustness,
    CrossAssetGeneralization,
    MicrostructureInvariance,
    DefeaterResistance,
    StatisticalCredibility,
    EvaluationSafety,
    CapacityScalability,
    RepresentationStability,
    OperationalSimplicity,
}

impl CapabilityDomain {
    pub const ALL: [CapabilityDomain; 10] = [
        CapabilityDomain::ExecutionFidelity,
        CapabilityDomain::RegimeRobustness,
        CapabilityDomain::CrossAssetGeneralization,
        CapabilityDomain::MicrostructureInvariance,
        CapabilityDomain::DefeaterResistance,
        CapabilityDomain::StatisticalCredibility,
        CapabilityDomain::EvaluationSafety,
        CapabilityDomain::CapacityScalability,
        CapabilityDomain::RepresentationStability,
        CapabilityDomain::OperationalSimplicity,
    ];

    pub fn as_str(&self) -> &'static str {
        match self {
            CapabilityDomain::ExecutionFidelity => "ExecutionFidelity",
            CapabilityDomain::RegimeRobustness => "RegimeRobustness",
            CapabilityDomain::CrossAssetGeneralization => "CrossAssetGeneralization",
            CapabilityDomain::MicrostructureInvariance => "MicrostructureInvariance",
            CapabilityDomain::DefeaterResistance => "DefeaterResistance",
            CapabilityDomain::StatisticalCredibility => "StatisticalCredibility",
            CapabilityDomain::EvaluationSafety => "EvaluationSafety",
            CapabilityDomain::CapacityScalability => "CapacityScalability",
            CapabilityDomain::RepresentationStability => "RepresentationStability",
            CapabilityDomain::OperationalSimplicity => "OperationalSimplicity",
        }
    }
}

/// Evaluation Population Type (D-153 Section 33)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EvaluationPopulation {
    BurnedDiagnosticReal,
    ChronologicalWalkForward,
    PurgedCombinatorialKFold,
    ProtectedFrozenOos,
    FoundrySyntheticNovelty,
    ExternalExecutionParity,
}

impl EvaluationPopulation {
    pub fn is_synthetic(&self) -> bool {
        matches!(self, EvaluationPopulation::FoundrySyntheticNovelty)
    }

    pub fn is_protected(&self) -> bool {
        matches!(self, EvaluationPopulation::ProtectedFrozenOos)
    }
}

/// Strict Metric Categorization
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MetricCategory {
    EngineeringFidelity,
    StressRobustness,
    CounterfactualAgnostic,
    RealizedEconomic,
}

/// Bounded score with uncertainty bounds
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BoundedScore {
    pub value: f64,
    pub lower_bound_95: f64,
    pub upper_bound_95: f64,
    pub sample_size: usize,
    pub effective_sample_size: f64,
}

impl BoundedScore {
    pub fn new(value: f64, lower: f64, upper: f64, n: usize, ess: f64) -> Self {
        Self {
            value: value.clamp(0.0, 1.0),
            lower_bound_95: lower.clamp(0.0, 1.0),
            upper_bound_95: upper.clamp(0.0, 1.0),
            sample_size: n,
            effective_sample_size: ess,
        }
    }
}
