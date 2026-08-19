//! In-memory, identity-bearing Oracle artifacts (TARGET_ORACLE_SPEC §17).
//!
//! O0-O1 intentionally do not serialize these into evaluation bundles.

#![allow(dead_code)]

use crate::hash::Canon;

use super::taxonomy::{AuthorityLevel, Identifiability, OracleRole, ValueNotion};

#[derive(Debug, Clone, Eq, PartialEq)]
pub struct OpportunityUniverseVersion {
    pub universe_id: String,
    pub version: String,
    pub parent_universe_id: Option<String>,
    pub instrument_universe: Vec<String>,
    pub timeframe_set: Vec<String>,
    pub information_contract_id: String,
    pub primitive_registry_hash: String,
    pub predicate_ir_version: String,
    pub behavior_template_registry_hash: String,
    pub parameter_grid_hash: String,
    pub tradability_rule_id: String,
    pub support_rule_id: String,
    pub authority_contract_id: String,
    pub search_universe_size: usize,
    pub complexity_budget: usize,
    /// Declared configuration timestamp; never filled from a wall clock.
    pub created_at: i64,
    pub code_hash: String,
    /// Detection execution mode is hash-bound because it changes the finite
    /// search frame; it has no execution simulation semantics in O1.
    pub execution_mode_id: String,
}

impl OpportunityUniverseVersion {
    pub fn identity(&self) -> String {
        let mut c = Canon::new();
        c.push_str("opportunity-universe-v1");
        c.push_value(&serde_json::json!({
            "version": self.version, "parent_universe_id": self.parent_universe_id,
            "instrument_universe": self.instrument_universe, "timeframe_set": self.timeframe_set,
            "information_contract_id": self.information_contract_id,
            "primitive_registry_hash": self.primitive_registry_hash,
            "predicate_ir_version": self.predicate_ir_version,
            "behavior_template_registry_hash": self.behavior_template_registry_hash,
            "parameter_grid_hash": self.parameter_grid_hash, "tradability_rule_id": self.tradability_rule_id,
            "support_rule_id": self.support_rule_id, "authority_contract_id": self.authority_contract_id,
            "search_universe_size": self.search_universe_size, "complexity_budget": self.complexity_budget,
            "created_at": self.created_at, "code_hash": self.code_hash,
            "execution_mode_id": self.execution_mode_id,
        }));
        c.finish_sha1_hex()
    }

    pub fn bind_identity(&mut self) {
        self.instrument_universe.sort();
        self.instrument_universe.dedup();
        self.timeframe_set.sort();
        self.timeframe_set.dedup();
        self.universe_id = self.identity();
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct OracleEvaluationRecord {
    pub evaluation_id: String,
    pub oracle_role: OracleRole,
    pub authority_level: AuthorityLevel,
    pub identifiability_status: Identifiability,
    pub information_contract_id: String,
    pub opportunity_universe_id: String,
    pub utility_contract_id: String,
    pub policy_class_id: String,
    pub cost_model_id: String,
    pub capacity_model_id: String,
    pub environment_target_id: String,
    pub candidate_population_hash: String,
    pub action_manifest_hash: String,
    pub simulator_or_receipt_hash: String,
    pub code_hash: String,
    pub config_hash: String,
    pub value_notion: ValueNotion,
    pub point_estimate: Option<f64>,
    pub lower_bound: Option<f64>,
    pub upper_bound: Option<f64>,
    pub uncertainty_artifact_id: Option<String>,
    pub refusal_reason: Option<String>,
    pub assumptions: Vec<String>,
    pub lineage_id: String,
}

impl OracleEvaluationRecord {
    pub fn identity(&self) -> String {
        let mut c = Canon::new();
        c.push_str("oracle-evaluation-record-v1");
        c.push_value(&serde_json::json!({
            "oracle_role": format!("{:?}", self.oracle_role), "authority_level": format!("{:?}", self.authority_level),
            "identifiability_status": format!("{:?}", self.identifiability_status),
            "information_contract_id": self.information_contract_id, "opportunity_universe_id": self.opportunity_universe_id,
            "utility_contract_id": self.utility_contract_id, "policy_class_id": self.policy_class_id,
            "cost_model_id": self.cost_model_id, "capacity_model_id": self.capacity_model_id,
            "environment_target_id": self.environment_target_id, "candidate_population_hash": self.candidate_population_hash,
            "action_manifest_hash": self.action_manifest_hash, "simulator_or_receipt_hash": self.simulator_or_receipt_hash,
            "code_hash": self.code_hash, "config_hash": self.config_hash, "value_notion": format!("{:?}", self.value_notion),
            "point_estimate": self.point_estimate, "lower_bound": self.lower_bound, "upper_bound": self.upper_bound,
            "uncertainty_artifact_id": self.uncertainty_artifact_id, "refusal_reason": self.refusal_reason,
            "assumptions": self.assumptions, "lineage_id": self.lineage_id,
        }));
        c.finish_sha1_hex()
    }
}
