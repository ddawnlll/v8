#![allow(dead_code)]
//! Canonical Decision Spans, Evidence Spans, and Semantic Graph Links (EEO-001H, D-136).
//!
//! Constitutional Invariants:
//! 1. Epistemic Separation: PIT economic decision stages (`DecisionStage`) are strictly isolated
//!    from post-outcome evidence and Oracle/Audit evaluation (`EvidenceStage`).
//! 2. Ancestry Integrity: PIT decision spans can NEVER take post-outcome evidence or Oracle spans
//!    as an upstream parent/ancestor.
//! 3. Counterfactual Lineage: Explicit `SpanLinkType::CounterfactualBranch` distinguishes counterfactual
//!    derivation from observed execution.
//! 4. Many-to-Many Graph Topology: `SpanLink` connects aggregated campaigns without assuming 1 opp = 1 trade.

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use super::identity::{EconomicTraceId, SpanId};

/// Canonical Point-In-Time Economic Decision Stage in the V8.3 trajectory.
/// Oracle hindsight and Audit adjudication are strictly EXCLUDED from this enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum DecisionStage {
    MarketState,
    OpportunityDetection,
    WitnessObservation,
    EvidenceReconciliation,
    SelectiveUtility,
    PortfolioFeasibility,
    CampaignAdmission,
    OrderDispatch,
    ExecutionFill,
    PositionManagement,
    CashflowSettlement,
}

impl DecisionStage {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::MarketState => "MarketState",
            Self::OpportunityDetection => "OpportunityDetection",
            Self::WitnessObservation => "WitnessObservation",
            Self::EvidenceReconciliation => "EvidenceReconciliation",
            Self::SelectiveUtility => "SelectiveUtility",
            Self::PortfolioFeasibility => "PortfolioFeasibility",
            Self::CampaignAdmission => "CampaignAdmission",
            Self::OrderDispatch => "OrderDispatch",
            Self::ExecutionFill => "ExecutionFill",
            Self::PositionManagement => "PositionManagement",
            Self::CashflowSettlement => "CashflowSettlement",
        }
    }

    /// Confirms that this is a PIT economic decision stage.
    pub fn is_pit_decision(&self) -> bool {
        true
    }
}

/// Post-Outcome & Evidence Plane Evaluation Stage (D-136-RP-001 §5.2, §5.3).
/// Operates strictly as downstream observation/adjudication over frozen decision spans.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum EvidenceStage {
    /// Hindsight frontier opportunity evaluation (Target Oracle).
    TargetOracleHindsight,
    /// Realized path markout and MFE/MAE analysis.
    HindsightPathAnalysis,
    /// Audit invariant, provenance, and claim adjudication.
    AuditAdjudication,
    /// Versioned Evidence Provider evaluation (P01–P12).
    ProviderEvaluation,
    /// Multiplicity and search space accounting.
    MultiplicityAccounting,
}

impl EvidenceStage {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::TargetOracleHindsight => "TargetOracleHindsight",
            Self::HindsightPathAnalysis => "HindsightPathAnalysis",
            Self::AuditAdjudication => "AuditAdjudication",
            Self::ProviderEvaluation => "ProviderEvaluation",
            Self::MultiplicityAccounting => "MultiplicityAccounting",
        }
    }

    /// Confirms that this is post-outcome evidence with zero PIT decision authority.
    pub fn is_post_outcome(&self) -> bool {
        true
    }
}

/// Classification of span category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum SpanKind {
    Decision(DecisionStage),
    Evidence(EvidenceStage),
}

/// Semantic relationship type between decision spans and opportunities.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum SpanLinkType {
    /// Multiple opportunities aggregated into a single execution campaign.
    AggregatedIntoCampaign,
    /// Upstream opportunity episode that parented or catalyzed this decision.
    ParentOpportunity,
    /// Transformed or decomposed exposure structure.
    TransformedExposure,
    /// Co-temporal correlated market episode.
    CorrelatedEpisode,
    /// Branch under counterfactual replay or candidate intervention.
    CounterfactualBranch,
    /// Causal dependency or related decision.
    RelatedDecision,
    /// Post-outcome observation or evidence attachment.
    PostOutcomeEvidenceLink,
}

impl SpanLinkType {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::AggregatedIntoCampaign => "AggregatedIntoCampaign",
            Self::ParentOpportunity => "ParentOpportunity",
            Self::TransformedExposure => "TransformedExposure",
            Self::CorrelatedEpisode => "CorrelatedEpisode",
            Self::CounterfactualBranch => "CounterfactualBranch",
            Self::RelatedDecision => "RelatedDecision",
            Self::PostOutcomeEvidenceLink => "PostOutcomeEvidenceLink",
        }
    }

    pub fn is_counterfactual_branch(&self) -> bool {
        matches!(self, Self::CounterfactualBranch)
    }
}

/// Explicit many-to-many link between decision spans and opportunity traces.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SpanLink {
    pub target_trace_id: EconomicTraceId,
    pub target_span_id: Option<SpanId>,
    pub opportunity_id: String,
    pub link_type: SpanLinkType,
    pub attributes: Vec<(String, String)>,
}

impl SpanLink {
    pub fn new(
        target_trace_id: EconomicTraceId,
        target_span_id: Option<SpanId>,
        opportunity_id: impl Into<String>,
        link_type: SpanLinkType,
    ) -> Self {
        Self {
            target_trace_id,
            target_span_id,
            opportunity_id: opportunity_id.into(),
            link_type,
            attributes: Vec::new(),
        }
    }

    pub fn with_attribute(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.attributes.push((key.into(), value.into()));
        self
    }
}

/// Canonical Unit of Work in the PIT Economic Decision Path.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DecisionSpan {
    pub span_id: SpanId,
    pub trace_id: EconomicTraceId,
    pub parent_span_id: Option<SpanId>,
    pub stage: DecisionStage,
    pub start_time: i64,
    pub end_time: Option<i64>,
    pub receipt_id: Option<String>,
    pub links: Vec<SpanLink>,
    pub attributes: Vec<(String, String)>,
}

impl DecisionSpan {
    /// Creates a new `DecisionSpan` with deterministic BLAKE3 identity.
    pub fn new(
        trace_id: EconomicTraceId,
        parent_span_id: Option<SpanId>,
        stage: DecisionStage,
        start_time: i64,
        disambiguator: &str,
    ) -> Self {
        let span_id = SpanId::compute(
            &trace_id,
            parent_span_id.as_ref(),
            stage.as_str(),
            start_time,
            disambiguator,
        );
        Self {
            span_id,
            trace_id,
            parent_span_id,
            stage,
            start_time,
            end_time: None,
            receipt_id: None,
            links: Vec::new(),
            attributes: Vec::new(),
        }
    }

    pub fn with_link(mut self, link: SpanLink) -> Self {
        self.links.push(link);
        self
    }

    pub fn with_attribute(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.attributes.push((key.into(), value.into()));
        self
    }

    pub fn with_receipt(mut self, receipt_id: impl Into<String>) -> Self {
        self.receipt_id = Some(receipt_id.into());
        self
    }

    /// Closes the span with monotonic time validation.
    pub fn close(&mut self, end_time: i64) -> Result<(), V8CoreError> {
        if end_time < self.start_time {
            return Err(V8CoreError::TraceLineageError(format!(
                "DecisionSpan {} end_time ({}) cannot precede start_time ({})",
                self.span_id, end_time, self.start_time
            )));
        }
        self.end_time = Some(end_time);
        Ok(())
    }
}

/// Post-Outcome Evidence Span observing a completed Decision Span.
/// Bound to the Telemetry & Evidence Plane (D-136-RP-001 §5.2).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvidenceSpan {
    pub span_id: SpanId,
    pub trace_id: EconomicTraceId,
    pub observed_decision_span_id: SpanId,
    pub stage: EvidenceStage,
    pub evaluation_time: i64,
    pub receipt_id: Option<String>,
    pub claims: Vec<String>,
    pub attributes: Vec<(String, String)>,
}

impl EvidenceSpan {
    pub fn new(
        trace_id: EconomicTraceId,
        observed_decision_span_id: SpanId,
        stage: EvidenceStage,
        evaluation_time: i64,
        disambiguator: &str,
    ) -> Self {
        let span_id = SpanId::compute(
            &trace_id,
            Some(&observed_decision_span_id),
            stage.as_str(),
            evaluation_time,
            disambiguator,
        );
        Self {
            span_id,
            trace_id,
            observed_decision_span_id,
            stage,
            evaluation_time,
            receipt_id: None,
            claims: Vec::new(),
            attributes: Vec::new(),
        }
    }

    pub fn with_claim(mut self, claim: impl Into<String>) -> Self {
        self.claims.push(claim.into());
        self
    }

    pub fn with_receipt(mut self, receipt_id: impl Into<String>) -> Self {
        self.receipt_id = Some(receipt_id.into());
        self
    }

    pub fn with_attribute(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.attributes.push((key.into(), value.into()));
        self
    }
}
