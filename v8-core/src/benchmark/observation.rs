//! MetricObservation and Benchmark Observation Registry (D-153 §32, §64–75).
//!
//! Provides granular observations across benchmark capability domains, binding
//! raw values, calibrated scores, epistemic authority, data roles, and statistical bounds.

use serde::{Deserialize, Serialize};
use crate::assurance::evidence_profile::DataRole;
use crate::benchmark::types::CapabilityDomain;

/// Canonical single observation recorded in a benchmark evaluation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MetricObservation {
    pub metric_id: String,
    pub domain: CapabilityDomain,
    pub authority: String,
    pub population_role: DataRole,
    pub raw_value: f64,
    pub normalized_score: f64,
    pub lower_bound_95: f64,
    pub upper_bound_95: f64,
    pub sample_size: usize,
    pub effective_sample_size: f64,
    pub passed_floor: bool,
    pub notes: String,
}

impl MetricObservation {
    pub fn new(
        metric_id: impl Into<String>,
        domain: CapabilityDomain,
        authority: impl Into<String>,
        population_role: DataRole,
        raw_value: f64,
        normalized_score: f64,
        lower_bound_95: f64,
        upper_bound_95: f64,
        sample_size: usize,
        effective_sample_size: f64,
        passed_floor: bool,
    ) -> Self {
        Self {
            metric_id: metric_id.into(),
            domain,
            authority: authority.into(),
            population_role,
            raw_value,
            normalized_score: normalized_score.clamp(0.0, 1.0),
            lower_bound_95: lower_bound_95.clamp(0.0, 1.0),
            upper_bound_95: upper_bound_95.clamp(0.0, 1.0),
            sample_size,
            effective_sample_size,
            passed_floor,
            notes: String::new(),
        }
    }
}
