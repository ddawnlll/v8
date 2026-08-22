//! V8.3 Opportunity-Sovereign End-to-End Runloop & Ledger Engine (Issue #231, #239, D-130).
//!
//! Owning Authority: V8 Constitution Rules 1, 6, 13, 15, 16, 20, 24, 25, 26.
//!
//! Execution Sequence (Seven Constitutional Primitives):
//!   1. MarketState (FeatureStore / StateView)
//!   2. EconomicExposureStructure (ExposureResolver)
//!   3. OpportunityEpisode (OpportunityGrammar -> OpportunityBook)
//!   4. ObserverEvidence (ExpertWitness ensemble)
//!   5. ReconciledOpportunityState (EvidenceReconciler)
//!   6. ExecutionCampaign (SelectiveUtility -> PortfolioFeasibility)
//!   7. Order / Fill / Position / Outcome (USDMSim Execution Engine)

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::experts::base::{FeatMap, ProjectedFeatures};
use crate::experts::witness_adapter::{default_28_witness_ensemble, ExpertWitness, LegacyExpertWitnessAdapter};
use crate::state::FeatureStore;
use super::book::OpportunityBook;
use super::campaign::{ExecutionCampaign, PortfolioFeasibilityConfig, PortfolioFeasibilityEngine, CampaignIntent};
use super::exposure::ExposureResolver;
use super::grammar::OpportunityGrammar;
use super::reconcile::{EvidenceReconciler, ReconciledOpportunityState, ReconciledStance};
use super::utility::{FrictionModel, SelectiveUtility, SelectiveUtilityDecision, UtilityAction};
use std::collections::HashMap;

/// Summary ledger of one complete V8.3 opportunity cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityCycleLedger {
    pub as_of_time: i64,
    pub symbol: String,
    pub venue: String,
    pub episodes_generated: usize,
    pub evidence_count: usize,
    pub reconciled_states: Vec<ReconciledOpportunityState>,
    pub utility_decisions: Vec<SelectiveUtilityDecision>,
    pub campaigns_launched: Vec<ExecutionCampaign>,
}

/// The V8.3 Opportunity Runloop orchestrator.
pub struct V83Runloop {
    pub grammar: OpportunityGrammar,
    pub resolver: ExposureResolver,
    pub witnesses: Vec<LegacyExpertWitnessAdapter>,
    pub friction: FrictionModel,
    pub portfolio_config: PortfolioFeasibilityConfig,
}

impl Default for V83Runloop {
    fn default() -> Self {
        Self {
            grammar: OpportunityGrammar::default(),
            resolver: ExposureResolver::new(),
            witnesses: default_28_witness_ensemble(),
            friction: FrictionModel::default(),
            portfolio_config: PortfolioFeasibilityConfig::default(),
        }
    }
}

impl V83Runloop {
    pub fn new() -> Self {
        Self::default()
    }

    /// Executes one bar tick across the 7 opportunity primitives.
    pub fn step_bar(
        &self,
        symbol: &str,
        venue: &str,
        store: &FeatureStore,
        bar_idx: usize,
        book: &mut OpportunityBook,
        current_committed_notional: f64,
    ) -> Result<OpportunityCycleLedger, V8CoreError> {
        let as_of = store.avail[bar_idx];

        // 1 & 2 & 3: MarketState -> Exposure -> OpportunityGrammar -> OpportunityBook
        let detected_episodes = self.grammar.scan_market_state(symbol, venue, store, bar_idx, &self.resolver)?;
        let mut episode_count = 0usize;
        for ep in &detected_episodes {
            book.insert(ep.clone())?;
            episode_count += 1;
        }

        let t = bar_idx + 1;
        let feats = if t >= 32 {
            crate::state::state_features(store, t, as_of, 32)
        } else {
            Vec::new()
        };
        let hist = if t >= 32 {
            crate::state::history_bars(store, t, 32)
        } else {
            Vec::new()
        };
        let empty_variants = HashMap::new();

        let mut total_evidence_count = 0usize;
        let mut reconciled_states = Vec::new();
        let mut utility_decisions = Vec::new();
        let mut campaigns_launched = Vec::new();
        let mut committed = current_committed_notional;

        // 4: Epistemic Witness Observation
        for ep in &detected_episodes {
            let mut evidences = Vec::with_capacity(self.witnesses.len());
            for witness in &self.witnesses {
                let closure = crate::features::group_closure(crate::experts::requires_for(&witness.expert_id));
                let allows_hist = crate::features::history_allowed(&closure);
                let expert_hist = if allows_hist { hist.clone() } else { Vec::new() };
                let fm = FeatMap {
                    features: ProjectedFeatures::new(&feats, &closure),
                    history: expert_hist,
                    as_of,
                    symbol,
                    variant_overrides: &empty_variants,
                };
                if let Ok(ev) = witness.observe(ep, &fm) {
                    evidences.push(ev);
                }
            }
            total_evidence_count += evidences.len();

            // 5: Dependence-Aware Evidence Reconciliation
            let reconciled = EvidenceReconciler::reconcile(ep, &evidences)?;
            
            // 6: Selective Utility
            let gross_edge_bps = (reconciled.support_weight * 50.0).max(self.friction.total_friction_bps() * 2.0);
            let decision = SelectiveUtility::evaluate(ep, &reconciled, &self.friction, gross_edge_bps)?;
            
            // 7: Portfolio Feasibility & ExecutionCampaign
            if decision.action == UtilityAction::Trade && reconciled.aggregate_stance == ReconciledStance::Supported {
                let intent = CampaignIntent::new(
                    &ep.episode_id,
                    &decision.decision_id,
                    ep.exposure.clone(),
                    1.0,
                    200.0,
                    as_of,
                )?;

                if let Ok(camp) = PortfolioFeasibilityEngine::evaluate_intent(
                    &self.portfolio_config,
                    &intent,
                    committed,
                    as_of,
                ) {
                    committed += camp.allocated_capital_usdt;
                    campaigns_launched.push(camp);
                }
            }

            reconciled_states.push(reconciled);
            utility_decisions.push(decision);
        }

        Ok(OpportunityCycleLedger {
            as_of_time: as_of,
            symbol: symbol.to_string(),
            venue: venue.to_string(),
            episodes_generated: episode_count,
            evidence_count: total_evidence_count,
            reconciled_states,
            utility_decisions,
            campaigns_launched,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::TapeRow;

    fn build_test_store() -> FeatureStore {
        let n = 50;
        let hour_ns = 3_600_000_000_000i64;
        let mut rows = Vec::with_capacity(n);
        for i in 0..n {
            let t = (i as i64 + 1) * hour_ns;
            let c = if i == 35 { 130.0 } else { 100.0 };
            rows.push(TapeRow {
                source: "binance-um".into(),
                channel: "kline".into(),
                instrument: "BTCUSDT".into(),
                event_time: t,
                available_time: t + 1,
                ingested_time: t + 2,
                venue_sequence: (i + 1) as i64,
                event_id: format!("bar_{i}"),
                payload: serde_json::json!({
                    "open": c - 0.5,
                    "high": c + 1.0,
                    "low": c - 1.0,
                    "close": c,
                    "volume": 1000.0,
                    "closed": true,
                }),
                nonfinite: vec![],
            });
        }
        let ds = crate::data::Dataset::from_rows(rows).unwrap();
        crate::state::build_stores(&ds).into_iter().next().unwrap()
    }

    #[test]
    fn test_v83_runloop_end_to_end_pipeline() {
        let store = build_test_store();
        let loop_engine = V83Runloop::default();
        let mut book = OpportunityBook::new();

        let ledger = loop_engine
            .step_bar("BTCUSDT", "binance-um", &store, 35, &mut book, 0.0)
            .unwrap();

        assert_eq!(ledger.symbol, "BTCUSDT");
        assert!(ledger.episodes_generated > 0);
        assert_eq!(ledger.evidence_count, ledger.episodes_generated * loop_engine.witnesses.len());
        assert_eq!(ledger.reconciled_states.len(), ledger.episodes_generated);
        assert_eq!(ledger.utility_decisions.len(), ledger.episodes_generated);
    }
}
