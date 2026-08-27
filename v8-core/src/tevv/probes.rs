//! 10 Mandatory TEVV Integrity Probes (D-147, D-149, M5).
//!
//! Autonomous safety probes auditing all agent outputs and proposals.
//! Failing any probe immediately emits an immutable DefeaterReceipt (AF-T15).

use serde::{Deserialize, Serialize};
use crate::assurance::claim::AssuranceClaim;
use crate::assurance::defeater::{DefeaterReceipt, DefeaterSeverity};

/// The 10 Mandatory TEVV Integrity Probes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum IntegrityProbeKind {
    PitLookahead,
    TargetChasing,
    CherryPickingOos,
    OverfittingTrialMultiplicity,
    DataSnooping,
    BoundaryEscalation,
    DiscardMasking,
    DefeaterSuppression,
    UncalibratedRealism,
    GhostReceiptHallucination,
}

impl IntegrityProbeKind {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::PitLookahead => "PIT_LOOKAHEAD_PROBE",
            Self::TargetChasing => "TARGET_CHASING_PROBE",
            Self::CherryPickingOos => "CHERRY_PICKING_OOS_PROBE",
            Self::OverfittingTrialMultiplicity => "OVERFITTING_TRIAL_MULTIPLICITY_PROBE",
            Self::DataSnooping => "DATA_SNOOPING_PROBE",
            Self::BoundaryEscalation => "BOUNDARY_ESCALATION_PROBE",
            Self::DiscardMasking => "DISCARD_MASKING_PROBE",
            Self::DefeaterSuppression => "DEFEATER_SUPPRESSION_PROBE",
            Self::UncalibratedRealism => "UNCALIBRATED_REALISM_PROBE",
            Self::GhostReceiptHallucination => "GHOST_RECEIPT_HALLUCINATION_PROBE",
        }
    }
}

pub struct IntegrityProbeAuditor;

impl IntegrityProbeAuditor {
    /// Audits an agent proposal for prompt gaming or metric manipulation (AF-T15).
    pub fn audit_proposal(
        probe: IntegrityProbeKind,
        detected_violation: Option<&str>,
        timestamp_ns: u64,
    ) -> Result<(), DefeaterReceipt> {
        if let Some(reason) = detected_violation {
            let defeater = DefeaterReceipt::new(
                AssuranceClaim::ResearchIntegrity,
                DefeaterSeverity::ConstitutionalVeto,
                format!("{}: {}", probe.as_str(), reason),
                "tevv_probe_auditor".to_string(),
                vec![probe.as_str().to_string()],
                timestamp_ns,
            );
            return Err(defeater);
        }
        Ok(())
    }
}
