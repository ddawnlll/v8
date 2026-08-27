//! Provenance Graph & Artifact Lineage Verification (D-147, D-149, M1).
//!
//! Enforces content-addressed artifact lineage and immutable hash tracking.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Directed acyclic graph tracking artifact provenance edges.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProvenanceGraph {
    /// Maps artifact hash to its direct upstream parent artifact hashes.
    pub edges: HashMap<String, Vec<String>>,
    /// Maps artifact hash to its declared generating provider ID.
    pub providers: HashMap<String, String>,
}

impl ProvenanceGraph {
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers a new artifact with its upstream dependencies and provider.
    pub fn add_artifact(&mut self, hash: String, upstream: Vec<String>, provider: String) {
        self.edges.insert(hash.clone(), upstream);
        self.providers.insert(hash, provider);
    }

    /// Checks whether an upstream artifact is in the direct or indirect lineage of target.
    pub fn has_ancestor(&self, target_hash: &str, ancestor_hash: &str) -> bool {
        let mut visited = HashSet::new();
        let mut queue = vec![target_hash.to_string()];

        while let Some(curr) = queue.pop() {
            if curr == ancestor_hash {
                return true;
            }
            if visited.insert(curr.clone()) {
                if let Some(parents) = self.edges.get(&curr) {
                    for p in parents {
                        queue.push(p.clone());
                    }
                }
            }
        }
        false
    }
}
