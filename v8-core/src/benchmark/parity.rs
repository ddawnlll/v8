//! Policy-bound external parity adapters (#329; D-153 §§2.6, 3.2-3.3, 4.6; D-116).
//!
//! # The defect this module closes
//!
//! `external.rs::evaluate_parity(policy_id)` accepted a policy id, discarded it
//! (`_policy_id`), and compared two hardcoded in-process arrays:
//!
//! ```text
//! let native   = [0.012, -0.005, 0.008, 0.015, -0.002];
//! let external = [0.0121, -0.0049, 0.0081, 0.0149, -0.002];
//! ```
//!
//! Those literals are not V8 output and not LEAN output. They were chosen to sit
//! inside the adapter's own tolerance, so every "parity" result was
//! (a) predetermined, (b) unrelated to the policy named in the call, and (c)
//! unrelated to any artifact on disk. Two further fields were fabricated rather
//! than measured: `fill_timing_mae_ms` was a constant `0.0` (indistinguishable
//! from "measured, zero error", i.e. absence reported as perfect agreement), and
//! `maximum_drawdown_discrepancy_bps` was `pnl_discrepancy_bps * 1.5` (or `* 1.2`,
//! `* 1.1`) — a made-up multiplier with no drawdown anywhere in sight.
//!
//! So the module demonstrated that a number it wrote down equals a number it wrote
//! down. It could not have failed.
//!
//! # The contract now
//!
//! `ParityRun` consumes a [`ParitySubject`] (case + policy identity, bound so a
//! result cannot be re-labelled onto another policy), two **physical** trade
//! ledgers verified through #328's [`ArtifactBinding`], and a versioned
//! [`SemanticMapping`]. It emits a [`ParityReceipt`] whose identity covers policy,
//! artifact, mapping and engine hashes (issue §13).
//!
//! Missing or unverifiable input yields `DataBlocked`/`Unknown`, never a zero
//! difference and never a pass (AGENTS.md: absence is recorded, not synthesized).
//!
//! ## Parity is exact, per the registered spec
//!
//! `PARITY_AND_IDENTITY_SPEC` §3: *"Floating point: equality of the IEEE-754 bit
//! pattern, not `==`. ... Tolerance-based comparison is not permitted anywhere in
//! the parity path."* The pre-#329 adapters gated `parity_passed` on a bps
//! tolerance, which the spec forbids. Here the verdict is bit-pattern equality of
//! every paired value, and magnitudes (mean/max bps divergence) are reported as
//! *diagnostics* beside it — an engineer may read them, and no gate may consume
//! them as a pass.
//!
//! ## Honest scope: this is trade-PnL parity, not D-116 monetary parity
//!
//! D-116 requires differential reconciliation of *"every order, fill, commission,
//! funding payment, and terminal wallet balance"* before an economic claim. This
//! adapter compares paired per-trade PnL, fill times, order semantics and the
//! resulting equity curve. Commissions, funding and balance settlement are not
//! compared, because no field for them is declared in [`SemanticMapping`] yet.
//! That gap is therefore reported in
//! [`ParityReceipt::reconciliation_gaps`] on every receipt, agreement included,
//! so an exact match here reads as "the trade paths agree" and cannot be
//! mistaken for "the monetary accounting agrees". Closing it means adding the
//! cost fields to the mapping (and bumping `MAPPING_VERSION`), not deleting the
//! gap note.
//!
//! ## Adapters are instruments, not authorities (#329 R3)
//!
//! [`ParityReceipt::authority`] is `EvidenceAuthority::None` for every outcome
//! including `ExactMatch`, and [`ParityReceipt::to_observation`] emits an
//! observation whose authority string marks it non-sovereign. D-153 §2.1 keeps
//! `SUPPORTED_EDGE` with the ClaimRegistry; a parity receipt is input to G0-G3
//! class diagnostic domains and can never raise economic authority
//! (see [`crate::benchmark::gate_authority::cap_authority`]).

use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::path::Path;

use crate::assurance::evidence_profile::DataRole;
use crate::benchmark::case::BenchmarkCase;
use crate::benchmark::observation::MetricObservation;
use crate::benchmark::receipt::{ArtifactBinding, ArtifactVerifyError};
use crate::benchmark::types::CapabilityDomain;
use crate::hash::Canon;

/// Semantic version of the native↔reference mapping rules.
///
/// Bumped only by a registered change to [`SemanticMapping`]'s rules: a mapping
/// change alters what "the same fill" means, so it must invalidate every parity
/// result recorded under the old mapping (issue §13).
pub const MAPPING_VERSION: &str = "v8.d153.parity.mapping.v1";

/// Digest generation for parity identity.
pub const PARITY_IDENTITY_VERSION: &str = "d153.parity.v1";

/// The authority ceiling for every parity result: diagnostic only, never
/// realized, never economic. Reuses #327's floor rather than defining a parallel
/// one (#327 non-goal: no parallel authority root).
pub const PARITY_INSTRUMENT_AUTHORITY: crate::authority::Authority =
    crate::benchmark::gate_authority::BENCHMARK_DIAGNOSTIC_AUTHORITY;

/// Stable authority string for a non-sovereign instrument.
///
/// Spelled out rather than left implicit so it cannot be mistaken for the
/// `"measured"` authority string real statistical evidence carries.
pub const NON_SOVEREIGN_INSTRUMENT_STATUS: &str = "external_instrument_non_sovereign";

/// Which engine produced a reference ledger.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ReferenceEngine {
    Lean,
    Skfolio,
    VectorBt,
}

impl ReferenceEngine {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Lean => "QuantConnect-LEAN",
            Self::Skfolio => "skfolio",
            Self::VectorBt => "vectorbt",
        }
    }
}

/// Policy and case identity a parity result belongs to (#329 R1).
///
/// Captured from a [`BenchmarkCase`] so the ids cannot be invented after the
/// fact, and bound into the receipt identity so a result about `pol_A` cannot be
/// re-tagged as evidence about `pol_B`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParitySubject {
    pub case_id: String,
    pub case_hash: String,
    pub policy_id: String,
    pub commit_hash: String,
    pub binary_digest: String,
    pub family: String,
}

impl ParitySubject {
    pub fn from_case(case: &BenchmarkCase) -> Self {
        Self {
            case_id: case.case_id.clone(),
            case_hash: case.case_hash.clone(),
            policy_id: case.target.policy_id.clone(),
            commit_hash: case.target.commit_hash.clone(),
            binary_digest: case.target.binary_digest.clone(),
            family: case.target.family.clone(),
        }
    }

    /// The subject is only usable if it identifies a policy and a case.
    pub fn missing_fields(&self) -> Vec<&'static str> {
        let mut out = Vec::new();
        let blank = |s: &str| s.trim().is_empty();
        if blank(&self.case_id) {
            out.push("case_id");
        }
        if blank(&self.case_hash) {
            out.push("case_hash");
        }
        if blank(&self.policy_id) {
            out.push("policy_id");
        }
        if blank(&self.commit_hash) {
            out.push("commit_hash");
        }
        if blank(&self.binary_digest) {
            out.push("binary_digest");
        }
        out
    }
}

/// How native and reference trade records are paired, and what counts as the
/// same fill (#329 R1, §13).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SemanticMapping {
    pub mapping_version: String,
    /// Key field used to pair records across the two ledgers.
    pub pairing_key: String,
    /// Order semantics this mapping can express. Anything else in an artifact is
    /// `UnsupportedSemantics`, never a silent skip (BFS-015).
    pub supported_order_types: Vec<String>,
    /// Field carrying the per-trade PnL/return on both sides.
    pub pnl_field: String,
    /// Optional field carrying fill time in integer nanoseconds on both sides.
    #[serde(default)]
    pub fill_time_field: Option<String>,
    /// Optional field carrying an integer sequence number used to order each
    /// ledger's own equity curve.
    ///
    /// `None` (the default) orders by physical file order, which is deterministic
    /// but puts the onus on the exporting tool to write chronologically. `Some(f)`
    /// requires *every* record to carry `f`: a partially sequenced ledger is
    /// refused rather than ordered by a splice of two different rules, and the
    /// drawdown diagnostic is reported as absent instead of invented. Declaring a
    /// sequence field changes the mapping hash, so results under the two ordering
    /// rules are never interchangeable.
    #[serde(default)]
    pub sequence_field: Option<String>,
}

impl Default for SemanticMapping {
    fn default() -> Self {
        Self {
            mapping_version: MAPPING_VERSION.to_string(),
            pairing_key: "trade_id".to_string(),
            supported_order_types: vec![
                "MARKET".into(),
                "LIMIT".into(),
                "STOP_MARKET".into(),
            ],
            pnl_field: "pnl".to_string(),
            fill_time_field: Some("fill_time_ns".to_string()),
            sequence_field: None,
        }
    }
}

impl SemanticMapping {
    /// Hash of the mapping rules. Part of parity identity, so editing a rule
    /// invalidates every result recorded under it.
    pub fn mapping_hash(&self) -> String {
        let mut canon = Canon::new();
        canon.push_str("SemanticMapping");
        canon.push_str(&self.mapping_version);
        canon.push_str(&self.pairing_key);
        canon.push_str(&self.pnl_field);
        canon.push_count(self.supported_order_types.len());
        // Sorted: the set is the contract, its declaration order is not.
        let mut types = self.supported_order_types.clone();
        types.sort();
        for t in types {
            canon.push_str(&t);
        }
        match &self.fill_time_field {
            None => canon.push_null(),
            Some(f) => canon.push_str(f),
        }
        match &self.sequence_field {
            None => canon.push_null(),
            Some(f) => canon.push_str(f),
        }
        canon.finish_sha256_hex()
    }

    pub fn supports_order_type(&self, order_type: &str) -> bool {
        self.supported_order_types.iter().any(|t| t == order_type)
    }
}

/// A declared reference engine build. Version is mandatory: a parity result
/// against an unidentified engine build is not reproducible, so it is not
/// evidence (issue §14: missing provenance -> blocked).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngineVersion {
    pub engine: ReferenceEngine,
    pub version: String,
    /// Hash of the reference engine's own build/commit, when the tool exposes one.
    /// `None` is a recorded absence, reported in
    /// [`ParityReceipt::provenance_gaps`], not a zero hash.
    #[serde(default)]
    pub engine_build_hash: Option<String>,
}

impl EngineVersion {
    pub fn new(engine: ReferenceEngine, version: &str) -> Result<Self, String> {
        if is_placeholder(version) {
            return Err(format!(
                "BLOCKED_ENGINE_VERSION_UNKNOWN: {} parity requires a declared \
                 reference engine version, got {version:?}",
                engine.as_str()
            ));
        }
        Ok(Self {
            engine,
            version: version.to_string(),
            engine_build_hash: None,
        })
    }

    pub fn with_build_hash(mut self, hash: &str) -> Result<Self, String> {
        if is_placeholder(hash) {
            return Err(format!(
                "BLOCKED_ENGINE_BUILD_HASH_EMPTY: {hash:?} is empty or a placeholder"
            ));
        }
        self.engine_build_hash = Some(hash.to_string());
        Ok(self)
    }

    pub fn identity(&self) -> String {
        match &self.engine_build_hash {
            None => format!("{}@{}", self.engine.as_str(), self.version),
            Some(h) => format!("{}@{}+{}", self.engine.as_str(), self.version, h),
        }
    }
}

/// A declared physical ledger plus its verified hash (#329 R2, Rule 5).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParityArtifact {
    pub role: String,
    pub binding: ArtifactBinding,
    pub rows: usize,
}

/// Outcome of loading and pairing a ledger.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct LedgerRecord {
    key: String,
    pnl: f64,
    order_type: Option<String>,
    fill_time_ns: Option<i64>,
    seq: Option<i64>,
    /// Position in the file, used only when no sequence field is declared.
    file_order: usize,
}

/// Errors that stop a parity run before any comparison happens.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParityBlocked {
    /// Subject does not identify a policy/case.
    IncompleteSubject { fields: Vec<&'static str> },
    /// Mapping version is not the registered one, or the mapping is unusable.
    MappingUnusable { reason: String },
    /// Declared artifact could not be read or hashed.
    ArtifactUnreadable { role: String, reason: String },
    /// Artifact hash does not match the declared binding (tamper-at-rest).
    ArtifactMismatch { role: String, error: ArtifactVerifyError },
    /// Ledger is empty. An empty ledger is not "zero disagreement".
    EmptyLedger { role: String },
    /// A required field is missing or non-finite in a record.
    InvalidRecord { role: String, key: String, reason: String },
    /// Duplicate pairing keys: which record is "the" trade is undefined.
    AmbiguousKeys { role: String, key: String },
}

impl std::fmt::Display for ParityBlocked {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::IncompleteSubject { fields } => write!(
                f,
                "BLOCKED_PARITY_SUBJECT_INCOMPLETE: {}",
                fields.join(",")
            ),
            Self::MappingUnusable { reason } => {
                write!(f, "BLOCKED_PARITY_MAPPING_UNUSABLE: {reason}")
            }
            Self::ArtifactUnreadable { role, reason } => {
                write!(f, "DATA_BLOCKED_PARITY_ARTIFACT_UNREADABLE [{role}]: {reason}")
            }
            Self::ArtifactMismatch { role, error } => {
                write!(f, "DATA_BLOCKED_PARITY_ARTIFACT_MISMATCH [{role}]: {error}")
            }
            Self::EmptyLedger { role } => {
                write!(f, "DATA_BLOCKED_PARITY_LEDGER_EMPTY [{role}]")
            }
            Self::InvalidRecord { role, key, reason } => write!(
                f,
                "DATA_BLOCKED_PARITY_RECORD_INVALID [{role}/{key}]: {reason}"
            ),
            Self::AmbiguousKeys { role, key } => write!(
                f,
                "BLOCKED_PARITY_AMBIGUOUS_KEYS [{role}]: duplicate pairing key {key}"
            ),
        }
    }
}

impl std::error::Error for ParityBlocked {}

/// Verdict of a parity run.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ParityOutcome {
    /// Every paired value is bit-identical and no semantics are unsupported.
    /// Note this is *not* a claim that either engine is right (D-153 §2.6).
    ExactMatch,
    /// Comparison ran on real artifacts and the engines disagree.
    Diverged,
    /// An order semantics appeared that the mapping cannot express (BFS-015).
    /// No parity conclusion is drawn: "unsupported" is not "matching".
    UnsupportedSemantics { order_type: String },
    /// One side has a key the other lacks (or vice versa). Structural
    /// disagreement; never scored as zero difference.
    UnpairedRecords { native_only: usize, reference_only: usize },
    /// Input was missing, unreadable, hash-mismatched or empty.
    DataBlocked { reason: String },
}

impl ParityOutcome {
    pub fn code(&self) -> &'static str {
        match self {
            Self::ExactMatch => "PARITY_EXACT_MATCH",
            Self::Diverged => "PARITY_DIVERGED",
            Self::UnsupportedSemantics { .. } => "PARITY_UNSUPPORTED_SEMANTICS",
            Self::UnpairedRecords { .. } => "PARITY_UNPAIRED_RECORDS",
            Self::DataBlocked { .. } => "DATA_BLOCKED",
        }
    }

    /// `true` only for a completed comparison over verified artifacts that found
    /// exact agreement. `DataBlocked` and `Unknown`-class outcomes are excluded,
    /// so absence can never be read as agreement.
    pub fn is_agreement(&self) -> bool {
        matches!(self, Self::ExactMatch)
    }

    /// Machine code plus the reason it fired, for notes and receipts.
    pub fn detail(&self) -> String {
        match self {
            Self::DataBlocked { reason } => format!("{}: {reason}", self.code()),
            Self::UnsupportedSemantics { order_type } => {
                format!("{}: {order_type}", self.code())
            }
            Self::UnpairedRecords { native_only, reference_only } => format!(
                "{}: native_only={native_only} reference_only={reference_only}",
                self.code()
            ),
            other => other.code().to_string(),
        }
    }
}

/// Measured divergence magnitudes.
///
/// Diagnostics only. `PARITY_AND_IDENTITY_SPEC` §3 forbids tolerance-based
/// parity, so nothing here may be consumed as a pass/fail gate; they exist so an
/// engineer can size a disagreement after [`ParityOutcome::Diverged`] says one
/// exists.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParityDiagnostics {
    pub paired_records: usize,
    /// Paired records that diverged: differing PnL bit patterns, or differing
    /// fill times where both sides recorded one.
    pub mismatched_records: usize,
    /// Mean absolute per-record divergence, in bps. `None` when no pairs.
    pub mean_abs_divergence_bps: Option<f64>,
    /// Largest single-record divergence, in bps. `None` when no pairs.
    pub max_abs_divergence_bps: Option<f64>,
    /// Terminal (summed) PnL difference, in bps. `None` if either side empty.
    pub terminal_divergence_bps: Option<f64>,
    /// Sign disagreement between the two terminal results (BFS-009).
    pub terminal_sign_disagreement: bool,
    /// Mean absolute fill-time error in ms. `None` when either side lacks fill
    /// times — the pre-#329 code reported `0.0` here, which read as "perfect
    /// timing" for a quantity that was never measured.
    pub fill_timing_mae_ms: Option<f64>,
    /// Difference of the two maximum drawdowns, in bps, computed from each
    /// ledger's own equity curve. `None` when a curve cannot be built (no
    /// declared order, or a partially sequenced ledger). The pre-#329 code
    /// fabricated this as `pnl_discrepancy * 1.5`.
    pub max_drawdown_divergence_bps: Option<f64>,
}

impl Default for ParityDiagnostics {
    fn default() -> Self {
        Self {
            paired_records: 0,
            mismatched_records: 0,
            mean_abs_divergence_bps: None,
            max_abs_divergence_bps: None,
            terminal_divergence_bps: None,
            terminal_sign_disagreement: false,
            fill_timing_mae_ms: None,
            max_drawdown_divergence_bps: None,
        }
    }
}

/// A parity receipt: identity-bound, non-authoritative, and explicit about
/// absence (#329 R1-R4).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParityReceipt {
    pub identity_version: String,
    /// H(policy ‖ case ‖ native artifact ‖ reference artifact ‖ mapping ‖ engine).
    /// Distinct inputs can never share a receipt (issue §13).
    pub parity_identity: String,
    pub subject: ParitySubject,
    pub engine: EngineVersion,
    pub mapping_hash: String,
    /// Method version this receipt was computed under. Part of identity.
    pub method_version: String,
    pub native: Option<ParityArtifact>,
    pub reference: Option<ParityArtifact>,
    pub outcome: ParityOutcome,
    pub diagnostics: ParityDiagnostics,
    /// Declared-but-absent provenance, e.g. an engine that exposes no build hash.
    pub provenance_gaps: Vec<String>,
    /// Comparison scope this receipt does **not** cover, e.g. D-116 commission
    /// and funding reconciliation. Always non-empty today; see the module docs.
    pub reconciliation_gaps: Vec<String>,
    pub computed_at_timestamp_ns: u64,
}

impl ParityReceipt {
    /// Authority this receipt contributes, always the benchmark diagnostic floor
    /// (#329 R3, D-153 §2.1/§2.6).
    ///
    /// Computed, never stored: there is no field an attacker or a careless
    /// deserializer can set to `PortfolioAuthorized`. `evidence` is `Observed`
    /// because the ledgers are physically verified, but `decision` is pinned to
    /// `DiagnosticOnly` and `realization` to `Hypothetical`, so parity agreement
    /// can raise a diagnostic confidence and nothing else. D-153 §2.1 keeps
    /// `SUPPORTED_EDGE` exclusively with the ClaimRegistry.
    pub fn authority(&self) -> crate::authority::Authority {
        PARITY_INSTRUMENT_AUTHORITY
    }

    /// Machine-readable status string for rendering. A method, not a field: a
    /// stored `authority: String` could be overwritten in the persisted JSON and
    /// then read back as a claim, which is the hazard #329 exists to close.
    pub fn authority_class(&self) -> &'static str {
        NON_SOVEREIGN_INSTRUMENT_STATUS
    }

    /// Recompute the identity from the inputs. Public so an auditor can verify
    /// the stamped value rather than trust it.
    pub fn compute_parity_identity(
        subject: &ParitySubject,
        engine: &EngineVersion,
        mapping_hash: &str,
        method_version: &str,
        native: Option<&ParityArtifact>,
        reference: Option<&ParityArtifact>,
    ) -> String {
        let mut canon = Canon::new();
        canon.push_str(PARITY_IDENTITY_VERSION);
        canon.push_str(&subject.case_id);
        canon.push_str(&subject.case_hash);
        canon.push_str(&subject.policy_id);
        canon.push_str(&subject.commit_hash);
        canon.push_str(&subject.binary_digest);
        canon.push_str(&subject.family);
        canon.push_str(&engine.identity());
        canon.push_str(mapping_hash);
        canon.push_str(method_version);
        for artifact in [native, reference] {
            match artifact {
                None => canon.push_null(),
                Some(a) => {
                    canon.push_str(&a.role);
                    canon.push_str(&a.binding.sha256_hex);
                    canon.push_u64(a.binding.bytes);
                    canon.push_count(a.rows);
                }
            }
        }
        canon.finish_sha256_hex()
    }

    pub fn verify_identity(&self) -> bool {
        self.identity_version == PARITY_IDENTITY_VERSION
            && self.parity_identity
                == Self::compute_parity_identity(
                    &self.subject,
                    &self.engine,
                    &self.mapping_hash,
                    &self.method_version,
                    self.native.as_ref(),
                    self.reference.as_ref(),
                )
    }

    /// Project the receipt into a benchmark observation.
    ///
    /// Only a completed comparison contributes a value. Every non-agreement
    /// outcome is recorded as a failed floor with `raw_value = 0.0` *and* an
    /// explicit `reason` in `notes`, while `DataBlocked` records absence: the
    /// coverage machinery, not a fake number, is what must penalize missing data
    /// (D-153 §3.4, BFS-002).
    pub fn to_observation(&self) -> MetricObservation {
        let metric_id = format!("external_parity::{}", self.engine.engine.as_str());
        let (raw, passed, detail) = match &self.outcome {
            ParityOutcome::ExactMatch => (
                1.0,
                true,
                format!(
                    "{}: {} paired records bit-identical",
                    self.outcome.code(),
                    self.diagnostics.paired_records
                ),
            ),
            ParityOutcome::Diverged => (
                0.0,
                false,
                format!(
                    "{}: {}/{} paired records differ at bit level",
                    self.outcome.code(),
                    self.diagnostics.mismatched_records,
                    self.diagnostics.paired_records
                ),
            ),
            other => (0.0, false, other.detail()),
        };
        // The parity identity travels in the note so the observation can be
        // traced back to the exact artifact/mapping/engine triple that produced
        // it. An observation that cannot be traced is not evidence.
        let notes = format!("{detail} | parity_identity={}", self.parity_identity);
        let mut obs = MetricObservation::new(
            metric_id,
            CapabilityDomain::ExecutionFidelity,
            NON_SOVEREIGN_INSTRUMENT_STATUS,
            self.subject_data_role(),
            raw,
            raw,
            raw,
            raw,
            self.diagnostics.paired_records,
            self.diagnostics.paired_records as f64,
            passed,
        );
        obs.notes = notes;
        obs
    }

    /// Data role this observation carries: `Development`, unconditionally.
    ///
    /// `DataRole` drives promotion weight, and `Development` is the only role
    /// whose `promotion_authority()` is `NONE` that also does not imply the data
    /// was burned. A parity run cannot know the holdout status of a reference
    /// engine's ledger from two files alone, and guessing `FrozenOOS` would let
    /// an external instrument mint replication authority it is not entitled to
    /// (BFS-011, D-153 §2.6).
    fn subject_data_role(&self) -> DataRole {
        DataRole::Development
    }
}

/// Strings that look like provenance but carry none. Checked case-insensitively
/// after trimming, because "N/A", "unknown" and "TBD" are how an absent value
/// gets written into a field that has no way to express absence — and a version
/// field that can be filled with a placeholder is a version field that will be.
pub const PLACEHOLDER_VERSIONS: &[&str] = &[
    "n/a",
    "na",
    "none",
    "null",
    "nil",
    "unknown",
    "tbd",
    "todo",
    "placeholder",
    "unspecified",
    "-",
    "--",
    "?",
];

fn is_placeholder(value: &str) -> bool {
    let lowered = value.trim().to_ascii_lowercase();
    lowered.is_empty() || PLACEHOLDER_VERSIONS.contains(&lowered.as_str())
}

/// Reject empty or placeholder method versions, mirroring
/// [`crate::benchmark::receipt::BenchmarkReceipt::with_method_version`]: a
/// version field filled with "N/A" looks like provenance and carries none, so it
/// must be refused at the boundary rather than sealed into an identity.
pub fn check_method_version(version: &str) -> Result<(), String> {
    if is_placeholder(version) {
        return Err(format!(
            "BLOCKED_EMPTY_METHOD_VERSION: {version:?} is empty or a placeholder; \
             parity requires a real adapter method version"
        ));
    }
    Ok(())
}

/// Declared inputs to one parity run.
#[derive(Debug, Clone)]
pub struct ParityRequest {
    pub subject: ParitySubject,
    pub mapping: SemanticMapping,
    pub engine: EngineVersion,
    /// Adapter implementation version that ran the comparison. Distinct from
    /// [`SemanticMapping::mapping_version`]: the mapping is what "the same fill"
    /// means, the method is which code performed the pairing. Binding both lets
    /// a method refactor invalidate prior results without a mapping change, and
    /// vice versa.
    pub method_version: String,
    /// V8's own ledger, declared with the hash it must match.
    pub native_artifact: ArtifactBinding,
    /// The reference engine's ledger.
    pub reference_artifact: ArtifactBinding,
    pub computed_at_timestamp_ns: u64,
}

/// One adapter instance: which reference engine's output it reads.
///
/// The mapping is deliberately *not* adapter state. It is part of the declared
/// request, so there is exactly one mapping per run; holding it in two places
/// would let the comparison and the identity hash disagree about which semantics
/// were applied, which is the same class of defect #329 is fixing.
///
/// Adapters are constructed, never invoked by a runtime policy: D-153 §2.6 makes
/// them instruments, and BFS-021 forbids a policy reading them at decision time.
#[derive(Debug, Clone, Copy)]
pub struct ParityAdapter {
    pub engine: ReferenceEngine,
}

impl ParityAdapter {
    pub fn new(engine: ReferenceEngine) -> Self {
        Self { engine }
    }

    pub fn lean() -> Self {
        Self::new(ReferenceEngine::Lean)
    }
    pub fn skfolio() -> Self {
        Self::new(ReferenceEngine::Skfolio)
    }
    pub fn vectorbt() -> Self {
        Self::new(ReferenceEngine::VectorBt)
    }

    /// Run parity over two physical ledgers.
    ///
    /// Every failure mode is reported as `DataBlocked` with a reason; there is no
    /// path from "no data" to "agreement".
    pub fn run(&self, req: &ParityRequest) -> ParityReceipt {
        let gaps = self.provenance_gaps(req);
        let reconciliation_gaps: Vec<String> =
            reconciliation_gaps().iter().map(|g| g.to_string()).collect();

        if self.engine != req.engine.engine {
            return self.blocked(
                req,
                gaps,
                reconciliation_gaps,
                format!(
                    "BLOCKED_PARITY_ENGINE_MISMATCH: adapter is {} but the request \
                     declares {}",
                    self.engine.as_str(),
                    req.engine.engine.as_str()
                ),
                ParityDiagnostics::default(),
            );
        }

        if let Some(fields) = self.subject_gap(req) {
            return self.blocked(
                req,
                gaps,
                reconciliation_gaps,
                format!("{}", ParityBlocked::IncompleteSubject { fields }),
                ParityDiagnostics::default(),
            );
        }
        if let Err(reason) = check_method_version(&req.method_version) {
            return self.blocked(
                req,
                gaps,
                reconciliation_gaps,
                reason,
                ParityDiagnostics::default(),
            );
        }
        if let Some(reason) = self.mapping_gap(&req.mapping) {
            return self.blocked(
                req,
                gaps,
                reconciliation_gaps,
                reason,
                ParityDiagnostics::default(),
            );
        }

        let (native_records, reference_records) = match (
            self.load(&req.mapping, &req.native_artifact, "native"),
            self.load(&req.mapping, &req.reference_artifact, "reference"),
        ) {
            (Ok(n), Ok(r)) => (n, r),
            (Err(e), _) | (_, Err(e)) => {
                return self.blocked(
                    req,
                    gaps,
                    reconciliation_gaps,
                    e.to_string(),
                    ParityDiagnostics::default(),
                );
            }
        };

        let native = ParityArtifact {
            role: "native".into(),
            binding: req.native_artifact.clone(),
            rows: native_records.len(),
        };
        let reference = ParityArtifact {
            role: "reference".into(),
            binding: req.reference_artifact.clone(),
            rows: reference_records.len(),
        };

        let (outcome, diagnostics) = self.compare(
            &req.mapping,
            &native_records,
            &reference_records,
        );

        let parity_identity = ParityReceipt::compute_parity_identity(
            &req.subject,
            &req.engine,
            &req.mapping.mapping_hash(),
            &req.method_version,
            Some(&native),
            Some(&reference),
        );

        ParityReceipt {
            identity_version: PARITY_IDENTITY_VERSION.to_string(),
            parity_identity,
            subject: req.subject.clone(),
            engine: req.engine.clone(),
            mapping_hash: req.mapping.mapping_hash(),
            method_version: req.method_version.clone(),
            native: Some(native),
            reference: Some(reference),
            outcome,
            diagnostics,
            provenance_gaps: gaps,
            reconciliation_gaps,
            computed_at_timestamp_ns: req.computed_at_timestamp_ns,
        }
    }

    fn subject_gap(&self, req: &ParityRequest) -> Option<Vec<&'static str>> {
        let missing = req.subject.missing_fields();
        (!missing.is_empty()).then_some(missing)
    }

    fn mapping_gap(&self, mapping: &SemanticMapping) -> Option<String> {
        if mapping.mapping_version.trim().is_empty() {
            return Some(
                ParityBlocked::MappingUnusable {
                    reason: "mapping_version is blank".into(),
                }
                .to_string(),
            );
        }
        if mapping.pairing_key.trim().is_empty() || mapping.pnl_field.trim().is_empty() {
            return Some(
                ParityBlocked::MappingUnusable {
                    reason: "pairing_key and pnl_field are required".into(),
                }
                .to_string(),
            );
        }
        if mapping.supported_order_types.is_empty() {
            return Some(
                ParityBlocked::MappingUnusable {
                    reason: "no order semantics declared as supported".into(),
                }
                .to_string(),
            );
        }
        None
    }

    fn provenance_gaps(&self, req: &ParityRequest) -> Vec<String> {
        let mut gaps = Vec::new();
        if req.engine.engine_build_hash.is_none() {
            gaps.push(format!(
                "engine_build_hash absent for {}",
                req.engine.engine.as_str()
            ));
        }
        gaps
    }

    /// Verify the declared hash against the physical file, then parse it once.
    ///
    /// The hash check happens before the file is read, so an artifact that
    /// disagrees with its binding is never parsed and never contributes values
    /// to a comparison (Rule 5; #329 R2).
    fn load(
        &self,
        mapping: &SemanticMapping,
        binding: &ArtifactBinding,
        role: &str,
    ) -> Result<Vec<LedgerRecord>, ParityBlocked> {
        binding.verify_file().map_err(|error| {
            if error.is_missing_file() {
                ParityBlocked::ArtifactUnreadable {
                    role: role.into(),
                    reason: error.to_string(),
                }
            } else {
                ParityBlocked::ArtifactMismatch {
                    role: role.into(),
                    error,
                }
            }
        })?;
        let records = read_ledger(mapping, binding, role)?;
        if records.is_empty() {
            return Err(ParityBlocked::EmptyLedger { role: role.into() });
        }
        Ok(records)
    }

    fn compare(
        &self,
        mapping: &SemanticMapping,
        native_records: &[LedgerRecord],
        reference_records: &[LedgerRecord],
    ) -> (ParityOutcome, ParityDiagnostics) {
        // Unsupported semantics veto the whole comparison before any pairing: an
        // unmappable fill has no defined parity, so it must not be dropped and
        // must not be counted as agreement (BFS-015).
        for records in [native_records, reference_records] {
            for rec in records {
                if let Some(ot) = &rec.order_type {
                    if !mapping.supports_order_type(ot) {
                        return (
                            ParityOutcome::UnsupportedSemantics {
                                order_type: ot.clone(),
                            },
                            ParityDiagnostics::default(),
                        );
                    }
                }
            }
        }

        if native_records.is_empty() || reference_records.is_empty() {
            return (
                ParityOutcome::DataBlocked {
                    reason: ParityBlocked::EmptyLedger {
                        role: if native_records.is_empty() { "native" } else { "reference" }.into(),
                    }
                    .to_string(),
                },
                ParityDiagnostics::default(),
            );
        }

        let native_map: BTreeSet<String> = native_records.iter().map(|r| r.key.clone()).collect();
        let reference_map: BTreeSet<String> = reference_records
            .iter()
            .map(|r| r.key.clone())
            .collect();
        let native_only = native_map.difference(&reference_map).count();
        let reference_only = reference_map.difference(&native_map).count();

        let mut diag = ParityDiagnostics::default();
        // Paired records in deterministic key order, so the result cannot depend
        // on file ordering.
        let mut paired: Vec<&LedgerRecord> = Vec::new();
        let mut paired_ref: Vec<&LedgerRecord> = Vec::new();
        let mut ref_by_key: std::collections::BTreeMap<&str, &LedgerRecord> = Default::default();
        for r in reference_records {
            ref_by_key.insert(r.key.as_str(), r);
        }
        for n in native_records {
            if let Some(r) = ref_by_key.get(n.key.as_str()) {
                paired.push(n);
                paired_ref.push(r);
            }
        }

        diag.paired_records = paired.len();
        if paired.is_empty() {
            return (
                ParityOutcome::UnpairedRecords {
                    native_only,
                    reference_only,
                },
                diag,
            );
        }

        let mut sum_abs = 0.0f64;
        let mut max_abs = 0.0f64;
        let mut mismatches = 0usize;
        let mut timing_abs: Vec<f64> = Vec::new();
        for (n, r) in paired.iter().zip(paired_ref.iter()) {
            let mut diverged = false;
            // IEEE-754 bit-pattern equality, per spec §3, not `==`: this keeps
            // -0.0 vs 0.0 a divergence.
            if n.pnl.to_bits() != r.pnl.to_bits() {
                diverged = true;
                let d = (n.pnl - r.pnl).abs() * 10_000.0;
                sum_abs += d;
                max_abs = max_abs.max(d);
            }
            match (n.fill_time_ns, r.fill_time_ns) {
                (Some(a), Some(b)) => {
                    timing_abs.push(((a - b) as f64).abs() / 1_000_000.0);
                    // Two engines that filled the same trade at different
                    // instants have not produced the same execution, even if
                    // they happen to agree on the PnL. Timing is only compared
                    // where both sides recorded it: an unrecorded field is an
                    // absence, not agreement (and not the old hardcoded 0.0).
                    if a != b {
                        diverged = true;
                    }
                }
                _ => {}
            }
            if diverged {
                mismatches += 1;
            }
        }
        diag.mismatched_records = mismatches;
        if mismatches > 0 {
            diag.mean_abs_divergence_bps = Some(sum_abs / paired.len() as f64);
            diag.max_abs_divergence_bps = Some(max_abs);
        }
        if !timing_abs.is_empty() {
            diag.fill_timing_mae_ms =
                Some(timing_abs.iter().sum::<f64>() / timing_abs.len() as f64);
        }

        let native_terminal: f64 = native_records.iter().map(|r| r.pnl).sum();
        let reference_terminal: f64 = reference_records.iter().map(|r| r.pnl).sum();
        diag.terminal_divergence_bps = Some((native_terminal - reference_terminal).abs() * 10_000.0);
        diag.terminal_sign_disagreement = (native_terminal > 0.0 && reference_terminal < 0.0)
            || (native_terminal < 0.0 && reference_terminal > 0.0);

        // Real maximum-drawdown divergence, computed from each ledger's own
        // equity curve in that ledger's declared order. Either curve being
        // unorderable makes the diagnostic absent, not zero.
        let sequenced = mapping.sequence_field.is_some();
        if let (Some(nv), Some(rv)) = (
            curve_order(native_records, sequenced).and_then(|r| max_drawdown_bps(&r)),
            curve_order(reference_records, sequenced).and_then(|r| max_drawdown_bps(&r)),
        ) {
            diag.max_drawdown_divergence_bps = Some((nv - rv).abs());
        }

        let outcome = if native_only > 0 || reference_only > 0 {
            ParityOutcome::UnpairedRecords {
                native_only,
                reference_only,
            }
        } else if mismatches > 0 || diag.terminal_sign_disagreement {
            ParityOutcome::Diverged
        } else {
            ParityOutcome::ExactMatch
        };
        (outcome, diag)
    }

    fn blocked(
        &self,
        req: &ParityRequest,
        gaps: Vec<String>,
        reconciliation_gaps: Vec<String>,
        reason: String,
        diagnostics: ParityDiagnostics,
    ) -> ParityReceipt {
        let parity_identity = ParityReceipt::compute_parity_identity(
            &req.subject,
            &req.engine,
            &req.mapping.mapping_hash(),
            &req.method_version,
            None,
            None,
        );
        ParityReceipt {
            identity_version: PARITY_IDENTITY_VERSION.to_string(),
            parity_identity,
            subject: req.subject.clone(),
            engine: req.engine.clone(),
            mapping_hash: req.mapping.mapping_hash(),
            method_version: req.method_version.clone(),
            native: None,
            reference: None,
            outcome: ParityOutcome::DataBlocked { reason },
            diagnostics,
            provenance_gaps: gaps,
            reconciliation_gaps,
            computed_at_timestamp_ns: req.computed_at_timestamp_ns,
        }
    }
}

/// Parse a JSONL trade ledger through the mapping's field names.
///
/// Strict by design: an unparseable line, a missing pairing key, a non-numeric
/// or non-finite PnL, or a duplicate key blocks the whole run. Partial parses
/// would let a truncated artifact silently shrink the sample and still report
/// agreement over what survived.
fn read_ledger(
    mapping: &SemanticMapping,
    binding: &ArtifactBinding,
    role: &str,
) -> Result<Vec<LedgerRecord>, ParityBlocked> {
    let path = Path::new(&binding.path);
    let text = std::fs::read_to_string(path).map_err(|e| ParityBlocked::ArtifactUnreadable {
        role: role.into(),
        reason: format!("{e}"),
    })?;
    let mut out = Vec::new();
    let mut seen: BTreeSet<String> = BTreeSet::new();
    for (n, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(line).map_err(|e| ParityBlocked::InvalidRecord {
                role: role.into(),
                key: format!("line{n}"),
                reason: format!("unparseable JSON: {e}"),
            })?;
        let obj = value.as_object().ok_or_else(|| ParityBlocked::InvalidRecord {
            role: role.into(),
            key: format!("line{n}"),
            reason: "record is not a JSON object".into(),
        })?;

        let key = obj
            .get(&mapping.pairing_key)
            .and_then(|v| match v {
                serde_json::Value::String(s) => Some(s.clone()),
                serde_json::Value::Number(num) => Some(num.to_string()),
                _ => None,
            })
            .ok_or_else(|| ParityBlocked::InvalidRecord {
                role: role.into(),
                key: format!("line{n}"),
                reason: format!("missing pairing key {:?}", mapping.pairing_key),
            })?;
        if !seen.insert(key.clone()) {
            return Err(ParityBlocked::AmbiguousKeys {
                role: role.into(),
                key,
            });
        }

        let pnl = obj
            .get(&mapping.pnl_field)
            .and_then(|v| v.as_f64())
            .ok_or_else(|| ParityBlocked::InvalidRecord {
                role: role.into(),
                key: key.clone(),
                reason: format!("missing or non-numeric {:?}", mapping.pnl_field),
            })?;
        if !pnl.is_finite() {
            return Err(ParityBlocked::InvalidRecord {
                role: role.into(),
                key,
                reason: "non-finite pnl".into(),
            });
        }

        let order_type = obj
            .get("order_type")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        let fill_time_ns = match &mapping.fill_time_field {
            None => None,
            Some(field) => obj.get(field).and_then(|v| v.as_i64()),
        };
        let seq = match &mapping.sequence_field {
            None => None,
            Some(field) => obj.get(field).and_then(|v| v.as_i64()),
        };

        out.push(LedgerRecord {
            key,
            pnl,
            order_type,
            fill_time_ns,
            seq,
            file_order: n,
        });
    }
    Ok(out)
}

/// What this parity run does not compare. Reported on every receipt, agreement
/// included, so a green result cannot be read as D-116 monetary parity.
pub fn reconciliation_gaps() -> [&'static str; 3] {
    [
        "commission/fee reconciliation not mapped (D-116)",
        "funding payment reconciliation not mapped (D-116)",
        "terminal wallet/balance settlement not mapped (D-116)",
    ]
}

/// Order records for equity-curve diagnostics, or `None` when they cannot be
/// ordered.
///
/// Three cases, and the distinction matters because a drawdown is a
/// time-ordered quantity:
///
/// - the mapping declares no sequence field: file order is the declared order,
///   so curve the curve on that and say so in the mapping hash;
/// - a sequence field is declared and every record carries it: order by it;
/// - a sequence field is declared but some records lack it: refuse. Sorting the
///   numbered rows by sequence and the unnumbered ones by position would splice
///   two different orderings into one curve, which fabricates a path between them.
fn curve_order(records: &[LedgerRecord], sequenced: bool) -> Option<Vec<LedgerRecord>> {
    let mut out = records.to_vec();
    if sequenced {
        if !out.iter().all(|r| r.seq.is_some()) {
            return None;
        }
        out.sort_by_key(|r| (r.seq.unwrap(), r.file_order));
    } else {
        out.sort_by_key(|r| r.file_order);
    }
    Some(out)
}

/// Peak-to-trough drawdown of a ledger's equity curve, in bps.
///
/// Returns `None` rather than 0.0 when the curve cannot be built, so an
/// unmeasurable quantity stays unmeasurable.
fn max_drawdown_bps(records: &[LedgerRecord]) -> Option<f64> {
    if records.is_empty() {
        return None;
    }
    let mut equity = 0.0f64;
    let mut peak = 0.0f64;
    let mut worst = 0.0f64;
    for r in records {
        equity += r.pnl;
        peak = peak.max(equity);
        worst = worst.min(equity - peak);
    }
    Some(-worst * 10_000.0)
}

/// Attach a parity receipt to a benchmark receipt (issue §15: parity receipt ->
/// `BenchmarkReceipt`/report).
///
/// This is the only supported way a parity result enters a receipt, and it is
/// deliberately narrow:
///
/// 1. **Identity must match.** The receipt's `policy_id`/`case_hash` must be the
///    subject the parity ran against. Without this check a parity result computed
///    for one policy could be grafted onto another policy's receipt, which is the
///    #329 defect in a new location.
/// 2. **Artifacts are bound, not described.** The native and reference
///    [`ArtifactBinding`]s are merged into the receipt's artifact list, so #328's
///    `verify_artifacts()` re-hashes the physical files at read time.
/// 3. **Digest is recomputed.** Parity changes what the receipt attests to, so
///    the stored digest must move with it.
/// 4. **A blocked parity run still attaches.** `DataBlocked` contributes a
///    failed-floor observation carrying `raw_value = 0.0` and the reason, and the
///    artifacts list stays empty. That is an honest negative record: coverage and
///    gates see the gap, and nothing pretends agreement was measured.
impl crate::benchmark::receipt::BenchmarkReceipt {
    pub fn with_parity(
        mut self,
        receipt: &ParityReceipt,
    ) -> Result<Self, String> {
        if !receipt.verify_identity() {
            return Err(format!(
                "BLOCKED_PARITY_IDENTITY_MISMATCH: parity receipt {} was edited \
                 after computation",
                receipt.parity_identity
            ));
        }
        if receipt.subject.policy_id != self.policy_id {
            return Err(format!(
                "BLOCKED_PARITY_POLICY_MISMATCH: receipt is for policy {:?}, \
                 parity ran against {:?}",
                self.policy_id, receipt.subject.policy_id
            ));
        }
        if receipt.subject.case_hash != self.case_hash {
            return Err(format!(
                "BLOCKED_PARITY_CASE_MISMATCH: receipt case_hash {:?}, \
                 parity subject case_hash {:?}",
                self.case_hash, receipt.subject.case_hash
            ));
        }

        self.observations.push(receipt.to_observation());
        for artifact in receipt.native.iter().chain(receipt.reference.iter()) {
            let already_bound = self
                .artifacts
                .iter()
                .any(|b| b.path == artifact.binding.path && b.role == artifact.binding.role);
            if !already_bound {
                self.artifacts.push(artifact.binding.clone());
            } else if self
                .artifacts
                .iter()
                .any(|b| b.path == artifact.binding.path && b.sha256_hex != artifact.binding.sha256_hex)
            {
                // Same file claimed with two hashes: one of the two attestations
                // is wrong, and we cannot tell which. Fail closed.
                return Err(format!(
                    "BLOCKED_PARITY_ARTIFACT_CONFLICT: {:?} is bound under two \
                     different hashes",
                    artifact.binding.path
                ));
            }
        }
        self.receipt_digest = self
            .compute_digest()
            .map_err(|e| format!("BLOCKED_RECEIPT_DIGEST: {e}"))?;
        Ok(self)
    }
}

/// Wall-clock stamp for a parity run, taken from the host clock.
///
/// Kept out of the identity hash (a recomputation minutes later must still
/// verify), and reported so an auditor can order runs. Deliberately not a
/// default-able `0`: callers must pass a real observation.
pub fn now_timestamp_ns() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0)
}
