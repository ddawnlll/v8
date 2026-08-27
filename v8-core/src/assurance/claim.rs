//! Operational Assurance Claims & Taxonomy (D-147, D-149, M0_CLOSED, M1).
//!
//! Formalizes the 9 operational assurance claims evaluated by the Assurance Fabric.
//! Invariant: Synthetic evidence cannot satisfy ECONOMIC_REPLICATION or REALIZED_CASHFLOW.

use serde::{Deserialize, Serialize};
use crate::claims::StatutoryClaimClass;

/// The 9 Operational Assurance Claims evaluated across the pipeline.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum AssuranceClaim {
    /// Zero undefined behaviors, type memory safety, bit-level deterministic reproducibility.
    EngineeringIntegrity,
    /// Point-in-time causation, strictly ex-ante signal conditioning, no lookahead/leakage.
    SemanticIntegrity,
    /// Lineage-aware trial debt accounting, holdout isolation, probe resistance.
    ResearchIntegrity,
    /// Stability across regime shifts, jump shocks, volatility clusters, and liquidity holes.
    StructuralRobustness,
    /// Verified positive edge after realistic taker fees, funding, and execution slippage.
    EconomicReplication,
    /// Efficient capture of identified oracle opportunities with low unforced regret.
    OpportunityCapture,
    /// Out-of-sample forward stability under prospective shadow observation.
    ProspectiveEfficacy,
    /// Reconciled double-entry ledger settlement on live/historical venue physical tape.
    RealizedCashflow,
    /// Multi-dimensional readiness qualification across all statutory requirements.
    DeploymentQualified,
}

impl AssuranceClaim {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::EngineeringIntegrity => "ENGINEERING_INTEGRITY",
            Self::SemanticIntegrity => "SEMANTIC_INTEGRITY",
            Self::ResearchIntegrity => "RESEARCH_INTEGRITY",
            Self::StructuralRobustness => "STRUCTURAL_ROBUSTNESS",
            Self::EconomicReplication => "ECONOMIC_REPLICATION",
            Self::OpportunityCapture => "OPPORTUNITY_CAPTURE",
            Self::ProspectiveEfficacy => "PROSPECTIVE_EFFICACY",
            Self::RealizedCashflow => "REALIZED_CASHFLOW",
            Self::DeploymentQualified => "DEPLOYMENT_QUALIFIED",
        }
    }

    /// Maps the operational assurance claim to the underlying statutory claim class.
    pub const fn to_statutory_class(&self) -> StatutoryClaimClass {
        match self {
            Self::EngineeringIntegrity => StatutoryClaimClass::DiagnosticSignal,
            Self::SemanticIntegrity => StatutoryClaimClass::DiagnosticSignal,
            Self::ResearchIntegrity => StatutoryClaimClass::DiagnosticSignal,
            Self::StructuralRobustness => StatutoryClaimClass::DiagnosticSignal,
            Self::OpportunityCapture => StatutoryClaimClass::CounterfactualPotential,
            Self::EconomicReplication => StatutoryClaimClass::SimulatedCashflow,
            Self::ProspectiveEfficacy => StatutoryClaimClass::SupportedEdge,
            Self::RealizedCashflow => StatutoryClaimClass::RealizedCashflow,
            Self::DeploymentQualified => StatutoryClaimClass::SupportedEdge,
        }
    }

    /// Returns true if synthetic evidence is permitted to contribute to this claim.
    pub const fn accepts_synthetic_evidence(&self) -> bool {
        match self {
            Self::EngineeringIntegrity => true,
            Self::SemanticIntegrity => true,
            Self::ResearchIntegrity => true,
            Self::StructuralRobustness => true,
            Self::OpportunityCapture => false,
            Self::EconomicReplication => false,
            Self::ProspectiveEfficacy => false,
            Self::RealizedCashflow => false,
            Self::DeploymentQualified => false,
        }
    }
}
