//! Typestate Execution Mandate & Capability Scoping (D-134, Rule 36, Rule 40, Rule 41).

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use crate::hash::Canon;

/// Risk-Weighted Mobilization Tier (Rule 40, Amendment A3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum MobilizationTier {
    /// Tier 0 (Routine): Typo, docs, trivial deterministic test.
    Tier0Routine = 0,
    /// Tier 1 (Material): New module, semantic change, risk/utility/evidence logic.
    Tier1Material = 1,
    /// Tier 2 (Constitutional/Economic): Core authority, simulator, cashflow, G4/G5 succession.
    Tier2Constitutional = 2,
}

/// Time and resource lease bound to a single task execution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TaskLease {
    pub lease_id: String,
    pub task_id: String,
    pub issued_at_utc: i64,
    pub expires_at_utc: i64,
    pub token_budget_ceiling: u64,
}

impl TaskLease {
    pub fn is_valid(&self, current_time_utc: i64) -> bool {
        current_time_utc >= self.issued_at_utc && current_time_utc <= self.expires_at_utc
    }
}

/// Permitted and forbidden semantic mutation classes for an execution mandate.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SemanticChangeClass {
    DocumentationOnly,
    BugFix,
    Refactoring,
    AuthorityHardening,
    EconomicThresholdTuning, // STRICTLY FORBIDDEN during hotfixes
    WitnessHabitatModification,
    UtilityHurdleAdjustment,
}

/// Strongly-typed Execution Mandate governing every agent's operational scope (Rule 36, Rule 41).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionMandate {
    pub mandate_id: String,
    pub decision_id: String,
    pub tier: MobilizationTier,
    pub execution_owner: String,
    pub permitted_modules: Vec<String>,
    pub permitted_changes: Vec<SemanticChangeClass>,
    pub forbidden_changes: Vec<SemanticChangeClass>,
    pub constitution_tree_hash: String,
    pub baseline_commit: String,
    pub lease: TaskLease,
}

impl ExecutionMandate {
    /// Computes cryptographic 256-bit BLAKE3 identity for ExecutionMandate.
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("ExecutionMandate");
        c.push_str(&self.decision_id);
        c.push_str(&format!("{:?}", self.tier));
        c.push_str(&self.execution_owner);
        c.push_str(&self.constitution_tree_hash);
        c.push_str(&self.baseline_commit);
        c.push_str(&self.lease.lease_id);
        c.push_u64(self.lease.token_budget_ceiling);

        c.push_list();
        c.push_count(self.permitted_modules.len());
        for m in &self.permitted_modules {
            c.push_str(m);
        }

        c.finish_blake3_hex()
    }

    /// Asserts whether a target module path is within the permitted scope.
    pub fn assert_module_permitted(&self, target_module: &str) -> Result<(), String> {
        let normalized = target_module.replace('\\', "/");
        if !self.permitted_modules.iter().any(|m| normalized.starts_with(m)) {
            return Err(format!(
                "MANDATE_SCOPE_VIOLATION: Target module '{target_module}' is not authorized under mandate '{}'",
                self.mandate_id
            ));
        }
        Ok(())
    }

    /// Asserts whether a semantic change class is authorized.
    pub fn assert_change_permitted(&self, change: &SemanticChangeClass) -> Result<(), String> {
        if self.forbidden_changes.contains(change) {
            return Err(format!(
                "MANDATE_FORBIDDEN_MUTATION: Semantic change '{change:?}' is explicitly forbidden under mandate '{}'",
                self.mandate_id
            ));
        }
        if !self.permitted_changes.contains(change) {
            return Err(format!(
                "MANDATE_UNAUTHORIZED_MUTATION: Semantic change '{change:?}' is not permitted under mandate '{}'",
                self.mandate_id
            ));
        }
        Ok(())
    }

    /// Asserts that the runtime constitution hash matches the pinned constitution at checkout (Amendment A4).
    pub fn assert_constitution_unmodified(&self, current_constitution_hash: &str) -> Result<(), String> {
        if self.constitution_tree_hash != current_constitution_hash {
            return Err(format!(
                "CONSTITUTION_TREE_HASH_DRIFT: Mandate pinned '{}', but runtime is '{}'",
                self.constitution_tree_hash, current_constitution_hash
            ));
        }
        Ok(())
    }
}
