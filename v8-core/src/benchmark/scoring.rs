//! CapabilityScore Mathematics and Aggregation (D-153 Section 74-80).
//!
//! Enforces:
//! - Weighted harmonic mean / robust penalty aggregation
//! - Uncertainty penalty (penalizing small sample size / high variance)
//! - Hard Invariant Gating: if any hard invariant in G0-G9 fails, the composite
//!   score is capped / zeroed, or marked failed.
//! - Non-compensatory: massive outperformance in one domain cannot compensate
//!   for failure in another.

use std::collections::HashMap;
use crate::benchmark::types::{CapabilityDomain, BoundedScore};

#[derive(Debug, Clone, PartialEq)]
pub struct CapabilityScorer {
    pub domain_weights: HashMap<CapabilityDomain, f64>,
}

impl Default for CapabilityScorer {
    fn default() -> Self {
        let mut weights = HashMap::new();
        // Equal weighting by default across 10 capability domains
        for d in &CapabilityDomain::ALL {
            weights.insert(*d, 0.10);
        }
        Self { domain_weights: weights }
    }
}

impl CapabilityScorer {
    pub fn new(weights: HashMap<CapabilityDomain, f64>) -> Self {
        Self { domain_weights: weights }
    }

    /// Calculate aggregate capability score across evaluated domains.
    ///
    /// Uses penalized harmonic mean to strictly prevent averaging away weak performance.
    /// If `hard_invariant_failed` is true for any domain, composite score is capped at 0.0.
    pub fn calculate_aggregate(
        &self,
        domain_scores: &HashMap<CapabilityDomain, BoundedScore>,
        hard_invariants_passed: bool,
    ) -> f64 {
        if !hard_invariants_passed || domain_scores.is_empty() {
            return 0.0;
        }

        let mut weighted_inverse_sum = 0.0;
        let mut total_weight = 0.0;

        for (domain, score) in domain_scores {
            let w = *self.domain_weights.get(domain).unwrap_or(&0.10);
            total_weight += w;

            // Apply sample uncertainty penalty: use lower 95% bound
            let effective_val = score.lower_bound_95.max(0.001); // Prevent div-by-zero
            weighted_inverse_sum += w / effective_val;
        }

        if total_weight <= 0.0 || weighted_inverse_sum <= 0.0 {
            return 0.0;
        }

        // Harmonic mean
        let harmonic_mean = total_weight / weighted_inverse_sum;
        harmonic_mean.clamp(0.0, 1.0)
    }
}
