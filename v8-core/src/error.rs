//! Canonical error taxonomy for v8-core (Issue #208).
//!
//! Provides strongly-typed errors replacing stringly-typed `Result<T, String>`
//! across scheduler, runloop, candidate lifecycle, data streaming, and telemetry.

use thiserror::Error;

/// The central error type for the V8 core runtime.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum V8CoreError {
    #[error("Scheduler evaluation error: {0}")]
    Scheduler(String),

    #[error("Candidate lifecycle error: candidate {candidate_id} cannot transition from {from:?} to {to}: {reason}")]
    InvalidCandidateTransition {
        candidate_id: String,
        from: Option<String>,
        to: String,
        reason: String,
    },

    #[error("Data streaming error: {0}")]
    DataStreaming(String),

    #[error("Checkpoint error: {0}")]
    Checkpoint(String),

    #[error("Path sanitization violation: {0}")]
    PathSanitization(String),

    #[error("Serialization / Deserialization error: {0}")]
    Serialization(String),

    #[error("IO error: {0}")]
    Io(String),

    #[error("Quant / Mathematical invariant failure: {0}")]
    QuantInvariant(String),

    #[error("Invalid opportunity state for {opportunity_id}: state {state}, reason: {reason}")]
    InvalidOpportunityState {
        opportunity_id: String,
        state: String,
        reason: String,
    },

    #[error("Unresolved economic exposure for symbol '{symbol}' on venue '{venue}': {reason}")]
    UnresolvedExposure {
        symbol: String,
        venue: String,
        reason: String,
    },

    #[error("Opportunity identity error for episode '{episode_id}': {reason}")]
    OpportunityIdentityError {
        episode_id: String,
        reason: String,
    },

    #[error("Invalid exposure structure: {0}")]
    InvalidExposureStructure(String),

    #[error("Witness reconciliation error: {0}")]
    WitnessReconciliationError(String),

    #[error("Selective utility error: {0}")]
    SelectiveUtilityError(String),

    #[error("Campaign lifecycle error: {0}")]
    CampaignLifecycleError(String),

    #[error("Economic trace lineage error: {0}")]
    TraceLineageError(String),
}

impl From<std::io::Error> for V8CoreError {
    fn from(err: std::io::Error) -> Self {
        V8CoreError::Io(err.to_string())
    }
}

impl From<bincode::Error> for V8CoreError {
    fn from(err: bincode::Error) -> Self {
        V8CoreError::Serialization(err.to_string())
    }
}

impl From<serde_json::Error> for V8CoreError {
    fn from(err: serde_json::Error) -> Self {
        V8CoreError::Serialization(err.to_string())
    }
}
