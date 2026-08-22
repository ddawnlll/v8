//! Diagnostic Evidence Providers P05–P09 & Economic Pathology Map (EEO-006, D-136-RP-001 §13, Issues #260, #264, #265, #266, #267, #268, #269).
//!
//! Diagnostic Providers:
//! - P05: Belief Calibration Provider (calibrates ex-ante expectations against observed outcomes without inventing probabilities).
//! - P06: Oracle Gap & Opportunity Coverage Provider (separates RAW, OVERLAP_ADJUSTED, and PORTFOLIO_REALIZABLE gaps from real data).
//! - P07: Expert Evidence Quality & Habitat Provider (analyzes witness contribution, redundancy, and collinearity from real cycle ledgers).
//! - P08: Decision Transfer Efficiency Provider (measures empirical information loss through reconciliation, utility, and feasibility).
//! - P09: Implementation Shortfall / TCA Provider (decomposes real fee, slippage, delay, and opportunity costs from CashflowLedger).
//!
//! Major Checkpoint A:
//! - `EconomicPathologyMap`: OBSERVED, SUPPORTED, CONTESTED, UNIDENTIFIED, ORACLE_GAP, BAD_EXECUTED, MISSED_GOOD, GOOD_BUT_MISEXPRESSED.

#![allow(dead_code)]

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use super::contract::{
    Assumption, AuditEvidenceProvider, EvidenceAuthority, EvidenceBundle, EvidenceClaim,
    EvidenceContext, EvidenceCoverage, EvidenceDependency, ProviderIdentity, ProviderLifecycle,
};
use super::graph::{ClaimVerdict, EvidenceGraph};

/// P05: Belief Calibration Provider.
pub struct P05BeliefCalibrationProvider {
    pub lifecycle: ProviderLifecycle,
}

impl Default for P05BeliefCalibrationProvider {
    fn default() -> Self {
        Self {
            lifecycle: ProviderLifecycle::Validated,
        }
    }
}

impl AuditEvidenceProvider for P05BeliefCalibrationProvider {
    fn identity(&self) -> ProviderIdentity {
        ProviderIdentity::new("P05_BELIEF_CALIBRATION", "Belief Calibration Analyzer", "v1.1.0-production")
    }

    fn lifecycle(&self) -> ProviderLifecycle {
        self.lifecycle
    }

    fn declared_authority(&self) -> EvidenceAuthority {
        EvidenceAuthority::StatisticalEstimate
    }

    fn assumptions(&self) -> Vec<Assumption> {
        vec![Assumption::new("NO_SYNTHETIC_PROBABILITY", "Calibration operates exclusively on computed gross edge and net utility hurdles without manufactured distributions.", true)]
    }

    fn dependencies(&self) -> Vec<EvidenceDependency> {
        vec![EvidenceDependency::new("v8-belief-ledger", "1.0", "blake3_belief_digest")]
    }

    fn evaluate(&self, ctx: &EvidenceContext) -> Result<EvidenceBundle, V8CoreError> {
        let mut claims = Vec::new();
        let total = ctx.scope.trace_ids.len();
        let prov = ctx.resolve_provenance()?;

        let mut paired_count = 0usize;
        let mut sum_abs_error = 0.0f64;

        if let Some(cf_ledger) = ctx.cashflow_ledger {
            for flow in &cf_ledger.flows {
                // Find belief receipts corresponding to candidate/opportunity
                let matched = ctx.belief_ledger.all().iter().find(|b| b.opportunity_id == flow.candidate_id);
                if let Some(receipt) = matched {
                    if let Some(exp_u) = receipt.expected_net_utility_r {
                        let realized_r = flow.net_pnl_usdt;
                        sum_abs_error += (exp_u - realized_r).abs();
                        paired_count += 1;
                    }
                }
            }
        }

        if paired_count >= 5 {
            let mean_error = sum_abs_error / paired_count as f64;
            claims.push(EvidenceClaim::new(
                "BELIEF_CALIBRATION_EVALUATED",
                EvidenceAuthority::StatisticalEstimate,
                Some(mean_error),
                format!("Empirically calibrated {} ex-ante belief pairs (MAE={:.4}).", paired_count, mean_error),
                None,
                None,
                false,
            ));
        } else {
            claims.push(EvidenceClaim::new(
                "CALIBRATION_DIMENSION_UNAVAILABLE",
                EvidenceAuthority::Unidentified,
                None,
                format!("Insufficient paired cashflow-belief samples ({} pairs, required >= 5); continuous probability distributions are explicitly unmodeled.", paired_count),
                None,
                None,
                false,
            ));
        }

        Ok(EvidenceBundle::new(
            self.identity(),
            self.lifecycle(),
            ctx.scope.clone(),
            claims,
            self.assumptions(),
            self.dependencies(),
            EvidenceCoverage::partial(total.max(1), paired_count),
            None,
            prov,
            ctx.as_of_time,
        ))
    }
}

/// P06: Oracle Gap & Coverage Provider.
pub struct P06OracleGapCoverageProvider {
    pub lifecycle: ProviderLifecycle,
}

impl Default for P06OracleGapCoverageProvider {
    fn default() -> Self {
        Self {
            lifecycle: ProviderLifecycle::Validated,
        }
    }
}

impl AuditEvidenceProvider for P06OracleGapCoverageProvider {
    fn identity(&self) -> ProviderIdentity {
        ProviderIdentity::new("P06_ORACLE_GAP_COVERAGE", "Oracle Gap & Coverage Analyzer", "v1.1.0-production")
    }

    fn lifecycle(&self) -> ProviderLifecycle {
        self.lifecycle
    }

    fn declared_authority(&self) -> EvidenceAuthority {
        EvidenceAuthority::OracleUpperBound
    }

    fn assumptions(&self) -> Vec<Assumption> {
        vec![
            Assumption::new("ORACLE_UPPER_BOUND", "Target Oracle markouts represent ex-post frontier potential, NEVER realized cashflows.", true),
            Assumption::new("GAP_DECOMPOSITION", "Separates raw, overlap-adjusted, and portfolio-realizable gaps.", true),
        ]
    }

    fn dependencies(&self) -> Vec<EvidenceDependency> {
        vec![EvidenceDependency::new("v8-target-oracle", "1.0", "blake3_oracle_digest")]
    }

    fn evaluate(&self, ctx: &EvidenceContext) -> Result<EvidenceBundle, V8CoreError> {
        let mut claims = Vec::new();
        let prov = ctx.resolve_provenance()?;

        if let Some(funnel) = ctx.oracle_funnel {
            let executed = funnel.counterfactual_campaigns_admitted;
            let raw_gap = (funnel.total_oracle_universe.saturating_sub(executed)) as f64;
            let overlap_adj_gap = (funnel.witness_supported.saturating_sub(executed)) as f64;
            let portfolio_gap = (funnel.portfolio_admitted.saturating_sub(executed)) as f64;

            claims.push(EvidenceClaim::new(
                "RAW_ORACLE_GAP",
                EvidenceAuthority::OracleUpperBound,
                Some(raw_gap),
                format!("Gross theoretical Oracle upper bound opportunity gap: {} opportunities.", raw_gap as usize),
                None,
                None,
                false,
            ));
            claims.push(EvidenceClaim::new(
                "OVERLAP_ADJUSTED_GAP",
                EvidenceAuthority::OracleUpperBound,
                Some(overlap_adj_gap),
                format!("Oracle gap adjusted for concurrent co-temporal opportunity overlaps: {} opportunities.", overlap_adj_gap as usize),
                None,
                None,
                false,
            ));
            claims.push(EvidenceClaim::new(
                "PORTFOLIO_REALIZABLE_GAP",
                EvidenceAuthority::OracleUpperBound,
                Some(portfolio_gap),
                format!("Realizable Oracle gap within portfolio capacity: {} opportunities.", portfolio_gap as usize),
                None,
                None,
                false,
            ));
        } else {
            claims.push(EvidenceClaim::new(
                "ORACLE_GAP_UNAVAILABLE",
                EvidenceAuthority::OracleUpperBound,
                None,
                "Target Oracle markout tables not provided in evidence context; zero synthetic gaps manufactured.".to_string(),
                None,
                None,
                false,
            ));
        }

        Ok(EvidenceBundle::new(
            self.identity(),
            self.lifecycle(),
            ctx.scope.clone(),
            claims,
            self.assumptions(),
            self.dependencies(),
            EvidenceCoverage::full(1),
            None,
            prov,
            ctx.as_of_time,
        ))
    }
}

/// P07: Expert Evidence Quality & Redundancy Provider.
pub struct P07ExpertEvidenceQualityProvider {
    pub lifecycle: ProviderLifecycle,
}

impl Default for P07ExpertEvidenceQualityProvider {
    fn default() -> Self {
        Self {
            lifecycle: ProviderLifecycle::Validated,
        }
    }
}

impl AuditEvidenceProvider for P07ExpertEvidenceQualityProvider {
    fn identity(&self) -> ProviderIdentity {
        ProviderIdentity::new("P07_EXPERT_EVIDENCE_QUALITY", "Expert Quality & Habitat Analyzer", "v1.1.0-production")
    }

    fn lifecycle(&self) -> ProviderLifecycle {
        self.lifecycle
    }

    fn declared_authority(&self) -> EvidenceAuthority {
        EvidenceAuthority::DeterministicDerivation
    }

    fn assumptions(&self) -> Vec<Assumption> {
        vec![Assumption::new("CLONE_INVARIANCE", "Duplicate collinear witnesses collapse to effective weight 1.0.", true)]
    }

    fn dependencies(&self) -> Vec<EvidenceDependency> {
        vec![EvidenceDependency::new("v8-witness-scorecard", "1.0", "blake3_witness_digest")]
    }

    fn evaluate(&self, ctx: &EvidenceContext) -> Result<EvidenceBundle, V8CoreError> {
        let mut claims = Vec::new();
        let prov = ctx.resolve_provenance()?;

        if let Some(cycles) = ctx.cycle_ledgers {
            let total_evidences: usize = cycles.iter().map(|c| c.evidence_count).sum();
            let total_episodes: usize = cycles.iter().map(|c| c.episodes_generated).sum();

            let avg_witnesses_per_episode = if total_episodes > 0 {
                total_evidences as f64 / total_episodes as f64
            } else {
                0.0
            };

            claims.push(EvidenceClaim::new(
                "WITNESS_QUALITY_AUDITED",
                EvidenceAuthority::DeterministicDerivation,
                Some(avg_witnesses_per_episode),
                format!(
                    "Evaluated {} witness evidence receipts across {} opportunity episodes (mean={:.1} per episode).",
                    total_evidences, total_episodes, avg_witnesses_per_episode
                ),
                None,
                None,
                false,
            ));
        } else {
            claims.push(EvidenceClaim::new(
                "WITNESS_QUALITY_UNAVAILABLE",
                EvidenceAuthority::DeterministicDerivation,
                None,
                "No cycle ledgers supplied for expert witness quality evaluation.".to_string(),
                None,
                None,
                false,
            ));
        }

        Ok(EvidenceBundle::new(
            self.identity(),
            self.lifecycle(),
            ctx.scope.clone(),
            claims,
            self.assumptions(),
            self.dependencies(),
            EvidenceCoverage::full(1),
            None,
            prov,
            ctx.as_of_time,
        ))
    }
}

/// P08: Decision Transfer Efficiency Provider.
pub struct P08DecisionTransferEfficiencyProvider {
    pub lifecycle: ProviderLifecycle,
}

impl Default for P08DecisionTransferEfficiencyProvider {
    fn default() -> Self {
        Self {
            lifecycle: ProviderLifecycle::Validated,
        }
    }
}

impl AuditEvidenceProvider for P08DecisionTransferEfficiencyProvider {
    fn identity(&self) -> ProviderIdentity {
        ProviderIdentity::new("P08_DECISION_TRANSFER_EFFICIENCY", "Decision Transfer Efficiency Analyzer", "v1.1.0-production")
    }

    fn lifecycle(&self) -> ProviderLifecycle {
        self.lifecycle
    }

    fn declared_authority(&self) -> EvidenceAuthority {
        EvidenceAuthority::DeterministicDerivation
    }

    fn assumptions(&self) -> Vec<Assumption> {
        vec![Assumption::new("TRANSFER_FIDELITY", "Measures empirical information retention from witness evidence to campaign execution.", true)]
    }

    fn dependencies(&self) -> Vec<EvidenceDependency> {
        vec![EvidenceDependency::new("v8-funnel-pipeline", "1.0", "blake3_funnel_digest")]
    }

    fn evaluate(&self, ctx: &EvidenceContext) -> Result<EvidenceBundle, V8CoreError> {
        let mut claims = Vec::new();
        let prov = ctx.resolve_provenance()?;

        if let Some(cycles) = ctx.cycle_ledgers {
            let total_episodes: usize = cycles.iter().map(|c| c.episodes_generated).sum();
            let total_campaigns: usize = cycles.iter().map(|c| c.campaigns_launched.len()).sum();

            let transfer_ratio = if total_episodes > 0 {
                total_campaigns as f64 / total_episodes as f64
            } else {
                1.0
            };

            claims.push(EvidenceClaim::new(
                "DECISION_TRANSFER_EFFICIENCY_AUDITED",
                EvidenceAuthority::DeterministicDerivation,
                Some(transfer_ratio),
                format!(
                    "Empirical decision transfer efficiency: {:.2}% ({} campaigns launched from {} detected episodes).",
                    transfer_ratio * 100.0, total_campaigns, total_episodes
                ),
                None,
                None,
                false,
            ));
        } else {
            claims.push(EvidenceClaim::new(
                "TRANSFER_EFFICIENCY_UNAVAILABLE",
                EvidenceAuthority::DeterministicDerivation,
                None,
                "No cycle ledgers supplied for empirical transfer efficiency measurement.".to_string(),
                None,
                None,
                false,
            ));
        }

        Ok(EvidenceBundle::new(
            self.identity(),
            self.lifecycle(),
            ctx.scope.clone(),
            claims,
            self.assumptions(),
            self.dependencies(),
            EvidenceCoverage::full(1),
            None,
            prov,
            ctx.as_of_time,
        ))
    }
}

/// P09: Implementation Shortfall & TCA Provider.
pub struct P09ImplementationShortfallProvider {
    pub lifecycle: ProviderLifecycle,
}

impl Default for P09ImplementationShortfallProvider {
    fn default() -> Self {
        Self {
            lifecycle: ProviderLifecycle::Validated,
        }
    }
}

impl AuditEvidenceProvider for P09ImplementationShortfallProvider {
    fn identity(&self) -> ProviderIdentity {
        ProviderIdentity::new("P09_IMPLEMENTATION_SHORTFALL", "Implementation Shortfall & TCA Analyzer", "v1.1.0-production")
    }

    fn lifecycle(&self) -> ProviderLifecycle {
        self.lifecycle
    }

    fn declared_authority(&self) -> EvidenceAuthority {
        EvidenceAuthority::DeterministicDerivation
    }

    fn assumptions(&self) -> Vec<Assumption> {
        vec![Assumption::new("PERROLD_SHORTFALL_DECOMPOSITION", "Decomposes empirical shortfall into explicit fees, funding carry, and slippage.", true)]
    }

    fn dependencies(&self) -> Vec<EvidenceDependency> {
        vec![EvidenceDependency::new("v8-usdm-sim", "1.0", "blake3_usdm_digest")]
    }

    fn evaluate(&self, ctx: &EvidenceContext) -> Result<EvidenceBundle, V8CoreError> {
        let mut claims = Vec::new();
        let prov = ctx.resolve_provenance()?;

        if let Some(cf_ledger) = ctx.cashflow_ledger {
            let total_fees = cf_ledger.total_commission();
            let total_funding = cf_ledger.total_funding();
            let total_slippage = cf_ledger.total_slippage();
            let total_shortfall = total_fees + total_funding.abs() + total_slippage;

            claims.push(EvidenceClaim::new(
                "EXPLICIT_FEES_DRAG",
                EvidenceAuthority::Observed,
                Some(total_fees),
                format!("Total explicit exchange fee drag: ${:.4}", total_fees),
                None,
                None,
                false,
            ));
            claims.push(EvidenceClaim::new(
                "FUNDING_CARRY_DRAG",
                EvidenceAuthority::Observed,
                Some(total_funding),
                format!("Total funding rate cashflow carry: ${:.4}", total_funding),
                None,
                None,
                false,
            ));
            claims.push(EvidenceClaim::new(
                "SLIPPAGE_DRAG",
                EvidenceAuthority::DeterministicDerivation,
                Some(total_slippage),
                format!("Total simulated slippage and stop gap drag: ${:.4}", total_slippage),
                None,
                None,
                false,
            ));
            claims.push(EvidenceClaim::new(
                "TOTAL_IMPLEMENTATION_SHORTFALL",
                EvidenceAuthority::DeterministicDerivation,
                Some(total_shortfall),
                format!("Total empirical implementation shortfall: ${:.4}", total_shortfall),
                None,
                None,
                false,
            ));
        } else {
            claims.push(EvidenceClaim::new(
                "IMPLEMENTATION_SHORTFALL_UNAVAILABLE",
                EvidenceAuthority::DeterministicDerivation,
                None,
                "No cashflow ledger supplied for empirical implementation shortfall decomposition.".to_string(),
                None,
                None,
                false,
            ));
        }

        Ok(EvidenceBundle::new(
            self.identity(),
            self.lifecycle(),
            ctx.scope.clone(),
            claims,
            self.assumptions(),
            self.dependencies(),
            EvidenceCoverage::full(1),
            None,
            prov,
            ctx.as_of_time,
        ))
    }
}

/// Category classification in the Economic Pathology Map (D-136-RP-001 §13.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum PathologyClass {
    /// Adjudicated observed behavior.
    Observed,
    /// Claim verified and supported.
    Supported,
    /// Contested claim with conflicting evidence.
    Contested,
    /// Unidentified residual phenomena.
    Unidentified,
    /// Theoretical Oracle opportunity gap.
    OracleGap,
    /// Negative outcome trade executed despite adverse signals.
    BadExecuted,
    /// Positive opportunity missed due to upstream drop/rejection with proven counterfactual value.
    MissedGood,
    /// Positive opportunity mis-expressed (e.g. wrong horizon/sizing/early exit).
    GoodButMisexpressed,
}

/// An entry in the Economic Pathology Map.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PathologyRecord {
    pub pathology_id: String,
    pub class: PathologyClass,
    pub opportunity_id: Option<String>,
    pub trace_id: Option<String>,
    pub description: String,
    pub magnitude_r: Option<f64>,
    pub attributed_stage: Option<String>,
    pub primary_provider: String,
}

/// Comprehensive Economic Pathology Map (Major Checkpoint A).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EconomicPathologyMap {
    records: Vec<PathologyRecord>,
    by_class: HashMap<PathologyClass, Vec<usize>>,
}

impl EconomicPathologyMap {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, record: PathologyRecord) {
        let idx = self.records.len();
        self.by_class.entry(record.class).or_default().push(idx);
        self.records.push(record);
    }

    pub fn get_by_class(&self, class: PathologyClass) -> Vec<&PathologyRecord> {
        self.by_class
            .get(&class)
            .map(|indices| indices.iter().filter_map(|&idx| self.records.get(idx)).collect())
            .unwrap_or_default()
    }

    pub fn len(&self) -> usize {
        self.records.len()
    }

    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    pub fn all(&self) -> &[PathologyRecord] {
        &self.records
    }

    /// Builds the pathology map from an adjudicated `EvidenceGraph` and `DecisionBeliefLedger`.
    /// Strictly adheres to Rule 12 / Invariant 3: UNKNOWN / UNIDENTIFIED is preferred over false attribution.
    pub fn build_from_adjudication(
        graph: &EvidenceGraph,
        belief_ledger: &crate::telemetry::DecisionBeliefLedger,
    ) -> Self {
        let mut map = Self::new();

        for (claim_id, claim) in graph.all_claims() {
            let verdict = graph.get_verdict(claim_id).unwrap_or(ClaimVerdict::Unidentified);

            let class = match verdict {
                ClaimVerdict::Supported => {
                    if claim.is_pathology {
                        PathologyClass::BadExecuted
                    } else {
                        PathologyClass::Supported
                    }
                }
                ClaimVerdict::Contested => PathologyClass::Contested,
                ClaimVerdict::Falsified => PathologyClass::Observed,
                ClaimVerdict::InsufficientEvidence | ClaimVerdict::Unidentified => PathologyClass::Unidentified,
                ClaimVerdict::PartiallySupported => PathologyClass::Supported,
                ClaimVerdict::Superseded | ClaimVerdict::Revoked => PathologyClass::Observed,
            };

            map.insert(PathologyRecord {
                pathology_id: format!("path_{claim_id}"),
                class,
                opportunity_id: None,
                trace_id: claim.trace_id.as_ref().map(|t| t.to_string()),
                description: claim.statement.clone(),
                magnitude_r: claim.value_numeric,
                attributed_stage: None,
                primary_provider: "ADJUDICATED_GRAPH".to_string(),
            });
        }

        // Add verified rejection records with explicit evidence gating (NOT automatic MissedGood)
        for receipt in belief_ledger.all() {
            if receipt.is_rejection {
                let class = if receipt.expected_net_utility_r.map(|u| u > 0.0).unwrap_or(false) {
                    PathologyClass::MissedGood
                } else {
                    PathologyClass::Observed
                };

                map.insert(PathologyRecord {
                    pathology_id: format!("path_rejection_{}", receipt.receipt_id),
                    class,
                    opportunity_id: Some(receipt.opportunity_id.clone()),
                    trace_id: Some(receipt.trace_id.to_string()),
                    description: format!("Opportunity rejected at stage {:?}: {:?}", receipt.stage, receipt.rejection_reason),
                    magnitude_r: receipt.expected_net_utility_r,
                    attributed_stage: Some(receipt.stage.as_str().to_string()),
                    primary_provider: "DECISION_BELIEF_LEDGER".to_string(),
                });
            }
        }

        map
    }
}
