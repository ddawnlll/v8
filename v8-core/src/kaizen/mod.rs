//! V8 Kaizen Continuous Improvement Engine (v8.kaizen.engine.v1).
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md`
//! - `HYPOTHESIS_LAB_PROTOCOL.md`
//! - `EVALUATION_EVIDENCE_SYSTEM.md`
//! - `LEARNING_PROTOCOL.md`

pub mod diagnosis;

pub use diagnosis::{
    EvidenceRequirement, EvidenceValidity, ExpertForensics, ExpertId, FailureTag,
    ForensicAssessment, ForensicsError, RegimeForensics, ReplicationStatus, VariantId,
};
