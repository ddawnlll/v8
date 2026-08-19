//! Support classifier and evaluability validation (TARGET_ORACLE_SPEC §5.7,
//! §8, §16.2).
//!
//! Evaluates whether candidate/action pairs are supported by declared data,
//! execution, and environment models without fabricating point estimates.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

use crate::hash::Canon;
use crate::regret::Action;

use super::authority::CounterfactualAuthority;
use super::opportunity::GrammarCandidate;
use super::taxonomy::{AuthorityLevel, Identifiability, OracleRefusal};

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct SupportRule {
    pub rule_id: String,
    pub environment_model_id: String,
    pub max_allowed_authority: AuthorityLevel,
    pub min_future_horizon_bars: usize,
    pub allowed_actions: Vec<String>,
    pub allows_model_counterfactuals: bool,
    pub assumptions: Vec<String>,
}

impl SupportRule {
    pub fn identity(&self) -> String {
        let mut c = Canon::new();
        c.push_str("support-rule-v1");
        c.push_value(&serde_json::json!({
            "rule_id": self.rule_id,
            "environment_model_id": self.environment_model_id,
            "max_allowed_authority": format!("{:?}", self.max_allowed_authority),
            "min_future_horizon_bars": self.min_future_horizon_bars,
            "allowed_actions": self.allowed_actions,
            "allows_model_counterfactuals": self.allows_model_counterfactuals,
            "assumptions": self.assumptions,
        }));
        c.finish_sha1_hex()
    }
}

pub struct SupportClassifier {
    pub rule: SupportRule,
}

impl SupportClassifier {
    pub fn new(rule: SupportRule) -> Self {
        Self { rule }
    }

    pub fn canonical_l1() -> Self {
        Self {
            rule: SupportRule {
                rule_id: "canonical-l1-support-v1".to_string(),
                environment_model_id: "binance-usdt-perp-l1".to_string(),
                max_allowed_authority: AuthorityLevel::L1,
                min_future_horizon_bars: 1,
                allowed_actions: vec![
                    "NO_TRADE".to_string(),
                    "ACTUAL".to_string(),
                    "GEOMETRY_VARIANT".to_string(),
                ],
                allows_model_counterfactuals: false,
                assumptions: vec![
                    "L1_BAR_CLOSE_FILL".to_string(),
                    "STATIC_SPREAD_FEE".to_string(),
                    "NO_ENDOGENOUS_IMPACT".to_string(),
                ],
            },
        }
    }

    /// Classify candidate and action support under requested authority level.
    pub fn classify(
        &self,
        candidate: &GrammarCandidate,
        action: &Action,
        requested_authority: AuthorityLevel,
    ) -> CounterfactualAuthority {
        let (auth, _) = self.evaluate_support(candidate, action, requested_authority, None);
        auth
    }

    /// Full evaluation returning orthogonal CounterfactualAuthority and optional OracleRefusal.
    pub fn evaluate_support(
        &self,
        candidate: &GrammarCandidate,
        action: &Action,
        requested_authority: AuthorityLevel,
        future_bars_available: Option<usize>,
    ) -> (CounterfactualAuthority, Option<OracleRefusal>) {
        // 1. Authority Level Check: L1 cannot support L2/L3 claims
        let authority_exceeded = matches!(
            (self.rule.max_allowed_authority, requested_authority),
            (AuthorityLevel::L1, AuthorityLevel::L2)
                | (AuthorityLevel::L1, AuthorityLevel::L3)
                | (AuthorityLevel::L1, AuthorityLevel::LiveReceipt)
                | (AuthorityLevel::L2, AuthorityLevel::L3)
                | (AuthorityLevel::L2, AuthorityLevel::LiveReceipt)
                | (AuthorityLevel::L3, AuthorityLevel::LiveReceipt)
        );

        if authority_exceeded {
            let mut assumptions = self.rule.assumptions.clone();
            assumptions.push("REQUESTED_AUTHORITY_EXCEEDS_SUPPORTED_MODEL".to_string());
            let auth = CounterfactualAuthority::new(
                requested_authority,
                Identifiability::NotIdentifiable,
                &self.rule.rule_id,
                &self.rule.environment_model_id,
                assumptions,
            );
            return (auth, Some(OracleRefusal::ExecutionAuthorityTooWeak));
        }

        // 2. Decision Time Data Check
        if candidate.decision_time < 0 {
            let auth = CounterfactualAuthority::new(
                requested_authority,
                Identifiability::NotIdentifiable,
                &self.rule.rule_id,
                &self.rule.environment_model_id,
                self.rule.assumptions.clone(),
            );
            return (auth, Some(OracleRefusal::MissingDecisionTimeData));
        }

        // 3. Action Kind Support
        if !self.rule.allowed_actions.iter().any(|a| a == action.kind || a == action.provenance) {
            let auth = CounterfactualAuthority::new(
                requested_authority,
                Identifiability::NotIdentifiable,
                &self.rule.rule_id,
                &self.rule.environment_model_id,
                self.rule.assumptions.clone(),
            );
            return (auth, Some(OracleRefusal::OutOfSupportAction));
        }

        // 4. Action Parameters & Fill Feasibility
        if let Some(size) = action.override_geom.get("size").and_then(|v| v.as_f64()) {
            if size <= 0.0 || !size.is_finite() {
                let auth = CounterfactualAuthority::new(
                    requested_authority,
                    Identifiability::NotIdentifiable,
                    &self.rule.rule_id,
                    &self.rule.environment_model_id,
                    self.rule.assumptions.clone(),
                );
                return (auth, Some(OracleRefusal::OutOfSupportAction));
            }
        }

        if action.override_geom.contains_key("queue_priority")
            || action.override_geom.contains_key("partial_fill_ratio")
        {
            // Queue and partial fill mechanisms require unobserved microstructure at L1
            let auth = CounterfactualAuthority::new(
                requested_authority,
                Identifiability::NotIdentifiable,
                &self.rule.rule_id,
                &self.rule.environment_model_id,
                self.rule.assumptions.clone(),
            );
            return (auth, Some(OracleRefusal::NonIdentifiableFill));
        }

        // 5. Future Horizon Check
        let expiry = action
            .override_geom
            .get("expiry_bars")
            .and_then(|v| v.as_u64())
            .map(|n| n as usize)
            .unwrap_or(self.rule.min_future_horizon_bars);

        if let Some(available) = future_bars_available {
            if available < expiry || available < self.rule.min_future_horizon_bars {
                let auth = CounterfactualAuthority::new(
                    requested_authority,
                    Identifiability::NotIdentifiable,
                    &self.rule.rule_id,
                    &self.rule.environment_model_id,
                    self.rule.assumptions.clone(),
                );
                return (auth, Some(OracleRefusal::UndefinedFuture));
            }
        }

        // 6. Model-only Counterfactual Check
        if action.override_geom.contains_key("model_counterfactual")
            && !self.rule.allows_model_counterfactuals
        {
            let auth = CounterfactualAuthority::new(
                requested_authority,
                Identifiability::ModelDerived,
                &self.rule.rule_id,
                &self.rule.environment_model_id,
                self.rule.assumptions.clone(),
            );
            return (auth, Some(OracleRefusal::ModelOnlyCounterfactual));
        }

        // 7. Fully Supported
        let auth = CounterfactualAuthority::new(
            requested_authority,
            Identifiability::Identified,
            &self.rule.rule_id,
            &self.rule.environment_model_id,
            self.rule.assumptions.clone(),
        );
        (auth, None)
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use super::*;
    use crate::oracle::opportunity::Direction;

    fn sample_candidate(decision_time: i64) -> GrammarCandidate {
        GrammarCandidate {
            grammar_candidate_id: "test-cand-01".to_string(),
            universe_id: "universe-v1".to_string(),
            template_id: "template-breakout".to_string(),
            instrument: "BTCUSDT".to_string(),
            timeframe: "1h".to_string(),
            direction: Direction::Long,
            decision_time,
            parameters: BTreeMap::new(),
        }
    }

    fn sample_action() -> Action {
        Action {
            action_id: "ACTUAL".to_string(),
            kind: "ACTUAL",
            provenance: "ACTUAL",
            override_geom: serde_json::Map::new(),
        }
    }

    #[test]
    fn l1_request_for_l3_returns_execution_authority_too_weak_and_not_identifiable() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = sample_candidate(100);
        let action = sample_action();

        let (auth, refusal) = classifier.evaluate_support(
            &candidate,
            &action,
            AuthorityLevel::L3,
            Some(10),
        );
        assert_eq!(auth.oracle_authority_level, AuthorityLevel::L3);
        assert_eq!(auth.identifiability_status, Identifiability::NotIdentifiable);
        assert_eq!(refusal, Some(OracleRefusal::ExecutionAuthorityTooWeak));
    }

    #[test]
    fn future_or_negative_decision_time_returns_missing_decision_time_data() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = sample_candidate(-1);
        let action = sample_action();

        let (auth, refusal) = classifier.evaluate_support(
            &candidate,
            &action,
            AuthorityLevel::L1,
            Some(10),
        );
        assert_eq!(auth.identifiability_status, Identifiability::NotIdentifiable);
        assert_eq!(refusal, Some(OracleRefusal::MissingDecisionTimeData));
    }

    #[test]
    fn unsupported_size_or_queue_fill_fails_support() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = sample_candidate(100);

        let mut bad_size_action = sample_action();
        bad_size_action
            .override_geom
            .insert("size".to_string(), serde_json::json!(-1.0));

        let (_, refusal1) = classifier.evaluate_support(
            &candidate,
            &bad_size_action,
            AuthorityLevel::L1,
            Some(10),
        );
        assert_eq!(refusal1, Some(OracleRefusal::OutOfSupportAction));

        let mut queue_action = sample_action();
        queue_action
            .override_geom
            .insert("queue_priority".to_string(), serde_json::json!(1));

        let (_, refusal2) = classifier.evaluate_support(
            &candidate,
            &queue_action,
            AuthorityLevel::L1,
            Some(10),
        );
        assert_eq!(refusal2, Some(OracleRefusal::NonIdentifiableFill));
    }

    #[test]
    fn insufficient_future_horizon_returns_undefined_future() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = sample_candidate(100);
        let mut action = sample_action();
        action
            .override_geom
            .insert("expiry_bars".to_string(), serde_json::json!(24));

        let (auth, refusal) = classifier.evaluate_support(
            &candidate,
            &action,
            AuthorityLevel::L1,
            Some(5), // only 5 bars available < 24
        );
        assert_eq!(auth.identifiability_status, Identifiability::NotIdentifiable);
        assert_eq!(refusal, Some(OracleRefusal::UndefinedFuture));
    }

    #[test]
    fn model_only_counterfactual_returns_model_only_refusal() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = sample_candidate(100);
        let mut action = sample_action();
        action
            .override_geom
            .insert("model_counterfactual".to_string(), serde_json::json!(true));

        let (auth, refusal) = classifier.evaluate_support(
            &candidate,
            &action,
            AuthorityLevel::L1,
            Some(10),
        );
        assert_eq!(auth.identifiability_status, Identifiability::ModelDerived);
        assert_eq!(refusal, Some(OracleRefusal::ModelOnlyCounterfactual));
    }
}
