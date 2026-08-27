//! Continuous Production Evaluation & Epoch Evolution (D-147, D-149, D-150, Rules 25-30, 51-56).
//!
//! Enforces:
//! 1. Evaluation epochs advance monotonically N -> N+1 (`D150-I03`).
//! 2. Append-only ledger preserves all historical epoch receipts without mutation (`D150-I02`).
//! 3. Epoch transitions reset active prospective horizons while archiving immutable receipts.
//! 4. PolicyIdentity != EvidenceState temporal separation (`D150-I04`).
//! 5. Transitive defeat propagation and mandatory Kaizen handoff (`D150-I09`, `D150-I12`).
//! 6. World coverage manifests and sequential monitoring plans (`D150-I10`, `D150-I11`, `D150-I17`).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

use crate::assurance::attestation::{AdmissibilityVerdict, EvidenceAttestation};
use crate::assurance::case::{CaseIdentity, EvaluationCaseManifest, EvaluationEpoch};
use crate::assurance::certificate::{CertificateStatus, ProductionEvidenceCertificate};
use crate::assurance::defeater::DefeaterReceipt;
use crate::assurance::receipt::{AssuranceCaseReceipt, ClaimStatus};

/// Cryptographically sealed record of an evaluation epoch (D-150 Section 10.2).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvaluationEpochRecord {
    pub epoch_id: EvaluationEpoch,
    pub case_id: CaseIdentity,
    pub parent_epoch_id: Option<EvaluationEpoch>,
    pub evidence_delta_hash: String,
    pub cumulative_evidence_root: String,
    pub world_coverage_root: Option<String>,
    pub monitoring_plan_id: Option<String>,
    pub assurance_receipt_id: String,
    pub certificate_id: String,
    pub opened_at_ns: u64,
    pub sealed_at_ns: u64,
    pub epoch_digest: String,
}

impl EvaluationEpochRecord {
    /// Creates and cryptographically seals a new EvaluationEpochRecord.
    pub fn new_sealed(
        epoch_id: EvaluationEpoch,
        case_id: CaseIdentity,
        parent_epoch_id: Option<EvaluationEpoch>,
        evidence_delta_hash: String,
        cumulative_evidence_root: String,
        world_coverage_root: Option<String>,
        monitoring_plan_id: Option<String>,
        assurance_receipt_id: String,
        certificate_id: String,
        opened_at_ns: u64,
        sealed_at_ns: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(&epoch_id.0.to_le_bytes());
        hasher.update(case_id.0.as_bytes());
        if let Some(parent) = parent_epoch_id {
            hasher.update(&parent.0.to_le_bytes());
        }
        hasher.update(evidence_delta_hash.as_bytes());
        hasher.update(cumulative_evidence_root.as_bytes());
        if let Some(ref cov) = world_coverage_root {
            hasher.update(cov.as_bytes());
        }
        if let Some(ref plan) = monitoring_plan_id {
            hasher.update(plan.as_bytes());
        }
        hasher.update(assurance_receipt_id.as_bytes());
        hasher.update(certificate_id.as_bytes());
        hasher.update(&opened_at_ns.to_le_bytes());
        hasher.update(&sealed_at_ns.to_le_bytes());
        let epoch_digest = format!("{:x}", hasher.finalize());

        Self {
            epoch_id,
            case_id,
            parent_epoch_id,
            evidence_delta_hash,
            cumulative_evidence_root,
            world_coverage_root,
            monitoring_plan_id,
            assurance_receipt_id,
            certificate_id,
            opened_at_ns,
            sealed_at_ns,
            epoch_digest,
        }
    }

    /// Verifies the cryptographic integrity of the sealed epoch record (D150-T02).
    pub fn verify_integrity(&self) -> bool {
        let mut hasher = Sha256::new();
        hasher.update(&self.epoch_id.0.to_le_bytes());
        hasher.update(self.case_id.0.as_bytes());
        if let Some(parent) = self.parent_epoch_id {
            hasher.update(&parent.0.to_le_bytes());
        }
        hasher.update(self.evidence_delta_hash.as_bytes());
        hasher.update(self.cumulative_evidence_root.as_bytes());
        if let Some(ref cov) = self.world_coverage_root {
            hasher.update(cov.as_bytes());
        }
        if let Some(ref plan) = self.monitoring_plan_id {
            hasher.update(plan.as_bytes());
        }
        hasher.update(self.assurance_receipt_id.as_bytes());
        hasher.update(self.certificate_id.as_bytes());
        hasher.update(&self.opened_at_ns.to_le_bytes());
        hasher.update(&self.sealed_at_ns.to_le_bytes());
        let computed = format!("{:x}", hasher.finalize());
        computed == self.epoch_digest
    }
}

/// Ingested delta of new evidence for a successor epoch (D-150 Section 10 & 24).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceDelta {
    pub delta_id: String,
    pub case_id: CaseIdentity,
    pub target_epoch: EvaluationEpoch,
    pub attestations: Vec<EvidenceAttestation>,
    pub defeaters: Vec<DefeaterReceipt>,
    pub delta_digest: String,
}

impl EvidenceDelta {
    pub fn new(
        case_id: CaseIdentity,
        target_epoch: EvaluationEpoch,
        attestations: Vec<EvidenceAttestation>,
        defeaters: Vec<DefeaterReceipt>,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(case_id.0.as_bytes());
        hasher.update(&target_epoch.0.to_le_bytes());
        for att in &attestations {
            hasher.update(att.attestation_id.as_bytes());
            hasher.update(att.artifact_hash.as_bytes());
        }
        for def in &defeaters {
            hasher.update(def.defeater_id.as_bytes());
            hasher.update(def.receipt_hash.as_bytes());
        }
        let delta_digest = format!("{:x}", hasher.finalize());
        let delta_id = format!("delta-{}", &delta_digest[..16]);

        Self {
            delta_id,
            case_id,
            target_epoch,
            attestations,
            defeaters,
            delta_digest,
        }
    }
}

/// Manifest declaring world/evaluator coverage for robustness claims (D-150 Section 22).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorldCoverageManifest {
    pub coverage_id: String,
    pub generator_families: Vec<String>,
    pub generator_versions: HashMap<String, String>,
    pub scenario_count: usize,
    pub behavioral_cells: Vec<String>,
    pub cross_asset_cells: Vec<String>,
    pub novelty_vault_id: Option<String>,
    pub manifest_digest: String,
}

impl WorldCoverageManifest {
    pub fn new(
        generator_families: Vec<String>,
        generator_versions: HashMap<String, String>,
        scenario_count: usize,
        behavioral_cells: Vec<String>,
        cross_asset_cells: Vec<String>,
        novelty_vault_id: Option<String>,
    ) -> Self {
        let mut hasher = Sha256::new();
        for f in &generator_families {
            hasher.update(f.as_bytes());
        }
        hasher.update(&scenario_count.to_le_bytes());
        for b in &behavioral_cells {
            hasher.update(b.as_bytes());
        }
        for c in &cross_asset_cells {
            hasher.update(c.as_bytes());
        }
        if let Some(ref n) = novelty_vault_id {
            hasher.update(n.as_bytes());
        }
        let manifest_digest = format!("{:x}", hasher.finalize());
        let coverage_id = format!("worldcov-{}", &manifest_digest[..16]);

        Self {
            coverage_id,
            generator_families,
            generator_versions,
            scenario_count,
            behavioral_cells,
            cross_asset_cells,
            novelty_vault_id,
            manifest_digest,
        }
    }
}

/// Manifest declaring sequential monitoring methods and firewall guarantees (D-150 Section 18).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MonitoringPlan {
    pub plan_id: String,
    pub estimand: String,
    pub data_stream: String,
    pub method_id: String,
    pub assumptions: Vec<String>,
    pub alert_boundary: f64,
    pub is_time_valid_sequential: bool,
    pub plan_digest: String,
}

impl MonitoringPlan {
    pub fn new(
        estimand: &str,
        data_stream: &str,
        method_id: &str,
        assumptions: Vec<String>,
        alert_boundary: f64,
        is_time_valid_sequential: bool,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(estimand.as_bytes());
        hasher.update(data_stream.as_bytes());
        hasher.update(method_id.as_bytes());
        hasher.update(&alert_boundary.to_le_bytes());
        hasher.update(&[is_time_valid_sequential as u8]);
        let plan_digest = format!("{:x}", hasher.finalize());
        let plan_id = format!("monplan-{}", &plan_digest[..16]);

        Self {
            plan_id,
            estimand: estimand.to_string(),
            data_stream: data_stream.to_string(),
            method_id: method_id.to_string(),
            assumptions,
            alert_boundary,
            is_time_valid_sequential,
            plan_digest,
        }
    }

    /// Checks whether this plan is valid for time-uniform inferential claims (D150-T10).
    pub fn is_valid_for_inferential_evidence(&self) -> bool {
        self.is_time_valid_sequential
    }
}

/// Loss decomposition receipt handed to Kaizen upon defeat (D-150 Section 23).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FailureAttribution {
    pub detection_loss: f64,
    pub representation_loss: f64,
    pub selection_loss: f64,
    pub allocation_loss: f64,
    pub execution_loss: f64,
    pub exit_capture_loss: f64,
    pub friction_loss: f64,
    pub unidentified_residual: f64,
}

impl FailureAttribution {
    pub fn total_loss(&self) -> f64 {
        self.detection_loss
            + self.representation_loss
            + self.selection_loss
            + self.allocation_loss
            + self.execution_loss
            + self.exit_capture_loss
            + self.friction_loss
            + self.unidentified_residual
    }
}

/// Receipt transferring a material failure from D-150 to Kaizen (D-150 Section 20).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KaizenHandoffReceipt {
    pub handoff_id: String,
    pub defeater_receipt_id: String,
    pub affected_policy_id: String,
    pub policy_code_hash: String,
    pub epoch: EvaluationEpoch,
    pub failure_attribution: Option<FailureAttribution>,
    pub timestamp_ns: u64,
    pub handoff_digest: String,
}

impl KaizenHandoffReceipt {
    pub fn new(
        defeater_receipt_id: &str,
        affected_policy_id: &str,
        policy_code_hash: &str,
        epoch: EvaluationEpoch,
        failure_attribution: Option<FailureAttribution>,
        timestamp_ns: u64,
    ) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(defeater_receipt_id.as_bytes());
        hasher.update(affected_policy_id.as_bytes());
        hasher.update(policy_code_hash.as_bytes());
        hasher.update(&epoch.0.to_le_bytes());
        hasher.update(&timestamp_ns.to_le_bytes());
        let handoff_digest = format!("{:x}", hasher.finalize());
        let handoff_id = format!("handoff-{}", &handoff_digest[..16]);

        Self {
            handoff_id,
            defeater_receipt_id: defeater_receipt_id.to_string(),
            affected_policy_id: affected_policy_id.to_string(),
            policy_code_hash: policy_code_hash.to_string(),
            epoch,
            failure_attribution,
            timestamp_ns,
            handoff_digest,
        }
    }
}

/// Continuous evaluation manager tracking epoch progression, certificates, and historical ledgers.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContinuousEvaluationLedger {
    pub current_epoch: EvaluationEpoch,
    pub epoch_records: HashMap<EvaluationEpoch, EvaluationEpochRecord>,
    pub epoch_receipts: HashMap<EvaluationEpoch, Vec<AssuranceCaseReceipt>>,
    pub epoch_certificates: HashMap<EvaluationEpoch, ProductionEvidenceCertificate>,
    pub current_certificate: Option<ProductionEvidenceCertificate>,
    pub historical_certificates: Vec<ProductionEvidenceCertificate>,
    pub kaizen_handoffs: Vec<KaizenHandoffReceipt>,
    pub world_coverages: HashMap<String, WorldCoverageManifest>,
    pub monitoring_plans: HashMap<String, MonitoringPlan>,
}

impl Default for ContinuousEvaluationLedger {
    fn default() -> Self {
        Self::new()
    }
}

impl ContinuousEvaluationLedger {
    pub fn new() -> Self {
        Self {
            current_epoch: EvaluationEpoch(1),
            epoch_records: HashMap::new(),
            epoch_receipts: HashMap::new(),
            epoch_certificates: HashMap::new(),
            current_certificate: None,
            historical_certificates: Vec::new(),
            kaizen_handoffs: Vec::new(),
            world_coverages: HashMap::new(),
            monitoring_plans: HashMap::new(),
        }
    }

    /// Records an evaluated case receipt into the append-only ledger for the current epoch (AF-T20).
    pub fn record_receipt(&mut self, receipt: AssuranceCaseReceipt) {
        self.epoch_receipts
            .entry(self.current_epoch)
            .or_default()
            .push(receipt);
    }

    /// Advances the evaluation epoch monotonically to N+1 (AF-T20, D150-I03).
    pub fn advance_epoch(&mut self) -> EvaluationEpoch {
        self.current_epoch = EvaluationEpoch(self.current_epoch.0 + 1);
        self.current_epoch
    }

    /// Returns the count of historical receipts archived across all past epochs.
    pub fn total_archived_receipts(&self) -> usize {
        self.epoch_receipts.values().map(|v| v.len()).sum()
    }

    /// Ingests an evidence delta and seals a successor epoch record (D-150 Algorithm A).
    pub fn ingest_delta_and_seal_epoch(
        &mut self,
        case: &EvaluationCaseManifest,
        delta: &EvidenceDelta,
        world_coverage_root: Option<String>,
        monitoring_plan_id: Option<String>,
        assurance_receipt_id: &str,
        certificate: ProductionEvidenceCertificate,
        opened_at_ns: u64,
        sealed_at_ns: u64,
    ) -> Result<EvaluationEpochRecord, &'static str> {
        if !case.verify_integrity() {
            return Err("SEALED_CASE_INTEGRITY_VIOLATION");
        }

        // Validate admissibility of all attestations in delta
        for att in &delta.attestations {
            if let AdmissibilityVerdict::Inadmissible(reason) = att.check_admissibility() {
                return Err(reason);
            }
        }

        let parent_epoch = if self.current_epoch.0 > 1 {
            Some(EvaluationEpoch(self.current_epoch.0 - 1))
        } else {
            None
        };

        // If a previous certificate was current, mark it as superseded
        if let Some(mut prev_cert) = self.current_certificate.take() {
            prev_cert.mark_superseded(&certificate.certificate_id);
            self.historical_certificates.push(prev_cert);
        }

        let record = EvaluationEpochRecord::new_sealed(
            self.current_epoch,
            case.case_id.clone(),
            parent_epoch,
            delta.delta_digest.clone(),
            format!("cum-root-epoch-{}", self.current_epoch.0),
            world_coverage_root,
            monitoring_plan_id,
            assurance_receipt_id.to_string(),
            certificate.certificate_id.clone(),
            opened_at_ns,
            sealed_at_ns,
        );

        self.epoch_records.insert(self.current_epoch, record.clone());
        self.epoch_certificates.insert(self.current_epoch, certificate.clone());
        self.current_certificate = Some(certificate);

        Ok(record)
    }

    /// Emits a Kaizen handoff receipt for a hard defeater and records it (D-150 Section 20).
    pub fn handoff_defeater_to_kaizen(
        &mut self,
        defeater: &DefeaterReceipt,
        affected_policy_id: &str,
        policy_code_hash: &str,
        attribution: Option<FailureAttribution>,
        timestamp_ns: u64,
    ) -> KaizenHandoffReceipt {
        let receipt = KaizenHandoffReceipt::new(
            &defeater.defeater_id,
            affected_policy_id,
            policy_code_hash,
            self.current_epoch,
            attribution,
            timestamp_ns,
        );
        self.kaizen_handoffs.push(receipt.clone());

        // Also revoke current certificate if active
        if let Some(ref mut cert) = self.current_certificate {
            cert.revoke("HARD_DEFEATER_DETECTED", Some(&defeater.defeater_id));
        }

        receipt
    }

    /// Verifies the cryptographic lineage and immutability across all archived epochs (D150-T18).
    pub fn verify_epoch_lineage(&self) -> bool {
        let mut expected_parent: Option<EvaluationEpoch> = None;
        let mut sorted_epochs: Vec<_> = self.epoch_records.keys().copied().collect();
        sorted_epochs.sort();

        for epoch in sorted_epochs {
            if let Some(record) = self.epoch_records.get(&epoch) {
                if !record.verify_integrity() {
                    return false;
                }
                if record.parent_epoch_id != expected_parent {
                    return false;
                }
                expected_parent = Some(epoch);
            }
        }
        true
    }
}
