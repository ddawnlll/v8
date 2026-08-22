#![allow(dead_code, unused_imports, unused_variables, unused_mut)]
//! Canonical Evidence Bundle Contract & Evidence Provider Specification (EEO-003, D-136-RP-001 §8, §9, §10, §21).
//!
//! Constitutional Invariants:
//! 1. Authority Separation: Evidence is typed into distinct epistemic classes (Observed, Deterministic, Statistical, Counterfactual, etc.).
//! 2. Explicit Assumptions & Dependencies: Every claim must expose its assumptions, dependencies, and coverage.
//! 3. Versioned & Non-Constitutional: Provider count, weights, and algorithms are versioned implementation details.
//! 4. Lifecycle Sovereignty: Providers transition through an explicit lifecycle (Experimental -> Shadow -> Validated -> Trusted -> Restricted -> Deprecated -> Superseded / Revoked).
//! 5. Zero Direct Policy Mutation: Providers emit evidence bundles only; they have ZERO authority over runtime execution or Kaizen policy.

use std::fmt;
use std::ops::Deref;
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;
use crate::telemetry::{DecisionBeliefLedger, EconomicTraceId, EconomicTraceLedger, SpanId, TraceProvenance};

/// Canonical Epistemic Authority Classes (D-136-RP-001 §10).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum EvidenceAuthority {
    /// Physically observed cashflows, fees, fills, or raw ledger events.
    Observed,
    /// Mathematically exact deterministic derivation from certified telemetry/code state.
    DeterministicDerivation,
    /// Calibrated statistical estimate under declared sample/distribution assumptions.
    StatisticalEstimate,
    /// Deterministic replay on frozen exogenous market tape under registered intervention.
    DeterministicCounterfactual,
    /// Off-policy estimate (e.g. Doubly Robust) under propensity / support assumptions.
    OffPolicyEstimate,
    /// Theoretical hindsight frontier / diagnostic upper bound from Target Oracle.
    OracleUpperBound,
    /// Explicitly unidentifiable / unmodeled residual.
    Unidentified,
}

impl EvidenceAuthority {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Observed => "Observed",
            Self::DeterministicDerivation => "DeterministicDerivation",
            Self::StatisticalEstimate => "StatisticalEstimate",
            Self::DeterministicCounterfactual => "DeterministicCounterfactual",
            Self::OffPolicyEstimate => "OffPolicyEstimate",
            Self::OracleUpperBound => "OracleUpperBound",
            Self::Unidentified => "Unidentified",
        }
    }

    pub fn is_deterministic(&self) -> bool {
        matches!(self, Self::Observed | Self::DeterministicDerivation | Self::DeterministicCounterfactual)
    }

    pub fn is_oracle(&self) -> bool {
        matches!(self, Self::OracleUpperBound)
    }
}

/// Provider Lifecycle State (D-136-RP-001 §21).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ProviderLifecycle {
    /// In development / internal test.
    Experimental,
    /// Running in shadow mode, outputting unadjudicated diagnostic receipts.
    Shadow,
    /// Successfully passed qualification test suite (Q01–Q15).
    Validated,
    /// Fully qualified and trusted for Kaizen experiment candidate generation.
    Trusted,
    /// Usage restricted due to domain degradation, regime shift, or elevated uncertainty.
    Restricted,
    /// Deprecated in favor of a newer provider version.
    Deprecated,
    /// Superseded by a newer provider version.
    Superseded,
    /// Revoked due to falsification, invalidation, or fatal common-mode defect.
    Revoked,
}

impl ProviderLifecycle {
    pub fn is_active_authority(&self) -> bool {
        matches!(self, Self::Validated | Self::Trusted | Self::Restricted)
    }

    pub fn is_revoked_or_superseded(&self) -> bool {
        matches!(self, Self::Revoked | Self::Superseded | Self::Deprecated)
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Experimental => "Experimental",
            Self::Shadow => "Shadow",
            Self::Validated => "Validated",
            Self::Trusted => "Trusted",
            Self::Restricted => "Restricted",
            Self::Deprecated => "Deprecated",
            Self::Superseded => "Superseded",
            Self::Revoked => "Revoked",
        }
    }
}

/// Provider Identity structure.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ProviderIdentity {
    pub provider_id: String,
    pub name: String,
    pub version: String,
}

impl ProviderIdentity {
    pub fn new(provider_id: impl Into<String>, name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            provider_id: provider_id.into(),
            name: name.into(),
            version: version.into(),
        }
    }

    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("ProviderIdentity");
        c.push_str(&self.provider_id);
        c.push_str(&self.version);
        c.finish_blake3_hex()
    }
}

/// Declared assumption under which evidence is generated.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Assumption {
    pub tag: String,
    pub description: String,
    pub is_falsifiable: bool,
}

impl Assumption {
    pub fn new(tag: impl Into<String>, description: impl Into<String>, is_falsifiable: bool) -> Self {
        Self {
            tag: tag.into(),
            description: description.into(),
            is_falsifiable,
        }
    }

    pub fn exogenous_tape() -> Self {
        Self::new("EXOGENOUS_TAPE", "Price-taking assumption; actions do not perturb subsequent market tape.", true)
    }

    pub fn unconstrained_capital() -> Self {
        Self::new("UNCONSTRAINED_CAPITAL", "Evaluated under unconstrained capital allocation.", true)
    }

    pub fn standard_slippage_model() -> Self {
        Self::new("STANDARD_SLIPPAGE_MODEL", "Slippage bounded by half of bid-ask spread.", true)
    }
}

/// Explicit dependency required by an Evidence Provider.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EvidenceDependency {
    pub name: String,
    pub version: String,
    pub digest: String,
}

impl EvidenceDependency {
    pub fn new(name: impl Into<String>, version: impl Into<String>, digest: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
            digest: digest.into(),
        }
    }
}

/// Evaluation scope of an evidence bundle.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EvidenceScope {
    pub symbol: String,
    pub venue: String,
    pub start_time: i64,
    pub end_time: i64,
    pub trace_ids: Vec<EconomicTraceId>,
}

impl EvidenceScope {
    pub fn single_trace(symbol: impl Into<String>, venue: impl Into<String>, timestamp: i64, trace_id: EconomicTraceId) -> Self {
        Self {
            symbol: symbol.into(),
            venue: venue.into(),
            start_time: timestamp,
            end_time: timestamp,
            trace_ids: vec![trace_id],
        }
    }

    pub fn range(symbol: impl Into<String>, venue: impl Into<String>, start_time: i64, end_time: i64, trace_ids: Vec<EconomicTraceId>) -> Self {
        Self {
            symbol: symbol.into(),
            venue: venue.into(),
            start_time,
            end_time,
            trace_ids,
        }
    }
}

/// Metric coverage description.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceCoverage {
    pub total_entities: usize,
    pub evaluated_entities: usize,
    pub coverage_ratio: f64,
    pub missing_count: usize,
}

impl EvidenceCoverage {
    pub fn full(count: usize) -> Self {
        Self {
            total_entities: count,
            evaluated_entities: count,
            coverage_ratio: 1.0,
            missing_count: 0,
        }
    }

    pub fn partial(total: usize, evaluated: usize) -> Self {
        let coverage_ratio = if total == 0 { 1.0 } else { evaluated as f64 / total as f64 };
        Self {
            total_entities: total,
            evaluated_entities: evaluated,
            coverage_ratio,
            missing_count: total.saturating_sub(evaluated),
        }
    }
}

/// Uncertainty evaluation of evidence claims.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UncertaintyDescriptor {
    pub confidence_score: f64,
    pub entropy: f64,
    pub sample_size: usize,
}

/// Canonical atomic Claim asserted by an Evidence Provider.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceClaim {
    pub claim_id: String,
    pub claim_type: String,
    pub authority: EvidenceAuthority,
    pub value_numeric: Option<f64>,
    pub statement: String,
    pub trace_id: Option<EconomicTraceId>,
    pub span_id: Option<SpanId>,
    pub is_pathology: bool,
}

impl EvidenceClaim {
    pub fn new(
        claim_type: impl Into<String>,
        authority: EvidenceAuthority,
        value_numeric: Option<f64>,
        statement: impl Into<String>,
        trace_id: Option<EconomicTraceId>,
        span_id: Option<SpanId>,
        is_pathology: bool,
    ) -> Self {
        let claim_type = claim_type.into();
        let statement = statement.into();

        let mut c = Canon::new();
        c.push_str("EvidenceClaim");
        c.push_str(&claim_type);
        c.push_str(authority.as_str());
        if let Some(v) = value_numeric {
            c.push_f64(v);
        } else {
            c.push_null();
        }
        c.push_str(&statement);
        if let Some(ref t) = trace_id {
            c.push_str(t.as_str());
        } else {
            c.push_null();
        }
        let claim_id = c.finish_blake3_hex();

        Self {
            claim_id,
            claim_type,
            authority,
            value_numeric,
            statement,
            trace_id,
            span_id,
            is_pathology,
        }
    }
}

/// Canonical Output Bundle emitted by an Evidence Provider (D-136-RP-001 §9).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceBundle {
    pub bundle_id: String,
    pub provider: ProviderIdentity,
    pub lifecycle: ProviderLifecycle,
    pub scope: EvidenceScope,
    pub claims: Vec<EvidenceClaim>,
    pub assumptions: Vec<Assumption>,
    pub dependencies: Vec<EvidenceDependency>,
    pub coverage: EvidenceCoverage,
    pub uncertainty: Option<UncertaintyDescriptor>,
    pub provenance: TraceProvenance,
    pub created_time: i64,
}

impl EvidenceBundle {
    pub fn new(
        provider: ProviderIdentity,
        lifecycle: ProviderLifecycle,
        scope: EvidenceScope,
        claims: Vec<EvidenceClaim>,
        assumptions: Vec<Assumption>,
        dependencies: Vec<EvidenceDependency>,
        coverage: EvidenceCoverage,
        uncertainty: Option<UncertaintyDescriptor>,
        provenance: TraceProvenance,
        created_time: i64,
    ) -> Self {
        let mut c = Canon::new();
        c.push_str("EvidenceBundle");
        c.push_str(&provider.compute_id());
        c.push_str(lifecycle.as_str());
        c.push_str(&scope.symbol);
        c.push_i64(created_time);
        c.push_list();
        c.push_count(claims.len());
        for cl in &claims {
            c.push_str(&cl.claim_id);
        }
        let bundle_id = c.finish_blake3_hex();

        Self {
            bundle_id,
            provider,
            lifecycle,
            scope,
            claims,
            assumptions,
            dependencies,
            coverage,
            uncertainty,
            provenance,
            created_time,
        }
    }
}

/// Input context supplied to Evidence Providers for evaluation.
pub struct EvidenceContext<'a> {
    pub trace_ledger: &'a EconomicTraceLedger,
    pub belief_ledger: &'a DecisionBeliefLedger,
    pub cashflow_ledger: Option<&'a crate::cashflow::CashflowLedger>,
    pub cycle_ledgers: Option<&'a [crate::opportunity::runloop::OpportunityCycleLedger]>,
    pub oracle_funnel: Option<&'a crate::opportunity::funnel::CanonicalFunnelReport>,
    pub multiplicity_ledger: Option<&'a crate::eeo::challenge::ResearchMultiplicityLedger>,
    pub scope: &'a EvidenceScope,
    pub provenance: Option<&'a TraceProvenance>,
    pub as_of_time: i64,
}

impl<'a> EvidenceContext<'a> {
    pub fn new(
        trace_ledger: &'a EconomicTraceLedger,
        belief_ledger: &'a DecisionBeliefLedger,
        scope: &'a EvidenceScope,
        as_of_time: i64,
    ) -> Self {
        Self {
            trace_ledger,
            belief_ledger,
            cashflow_ledger: None,
            cycle_ledgers: None,
            oracle_funnel: None,
            multiplicity_ledger: None,
            scope,
            provenance: None,
            as_of_time,
        }
    }

    pub fn with_cashflow_ledger(mut self, cashflow_ledger: &'a crate::cashflow::CashflowLedger) -> Self {
        self.cashflow_ledger = Some(cashflow_ledger);
        self
    }

    pub fn with_cycle_ledgers(mut self, cycle_ledgers: &'a [crate::opportunity::runloop::OpportunityCycleLedger]) -> Self {
        self.cycle_ledgers = Some(cycle_ledgers);
        self
    }

    pub fn with_oracle_funnel(mut self, oracle_funnel: &'a crate::opportunity::funnel::CanonicalFunnelReport) -> Self {
        self.oracle_funnel = Some(oracle_funnel);
        self
    }

    pub fn with_multiplicity_ledger(mut self, multiplicity_ledger: &'a crate::eeo::challenge::ResearchMultiplicityLedger) -> Self {
        self.multiplicity_ledger = Some(multiplicity_ledger);
        self
    }

    pub fn with_provenance(mut self, provenance: &'a TraceProvenance) -> Self {
        self.provenance = Some(provenance);
        self
    }

    pub fn resolve_provenance(&self) -> Result<TraceProvenance, V8CoreError> {
        if let Some(p) = self.provenance {
            return Ok(p.clone());
        }
        for tid in &self.scope.trace_ids {
            if let Some(ctx) = self.trace_ledger.get_context(tid) {
                return Ok(ctx.provenance.clone());
            }
        }
        // Fall back to first available context in ledger
        if let Some(first) = self.trace_ledger.contexts().values().next() {
            return Ok(first.provenance.clone());
        }
        Err(V8CoreError::TraceLineageError(
            "Missing required cryptographic trace provenance in evidence context".to_string(),
        ))
    }
}

/// Universal Trait implemented by all versioned Evidence Providers (D-136-RP-001 §9).
pub trait AuditEvidenceProvider: Send + Sync {
    fn identity(&self) -> ProviderIdentity;
    fn lifecycle(&self) -> ProviderLifecycle;
    fn declared_authority(&self) -> EvidenceAuthority;
    fn assumptions(&self) -> Vec<Assumption>;
    fn dependencies(&self) -> Vec<EvidenceDependency>;
    fn evaluate(&self, ctx: &EvidenceContext) -> Result<EvidenceBundle, V8CoreError>;
}

/// Central Provider Registry managing provider registrations and lifecycle state.
pub struct ProviderRegistry {
    providers: Vec<Box<dyn AuditEvidenceProvider>>,
}

impl Default for ProviderRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl ProviderRegistry {
    pub fn new() -> Self {
        Self {
            providers: Vec::new(),
        }
    }

    pub fn register(&mut self, provider: Box<dyn AuditEvidenceProvider>) {
        self.providers.push(provider);
    }

    pub fn providers(&self) -> &[Box<dyn AuditEvidenceProvider>] {
        &self.providers
    }

    pub fn get_by_id(&self, provider_id: &str) -> Option<&(dyn AuditEvidenceProvider + 'static)> {
        self.providers
            .iter()
            .find(|p| p.identity().provider_id == provider_id)
            .map(|p| &**p)
    }

    pub fn evaluate_all(&self, ctx: &EvidenceContext) -> Vec<Result<EvidenceBundle, V8CoreError>> {
        self.providers.iter().map(|p| p.evaluate(ctx)).collect()
    }
}
