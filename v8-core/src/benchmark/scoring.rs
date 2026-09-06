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
pub struct CapabilityScoreCalculator {
    pub domain_weights: HashMap<CapabilityDomain, f64>,
}

impl Default for CapabilityScoreCalculator {
    fn default() -> Self {
        let mut weights = HashMap::new();
        // Equal weighting by default across 10 capability domains
        for d in &CapabilityDomain::ALL {
            weights.insert(*d, 0.10);
        }
        Self { domain_weights: weights }
    }
}

impl CapabilityScoreCalculator {
    pub fn new(weights: HashMap<CapabilityDomain, f64>) -> Self {
        Self { domain_weights: weights }
    }

    /// Monograph V1 provisional domain weights (D-153 §76, Monograph line 1283)
    pub fn monograph_v1() -> Self {
        let mut weights = HashMap::new();
        weights.insert(CapabilityDomain::MicrostructureInvariance, 0.12); // Discovery & Selection
        weights.insert(CapabilityDomain::OperationalSimplicity, 0.15);     // Economic Quality
        weights.insert(CapabilityDomain::ExecutionFidelity, 0.10);         // Execution & Friction
        weights.insert(CapabilityDomain::CrossAssetGeneralization, 0.20);  // Generalization
        weights.insert(CapabilityDomain::RepresentationStability, 0.08);  // Reliability / Stability
        weights.insert(CapabilityDomain::StatisticalCredibility, 0.07);    // Statistical Credibility
        weights.insert(CapabilityDomain::EvaluationSafety, 0.05);          // Research Integrity
        weights.insert(CapabilityDomain::DefeaterResistance, 0.08);        // Engineering & Data Integrity
        weights.insert(CapabilityDomain::RegimeRobustness, 0.10);          // Risk / Regime Survival
        weights.insert(CapabilityDomain::CapacityScalability, 0.05);       // Capacity Scalability
        Self { domain_weights: weights }
    }

    /// Linear metric margin for higher-is-better metric (D-153 §74)
    pub fn metric_margin_higher_better(val: f64, lower_bound: f64, upper_bound: f64) -> f64 {
        if upper_bound <= lower_bound {
            return 0.0;
        }
        ((val - lower_bound) / (upper_bound - lower_bound)).clamp(0.0, 1.0)
    }

    /// Linear metric margin for lower-is-better metric (e.g. drawdown, slippage)
    pub fn metric_margin_lower_better(val: f64, lower_bound: f64, upper_bound: f64) -> f64 {
        if upper_bound <= lower_bound {
            return 0.0;
        }
        ((upper_bound - val) / (upper_bound - lower_bound)).clamp(0.0, 1.0)
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
        self.calculate_aggregate_with_coverage(domain_scores, 1.0, hard_invariants_passed)
    }

    /// Calculate aggregate capability score with coverage penalty multiplier (D-153 §76).
    pub fn calculate_aggregate_with_coverage(
        &self,
        domain_scores: &HashMap<CapabilityDomain, BoundedScore>,
        coverage_factor: f64,
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

        // Harmonic mean multiplied by coverage factor
        let harmonic_mean = total_weight / weighted_inverse_sum;
        let clamped_coverage = coverage_factor.clamp(0.10, 1.0);
        (harmonic_mean * clamped_coverage).clamp(0.0, 1.0)
    }
}
