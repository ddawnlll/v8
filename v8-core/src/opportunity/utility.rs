//! Selective Utility & Cost-Aware Trade / No-Trade / Defer Decisions (Issue #231, #237, D-130).
//!
//! Owning Authority: V8 Constitution Rules 21, 24.
//!
//! Net Value Invariant:
//!   E[Delta PnL_net] = GrossEdge - Friction - UncertaintyPenalty > 0
//!   Sub-friction setups default strictly to NO_TRADE.

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;
use super::book::OpportunityEpisode;
use super::reconcile::{ReconciledOpportunityState, ReconciledStance};

/// Selective utility action.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum UtilityAction {
    Trade,
    NoTrade,
    Defer,
}

/// Cost and friction parameters for utility evaluation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FrictionModel {
    pub entry_fee_bps: f64,
    pub exit_fee_bps: f64,
    pub bid_ask_spread_bps: f64,
    pub funding_rate_est: f64,
    pub slippage_bps: f64,
    pub uncertainty_buffer_bps: f64,
}

impl Default for FrictionModel {
    fn default() -> Self {
        Self {
            entry_fee_bps: 5.0,        // 0.05% taker fee
            exit_fee_bps: 5.0,         // 0.05% taker fee
            bid_ask_spread_bps: 2.0,   // 0.02% spread
            funding_rate_est: 1.0,     // 0.01% per interval
            slippage_bps: 2.0,         // 0.02% slippage markout
            uncertainty_buffer_bps: 5.0, // 0.05% safety hurdle
        }
    }
}

impl FrictionModel {
    /// Total expected friction in basis points.
    pub fn total_friction_bps(&self) -> f64 {
        self.entry_fee_bps + self.exit_fee_bps + self.bid_ask_spread_bps + self.funding_rate_est + self.slippage_bps
    }

    /// Total hurdle in basis points (friction + uncertainty buffer).
    pub fn total_hurdle_bps(&self) -> f64 {
        self.total_friction_bps() + self.uncertainty_buffer_bps
    }
}

/// Selective Utility Decision (Derived Decision Artifact).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SelectiveUtilityDecision {
    pub decision_id: String,
    pub opportunity_id: String,
    pub action: UtilityAction,
    pub expected_gross_edge: f64,
    pub estimated_friction: f64,
    pub uncertainty_penalty: f64,
    pub expected_net_utility: f64,
    pub rejection_reason: Option<String>,
}

impl SelectiveUtilityDecision {
    /// Computes cryptographic BLAKE3 identity for SelectiveUtilityDecision.
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("SelectiveUtilityDecision");
        c.push_str(&self.opportunity_id);
        c.push_str(&format!("{:?}", self.action));
        c.push_f64(self.expected_gross_edge);
        c.push_f64(self.estimated_friction);
        c.push_f64(self.uncertainty_penalty);
        c.push_f64(self.expected_net_utility);
        if let Some(r) = &self.rejection_reason {
            c.push_str(r);
        } else {
            c.push_null();
        }
        c.finish_blake3_hex()
    }

    pub fn is_executable(&self) -> bool {
        self.action == UtilityAction::Trade && self.expected_net_utility > 0.0
    }
}

/// Selective Utility Decision Engine.
pub struct SelectiveUtility;

impl SelectiveUtility {
    /// Evaluates whether an opportunity qualifies for execution after all costs and penalties.
    pub fn evaluate(
        episode: &OpportunityEpisode,
        reconciled: &ReconciledOpportunityState,
        friction: &FrictionModel,
        baseline_gross_edge_bps: f64,
    ) -> Result<SelectiveUtilityDecision, V8CoreError> {
        if reconciled.opportunity_id != episode.episode_id {
            return Err(V8CoreError::SelectiveUtilityError(format!(
                "Reconciled state opportunity_id ({}) does not match episode ({})",
                reconciled.opportunity_id, episode.episode_id
            )));
        }

        // Check aggregate stance
        if reconciled.aggregate_stance != ReconciledStance::Supported {
            let reason = format!("Opportunity stance is {:?}", reconciled.aggregate_stance);
            let mut dec = SelectiveUtilityDecision {
                decision_id: String::new(),
                opportunity_id: episode.episode_id.clone(),
                action: UtilityAction::NoTrade,
                expected_gross_edge: 0.0,
                estimated_friction: friction.total_friction_bps(),
                uncertainty_penalty: friction.uncertainty_buffer_bps,
                expected_net_utility: -friction.total_hurdle_bps(),
                rejection_reason: Some(reason),
            };
            dec.decision_id = dec.compute_id();
            return Ok(dec);
        }

        // Expected gross edge scaled by net confidence
        let expected_gross_edge = baseline_gross_edge_bps * reconciled.net_confidence.max(0.0);
        let estimated_friction = friction.total_friction_bps();
        let uncertainty_penalty = friction.uncertainty_buffer_bps * (1.0 + reconciled.contradiction_entropy);
        let expected_net_utility = expected_gross_edge - estimated_friction - uncertainty_penalty;

        let (action, rejection_reason) = if expected_net_utility > 0.0 {
            (UtilityAction::Trade, None)
        } else if expected_gross_edge > estimated_friction {
            (
                UtilityAction::Defer,
                Some(format!(
                    "Net edge below uncertainty hurdle: net_utility={:.2}bps",
                    expected_net_utility
                )),
            )
        } else {
            (
                UtilityAction::NoTrade,
                Some(format!(
                    "Sub-friction negative expectation: gross={:.2}bps < friction={:.2}bps",
                    expected_gross_edge, estimated_friction
                )),
            )
        };

        let mut decision = SelectiveUtilityDecision {
            decision_id: String::new(),
            opportunity_id: episode.episode_id.clone(),
            action,
            expected_gross_edge,
            estimated_friction,
            uncertainty_penalty,
            expected_net_utility,
            rejection_reason,
        };
        decision.decision_id = decision.compute_id();
        Ok(decision)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::opportunity::book::IdentityStatus;
    use crate::opportunity::exposure::{EconomicExposureStructure, ExposureDirection};

    fn make_test_data(stance: ReconciledStance, net_confidence: f64) -> (OpportunityEpisode, ReconciledOpportunityState) {
        let exp = EconomicExposureStructure::single_perp(
            "BTCUSDT",
            "BTC",
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        let ep = OpportunityEpisode::new(
            exp,
            1_000_000,
            2_000_000,
            24,
            IdentityStatus::Canonical,
            "state_hash",
            "lineage",
        )
        .unwrap();

        let mut reconciled = ReconciledOpportunityState {
            reconciled_id: String::new(),
            opportunity_id: ep.episode_id.clone(),
            aggregate_stance: stance,
            effective_observer_count: 3.0,
            support_weight: 2.5,
            contradict_weight: 0.0,
            abstention_weight: 0.5,
            contradiction_entropy: 0.0,
            net_confidence,
            reconciliation_time: 1_000_000,
            participating_evidence_ids: vec!["ev1".to_string()],
        };
        reconciled.reconciled_id = reconciled.compute_id();
        (ep, reconciled)
    }

    #[test]
    fn test_sub_friction_opportunity_defaults_to_no_trade() {
        let (ep, reconciled) = make_test_data(ReconciledStance::Supported, 0.5);
        let friction = FrictionModel::default(); // total hurdle ~ 20bps

        // Gross edge 10bps < friction 15bps
        let dec = SelectiveUtility::evaluate(&ep, &reconciled, &friction, 20.0).unwrap();
        assert_eq!(dec.action, UtilityAction::NoTrade);
        assert!(!dec.is_executable());
    }

    #[test]
    fn test_marginal_edge_above_friction_below_uncertainty_defers() {
        let (ep, reconciled) = make_test_data(ReconciledStance::Supported, 0.8);
        let friction = FrictionModel::default();

        // 0.8 * 22bps = 17.6bps > friction (15bps) but < hurdle (20bps)
        let dec = SelectiveUtility::evaluate(&ep, &reconciled, &friction, 22.0).unwrap();
        assert_eq!(dec.action, UtilityAction::Defer);
        assert!(!dec.is_executable());
    }

    #[test]
    fn test_robust_edge_above_all_hurdles_qualifies_for_trade() {
        let (ep, reconciled) = make_test_data(ReconciledStance::Supported, 0.9);
        let friction = FrictionModel::default();

        // 0.9 * 60bps = 54bps >> hurdle (20bps)
        let dec = SelectiveUtility::evaluate(&ep, &reconciled, &friction, 60.0).unwrap();
        assert_eq!(dec.action, UtilityAction::Trade);
        assert!(dec.is_executable());
        assert!(dec.expected_net_utility > 30.0);
    }

    #[test]
    fn test_unsupported_or_contradicted_stance_defaults_to_no_trade() {
        let (ep, reconciled) = make_test_data(ReconciledStance::Inconclusive, 0.9);
        let friction = FrictionModel::default();

        let dec = SelectiveUtility::evaluate(&ep, &reconciled, &friction, 100.0).unwrap();
        assert_eq!(dec.action, UtilityAction::NoTrade);
        assert!(!dec.is_executable());
    }
}
