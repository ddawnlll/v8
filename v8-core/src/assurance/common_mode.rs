//! Common-Mode Failure & Evidence Dependency Graph (D-147, D-149, M1).
//!
//! Detects shared data pipelines, duplicate lineages, or common-mode sensors
//! to prevent counting the same underlying evidence twice in independence tests.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Tracks evidence provider lineage to enforce independence requirements.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct CommonModeGraph {
    pub provider_lineages: HashMap<String, String>,
}

impl CommonModeGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register_provider(&mut self, provider_id: String, lineage: String) {
        self.provider_lineages.insert(provider_id, lineage);
    }

    /// Returns true if all provided provider IDs originate from disjoint lineages.
    pub fn are_independent(&self, provider_ids: &[String]) -> bool {
        let mut seen_lineages = HashSet::new();
        for p in provider_ids {
            let lineage = self.provider_lineages.get(p).unwrap_or(p);
            if !seen_lineages.insert(lineage) {
                return false;
            }
        }
        true
    }
}
