//! Non-Scalar Revocable Production Evidence Certificate (D-147, D-149, D-150, Rules 28-30, M6).
//!
//! Enforces:
//! 1. Multi-dimensional qualification vector — scalar collapsing / averaging is FORBIDDEN (AF-T19, D150-T14).
//! 2. Time-bounded validity horizon — expired certificate is invalid (AF-T08, D150-I01).
//! 3. Revocable on active defeaters or out-of-bounds performance drawdowns (D150-I15).
//! 4. Typed lifecycle states: ACTIVE / QUALIFIED, SUPERSEDED, QUARANTINED, REVOKED, DEFEATED, EXPIRED.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::assurance::case::EvaluationEpoch;
use crate::assurance::receipt::ClaimStatus;

/// Status of the Production Evidence Certificate (D-150 Section 11).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CertificateStatus {
    Qualified, // Equivalent to Active
    Active,
    Expired,
    Revoked(String),
    Defeated,
    Quarantined(String),
    Superseded,
}

impl CertificateStatus {
    pub fn is_active_or_qualified(&self) -> bool {
        matches!(self, CertificateStatus::Qualified | CertificateStatus::Active)
    }

    pub fn is_revoked(&self) -> bool {
        matches!(self, CertificateStatus::Revoked(_))
    }

    pub fn is_quarantined(&self) -> bool {
        matches!(self, CertificateStatus::Quarantined(_))
    }

    pub fn is_superseded(&self) -> bool {
        matches!(self, CertificateStatus::Superseded)
    }
}

/// The Non-Scalar V8.5 Production Evidence Certificate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProductionEvidenceCertificate {
    pub certificate_id: String,
    pub policy_id: String,
    pub policy_code_hash: String,
    pub epoch: EvaluationEpoch,
    pub issued_at_timestamp_ns: u64,
    pub valid_until_timestamp_ns: u64,
    pub engineering_status: ClaimStatus,
    pub semantic_status: ClaimStatus,
    pub research_status: ClaimStatus,
    pub structural_status: ClaimStatus,
    pub economic_status: ClaimStatus,
    pub opportunity_status: ClaimStatus,
    pub prospective_status: ClaimStatus,
    pub realized_status: ClaimStatus,
    pub lgng_score: f64,
    pub max_drawdown_pct: f64,
    pub opportunity_value_recall_pct: f64,
    pub status: CertificateStatus,
    pub supersedes_cert_id: Option<String>,
    pub revokes_cert_id: Option<String>,
    pub world_coverage_root: Option<String>,
    pub monitoring_plan_id: Option<String>,
    pub is_current: bool,
    pub certificate_digest: String,
}

impl ProductionEvidenceCertificate {
    /// Creates and cryptographically seals a new Production Evidence Certificate.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        policy_id: &str,
        policy_code_hash: &str,
        epoch: EvaluationEpoch,
        issued_at_ns: u64,
        valid_duration_ns: u64,
        engineering_status: ClaimStatus,
        semantic_status: ClaimStatus,
        research_status: ClaimStatus,
        structural_status: ClaimStatus,
        economic_status: ClaimStatus,
        opportunity_status: ClaimStatus,
        prospective_status: ClaimStatus,
        realized_status: ClaimStatus,
        lgng: f64,
        max_dd: f64,
        value_recall: f64,
    ) -> Self {
        let valid_until_ns = issued_at_ns + valid_duration_ns;

        let mut hasher = Sha256::new();
        hasher.update(policy_id.as_bytes());
        hasher.update(policy_code_hash.as_bytes());
        hasher.update(&epoch.0.to_le_bytes());
        hasher.update(&issued_at_ns.to_le_bytes());
        hasher.update(&valid_until_ns.to_le_bytes());
        hasher.update(&lgng.to_le_bytes());
        let digest = format!("{:x}", hasher.finalize());
        let certificate_id = format!("cert-v85-{}", &digest[..16]);

        Self {
            certificate_id,
            policy_id: policy_id.to_string(),
            policy_code_hash: policy_code_hash.to_string(),
            epoch,
            issued_at_timestamp_ns: issued_at_ns,
            valid_until_timestamp_ns: valid_until_ns,
            engineering_status,
            semantic_status,
            research_status,
            structural_status,
            economic_status,
            opportunity_status,
            prospective_status,
            realized_status,
            lgng_score: lgng,
            max_drawdown_pct: max_dd,
            opportunity_value_recall_pct: value_recall,
            status: CertificateStatus::Qualified,
            supersedes_cert_id: None,
            revokes_cert_id: None,
            world_coverage_root: None,
            monitoring_plan_id: None,
            is_current: true,
            certificate_digest: digest,
        }
    }

    /// Evaluates current status of certificate at a given point in time (AF-T08, D150-T14).
    pub fn evaluate_status(&self, current_timestamp_ns: u64, has_active_defeaters: bool) -> CertificateStatus {
        if has_active_defeaters {
            return CertificateStatus::Defeated;
        }
        if !self.is_current && self.status == CertificateStatus::Superseded {
            return CertificateStatus::Superseded;
        }
        if current_timestamp_ns > self.valid_until_timestamp_ns {
            return CertificateStatus::Expired;
        }
        // Multi-dimensional non-scalar check: All statutory claims must be verified
        if self.engineering_status == ClaimStatus::Verified
            && self.semantic_status == ClaimStatus::Verified
            && self.research_status == ClaimStatus::Verified
            && self.structural_status == ClaimStatus::Verified
            && self.economic_status == ClaimStatus::Verified
            && self.opportunity_status == ClaimStatus::Verified
            && self.prospective_status == ClaimStatus::Verified
            && self.lgng_score > 0.0
            && self.max_drawdown_pct < 15.0
        {
            CertificateStatus::Qualified
        } else {
            CertificateStatus::Revoked("MULTI_DIMENSIONAL_STATUS_DEFICIT".to_string())
        }
    }

    /// Marks the certificate as superseded by a successor epoch's certificate (D150-T07).
    pub fn mark_superseded(&mut self, successor_cert_id: &str) {
        self.status = CertificateStatus::Superseded;
        self.is_current = false;
        self.supersedes_cert_id = Some(successor_cert_id.to_string());
    }

    /// Places the certificate into quarantine due to contested or incomplete evidence (D-150).
    pub fn quarantine(&mut self, reason: &str) {
        self.status = CertificateStatus::Quarantined(reason.to_string());
    }

    /// Revokes the certificate due to a hard defeater (D150-I15).
    pub fn revoke(&mut self, reason: &str, revoking_cert_or_defeater_id: Option<&str>) {
        self.status = CertificateStatus::Revoked(reason.to_string());
        self.is_current = false;
        if let Some(id) = revoking_cert_or_defeater_id {
            self.revokes_cert_id = Some(id.to_string());
        }
    }

    /// Verifies cryptographic integrity of the certificate digest.
    pub fn verify_integrity(&self) -> bool {
        let mut hasher = Sha256::new();
        hasher.update(self.policy_id.as_bytes());
        hasher.update(self.policy_code_hash.as_bytes());
        hasher.update(&self.epoch.0.to_le_bytes());
        hasher.update(&self.issued_at_timestamp_ns.to_le_bytes());
        hasher.update(&self.valid_until_timestamp_ns.to_le_bytes());
        hasher.update(&self.lgng_score.to_le_bytes());
        let computed = format!("{:x}", hasher.finalize());
        computed == self.certificate_digest
    }
}
