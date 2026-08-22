//! Epistemic Witness Evidence & 9-Dimensional Scorecards (Issue #231, #234, #235, D-130).
//!
//! Owning Authority: V8 Constitution Rules 13, 20, 21, 22.
//!
//! Epistemic Invariant:
//!   Experts are epistemic witnesses, NOT economic sovereigns.
//!   They possess ZERO capital or execution authority.

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;

/// Habitat assessment for an expert observation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum HabitatAssessment {
    InHabitat,
    OutOfHabitat,
    UnknownHabitat,
    Contraindicated,
}

/// Reason for first-class unpenalized abstention.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum AbstentionReason {
    RegimeMismatch,
    UncertaintyHigh,
    InsufficientHistory,
    BoundaryAmbiguity,
    CapacityFull,
    StructuralVeto,
}

/// Epistemic stance emitted by a witness.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ObserverStance {
    Support {
        confidence: f64,
        expected_edge_r: f64,
    },
    Contradict {
        reason: String,
        severity: f64,
    },
    Abstain {
        reason: AbstentionReason,
    },
    Unknown {
        reason: String,
    },
}

/// Observer Evidence (Primitive 4 of 7).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ObserverEvidence {
    pub evidence_id: String,
    pub opportunity_id: String,
    pub observer_id: String,
    pub observer_version: String,
    pub mechanism_family_id: String,
    pub behavior_family_id: String,
    pub dependency_group: String,
    pub stance: ObserverStance,
    pub habitat_assessment: HabitatAssessment,
    pub uncertainty: f64,
    pub evidence_time: i64,
    pub data_lineage: String,
}

impl ObserverEvidence {
    /// Builds and computes the cryptographic BLAKE3 identity for ObserverEvidence.
    pub fn new(
        opportunity_id: impl Into<String>,
        observer_id: impl Into<String>,
        observer_version: impl Into<String>,
        mechanism_family_id: impl Into<String>,
        behavior_family_id: impl Into<String>,
        dependency_group: impl Into<String>,
        stance: ObserverStance,
        habitat_assessment: HabitatAssessment,
        uncertainty: f64,
        evidence_time: i64,
        data_lineage: impl Into<String>,
    ) -> Result<Self, V8CoreError> {
        let opportunity_id = opportunity_id.into();
        let observer_id = observer_id.into();
        let observer_version = observer_version.into();
        let mechanism_family_id = mechanism_family_id.into();
        let behavior_family_id = behavior_family_id.into();
        let dependency_group = dependency_group.into();
        let data_lineage = data_lineage.into();

        if uncertainty < 0.0 || uncertainty > 1.0 {
            return Err(V8CoreError::WitnessReconciliationError(
                format!("Uncertainty ({uncertainty}) must be bounded in [0.0, 1.0]"),
            ));
        }

        let mut evidence = Self {
            evidence_id: String::new(),
            opportunity_id,
            observer_id,
            observer_version,
            mechanism_family_id,
            behavior_family_id,
            dependency_group,
            stance,
            habitat_assessment,
            uncertainty,
            evidence_time,
            data_lineage,
        };
        evidence.evidence_id = evidence.compute_id();
        Ok(evidence)
    }

    /// Computes cryptographic BLAKE3 identity for this evidence stance.
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("ObserverEvidence");
        c.push_str(&self.opportunity_id);
        c.push_str(&self.observer_id);
        c.push_str(&self.observer_version);
        c.push_str(&self.mechanism_family_id);
        c.push_str(&self.behavior_family_id);
        c.push_str(&self.dependency_group);
        c.push_str(&format!("{:?}", self.habitat_assessment));
        c.push_f64(self.uncertainty);
        c.push_i64(self.evidence_time);
        c.push_str(&self.data_lineage);

        match &self.stance {
            ObserverStance::Support { confidence, expected_edge_r } => {
                c.push_str("Support");
                c.push_f64(*confidence);
                c.push_f64(*expected_edge_r);
            }
            ObserverStance::Contradict { reason, severity } => {
                c.push_str("Contradict");
                c.push_str(reason);
                c.push_f64(*severity);
            }
            ObserverStance::Abstain { reason } => {
                c.push_str("Abstain");
                c.push_str(&format!("{:?}", reason));
            }
            ObserverStance::Unknown { reason } => {
                c.push_str("Unknown");
                c.push_str(reason);
            }
        }

        c.finish_blake3_hex()
    }

    pub fn is_active_support(&self) -> bool {
        matches!(self.stance, ObserverStance::Support { .. })
    }

    pub fn is_contradiction(&self) -> bool {
        matches!(self.stance, ObserverStance::Contradict { .. })
    }

    pub fn is_abstention(&self) -> bool {
        matches!(self.stance, ObserverStance::Abstain { .. })
    }
}

/// 9-Dimensional Epistemic Witness Scorecard (Rule 22 / D-130).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WitnessScorecard {
    pub observer_id: String,
    pub habitat_precision: f64,
    pub abstention_quality: f64,
    pub calibration_score: f64,
    pub unique_coverage: f64,
    pub incremental_information: f64,
    pub redundancy_score: f64,
    pub contradiction_value: f64,
    pub decision_utility_ablation: f64,
    pub stability_score: f64,
    pub scorecard_time: i64,
}

impl WitnessScorecard {
    pub fn default_neutral(observer_id: impl Into<String>, timestamp: i64) -> Self {
        Self {
            observer_id: observer_id.into(),
            habitat_precision: 1.0,
            abstention_quality: 1.0,
            calibration_score: 1.0,
            unique_coverage: 1.0,
            incremental_information: 1.0,
            redundancy_score: 0.0,
            contradiction_value: 1.0,
            decision_utility_ablation: 0.0,
            stability_score: 1.0,
            scorecard_time: timestamp,
        }
    }
}
