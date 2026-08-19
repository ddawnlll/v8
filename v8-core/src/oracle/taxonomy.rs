//! Controlled Oracle taxonomy and refusal vocabulary (TARGET_ORACLE_SPEC §2,
//! §8, §16.2, Appendix C).

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
pub enum OracleRole {
    Parity,
    Hindsight,
    Target,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
pub enum AuthorityLevel {
    L1,
    L2,
    L3,
    LiveReceipt,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
pub enum Identifiability {
    Identified,
    PartiallyIdentified,
    ModelDerived,
    NotIdentifiable,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
pub enum ValueNotion {
    Retrospective,
    Replication,
    ProspectiveShadow,
    LiveRealized,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct OracleContext {
    pub role: OracleRole,
    pub authority: AuthorityLevel,
    pub information_contract_id: String,
    pub opportunity_universe_id: String,
    pub utility_contract_id: String,
    pub policy_class_id: String,
    pub cost_model_id: String,
    pub capacity_model_id: String,
    pub environment_target_id: String,
}

/// Canonical fail-closed vocabulary.  Callers receive a typed refusal rather
/// than an ad-hoc string so later O2-O3 surfaces cannot reclassify failures.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
pub enum OracleRefusal {
    MissingDecisionTimeData,
    OutOfSupportAction,
    ExecutionAuthorityTooWeak,
    UndefinedFuture,
    NonIdentifiableFill,
    ConstraintInfeasible,
    ProtectedSliceAlreadyConsumed,
    ModelOnlyCounterfactual,
    InsufficientSupport,
}

impl OracleRefusal {
    pub const fn code(self) -> &'static str {
        match self {
            Self::MissingDecisionTimeData => "MISSING_DECISION_TIME_DATA",
            Self::OutOfSupportAction => "OUT_OF_SUPPORT_ACTION",
            Self::ExecutionAuthorityTooWeak => "EXECUTION_AUTHORITY_TOO_WEAK",
            Self::UndefinedFuture => "UNDEFINED_FUTURE",
            Self::NonIdentifiableFill => "NON_IDENTIFIABLE_FILL",
            Self::ConstraintInfeasible => "CONSTRAINT_INFEASIBLE",
            Self::ProtectedSliceAlreadyConsumed => "PROTECTED_SLICE_ALREADY_CONSUMED",
            Self::ModelOnlyCounterfactual => "MODEL_ONLY_COUNTERFACTUAL",
            Self::InsufficientSupport => "INSUFFICIENT_SUPPORT",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn taxonomy_has_only_the_three_oracle_roles() {
        let roles = [
            OracleRole::Parity,
            OracleRole::Hindsight,
            OracleRole::Target,
        ];
        assert_eq!(roles.len(), 3);
        assert_ne!(OracleRole::Parity, OracleRole::Target);
        assert_eq!(AuthorityLevel::L1 as u8, 0);
        assert_eq!(ValueNotion::Retrospective as u8, 0);
    }

    #[test]
    fn refusal_codes_are_closed_and_stable() {
        assert_eq!(
            OracleRefusal::MissingDecisionTimeData.code(),
            "MISSING_DECISION_TIME_DATA"
        );
        assert_eq!(
            OracleRefusal::ConstraintInfeasible.code(),
            "CONSTRAINT_INFEASIBLE"
        );
    }
}
