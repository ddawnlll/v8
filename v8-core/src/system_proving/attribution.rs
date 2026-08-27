//! Failure-Domain Attribution Algebra (D-147, D-149, M3).
//!
//! Classifies every trade/campaign failure into exactly one of 7 disjoint pipeline domains.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// The 7 Disjoint Pipeline Failure Domains.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum FailureDomain {
    Detection,
    Representation,
    Reconciliation,
    Selection,
    Allocation,
    Execution,
    Exit,
}

impl FailureDomain {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Detection => "DETECTION",
            Self::Representation => "REPRESENTATION",
            Self::Reconciliation => "RECONCILIATION",
            Self::Selection => "SELECTION",
            Self::Allocation => "ALLOCATION",
            Self::Execution => "EXECUTION",
            Self::Exit => "EXIT",
        }
    }
}

/// Attribution breakdown summary.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct FailureAttributionBreakdown {
    pub counts_by_domain: HashMap<FailureDomain, usize>,
    pub total_failures: usize,
}

impl FailureAttributionBreakdown {
    pub fn record_failure(&mut self, domain: FailureDomain) {
        *self.counts_by_domain.entry(domain).or_insert(0) += 1;
        self.total_failures += 1;
    }

    /// Invariant: Sum of domain counts must equal total failures exactly.
    pub fn verify_conservation(&self) -> bool {
        let sum: usize = self.counts_by_domain.values().sum();
        sum == self.total_failures
    }
}
