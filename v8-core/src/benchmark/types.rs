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

/// Five-tier capital outcome projection evidence grade (D-153 §89, App D)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ProjectionGrade {
    GradeU, // Unknown / Uncertified
    GradeD, // Diagnostic Only
    GradeC, // Synthetic Robustness Only
    GradeB, // Replication Backed
    GradeA, // Empirically Certified
}

impl ProjectionGrade {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::GradeU => "U (Unknown/Uncertified)",
            Self::GradeD => "D (Diagnostic Only)",
            Self::GradeC => "C (Synthetic Robustness Only)",
            Self::GradeB => "B (Replication Backed)",
            Self::GradeA => "A (Empirically Certified)",
        }
    }

    pub fn allows_forward_probability(&self) -> bool {
        matches!(self, Self::GradeB | Self::GradeA)
    }
}

/// Hard Gate State (D-153 §80, §106)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GateState {
    Pass,
    Blocked,
    Unknown,
    Defeated,
    NotApplicable,
}

impl GateState {
    pub fn is_pass(&self) -> bool {
        matches!(self, Self::Pass)
    }

    pub fn is_failure(&self) -> bool {
        matches!(self, Self::Blocked | Self::Defeated)
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Pass => "PASS",
            Self::Blocked => "BLOCKED",
            Self::Unknown => "UNKNOWN",
            Self::Defeated => "DEFEATED",
            Self::NotApplicable => "NOT_APPLICABLE",
        }
    }
}

/// Hard Gate Vector G0–G9 (D-153 §80, App F)
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateVector {
    pub g0_identity: GateState,
    pub g1_causal_pit: GateState,
    pub g2_determinism_ledger: GateState,
    pub g3_benchmark_coverage: GateState,
    pub g4_structural_robustness: GateState,
    pub g5_statistical_credibility: GateState,
    pub g6_protected_oos: GateState,
    pub g7_generalization: GateState,
    pub g8_prospective_shadow: GateState,
    pub g9_live_realization: GateState,
}

impl Default for GateVector {
    fn default() -> Self {
        Self {
            g0_identity: GateState::Unknown,
            g1_causal_pit: GateState::Unknown,
            g2_determinism_ledger: GateState::Unknown,
            g3_benchmark_coverage: GateState::Unknown,
            g4_structural_robustness: GateState::Unknown,
            g5_statistical_credibility: GateState::Unknown,
            g6_protected_oos: GateState::Unknown,
            g7_generalization: GateState::Unknown,
            g8_prospective_shadow: GateState::NotApplicable,
            g9_live_realization: GateState::NotApplicable,
        }
    }
}

impl GateVector {
    /// Non-compensable conjunction check: all active gates must PASS.
    pub fn all_passed(&self) -> bool {
        let active = [
            self.g0_identity,
            self.g1_causal_pit,
            self.g2_determinism_ledger,
            self.g3_benchmark_coverage,
            self.g4_structural_robustness,
            self.g5_statistical_credibility,
        ];
        active.iter().all(|g| g.is_pass())
    }

    /// Any hard failure or defeat triggers immediate overall failure.
    pub fn any_hard_failure(&self) -> bool {
        let all = [
            self.g0_identity,
            self.g1_causal_pit,
            self.g2_determinism_ledger,
            self.g3_benchmark_coverage,
            self.g4_structural_robustness,
            self.g5_statistical_credibility,
            self.g6_protected_oos,
            self.g7_generalization,
            self.g8_prospective_shadow,
            self.g9_live_realization,
        ];
        all.iter().any(|g| g.is_failure())
    }
}

