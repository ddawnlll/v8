//! Canonical Evidence Graph & Audit Adjudication Kernel (EEO-005, D-136-RP-001 §12).
//!
//! Constitutional Invariants:
//! 1. Adjudication Integrity: Audit adjudicates claims (SUPPORTED, FALSIFIED, CONTESTED, etc.); Audit does NOT invent interventions.
//! 2. Anti-Self-Certification: No provider may certify its own causal claim.
//! 3. Typed Claim Relationships: SUPPORTS, CHALLENGES, DEPENDS_ON, REPLICATES, SUPERSEDES, INVALIDATES.

#![allow(dead_code)]

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use super::contract::{EvidenceBundle, EvidenceClaim};

/// Typed edge relationship between evidence claims (D-136-RP-001 §12.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ClaimRelationship {
    Supports,
    Challenges,
    DependsOn,
    Replicates,
    Supersedes,
    Invalidates,
}

impl ClaimRelationship {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Supports => "SUPPORTS",
            Self::Challenges => "CHALLENGES",
            Self::DependsOn => "DEPENDS_ON",
            Self::Replicates => "REPLICATES",
            Self::Supersedes => "SUPERSEDES",
            Self::Invalidates => "INVALIDATES",
        }
    }
}

/// Adjudicated verdict emitted by the Central Audit Adjudicator (D-136-RP-001 §12.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ClaimVerdict {
    Supported,
    PartiallySupported,
    Contested,
    Falsified,
    InsufficientEvidence,
    Unidentified,
    Superseded,
    Revoked,
}

impl ClaimVerdict {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Supported => "SUPPORTED",
            Self::PartiallySupported => "PARTIALLY_SUPPORTED",
            Self::Contested => "CONTESTED",
            Self::Falsified => "FALSIFIED",
            Self::InsufficientEvidence => "INSUFFICIENT_EVIDENCE",
            Self::Unidentified => "UNIDENTIFIED",
            Self::Superseded => "SUPERSEDED",
            Self::Revoked => "REVOKED",
        }
    }

    pub fn is_actionable_for_kaizen(&self) -> bool {
        matches!(self, Self::Supported | Self::PartiallySupported)
    }
}

/// An edge connecting two claims in the Evidence Graph.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ClaimEdge {
    pub source_claim_id: String,
    pub target_claim_id: String,
    pub relationship: ClaimRelationship,
    pub weight: Option<u64>,
}

/// Directed Evidence Graph combining multi-provider claims and adjudicated verdicts.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EvidenceGraph {
    claims: HashMap<String, EvidenceClaim>,
    edges: Vec<ClaimEdge>,
    verdicts: HashMap<String, ClaimVerdict>,
    provider_by_claim: HashMap<String, String>,
}

impl EvidenceGraph {
    pub fn new() -> Self {
        Self::default()
    }

    /// Ingests a complete `EvidenceBundle` into the graph.
    pub fn ingest_bundle(&mut self, bundle: &EvidenceBundle) {
        let provider_id = bundle.provider.provider_id.clone();
        for claim in &bundle.claims {
            self.claims.insert(claim.claim_id.clone(), claim.clone());
            self.provider_by_claim.insert(claim.claim_id.clone(), provider_id.clone());
        }
    }

    /// Connects two claims with a typed relationship edge.
    /// Enforces Anti-Self-Certification: A provider cannot create SUPPORTS edges to its own claims.
    pub fn add_edge(
        &mut self,
        source_claim_id: &str,
        target_claim_id: &str,
        relationship: ClaimRelationship,
    ) -> Result<(), V8CoreError> {
        if !self.claims.contains_key(source_claim_id) {
            return Err(V8CoreError::TraceLineageError(format!(
                "Source claim {source_claim_id} not found in EvidenceGraph"
            )));
        }
        if !self.claims.contains_key(target_claim_id) {
            return Err(V8CoreError::TraceLineageError(format!(
                "Target claim {target_claim_id} not found in EvidenceGraph"
            )));
        }

        // Anti-Self-Certification rule
        let src_prov = &self.provider_by_claim[source_claim_id];
        let tgt_prov = &self.provider_by_claim[target_claim_id];
        if relationship == ClaimRelationship::Supports && src_prov == tgt_prov {
            return Err(V8CoreError::TraceLineageError(format!(
                "Anti-Self-Certification Violation: Provider {src_prov} cannot certify claim {target_claim_id}"
            )));
        }

        self.edges.push(ClaimEdge {
            source_claim_id: source_claim_id.to_string(),
            target_claim_id: target_claim_id.to_string(),
            relationship,
            weight: None,
        });

        Ok(())
    }

    /// Adjudicates all claims in the graph.
    pub fn adjudicate(&mut self) {
        for (claim_id, claim) in &self.claims {
            let challenges = self.edges.iter().filter(|e| e.target_claim_id == *claim_id && e.relationship == ClaimRelationship::Challenges).count();
            let supports = self.edges.iter().filter(|e| e.target_claim_id == *claim_id && e.relationship == ClaimRelationship::Supports).count();
            let invalidates = self.edges.iter().filter(|e| e.target_claim_id == *claim_id && e.relationship == ClaimRelationship::Invalidates).count();

            let verdict = if invalidates > 0 {
                ClaimVerdict::Falsified
            } else if challenges > 0 && supports > 0 {
                ClaimVerdict::Contested
            } else if challenges > 0 && supports == 0 {
                ClaimVerdict::Falsified
            } else if supports > 0 || !claim.is_pathology {
                ClaimVerdict::Supported
            } else {
                ClaimVerdict::InsufficientEvidence
            };

            self.verdicts.insert(claim_id.clone(), verdict);
        }
    }

    pub fn get_verdict(&self, claim_id: &str) -> Option<ClaimVerdict> {
        self.verdicts.get(claim_id).copied()
    }

    pub fn all_claims(&self) -> &HashMap<String, EvidenceClaim> {
        &self.claims
    }

    pub fn verdicts(&self) -> &HashMap<String, ClaimVerdict> {
        &self.verdicts
    }

    pub fn edges(&self) -> &[ClaimEdge] {
        &self.edges
    }
}
