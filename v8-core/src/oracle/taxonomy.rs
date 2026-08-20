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

// ---------------------------------------------------------------------------
// Issue #AUD-010: The Four Orthogonal Epistemic and Authority Dimensions
// (V8_CONSTITUTION Rule 12, TARGET_ORACLE_SPEC §7, §16, EVALUATION_EVIDENCE_SYSTEM §1-4)
// ---------------------------------------------------------------------------

/// Axis 1: Code & Implementation Verification Dimension.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub enum VerificationDimension {
    /// Satisfies unit tests, type invariants, and state-machine transitions.
    ContractVerified,
    /// Satisfies D-116 differential parity against independent reference engine.
    ImplementationParity,
    /// Satisfies PIT temporal non-interference and permutation invariance.
    MetamorphicInvariant,
}

impl VerificationDimension {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ContractVerified => "CONTRACT_VERIFIED",
            Self::ImplementationParity => "IMPLEMENTATION_PARITY",
            Self::MetamorphicInvariant => "METAMORPHIC_INVARIANT",
        }
    }
}

/// Axis 2: Economic Evidence & Promotion Stage (Constitution Rule 12).
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub enum EconomicEvidenceStage {
    /// Default state for all unpromoted / uncertified research: NO ECONOMIC CLAIM.
    NoEconomicClaim,
    /// Hindsight / regret analysis proves value recovery is structurally feasible.
    RecoverableWithinClass,
    /// Policy admissible under certified multiple-testing and risk constraints.
    PromotableWithinContract,
    /// Empirically demonstrated edge in non-interfering live paper shadow execution.
    ShadowSupported,
    /// Realized predictive profitability with certified multiple-testing adjustments.
    LiveSupported,
}

impl EconomicEvidenceStage {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NoEconomicClaim => "NO_ECONOMIC_CLAIM",
            Self::RecoverableWithinClass => "RECOVERABLE_WITHIN_CLASS",
            Self::PromotableWithinContract => "PROMOTABLE_WITHIN_CONTRACT",
            Self::ShadowSupported => "SHADOW_SUPPORTED",
            Self::LiveSupported => "LIVE_SUPPORTED",
        }
    }
}

/// Axis 3: Counterfactual & Microstructure Authority Level.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub enum CounterfactualAuthority {
    /// Fully identified from observable order book / matching engine state.
    Identified,
    /// Bounded by partial identification intervals (e.g. Manski bounds).
    PartiallyIdentified,
    /// Derived from parametric or historical simulation models (uncertified).
    ModelDerived,
    /// Microstructure or queue dynamics cannot be identified from available data.
    NotIdentifiable,
}

impl CounterfactualAuthority {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Identified => "IDENTIFIED",
            Self::PartiallyIdentified => "PARTIALLY_IDENTIFIED",
            Self::ModelDerived => "MODEL_DERIVED",
            Self::NotIdentifiable => "NOT_IDENTIFIABLE",
        }
    }
}

/// Axis 4: Statistical Hypothesis Testing Verdict (arXiv:2607.20093 §4).
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub enum StatisticalVerdict {
    /// Statistically significant rejection of the null with FDR/FWER control.
    Supported,
    /// Statistically significant evidence against the edge hypothesis (negative result).
    Refuted,
    /// Insufficient sample size or power to distinguish signal from noise.
    InconclusiveUnderpowered,
}

impl StatisticalVerdict {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Supported => "SUPPORTED",
            Self::Refuted => "REFUTED",
            Self::InconclusiveUnderpowered => "INCONCLUSIVE_UNDERPOWERED",
        }
    }
}

/// Canonical Unknown Reason Code Attribution Surface.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub enum UnknownReasonCode {
    MissingDecisionTimeData,
    NonIdentifiableFill,
    InsufficientSupport,
    ModelOnlyCounterfactual,
    ExecutionAuthorityTooWeak,
    OutOfSupportAction,
    UndefinedFuture,
    ConstraintInfeasible,
    ProtectedSliceAlreadyConsumed,
}

impl UnknownReasonCode {
    pub const fn code(self) -> &'static str {
        match self {
            Self::MissingDecisionTimeData => "MISSING_DECISION_TIME_DATA",
            Self::NonIdentifiableFill => "NON_IDENTIFIABLE_FILL",
            Self::InsufficientSupport => "INSUFFICIENT_SUPPORT",
            Self::ModelOnlyCounterfactual => "MODEL_ONLY_COUNTERFACTUAL",
            Self::ExecutionAuthorityTooWeak => "EXECUTION_AUTHORITY_TOO_WEAK",
            Self::OutOfSupportAction => "OUT_OF_SUPPORT_ACTION",
            Self::UndefinedFuture => "UNDEFINED_FUTURE",
            Self::ConstraintInfeasible => "CONSTRAINT_INFEASIBLE",
            Self::ProtectedSliceAlreadyConsumed => "PROTECTED_SLICE_ALREADY_CONSUMED",
        }
    }
}

/// Authority Error for invalid states or Rule 12 violations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuthorityError {
    AmbiguousTaxonomyState(String),
    UncertifiedEconomicClaim(String),
    InvalidReasonCode(String),
}

impl std::fmt::Display for AuthorityError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::AmbiguousTaxonomyState(s) => write!(f, "Ambiguous taxonomy state: {s}"),
            Self::UncertifiedEconomicClaim(s) => write!(f, "Rule 12 violation (uncertified economic claim): {s}"),
            Self::InvalidReasonCode(s) => write!(f, "Invalid unknown reason code: {s}"),
        }
    }
}

impl std::error::Error for AuthorityError {}

/// Full Orthogonal Product Space State ($I1$ invariant).
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub struct AuditState {
    pub verification: VerificationDimension,
    pub economic_stage: EconomicEvidenceStage,
    pub counterfactual_authority: CounterfactualAuthority,
    pub statistical_verdict: StatisticalVerdict,
}

impl AuditState {
    pub fn new(
        verification: VerificationDimension,
        economic_stage: EconomicEvidenceStage,
        counterfactual_authority: CounterfactualAuthority,
        statistical_verdict: StatisticalVerdict,
    ) -> Self {
        Self {
            verification,
            economic_stage,
            counterfactual_authority,
            statistical_verdict,
        }
    }

    /// Enforce Constitution Rule 12: No uncertified economic edge claim.
    pub fn validate_rule12(&self) -> Result<(), AuthorityError> {
        if (self.economic_stage == EconomicEvidenceStage::LiveSupported
            || self.economic_stage == EconomicEvidenceStage::ShadowSupported)
            && (self.counterfactual_authority == CounterfactualAuthority::ModelDerived
                || self.counterfactual_authority == CounterfactualAuthority::NotIdentifiable
                || self.statistical_verdict != StatisticalVerdict::Supported)
        {
            return Err(AuthorityError::UncertifiedEconomicClaim(format!(
                "Cannot claim {:?} when authority is {:?} and statistical verdict is {:?}",
                self.economic_stage, self.counterfactual_authority, self.statistical_verdict
            )));
        }
        Ok(())
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
