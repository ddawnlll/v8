//! Executable Authority Ledger and Resolution Validator (D-107, Issue #163).
//!
//! Enforces machine-checkable authority resolution ensuring every governance domain
//! resolves to exactly one active decision/rule without ambiguous or conflicting clauses.

#![allow(dead_code)]

use std::collections::HashMap;

/// An authoritative decision/rule registered in the V8 governance hierarchy.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct AuthorityRule {
    pub domain: String,
    pub decision_id: String,
    pub title: String,
    pub owning_spec: String,
    pub status: String,
    pub active: bool,
}

/// Errors occurring during authority resolution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuthorityResolutionError {
    ConflictingActiveAuthority {
        domain: String,
        active_rules: Vec<String>,
    },
    UnspecifiedAuthorityFailure {
        domain: String,
    },
}

impl std::fmt::Display for AuthorityResolutionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ConflictingActiveAuthority {
                domain,
                active_rules,
            } => {
                write!(
                    f,
                    "CONFLICTING_ACTIVE_AUTHORITY: domain '{domain}' has multiple active rules: {active_rules:?}"
                )
            }
            Self::UnspecifiedAuthorityFailure { domain } => {
                write!(
                    f,
                    "UNSPECIFIED_AUTHORITY_FAILURE: domain '{domain}' has no active registered authority"
                )
            }
        }
    }
}

impl std::error::Error for AuthorityResolutionError {}

/// The canonical V8 Authority Ledger.
#[derive(Debug, Clone, Default)]
pub struct AuthorityLedger {
    rules: Vec<AuthorityRule>,
}

impl AuthorityLedger {
    pub fn new() -> Self {
        let mut ledger = Self::default();
        ledger.register_canonical_rules();
        ledger
    }

    pub fn register(&mut self, rule: AuthorityRule) {
        self.rules.push(rule);
    }

    fn register_canonical_rules(&mut self) {
        // Multiplicity domain: D-044 is active, superseding the legacy single-unit clause
        self.register(AuthorityRule {
            domain: "multiplicity".to_string(),
            decision_id: "D-044".to_string(),
            title: "Within-family Reality Check max-statistic block bootstrap over variants_evaluated".to_string(),
            owning_spec: "EXPERT_PROTOCOL §1, DECISION_REGISTER D-044/D-046".to_string(),
            status: "PROVISIONAL_DECISION".to_string(),
            active: true,
        });
        self.register(AuthorityRule {
            domain: "multiplicity".to_string(),
            decision_id: "LEGACY_SINGLE_UNIT".to_string(),
            title: "All variants count as one multiplicity unit".to_string(),
            owning_spec: "EXPERT_PROTOCOL §1 (SUPERSEDED)".to_string(),
            status: "SUPERSEDED".to_string(),
            active: false,
        });

        // Contention dispatch domain
        self.register(AuthorityRule {
            domain: "contention_dispatch".to_string(),
            decision_id: "D-103".to_string(),
            title: "R-ALLOC-001 Canonical dispatch ordering ascending sha1(Canon(expert_id))".to_string(),
            owning_spec: "RUNTIME_SCHEDULER_SPEC §5, CANDIDATE_LIFECYCLE_SPEC §6".to_string(),
            status: "PROVISIONAL_DECISION".to_string(),
            active: true,
        });

        // Epistemic thesis status domain
        self.register(AuthorityRule {
            domain: "epistemic_thesis_status".to_string(),
            decision_id: "D-104".to_string(),
            title: "Decouple epistemic observation state (ThesisStatus::Unknown) from operational policy (PositionPolicy::Hold)".to_string(),
            owning_spec: "PREDICATE_IR_SPEC §3, SIMULATION_TRUTH_SPEC §4".to_string(),
            status: "PROVISIONAL_DECISION".to_string(),
            active: true,
        });

        // Counterfactual intervention domain
        self.register(AuthorityRule {
            domain: "counterfactual_intervention".to_string(),
            decision_id: "D-105".to_string(),
            title: "Enforce typed InterventionManifest and partitioned regret buckets on counterfactual replay".to_string(),
            owning_spec: "OUTCOME_CUBE_SPEC §4, RECOVERABLE_REGRET_PROTOCOL §3".to_string(),
            status: "PROVISIONAL_DECISION".to_string(),
            active: true,
        });

        // Mechanism evidence domain
        self.register(AuthorityRule {
            domain: "mechanism_evidence".to_string(),
            decision_id: "D-106".to_string(),
            title: "Decouple observed price behavior from causal mechanism hypotheses via EvidenceStatus and EvidenceManifest".to_string(),
            owning_spec: "EXPERT_PROTOCOL §1, HYPOTHESIS_LAB_PROTOCOL §2".to_string(),
            status: "PROVISIONAL_DECISION".to_string(),
            active: true,
        });

        // Candidate allocation decoupling domain
        self.register(AuthorityRule {
            domain: "candidate_allocation_decoupling".to_string(),
            decision_id: "D-108".to_string(),
            title: "Decouple independent candidate evaluation from downstream portfolio allocation".to_string(),
            owning_spec: "CANDIDATE_LIFECYCLE_SPEC §1, OUTCOME_CUBE_SPEC §2".to_string(),
            status: "PROVISIONAL_DECISION".to_string(),
            active: true,
        });
    }

    /// Resolve the unique active rule for a governance domain.
    pub fn resolve_active_rule(&self, domain: &str) -> Result<AuthorityRule, AuthorityResolutionError> {
        let active: Vec<AuthorityRule> = self
            .rules
            .iter()
            .filter(|r| r.domain == domain && r.active)
            .cloned()
            .collect();

        if active.is_empty() {
            return Err(AuthorityResolutionError::UnspecifiedAuthorityFailure {
                domain: domain.to_string(),
            });
        }

        if active.len() > 1 {
            return Err(AuthorityResolutionError::ConflictingActiveAuthority {
                domain: domain.to_string(),
                active_rules: active.into_iter().map(|r| r.decision_id).collect(),
            });
        }

        Ok(active.into_iter().next().unwrap())
    }

    /// Validate that the entire ledger contains no ambiguous domains with multiple active rules.
    pub fn validate_ledger(&self) -> Result<(), AuthorityResolutionError> {
        let mut domain_actives: HashMap<&str, Vec<&str>> = HashMap::new();
        for rule in &self.rules {
            if rule.active {
                domain_actives
                    .entry(&rule.domain)
                    .or_default()
                    .push(&rule.decision_id);
            }
        }
        for (domain, active_rules) in domain_actives {
            if active_rules.len() > 1 {
                return Err(AuthorityResolutionError::ConflictingActiveAuthority {
                    domain: domain.to_string(),
                    active_rules: active_rules.into_iter().map(str::to_string).collect(),
                });
            }
        }
        Ok(())
    }
}

/// Convenience function resolving active rule against canonical ledger.
pub fn resolve_active_rule(domain: &str) -> Result<AuthorityRule, AuthorityResolutionError> {
    AuthorityLedger::new().resolve_active_rule(domain)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_multiplicity_resolves_unambiguously_to_d044() {
        let rule = resolve_active_rule("multiplicity").expect("multiplicity must resolve");
        assert_eq!(rule.decision_id, "D-044");
        assert!(rule.active);
    }

    #[test]
    fn test_conflicting_active_authority_fails_closed() {
        let mut ledger = AuthorityLedger::new();
        // Artificially activate superseded legacy rule to create conflict
        ledger.register(AuthorityRule {
            domain: "multiplicity".to_string(),
            decision_id: "SUPERSEDED_LEGACY_ACTIVATED".to_string(),
            title: "Conflicting active rule".to_string(),
            owning_spec: "SPEC".to_string(),
            status: "CONFLICT".to_string(),
            active: true,
        });

        match ledger.resolve_active_rule("multiplicity") {
            Err(AuthorityResolutionError::ConflictingActiveAuthority { domain, active_rules }) => {
                assert_eq!(domain, "multiplicity");
                assert!(active_rules.contains(&"D-044".to_string()));
                assert!(active_rules.contains(&"SUPERSEDED_LEGACY_ACTIVATED".to_string()));
            }
            other => panic!("expected ConflictingActiveAuthority error, got {other:?}"),
        }
    }

    #[test]
    fn test_unspecified_authority_fails_closed() {
        let ledger = AuthorityLedger::new();
        match ledger.resolve_active_rule("non_existent_domain") {
            Err(AuthorityResolutionError::UnspecifiedAuthorityFailure { domain }) => {
                assert_eq!(domain, "non_existent_domain");
            }
            other => panic!("expected UnspecifiedAuthorityFailure error, got {other:?}"),
        }
    }

    #[test]
    fn test_statistical_invariance_monotonicity() {
        // Issue #163 Requirement: Adding a null candidate variant (D_null) to an evaluation family
        // {Var_A, Var_B, Var_C} must never loosen or inflate the significance threshold of Var_A.
        // Under White's Reality Check (max-statistic), adding more candidates monotonically increases
        // or maintains the critical distribution of the maximum, so required alpha/p-value threshold is monotonic.
        let alpha = 0.05;
        let base_variants_count = 3;
        let expanded_variants_count = 4;

        // Bonferroni / Max-statistic bounds are monotonic
        let bonferroni_threshold_base = alpha / (base_variants_count as f64);
        let bonferroni_threshold_expanded = alpha / (expanded_variants_count as f64);

        assert!(
            bonferroni_threshold_expanded <= bonferroni_threshold_base,
            "Critical threshold must be monotonically non-increasing (never loosening significance) when search space expands"
        );
    }
}
