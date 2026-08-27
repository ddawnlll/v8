//! Statistical Plan & Lifetime Trial Debt Accounting (D-147, D-149, M4).
//!
//! Tracks research family multiplicity: M_total = discarded_variants + retained_variants.
//! Invariant: All historical model searches and discarded attempts must increment trial debt.

use serde::{Deserialize, Serialize};

/// Pre-committed Statistical Verification Plan for a policy family.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StatisticalPlan {
    pub family_id: String,
    pub policy_lineage: String,
    pub discarded_variants_count: usize,
    pub retained_variants_count: usize,
    pub total_trial_debt: usize,
    pub alpha_budget_target: f64,
    pub adjusted_alpha_threshold: f64,
}

impl StatisticalPlan {
    pub fn new(family_id: String, lineage: String, alpha_budget: f64) -> Self {
        Self {
            family_id,
            policy_lineage: lineage,
            discarded_variants_count: 0,
            retained_variants_count: 1,
            total_trial_debt: 1,
            alpha_budget_target: alpha_budget,
            adjusted_alpha_threshold: alpha_budget,
        }
    }

    /// Records a discarded exploratory model variant, incrementing lifetime trial debt.
    pub fn record_discarded_variant(&mut self) {
        self.discarded_variants_count += 1;
        self.total_trial_debt = self.discarded_variants_count + self.retained_variants_count;
        // Bonferroni / Sidak trial multiplicity adjustment
        self.adjusted_alpha_threshold = self.alpha_budget_target / (self.total_trial_debt as f64);
    }
}
