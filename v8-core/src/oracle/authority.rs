//! Counterfactual authority, identifiability, and fail-closed outcome semantics
//! (TARGET_ORACLE_SPEC §8, §16, §18.1).

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

use crate::hash::Canon;

use super::artifacts::OracleEvaluationRecord;
use super::taxonomy::{AuthorityLevel, Identifiability, OracleContext, OracleRefusal, ValueNotion};

/// Explicit counterfactual authority composition. Authority level and
/// identifiability status are strictly orthogonal (TARGET_ORACLE_SPEC §8.3).
#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct CounterfactualAuthority {
    pub oracle_authority_level: AuthorityLevel,
    pub identifiability_status: Identifiability,
    pub support_rule_id: String,
    pub environment_model_id: String,
    pub assumptions: Vec<String>,
}

impl CounterfactualAuthority {
    pub fn new(
        oracle_authority_level: AuthorityLevel,
        identifiability_status: Identifiability,
        support_rule_id: impl Into<String>,
        environment_model_id: impl Into<String>,
        assumptions: Vec<String>,
    ) -> Self {
        Self {
            oracle_authority_level,
            identifiability_status,
            support_rule_id: support_rule_id.into(),
            environment_model_id: environment_model_id.into(),
            assumptions,
        }
    }

    pub fn identity(&self) -> String {
        let mut c = Canon::new();
        c.push_str("counterfactual-authority-v1");
        c.push_value(&serde_json::json!({
            "oracle_authority_level": format!("{:?}", self.oracle_authority_level),
            "identifiability_status": format!("{:?}", self.identifiability_status),
            "support_rule_id": self.support_rule_id,
            "environment_model_id": self.environment_model_id,
            "assumptions": self.assumptions,
        }));
        c.finish_sha1_hex()
    }

    pub fn is_identified(&self) -> bool {
        self.identifiability_status == Identifiability::Identified
    }
}

/// Typed Oracle evaluation outcome wrapping refusal and authority.
/// UNKNOWN is first-class and never collapses to a zero point estimate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum OracleOutcome {
    Identified {
        point_estimate: f64,
        authority: CounterfactualAuthority,
    },
    PartiallyIdentified {
        lower_bound: f64,
        upper_bound: f64,
        authority: CounterfactualAuthority,
    },
    ModelDerived {
        point_estimate: Option<f64>,
        lower_bound: Option<f64>,
        upper_bound: Option<f64>,
        authority: CounterfactualAuthority,
    },
    Unknown {
        refusal: OracleRefusal,
        authority: CounterfactualAuthority,
    },
}

impl OracleOutcome {
    pub fn identified(
        point: f64,
        authority: CounterfactualAuthority,
    ) -> Result<Self, OracleRefusal> {
        if authority.identifiability_status != Identifiability::Identified {
            return Err(OracleRefusal::InsufficientSupport);
        }
        if !point.is_finite() {
            return Err(OracleRefusal::InsufficientSupport);
        }
        Ok(Self::Identified {
            point_estimate: point,
            authority,
        })
    }

    pub fn partially_identified(
        lower: f64,
        upper: f64,
        authority: CounterfactualAuthority,
    ) -> Result<Self, OracleRefusal> {
        if authority.identifiability_status != Identifiability::PartiallyIdentified {
            return Err(OracleRefusal::InsufficientSupport);
        }
        if !lower.is_finite() || !upper.is_finite() || lower > upper {
            return Err(OracleRefusal::InsufficientSupport);
        }
        Ok(Self::PartiallyIdentified {
            lower_bound: lower,
            upper_bound: upper,
            authority,
        })
    }

    pub fn model_derived(
        point: Option<f64>,
        lower: Option<f64>,
        upper: Option<f64>,
        authority: CounterfactualAuthority,
    ) -> Result<Self, OracleRefusal> {
        if authority.identifiability_status != Identifiability::ModelDerived {
            return Err(OracleRefusal::InsufficientSupport);
        }
        Ok(Self::ModelDerived {
            point_estimate: point,
            lower_bound: lower,
            upper_bound: upper,
            authority,
        })
    }

    pub fn unknown(refusal: OracleRefusal, authority: CounterfactualAuthority) -> Self {
        Self::Unknown {
            refusal,
            authority,
        }
    }

    pub fn is_unknown(&self) -> bool {
        matches!(self, Self::Unknown { .. })
    }

    pub fn is_identified(&self) -> bool {
        matches!(self, Self::Identified { .. })
    }

    pub fn point_estimate(&self) -> Option<f64> {
        match self {
            Self::Identified { point_estimate, .. } => Some(*point_estimate),
            Self::ModelDerived { point_estimate, .. } => *point_estimate,
            Self::PartiallyIdentified { .. } | Self::Unknown { .. } => None,
        }
    }

    pub fn bounds(&self) -> Option<(f64, f64)> {
        match self {
            Self::Identified { point_estimate, .. } => Some((*point_estimate, *point_estimate)),
            Self::PartiallyIdentified {
                lower_bound,
                upper_bound,
                ..
            } => Some((*lower_bound, *upper_bound)),
            Self::ModelDerived {
                lower_bound: Some(l),
                upper_bound: Some(u),
                ..
            } => Some((*l, *u)),
            _ => None,
        }
    }

    pub fn refusal_reason(&self) -> Option<OracleRefusal> {
        match self {
            Self::Unknown { refusal, .. } => Some(*refusal),
            _ => None,
        }
    }

    pub fn refusal_code(&self) -> Option<&'static str> {
        self.refusal_reason().map(|r| r.code())
    }

    pub fn authority(&self) -> &CounterfactualAuthority {
        match self {
            Self::Identified { authority, .. }
            | Self::PartiallyIdentified { authority, .. }
            | Self::ModelDerived { authority, .. }
            | Self::Unknown { authority, .. } => authority,
        }
    }

    /// Compare outcomes for decision ordering.
    /// Overlapping intervals fail closed with `OracleRefusal::InsufficientSupport`.
    /// UNKNOWN and ModelDerived fail closed with their respective refusal.
    pub fn compare_for_ordering(&self, other: &Self) -> Result<std::cmp::Ordering, OracleRefusal> {
        match (self, other) {
            (Self::Unknown { refusal, .. }, _) => Err(*refusal),
            (_, Self::Unknown { refusal, .. }) => Err(*refusal),
            (Self::ModelDerived { .. }, _) | (_, Self::ModelDerived { .. }) => {
                Err(OracleRefusal::ModelOnlyCounterfactual)
            }
            (
                Self::Identified {
                    point_estimate: a, ..
                },
                Self::Identified {
                    point_estimate: b, ..
                },
            ) => a
                .partial_cmp(b)
                .ok_or(OracleRefusal::InsufficientSupport),
            (a, b) => {
                let (a_lo, a_hi) = a.bounds().ok_or(OracleRefusal::InsufficientSupport)?;
                let (b_lo, b_hi) = b.bounds().ok_or(OracleRefusal::InsufficientSupport)?;
                if a_hi < b_lo {
                    Ok(std::cmp::Ordering::Less)
                } else if a_lo > b_hi {
                    Ok(std::cmp::Ordering::Greater)
                } else {
                    // Overlapping intervals fail closed
                    Err(OracleRefusal::InsufficientSupport)
                }
            }
        }
    }

    pub fn to_evaluation_record(
        &self,
        context: &OracleContext,
        candidate_population_hash: &str,
        action_manifest_hash: &str,
        simulator_or_receipt_hash: &str,
        code_hash: &str,
        config_hash: &str,
        value_notion: ValueNotion,
        lineage_id: &str,
    ) -> OracleEvaluationRecord {
        let auth = self.authority();
        let (pt, lo, hi) = match self {
            Self::Identified { point_estimate, .. } => (Some(*point_estimate), None, None),
            Self::PartiallyIdentified {
                lower_bound,
                upper_bound,
                ..
            } => (None, Some(*lower_bound), Some(*upper_bound)),
            Self::ModelDerived {
                point_estimate,
                lower_bound,
                upper_bound,
                ..
            } => (*point_estimate, *lower_bound, *upper_bound),
            Self::Unknown { .. } => (None, None, None),
        };

        let mut rec = OracleEvaluationRecord {
            evaluation_id: String::new(),
            oracle_role: context.role,
            authority_level: auth.oracle_authority_level,
            identifiability_status: auth.identifiability_status,
            information_contract_id: context.information_contract_id.clone(),
            opportunity_universe_id: context.opportunity_universe_id.clone(),
            utility_contract_id: context.utility_contract_id.clone(),
            policy_class_id: context.policy_class_id.clone(),
            cost_model_id: context.cost_model_id.clone(),
            capacity_model_id: context.capacity_model_id.clone(),
            environment_target_id: context.environment_target_id.clone(),
            candidate_population_hash: candidate_population_hash.to_string(),
            action_manifest_hash: action_manifest_hash.to_string(),
            simulator_or_receipt_hash: simulator_or_receipt_hash.to_string(),
            code_hash: code_hash.to_string(),
            config_hash: config_hash.to_string(),
            value_notion,
            point_estimate: pt,
            lower_bound: lo,
            upper_bound: hi,
            uncertainty_artifact_id: None,
            refusal_reason: self.refusal_code().map(ToString::to_string),
            assumptions: auth.assumptions.clone(),
            lineage_id: lineage_id.to_string(),
        };
        rec.bind_identity();
        rec
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_authority(level: AuthorityLevel, ident: Identifiability) -> CounterfactualAuthority {
        CounterfactualAuthority::new(
            level,
            ident,
            "l1-support-v1",
            "env-model-v1",
            vec!["L1_BAR_CLOSE".into()],
        )
    }

    #[test]
    fn unknown_returns_no_numeric_point_value() {
        let auth = sample_authority(AuthorityLevel::L1, Identifiability::NotIdentifiable);
        let outcome = OracleOutcome::unknown(OracleRefusal::MissingDecisionTimeData, auth);
        assert!(outcome.is_unknown());
        assert_eq!(outcome.point_estimate(), None);
        assert_eq!(outcome.bounds(), None);
        assert_eq!(
            outcome.refusal_code(),
            Some("MISSING_DECISION_TIME_DATA")
        );
    }

    #[test]
    fn identified_outcome_carries_point_estimate() {
        let auth = sample_authority(AuthorityLevel::L1, Identifiability::Identified);
        let outcome = OracleOutcome::identified(1.25, auth).unwrap();
        assert!(outcome.is_identified());
        assert_eq!(outcome.point_estimate(), Some(1.25));
        assert_eq!(outcome.bounds(), Some((1.25, 1.25)));
        assert_eq!(outcome.refusal_reason(), None);
    }

    #[test]
    fn partially_identified_overlapping_intervals_fail_closed_for_ordering() {
        let auth = sample_authority(AuthorityLevel::L1, Identifiability::PartiallyIdentified);
        let a = OracleOutcome::partially_identified(0.5, 1.5, auth.clone()).unwrap();
        let b = OracleOutcome::partially_identified(1.0, 2.0, auth.clone()).unwrap();
        let c = OracleOutcome::partially_identified(2.5, 3.5, auth).unwrap();

        // Disjoint intervals compare successfully
        assert_eq!(a.compare_for_ordering(&c), Ok(std::cmp::Ordering::Less));
        assert_eq!(c.compare_for_ordering(&a), Ok(std::cmp::Ordering::Greater));

        // Overlapping intervals fail closed
        assert_eq!(
            a.compare_for_ordering(&b),
            Err(OracleRefusal::InsufficientSupport)
        );
    }

    #[test]
    fn unknown_fails_closed_in_ordering_comparison() {
        let auth_id = sample_authority(AuthorityLevel::L1, Identifiability::Identified);
        let auth_unk = sample_authority(AuthorityLevel::L1, Identifiability::NotIdentifiable);
        let good = OracleOutcome::identified(1.0, auth_id).unwrap();
        let bad = OracleOutcome::unknown(OracleRefusal::ExecutionAuthorityTooWeak, auth_unk);

        assert_eq!(
            good.compare_for_ordering(&bad),
            Err(OracleRefusal::ExecutionAuthorityTooWeak)
        );
        assert_eq!(
            bad.compare_for_ordering(&good),
            Err(OracleRefusal::ExecutionAuthorityTooWeak)
        );
    }
}
