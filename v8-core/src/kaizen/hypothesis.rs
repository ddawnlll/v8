//! V8 Kaizen Continuous Improvement Engine — Falsifiable Research Hypothesis Records.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §3.1 (Hypothesis Formulation)
//! - `HYPOTHESIS_LAB_PROTOCOL.md` §1–4
//! - arXiv:2606.01650 (*Post-Selection Inference, Covariance Lineage, and Overfitting Penalties in Quantitative Strategy Search*)

use serde::{Deserialize, Serialize};

use crate::kaizen::challenger::ChallengerFamilySpec;
use crate::kaizen::diagnosis::{ExpertId, FailureTag, ForensicAssessment, VariantId};

/// Canonical hypothesis error types.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HypothesisError {
    UnfalsifiableClaim(String),
    UnboundedSearchSpace(String),
    InvalidLineage(String),
}

impl std::fmt::Display for HypothesisError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnfalsifiableClaim(msg) => write!(f, "UNFALSIFIABLE_CLAIM: {msg}"),
            Self::UnboundedSearchSpace(msg) => write!(f, "UNBOUNDED_SEARCH_SPACE: {msg}"),
            Self::InvalidLineage(msg) => write!(f, "INVALID_LINEAGE: {msg}"),
        }
    }
}

impl std::error::Error for HypothesisError {}

/// An observed forensic finding extracted from diagnostics.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResearchFinding {
    pub finding_id: String,
    pub assessment: ForensicAssessment,
    pub primary_failure_tag: FailureTag,
    pub observation_summary: String,
    pub timestamp_ns: i64,
}

/// Quantified falsification rule for a scientific hypothesis.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FalsificationRule {
    pub metric_target: String,
    pub threshold: f64,
    pub max_drawdown_ceiling: Option<f64>,
    pub min_wfa_pass_rate: Option<f64>,
}

impl FalsificationRule {
    pub fn new(
        metric_target: &str,
        threshold: f64,
        max_drawdown_ceiling: Option<f64>,
        min_wfa_pass_rate: Option<f64>,
    ) -> Result<Self, HypothesisError> {
        if metric_target.trim().is_empty() {
            return Err(HypothesisError::UnfalsifiableClaim(
                "metric_target cannot be empty".to_string(),
            ));
        }
        if threshold.is_nan() || threshold.is_infinite() {
            return Err(HypothesisError::UnfalsifiableClaim(
                "threshold must be a finite number".to_string(),
            ));
        }
        if let Some(dd) = max_drawdown_ceiling {
            if dd.is_nan() || dd <= 0.0 {
                return Err(HypothesisError::UnfalsifiableClaim(
                    "max_drawdown_ceiling must be positive".to_string(),
                ));
            }
        }
        if let Some(wfa) = min_wfa_pass_rate {
            if wfa.is_nan() || !(0.0..=1.0).contains(&wfa) {
                return Err(HypothesisError::UnfalsifiableClaim(
                    "min_wfa_pass_rate must be in [0, 1]".to_string(),
                ));
            }
        }

        Ok(Self {
            metric_target: metric_target.to_string(),
            threshold,
            max_drawdown_ceiling,
            min_wfa_pass_rate,
        })
    }
}

/// An immutable, schema-validated research hypothesis.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HypothesisRecord {
    pub hypothesis_id: String,
    pub parent_finding_id: String,
    pub expert_id: ExpertId,
    pub variant_id: VariantId,
    pub mechanism_claim: String,
    pub falsification_rule: FalsificationRule,
    pub challenger_family_id: String,
    pub created_ts_ns: i64,
}

/// Generates findings from forensic assessments without mutating runtime experts (Invariant I1).
pub struct FindingGenerator;

impl FindingGenerator {
    pub fn from_assessment(
        assessment: &ForensicAssessment,
        timestamp_ns: i64,
    ) -> Vec<ResearchFinding> {
        let mut findings = Vec::new();

        for (idx, &tag) in assessment.tags.iter().enumerate() {
            let summary = match tag {
                FailureTag::ObservedGrossNegative => format!(
                    "Observed gross underperformance: gross_R={:.4}",
                    assessment.gross_r
                ),
                FailureTag::CostDominated => format!(
                    "Cost dominated: gross_R={:.4} > 0 but net_R={:.4} <= 0 (fee={:.4}, slip={:.4}, fund={:.4})",
                    assessment.gross_r,
                    assessment.net_r,
                    assessment.fee_r,
                    assessment.slippage_r,
                    assessment.funding_r
                ),
                FailureTag::ParameterFragile => {
                    "Parameter fragile: candidate collapses under neighborhood perturbation"
                        .to_string()
                }
                FailureTag::RegimeFragile => {
                    let fragile_regimes: Vec<&str> = assessment
                        .regime_breakdown
                        .iter()
                        .filter(|r| r.is_fragile)
                        .map(|r| r.regime_name.as_str())
                        .collect();
                    format!(
                        "Regime fragile: performance fails in regimes: {:?}",
                        fragile_regimes
                    )
                }
            };

            findings.push(ResearchFinding {
                finding_id: format!("{}_{}_f_{:02}", assessment.expert_id, assessment.variant_id, idx),
                assessment: assessment.clone(),
                primary_failure_tag: tag,
                observation_summary: summary,
                timestamp_ns,
            });
        }

        findings
    }
}

/// Unprescriptive hypothesis generator.
pub struct HypothesisGenerator;

impl HypothesisGenerator {
    pub fn generate(
        finding: &ResearchFinding,
        mechanism_claim: &str,
        falsification_rule: FalsificationRule,
        challenger_spec: &ChallengerFamilySpec,
        timestamp_ns: i64,
    ) -> Result<HypothesisRecord, HypothesisError> {
        if mechanism_claim.trim().is_empty() {
            return Err(HypothesisError::UnfalsifiableClaim(
                "mechanism_claim cannot be empty".to_string(),
            ));
        }

        challenger_spec.validate()?;

        let hypothesis_id = format!(
            "hyp_{}_{}",
            finding.finding_id, challenger_spec.family_id
        );

        Ok(HypothesisRecord {
            hypothesis_id,
            parent_finding_id: finding.finding_id.clone(),
            expert_id: finding.assessment.expert_id.clone(),
            variant_id: finding.assessment.variant_id.clone(),
            mechanism_claim: mechanism_claim.to_string(),
            falsification_rule,
            challenger_family_id: challenger_spec.family_id.clone(),
            created_ts_ns: timestamp_ns,
        })
    }
}
