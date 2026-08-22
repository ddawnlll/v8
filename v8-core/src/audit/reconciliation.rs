//! Reconciliation Receipt & Clone Collapse Auditor (D-132, Rule 20/22).

use crate::opportunity::reconcile::{ReconciliationReceipt, ReconciledOpportunityState};

pub struct ReconciliationAuditor;

impl ReconciliationAuditor {
    /// Validates receipt cryptographic authenticity and clone collapse proof integrity.
    pub fn audit_receipt(
        state: &ReconciledOpportunityState,
        receipt: &ReconciliationReceipt,
    ) -> Result<(), String> {
        if state.receipt_id != receipt.receipt_id {
            return Err("RECEIPT_ID_MISMATCH".to_string());
        }

        if receipt.compute_id() != receipt.receipt_id {
            return Err("RECEIPT_PAYLOAD_TAMPERED".to_string());
        }

        if state.compute_id() != state.reconciled_id {
            return Err("STATE_IDENTITY_TAMPERED".to_string());
        }

        // Validate effective observer count matches collapse proofs
        let proof_effective_sum: f64 = receipt
            .collapse_proofs
            .iter()
            .map(|p| p.normalized_effective_weight)
            .sum();

        if (receipt.effective_observer_count - proof_effective_sum).abs() > 1e-6 {
            return Err(format!(
                "CLONE_COLLAPSE_INTEGRITY_FAILURE: EffectiveCount={}, ProofSum={}",
                receipt.effective_observer_count, proof_effective_sum
            ));
        }

        Ok(())
    }
}
