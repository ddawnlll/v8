//! Veto Proofs, No-Naked-Veto Gate & Expedited Appeal Engine (D-134, Rule 39, Amendment A2).

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

/// Type of evidence backing a commissioner or red-team veto.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum VetoEvidenceType {
    /// Reproducible, panic-inducing unit test failure in Rust (`cargo test`).
    PanicUnitTestFailure {
        test_name: String,
        panic_message: String,
    },
    /// Cryptographic receipt violation (e.g. hash mismatch, Merkle root corruption).
    ReceiptIntegrityViolation {
        receipt_id: String,
        expected_digest: String,
        actual_digest: String,
    },
    /// Scope violation against active `ExecutionMandate`.
    MandateScopeViolation {
        attempted_path: String,
        authorized_scopes: Vec<String>,
    },
    /// Direct violation of the 6 statutory claim classes or economic firewall.
    EconomicClaimViolation {
        claim_type: String,
        illegal_terms: Vec<String>,
    },
}

/// Cryptographically verifiable proof required for ANY execution veto (Amendment A2).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VetoProof {
    pub veto_id: String,
    pub issuing_commissioner: String,
    pub evidence: VetoEvidenceType,
    pub failure_reproduction_cmd: String,
    pub timestamp_utc: i64,
}

/// Outcome of processing a veto through the Judicial Veto Gate.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum VetoDecision {
    /// Veto accepted with valid executable proof -> Halts execution.
    VetoAffirmed {
        proof_digest: String,
        remediation_mandate_id: String,
    },
    /// Veto rejected: No executable test proof or empty justification -> Execution continues.
    VetoRejectedNakedVeto {
        reason: String,
    },
    /// Veto rejected: Veto issuer attempted production mutation instead of pure oversight.
    VetoRejectedAuditorOverreach {
        violation: String,
    },
}

/// Judicial Veto Gate enforcing `No Naked Veto` (Rule 39).
pub struct JudicialVetoGate;

impl JudicialVetoGate {
    /// Evaluates a commissioner's veto. Fails if naked (no verifiable evidence).
    pub fn process_veto(
        issuer_is_oversight_only: bool,
        proof: Option<&VetoProof>,
    ) -> VetoDecision {
        if !issuer_is_oversight_only {
            return VetoDecision::VetoRejectedAuditorOverreach {
                violation: "VETO_DENIED: Issuer holds write/merge/production permissions. Veto is restricted to oversight.".into(),
            };
        }

        match proof {
            None => VetoDecision::VetoRejectedNakedVeto {
                reason: "NO_NAKED_VETO: Abstract textual objections without reproducible test proofs are unconstitutional.".into(),
            },
            Some(p) => {
                // Verify that evidence is non-empty and well-formed
                match &p.evidence {
                    VetoEvidenceType::PanicUnitTestFailure { test_name, panic_message }
                        if test_name.is_empty() || panic_message.is_empty() => {
                            return VetoDecision::VetoRejectedNakedVeto {
                                reason: "NO_NAKED_VETO: Unit test failure proof must contain valid test name and panic payload.".into(),
                            };
                        }
                    VetoEvidenceType::ReceiptIntegrityViolation { receipt_id, expected_digest, actual_digest }
                        if receipt_id.is_empty() || expected_digest == actual_digest => {
                            return VetoDecision::VetoRejectedNakedVeto {
                                reason: "NO_NAKED_VETO: Receipt violation proof requires disparate expected and actual digests.".into(),
                            };
                        }
                    _ => {}
                }

                VetoDecision::VetoAffirmed {
                    proof_digest: p.veto_id.clone(),
                    remediation_mandate_id: format!("REMEDY-{}", p.veto_id),
                }
            }
        }
    }
}

/// Outcome of an expedited 1-turn appeal against an affirmed veto.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AppealVerdict {
    /// Appeal Upheld: The veto was falsified or proven out-of-scope; execution resumes.
    VetoOverturned {
        falsification_proof_digest: String,
    },
    /// Appeal Denied: The veto stands; implementer must remediate.
    VetoSustained {
        binding_remediation_reason: String,
    },
}

/// 1-Turn Expedited Appeal Engine for implementers (Amendment A2).
pub struct ExpeditedAppealEngine;

impl ExpeditedAppealEngine {
    /// Evaluates an implementer's appeal against a sustained veto.
    pub fn adjudicate_appeal(
        original_veto: &VetoProof,
        counter_proof_green_test: bool,
        counter_proof_digest: &str,
    ) -> AppealVerdict {
        if counter_proof_green_test && !counter_proof_digest.is_empty() {
            AppealVerdict::VetoOverturned {
                falsification_proof_digest: counter_proof_digest.to_string(),
            }
        } else {
            AppealVerdict::VetoSustained {
                binding_remediation_reason: format!(
                    "Appeal denied for veto '{}': Implementer failed to demonstrate green test execution.",
                    original_veto.veto_id
                ),
            }
        }
    }
}
