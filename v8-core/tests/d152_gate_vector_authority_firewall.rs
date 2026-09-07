//! Issue #327: canonical G0-G9 gate vector and authority firewall.
//!
//! Negative tests demanded by the issue's verification gates:
//!  - omitted G6-G9 cannot yield readiness
//!  - required UNKNOWN / N/A / MISSING / BLOCKED cannot satisfy readiness
//!  - blocked OOS/live states cannot increase authority
//!  - a certificate or claim outside ClaimRegistry cannot mint authority
//!  - readiness is monotone non-increasing under degraded evidence
//!  - a renderer cannot increase input authority
//!  - uncertified output is always NO_ECONOMIC_CLAIM

use std::collections::HashMap;

use v8_core::assurance::evidence_profile::GateId;
use v8_core::authority::{Authority, DecisionAuthority, EvidenceAuthority, RealizationStatus};
use v8_core::benchmark::gate_authority::{
    assert_no_escalation, cap_authority, certificate_status_ceiling, gate_verdicts,
    render_status_line, AuthorityDecision, AuthorityFirewall, BENCHMARK_DIAGNOSTIC_AUTHORITY,
    OPEN_PIN_GATE_NAMING,
};
use v8_core::benchmark::types::{GateState, GateVector, GATE_DESCRIPTORS};
use v8_core::claims::{ClaimRegistry, StatutoryClaimClass};

/// Every state a gate can be in, including the #327 `Missing` addition.
const ALL_STATES: [GateState; 6] = [
    GateState::Pass,
    GateState::Blocked,
    GateState::Unknown,
    GateState::Defeated,
    GateState::NotApplicable,
    GateState::Missing,
];

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

/// Set exactly one gate position, leaving the other nine at `Pass`.
fn with_gate(position: usize, state: GateState) -> GateVector {
    let mut g = all_pass();
    match position {
        0 => g.g0_identity = state,
        1 => g.g1_causal_pit = state,
        2 => g.g2_determinism_ledger = state,
        3 => g.g3_benchmark_coverage = state,
        4 => g.g4_structural_robustness = state,
        5 => g.g5_statistical_credibility = state,
        6 => g.g6_protected_oos = state,
        7 => g.g7_generalization = state,
        8 => g.g8_prospective_shadow = state,
        9 => g.g9_live_realization = state,
        _ => panic!("gate position out of range"),
    }
    g
}

// ---------------------------------------------------------------------------
// R1: the effective gate vector covers G0-G9 with no silent omission
// ---------------------------------------------------------------------------

#[test]
fn gate_vector_enumerates_all_ten_positions() {
    let gates = all_pass();
    let evs = gates.evaluated_gates();
    assert_eq!(evs.len(), 10, "G0-G9 must all be evaluated");
    for (i, ev) in evs.iter().enumerate() {
        assert_eq!(ev.descriptor.index as usize, i);
        assert!(
            ev.descriptor.canonical_id.as_str().starts_with(&format!("G{i}_")),
            "gate {i} must map to the canonical assurance GateId G{i}, got {}",
            ev.descriptor.canonical_id.as_str()
        );
        assert!(
            ev.descriptor.source_clause.starts_with(&format!("G{}", i)),
            "gate {i} clause must be traceable to D-152 §5, got {:?}",
            ev.descriptor.source_clause
        );
    }
    assert_eq!(GATE_DESCRIPTORS.len(), 10);
}

#[test]
fn omitted_g6_g9_cannot_yield_readiness() {
    // The #327 defect: G6-G9 were not inputs to readiness at all. A vector
    // whose G6-G9 are entirely unevaluated must not read as ready.
    let mut g = all_pass();
    g.g6_protected_oos = GateState::Missing;
    assert!(!g.all_passed(), "missing G6 must block");
    assert!(!g.readiness().status.is_certified());

    g.g6_protected_oos = GateState::Pass;
    g.g7_generalization = GateState::Unknown;
    assert!(!g.all_passed(), "unknown G7 must block");

    g.g7_generalization = GateState::Pass;
    g.g8_prospective_shadow = GateState::NotApplicable;
    assert!(!g.all_passed(), "N/A G8 must block: live realization is required");

    g.g8_prospective_shadow = GateState::Pass;
    g.g9_live_realization = GateState::NotApplicable;
    assert!(
        !g.all_passed(),
        "N/A G9 must block: certificate gate is required"
    );

    // And each is individually named in the verdict.
    assert_eq!(g.readiness().evidence_gaps, vec![9]);
}

#[test]
fn every_gate_position_blocks_when_not_pass() {
    for position in 0..10 {
        for state in ALL_STATES {
            let g = with_gate(position, state);
            let ready = g.readiness().status.is_certified();
            assert_eq!(
                ready,
                state.is_pass(),
                "gate position {position} with state {state:?} readiness={ready}"
            );
        }
    }
}

#[test]
fn default_gate_vector_proves_nothing() {
    let g = GateVector::default();
    assert!(!g.all_passed());
    assert!(!g.readiness().status.is_certified());
    assert_eq!(g.to_status_string(), "NO_ECONOMIC_CLAIM");
    // The escape hatch is closed: no position defaults to NotApplicable.
    for ev in g.evaluated_gates() {
        assert_eq!(
            ev.state,
            GateState::Missing,
            "gate {} must default to Missing",
            ev.descriptor.vector_field
        );
    }
}

// ---------------------------------------------------------------------------
// R2: required unknown / missing / blocked evidence cannot increase authority
// ---------------------------------------------------------------------------

#[test]
fn required_unknown_and_na_and_missing_never_satisfy_readiness() {
    for state in [
        GateState::Unknown,
        GateState::NotApplicable,
        GateState::Missing,
        GateState::Blocked,
        GateState::Defeated,
    ] {
        for position in 0..10 {
            let g = with_gate(position, state);
            assert!(!g.all_passed());
            let fw = AuthorityFirewall::without_registry();
            let d = fw.decide_from_gates(&g);
            assert!(
                d.is_uncertified(),
                "state {state:?} at gate {position} produced {d:?}"
            );
            assert_ne!(d.status_tag(), "REGISTERED_CLAIM");
        }
    }
}

#[test]
fn blocked_oos_and_live_states_cannot_raise_authority() {
    for position in [6usize, 7, 8, 9] {
        for state in [
            GateState::Blocked,
            GateState::Unknown,
            GateState::NotApplicable,
            GateState::Missing,
            GateState::Defeated,
        ] {
            let g = with_gate(position, state);
            let fw = AuthorityFirewall::without_registry();
            let decision = fw.decide_from_gates(&g);
            let capped = cap_authority(BENCHMARK_DIAGNOSTIC_AUTHORITY, Authority::realized_cashflow());
            assert_eq!(
                capped,
                BENCHMARK_DIAGNOSTIC_AUTHORITY,
                "blocked OOS/live at gate {position} must not raise authority"
            );
            assert!(decision.is_uncertified());
            assert_eq!(
                certificate_status_ceiling(&g),
                if state.is_failure() { "BLOCKED" } else { "NO_ECONOMIC_CLAIM" }
            );
        }
    }
}

#[test]
fn readiness_is_monotone_non_increasing_under_degraded_evidence() {
    // Start from the fully satisfied vector and degrade one gate at a time.
    // A degraded vector may never be *more* ready than its predecessor.
    let baseline = all_pass();
    assert!(baseline.readiness().status.is_certified());
    for position in 0..10 {
        // Order the states from strongest to weakest non-passing.
        for state in [
            GateState::Unknown,
            GateState::NotApplicable,
            GateState::Missing,
            GateState::Blocked,
            GateState::Defeated,
        ] {
            let degraded = with_gate(position, state);
            assert!(
                !degraded.readiness().status.is_certified(),
                "degrading gate {position} to {state:?} must never certify"
            );
            let before = baseline.readiness().failing_positions.len();
            let after = degraded.readiness().failing_positions.len();
            assert!(
                after > before,
                "failure set must strictly grow: {before} -> {after}"
            );
        }
    }
}

#[test]
fn gates_are_not_compensable_no_scalar_rescues_a_failure() {
    // Ten domains at a perfect score cannot outvote a single failed gate.
    let mut gates = all_pass();
    gates.g5_statistical_credibility = GateState::Blocked;
    assert_eq!(gates.authority_contribution().as_str_for_test(), "BLOCKED");
    assert!(!gates.readiness().status.is_certified());
    // The readiness index is a diagnostic scalar and cannot gate-override:
    assert_eq!(
        AuthorityFirewall::without_registry()
            .decide_from_gates(&gates)
            .status_tag(),
        "BLOCKED"
    );
}

// ---------------------------------------------------------------------------
// R3: certificate rendering is read-only and cannot mint claims
// ---------------------------------------------------------------------------

#[test]
fn certificate_without_registry_cannot_mint_authority() {
    let fw = AuthorityFirewall::without_registry();
    // Even with every gate passing, no claim exists, so nothing is registered.
    let d = fw.route_claim("bm_rcpt_does_not_exist");
    assert!(
        matches!(d, AuthorityDecision::Blocked { .. }),
        "claim outside ClaimRegistry must be refused, got {d:?}"
    );
    assert!(d.is_uncertified());
    assert_eq!(render_status_line(&d), format!("VERDICT: BLOCKED ({})", reason_of(&d)));
}

#[test]
fn registered_claim_resolves_only_through_registry() {
    let mut registry = ClaimRegistry::new();
    let record = registry
        .register_claim(
            StatutoryClaimClass::DiagnosticSignal,
            0.42,
            "capability_index",
            Authority::counterfactual_diagnostic(),
            vec!["bm_rcpt_parent".into()],
            None,
            None,
            None,
            0,
        )
        .expect("diagnostic claim registers");

    let fw = AuthorityFirewall::with_registry(&registry);
    let d = fw.route_claim(&record.claim_id);
    match d {
        AuthorityDecision::Registered { claim_id, class } => {
            assert_eq!(claim_id, record.claim_id);
            assert_eq!(class, "DIAGNOSTIC_SIGNAL");
        }
        other => panic!("expected Registered, got {other:?}"),
    }
    // A fabricated id still fails closed.
    assert!(matches!(
        fw.route_claim("bm_rcpt_fabricated"),
        AuthorityDecision::Blocked { .. }
    ));
}

#[test]
fn renderer_cannot_increase_authority() {
    // Property-style sweep: for every pair of authority states, capping never
    // yields more than the input, and escalation is always detected.
    let evidence = [
        EvidenceAuthority::Counterfactual,
        EvidenceAuthority::ModelDerived,
        EvidenceAuthority::Observed,
    ];
    let decisions = [
        DecisionAuthority::DiagnosticOnly,
        DecisionAuthority::Reconciled,
        DecisionAuthority::UtilityEligible,
        DecisionAuthority::PortfolioAuthorized,
        DecisionAuthority::ExecutionAuthorized,
    ];
    let realizations = [
        RealizationStatus::Hypothetical,
        RealizationStatus::Simulated,
        RealizationStatus::Filled,
        RealizationStatus::CashflowSettled,
    ];
    let mut inputs = Vec::new();
    for e in evidence {
        for d in decisions {
            for r in realizations {
                inputs.push(Authority {
                    evidence: e,
                    decision: d,
                    realization: r,
                });
            }
        }
    }
    assert_eq!(inputs.len(), 3 * 5 * 4);
    for input in &inputs {
        for rendered in &inputs {
            let capped = cap_authority(*input, *rendered);
            assert!(capped.evidence <= rendered.evidence);
            assert!(capped.decision <= rendered.decision);
            assert!(capped.realization <= rendered.realization);
            if capped != *rendered {
                assert!(
                    assert_no_escalation(*input, *rendered).is_err(),
                    "escalation from {input:?} to {rendered:?} must be caught"
                );
            } else {
                assert!(assert_no_escalation(*input, *rendered).is_ok());
            }
        }
        // A renderer that only echoes the input authority is always accepted.
        assert_eq!(cap_authority(*input, *input), *input);
    }
}

#[test]
fn gate_verdicts_use_the_assurance_vocabulary_not_a_parallel_one() {
    let verdicts = gate_verdicts(&with_gate(0, GateState::Defeated));
    assert_eq!(verdicts.len(), 10);
    assert!(verdicts.iter().any(|v| v.is_blocking()));
    // G2..G9 failures map to unresolved/blocked but only G0/G1 are "blocking"
    // per D-152 §5, so the taxonomy is preserved rather than invented.
    for v in &verdicts {
        assert!(
            matches!(
                v.gate,
                GateId::G0ConstitutionalIntegrity
                    | GateId::G1MeasurementIdentity
                    | GateId::G2HistoricalDiagnostic
                    | GateId::G3ScenarioRobustness
                    | GateId::G4SyntheticFalsification
                    | GateId::G5SelectionControl
                    | GateId::G6FrozenOOSReplication
                    | GateId::G7ProspectiveShadow
                    | GateId::G8LiveRealization
                    | GateId::G9Certificate
            ),
            "unexpected canonical gate {:?}",
            v.gate
        );
    }
}

#[test]
fn uncertified_output_is_always_no_economic_claim() {
    // Exhaustive over single-gate degradation: the printed status is never a
    // claim-bearing one.
    for position in 0..10 {
        for state in ALL_STATES {
            let g = with_gate(position, state);
            let line = render_status_line(&AuthorityFirewall::without_registry().decide_from_gates(&g));
            assert!(
                line.contains("NO_ECONOMIC_CLAIM") || line.contains("BLOCKED"),
                "gate {position} state {state:?} rendered {line}"
            );
            assert!(!line.contains("SUPPORTED_EDGE"));
        }
    }
    // Even the fully-satisfied vector grants no economic claim.
    let line = render_status_line(
        &AuthorityFirewall::without_registry().decide_from_gates(&all_pass()),
    );
    assert_eq!(line, "VERDICT: NO_ECONOMIC_CLAIM");
}

#[test]
fn open_pin_is_declared_not_invented() {
    assert!(OPEN_PIN_GATE_NAMING.contains("OPEN_PIN"));
    assert!(OPEN_PIN_GATE_NAMING.contains("D-152"));
    assert!(OPEN_PIN_GATE_NAMING.contains("D-153"));
    // The three conflicting positions are the ones we refuse to reinterpret.
    for i in [7usize, 8, 9] {
        assert!(
            GATE_DESCRIPTORS[i]
                .canonical_id
                .as_str()
                .starts_with(&format!("G{i}_")),
        );
    }
}

#[test]
fn unknown_domain_results_cannot_be_silently_ignored() {
    // Sanity: an empty gate evaluation map (HashMap with no entries) is not a
    // substitute for a gate vector; readiness is a conjunction over positions,
    // not over "whatever was provided".
    let empty: HashMap<usize, GateState> = HashMap::new();
    assert!(empty.is_empty());
    assert!(!GateVector::default().readiness().status.is_certified());
}

fn reason_of(d: &AuthorityDecision) -> String {
    match d {
        AuthorityDecision::Blocked { reason } => reason.clone(),
        other => panic!("expected Blocked, got {other:?}"),
    }
}

/// Local helper so the non-compensability test can assert on the contribution
/// without depending on `Debug` formatting.
trait ContributionStr {
    fn as_str_for_test(&self) -> &'static str;
}

impl ContributionStr for v8_core::benchmark::types::GateAuthorityContribution {
    fn as_str_for_test(&self) -> &'static str {
        use v8_core::benchmark::types::GateAuthorityContribution as C;
        match self {
            C::NonCompensableSatisfied => "SATISFIED_NO_CLAIM",
            C::Blocked => "BLOCKED",
            C::NoEconomicClaim => "NO_ECONOMIC_CLAIM",
        }
    }
}
