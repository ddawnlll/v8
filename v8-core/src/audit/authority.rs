//! Authority Audit & Receipt Chain Validator (D-132, Rule 28).

use crate::authority::{Authority, ClaimValue, ConstitutionalViolation, DecisionAuthority};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthorityAuditReport {
    pub passed: bool,
    pub receipts_checked: usize,
    pub violations: Vec<String>,
}

pub struct AuthorityAuditor;

impl AuthorityAuditor {
    /// Validates that an output authority does not exceed the minimum of parent authorities.
    pub fn audit_monotonicity(
        output_auth: &Authority,
        input_auths: &[Authority],
    ) -> Result<(), ConstitutionalViolation> {
        if input_auths.is_empty() {
            return Ok(());
        }

        let mut min_auth = input_auths[0];
        for auth in &input_auths[1..] {
            min_auth = min_auth.meet(auth);
        }

        if (output_auth.evidence as u8) > (min_auth.evidence as u8) {
            return Err(ConstitutionalViolation::AuthorityEscalationAttempted {
                attempted_evidence: output_auth.evidence,
                source_evidence: min_auth.evidence,
            });
        }
        if (output_auth.decision as u8) > (min_auth.decision as u8) {
            return Err(ConstitutionalViolation::ClaimBlocked {
                required_authority: format!("{:?}", min_auth.decision),
                provided_authority: format!("{:?}", output_auth.decision),
                reason: "DECISION_AUTHORITY_ESCALATION".to_string(),
            });
        }
        if (output_auth.realization as u8) > (min_auth.realization as u8) {
            return Err(ConstitutionalViolation::ClaimBlocked {
                required_authority: format!("{:?}", min_auth.realization),
                provided_authority: format!("{:?}", output_auth.realization),
                reason: "REALIZATION_STATUS_ESCALATION".to_string(),
            });
        }

        Ok(())
    }

    /// Audits a collection of claim values to verify receipt presence and authority contracts.
    pub fn audit_claims<T>(claims: &[ClaimValue<T>]) -> AuthorityAuditReport {
        let mut violations = Vec::new();
        for (i, c) in claims.iter().enumerate() {
            if c.receipt_id.is_empty() {
                violations.push(format!("Claim at index {i} has empty receipt_id"));
            }
            if c.authority.decision >= DecisionAuthority::PortfolioAuthorized && c.receipt_id.len() < 16 {
                violations.push(format!("Claim at index {i} has invalid cryptographic receipt"));
            }
        }

        AuthorityAuditReport {
            passed: violations.is_empty(),
            receipts_checked: claims.len(),
            violations,
        }
    }
}
