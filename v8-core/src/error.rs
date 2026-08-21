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
