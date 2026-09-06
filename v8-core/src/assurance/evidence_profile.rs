//! Scenario-Centric Policy Evidence Profile (D-152).
//!
//! Replaces the single-trajectory headline (`12M RETURN = +x%`) with a typed
//! evidence topology. Reuses `ProductionEvidenceCertificate`, `EvaluationCaseManifest`,
//! `EvaluationEpoch`, `GeneratorPassport`, `ArchetypeId` — no second bureaucracy.
//!
//! Invariants:
//! - Burned diagnostic output carries `promotion_authority = NONE` and can never
//!   mint `SUPPORTED_EDGE` or `REALIZED_CASHFLOW`.
//! - Synthetic PASS is non-economic; synthetic FAIL challenges a claim only when
//!   the generator passport passes and the claim admits synthetic relevance.
//! - No scalar average may hide a hard failure cell; UNKNOWN coverage stays UNKNOWN.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

use crate::assurance::case::{CaseIdentity, EvaluationEpoch};
use crate::assurance::certificate::CertificateStatus;
use crate::assurance::claim::AssuranceClaim;
use crate::assurance::receipt::ClaimStatus;
use crate::evaluation::allegory::ArchetypeId;
use crate::world::{GeneratorPassport, SyntheticPopulation, WorldFamily};

/// Canonical data role. A burned tape never regains untouched-OOS authority.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DataRole {
    Development,
    BurnedDiagnostic,
    FrozenOOS,
    ShadowProspective,
    LiveRealized,
    SyntheticDev,
    SyntheticQualification,
    SyntheticNovelty,
}

impl DataRole {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Development => "DEVELOPMENT",
            Self::BurnedDiagnostic => "BURNED_DIAGNOSTIC",
            Self::FrozenOOS => "FROZEN_OOS",
            Self::ShadowProspective => "SHADOW_PROSPECTIVE",
            Self::LiveRealized => "LIVE_REALIZED",
            Self::SyntheticDev => "SYNTHETIC_DEV",
            Self::SyntheticQualification => "SYNTHETIC_QUALIFICATION",
            Self::SyntheticNovelty => "SYNTHETIC_NOVELTY",
        }
    }

    /// Only frozen-OOS may support replication; only shadow supports prospective;
    /// only live supports realization. Everything else promotes nothing.
    pub const fn promotion_authority(&self) -> &'static str {
        match self {
            Self::FrozenOOS => "REPLICATION_ONLY",
            Self::ShadowProspective => "PROSPECTIVE_ONLY",
            Self::LiveRealized => "REALIZATION_ONLY",
            _ => "NONE",
        }
    }
}

impl From<SyntheticPopulation> for DataRole {
    fn from(p: SyntheticPopulation) -> Self {
        match p {
            SyntheticPopulation::SyntheticDev => Self::SyntheticDev,
            SyntheticPopulation::SyntheticQualification => Self::SyntheticQualification,
            SyntheticPopulation::SyntheticNovelty => Self::SyntheticNovelty,
        }
    }
}

/// Gate identifiers G0..G9. Each answers a distinct validity question.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GateId {
    G0ConstitutionalIntegrity,
    G1MeasurementIdentity,
    G2HistoricalDiagnostic,
    G3ScenarioRobustness,
    G4SyntheticFalsification,
    G5SelectionControl,
    G6FrozenOOSReplication,
    G7ProspectiveShadow,
    G8LiveRealization,
    G9Certificate,
}

impl GateId {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::G0ConstitutionalIntegrity => "G0_CONSTITUTIONAL_INTEGRITY",
            Self::G1MeasurementIdentity => "G1_MEASUREMENT_IDENTITY",
            Self::G2HistoricalDiagnostic => "G2_HISTORICAL_DIAGNOSTIC",
            Self::G3ScenarioRobustness => "G3_SCENARIO_ROBUSTNESS",
            Self::G4SyntheticFalsification => "G4_SYNTHETIC_FALSIFICATION",
            Self::G5SelectionControl => "G5_SELECTION_CONTROL",
            Self::G6FrozenOOSReplication => "G6_FROZEN_OOS_REPLICATION",
            Self::G7ProspectiveShadow => "G7_PROSPECTIVE_SHADOW",
            Self::G8LiveRealization => "G8_LIVE_REALIZATION",
            Self::G9Certificate => "G9_CERTIFICATE",
        }
    }
}

/// Outcome of a single gate. Blocks downstream claims on hard failure.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GateVerdict {
    pub gate: GateId,
    pub status: ClaimStatus,
    pub detail: String,
    pub authority_granted: String,
    pub authority_denied: Vec<String>,
}

impl GateVerdict {
    pub fn pass(gate: GateId, detail: &str, granted: &str) -> Self {
        Self {
            gate,
            status: ClaimStatus::Verified,
            detail: detail.to_string(),
            authority_granted: granted.to_string(),
            authority_denied: Vec::new(),
        }
    }

    pub fn fail_closed(gate: GateId, detail: &str, denied: &[&str]) -> Self {
        Self {
            gate,
            status: ClaimStatus::Blocked,
            detail: detail.to_string(),
            authority_granted: "NONE".to_string(),
            authority_denied: denied.iter().map(|s| s.to_string()).collect(),
        }
    }

    pub fn unknown(gate: GateId, detail: &str) -> Self {
        Self {
            gate,
            status: ClaimStatus::Unresolved,
            detail: detail.to_string(),
            authority_granted: "NONE".to_string(),
            authority_denied: Vec::new(),
        }
    }

    pub fn is_blocking(&self) -> bool {
        self.status == ClaimStatus::Blocked
            && matches!(
                self.gate,
                GateId::G0ConstitutionalIntegrity | GateId::G1MeasurementIdentity
            )
    }
}

/// One scenario cell. Hard failures stay visible; missing coverage stays UNKNOWN.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenarioCell {
    pub scenario_id: String,
    pub archetype: Option<ArchetypeId>,
    pub world_family: Option<WorldFamily>,
    pub coverage_bars: usize,
    pub episode_count: usize,
    pub net_utility_usdt: f64,
    pub survival: bool,
    pub max_drawdown_pct: f64,
    pub fee_retention_pct: f64,
    pub failure_phenotype: Option<String>,
    pub evidence_authority: String,
    pub status: ClaimStatus,
}

impl ScenarioCell {
    pub fn unknown(scenario_id: &str) -> Self {
        Self {
            scenario_id: scenario_id.to_string(),
            archetype: None,
            world_family: None,
            coverage_bars: 0,
            episode_count: 0,
            net_utility_usdt: 0.0,
            survival: false,
            max_drawdown_pct: 0.0,
            fee_retention_pct: 0.0,
            failure_phenotype: None,
            evidence_authority: "UNKNOWN".to_string(),
            status: ClaimStatus::Unresolved,
        }
    }
}

/// Robustness topology: nearest validated defeater + failed families + unknowns.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RobustnessTopology {
    pub nearest_plausible_defeater: Option<String>,
    pub minimal_defeater_distance: Option<f64>,
    pub failed_scenario_families: Vec<String>,
    pub unknown_regions: Vec<String>,
    pub passport_bindings: BTreeMap<String, bool>,
    pub world_coverage_manifest: Option<String>,
}

/// Frozen-OOS replication state. PASS means bounded replication only.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum FrozenOOSState {
    NotRun,
    Pass { receipt: String },
    Fail { receipt: String },
    Inconclusive { receipt: String },
}

/// Prospective shadow state with sequential-monitoring guard.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ShadowState {
    NotAvailable,
    Active { epochs: u64 },
    Degraded { reason: String },
    Quarantined { reason: String },
}

/// Live realization state. Only venue-settled fills count.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum LiveState {
    None,
    Paper,
    LimitedLive { fills: usize },
    Live { fills: usize },
}

/// Supportable economic conclusion. Never a scalar boolean.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EconomicConclusion {
    Unknown,
    HistoricallyReplicated,
    ProspectivelySupported,
    LiveSupported,
    NotProductionSupported,
}

impl EconomicConclusion {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Unknown => "UNKNOWN",
            Self::HistoricallyReplicated => "HISTORICALLY_REPLICATED",
            Self::ProspectivelySupported => "PROSPECTIVELY_SUPPORTED",
            Self::LiveSupported => "LIVE_SUPPORTED",
            Self::NotProductionSupported => "NOT_PRODUCTION_SUPPORTED",
        }
    }
}

/// Canonical multi-dimensional evaluation artifact.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PolicyEvidenceProfile {
    pub policy_id: String,
    pub policy_hash: String,
    pub config_hash: String,
    pub code_hash: String,
    pub lineage_id: String,
    pub evaluation_case_id: CaseIdentity,
    pub epoch_id: EvaluationEpoch,
    pub historical_net_usdt: f64,
    pub historical_gross_usdt: f64,
    pub historical_fee_usdt: f64,
    pub historical_role: DataRole,
    pub max_drawdown_pct: f64,
    pub trade_count: usize,
    pub asset_concentration_pct: f64,
    pub scenario_cells: Vec<ScenarioCell>,
    pub robustness: RobustnessTopology,
    pub frozen_oos: FrozenOOSState,
    pub shadow: ShadowState,
    pub live: LiveState,
    pub certificate: CertificateStatus,
    pub gates: Vec<GateVerdict>,
    pub conclusion: EconomicConclusion,
}

impl PolicyEvidenceProfile {
    /// Overall is NOT_PRODUCTION_SUPPORTED unless replication + selection +
    /// falsification boundaries all hold and no hard gate failed.
    pub fn derive_conclusion(&self) -> EconomicConclusion {
        if self.gates.iter().any(|g| g.is_blocking()) {
            return EconomicConclusion::NotProductionSupported;
        }
        if !matches!(self.frozen_oos, FrozenOOSState::Pass { .. }) {
            return EconomicConclusion::NotProductionSupported;
        }
        if matches!(self.live, LiveState::Live { .. }) {
            return EconomicConclusion::LiveSupported;
        }
        if matches!(self.shadow, ShadowState::Active { .. }) {
            return EconomicConclusion::ProspectivelySupported;
        }
        // Frozen-OOS pass alone is bounded replication, still not production.
        EconomicConclusion::NotProductionSupported
    }

    /// Human-readable typed rendering. The quad number never appears bare.
    pub fn render_text(&self) -> String {
        let mut out = String::new();
        out.push_str("POLICY EVIDENCE PROFILE\n");
        out.push_str(&format!("policy_id: {}\n", self.policy_id));
        out.push_str(&format!("policy_hash: {}\n", self.policy_hash));
        out.push_str(&format!("case: {} epoch: {}\n", (self.evaluation_case_id).0, (self.epoch_id).0));
        out.push_str(&format!(
            "Historical Diagnostic Net Growth: {:+.2}$ (gross {:+.2}$, fees -{:.2}$)\n",
            self.historical_net_usdt, self.historical_gross_usdt, self.historical_fee_usdt
        ));
        out.push_str(&format!(
            "Data role: {} | Economic promotion authority: {}\n",
            self.historical_role.as_str(),
            self.historical_role.promotion_authority()
        ));
        out.push_str(&format!(
            "Scenarios: {}/{} survived | failed: {} | unknown: {}\n",
            self.scenario_cells.iter().filter(|c| c.survival).count(),
            self.scenario_cells.len(),
            self.robustness.failed_scenario_families.join(","),
            self.robustness.unknown_regions.join(",")
        ));
        if let Some(d) = &self.robustness.nearest_plausible_defeater {
            out.push_str(&format!("Nearest validated plausible defeater: {d}\n"));
        }
        out.push_str(&format!("Frozen-OOS: {:?}\n", self.frozen_oos));
        out.push_str(&format!("Shadow: {:?}\n", self.shadow));
        out.push_str(&format!("Live: {:?}\n", self.live));
        out.push_str(&format!("Certificate: {:?}\n", self.certificate));
        out.push_str(&format!("Conclusion: {}\n", self.conclusion.as_str()));
        out
    }
}

/// G0: constitutional / causal integrity. Hard failure blocks everything.
pub fn gate_g0(has_pit_violation: bool, has_synthetic_leak: bool, receipts_valid: bool) -> GateVerdict {
    if has_pit_violation || has_synthetic_leak || !receipts_valid {
        GateVerdict::fail_closed(
            GateId::G0ConstitutionalIntegrity,
            "PIT_LEAK_OR_SYNTHETIC_LEAK_OR_RECEIPT_INVALID",
            &["SUPPORTED_EDGE", "REALIZED_CASHFLOW"],
        )
    } else {
        GateVerdict::pass(GateId::G0ConstitutionalIntegrity, "CAUSAL_AND_RECEIPT_INTEGRITY_OK", "DIAGNOSTIC_ONLY")
    }
}

/// G1: measurement identity & data-role integrity.
pub fn gate_g1(estimand_set: bool, data_role_set: bool, lineage_registered: bool) -> GateVerdict {
    if estimand_set && data_role_set && lineage_registered {
        GateVerdict::pass(GateId::G1MeasurementIdentity, "ESTIMAND_AND_ROLE_AND_LINEAGE_OK", "DIAGNOSTIC_ONLY")
    } else {
        GateVerdict::fail_closed(GateId::G1MeasurementIdentity, "MEASUREMENT_IDENTITY_INCOMPLETE", &["SUPPORTED_EDGE"])
    }
}

/// Claim-scoped synthetic defeater authority (D-150 asymmetry).
///
/// - Synthetic PASS never mints economic authority (always false).
/// - Synthetic FAIL challenges `claim` only when the passport passed AND the
///   claim admits synthetic relevance (StructuralRobustness-class). A garbage
///   generator (`passport_passed == false`) can never veto anything.
pub fn synthetic_fail_may_challenge(passport: &GeneratorPassport, claim: AssuranceClaim) -> bool {
    if !passport.passport_passed {
        return false;
    }
    if !passport.does_not_confer_economic_edge() {
        return false;
    }
    matches!(
        claim,
        AssuranceClaim::StructuralRobustness
            | AssuranceClaim::EngineeringIntegrity
            | AssuranceClaim::SemanticIntegrity
            | AssuranceClaim::ResearchIntegrity
    )
}

/// Synthetic PASS confers zero economic authority by construction.
pub fn synthetic_pass_confirms_no_edge(_passport: &GeneratorPassport) -> bool {
    true
}

/// Statistical triple audit (D-152 §7). Keeps WRC + genuine DSR + SPA as the
/// active burden; documents that the current in-tree multiplicity ledger uses
/// proxy PBO/DSR formulas and therefore cannot satisfy G5.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StatisticalTripleAudit {
    pub wrc_genuine: bool,
    pub dsr_genuine: bool,
    pub spa_genuine: bool,
    pub blocks_support: bool,
    pub rationale: String,
}

pub fn audit_statistical_triple() -> StatisticalTripleAudit {
    StatisticalTripleAudit {
        wrc_genuine: false,
        dsr_genuine: false,
        spa_genuine: false,
        blocks_support: true,
        rationale: "WRC_UNWIRED_DSR_PROXY_SPA_UNWIRED: multiplicity ledger uses analytic proxy formulas; genuine block-bootstrap WRC, covariance-penalized DSR and Hansen SPA receipts are absent, so G5 remains NO_ECONOMIC_CLAIM".to_string(),
    }
}
