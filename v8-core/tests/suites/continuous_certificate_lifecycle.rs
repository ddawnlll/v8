//! Constitutional Sabotage Suite — Part 7: AF-T08, AF-T19, AF-T20 (D-147, D-149, Rule 44).

use v8_core::assurance::case::EvaluationEpoch;
use v8_core::assurance::certificate::{CertificateStatus, ProductionEvidenceCertificate};
use v8_core::assurance::continuous::ContinuousEvaluationLedger;
use v8_core::assurance::receipt::{AssuranceCaseReceipt, ClaimStatus};
use v8_core::assurance::case::CaseIdentity;
use std::collections::HashMap;

#[test]
fn test_af_t08_time_bounded_certificate_expires_after_horizon() {
    let issued_at_ns = 1700000000000000000u64;
    let duration_ns = 86400 * 7 * 1_000_000_000u64; // 7 days

    let cert = ProductionEvidenceCertificate::new(
        "policy-prod-v1",
        "hash-policy-prod-v1",
        EvaluationEpoch(1),
        issued_at_ns,
        duration_ns,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.0015, // LGNG > 0
        6.5,    // Max DD = 6.5% < 15%
        45.0,   // Opportunity Value Recall = 45%
    );

    // 1. Within validity window -> Qualified
    let status_active = cert.evaluate_status(issued_at_ns + 1000, false);
    assert_eq!(status_active, CertificateStatus::Qualified);

    // 2. Beyond validity horizon (e.g. 8 days later) -> Expired (AF-T08)
    let status_expired = cert.evaluate_status(issued_at_ns + duration_ns + 1000, false);
    assert_eq!(status_expired, CertificateStatus::Expired);
}

#[test]
fn test_af_t19_multi_dimensional_vector_forbids_scalar_collapse() {
    let issued_at_ns = 1700000000000000000u64;
    let duration_ns = 86400 * 7 * 1_000_000_000u64;

    // Certificate where economic profit and recall are high, BUT research status is Falsified
    let deficit_cert = ProductionEvidenceCertificate::new(
        "policy-deficit-v1",
        "hash-policy-deficit-v1",
        EvaluationEpoch(1),
        issued_at_ns,
        duration_ns,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Falsified, // Research integrity deficit!
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        ClaimStatus::Verified,
        0.0020,
        5.0,
        50.0,
    );

    // Invariant (AF-T19): A deficit in ANY statutory claim revokes qualification (no averaging out)
    let status = deficit_cert.evaluate_status(issued_at_ns + 1000, false);
    assert!(matches!(status, CertificateStatus::Revoked(_)));
}

#[test]
fn test_af_t20_epoch_advancement_preserves_append_only_history() {
    let mut ledger = ContinuousEvaluationLedger::new();
    assert_eq!(ledger.current_epoch, EvaluationEpoch(1));

    // Record receipt in Epoch 1
    let receipt1 = AssuranceCaseReceipt::new(
        CaseIdentity("case-epoch1-001".to_string()),
        EvaluationEpoch(1),
        "ASSURANCE_CASE_VERIFIED".to_string(),
        HashMap::new(),
        vec![],
        1700000000000000000,
    );
    ledger.record_receipt(receipt1);

    // Advance Epoch to Epoch 2
    let next_epoch = ledger.advance_epoch();
    assert_eq!(next_epoch, EvaluationEpoch(2));
    assert_eq!(ledger.current_epoch, EvaluationEpoch(2));

    // Record receipt in Epoch 2
    let receipt2 = AssuranceCaseReceipt::new(
        CaseIdentity("case-epoch2-001".to_string()),
        EvaluationEpoch(2),
        "ASSURANCE_CASE_VERIFIED".to_string(),
        HashMap::new(),
        vec![],
        1700000001000000000,
    );
    ledger.record_receipt(receipt2);

    // Invariant (AF-T20): Historical Epoch 1 receipts remain intact
    assert_eq!(ledger.total_archived_receipts(), 2);
    assert_eq!(ledger.epoch_receipts.get(&EvaluationEpoch(1)).map(|v| v.len()), Some(1));
    assert_eq!(ledger.epoch_receipts.get(&EvaluationEpoch(2)).map(|v| v.len()), Some(1));
}
