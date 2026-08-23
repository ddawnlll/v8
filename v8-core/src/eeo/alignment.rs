#![allow(dead_code, unused_imports, unused_variables, unused_mut)]
//! Path Alignment & Interaction Analysis Engine (EEO-008, D-136-RP-001 §16, §17).
//!
//! Constitutional Invariants:
//! 1. Alignment Anchors: Opportunities aligned across baseline and challenger by `OpportunityId` and `EconomicTraceId`, NEVER by trade index.
//! 2. Path Expression Classification:
//!    - SAME_OPPORTUNITY_DIFFERENT_EXPRESSION
//!    - BASELINE_ONLY
//!    - CHALLENGER_ONLY
//!    - MISSED_GOOD
//!    - BAD_EXECUTED
//!    - GOOD_BUT_MISEXPRESSED
//! 3. Interaction Analysis: Single-intervention marginal effect and pairwise interaction without forced sum-to-one or Shapley axioms.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::error::V8CoreError;
use crate::telemetry::{DecisionBeliefLedger, EconomicTraceContext, EconomicTraceId, EconomicTraceLedger};

/// Alignment classification between baseline and challenger execution paths.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum AlignmentClass {
    SameOpportunityDifferentExpression,
    BaselineOnly,
    ChallengerOnly,
    MissedGood,
    BadExecuted,
    GoodButMisexpressed,
}

/// Aligned Opportunity Pair comparing baseline vs challenger trajectories.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AlignedOpportunityRecord {
    pub opportunity_id: String,
    pub baseline_trace_id: Option<EconomicTraceId>,
    pub challenger_trace_id: Option<EconomicTraceId>,
    pub alignment_class: AlignmentClass,
    pub baseline_net_r: Option<f64>,
    pub challenger_net_r: Option<f64>,
    pub delta_r: Option<f64>,
    pub delta_friction_bps: Option<f64>,
}

/// Pairwise interaction effect between two distinct interventions.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InteractionEffect {
    pub intervention_a: String,
    pub intervention_b: String,
    pub marginal_effect_a_r: f64,
    pub marginal_effect_b_r: f64,
    pub combined_effect_r: f64,
    pub interaction_delta_r: f64, // Combined - (A + B)
    pub is_synergistic: bool,
}

/// Path Alignment Engine.
pub struct PathAlignmentEngine;

impl PathAlignmentEngine {
    /// Aligns opportunities across baseline and challenger traces by `OpportunityId`.
    pub fn align_trajectories(
        opportunity_ids: &[String],
        baseline_ledger: &EconomicTraceLedger,
        challenger_ledger: &EconomicTraceLedger,
        baseline_beliefs: &DecisionBeliefLedger,
        challenger_beliefs: &DecisionBeliefLedger,
    ) -> Vec<AlignedOpportunityRecord> {
        let mut out = Vec::new();

        for opp_id in opportunity_ids {
            let base_beliefs = baseline_beliefs.receipts_for_opportunity(opp_id);
            let chall_beliefs = challenger_beliefs.receipts_for_opportunity(opp_id);

            let base_trace_id = base_beliefs.first().map(|b| b.trace_id.clone());
            let chall_trace_id = chall_beliefs.first().map(|b| b.trace_id.clone());

            let base_rejected = base_beliefs.iter().any(|b| b.is_rejection);
            let chall_rejected = chall_beliefs.iter().any(|b| b.is_rejection);

            let base_r = base_beliefs.iter().filter_map(|b| b.expected_net_utility_r).next_back();
            let chall_r = chall_beliefs.iter().filter_map(|b| b.expected_net_utility_r).next_back();

            let alignment_class = match (base_trace_id.is_some(), chall_trace_id.is_some()) {
                (true, true) => {
                    if base_rejected && !chall_rejected {
                        AlignmentClass::MissedGood // Challenger recovered what baseline missed
                    } else if !base_rejected && chall_rejected {
                        AlignmentClass::BadExecuted // Challenger avoided baseline bad execution
                    } else {
                        AlignmentClass::SameOpportunityDifferentExpression
                    }
                }
                (true, false) => AlignmentClass::BaselineOnly,
                (false, true) => AlignmentClass::ChallengerOnly,
                (false, false) => AlignmentClass::SameOpportunityDifferentExpression,
            };

            let delta_r = match (base_r, chall_r) {
                (Some(b), Some(c)) => Some(c - b),
                (None, Some(c)) => Some(c),
                (Some(b), None) => Some(-b),
                (None, None) => None,
            };

            out.push(AlignedOpportunityRecord {
                opportunity_id: opp_id.clone(),
                baseline_trace_id: base_trace_id,
                challenger_trace_id: chall_trace_id,
                alignment_class,
                baseline_net_r: base_r,
                challenger_net_r: chall_r,
                delta_r,
                delta_friction_bps: None,
            });
        }

        out
    }

    /// Evaluates pairwise interaction between two interventions.
    pub fn compute_interaction(
        intervention_a: &str,
        intervention_b: &str,
        marginal_a_r: f64,
        marginal_b_r: f64,
        combined_r: f64,
    ) -> InteractionEffect {
        let expected_additive = marginal_a_r + marginal_b_r;
        let interaction_delta_r = combined_r - expected_additive;
        let is_synergistic = interaction_delta_r > 0.0;

        InteractionEffect {
            intervention_a: intervention_a.to_string(),
            intervention_b: intervention_b.to_string(),
            marginal_effect_a_r: marginal_a_r,
            marginal_effect_b_r: marginal_b_r,
            combined_effect_r: combined_r,
            interaction_delta_r,
            is_synergistic,
        }
    }
}
