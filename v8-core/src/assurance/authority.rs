//! Read-Only Authority Projection & Non-Escalating Adapters (D-147, D-149, M0_CLOSED, M1).
//!
//! Provides a strictly non-escalating projection over the statutory `crate::authority::Authority` tensor.
//! Invariant: AdmissibleClaims(AuthorityProjection) ⊆ AdmissibleClaims(SourceAuthority).
//! Adapters are total, non-escalating, and fail closed to `UNMAPPED` / `INADMISSIBLE` on unknown values.

use serde::{Deserialize, Serialize};
use crate::authority::{Authority, EvidenceAuthority, DecisionAuthority, RealizationStatus};
use crate::claims::StatutoryClaimClass;

/// Read-only projection over statutory authority.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct AuthorityProjection {
    pub evidence: EvidenceAuthority,
    pub decision: DecisionAuthority,
    pub realization: RealizationStatus,
}

impl AuthorityProjection {
    /// Creates a read-only projection from the source statutory authority tensor.
    pub fn from_source(source: &Authority) -> Self {
        Self {
            evidence: source.evidence,
            decision: source.decision,
            realization: source.realization,
        }
    }

    /// Asserts that a statutory claim class is admissible under this authority projection.
    pub fn validate_claim_admissibility(&self, claim: StatutoryClaimClass) -> Result<(), String> {
        let auth = Authority {
            evidence: self.evidence,
            decision: self.decision,
            realization: self.realization,
        };
        claim.validate_authority(&auth)
    }

    /// Asserts non-escalation: self cannot exceed source in any of the 3 tensor dimensions.
    pub fn is_non_escalating_wrt(&self, source: &Authority) -> bool {
        self.evidence <= source.evidence
            && self.decision <= source.decision
            && self.realization <= source.realization
    }
}
