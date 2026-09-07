//! BenchmarkReceipt and Cryptographic Binding (D-153 §§2-3, §111; #328).
//!
//! # The defect this module closes
//!
//! Before #328 the digest was minted by an ad-hoc `Sha256` sequence built by
//! hand in `generate_with_context`. That sequence covered 8 scalars,
//! `calibrated_score` + `passed_hard_invariants` per domain, and
//! `metric_id`/`raw_value`/`normalized_score` per observation. It omitted:
//!
//! - the **entire `GateVector`** — all ten G0-G9 states, the single most
//!   authority-relevant field in a receipt;
//! - `raw_score`, `sample_count`, `lower_bound`, `upper_bound`,
//!   `failure_reasons` per domain;
//! - `domain`, `authority`, `population_role`, `lower_bound_95`,
//!   `upper_bound_95`, `sample_size`, `effective_sample_size`, `passed_floor`,
//!   `notes` per observation;
//! - `peak_drawdown_pct`, `failure_predicate`, `defeater_receipt_id`;
//! - `minerva.raw_score` and the rest of `MinervaRobustness`;
//! - case identity, `BenchmarkVersion`, `spec_hash`, `commit_hash`,
//!   `binary_digest`, `family`, and any method/artifact provenance.
//!
//! So a persisted receipt could be edited to flip `g1_causal_pit` from
//! `Defeated` to `Pass`, or to change a gate's whole vector, and its digest
//! would still "verify". Every downstream consumer (`ledger.rs`, `report.rs`,
//! `certificate.rs`) trusted that digest.
//!
//! # The contract now
//!
//! `receipt_digest = H(canonical_encode(all_authority_relevant_fields))`
//! (issue §13), where:
//!
//! 1. The whole receipt minus `receipt_digest` itself is serialized to a
//!    `serde_json::Value` and pushed through [`crate::hash::Canon`] — the
//!    registered V8.2 identity encoder (`PARITY_AND_IDENTITY_SPEC` §4). No new
//!    hash algorithm and no parallel identity system (issue non-goal). That
//!    gives, for free: `f64` as 8 IEEE-754 little-endian bytes with a declared
//!    NaN payload rather than a decimal rendering; length-prefixed strings so
//!    field boundaries cannot collide; maps keyed in byte-sorted order so
//!    `HashMap` iteration order can never change a digest; and `Null` vs value
//!    tags so absence cannot collide with a default.
//! 2. Nested types owned by other contracts (`GateVector`, `MetricObservation`,
//!    `MinervaRobustness`) are bound structurally through their own
//!    `Serialize`, not by hand-enumerating fields. Deliberate: #327 is adding
//!    `GateState` variants concurrently, and a hand-written list would silently
//!    stop binding new authority-relevant data. With serde coverage, a field
//!    added to a nested type is bound the moment it exists.
//! 3. A domain-separator prefix carries the digest version, so a v1 and a v2
//!    digest can never be confused (spec §4.1: version boundaries are where
//!    identities are *allowed* to change).
//! 4. `Vec` order is bound as an ordered list, so reordering observations or
//!    artifacts changes the digest (a reordered ledger row is a different
//!    claim), while map reordering does not.
//!
//! Canon's dispatch was checked empirically against the spec's §3 distinctness
//! requirements rather than assumed: `0.0`, `-0.0` and `0` produce three
//! different digests, and a `f64` field never collides with the same-valued
//! integer, because serde_json only answers `as_i64()` for integer-typed
//! numbers. A hand-rolled re-encoder that preferred `as_f64()` was tried during
//! this fix and removed — it *creates* the 45 / 45.0 collision the spec forbids.

use serde::{Deserialize, Serialize};
use sha2::Digest as _;
use std::collections::HashMap;
use std::path::Path;

use crate::benchmark::case::BenchmarkCase;
use crate::benchmark::observation::MetricObservation;
use crate::benchmark::types::{CapabilityDomain, GateVector, ProjectionGrade};
use crate::hash::Canon;

/// Digest generation tag, bound into every receipt as a domain separator.
///
/// Declared as a constant rather than inferred from code layout so that a
/// future encoding change is an explicit, registered decision (D-153 non-goal:
/// no new hash algorithm or parallel identity system without a decision).
pub const RECEIPT_DIGEST_VERSION: &str = "d153.receipt.v2";

/// The legacy generation. Retained only so pre-#328 persisted receipts are
/// reported as *unbound* instead of being deleted or silently trusted —
/// historical evidence is annotated, never destroyed.
pub const RECEIPT_DIGEST_VERSION_LEGACY: &str = "d153.receipt.v1";

/// Source and method provenance of a benchmark evaluation (#328 R1).
///
/// Captured at construction from the [`BenchmarkCase`] so it cannot drift from
/// the identity the evaluation actually ran under. These fields are what make a
/// receipt interpretable: without `commit_hash` and `binary_digest` there is no
/// fact of the matter about which code produced a score.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BenchmarkProvenance {
    pub case_id: String,
    pub version_name: String,
    pub version_major: u32,
    pub version_minor: u32,
    pub version_patch: u32,
    pub spec_hash: String,
    pub commit_hash: String,
    pub binary_digest: String,
    pub family: String,
    /// Scoring / statistical method version. `None` is a *recorded absence*,
    /// never a placeholder string standing in for an unknown method.
    #[serde(default)]
    pub method_version: Option<String>,
}

impl BenchmarkProvenance {
    /// Derive provenance from the case that was evaluated.
    pub fn from_case(case: &BenchmarkCase) -> Self {
        Self {
            case_id: case.case_id.clone(),
            version_name: case.version.name.clone(),
            version_major: case.version.major,
            version_minor: case.version.minor,
            version_patch: case.version.patch,
            spec_hash: case.version.spec_hash.clone(),
            commit_hash: case.target.commit_hash.clone(),
            binary_digest: case.target.binary_digest.clone(),
            family: case.target.family.clone(),
            method_version: None,
        }
    }

    /// Identity fields required to interpret a receipt.
    ///
    /// Reported as a list rather than a boolean so a report can say *what* is
    /// missing (issue §14: missing provenance -> `DATA_BLOCKED` /
    /// `NO_ECONOMIC_CLAIM`), and `method_version` is deliberately excluded:
    /// its absence is legitimate and must stay representable.
    pub fn missing_fields(&self) -> Vec<&'static str> {
        let mut out = Vec::new();
        let blank = |s: &str| s.trim().is_empty();
        if blank(&self.case_id) {
            out.push("case_id");
        }
        if blank(&self.version_name) {
            out.push("version_name");
        }
        if blank(&self.spec_hash) {
            out.push("spec_hash");
        }
        if blank(&self.commit_hash) {
            out.push("commit_hash");
        }
        if blank(&self.binary_digest) {
            out.push("binary_digest");
        }
        if blank(&self.family) {
            out.push("family");
        }
        out
    }
}

impl Default for BenchmarkProvenance {
    /// An empty provenance is *representable* so that a legacy persisted receipt
    /// deserializes instead of erroring, after which `missing_fields()` reports
    /// exactly which identity fields are absent. It is never accepted by
    /// [`BenchmarkReceipt::verify`].
    fn default() -> Self {
        Self {
            case_id: String::new(),
            version_name: String::new(),
            version_major: 0,
            version_minor: 0,
            version_patch: 0,
            spec_hash: String::new(),
            commit_hash: String::new(),
            binary_digest: String::new(),
            family: String::new(),
            method_version: None,
        }
    }
}

/// A declared source artifact bound to a receipt (#328 R3, Rule 5).
///
/// Recording a hash is only a *claim* about an artifact; [`ArtifactBinding::verify_file`]
/// checks it against the physical file. A path that does not exist is reported,
/// never replaced by a placeholder or a zero hash.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArtifactBinding {
    /// Role the artifact played, e.g. `native_ledger`, `reference_ledger`.
    pub role: String,
    pub path: String,
    /// Lowercase hex SHA-256 of the artifact bytes.
    pub sha256_hex: String,
    pub bytes: u64,
}

impl ArtifactBinding {
    /// Hash a physical file and bind it. Fails closed if the file cannot be
    /// read: an unhashable artifact is never recorded as an empty binding.
    pub fn from_file(role: &str, path: &Path) -> Result<Self, String> {
        let bytes = std::fs::read(path)
            .map_err(|e| format!("DATA_BLOCKED_ARTIFACT_UNREADABLE {path:?}: {e}"))?;
        let len = bytes.len() as u64;
        Ok(Self {
            role: role.to_string(),
            path: path.to_string_lossy().into_owned(),
            sha256_hex: sha256_hex(&bytes),
            bytes: len,
        })
    }

    /// Recompute the file hash and compare against the binding.
    ///
    /// Length is checked before hashing: a truncated file is a different claim,
    /// and reporting the size discrepancy is more actionable than reporting an
    /// unrelated hash difference.
    pub fn verify_file(&self) -> Result<(), ArtifactVerifyError> {
        let path = Path::new(&self.path);
        let bytes = match std::fs::read(path) {
            Ok(b) => b,
            Err(_) => {
                return Err(ArtifactVerifyError::Missing {
                    path: self.path.clone(),
                })
            }
        };
        if bytes.len() as u64 != self.bytes {
            return Err(ArtifactVerifyError::LengthMismatch {
                path: self.path.clone(),
                expected: self.bytes,
                actual: bytes.len() as u64,
            });
        }
        let actual = sha256_hex(&bytes);
        if !constant_time_eq(&self.sha256_hex, &actual) {
            return Err(ArtifactVerifyError::HashMismatch {
                path: self.path.clone(),
                expected: self.sha256_hex.clone(),
                actual,
            });
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ArtifactVerifyError {
    /// Referenced artifact is not present on this machine.
    Missing { path: String },
    HashMismatch {
        path: String,
        expected: String,
        actual: String,
    },
    LengthMismatch {
        path: String,
        expected: u64,
        actual: u64,
    },
}

impl std::fmt::Display for ArtifactVerifyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Missing { path } => write!(f, "ARTIFACT_MISSING {path}"),
            Self::HashMismatch {
                path,
                expected,
                actual,
            } => write!(
                f,
                "ARTIFACT_HASH_MISMATCH {path}: expected {expected}, computed {actual}"
            ),
            Self::LengthMismatch {
                path,
                expected,
                actual,
            } => write!(
                f,
                "ARTIFACT_LENGTH_MISMATCH {path}: expected {expected} bytes, found {actual}"
            ),
        }
    }
}

impl std::error::Error for ArtifactVerifyError {}

impl ArtifactVerifyError {
    /// `true` when the failure is "the file is not here", as opposed to "the
    /// file is here and disagrees with the binding".
    ///
    /// The distinction matters: a receipt's digest already commits to the
    /// declared hash, so a *missing* file is an environment condition (another
    /// mount, a cleaned scratch dir) and says nothing about the bytes on the
    /// ledger, while a *mismatching* file means the recorded claim no longer
    /// matches the physical artifact. Callers fail closed on the latter and
    /// degrade to a warning on the latter — never on a silent pass.
    pub fn is_missing_file(&self) -> bool {
        matches!(self, Self::Missing { .. })
    }
}

/// Why a receipt is not trustworthy (#328 R1, R2, R3).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReceiptVerificationError {
    /// Stored digest does not equal the digest recomputed from current
    /// contents: the contents were mutated, or the digest was forged.
    DigestMismatch { stored: String, computed: String },
    /// Digest was minted under the pre-#328 subset encoding, which this encoder
    /// cannot reproduce. Never trusted for authority.
    UnversionedLegacy { digest_version: String },
    /// Provenance fields needed to interpret the receipt are absent.
    MissingProvenance { fields: Vec<&'static str> },
    /// A referenced artifact failed physical verification.
    Artifact(ArtifactVerifyError),
    /// A bound metric is NaN or infinite.
    ///
    /// `serde_json` cannot serialize such a value at all, so the only
    /// alternatives to rejecting it are to hash a declared poison marker (which
    /// would let two receipts with *different* non-finite values share one
    /// digest) or to let `Canon` normalize NaN into its single declared payload
    /// (which would make `NaN` and `-NaN`, or `inf` and `inf*2`, collide). Both
    /// are a silent collision in the identity layer. The receipt therefore
    /// fails closed and the poison is recorded rather than papered over.
    NonFiniteMetric,
    /// The receipt claims to evaluate one policy but carries another.
    IdentityMismatch { expected: String, actual: String },
    /// A `null` appeared in the canonical tree at a path that is not a declared
    /// optional field.
    ///
    /// This is how a non-finite `f64` reaches the encoder: serde_json's
    /// `serialize_f64` rewrites `Nan | Infinite` as JSON `null` rather than
    /// erroring, so a poisoned score is otherwise indistinguishable from an
    /// absent one in the tree. The field is either a coerced non-finite value or
    /// a new `Option` field not yet declared in `NULLABLE_FIELDS`; both must stop
    /// the pipeline rather than be sealed.
    UnexpectedNull { path: String },
}

impl std::fmt::Display for ReceiptVerificationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DigestMismatch { stored, computed } => write!(
                f,
                "RECEIPT_DIGEST_MISMATCH: stored {stored} != recomputed {computed}"
            ),
            Self::UnversionedLegacy { digest_version } => write!(
                f,
                "RECEIPT_UNVERSIONED_LEGACY: digest_version {digest_version:?} predates \
                 {RECEIPT_DIGEST_VERSION}; the subset encoding cannot be recomputed \
                 (row preserved, not trusted)"
            ),
            Self::MissingProvenance { fields } => {
                write!(f, "RECEIPT_MISSING_PROVENANCE: {}", fields.join(","))
            }
            Self::Artifact(e) => write!(f, "RECEIPT_{e}"),
            Self::NonFiniteMetric => write!(
                f,
                "RECEIPT_NON_FINITE_METRIC: a bound score is NaN or infinite; \
                 no trustworthy digest can be computed"
            ),
            Self::IdentityMismatch { expected, actual } => write!(
                f,
                "RECEIPT_IDENTITY_MISMATCH: expected policy {expected}, receipt carries {actual}"
            ),
            Self::UnexpectedNull { path } => write!(
                f,
                "RECEIPT_UNEXPECTED_NULL at {path}: either a non-finite metric was                  coerced to null by serde, or an optional field is missing from                  NULLABLE_FIELDS; neither may be sealed"
            ),
        }
    }
}

impl std::error::Error for ReceiptVerificationError {}

impl From<ArtifactVerifyError> for ReceiptVerificationError {
    fn from(e: ArtifactVerifyError) -> Self {
        Self::Artifact(e)
    }
}

/// Minimal defeater summary for benchmark reporting (D-153 §44)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MinimalDefeaterSummary {
    pub family: String,
    pub plausibility_distance: f64,
    pub peak_drawdown_pct: f64,
    pub failure_predicate: String,
    pub defeater_receipt_id: Option<String>,
}

/// Per-domain evaluation result
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DomainEvaluationResult {
    pub domain: CapabilityDomain,
    pub raw_score: f64,
    pub calibrated_score: f64,
    pub lower_bound: f64,
    pub upper_bound: f64,
    pub sample_count: usize,
    pub passed_hard_invariants: bool,
    pub failure_reasons: Vec<String>,
}

/// Cryptographically sealed benchmark receipt (D-153 §45, §111).
///
/// Every field except `receipt_digest` is bound into the digest, so the stored
/// digest can be recomputed and compared at any later read.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkReceipt {
    pub receipt_id: String,
    pub case_hash: String,
    pub policy_id: String,
    pub domain_results: HashMap<CapabilityDomain, DomainEvaluationResult>,
    pub composite_capability_score: f64,
    pub gate_vector: GateVector,
    pub coverage_factor: f64,
    pub observations: Vec<MetricObservation>,
    pub nearest_defeater: Option<MinimalDefeaterSummary>,
    pub minerva_robustness: Option<crate::benchmark::minerva::MinervaRobustness>,
    pub projection_grade: ProjectionGrade,
    pub evaluation_duration_sec: f64,
    pub evaluated_at_timestamp_ns: u64,
    /// Case/version/commit/binary provenance. Bound into the digest.
    #[serde(default)]
    pub provenance: BenchmarkProvenance,
    /// Physical artifacts the evaluation consumed or produced. Bound into the
    /// digest; checked against disk by [`BenchmarkReceipt::verify_artifacts`].
    #[serde(default)]
    pub artifacts: Vec<ArtifactBinding>,
    /// Which canonical encoding produced `receipt_digest`.
    #[serde(default = "legacy_digest_version")]
    pub digest_version: String,
    pub receipt_digest: String,
}

fn legacy_digest_version() -> String {
    RECEIPT_DIGEST_VERSION_LEGACY.to_string()
}

impl BenchmarkReceipt {
    pub fn generate(
        case: &BenchmarkCase,
        domain_results: HashMap<CapabilityDomain, DomainEvaluationResult>,
        composite_score: f64,
        duration_sec: f64,
        timestamp_ns: u64,
    ) -> Self {
        Self::generate_with_context(
            case,
            domain_results,
            composite_score,
            GateVector::default(),
            1.0,
            Vec::new(),
            None,
            None,
            ProjectionGrade::GradeU,
            duration_sec,
            timestamp_ns,
        )
    }

    #[allow(clippy::too_many_arguments)]
    pub fn generate_with_context(
        case: &BenchmarkCase,
        domain_results: HashMap<CapabilityDomain, DomainEvaluationResult>,
        composite_score: f64,
        gate_vector: GateVector,
        coverage_factor: f64,
        observations: Vec<MetricObservation>,
        nearest_defeater: Option<MinimalDefeaterSummary>,
        minerva_robustness: Option<crate::benchmark::minerva::MinervaRobustness>,
        projection_grade: ProjectionGrade,
        duration_sec: f64,
        timestamp_ns: u64,
    ) -> Self {
        let receipt_id = format!("bm_rcpt_{}_{}", case.case_id, timestamp_ns);

        Self {
            receipt_id,
            case_hash: case.case_hash.clone(),
            policy_id: case.target.policy_id.clone(),
            domain_results,
            composite_capability_score: composite_score,
            gate_vector,
            coverage_factor,
            observations,
            nearest_defeater,
            minerva_robustness,
            projection_grade,
            evaluation_duration_sec: duration_sec,
            evaluated_at_timestamp_ns: timestamp_ns,
            provenance: BenchmarkProvenance::from_case(case),
            artifacts: Vec::new(),
            digest_version: RECEIPT_DIGEST_VERSION.to_string(),
            // A digest is never stored without being computed from the very
            // contents that will be persisted alongside it.
            receipt_digest: String::new(),
        }
        .recompute_digest()
    }

    /// The canonical byte encoding that defines receipt identity.
    ///
    /// `receipt_digest` is excluded by construction (it is the output), and the
    /// version tag is prefixed as a domain separator. Public so an auditor can
    /// dump the exact bytes a digest commits to.
    pub fn canonical_encoding(&self) -> Result<Vec<u8>, ReceiptVerificationError> {
        let value = self.canonical_tree()?;
        if let Some(path) = first_unexpected_null(&value, String::new()) {
            return Err(ReceiptVerificationError::UnexpectedNull { path });
        }
        let mut canon = Canon::new();
        canon.push_str("BenchmarkReceipt");
        canon.push_str(&self.digest_version);
        canon.push_value(&value);
        Ok(canon.as_bytes().to_vec())
    }

    /// The receipt as the un-encoded tree it is hashed from. Poison checks are
    /// deliberately *not* applied here, so a caller can ask "is any number
    /// non-finite?" and "is any null unexpected?" separately and get an exact
    /// message for each.
    fn canonical_tree(&self) -> Result<serde_json::Value, ReceiptVerificationError> {
        let mut probe = self.clone();
        probe.receipt_digest = String::new();
        // Non-finite map *keys* are already rejected by serde itself
        // (`float_key_must_be_finite`); non-finite values are coerced to null by
        // `serialize_f64` (`Nan | Infinite => write_null`), which is what
        // `first_unexpected_null` exists to catch.
        serde_json::to_value(&probe).map_err(|_| ReceiptVerificationError::NonFiniteMetric)
    }

    /// Recompute the digest from current contents.
    ///
    /// Pure with respect to `receipt_digest`: it never reads the stored value,
    /// so a stored digest cannot self-fulfil (issue R2).
    pub fn compute_digest(&self) -> Result<String, ReceiptVerificationError> {
        // Ordered so a genuinely non-finite score reports as NonFiniteMetric and
        // not as the generic null-coercion finding.
        if self.has_non_finite_metric() {
            return Err(ReceiptVerificationError::NonFiniteMetric);
        }
        let mut canon = Canon::new();
        canon.push_bytes(&self.canonical_encoding()?);
        Ok(canon.finish_sha256_hex())
    }

    /// Seal the receipt: set `receipt_digest` to the recomputed value.
    ///
    /// Every mutation path must end here, so a stored digest can never lag its
    /// contents. A receipt holding a non-finite metric cannot be sealed at all —
    /// the digest is left empty, which makes the poisoned receipt unverifiable
    /// rather than falsely verifiable.
    pub fn recompute_digest(mut self) -> Self {
        self.receipt_digest = self.compute_digest().unwrap_or_default();
        self
    }

    /// Bind a physical artifact, re-sealing the digest (#328 R3).
    pub fn with_artifact(mut self, binding: ArtifactBinding) -> Self {
        self.artifacts.push(binding);
        self.receipt_digest = self.compute_digest().unwrap_or_default();
        self
    }

    /// Record the method/scoring implementation version. Refuses an empty or
    /// whitespace placeholder: absence must stay representable as `None`, never
    /// as a string that looks like a version.
    pub fn with_method_version(mut self, version: &str) -> Result<Self, String> {
        if version.trim().is_empty() {
            return Err("BLOCKED_EMPTY_METHOD_VERSION".to_string());
        }
        self.provenance.method_version = Some(version.to_string());
        self.receipt_digest = self.compute_digest().unwrap_or_default();
        Ok(self)
    }

    /// `true` when this digest was minted before #328 and cannot be recomputed
    /// by the current encoding.
    ///
    /// Such a row is *unbound*, not *verified*: it is preserved and reported
    /// separately, never silently trusted, and never rewritten in place.
    /// Re-sealing a legacy row would be a BFS-020 history overwrite and would
    /// destroy the only record of what the old code claimed.
    pub fn is_legacy_bound(&self) -> bool {
        self.digest_version != RECEIPT_DIGEST_VERSION
    }

    /// True when any bound metric is NaN or infinite.
    ///
    /// Enumerated over the typed fields so a genuinely non-finite score produces
    /// `NonFiniteMetric` rather than the generic null-coercion finding.
    ///
    /// Drift safety: a `f64` added to a nested type later would be missed by this
    /// list, but it cannot slip through the seal, because
    /// [`ReceiptVerificationError::UnexpectedNull`] rejects any coerced
    /// non-finite at an undeclared path. The two checks are complementary: this
    /// one is precise, that one is complete.
    pub fn has_non_finite_metric(&self) -> bool {
        let f = |v: f64| !v.is_finite();
        f(self.composite_capability_score)
            || f(self.coverage_factor)
            || f(self.evaluation_duration_sec)
            || self.domain_results.values().any(|r| {
                f(r.raw_score)
                    || f(r.calibrated_score)
                    || f(r.lower_bound)
                    || f(r.upper_bound)
            })
            || self.observations.iter().any(|o| {
                f(o.raw_value)
                    || f(o.normalized_score)
                    || f(o.lower_bound_95)
                    || f(o.upper_bound_95)
                    || f(o.effective_sample_size)
            })
            || self
                .nearest_defeater
                .as_ref()
                .map(|d| f(d.plausibility_distance) || f(d.peak_drawdown_pct))
                .unwrap_or(false)
            || self
                .minerva_robustness
                .as_ref()
                .map(|m| f(m.raw_score) || f(m.effective_score))
                .unwrap_or(false)
    }

    /// Digest-only self-check: correct generation, finite metrics, stored digest
    /// equals the recomputed digest. No provenance or artifact requirements, so
    /// a caller can separate "the bytes are what was sealed" from "the bytes are
    /// interpretable".
    pub fn verify_digest(&self) -> Result<(), ReceiptVerificationError> {
        if self.is_legacy_bound() {
            return Err(ReceiptVerificationError::UnversionedLegacy {
                digest_version: self.digest_version.clone(),
            });
        }
        if self.has_non_finite_metric() {
            return Err(ReceiptVerificationError::NonFiniteMetric);
        }
        let computed = self.compute_digest()?;
        let stored = &self.receipt_digest;
        if stored.is_empty() || !constant_time_eq(stored, &computed) {
            return Err(ReceiptVerificationError::DigestMismatch {
                stored: stored.clone(),
                computed,
            });
        }
        Ok(())
    }

    /// Full self-verification: generation, finiteness, recomputed digest, and
    /// complete provenance.
    ///
    /// Does **not** touch the filesystem — artifact verification is separate,
    /// because a chain check must be able to run against a ledger whose bound
    /// artifacts live on another mount.
    pub fn verify(&self) -> Result<(), ReceiptVerificationError> {
        self.verify_digest()?;
        let missing = self.provenance.missing_fields();
        if !missing.is_empty() {
            return Err(ReceiptVerificationError::MissingProvenance { fields: missing });
        }
        Ok(())
    }

    /// Verify that every referenced artifact physically exists and hash-matches
    /// (Rule 5). Required of any report that puts a receipt's numbers in front
    /// of a decision-maker.
    pub fn verify_artifacts(&self) -> Result<(), ReceiptVerificationError> {
        for binding in &self.artifacts {
            binding.verify_file()?;
        }
        Ok(())
    }

    /// Assert this receipt is about the expected policy (#328 R1).
    pub fn verify_policy_identity(
        &self,
        expected_policy_id: &str,
    ) -> Result<(), ReceiptVerificationError> {
        if self.policy_id != expected_policy_id {
            return Err(ReceiptVerificationError::IdentityMismatch {
                expected: expected_policy_id.to_string(),
                actual: self.policy_id.clone(),
            });
        }
        Ok(())
    }
}

/// Fields that are legitimately `null` in the canonical tree.
///
/// Anything *else* that arrives as `null` is either a non-finite `f64` that
/// serde silently coerced (see [`check_poison`]) or a defect. Keeping this as a
/// named list is what makes the coercion detectable without a schema; a new
/// `Option` field must be added here deliberately, and the accompanying test
/// fails loudly if it is not.
const NULLABLE_FIELDS: &[&str] = &[
    "nearest_defeater",
    "minerva_robustness",
    "method_version",
    "defeater_receipt_id",
    "evidence",
];

/// Return the path of the first `null` that serde can only have produced by
/// coercing a non-finite `f64`, or that a new optional field introduced without
/// being declared.
///
/// Without this, `NaN`, `inf` and a genuine recorded absence would all encode
/// identically — a collision in the identity layer, and the exact class of hole
/// #328 exists to close.
fn first_unexpected_null(value: &serde_json::Value, path: String) -> Option<String> {
    match value {
        serde_json::Value::Null => {
            let leaf = path.rsplit('.').next().unwrap_or("");
            if NULLABLE_FIELDS.contains(&leaf) {
                None
            } else {
                Some(path)
            }
        }
        serde_json::Value::Array(items) => items.iter().enumerate().find_map(|(i, it)| {
            first_unexpected_null(it, format!("{path}[{i}]"))
        }),
        serde_json::Value::Object(map) => {
            // Sorted so the reported path is deterministic regardless of the
            // map's iteration order.
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            keys.into_iter().find_map(|k| {
                let child_path = if path.is_empty() {
                    k.clone()
                } else {
                    format!("{path}.{k}")
                };
                first_unexpected_null(&map[k], child_path)
            })
        }
        _ => None,
    }
}

/// Lowercase hex SHA-256. Delegates to the same `sha2` instance the ledger uses
/// — no new digest primitive (#328 non-goal).
fn sha256_hex(bytes: &[u8]) -> String {
    let mut h = sha2::Sha256::new();
    h.update(bytes);
    format!("{:x}", h.finalize())
}

/// Length-checked then constant-time hex comparison, so a forged-prefix oracle
/// is no cheaper than a brute-force one.
fn constant_time_eq(a: &str, b: &str) -> bool {
    let (a, b) = (a.as_bytes(), b.as_bytes());
    if a.len() != b.len() {
        return false;
    }
    a.iter().zip(b).fold(0u8, |acc, (x, y)| acc | (x ^ y)) == 0
}
