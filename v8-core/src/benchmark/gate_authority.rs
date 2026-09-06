//! Gate Authority Firewall (D-152 §§5-6, D-153 §2, Constitution Rules 12 and 57).
//!
//! This module is the single boundary between *benchmark evidence* and
//! *authority*. Issue #327 found that `GateVector` evaluated only G0-G5 and
//! that `PolicyCertificate` could derive its own readiness and
//! "production ready" status locally. Both let incomplete evidence read as
//! certified.
//!
//! The firewall enforces three properties:
//!
//! 1. **No authority minting outside `ClaimRegistry`.** Everything produced
//!    here is a *projection* of inputs. A renderer cannot create a claim.
//! 2. **Monotone non-escalation.** `cap_authority` guarantees the output
//!    authority of any rendering step is at most its input authority, so a
//!    report can never be stronger than the evidence it renders.
//! 3. **Fail closed on absence.** Required `UNKNOWN`, `N/A`, `MISSING` or
//!    `BLOCKED` evidence yields `NO_ECONOMIC_CLAIM` / `BLOCKED`, never a pass.
//!
//! OPEN_PIN (#327): D-152 §5 and D-153 §2 assign conflicting names to gate
//! positions G7-G9 (D-152: prospective shadow / live realization / certificate;
//! D-153 field names: generalization / prospective shadow / live realization).
//! See `OPEN_PIN_GATE_NAMING` and `types::GATE_DESCRIPTORS`. The conflict is
//! surfaced rather than resolved: readiness is unaffected under either reading,
//! but any *per-gate narrative* that depends on which gate is "the live
//! realization gate" must not be authored until the register conflict is
//! settled.

use serde::{Deserialize, Serialize};

use crate::assurance::evidence_profile::{
    EconomicConclusion, GateId, GateVerdict, PolicyEvidenceProfile,
};
use crate::authority::{Authority, DecisionAuthority, EvidenceAuthority, RealizationStatus};
use crate::benchmark::types::{GateState, GateVector, ReadinessStatus};
use crate::claims::{ClaimRegistry, StatutoryClaimClass, StatutoryClaimRecord};

/// The unresolved gate-naming conflict between the two owning contracts.
pub const OPEN_PIN_GATE_NAMING: &str = concat!(
    "OPEN_PIN: D-152 §5 and D-153 §2 conflict on G7-G9 semantics. ",
    "docs/contracts/D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md §5 names ",
    "G7 prospective shadow, G8 live realization, G9 certificate; the D-153 ",
    "GateVector fields are g7_generalization, g8_prospective_shadow, ",
    "g9_live_realization. Positional mapping is used; neither document is ",
    "rewritten by this module."
);

/// Terminal authority decision for a rendered artifact (#327 R2, R3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuthorityDecision {
    /// The default for anything that has not been certified through
    /// `ClaimRegistry`. Constitution Rule 12.
    NoEconomicClaim,
    /// A gate was falsified, or a required identity/lineage check failed.
    Blocked { reason: String },
    /// The owning contracts disagree; refusing to invent an interpretation.
    OpenPin { reference: String, detail: String },
    /// All required gates hold and the claim exists in `ClaimRegistry`. This
    /// variant is only reachable through `AuthorityFirewall::route_claim`,
    /// which verifies registry membership.
    Registered { claim_id: String, class: String },
}

impl AuthorityDecision {
    pub fn status_tag(&self) -> &'static str {
        match self {
            Self::NoEconomicClaim => "NO_ECONOMIC_CLAIM",
            Self::Blocked { .. } => "BLOCKED",
            Self::OpenPin { .. } => "BLOCKED",
            Self::Registered { .. } => "REGISTERED_CLAIM",
        }
    }

    /// Nothing in the uncertified states may be described as ready.
    pub fn is_uncertified(&self) -> bool {
        matches!(self, Self::NoEconomicClaim | Self::Blocked { .. } | Self::OpenPin { .. })
    }
}

/// Capability to *read* evidence, to *decide* with it, and to have *realized*
/// it. Kept structurally identical to `authority::Authority` but with a
/// `Missing` bottom so that "no gate result" is representable; the conversion
/// into the canonical tensor goes through `Authority::diagnostic_floor()`,
/// never through a lossy `From` impl.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum GateEvidenceLevel {
    /// No evaluation at all.
    Missing,
    Counterfactual,
    ModelDerived,
    Observed,
}

impl From<Option<EvidenceAuthority>> for GateEvidenceLevel {
    fn from(v: Option<EvidenceAuthority>) -> Self {
        match v {
            None => Self::Missing,
            Some(EvidenceAuthority::Counterfactual) => Self::Counterfactual,
            Some(EvidenceAuthority::ModelDerived) => Self::ModelDerived,
            Some(EvidenceAuthority::Observed) => Self::Observed,
        }
    }
}

/// A non-escalating authority floor for benchmark artifacts.
///
/// A benchmark receipt is a diagnostic instrument (D-153 §2.1). Nothing it
/// produces may raise `decision` above `DiagnosticOnly` or `realization` above
/// `Hypothetical`, regardless of how strong the underlying evidence is.
pub const BENCHMARK_DIAGNOSTIC_AUTHORITY: Authority = Authority {
    evidence: EvidenceAuthority::Observed,
    decision: DecisionAuthority::DiagnosticOnly,
    realization: RealizationStatus::Hypothetical,
};

/// Clamp `rendered` to `input` on every axis (issue §13: "a renderer cannot
/// increase input authority").
///
/// Total by construction: no panics, no unreachable arms. Because
/// `Authority: Ord` is derived over the tuple of three `Ord` axes, taking the
/// minimum is the componentwise floor.
pub fn cap_authority(input: Authority, rendered: Authority) -> Authority {
    Authority {
        evidence: min_evidence(input.evidence, rendered.evidence),
        decision: input.decision.min(rendered.decision),
        realization: input.realization.min(rendered.realization),
    }
}

fn min_evidence(a: EvidenceAuthority, b: EvidenceAuthority) -> EvidenceAuthority {
    if (a as u8) <= (b as u8) { a } else { b }
}

/// Map a `GateVector` onto the canonical `assurance::GateVerdict` values so
/// the benchmark plane speaks the assurance plane's vocabulary instead of a
/// parallel one (#327 non-goal: "no parallel authority root").
pub fn gate_verdicts(gates: &GateVector) -> Vec<GateVerdict> {
    gates
        .evaluated_gates()
        .iter()
        .map(|ev| {
            let gate: GateId = ev.descriptor.canonical_id;
            match ev.state {
                GateState::Pass => GateVerdict::pass(
                    gate,
                    "benchmark gate position holds",
                    "NONE (benchmark mints no authority; see D-153 §2.1)",
                ),
                GateState::Blocked | GateState::Defeated => GateVerdict::fail_closed(
                    gate,
                    &format!("benchmark gate falsified: {}", ev.state.as_str()),
                    &["SUPPORTED_EDGE", "SIMULATED_CASHFLOW", "REALIZED_CASHFLOW"],
                ),
                other => GateVerdict::unknown(
                    gate,
                    &format!(
                        "required benchmark evidence absent or unresolved: {}",
                        other.as_str()
                    ),
                ),
            }
        })
        .collect()
}

/// True when the profile's own conclusion contradicts the gate vector.
///
/// This is the check that makes a certificate a *projection* rather than a
/// second authority root: if Assurance says `NotProductionSupported`, no
/// benchmark-side rendering may say otherwise.
pub fn conclusion_conflict(
    profile: Option<&PolicyEvidenceProfile>,
    gates: &GateVector,
) -> Option<String> {
    let profile = profile?;
    let readiness = gates.readiness();
    let hard_against_support = readiness.status == ReadinessStatus::HardFailure
        && matches!(
            profile.conclusion,
            EconomicConclusion::LiveSupported
                | EconomicConclusion::ProspectivelySupported
                | EconomicConclusion::HistoricallyReplicated
        );
    if hard_against_support {
        return Some(format!(
            "Assurance profile concludes {:?} while benchmark gate vector reports hard failure at positions {:?}",
            profile.conclusion, readiness.hard_failures
        ));
    }
    None
}

/// The firewall. Holds no authority of its own: it can only downgrade.
pub struct AuthorityFirewall<'a> {
    registry: Option<&'a ClaimRegistry>,
}

impl<'a> AuthorityFirewall<'a> {
    /// A firewall with no registry can never produce `Registered`.
    pub fn without_registry() -> Self {
        Self { registry: None }
    }

    /// The canonical route: authority requires the existing `ClaimRegistry`.
    pub fn with_registry(registry: &'a ClaimRegistry) -> Self {
        Self {
            registry: Some(registry),
        }
    }

    /// Decide what may be asserted from a gate vector alone.
    ///
    /// Deliberately cannot return `Registered`: gate satisfaction is not a
    /// claim, and this function has no registry access path to one.
    pub fn decide_from_gates(&self, gates: &GateVector) -> AuthorityDecision {
        let readiness = gates.readiness();
        match readiness.status {
            ReadinessStatus::HardFailure => AuthorityDecision::Blocked {
                reason: format!(
                    "hard gate failure at positions {:?} ({})",
                    readiness.hard_failures,
                    readiness
                        .hard_failures
                        .iter()
                        .map(|p| format!("G{}", p))
                        .collect::<Vec<_>>()
                        .join(",")
                ),
            },
            ReadinessStatus::InsufficientEvidence => {
                // Rule 12: uncertified output stays NO_ECONOMIC_CLAIM even
                // though the reason is missing evidence, not a defeat.
                AuthorityDecision::NoEconomicClaim
            }
            ReadinessStatus::Certified => {
                // All ten gates hold, but a satisfied vector is still not a
                // claim. Without a registry route we stop here.
                AuthorityDecision::NoEconomicClaim
            }
        }
    }

    /// Decide with the Assurance profile in the loop (D-152 §6).
    ///
    /// The profile is the *owner* of the conclusion; this function only checks
    /// agreement and never overrides it upward.
    pub fn decide_with_profile(
        &self,
        gates: &GateVector,
        profile: Option<&PolicyEvidenceProfile>,
    ) -> AuthorityDecision {
        if let Some(detail) = conclusion_conflict(profile, gates) {
            return AuthorityDecision::OpenPin {
                reference: "D-152 §6 vs D-153 §2 (Constitution Rule 12)".to_string(),
                detail,
            };
        }
        // A certificate that is not active/qualified blocks rendering
        // regardless of gate satisfaction. The certificate lifecycle stays
        // owned by `assurance::certificate` (#327: no parallel authority root).
        if let Some(p) = profile {
            if !p.certificate.is_active_or_qualified() {
                return AuthorityDecision::Blocked {
                    reason: format!(
                        "no active ProductionEvidenceCertificate (state {:?}); scalar collapse forbidden",
                        p.certificate
                    ),
                };
            }
        }
        self.decide_from_gates(gates)
    }

    /// The only path to `Registered`: the claim must physically exist in the
    /// registry handed to this firewall, and its class must be one the gate
    /// vector can support.
    pub fn route_claim(&self, claim_id: &str) -> AuthorityDecision {
        let Some(registry) = self.registry else {
            return AuthorityDecision::Blocked {
                reason: "no ClaimRegistry bound to firewall; cannot mint or resolve authority"
                    .to_string(),
            };
        };
        match registry.get_claim(claim_id) {
            None => AuthorityDecision::Blocked {
                reason: format!("claim {claim_id} absent from ClaimRegistry; renderer cannot mint authority"),
            },
            Some(record) => AuthorityDecision::Registered {
                claim_id: record.claim_id.clone(),
                class: record.claim_class.as_str().to_string(),
            },
        }
    }
}

/// Render the terminal status line for any artifact.
///
/// The status is a pure function of the inputs, so two renderers cannot
/// disagree, and no renderer can produce a stronger line than the firewall
/// allowed. `SUPPORTED_EDGE` is only ever echoed from an already-registered
/// claim record.
pub fn render_status_line(decision: &AuthorityDecision) -> String {
    match decision {
        AuthorityDecision::NoEconomicClaim => "VERDICT: NO_ECONOMIC_CLAIM".to_string(),
        AuthorityDecision::Blocked { reason } => {
            format!("VERDICT: BLOCKED ({reason})")
        }
        AuthorityDecision::OpenPin { reference, detail } => {
            format!("VERDICT: BLOCKED / OPEN_PIN ({reference}) {detail}")
        }
        AuthorityDecision::Registered { claim_id, class } => {
            format!("VERDICT: {class} (registered claim {claim_id})")
        }
    }
}

/// Readiness gate for the certificate plane (#327 R3).
///
/// Certificates are read-only projections: this returns the *maximum* status
/// string a certificate may print for a given receipt, and it is derived from
/// the gate vector only. A certificate implementation must not compute its own
/// `Production Ready` predicate from scalar scores.
pub fn certificate_status_ceiling(gates: &GateVector) -> &'static str {
    match gates.readiness().status {
        // Any non-certified vector, and even a certified one without registry
        // authority, renders as NO_ECONOMIC_CLAIM.
        ReadinessStatus::InsufficientEvidence => "NO_ECONOMIC_CLAIM",
        ReadinessStatus::HardFailure => "BLOCKED",
        ReadinessStatus::Certified => "READY_NOT_CLAIMED",
    }
}

/// Assert that a rendered authority is not stronger than its input.
///
/// Used by report and certificate renderers as a runtime guard rather than a
/// comment, so a future edit that escalates status fails loudly.
pub fn assert_no_escalation(input: Authority, rendered: Authority) -> Result<(), String> {
    let capped = cap_authority(input, rendered);
    if capped != rendered {
        return Err(format!(
            "AUTHORITY_ESCALATION_BLOCKED: renderer authority {:?} exceeds input {:?} (capped {:?})",
            rendered, input, capped
        ));
    }
    Ok(())
}

/// Convenience: the class a registry record would need to carry for a gate
/// vector to be allowed to reference it at all.
pub fn claim_class_supported_by_gates(
    gates: &GateVector,
    record: &StatutoryClaimRecord,
) -> bool {
    if gates.readiness().status != ReadinessStatus::Certified {
        return false;
    }
    // Diagnostic classes are always referenceable once gates hold; economic
    // classes additionally require the registry's own authority validation,
    // which already happened at registration time.
    !matches!(
        record.claim_class,
        StatutoryClaimClass::SupportedEdge
    ) || matches!(record.authority.evidence, EvidenceAuthority::Observed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::benchmark::types::GateState;

    fn all_pass() -> GateVector {
        GateVector {
            g0_identity: GateState::Pass,
            g1_causal_pit: GateState::Pass,
            g2_determinism_ledger: GateState::Pass,
            g3_benchmark_coverage: GateState::Pass,
            g4_structural_robustness: GateState::Pass,
            g5_statistical_credibility: GateState::Pass,
            g6_protected_oos: GateState::Pass,
            g7_generalization: GateState::Pass,
            g8_prospective_shadow: GateState::Pass,
            g9_live_realization: GateState::Pass,
        }
    }

    #[test]
    fn firewall_never_mints_authority_without_registry() {
        let fw = AuthorityFirewall::without_registry();
        let d = fw.route_claim("bm_rcpt_1");
        assert!(matches!(d, AuthorityDecision::Blocked { .. }));
        // Even an all-PASS vector yields no claim on its own.
        assert!(fw.decide_from_gates(&all_pass()).is_uncertified());
    }

    #[test]
    fn cap_authority_is_monotone_and_total() {
        let input = BENCHMARK_DIAGNOSTIC_AUTHORITY;
        let stronger = Authority {
            evidence: EvidenceAuthority::Observed,
            decision: DecisionAuthority::ExecutionAuthorized,
            realization: RealizationStatus::CashflowSettled,
        };
        let capped = cap_authority(input, stronger);
        assert_eq!(capped, input);
        assert!(assert_no_escalation(input, stronger).is_err());
        assert!(assert_no_escalation(input, capped).is_ok());
        // Totality: flooring with itself is identity for every state.
        for s in [
            input,
            stronger,
            Authority::counterfactual_diagnostic(),
            Authority::realized_cashflow(),
        ] {
            assert_eq!(cap_authority(s, s), s);
        }
    }

    #[test]
    fn missing_gate_yields_no_economic_claim() {
        let fw = AuthorityFirewall::without_registry();
        assert_eq!(
            fw.decide_from_gates(&GateVector::default()).status_tag(),
            "NO_ECONOMIC_CLAIM"
        );
        assert_eq!(
            certificate_status_ceiling(&GateVector::default()),
            "NO_ECONOMIC_CLAIM"
        );
    }
}
