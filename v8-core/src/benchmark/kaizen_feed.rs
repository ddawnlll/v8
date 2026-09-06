//! Kaizen Benchmark Feedback & Research Debt Accounting (D-153 Section 95-102).
//!
//! Provides:
//! - BenchmarkDelta: comparison between incumbent and challenger across domains
//! - ResearchDebtTracker: tracks trial penalties when hypotheses consume populations
//! - Zero-Leakage Interface: Kaizen loop consumes diagnostic deltas without gaining
//!   direct access to protected evaluation data.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::benchmark::receipt::BenchmarkReceipt;
use crate::benchmark::types::CapabilityDomain;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DomainDelta {
    pub domain: CapabilityDomain,
    pub incumbent_score: f64,
    pub challenger_score: f64,
    pub delta: f64,
    pub statistically_significant: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkDelta {
    pub incumbent_policy_id: String,
    pub challenger_policy_id: String,
    pub domain_deltas: HashMap<CapabilityDomain, DomainDelta>,
    pub composite_delta: f64,
    pub challenger_is_pareto_superior: bool,
    pub research_trials_consumed: usize,
    pub accrued_research_debt_penalty: f64,
}

impl BenchmarkDelta {
    pub fn compute_delta(
        incumbent: &BenchmarkReceipt,
        challenger: &BenchmarkReceipt,
        trials_count: usize,
    ) -> Self {
        let mut deltas = HashMap::new();
        let mut pareto_superior = true;

        for d in &CapabilityDomain::ALL {
            let inc_score = incumbent.domain_results.get(d).map(|r| r.calibrated_score).unwrap_or(0.0);
            let chal_score = challenger.domain_results.get(d).map(|r| r.calibrated_score).unwrap_or(0.0);
            let delta = chal_score - inc_score;

            if delta < -0.01 {
                // Challenger degraded in this domain
                pareto_superior = false;
            }

            deltas.insert(*d, DomainDelta {
                domain: *d,
                incumbent_score: inc_score,
                challenger_score: chal_score,
                delta,
                statistically_significant: delta.abs() > 0.05,
            });
        }

        // Multiple testing adjustment (accrued research debt penalty)
        let debt_penalty = (trials_count as f64).ln().max(0.0) * 0.02;
        let comp_delta = challenger.composite_capability_score - incumbent.composite_capability_score - debt_penalty;

        Self {
            incumbent_policy_id: incumbent.policy_id.clone(),
            challenger_policy_id: challenger.policy_id.clone(),
            domain_deltas: deltas,
            composite_delta: comp_delta,
            challenger_is_pareto_superior: pareto_superior && comp_delta > 0.0,
            research_trials_consumed: trials_count,
            accrued_research_debt_penalty: debt_penalty,
        }
    }
}
