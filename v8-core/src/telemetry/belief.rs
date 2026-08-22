//! Canonical Decision Belief Ledger & Epistemic Receipts (EEO-002, D-136, D-136-RP-001 §7).
//!
//! Owning Authority: V8 Constitution Rules 1, 3, 4, 18, 20, 21, 24, 28, 35; D-136.
//!
//! Constitutional Invariants:
//! 1. No Fabricated Beliefs (Anti-Hallucination): Record only ex-ante signals V8 actually computes Point-In-Time.
//!    Unavailable dimensions remain explicitly `None` or `Unavailable`, never synthetic defaults.
//! 2. Append-Only Immutability: Once a `BeliefReceipt` is recorded, future price paths, Oracles, Audits,
//!    or later execution outcomes CANNOT mutate it.
//! 3. PIT & Hindsight Firewall: `BeliefReceipt` can ONLY be constructed from Point-In-Time `DecisionStage`s.
//!    Evidence plane stages (`TargetOracleHindsight`, `AuditAdjudication`, `ProviderEvaluation`) are
//!    strictly prohibited from creating or populating ex-ante belief receipts.
//! 4. Full Funnel Coverage: Opportunities rejected at witness, reconciliation, utility, or portfolio
//!    stages MUST leave a final immutable ex-ante `BeliefReceipt` so downstream Oracle Gap analysis
//!    is not biased toward executed trades.
//! 5. Identity-Lineage Decoupling: `BeliefReceiptId` != `EconomicTraceId` != `OpportunityId` != `SpanId` != `TraceProvenance`.

#![allow(dead_code)]

use std::collections::HashMap;
use std::fmt;
use std::ops::Deref;
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;
use crate::opportunity::book::OpportunityEpisode;
use crate::opportunity::campaign::{CampaignIntent, ExecutionCampaign};
use crate::opportunity::evidence::ObserverEvidence;
use crate::opportunity::reconcile::{ReconciledOpportunityState, ReconciledStance};
use crate::opportunity::utility::{SelectiveUtilityDecision, UtilityAction};
use super::identity::{EconomicTraceContext, EconomicTraceId, SpanId, TraceProvenance};
use super::span::DecisionStage;

/// Checkpoint in the PIT economic pipeline where an ex-ante belief receipt is captured.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum BeliefStage {
    /// Initial opportunity episode detection.
    OpportunityDetected,
    /// Post-witness ensemble observation.
    PostWitnessObservation,
    /// Post-dependence reconciliation.
    PostReconciliation,
    /// Post-selective utility net hurdle evaluation.
    PostSelectiveUtility,
    /// Pre-execution portfolio feasibility check.
    PortfolioFeasibilityEvaluated,
    /// Execution campaign authorized & dispatched.
    CampaignDispatched,
}

impl BeliefStage {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::OpportunityDetected => "OpportunityDetected",
            Self::PostWitnessObservation => "PostWitnessObservation",
            Self::PostReconciliation => "PostReconciliation",
            Self::PostSelectiveUtility => "PostSelectiveUtility",
            Self::PortfolioFeasibilityEvaluated => "PortfolioFeasibilityEvaluated",
            Self::CampaignDispatched => "CampaignDispatched",
        }
    }

    /// Maps a PIT DecisionStage to the corresponding BeliefStage.
    /// Strictly rejects post-outcome evidence stages.
    pub fn from_decision_stage(stage: DecisionStage) -> Self {
        match stage {
            DecisionStage::MarketState | DecisionStage::OpportunityDetection => Self::OpportunityDetected,
            DecisionStage::WitnessObservation => Self::PostWitnessObservation,
            DecisionStage::EvidenceReconciliation => Self::PostReconciliation,
            DecisionStage::SelectiveUtility => Self::PostSelectiveUtility,
            DecisionStage::PortfolioFeasibility => Self::PortfolioFeasibilityEvaluated,
            DecisionStage::CampaignAdmission | DecisionStage::OrderDispatch | DecisionStage::ExecutionFill => Self::CampaignDispatched,
            DecisionStage::PositionManagement | DecisionStage::CashflowSettlement => Self::CampaignDispatched,
        }
    }
}

/// Canonical ex-ante action chosen at this decision checkpoint.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ChosenAction {
    /// Episode acknowledged / queued.
    OpportunityIdentified,
    /// Witness stances collected.
    WitnessEvaluated {
        participating_witnesses: usize,
        supporting_witnesses: usize,
        contradicting_witnesses: usize,
        abstaining_witnesses: usize,
    },
    /// Reconciled aggregate verdict.
    Reconciled {
        stance: ReconciledStance,
        effective_observer_count: f64,
        support_weight: f64,
        contradict_weight: f64,
        contradiction_entropy: f64,
    },
    /// Selective utility evaluation result.
    SelectiveUtilityDecision {
        action: UtilityAction,
        expected_net_utility_r: f64,
        rejection_reason: Option<String>,
    },
    /// Portfolio feasibility admission or capacity reject.
    PortfolioDecision {
        admitted: bool,
        allocated_capital_usdt: f64,
        target_risk_r: f64,
        rejection_reason: Option<String>,
    },
}

/// Canonical ex-ante cost expectation calculated prior to order dispatch.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExAnteCostExpectation {
    pub total_friction_bps: f64,
    pub entry_fee_bps: f64,
    pub exit_fee_bps: f64,
    pub bid_ask_spread_bps: f64,
    pub funding_rate_est: f64,
    pub slippage_bps: f64,
    pub uncertainty_buffer_bps: f64,
}

/// Canonical ex-ante uncertainty metrics calculated Point-In-Time.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExAnteUncertainty {
    pub contradiction_entropy: f64,
    pub uncertainty_penalty_r: Option<f64>,
    pub effective_observer_count: f64,
}

/// Canonical Belief Receipt Identifier (BLAKE3-derived hex).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct BeliefReceiptId(pub String);

impl BeliefReceiptId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn compute(
        trace_id: &EconomicTraceId,
        opportunity_id: &str,
        span_id: &SpanId,
        stage: BeliefStage,
        pit_timestamp: i64,
        provenance_hash: &str,
    ) -> Self {
        let mut c = Canon::new();
        c.push_str("BeliefReceiptId");
        c.push_str(trace_id.as_str());
        c.push_str(opportunity_id);
        c.push_str(span_id.as_str());
        c.push_str(stage.as_str());
        c.push_i64(pit_timestamp);
        c.push_str(provenance_hash);
        Self(c.finish_blake3_hex())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for BeliefReceiptId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Deref for BeliefReceiptId {
    type Target = str;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl AsRef<str> for BeliefReceiptId {
    fn as_ref(&self) -> &str {
        &self.0
    }
}

/// Point-In-Time Snapshot of V8's ex-ante epistemic state (EEO-002, D-136-RP-001 §7).
/// Contains only signals canonically computed prior to outcome realization.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BeliefReceipt {
    pub receipt_id: BeliefReceiptId,
    pub trace_id: EconomicTraceId,
    pub opportunity_id: String,
    pub span_id: SpanId,
    pub stage: BeliefStage,
    pub pit_timestamp: i64,
    pub provenance: TraceProvenance,

    // Ex-ante epistemic values actually computed by V8
    pub expected_gross_edge_bps: Option<f64>,
    pub expected_net_utility_r: Option<f64>,
    pub expected_horizon_bars: usize,
    pub cost_expectation: Option<ExAnteCostExpectation>,
    pub uncertainty: Option<ExAnteUncertainty>,
    pub chosen_action: ChosenAction,
    pub is_rejection: bool,
    pub rejection_reason: Option<String>,

    // Explicitly unmodeled / unavailable dimensions (Anti-Hallucination Invariant)
    // V8 does not currently compute arbitrary continuous outcome probability distributions
    // or expected MFE/MAE ex ante; these remain explicit None rather than invented numbers.
    pub outcome_probabilities: Option<Vec<f64>>,
    pub expected_mfe_r: Option<f64>,
    pub expected_mae_r: Option<f64>,
}

impl BeliefReceipt {
    /// Constructs and fingerprints an immutable `BeliefReceipt`.
    pub fn new(
        trace_id: EconomicTraceId,
        opportunity_id: impl Into<String>,
        span_id: SpanId,
        stage: BeliefStage,
        pit_timestamp: i64,
        provenance: TraceProvenance,
        expected_gross_edge_bps: Option<f64>,
        expected_net_utility_r: Option<f64>,
        expected_horizon_bars: usize,
        cost_expectation: Option<ExAnteCostExpectation>,
        uncertainty: Option<ExAnteUncertainty>,
        chosen_action: ChosenAction,
        is_rejection: bool,
        rejection_reason: Option<String>,
    ) -> Result<Self, V8CoreError> {
        let opportunity_id = opportunity_id.into();
        if opportunity_id.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "opportunity_id cannot be empty in BeliefReceipt".to_string(),
            ));
        }

        let prov_hash = provenance.compute_hash();
        let receipt_id = BeliefReceiptId::compute(
            &trace_id,
            &opportunity_id,
            &span_id,
            stage,
            pit_timestamp,
            &prov_hash,
        );

        Ok(Self {
            receipt_id,
            trace_id,
            opportunity_id,
            span_id,
            stage,
            pit_timestamp,
            provenance,
            expected_gross_edge_bps,
            expected_net_utility_r,
            expected_horizon_bars,
            cost_expectation,
            uncertainty,
            chosen_action,
            is_rejection,
            rejection_reason,
            outcome_probabilities: None,
            expected_mfe_r: None,
            expected_mae_r: None,
        })
    }

    /// Snapshot from initial Opportunity Episode.
    pub fn from_opportunity(
        ctx: &EconomicTraceContext,
        span_id: &SpanId,
        episode: &OpportunityEpisode,
    ) -> Result<Self, V8CoreError> {
        Self::new(
            ctx.trace_id.clone(),
            &episode.episode_id,
            span_id.clone(),
            BeliefStage::OpportunityDetected,
            episode.as_of_time,
            ctx.provenance.clone(),
            None,
            None,
            episode.expected_horizon_bars,
            None,
            None,
            ChosenAction::OpportunityIdentified,
            false,
            None,
        )
    }

    /// Snapshot after witness ensemble observation.
    pub fn from_witnesses(
        ctx: &EconomicTraceContext,
        span_id: &SpanId,
        episode: &OpportunityEpisode,
        witness_evidences: &[ObserverEvidence],
    ) -> Result<Self, V8CoreError> {
        let mut supp = 0;
        let mut cont = 0;
        let mut abst = 0;
        for ev in witness_evidences {
            match &ev.stance {
                crate::opportunity::evidence::ObserverStance::Support { .. } => supp += 1,
                crate::opportunity::evidence::ObserverStance::Contradict { .. } => cont += 1,
                crate::opportunity::evidence::ObserverStance::Abstain { .. } => abst += 1,
                crate::opportunity::evidence::ObserverStance::Unknown { .. } => abst += 1,
            }
        }

        Self::new(
            ctx.trace_id.clone(),
            &episode.episode_id,
            span_id.clone(),
            BeliefStage::PostWitnessObservation,
            episode.as_of_time,
            ctx.provenance.clone(),
            None,
            None,
            episode.expected_horizon_bars,
            None,
            None,
            ChosenAction::WitnessEvaluated {
                participating_witnesses: witness_evidences.len(),
                supporting_witnesses: supp,
                contradicting_witnesses: cont,
                abstaining_witnesses: abst,
            },
            false,
            None,
        )
    }

    /// Snapshot after dependence-aware evidence reconciliation.
    pub fn from_reconciliation(
        ctx: &EconomicTraceContext,
        span_id: &SpanId,
        episode: &OpportunityEpisode,
        reconciled: &ReconciledOpportunityState,
    ) -> Result<Self, V8CoreError> {
        let is_rejected = reconciled.aggregate_stance != ReconciledStance::Supported;
        let rejection_reason = if is_rejected {
            Some(format!("ReconciledStance::{:?}", reconciled.aggregate_stance))
        } else {
            None
        };

        Self::new(
            ctx.trace_id.clone(),
            &episode.episode_id,
            span_id.clone(),
            BeliefStage::PostReconciliation,
            reconciled.reconciliation_time,
            ctx.provenance.clone(),
            None,
            None,
            episode.expected_horizon_bars,
            None,
            Some(ExAnteUncertainty {
                contradiction_entropy: reconciled.contradiction_entropy,
                uncertainty_penalty_r: None, // Explicitly unavailable at reconciliation stage; utility stage computes penalty
                effective_observer_count: reconciled.effective_observer_count,
            }),
            ChosenAction::Reconciled {
                stance: reconciled.aggregate_stance,
                effective_observer_count: reconciled.effective_observer_count,
                support_weight: reconciled.support_weight,
                contradict_weight: reconciled.contradict_weight,
                contradiction_entropy: reconciled.contradiction_entropy,
            },
            is_rejected,
            rejection_reason,
        )
    }

    /// Snapshot after selective utility evaluation.
    pub fn from_utility(
        ctx: &EconomicTraceContext,
        span_id: &SpanId,
        episode: &OpportunityEpisode,
        reconciled: &ReconciledOpportunityState,
        decision: &SelectiveUtilityDecision,
        friction: &crate::opportunity::utility::FrictionModel,
    ) -> Result<Self, V8CoreError> {
        let is_rejected = !decision.is_executable();
        let rejection_reason = if is_rejected {
            decision.rejection_reason.clone().or_else(|| Some(format!("UtilityAction::{:?}", decision.action)))
        } else {
            None
        };

        Self::new(
            ctx.trace_id.clone(),
            &episode.episode_id,
            span_id.clone(),
            BeliefStage::PostSelectiveUtility,
            reconciled.reconciliation_time,
            ctx.provenance.clone(),
            Some(decision.expected_gross_edge),
            Some(decision.expected_net_utility),
            episode.expected_horizon_bars,
            Some(ExAnteCostExpectation {
                total_friction_bps: friction.total_friction_bps(),
                entry_fee_bps: friction.entry_fee_bps,
                exit_fee_bps: friction.exit_fee_bps,
                bid_ask_spread_bps: friction.bid_ask_spread_bps,
                funding_rate_est: friction.funding_rate_est,
                slippage_bps: friction.slippage_bps,
                uncertainty_buffer_bps: friction.uncertainty_buffer_bps,
            }),
            Some(ExAnteUncertainty {
                contradiction_entropy: reconciled.contradiction_entropy,
                uncertainty_penalty_r: Some(decision.uncertainty_penalty),
                effective_observer_count: reconciled.effective_observer_count,
            }),
            ChosenAction::SelectiveUtilityDecision {
                action: decision.action,
                expected_net_utility_r: decision.expected_net_utility,
                rejection_reason: decision.rejection_reason.clone(),
            },
            is_rejected,
            rejection_reason,
        )
    }

    /// Snapshot after portfolio feasibility evaluation (admitted or capacity-vetoed).
    pub fn from_portfolio_feasibility(
        ctx: &EconomicTraceContext,
        span_id: &SpanId,
        intent: &CampaignIntent,
        campaign_res: &Result<ExecutionCampaign, V8CoreError>,
        expected_horizon_bars: usize,
    ) -> Result<Self, V8CoreError> {
        let (admitted, allocated, target_r, reason) = match campaign_res {
            Ok(c) => (true, c.allocated_capital_usdt, c.target_risk_r, None),
            Err(e) => (false, 0.0, 0.0, Some(e.to_string())),
        };

        Self::new(
            ctx.trace_id.clone(),
            &intent.opportunity_id,
            span_id.clone(),
            BeliefStage::PortfolioFeasibilityEvaluated,
            intent.created_time,
            ctx.provenance.clone(),
            None,
            None,
            expected_horizon_bars,
            None,
            None,
            ChosenAction::PortfolioDecision {
                admitted,
                allocated_capital_usdt: allocated,
                target_risk_r: target_r,
                rejection_reason: reason.clone(),
            },
            !admitted,
            reason,
        )
    }
}

/// Append-Only Decision Belief Ledger (EEO-002, D-136-RP-001 §7).
/// Stores and indexes ex-ante epistemic snapshots across the canonical decision trajectory.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DecisionBeliefLedger {
    receipts: Vec<BeliefReceipt>,
    receipts_by_id: HashMap<BeliefReceiptId, usize>,
    by_trace: HashMap<EconomicTraceId, Vec<usize>>,
    by_opportunity: HashMap<String, Vec<usize>>,
}

impl DecisionBeliefLedger {
    pub fn new() -> Self {
        Self::default()
    }

    /// Appends a new immutable `BeliefReceipt`.
    pub fn append(&mut self, receipt: BeliefReceipt) -> Result<(), V8CoreError> {
        let rid = receipt.receipt_id.clone();
        if self.receipts_by_id.contains_key(&rid) {
            // Idempotent identical check
            let idx = self.receipts_by_id[&rid];
            if self.receipts[idx] != receipt {
                return Err(V8CoreError::TraceLineageError(format!(
                    "Conflicting BeliefReceipt mutation attempt for receipt_id {}",
                    rid
                )));
            }
            return Ok(());
        }

        let idx = self.receipts.len();
        self.by_trace
            .entry(receipt.trace_id.clone())
            .or_default()
            .push(idx);
        self.by_opportunity
            .entry(receipt.opportunity_id.clone())
            .or_default()
            .push(idx);
        self.receipts_by_id.insert(rid, idx);
        self.receipts.push(receipt);
        Ok(())
    }

    pub fn get(&self, receipt_id: &BeliefReceiptId) -> Option<&BeliefReceipt> {
        let idx = *self.receipts_by_id.get(receipt_id)?;
        self.receipts.get(idx)
    }

    pub fn receipts_for_trace(&self, trace_id: &EconomicTraceId) -> Vec<&BeliefReceipt> {
        self.by_trace
            .get(trace_id)
            .map(|indices| indices.iter().filter_map(|&idx| self.receipts.get(idx)).collect())
            .unwrap_or_default()
    }

    pub fn receipts_for_opportunity(&self, opportunity_id: &str) -> Vec<&BeliefReceipt> {
        self.by_opportunity
            .get(opportunity_id)
            .map(|indices| indices.iter().filter_map(|&idx| self.receipts.get(idx)).collect())
            .unwrap_or_default()
    }

    pub fn final_belief_for_opportunity(&self, opportunity_id: &str) -> Option<&BeliefReceipt> {
        let indices = self.by_opportunity.get(opportunity_id)?;
        let last_idx = *indices.last()?;
        self.receipts.get(last_idx)
    }

    pub fn len(&self) -> usize {
        self.receipts.len()
    }

    pub fn is_empty(&self) -> bool {
        self.receipts.is_empty()
    }

    pub fn all(&self) -> &[BeliefReceipt] {
        &self.receipts
    }

    /// Validates full epistemic and temporal integrity of the belief ledger.
    pub fn validate_lineage(&self) -> Result<(), V8CoreError> {
        for receipt in &self.receipts {
            if receipt.opportunity_id.is_empty() {
                return Err(V8CoreError::TraceLineageError(format!(
                    "BeliefReceipt {} has empty opportunity_id",
                    receipt.receipt_id
                )));
            }
            if receipt.provenance.tape_hash.is_empty()
                || receipt.provenance.policy_hash.is_empty()
                || receipt.provenance.constitution_hash.is_empty()
                || receipt.provenance.code_hash.is_empty()
            {
                return Err(V8CoreError::TraceLineageError(format!(
                    "BeliefReceipt {} has corrupted provenance hashes",
                    receipt.receipt_id
                )));
            }
        }
        Ok(())
    }

    pub fn to_json(&self) -> Result<String, V8CoreError> {
        serde_json::to_string_pretty(self).map_err(|e| V8CoreError::Serialization(e.to_string()))
    }

    pub fn from_json(json_str: &str) -> Result<Self, V8CoreError> {
        serde_json::from_str(json_str).map_err(|e| V8CoreError::Serialization(e.to_string()))
    }
}
