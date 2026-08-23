#![allow(dead_code)]
//! Canonical Economic Trace Identity & Provenance (EEO-001H, D-136).
//!
//! Constitutional Invariants:
//! 1. Opportunity Sovereignty: `OpportunityId` identifies the market economic event.
//! 2. Trajectory Identity: `EconomicTraceId` identifies a specific execution or decision path.
//! 3. Provenance Isolation: `TraceProvenance` captures the cryptographic commit/tape/policy state
//!    without destroying identity alignment between baseline, challenger, and counterfactual runs.
//! 4. Typed Modality: `TrajectoryType` distinguishes `Observed` from `Counterfactual` without naming heuristics.

use std::fmt;
use std::ops::Deref;
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;
use crate::opportunity::book::OpportunityEpisode;

/// Execution modality for an economic decision trajectory.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum TrajectoryType {
    /// Canonical observed forward simulation or physical execution.
    Observed,
    /// Counterfactual branch under registered or exploratory policy intervention.
    Counterfactual,
}

impl TrajectoryType {
    pub fn is_observed(&self) -> bool {
        matches!(self, Self::Observed)
    }

    pub fn is_counterfactual(&self) -> bool {
        matches!(self, Self::Counterfactual)
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Observed => "Observed",
            Self::Counterfactual => "Counterfactual",
        }
    }
}

/// Cryptographic provenance context binding the decision environment (D-136-RP-001 §6.1).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TraceProvenance {
    pub tape_hash: String,
    pub policy_hash: String,
    pub constitution_hash: String,
    pub code_hash: String,
}

impl TraceProvenance {
    pub fn new(
        tape_hash: impl Into<String>,
        policy_hash: impl Into<String>,
        constitution_hash: impl Into<String>,
        code_hash: impl Into<String>,
    ) -> Result<Self, V8CoreError> {
        let tape_hash = tape_hash.into();
        let policy_hash = policy_hash.into();
        let constitution_hash = constitution_hash.into();
        let code_hash = code_hash.into();

        if tape_hash.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "tape_hash cannot be empty in TraceProvenance".to_string(),
            ));
        }
        if policy_hash.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "policy_hash cannot be empty in TraceProvenance".to_string(),
            ));
        }
        if constitution_hash.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "constitution_hash cannot be empty in TraceProvenance".to_string(),
            ));
        }
        if code_hash.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "code_hash cannot be empty in TraceProvenance".to_string(),
            ));
        }

        Ok(Self {
            tape_hash,
            policy_hash,
            constitution_hash,
            code_hash,
        })
    }

    /// Computes deterministic BLAKE3 digest of the provenance bundle.
    pub fn compute_hash(&self) -> String {
        let mut c = Canon::new();
        c.push_str("TraceProvenance");
        c.push_str(&self.tape_hash);
        c.push_str(&self.policy_hash);
        c.push_str(&self.constitution_hash);
        c.push_str(&self.code_hash);
        c.finish_blake3_hex()
    }
}

/// Canonical Economic Trace Identifier (BLAKE3-derived hex).
/// Identifies a specific execution/decision trajectory for an opportunity.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct EconomicTraceId(pub String);

impl EconomicTraceId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    /// Computes deterministic BLAKE3 identity for an economic trajectory.
    /// Trajectory tag distinguishes baseline vs challenger vs counterfactual branches
    /// while preserving opportunity identity alignment.
    pub fn compute(
        opportunity_id: &str,
        trajectory_tag: &str,
        trajectory_type: TrajectoryType,
        pit_timestamp: i64,
    ) -> Self {
        let mut c = Canon::new();
        c.push_str("EconomicTraceId");
        c.push_str(opportunity_id);
        c.push_str(trajectory_tag);
        c.push_str(trajectory_type.as_str());
        c.push_i64(pit_timestamp);
        Self(c.finish_blake3_hex())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for EconomicTraceId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Deref for EconomicTraceId {
    type Target = str;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl AsRef<str> for EconomicTraceId {
    fn as_ref(&self) -> &str {
        &self.0
    }
}

impl From<String> for EconomicTraceId {
    fn from(s: String) -> Self {
        Self(s)
    }
}

impl From<&str> for EconomicTraceId {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

/// Canonical Decision Span Identifier (BLAKE3-derived hex).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct SpanId(pub String);

impl SpanId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    /// Computes deterministic BLAKE3 identity for a span.
    pub fn compute(
        trace_id: &EconomicTraceId,
        parent_span_id: Option<&SpanId>,
        stage_name: &str,
        start_time: i64,
        disambiguator: &str,
    ) -> Self {
        let mut c = Canon::new();
        c.push_str("SpanId");
        c.push_str(trace_id.as_str());
        if let Some(parent) = parent_span_id {
            c.push_str(parent.as_str());
        } else {
            c.push_null();
        }
        c.push_str(stage_name);
        c.push_i64(start_time);
        c.push_str(disambiguator);
        Self(c.finish_blake3_hex())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for SpanId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Deref for SpanId {
    type Target = str;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl AsRef<str> for SpanId {
    fn as_ref(&self) -> &str {
        &self.0
    }
}

impl From<String> for SpanId {
    fn from(s: String) -> Self {
        Self(s)
    }
}

impl From<&str> for SpanId {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

/// Immutable Root Context of an Economic Trace (D-136-RP-001 §6.1).
/// Preserves opportunity identity, trajectory identity, and provenance as distinct dimensions.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EconomicTraceContext {
    pub trace_id: EconomicTraceId,
    pub opportunity_id: String,
    pub trajectory_type: TrajectoryType,
    pub trajectory_tag: String,
    pub pit_timestamp: i64,
    pub provenance: TraceProvenance,
}

impl EconomicTraceContext {
    /// Creates and cryptographically validates a new `EconomicTraceContext`.
    pub fn new(
        opportunity_id: impl Into<String>,
        trajectory_type: TrajectoryType,
        trajectory_tag: impl Into<String>,
        pit_timestamp: i64,
        provenance: TraceProvenance,
    ) -> Result<Self, V8CoreError> {
        let opportunity_id = opportunity_id.into();
        let trajectory_tag = trajectory_tag.into();

        if opportunity_id.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "opportunity_id cannot be empty".to_string(),
            ));
        }
        if trajectory_tag.is_empty() {
            return Err(V8CoreError::TraceLineageError(
                "trajectory_tag cannot be empty".to_string(),
            ));
        }

        let trace_id = EconomicTraceId::compute(
            &opportunity_id,
            &trajectory_tag,
            trajectory_type,
            pit_timestamp,
        );

        Ok(Self {
            trace_id,
            opportunity_id,
            trajectory_type,
            trajectory_tag,
            pit_timestamp,
            provenance,
        })
    }

    /// Constructs an `EconomicTraceContext` for an observed opportunity episode.
    pub fn from_episode(
        episode: &OpportunityEpisode,
        tape_hash: &str,
        policy_hash: &str,
        constitution_hash: &str,
        code_hash: &str,
    ) -> Result<Self, V8CoreError> {
        let prov = TraceProvenance::new(tape_hash, policy_hash, constitution_hash, code_hash)?;
        Self::new(
            &episode.episode_id,
            TrajectoryType::Observed,
            "canonical_observed",
            episode.as_of_time,
            prov,
        )
    }

    /// Constructs an `EconomicTraceContext` for a named challenger or counterfactual trajectory.
    pub fn from_episode_trajectory(
        episode: &OpportunityEpisode,
        trajectory_type: TrajectoryType,
        trajectory_tag: &str,
        tape_hash: &str,
        policy_hash: &str,
        constitution_hash: &str,
        code_hash: &str,
    ) -> Result<Self, V8CoreError> {
        let prov = TraceProvenance::new(tape_hash, policy_hash, constitution_hash, code_hash)?;
        Self::new(
            &episode.episode_id,
            trajectory_type,
            trajectory_tag,
            episode.as_of_time,
            prov,
        )
    }

    /// Convenience accessors for provenance fields
    pub fn tape_hash(&self) -> &str {
        &self.provenance.tape_hash
    }

    pub fn policy_hash(&self) -> &str {
        &self.provenance.policy_hash
    }

    pub fn constitution_hash(&self) -> &str {
        &self.provenance.constitution_hash
    }

    pub fn code_hash(&self) -> &str {
        &self.provenance.code_hash
    }

    /// Computes cryptographic hash for the entire trace context payload.
    pub fn compute_hash(&self) -> String {
        let mut c = Canon::new();
        c.push_str("EconomicTraceContext");
        c.push_str(self.trace_id.as_str());
        c.push_str(&self.opportunity_id);
        c.push_str(self.trajectory_type.as_str());
        c.push_str(&self.trajectory_tag);
        c.push_i64(self.pit_timestamp);
        c.push_str(&self.provenance.compute_hash());
        c.finish_blake3_hex()
    }
}
