//! Assurance Case Adjudication Engine (D-147, D-149, M1).
//!
//! Orchestrates the full evaluation of an EvaluationCaseManifest against attestations and claim rules.
//! Hard defeaters unconditionally propagate to block affected claims.

use crate::assurance::attestation::{AttestationStatus, EvidenceAttestation};
use crate::assurance::case::EvaluationCaseManifest;
use crate::assurance::claim::AssuranceClaim;
use crate::assurance::defeater::{DefeaterReceipt, DefeaterSeverity};
use crate::assurance::receipt::{AssuranceCaseReceipt, ClaimStatus};
use crate::assurance::rules::ClaimRule;
use std::collections::HashMap;

/// Sovereign adjudicator for Assurance Fabric.
pub struct AssuranceCaseAdjudicator;

impl AssuranceCaseAdjudicator {
    /// Adjudicates an entire EvaluationCase against incoming evidence and defeaters.
    pub fn adjudicate(
        manifest: &EvaluationCaseManifest,
        rules: &[ClaimRule],
        attestations: &[EvidenceAttestation],
        defeaters: &[DefeaterReceipt],
        timestamp_ns: u64,
    ) -> AssuranceCaseReceipt {
        let mut claim_statuses = HashMap::new();

        // 1. Process target claims
        for target in &manifest.target_claims {
            // Check if blocked by any constitutional or claim-scoped defeater
            let is_blocked = defeaters.iter().any(|d| {
                d.severity == DefeaterSeverity::ConstitutionalVeto
                    || (d.severity == DefeaterSeverity::ClaimScoped && d.blocked_claim == *target)
            });

            if is_blocked {
                claim_statuses.insert(*target, ClaimStatus::Blocked);
                continue;
            }

            // Find matching rule
            let rule = rules.iter().find(|r| r.target_claim == *target);
            if let Some(r) = rule {
                let passed = r.evaluate(attestations);
                let status = if passed {
                    ClaimStatus::Verified
                } else {
                    ClaimStatus::Falsified
                };
                claim_statuses.insert(*target, status);
            } else {
                // Default evaluation: verify all attestations matching this claim
                let matching: Vec<&EvidenceAttestation> = attestations
                    .iter()
                    .filter(|a| a.target_claim == *target)
                    .collect();

                let status = if matching.is_empty() {
                    ClaimStatus::Unresolved
                } else if matching.iter().all(|a| a.status == AttestationStatus::Verified) {
                    ClaimStatus::Verified
                } else {
                    ClaimStatus::Falsified
                };
                claim_statuses.insert(*target, status);
            }
        }

        // Overall case verdict: ALL target claims must be Verified
        let all_verified = manifest
            .target_claims
            .iter()
            .all(|c| claim_statuses.get(c) == Some(&ClaimStatus::Verified));

        let overall_verdict = if all_verified {
            "ASSURANCE_CASE_VERIFIED"
        } else if defeaters.iter().any(|d| d.severity == DefeaterSeverity::ConstitutionalVeto) {
            "ASSURANCE_CASE_VETOED"
        } else {
            "ASSURANCE_CASE_FALSIFIED"
        };

        AssuranceCaseReceipt::new(
            manifest.case_id.clone(),
            manifest.epoch,
            overall_verdict.to_string(),
            claim_statuses,
            defeaters.to_vec(),
            timestamp_ns,
        )
    }
}
