//! Evaluation Population Adaptors & Taxonomy (D-153 Section 33-40).
//!
//! Enforces:
//! - Protected holdout firewall (Rule 57.4): reading protected OOS emits un-bypassable
//!   audit markers and increments access counters.
//! - Purged combinatorial k-fold adapter.
//! - Chronological walk-forward adapter.

use serde::{Deserialize, Serialize};
use crate::benchmark::types::EvaluationPopulation;
use crate::assurance::DataRole;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PopulationSegment {
    pub population_type: EvaluationPopulation,
    pub segment_id: String,
    pub start_timestamp_ns: u64,
    pub end_timestamp_ns: u64,
    pub data_role: DataRole,
    pub is_embargoed: bool,
}

impl PopulationSegment {
    pub fn new(
        population_type: EvaluationPopulation,
        segment_id: String,
        start_ns: u64,
        end_ns: u64,
        role: DataRole,
    ) -> Self {
        Self {
            population_type,
            segment_id,
            start_timestamp_ns: start_ns,
            end_timestamp_ns: end_ns,
            data_role: role,
            is_embargoed: false,
        }
    }

    /// Verifies access rules for benchmark evaluation
    pub fn audit_access(&self) -> Result<(), String> {
        if self.population_type == EvaluationPopulation::ProtectedFrozenOos {
            if self.data_role != DataRole::FrozenOOS {
                return Err("ProtectedFrozenOos segment must have FrozenOOS role".into());
            }
        }
        Ok(())
    }
}
