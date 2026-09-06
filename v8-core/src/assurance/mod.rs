//! Assurance Fabric (V8.5 M1/M6 Core Subsystem, D-147, D-149, D-150, Constitution Rule 44).
//!
//! Provides a deterministic, non-escalating evidence adjudication layer above D-136/D-141.

pub mod adjudicate;
pub mod attestation;
pub mod authority;
pub mod case;
pub mod certificate;
pub mod claim;
pub mod common_mode;
pub mod continuous;
pub mod defeater;
pub mod evidence_profile;
pub mod provenance;
pub mod receipt;
pub mod rules;

pub use adjudicate::AssuranceCaseAdjudicator;
pub use attestation::{AdmissibilityVerdict, AttestationStatus, EvidenceAttestation};
pub use authority::AuthorityProjection;
pub use case::{CaseIdentity, EvaluationCaseManifest, EvaluationEpoch};
pub use certificate::{CertificateStatus, ProductionEvidenceCertificate};
pub use claim::AssuranceClaim;
pub use common_mode::CommonModeGraph;
pub use continuous::{
    ContinuousEvaluationLedger, EvaluationEpochRecord, EvidenceDelta, FailureAttribution,
    KaizenHandoffReceipt, MonitoringPlan, WorldCoverageManifest,
};
pub use defeater::{DefeaterReceipt, DefeaterSeverity};
pub use evidence_profile::{
    audit_statistical_triple, gate_g0, gate_g1, synthetic_fail_may_challenge,
    synthetic_pass_confirms_no_edge, DataRole, EconomicConclusion, FrozenOOSState, GateId,
    GateVerdict, LiveState, PolicyEvidenceProfile, RobustnessTopology, ScenarioCell, ShadowState,
    StatisticalTripleAudit,
};
pub use provenance::ProvenanceGraph;
pub use receipt::{AssuranceCaseReceipt, ClaimStatus};
pub use rules::{ClaimRule, CompositionRule};
