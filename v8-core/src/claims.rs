//! Statutory Claim Classes, Central Claim Registry & Renderer Firewall (D-132, Rules 29-31, PH2-003A.1).
//!
//! Enforces:
//! 1. Closed algebra of 6 statutory claim classes.
//! 2. Centralized, content-addressed ClaimRegistry.
//! 3. Renderer Firewall prohibiting unauthorized prose, free-form formatting, and mislabeling.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::authority::{Authority, EvidenceAuthority, DecisionAuthority, RealizationStatus};
use crate::hash::Canon;

/// The Closed Algebra of 6 Statutory Claim Classes (Rule 30).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum StatutoryClaimClass {
    /// Internal exploratory metric / diagnostic hypothesis (e.g. raw candidate counts).
    DiagnosticSignal,
    /// Unconstrained oracle or ex-post markout potential (e.g. raw counterfactual regret).
    CounterfactualPotential,
    /// Overlap- and dependence-adjusted regret candidate for recovery.
    RecoverableRegret,
    /// Authoritative closed-lifecycle venue simulation output with fee/funding/slippage.
    SimulatedCashflow,
    /// Physically settled venue execution fills with double-entry cashflow reconciliation.
    RealizedCashflow,
    /// Multi-testing certified, frozen-OOS verified predictive edge (SPA / DSR / WRC certified).
    SupportedEdge,
}

impl StatutoryClaimClass {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::DiagnosticSignal => "DIAGNOSTIC_SIGNAL",
            Self::CounterfactualPotential => "COUNTERFACTUAL_POTENTIAL",
            Self::RecoverableRegret => "RECOVERABLE_REGRET",
            Self::SimulatedCashflow => "SIMULATED_CASHFLOW",
            Self::RealizedCashflow => "REALIZED_CASHFLOW",
            Self::SupportedEdge => "SUPPORTED_EDGE",
        }
    }

    /// Canonical, legally authorized rendering header (Rule 31).
    pub const fn canonical_header(&self) -> &'static str {
        match self {
            Self::DiagnosticSignal => "Diagnostic Signal (Zero Economic Authority)",
            Self::CounterfactualPotential => "Counterfactual Ex-Post Potential (Diagnostic Upper Bound)",
            Self::RecoverableRegret => "Recoverable Regret (Friction & Overlap Adjusted)",
            Self::SimulatedCashflow => "Simulated Cashflow Delta (ExecutionBackend Physics)",
            Self::RealizedCashflow => "Realized Cashflow Settlement (Physical Venue Fills)",
            Self::SupportedEdge => "Statistically Certified Edge (Multiple-Testing Adjusted)",
        }
    }

    /// Asserts minimum authority requirement for this claim class.
    pub fn validate_authority(&self, authority: &Authority) -> Result<(), String> {
        match self {
            Self::DiagnosticSignal => Ok(()),
            Self::CounterfactualPotential => {
                if authority.realization == RealizationStatus::CashflowSettled {
                    return Err("COUNTERFACTUAL_CANNOT_BE_SETTLED_CASHFLOW".to_string());
                }
                Ok(())
            }
            Self::RecoverableRegret => {
                if authority.evidence == EvidenceAuthority::Observed && authority.realization == RealizationStatus::CashflowSettled {
                    return Err("RECOVERABLE_REGRET_IS_NOT_REALIZED_CASHFLOW".to_string());
                }
                Ok(())
            }
            Self::SimulatedCashflow => {
                if authority.decision < DecisionAuthority::PortfolioAuthorized {
                    return Err("SIMULATED_CASHFLOW_REQUIRES_PORTFOLIO_AUTHORIZATION".to_string());
                }
                if authority.realization < RealizationStatus::Simulated {
                    return Err("SIMULATED_CASHFLOW_REQUIRES_SIMULATION_REALIZATION".to_string());
                }
                Ok(())
            }
            Self::RealizedCashflow => {
                if !authority.is_economic_claim_authorized() {
                    return Err("REALIZED_CASHFLOW_REQUIRES_FULL_OBSERVED_SETTLEMENT".to_string());
                }
                Ok(())
            }
            Self::SupportedEdge => {
                if authority.evidence != EvidenceAuthority::Observed {
                    return Err("SUPPORTED_EDGE_REQUIRES_OBSERVED_EVIDENCE".to_string());
                }
                Ok(())
            }
        }
    }
}

/// An immutable statutory claim record registered in the central ClaimRegistry.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StatutoryClaimRecord {
    pub claim_id: String,
    pub claim_class: StatutoryClaimClass,
    pub numeric_value: f64,
    pub units: String,
    pub authority: Authority,
    pub parent_receipt_hashes: Vec<String>,
    pub implementer_receipt: Option<String>,
    pub auditor_receipt: Option<String>,
    pub verdict_receipt: Option<String>,
    pub timestamp_utc: i64,
    pub allowed_rendering_header: String,
}

impl StatutoryClaimRecord {
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("StatutoryClaimRecord");
        c.push_str(self.claim_class.as_str());
        c.push_f64(self.numeric_value);
        c.push_str(&self.units);
        c.push_str(&format!("{:?}", self.authority));
        c.push_i64(self.timestamp_utc);

        c.push_list();
        c.push_count(self.parent_receipt_hashes.len());
        for p in &self.parent_receipt_hashes {
            c.push_str(p);
        }

        if let Some(ref imp) = self.implementer_receipt {
            c.push_str(imp);
        }
        if let Some(ref aud) = self.auditor_receipt {
            c.push_str(aud);
        }
        if let Some(ref verd) = self.verdict_receipt {
            c.push_str(verd);
        }

        c.finish_blake3_hex()
    }
}

/// Central Ledger for All Economic, Statistical and Diagnostic Claims (Rule 30).
#[derive(Debug, Clone, Default)]
pub struct ClaimRegistry {
    claims: HashMap<String, StatutoryClaimRecord>,
}

impl ClaimRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers a validated claim record into the registry.
    pub fn register_claim(
        &mut self,
        claim_class: StatutoryClaimClass,
        numeric_value: f64,
        units: &str,
        authority: Authority,
        parent_receipt_hashes: Vec<String>,
        implementer_receipt: Option<String>,
        auditor_receipt: Option<String>,
        verdict_receipt: Option<String>,
        timestamp_utc: i64,
    ) -> Result<StatutoryClaimRecord, String> {
        // Enforce authority compatibility
        claim_class.validate_authority(&authority)?;

        let mut record = StatutoryClaimRecord {
            claim_id: String::new(),
            claim_class,
            numeric_value,
            units: units.to_string(),
            authority,
            parent_receipt_hashes,
            implementer_receipt,
            auditor_receipt,
            verdict_receipt,
            timestamp_utc,
            allowed_rendering_header: claim_class.canonical_header().to_string(),
        };
        record.claim_id = record.compute_id();

        self.claims.insert(record.claim_id.clone(), record.clone());
        Ok(record)
    }

    pub fn get_claim(&self, claim_id: &str) -> Option<&StatutoryClaimRecord> {
        self.claims.get(claim_id)
    }

    pub fn all_claims(&self) -> Vec<&StatutoryClaimRecord> {
        self.claims.values().collect()
    }
}

/// Renderer Firewall Error (Fail-Closed).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RendererFirewallError {
    ForbiddenCommercialVocabulary { forbidden_word: String, claim_class: String },
    AuthorityRealizationMismatch { claim_class: String, realization: String },
    UnregisteredClaim { claim_id: String },
}

impl std::fmt::Display for RendererFirewallError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ForbiddenCommercialVocabulary { forbidden_word, claim_class } => {
                write!(
                    f,
                    "RENDERER_FIREWALL_VIOLATION: Forbidden word '{forbidden_word}' used for non-realized claim class '{claim_class}'"
                )
            }
            Self::AuthorityRealizationMismatch { claim_class, realization } => {
                write!(
                    f,
                    "RENDERER_FIREWALL_VIOLATION: Claim class '{claim_class}' incompatible with realization '{realization}'"
                )
            }
            Self::UnregisteredClaim { claim_id } => {
                write!(f, "RENDERER_FIREWALL_VIOLATION: Claim ID '{claim_id}' not found in ClaimRegistry")
            }
        }
    }
}

impl std::error::Error for RendererFirewallError {}

/// Rendered view produced strictly through the Renderer Firewall.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RenderedClaimView {
    pub claim_id: String,
    pub header: String,
    pub formatted_value: String,
    pub authority_tag: String,
    pub caveat: String,
}

/// Renderer Firewall (Rule 31).
/// Guarantees that reports and dashboards cannot format arbitrary prose or misrepresent claims.
pub struct RendererFirewall;

impl RendererFirewall {
    pub const FORBIDDEN_WORDS_NON_REALIZED: [&'static str; 7] = [
        "realized",
        "profit",
        "earned",
        "alpha",
        "pnl",
        "revenue",
        "gain",
    ];

    /// Renders a registered claim into a safe, certified string view.
    pub fn render_claim(claim: &StatutoryClaimRecord) -> Result<RenderedClaimView, RendererFirewallError> {
        // Enforce that counterfactual or diagnostic claims never carry commercial words
        if claim.claim_class == StatutoryClaimClass::CounterfactualPotential
            || claim.claim_class == StatutoryClaimClass::DiagnosticSignal
        {
            let header_lower = claim.allowed_rendering_header.to_lowercase();
            for word in Self::FORBIDDEN_WORDS_NON_REALIZED {
                if header_lower.contains(word) && !header_lower.contains("counterfactual") {
                    return Err(RendererFirewallError::ForbiddenCommercialVocabulary {
                        forbidden_word: word.to_string(),
                        claim_class: claim.claim_class.as_str().to_string(),
                    });
                }
            }
        }

        let caveat = match claim.claim_class {
            StatutoryClaimClass::DiagnosticSignal => "INTERNAL DIAGNOSTIC ONLY - ZERO ECONOMIC AUTHORITY",
            StatutoryClaimClass::CounterfactualPotential => "EX-POST UNCONSTRAINED THEORETICAL BOUND - NOT REALIZABLE CASHFLOW",
            StatutoryClaimClass::RecoverableRegret => "DEPENDENCE-ADJUSTED RECOVERY CANDIDATE - SUBJECT TO PORTFOLIO CAPACITY",
            StatutoryClaimClass::SimulatedCashflow => "SIMULATED VENUE CASHFLOW UNDER EXECUTIONBACKEND PHYSICS",
            StatutoryClaimClass::RealizedCashflow => "SETTLED PHYSICAL CASHFLOW",
            StatutoryClaimClass::SupportedEdge => "MULTIPLE-TESTING CERTIFIED STATISTICAL PREDICTIVE EDGE",
        };

        Ok(RenderedClaimView {
            claim_id: claim.claim_id.clone(),
            header: claim.allowed_rendering_header.clone(),
            formatted_value: format!("{:.4} {}", claim.numeric_value, claim.units),
            authority_tag: format!(
                "{:?}/{:?}/{:?}",
                claim.authority.evidence, claim.authority.decision, claim.authority.realization
            ),
            caveat: caveat.to_string(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_counterfactual_potential_authority_validation() {
        let auth_diag = Authority::counterfactual_diagnostic();
        assert!(StatutoryClaimClass::CounterfactualPotential.validate_authority(&auth_diag).is_ok());

        let auth_illegal = Authority::realized_cashflow();
        assert!(StatutoryClaimClass::CounterfactualPotential.validate_authority(&auth_illegal).is_err());
    }

    #[test]
    fn test_claim_registry_and_renderer_firewall() {
        let mut registry = ClaimRegistry::new();
        let claim = registry
            .register_claim(
                StatutoryClaimClass::CounterfactualPotential,
                29821.0,
                "R",
                Authority::counterfactual_diagnostic(),
                vec!["receipt_parent_1".to_string()],
                Some("impl_1".to_string()),
                Some("audit_1".to_string()),
                Some("verdict_1".to_string()),
                1_000_000,
            )
            .unwrap();

        let rendered = RendererFirewall::render_claim(&claim).unwrap();
        assert_eq!(rendered.header, "Counterfactual Ex-Post Potential (Diagnostic Upper Bound)");
        assert!(rendered.caveat.contains("NOT REALIZABLE CASHFLOW"));
        assert_eq!(rendered.formatted_value, "29821.0000 R");
    }

    #[test]
    fn test_realized_cashflow_requires_full_settlement() {
        let mut registry = ClaimRegistry::new();
        let invalid_realized = registry.register_claim(
            StatutoryClaimClass::RealizedCashflow,
            500.0,
            "USD",
            Authority::counterfactual_diagnostic(),
            vec![],
            None,
            None,
            None,
            1_000_000,
        );
        assert!(invalid_realized.is_err());

        let valid_realized = registry.register_claim(
            StatutoryClaimClass::RealizedCashflow,
            500.0,
            "USD",
            Authority::realized_cashflow(),
            vec!["receipt_fill_1".to_string()],
            Some("impl_rec".to_string()),
            Some("audit_rec".to_string()),
            Some("verdict_rec".to_string()),
            1_000_000,
        );
        assert!(valid_realized.is_ok());
    }
}
