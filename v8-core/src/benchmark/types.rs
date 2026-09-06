//! Canonical Benchmark Ontology and Types (D-153).
//!
//! Enforces ontological separation:
//! - BenchmarkCase != AssuranceCase
//! - BenchmarkProfile != PolicyEvidenceProfile
//! - CapabilityScore != Readiness
//! - Hard Gates (G0-G9) cannot be averaged away

use serde::{Deserialize, Serialize};

/// Ten explicit benchmark capability domains (Rule 57.5)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CapabilityDomain {
    ExecutionFidelity,
    RegimeRobustness,
    CrossAssetGeneralization,
    MicrostructureInvariance,
    DefeaterResistance,
    StatisticalCredibility,
    EvaluationSafety,
    CapacityScalability,
    RepresentationStability,
    OperationalSimplicity,
}

impl CapabilityDomain {
    pub const ALL: [CapabilityDomain; 10] = [
        CapabilityDomain::ExecutionFidelity,
        CapabilityDomain::RegimeRobustness,
        CapabilityDomain::CrossAssetGeneralization,
        CapabilityDomain::MicrostructureInvariance,
        CapabilityDomain::DefeaterResistance,
        CapabilityDomain::StatisticalCredibility,
        CapabilityDomain::EvaluationSafety,
        CapabilityDomain::CapacityScalability,
        CapabilityDomain::RepresentationStability,
        CapabilityDomain::OperationalSimplicity,
    ];

    pub fn as_str(&self) -> &'static str {
        match self {
            CapabilityDomain::ExecutionFidelity => "ExecutionFidelity",
            CapabilityDomain::RegimeRobustness => "RegimeRobustness",
            CapabilityDomain::CrossAssetGeneralization => "CrossAssetGeneralization",
            CapabilityDomain::MicrostructureInvariance => "MicrostructureInvariance",
            CapabilityDomain::DefeaterResistance => "DefeaterResistance",
            CapabilityDomain::StatisticalCredibility => "StatisticalCredibility",
            CapabilityDomain::EvaluationSafety => "EvaluationSafety",
            CapabilityDomain::CapacityScalability => "CapacityScalability",
            CapabilityDomain::RepresentationStability => "RepresentationStability",
            CapabilityDomain::OperationalSimplicity => "OperationalSimplicity",
        }
    }
}

/// Evaluation Population Type (D-153 Section 33)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EvaluationPopulation {
    BurnedDiagnosticReal,
    ChronologicalWalkForward,
    PurgedCombinatorialKFold,
    ProtectedFrozenOos,
    FoundrySyntheticNovelty,
    ExternalExecutionParity,
}

impl EvaluationPopulation {
    pub fn is_synthetic(&self) -> bool {
        matches!(self, EvaluationPopulation::FoundrySyntheticNovelty)
    }

    pub fn is_protected(&self) -> bool {
        matches!(self, EvaluationPopulation::ProtectedFrozenOos)
    }
}

/// Strict Metric Categorization
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MetricCategory {
    EngineeringFidelity,
    StressRobustness,
    CounterfactualAgnostic,
    RealizedEconomic,
}

/// Bounded score with uncertainty bounds
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BoundedScore {
    pub value: f64,
    pub lower_bound_95: f64,
    pub upper_bound_95: f64,
    pub sample_size: usize,
    pub effective_sample_size: f64,
}

impl BoundedScore {
    pub fn new(value: f64, lower: f64, upper: f64, n: usize, ess: f64) -> Self {
        Self {
            value: value.clamp(0.0, 1.0),
            lower_bound_95: lower.clamp(0.0, 1.0),
            upper_bound_95: upper.clamp(0.0, 1.0),
            sample_size: n,
            effective_sample_size: ess,
        }
    }
}

/// Five-tier capital outcome projection evidence grade (D-153 §89, App D)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ProjectionGrade {
    GradeU, // Unknown / Uncertified
    GradeD, // Diagnostic Only
    GradeC, // Synthetic Robustness Only
    GradeB, // Replication Backed
    GradeA, // Empirically Certified
}

impl ProjectionGrade {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::GradeU => "U (Unknown/Uncertified)",
            Self::GradeD => "D (Diagnostic Only)",
            Self::GradeC => "C (Synthetic Robustness Only)",
            Self::GradeB => "B (Replication Backed)",
            Self::GradeA => "A (Empirically Certified)",
        }
    }

    pub fn allows_forward_probability(&self) -> bool {
        matches!(self, Self::GradeB | Self::GradeA)
    }
}

/// Hard Gate State (D-153 §80, §106)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GateState {
    Pass,
    Blocked,
    Unknown,
    Defeated,
    NotApplicable,
    /// No gate result was produced at all.
    ///
    /// Added for #327: D-152/D-153 had no canonical status for a *missing*
    /// gate, so an unevaluated gate was indistinguishable from an evaluated
    /// `UNKNOWN` one. `Missing` is strictly non-satisfying; it can never be
    /// produced by an evaluation, only by the absence of one.
    Missing,
}

/// Taxonomy of why a gate does not hold (#327, D-152 §5).
///
/// The three classes are deliberately distinct because they have different
/// canonical failure semantics (issue §14): a *hard failure* is a falsified
/// claim, *insufficient evidence* is unresolved and may be produced later, and
/// *missing* means no evaluation was even attempted.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GateFailureClass {
    /// The gate was falsified: `Blocked` or `Defeated`.
    HardFailure,
    /// The gate was evaluated without enough evidence to conclude.
    InsufficientEvidence,
    /// The gate was never evaluated, or was declared inapplicable without
    /// satisfying it. `Missing`, `NotApplicable`.
    MissingEvidence,
}

impl GateState {
    pub fn is_pass(&self) -> bool {
        matches!(self, Self::Pass)
    }

    pub fn is_failure(&self) -> bool {
        matches!(self, Self::Blocked | Self::Defeated)
    }

    /// Why this state does not hold, or `None` when it does hold.
    ///
    /// `NotApplicable` is classified as `MissingEvidence`, not as a pass: an
    /// unmet required gate cannot be satisfied by declaring it irrelevant
    /// (#327 R2). `Missing` is likewise never a pass.
    pub fn failure_class(&self) -> Option<GateFailureClass> {
        match self {
            Self::Pass => None,
            Self::Blocked | Self::Defeated => Some(GateFailureClass::HardFailure),
            Self::Unknown => Some(GateFailureClass::InsufficientEvidence),
            Self::NotApplicable | Self::Missing => Some(GateFailureClass::MissingEvidence),
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Pass => "PASS",
            Self::Blocked => "BLOCKED",
            Self::Unknown => "UNKNOWN",
            Self::Defeated => "DEFEATED",
            Self::NotApplicable => "NOT_APPLICABLE",
            Self::Missing => "MISSING",
        }
    }
}

/// Requirement class of a gate position under D-152 §5.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GateRequirement {
    /// Mandatory for readiness. Only `Pass` satisfies it.
    Required,
    /// Mandatory for readiness and a failure here blocks everything downstream
    /// (D-152 §5: "hard fail blocks all" / "hard fail blocks inference").
    RequiredBlocking,
}

/// Static metadata for one gate position of the vector.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GateDescriptor {
    pub index: u8,
    pub canonical_id: crate::assurance::evidence_profile::GateId,
    pub vector_field: &'static str,
    pub requirement: GateRequirement,
    /// Verbatim owning clause (D-152 §5), so the requirement is traceable and
    /// not an invented interpretation.
    pub source_clause: &'static str,
}

/// The ten gate positions, G0..G9, in order.
///
/// Gate *semantics* are taken from D-152 §5 (`docs/contracts/
/// D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md`), which is the authority
/// that defines G0-G9. The `GateVector` field names in D-153 disagree with
/// D-152 for positions G7-G9; see `OPEN_PIN` notes below and
/// `gate_authority::OPEN_PIN_GATE_NAMING`.
pub const GATE_DESCRIPTORS: [GateDescriptor; 10] = [
    GateDescriptor {
        index: 0,
        canonical_id: crate::assurance::evidence_profile::GateId::G0ConstitutionalIntegrity,
        vector_field: "g0_identity",
        requirement: GateRequirement::RequiredBlocking,
        source_clause: "G0 constitutional/causal integrity (PIT, ChronosGate, determinism, ledger conservation, receipt integrity, non-escalation, synthetic isolation, claim typing): hard fail blocks all.",
    },
    GateDescriptor {
        index: 1,
        canonical_id: crate::assurance::evidence_profile::GateId::G1MeasurementIdentity,
        vector_field: "g1_causal_pit",
        requirement: GateRequirement::RequiredBlocking,
        source_clause: "G1 measurement identity (estimand, data role, lineage, search lineage, cost/execution/world versions, burn marking): hard fail blocks inference.",
    },
    GateDescriptor {
        index: 2,
        canonical_id: crate::assurance::evidence_profile::GateId::G2HistoricalDiagnostic,
        vector_field: "g2_determinism_ledger",
        requirement: GateRequirement::Required,
        source_clause: "G2 historical diagnostic court: outcome is diagnostic state, promotion NONE.",
    },
    GateDescriptor {
        index: 3,
        canonical_id: crate::assurance::evidence_profile::GateId::G3ScenarioRobustness,
        vector_field: "g3_benchmark_coverage",
        requirement: GateRequirement::Required,
        source_clause: "G3 scenario coverage & behavioral robustness: unknown stays unknown.",
    },
    GateDescriptor {
        index: 4,
        canonical_id: crate::assurance::evidence_profile::GateId::G4SyntheticFalsification,
        vector_field: "g4_structural_robustness",
        requirement: GateRequirement::Required,
        source_clause: "G4 adversarial/synthetic falsification: PASS mints nothing; FAIL is passport-scoped.",
    },
    GateDescriptor {
        index: 5,
        canonical_id: crate::assurance::evidence_profile::GateId::G5SelectionControl,
        vector_field: "g5_statistical_credibility",
        requirement: GateRequirement::Required,
        source_clause: "G5 selection control: WRC + genuine DSR + SPA remain the active burden ... keeps G5 at NO_ECONOMIC_CLAIM.",
    },
    GateDescriptor {
        index: 6,
        canonical_id: crate::assurance::evidence_profile::GateId::G6FrozenOOSReplication,
        vector_field: "g6_protected_oos",
        requirement: GateRequirement::Required,
        source_clause: "G6 frozen-OOS replication: PASS = bounded replication only.",
    },
    // OPEN_PIN(#327): D-152 calls G7 `prospective shadow succession`, while the
    // D-153 `GateVector` field at this position is named `g7_generalization`.
    // Positional mapping (field `gN` -> `GateId::G{N}`) is used because the
    // field names carry the index. Readiness is unaffected by the naming
    // conflict: under either reading a non-`Pass` state blocks.
    GateDescriptor {
        index: 7,
        canonical_id: crate::assurance::evidence_profile::GateId::G7ProspectiveShadow,
        vector_field: "g7_generalization",
        requirement: GateRequirement::Required,
        source_clause: "G7 prospective shadow succession: `EvaluationEpoch` forward evidence, survival/drift/drawdown, e-process state.",
    },
    // OPEN_PIN(#327): D-152 calls G8 `live realization`; the D-153 field here is
    // `g8_prospective_shadow`. Same positional resolution and same
    // readiness-neutrality as position 7.
    GateDescriptor {
        index: 8,
        canonical_id: crate::assurance::evidence_profile::GateId::G8LiveRealization,
        vector_field: "g8_prospective_shadow",
        requirement: GateRequirement::Required,
        source_clause: "G8 live realization: venue-settled fills/costs/settlement/deviation/capacity/incidents. Historical/synthetic never substitutes.",
    },
    // OPEN_PIN(#327): D-152 calls G9 the `certificate` gate; the D-153 field is
    // `g9_live_realization`. Position 9 is the certificate gate under D-152,
    // which is also the gate that forbids scalar collapse.
    GateDescriptor {
        index: 9,
        canonical_id: crate::assurance::evidence_profile::GateId::G9Certificate,
        vector_field: "g9_live_realization",
        requirement: GateRequirement::Required,
        source_clause: "G9 certificate: non-scalar `ProductionEvidenceCertificate` + profile conclusion; scalar collapse forbidden.",
    },
];

/// One explicit gate result: position, requirement and state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GateEvaluation {
    pub descriptor: &'static GateDescriptor,
    pub state: GateState,
}

impl GateEvaluation {
    pub fn holds(&self) -> bool {
        self.state.is_pass()
    }
}

/// Terminal readiness status of a gate vector. Never a bare boolean so that a
/// caller cannot silently treat "not ready" as "no information".
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReadinessStatus {
    /// Every required gate holds. Only this status may carry authority beyond
    /// `NO_ECONOMIC_CLAIM`, and even then only via `ClaimRegistry`.
    Certified,
    /// At least one gate was falsified.
    HardFailure,
    /// No falsification, but required evidence is absent or unresolved.
    InsufficientEvidence,
}

impl ReadinessStatus {
    pub fn is_certified(&self) -> bool {
        matches!(self, Self::Certified)
    }
}

/// Structured readiness verdict (#327 R1, R2).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadinessVerdict {
    pub evaluations: [GateEvaluation; 10],
    pub status: ReadinessStatus,
    /// Positions that failed to hold, in ascending gate order.
    pub failing_positions: Vec<u8>,
    /// Positions that were falsified (`Blocked`/`Defeated`).
    pub hard_failures: Vec<u8>,
    /// Positions with absent/unresolved evidence.
    pub evidence_gaps: Vec<u8>,
}

impl ReadinessVerdict {
    pub fn status_string(&self) -> &'static str {
        match self.status {
            ReadinessStatus::Certified => "READY_NOT_CLAIMED",
            ReadinessStatus::HardFailure => "BLOCKED",
            ReadinessStatus::InsufficientEvidence => "NO_ECONOMIC_CLAIM",
        }
    }
}

/// Hard Gate Vector G0–G9 (D-153 §80, App F)
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateVector {
    pub g0_identity: GateState,
    pub g1_causal_pit: GateState,
    pub g2_determinism_ledger: GateState,
    pub g3_benchmark_coverage: GateState,
    pub g4_structural_robustness: GateState,
    pub g5_statistical_credibility: GateState,
    pub g6_protected_oos: GateState,
    pub g7_generalization: GateState,
    pub g8_prospective_shadow: GateState,
    pub g9_live_realization: GateState,
}

impl Default for GateVector {
    /// A vector that proves nothing.
    ///
    /// Every position defaults to a strictly non-satisfying state. In
    /// particular `g8`/`g9` are `Missing`, **not** `NotApplicable`: #327 found
    /// that defaulting the two highest-authority gates (live realization and
    /// certificate) to `NotApplicable` created an escape hatch by which a
    /// freshly constructed vector read as "those gates do not apply here".
    /// Declaring a required gate inapplicable is a claim that needs its own
    /// authority; the absence of an evaluation does not.
    fn default() -> Self {
        Self {
            g0_identity: GateState::Missing,
            g1_causal_pit: GateState::Missing,
            g2_determinism_ledger: GateState::Missing,
            g3_benchmark_coverage: GateState::Missing,
            g4_structural_robustness: GateState::Missing,
            g5_statistical_credibility: GateState::Missing,
            g6_protected_oos: GateState::Missing,
            g7_generalization: GateState::Missing,
            g8_prospective_shadow: GateState::Missing,
            g9_live_realization: GateState::Missing,
        }
    }
}

impl GateVector {
    /// The ten gate positions G0..G9 in ascending order.
    ///
    /// #327 R1 (D-152 §5): the effective gate vector must cover G0-G9 with no
    /// silent omission, so this is the single source of enumeration and is
    /// fixed-length by construction.
    pub fn evaluated_gates(&self) -> [GateEvaluation; 10] {
        let states = [
            self.g0_identity,
            self.g1_causal_pit,
            self.g2_determinism_ledger,
            self.g3_benchmark_coverage,
            self.g4_structural_robustness,
            self.g5_statistical_credibility,
            self.g6_protected_oos,
            self.g7_generalization,
            self.g8_prospective_shadow,
            self.g9_live_realization,
        ];
        let mut out = std::array::from_fn(|i| GateEvaluation {
            descriptor: &GATE_DESCRIPTORS[i],
            state: states[i],
        });
        // Guard the positional mapping against a future descriptor reorder.
        for (i, ev) in out.iter().enumerate() {
            debug_assert_eq!(ev.descriptor.index as usize, i);
        }
        out
    }

    /// Strict non-compensable conjunction over **all ten** gates G0-G9.
    ///
    /// Before #327 this only inspected G0-G5, so G6-G9 could never block
    /// readiness. Any state other than `Pass` — including `Unknown`,
    /// `NotApplicable` and `Missing` — now fails.
    pub fn all_passed(&self) -> bool {
        self.evaluated_gates().iter().all(GateEvaluation::holds)
    }

    /// The structured readiness verdict for this vector (#327 R1, R2).
    ///
    /// Monotonicity invariant (issue §13): degrading any single gate from
    /// `Pass` to any other state, or from any other state to `Missing`, can
    /// never turn a non-`Certified` verdict into a `Certified` one, and can
    /// never reduce the set of recorded failures.
    pub fn readiness(&self) -> ReadinessVerdict {
        let evaluations = self.evaluated_gates();
        let mut failing_positions = Vec::new();
        let mut hard_failures = Vec::new();
        let mut evidence_gaps = Vec::new();

        for ev in &evaluations {
            if ev.holds() {
                continue;
            }
            failing_positions.push(ev.descriptor.index);
            match ev.state.failure_class() {
                Some(GateFailureClass::HardFailure) => hard_failures.push(ev.descriptor.index),
                Some(_) => evidence_gaps.push(ev.descriptor.index),
                None => unreachable!("non-passing state must have a failure class"),
            }
        }

        let status = if !hard_failures.is_empty() {
            ReadinessStatus::HardFailure
        } else if failing_positions.is_empty() {
            ReadinessStatus::Certified
        } else {
            ReadinessStatus::InsufficientEvidence
        };

        ReadinessVerdict {
            evaluations,
            status,
            failing_positions,
            hard_failures,
            evidence_gaps,
        }
    }

    /// Any hard failure or defeat triggers immediate overall failure.
    ///
    /// Retained with its original meaning (`Blocked`/`Defeated`) for existing
    /// call sites such as the capability scorer; use `readiness()` for the
    /// full three-class taxonomy.
    pub fn any_hard_failure(&self) -> bool {
        self.evaluated_gates()
            .iter()
            .any(|g| g.state.is_failure())
    }

    /// True when required evidence is absent or unresolved without being
    /// falsified — the distinction #327 R2 requires: absence is not a pass and
    /// is not a defeat either.
    pub fn any_evidence_gap(&self) -> bool {
        self.readiness().status == ReadinessStatus::InsufficientEvidence
    }

    /// Authority contribution of the vector. Never a score: gates are
    /// non-compensable (D-153 §2.4), so no scalar can average a failed gate
    /// away and there is nothing here for a weighted mean to consume.
    pub fn authority_contribution(&self) -> GateAuthorityContribution {
        match self.readiness().status {
            ReadinessStatus::Certified => GateAuthorityContribution::NonCompensableSatisfied,
            ReadinessStatus::HardFailure => GateAuthorityContribution::Blocked,
            ReadinessStatus::InsufficientEvidence => {
                GateAuthorityContribution::NoEconomicClaim
            }
        }
    }

    /// Canonical terminal status string. A renderer calls this and can only
    /// echo it — it cannot manufacture a stronger status (#327 R3).
    pub fn to_status_string(&self) -> &'static str {
        match self.authority_contribution() {
            GateAuthorityContribution::Blocked => "BLOCKED",
            GateAuthorityContribution::NoEconomicClaim => "NO_ECONOMIC_CLAIM",
            // Even a fully satisfied vector grants nothing by itself: economic
            // authority is minted only by ClaimRegistry (Rule 12).
            GateAuthorityContribution::NonCompensableSatisfied => "NO_ECONOMIC_CLAIM",
        }
    }
}

/// What a gate vector contributes to authority (#327 R2, R3).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateAuthorityContribution {
    /// All ten gates hold. Grants *eligibility to be considered*, never an
    /// economic claim.
    NonCompensableSatisfied,
    /// A gate was falsified.
    Blocked,
    /// Required evidence is missing or unresolved.
    NoEconomicClaim,
}

