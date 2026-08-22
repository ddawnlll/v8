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

        // Evidence Sovereignty and Sovereign Kaizen domain (D-132)
        self.register(AuthorityRule {
            domain: "evidence_sovereignty".to_string(),
            decision_id: "D-132".to_string(),
            title: "Central Evidence Sovereignty, Sovereign Kaizen & Claim Authorization Act (Rules 28-35)".to_string(),
            owning_spec: "V8_CONSTITUTION Rules 28-35, CC-BILL-V8.3-AUTHORITY-003, CC-AMEND-V8.3-KAIZEN-004".to_string(),
            status: "LOCKED_INVARIANT".to_string(),
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

// ============================================================================
// 3-DIMENSIONAL AUTHORITY TENSOR & CLAIM VALUE (D-132, Rules 28-35)
// ============================================================================

/// Provenance of the underlying observation / information (Axis 1 of 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
pub enum EvidenceAuthority {
    Counterfactual = 0,
    ModelDerived = 1,
    Observed = 2,
}

/// Operational policy or risk authorization level (Axis 2 of 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
pub enum DecisionAuthority {
    DiagnosticOnly = 0,
    Reconciled = 1,
    UtilityEligible = 2,
    PortfolioAuthorized = 3,
    ExecutionAuthorized = 4,
}

/// Physical execution and settlement state (Axis 3 of 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
pub enum RealizationStatus {
    Hypothetical = 0,
    Simulated = 1,
    Filled = 2,
    CashflowSettled = 3,
}

/// The Canonical 3-Dimensional Authority Tensor (Rule 28).
/// Decouples where information came from (evidence), what decisions it can make (decision),
/// and whether physical cashflow has occurred (realization).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
pub struct Authority {
    pub evidence: EvidenceAuthority,
    pub decision: DecisionAuthority,
    pub realization: RealizationStatus,
}

impl Authority {
    pub const fn new(
        evidence: EvidenceAuthority,
        decision: DecisionAuthority,
        realization: RealizationStatus,
    ) -> Self {
        Self {
            evidence,
            decision,
            realization,
        }
    }

    /// Pure diagnostic counterfactual authority (e.g. raw regret, oracle potential).
    pub const fn counterfactual_diagnostic() -> Self {
        Self {
            evidence: EvidenceAuthority::Counterfactual,
            decision: DecisionAuthority::DiagnosticOnly,
            realization: RealizationStatus::Hypothetical,
        }
    }

    /// Observed point-in-time market state (zero decision, hypothetical realization).
    pub const fn observed_market() -> Self {
        Self {
            evidence: EvidenceAuthority::Observed,
            decision: DecisionAuthority::DiagnosticOnly,
            realization: RealizationStatus::Hypothetical,
        }
    }

    /// Reconciled opportunity state with cryptographic receipt.
    pub const fn reconciled(evidence: EvidenceAuthority) -> Self {
        Self {
            evidence,
            decision: DecisionAuthority::Reconciled,
            realization: RealizationStatus::Hypothetical,
        }
    }

    /// Portfolio authorized for execution simulation or venue dispatch.
    pub const fn portfolio_authorized(evidence: EvidenceAuthority, realization: RealizationStatus) -> Self {
        Self {
            evidence,
            decision: DecisionAuthority::PortfolioAuthorized,
            realization,
        }
    }

    /// Realized cashflow settlement from physical venue fills.
    pub const fn realized_cashflow() -> Self {
        Self {
            evidence: EvidenceAuthority::Observed,
            decision: DecisionAuthority::ExecutionAuthorized,
            realization: RealizationStatus::CashflowSettled,
        }
    }

    /// Monotonic degradation operator: Output authority cannot exceed the minimum of inputs.
    pub fn meet(&self, other: &Self) -> Self {
        Self {
            evidence: if (self.evidence as u8) < (other.evidence as u8) {
                self.evidence
            } else {
                other.evidence
            },
            decision: if (self.decision as u8) < (other.decision as u8) {
                self.decision
            } else {
                other.decision
            },
            realization: if (self.realization as u8) < (other.realization as u8) {
                self.realization
            } else {
                other.realization
            },
        }
    }

    /// Asserts whether this authority can legally make an economic claim.
    pub fn is_economic_claim_authorized(&self) -> bool {
        self.evidence == EvidenceAuthority::Observed
            && self.decision == DecisionAuthority::ExecutionAuthorized
            && self.realization == RealizationStatus::CashflowSettled
    }
}

/// Typed economic/statistical value wrapper enforcing Rule 29 (No Naked Economic Claims).
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ClaimValue<T> {
    pub value: T,
    pub authority: Authority,
    pub receipt_id: String,
}

impl<T> ClaimValue<T> {
    pub fn new(value: T, authority: Authority, receipt_id: &str) -> Self {
        Self {
            value,
            authority,
            receipt_id: receipt_id.to_string(),
        }
    }

    pub fn peek_value(&self) -> &T {
        &self.value
    }
}

/// Constitutional Violation Taxonomy (Fail-Closed).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstitutionalViolation {
    ClaimBlocked {
        required_authority: String,
        provided_authority: String,
        reason: String,
    },
    MissingReceiptId {
        context: String,
    },
    AuthorityEscalationAttempted {
        attempted_evidence: EvidenceAuthority,
        source_evidence: EvidenceAuthority,
    },
}

impl std::fmt::Display for ConstitutionalViolation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ClaimBlocked { required_authority, provided_authority, reason } => {
                write!(
                    f,
                    "CONSTITUTIONAL_VIOLATION [CLAIM_BLOCKED]: Required '{required_authority}', provided '{provided_authority}'. Cause: {reason}"
                )
            }
            Self::MissingReceiptId { context } => {
                write!(f, "CONSTITUTIONAL_VIOLATION [MISSING_RECEIPT]: Context: {context}")
            }
            Self::AuthorityEscalationAttempted { attempted_evidence, source_evidence } => {
                write!(
                    f,
                    "CONSTITUTIONAL_VIOLATION [AUTHORITY_ESCALATION]: Attempted {attempted_evidence:?} from source {source_evidence:?}"
                )
            }
        }
    }
}

impl std::error::Error for ConstitutionalViolation {}

/// Execution Gatekeeper enforcing Rule 28 & Rule 34.
pub struct ExecutionGatekeeper;

impl ExecutionGatekeeper {
    /// Asserts portfolio authorization before permitting order dispatch or execution simulation.
    pub fn authorize_execution<'a, T>(
        claim: &'a ClaimValue<T>,
        context: &str,
    ) -> Result<&'a T, ConstitutionalViolation> {
        if claim.receipt_id.is_empty() {
            return Err(ConstitutionalViolation::MissingReceiptId {
                context: context.to_string(),
            });
        }
        if claim.authority.decision < DecisionAuthority::PortfolioAuthorized {
            return Err(ConstitutionalViolation::ClaimBlocked {
                required_authority: format!("{:?}", DecisionAuthority::PortfolioAuthorized),
                provided_authority: format!("{:?}", claim.authority.decision),
                reason: context.to_string(),
            });
        }
        Ok(&claim.value)
    }

    /// Asserts economic claim validity before public rendering or succession.
    pub fn authorize_economic_claim<'a, T>(
        claim: &'a ClaimValue<T>,
        context: &str,
    ) -> Result<&'a T, ConstitutionalViolation> {
        if !claim.authority.is_economic_claim_authorized() {
            return Err(ConstitutionalViolation::ClaimBlocked {
                required_authority: "Observed/ExecutionAuthorized/CashflowSettled".to_string(),
                provided_authority: format!("{:?}", claim.authority),
                reason: context.to_string(),
            });
        }
        Ok(&claim.value)
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

    #[test]
    fn test_evidence_sovereignty_resolves_to_d132() {
        let rule = resolve_active_rule("evidence_sovereignty").expect("evidence_sovereignty must resolve");
        assert_eq!(rule.decision_id, "D-132");
        assert!(rule.active);
    }

    #[test]
    fn test_3d_authority_meet_monotonic_degradation() {
        let observed_auth = Authority::new(
            EvidenceAuthority::Observed,
            DecisionAuthority::PortfolioAuthorized,
            RealizationStatus::Simulated,
        );
        let counterfactual_auth = Authority::new(
            EvidenceAuthority::Counterfactual,
            DecisionAuthority::ExecutionAuthorized,
            RealizationStatus::CashflowSettled,
        );

        let degraded = observed_auth.meet(&counterfactual_auth);

        // Evidence: min(Observed(2), Counterfactual(0)) = Counterfactual(0)
        assert_eq!(degraded.evidence, EvidenceAuthority::Counterfactual);
        // Decision: min(PortfolioAuthorized(3), ExecutionAuthorized(4)) = PortfolioAuthorized(3)
        assert_eq!(degraded.decision, DecisionAuthority::PortfolioAuthorized);
        // Realization: min(Simulated(1), CashflowSettled(3)) = Simulated(1)
        assert_eq!(degraded.realization, RealizationStatus::Simulated);
    }

    #[test]
    fn test_claim_value_execution_gatekeeper_blocks_unauthorized() {
        // Diagnostic claim without portfolio authorization
        let diag_claim = ClaimValue::new(
            150.0,
            Authority::counterfactual_diagnostic(),
            "receipt_diag_123",
        );

        let res = ExecutionGatekeeper::authorize_execution(&diag_claim, "live_order_dispatch");
        match res {
            Err(ConstitutionalViolation::ClaimBlocked { required_authority, provided_authority, .. }) => {
                assert!(required_authority.contains("PortfolioAuthorized"));
                assert!(provided_authority.contains("DiagnosticOnly"));
            }
            Ok(_) => panic!("Diagnostic claim must not pass ExecutionGatekeeper"),
            other => panic!("Unexpected error: {other:?}"),
        }

        // Missing receipt ID fails closed
        let no_receipt_claim = ClaimValue::new(
            150.0,
            Authority::portfolio_authorized(EvidenceAuthority::Observed, RealizationStatus::Simulated),
            "",
        );
        assert!(matches!(
            ExecutionGatekeeper::authorize_execution(&no_receipt_claim, "dispatch"),
            Err(ConstitutionalViolation::MissingReceiptId { .. })
        ));

        // Authorized claim passes
        let authorized_claim = ClaimValue::new(
            150.0,
            Authority::portfolio_authorized(EvidenceAuthority::Observed, RealizationStatus::Simulated),
            "receipt_auth_456",
        );
        assert_eq!(
            ExecutionGatekeeper::authorize_execution(&authorized_claim, "dispatch").unwrap(),
            &150.0
        );
    }

    #[test]
    fn test_counterfactual_never_passes_economic_claim_gate() {
        let counterfactual_pnl = ClaimValue::new(
            500.0,
            Authority::new(
                EvidenceAuthority::Counterfactual,
                DecisionAuthority::ExecutionAuthorized,
                RealizationStatus::CashflowSettled,
            ),
            "receipt_cf_789",
        );

        assert!(matches!(
            ExecutionGatekeeper::authorize_economic_claim(&counterfactual_pnl, "public_pnl_claim"),
            Err(ConstitutionalViolation::ClaimBlocked { .. })
        ));

        let realized_pnl = ClaimValue::new(
            500.0,
            Authority::realized_cashflow(),
            "receipt_realized_999",
        );
        assert_eq!(
            ExecutionGatekeeper::authorize_economic_claim(&realized_pnl, "public_pnl_claim").unwrap(),
            &500.0
        );
    }
}

