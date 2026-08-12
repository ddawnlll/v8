//! Columnar artifact writer (LEDGER_FORMAT_SPEC §3-4).
//!
//! The compute-plane boundary is an artifact file, not an FFI call
//! (COMPUTE_CORE_SPEC §7). Artifacts are column-major, one buffer per field,
//! in a self-describing container:
//!
//! ```text
//! magic "V82LDRG1"  (8 bytes)
//! header_len u32 LE
//! header JSON      (artifact_kind, hash_encoding, schema, run_constants,
//!                   tier, row_count, column_count, ordering)
//! per column: name, dtype u8, n_rows u32 LE, validity bitmask,
//!             values (fixed width / dict index), string dictionary
//! ```
//!
//! - Numeric columns are fixed-width IEEE-754 / two's complement, never
//!   decimal text (removes the float-rendering hazard from the storage path).
//! - Absent values carry an explicit validity bit; absence is never a
//!   sentinel number (MARKET_STATE_CONTRACT §4).
//! - Low-cardinality strings are dictionary-encoded to u16 ids with the
//!   dictionary in the header area of each column.
//! - Ordering is declared and stable, so two runs of the same request produce
//!   byte-identical artifacts (PARITY_AND_IDENTITY_SPEC G4). No wall clock
//!   ever enters an artifact.
//!
//! The artifact fingerprint is SHA-1 over the raw file bytes, computed by
//! `fingerprint()`; the header's `hash_encoding` binds the value encoding of
//! the columns to `v8.2-ieee-le`.
//!
//! Since S5 (issue #108) every artifact also carries an evidence tier
//! (IDENTITY_ONLY | VALUES | FULL, §5) and a run-constants set (§3), hoisted
//! into the header by the `state` / `candidate` / `outcome` / `evaluation` /
//! `cube` constructors. The tier-honesty rule (§4) is enforced by
//! `Artifact::add_field`, which rejects a field whose `FieldTier` is above
//! the artifact's tier. The raw `add_column` primitive stays available for
//! pre-validating callers (the S0 dataset path).
//!
//! The S5 ledger API is ahead of its wiring — exercised by its unit tests and
//! consumed by the ledger-check and later stages — so its dead-code is
//! expected and named here rather than hidden (same treatment as `hash.rs`).
#![allow(dead_code)]

use std::io;
use std::path::Path;

use sha1::{Digest, Sha1};

use crate::hash::HASH_ENCODING;

pub const MAGIC: &[u8; 8] = b"V82LDRG1";

/// Generator tag recorded in every S5 artifact's run-constants so a reader can
/// bind the artifact to the exact producer that emitted it — no wall clock
/// ever enters an artifact (PARITY_AND_IDENTITY_SPEC G5).
pub const GENERATOR: &str = "v8-core";
pub const GENERATOR_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Canonical `<generator>/<version>` tag, e.g. `v8-core/0.2.0`.
pub fn generator_tag() -> String {
    format!("{GENERATOR}/{GENERATOR_VERSION}")
}

/// Column data types. `F64`/`Bool` are value columns consumed from S1
/// (state/outcome artifacts); `from_tag` serves the S5 read-back path.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DType {
    I64 = 0,
    #[allow(dead_code)] // S1 value columns
    F64 = 1,
    #[allow(dead_code)] // S1 value columns
    Bool = 2,
    DictStr = 3,
}

impl DType {
    pub fn tag(self) -> u8 {
        match self {
            DType::I64 => 0,
            DType::F64 => 1,
            DType::Bool => 2,
            DType::DictStr => 3,
        }
    }
    #[allow(dead_code)] // S5 read-back
    pub fn from_tag(t: u8) -> Option<DType> {
        match t {
            0 => Some(DType::I64),
            1 => Some(DType::F64),
            2 => Some(DType::Bool),
            3 => Some(DType::DictStr),
            _ => None,
        }
    }
}

/// Evidence-depth tiers (LEDGER_FORMAT_SPEC §5). Every artifact carries one;
/// the tier is recorded in the header and is therefore part of the artifact
/// identity, so a `VALUES` artifact can never be mistaken for a `FULL` one.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArtifactTier {
    /// header + per-record identity and quality (sweeps, cache-warming)
    IdentityOnly = 0,
    /// identity + information columns — the research default
    Values = 1,
    /// `VALUES` + materialized derivables (lineage hashes, per-feature
    /// clocks, expanded history)
    Full = 2,
}

impl ArtifactTier {
    /// Header spelling of the tier (§3, §5).
    pub const fn as_str(self) -> &'static str {
        match self {
            ArtifactTier::IdentityOnly => "IDENTITY_ONLY",
            ArtifactTier::Values => "VALUES",
            ArtifactTier::Full => "FULL",
        }
    }

    pub fn from_str(s: &str) -> Option<ArtifactTier> {
        match s {
            "IDENTITY_ONLY" => Some(ArtifactTier::IdentityOnly),
            "VALUES" => Some(ArtifactTier::Values),
            "FULL" => Some(ArtifactTier::Full),
            _ => None,
        }
    }

    /// Numeric depth: `IDENTITY_ONLY < VALUES < FULL`.
    pub const fn rank(self) -> u8 {
        self as u8
    }

    /// Reader-side tier check (§8 test #4): can this tier satisfy a reader
    /// that requires `field_tier`? The failure is explicit — `false`, never
    /// an empty column handed to the caller.
    pub const fn can_serve(self, field_tier: FieldTier) -> bool {
        self.rank() >= field_tier.rank()
    }
}

/// Minimum tier at which a field may be carried (LEDGER_FORMAT_SPEC §5).
///
/// - `IdentityOnly`: identity + quality fields — present at every tier.
/// - `Values`: information columns — present at `VALUES` and `FULL`.
/// - `Full`: materialized derivables (lineage hashes, per-feature clocks,
///   expanded history) — present only at `FULL`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldTier {
    IdentityOnly = 0,
    Values = 1,
    Full = 2,
}

impl FieldTier {
    pub const fn as_str(self) -> &'static str {
        match self {
            FieldTier::IdentityOnly => "IDENTITY_ONLY",
            FieldTier::Values => "VALUES",
            FieldTier::Full => "FULL",
        }
    }

    pub const fn rank(self) -> u8 {
        self as u8
    }
}

/// A tier-honesty violation (§4): a field was added to an artifact whose tier
/// is below the field's `FieldTier`. The write is rejected rather than
/// silently producing a lower-tier artifact that carries a higher-tier field.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TierViolation {
    pub field: String,
    pub field_tier: FieldTier,
    pub artifact_tier: ArtifactTier,
}

impl std::fmt::Display for TierViolation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "field {:?} requires tier {} but artifact tier is {}",
            self.field,
            self.field_tier.as_str(),
            self.artifact_tier.as_str()
        )
    }
}

impl std::error::Error for TierViolation {}

/// A single column buffer being accumulated in memory before writing.
pub struct Column {
    pub name: String,
    pub dtype: DType,
    /// Per-row validity; default all-valid, flipped for absent rows.
    valid: Vec<bool>,
    i64s: Vec<i64>,
    f64s: Vec<f64>,
    bools: Vec<u8>,
    /// Dictionary for DictStr columns; id 0.. is reserved by insertion order.
    dict: Vec<String>,
    /// DictStr per-row ids; a row with an absent value has an id but invalid bit.
    str_ids: Vec<u16>,
}

impl Column {
    pub fn new(name: &str, dtype: DType) -> Self {
        Column {
            name: name.to_string(),
            dtype,
            valid: Vec::new(),
            i64s: Vec::new(),
            f64s: Vec::new(),
            bools: Vec::new(),
            dict: Vec::new(),
            str_ids: Vec::new(),
        }
    }

    pub fn n_rows(&self) -> usize {
        match self.dtype {
            DType::I64 => self.i64s.len(),
            DType::F64 => self.f64s.len(),
            DType::Bool => self.bools.len(),
            DType::DictStr => self.str_ids.len(),
        }
    }

    pub fn push_i64(&mut self, v: i64) {
        debug_assert_eq!(self.dtype, DType::I64);
        self.i64s.push(v);
        self.valid.push(true);
    }

    #[allow(dead_code)] // S1 value columns
    pub fn push_f64(&mut self, v: f64) {
        debug_assert_eq!(self.dtype, DType::F64);
        self.f64s.push(v);
        self.valid.push(true);
    }

    #[allow(dead_code)] // S1 value columns
    pub fn push_bool(&mut self, v: bool) {
        debug_assert_eq!(self.dtype, DType::Bool);
        self.bools.push(v as u8);
        self.valid.push(true);
    }

    pub fn push_str(&mut self, s: &str) {
        debug_assert_eq!(self.dtype, DType::DictStr);
        let id = match self.dict.iter().position(|d| d == s) {
            Some(i) => i as u16,
            None => {
                let i = self.dict.len();
                self.dict.push(s.to_string());
                i as u16
            }
        };
        self.str_ids.push(id);
        self.valid.push(true);
    }

    /// Mark the next (about-to-be-pushed) row absent. Call before pushing the
    /// row's value; the value slot is still pushed (as a fill) so the column
    /// stays rectangular, but the validity bit reads absent.
    #[allow(dead_code)] // S1 value columns
    pub fn push_absent(&mut self) {
        // Placeholder: the value fill happens via the dtype-specific push, so
        // here we only record that the *last* pushed row is invalid.
        self.valid.pop();
        self.valid.push(false);
    }
}

/// Run-constant set bound into every S5 artifact header (LEDGER_FORMAT_SPEC
/// §3). Every field is constant for all records of a run, so it is hoisted
/// into the header once instead of repeated per row.
#[derive(Debug, Clone, PartialEq)]
pub struct RunConstants {
    pub data_hash: String,
    pub code_hash: String,
    pub config_hash: String,
    pub simulator_hash: String,
    pub risk_gate_hash: String,
    pub evaluator_version: String,
    pub platform: String,
    pub utility_unit: String,
    pub cost_form: String,
    pub slippage: f64,
    pub action_manifest_id: String,
}

impl RunConstants {
    /// The §3 key set, in §3 order — the header-completeness contract.
    pub const REQUIRED_KEYS: [&'static str; 11] = [
        "data_hash",
        "code_hash",
        "config_hash",
        "simulator_hash",
        "risk_gate_hash",
        "evaluator_version",
        "platform",
        "utility_unit",
        "cost_form",
        "slippage",
        "action_manifest_id",
    ];

    /// The run-constants object for the header.
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "data_hash": self.data_hash,
            "code_hash": self.code_hash,
            "config_hash": self.config_hash,
            "simulator_hash": self.simulator_hash,
            "risk_gate_hash": self.risk_gate_hash,
            "evaluator_version": self.evaluator_version,
            "platform": self.platform,
            "utility_unit": self.utility_unit,
            "cost_form": self.cost_form,
            "slippage": self.slippage,
            "action_manifest_id": self.action_manifest_id,
        })
    }

    /// The header `run_constants` object with the per-artifact bindings
    /// hoisted in: `symbol`, `interval`, and the generator tag (also
    /// run-constants — constant for all records within a run, §2).
    pub fn with_binding(&self, symbol: &str, interval: &str, generator: &str) -> serde_json::Value {
        let mut obj = self
            .to_json()
            .as_object()
            .expect("run-constants serialize as an object")
            .clone();
        obj.insert("symbol".to_string(), serde_json::json!(symbol));
        obj.insert("interval".to_string(), serde_json::json!(interval));
        obj.insert("generator".to_string(), serde_json::json!(generator));
        serde_json::Value::Object(obj)
    }
}

/// Accumulates rows and writes one `.v82` artifact file.
pub struct Artifact {
    pub kind: String,
    pub tier: String,
    pub run_constants: serde_json::Value,
    pub ordering: String,
    pub columns: Vec<Column>,
    n_rows: usize,
}

impl Artifact {
    pub fn new(kind: &str, tier: &str, run_constants: serde_json::Value, ordering: &str) -> Self {
        Artifact {
            kind: kind.to_string(),
            tier: tier.to_string(),
            run_constants,
            ordering: ordering.to_string(),
            columns: Vec::new(),
            n_rows: 0,
        }
    }

    pub fn add_column(&mut self, name: &str, dtype: DType) -> usize {
        self.columns.push(Column::new(name, dtype));
        self.columns.len() - 1
    }

    /// The artifact's declared tier, if its header tier string is one of the
    /// three known tiers. A pre-S5 caller passing an arbitrary tier string
    /// yields `None`; `add_field` treats that as permissive, so legacy
    /// `Artifact::new("dataset", ...)` paths are unaffected.
    pub fn tier_enum(&self) -> Option<ArtifactTier> {
        ArtifactTier::from_str(&self.tier)
    }

    /// Add a column with a declared minimum field tier, enforcing the
    /// tier-honesty rule (§4): a field may not be stored in an artifact whose
    /// tier is below its `FieldTier` — a `VALUES` artifact cannot carry a
    /// `FULL`-only materialized derivative, an `IDENTITY_ONLY` artifact cannot
    /// carry an information column. The violation is an explicit `Err`, never
    /// an empty column. Callers that pre-validate keep using `add_column`.
    pub fn add_field(
        &mut self,
        name: &str,
        dtype: DType,
        field_tier: FieldTier,
    ) -> Result<usize, TierViolation> {
        match self.tier_enum() {
            Some(at) if !at.can_serve(field_tier) => Err(TierViolation {
                field: name.to_string(),
                field_tier,
                artifact_tier: at,
            }),
            _ => Ok(self.add_column(name, dtype)),
        }
    }

    /// Complete a row: every column must have exactly one slot pushed since
    /// the previous `end_row`.
    pub fn end_row(&mut self) {
        for c in &self.columns {
            debug_assert_eq!(c.n_rows(), self.n_rows + 1, "column {} row count", c.name);
        }
        self.n_rows += 1;
    }

    pub fn write(&self, path: &Path) -> io::Result<()> {
        let mut out = Vec::new();
        out.extend_from_slice(MAGIC);

        let schema: Vec<serde_json::Value> = self
            .columns
            .iter()
            .map(|c| {
                serde_json::json!({"name": c.name, "dtype": c.dtype.tag(),
                                   "dictionary": c.dict})
            })
            .collect();
        let header = serde_json::json!({
            "artifact_kind": self.kind,
            "hash_encoding": HASH_ENCODING,
            "schema": schema,
            "run_constants": self.run_constants,
            "tier": self.tier,
            "row_count": self.n_rows,
            "column_count": self.columns.len(),
            "ordering": self.ordering,
        });
        let header_bytes = serde_json::to_vec(&header)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        out.extend_from_slice(&(header_bytes.len() as u32).to_le_bytes());
        out.extend_from_slice(&header_bytes);

        for c in &self.columns {
            let name = c.name.as_bytes();
            out.extend_from_slice(&(name.len() as u16).to_le_bytes());
            out.extend_from_slice(name);
            out.push(c.dtype.tag());
            let n = c.n_rows();
            out.extend_from_slice(&(n as u32).to_le_bytes());
            // validity bitmask, LSB-first.
            let mut mask = vec![0u8; (n + 7) / 8];
            for (i, v) in c.valid.iter().enumerate() {
                if *v {
                    mask[i / 8] |= 1 << (i % 8);
                }
            }
            out.extend_from_slice(&mask);
            match c.dtype {
                DType::I64 => {
                    for v in &c.i64s {
                        out.extend_from_slice(&v.to_le_bytes());
                    }
                }
                DType::F64 => {
                    for v in &c.f64s {
                        out.extend_from_slice(&v.to_bits().to_le_bytes());
                    }
                }
                DType::Bool => {
                    for v in &c.bools {
                        out.push(*v);
                    }
                }
                DType::DictStr => {
                    for id in &c.str_ids {
                        out.extend_from_slice(&id.to_le_bytes());
                    }
                    out.extend_from_slice(&(c.dict.len() as u32).to_le_bytes());
                    for s in &c.dict {
                        out.extend_from_slice(&(s.len() as u32).to_le_bytes());
                        out.extend_from_slice(s.as_bytes());
                    }
                }
            }
        }
        std::fs::write(path, &out)
    }
}

/// SHA-1 (hex) over the raw artifact bytes — the artifact identity used for
/// byte-stability (G4) and cache keys. Content-addressed, no wall clock.
pub fn fingerprint(path: &Path) -> io::Result<String> {
    let bytes = std::fs::read(path)?;
    let mut h = Sha1::new();
    Digest::update(&mut h, &bytes);
    Ok(h.finalize().iter().map(|b| format!("{:02x}", b)).collect())
}

/// Read an artifact's JSON header back from disk (S5 read-back path). Returns
/// the header object; a reader uses it to verify `hash_encoding`, `tier`, and
/// the run-constants against the pinned producer before touching columns.
pub fn read_header(path: &Path) -> io::Result<serde_json::Value> {
    let bytes = std::fs::read(path)?;
    if bytes.len() < 12 || &bytes[..8] != MAGIC {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "not a V82LDRG1 artifact",
        ));
    }
    let header_len = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
    if 12 + header_len > bytes.len() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "truncated artifact header",
        ));
    }
    serde_json::from_slice(&bytes[12..12 + header_len])
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
}

// ---------------------------------------------------------------------------
// S5 artifact-kind constructors (LEDGER_FORMAT_SPEC §3, §5)
//
// Each kind hoists the run-constants — including `symbol`, `interval`, and the
// generator tag, all constant for every record within a run (§2) — into the
// header. The `ordering` key is declared and stable so two runs of the same
// request write byte-identical artifacts (PARITY_AND_IDENTITY_SPEC G4).
// ---------------------------------------------------------------------------

/// `state` artifact: per-bar feature/state evidence (S1). Ordering is bar
/// index, then as-of clock.
pub fn state_artifact(
    tier: ArtifactTier,
    symbol: &str,
    interval: &str,
    generator: &str,
    rc: &RunConstants,
) -> Artifact {
    Artifact::new("state", tier.as_str(), rc.with_binding(symbol, interval, generator), "bar_index,as_of")
}

/// `candidate` artifact: admitted-exposure candidates (S4). Ordering is
/// episode key, then the state that triggered the candidate.
pub fn candidate_artifact(
    tier: ArtifactTier,
    symbol: &str,
    interval: &str,
    generator: &str,
    rc: &RunConstants,
) -> Artifact {
    Artifact::new(
        "candidate",
        tier.as_str(),
        rc.with_binding(symbol, interval, generator),
        "episode_key,state_id",
    )
}

/// `outcome` artifact: replayed bar outcomes (S2/S3). Ordering is bar index,
/// then as-of clock.
pub fn outcome_artifact(
    tier: ArtifactTier,
    symbol: &str,
    interval: &str,
    generator: &str,
    rc: &RunConstants,
) -> Artifact {
    Artifact::new("outcome", tier.as_str(), rc.with_binding(symbol, interval, generator), "bar_index,as_of")
}

/// `evaluation` artifact: evaluator verdicts over episodes (S4). Ordering is
/// episode key, then the state being evaluated.
pub fn evaluation_artifact(
    tier: ArtifactTier,
    symbol: &str,
    interval: &str,
    generator: &str,
    rc: &RunConstants,
) -> Artifact {
    Artifact::new(
        "evaluation",
        tier.as_str(),
        rc.with_binding(symbol, interval, generator),
        "episode_key,state_id",
    )
}

/// `cube` artifact: outcome-cube cells (S3), columnar. Ordering is bar index,
/// then the cell index within the bar's action grid.
pub fn cube_artifact(
    tier: ArtifactTier,
    symbol: &str,
    interval: &str,
    generator: &str,
    rc: &RunConstants,
) -> Artifact {
    Artifact::new(
        "cube",
        tier.as_str(),
        rc.with_binding(symbol, interval, generator),
        "bar_index,cell_index",
    )
}

/// S5 ledger §8 cheap-test driver (issue #109): round-trip, header
/// completeness, byte-stability, tier honesty, no-decimal-floats scan,
/// retention — extended to verdict artifacts at S7 (issue #123).
pub fn ledger_check(args: &[String]) -> i32 {
    eprintln!("S5 ledger-check not implemented yet (issue #109): args={args:?}");
    1
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn artifact_round_trip_bytes_are_deterministic() {
        let dir = std::env::temp_dir();
        let p1 = dir.join("v82-art-1.v82");
        let p2 = dir.join("v82-art-2.v82");
        for p in [&p1, &p2] {
            let mut a = Artifact::new("dataset", "VALUES", serde_json::json!({"k": 1}), "row");
            let ev = a.add_column("event_time", DType::I64);
            let px = a.add_column("close", DType::F64);
            let sy = a.add_column("symbol", DType::DictStr);
            for _ in 0..3 {
                a.columns[ev].push_i64(100 + 0);
                a.columns[px].push_f64(1.5);
                a.columns[sy].push_str("SOLUSDT");
                a.end_row();
            }
            a.write(p).unwrap();
        }
        let b1 = std::fs::read(&p1).unwrap();
        let b2 = std::fs::read(&p2).unwrap();
        assert_eq!(b1, b2, "two identical requests must write byte-identical artifacts");
        std::fs::remove_file(&p1).ok();
        std::fs::remove_file(&p2).ok();
    }

    #[test]
    fn validity_bit_marks_absent_rows() {
        let dir = std::env::temp_dir();
        let p = dir.join("v82-art-validity.v82");
        let mut a = Artifact::new("dataset", "VALUES", serde_json::json!({}), "row");
        let ev = a.add_column("event_time", DType::I64);
        a.columns[ev].push_i64(1);
        a.end_row();
        a.columns[ev].push_i64(0);
        a.columns[ev].push_absent();
        a.end_row();
        a.write(&p).unwrap();
        let bytes = std::fs::read(&p).unwrap();
        // First byte after the header is the first column's mask: only row 0
        // valid -> 0b0000_0001.
        let mut off = 8 + 4; // magic + header_len
        let header_len = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
        off += header_len;
        // column: name_len(2) + name + dtype(1) + n_rows(4) + mask(1)
        let name_len = u16::from_le_bytes(bytes[off..off + 2].try_into().unwrap()) as usize;
        off += 2;
        off += name_len;
        off += 1; // dtype
        let mask_pos = off + 4; // after n_rows u32
        assert_eq!(bytes[mask_pos], 0b0000_0001);
        std::fs::remove_file(&p).ok();
    }

    #[test]
    fn fingerprint_is_content_addressed() {
        let dir = std::env::temp_dir();
        let p = dir.join("v82-art-fp.v82");
        let mut a = Artifact::new("dataset", "VALUES", serde_json::json!({"x": 1}), "row");
        let c = a.add_column("v", DType::I64);
        a.columns[c].push_i64(42);
        a.end_row();
        a.write(&p).unwrap();
        let f1 = fingerprint(&p).unwrap();
        let f2 = fingerprint(&p).unwrap();
        assert_eq!(f1, f2);
        std::fs::remove_file(&p).ok();
    }

    // ---------------------------------------------------------------------
    // S5 ledger tests (issue #108): tiers, run-constants, round-trip,
    // byte-stability (LEDGER_FORMAT_SPEC §3-5, §8).
    // ---------------------------------------------------------------------

    fn test_rc() -> RunConstants {
        RunConstants {
            data_hash: "d1a6".repeat(10),
            code_hash: "c0de".repeat(10),
            config_hash: "c0n".repeat(14),
            simulator_hash: "51m".repeat(14),
            risk_gate_hash: "r15k".repeat(10),
            evaluator_version: "evaluate/0.9.1".to_string(),
            platform: "cpu".to_string(),
            utility_unit: "quote".to_string(),
            cost_form: "taker-bps".to_string(),
            slippage: 0.5,
            action_manifest_id: "manifest-0001".to_string(),
        }
    }

    #[test]
    fn values_artifact_rejects_full_only_field() {
        // Tier honesty (§4 / §8 test #4): a VALUES artifact must not carry a
        // FULL-only materialized derivative; the failure is explicit, not an
        // empty column.
        let mut a =
            state_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &test_rc());
        let sid = a
            .add_field("state_id", DType::DictStr, FieldTier::IdentityOnly)
            .expect("identity field is legal at VALUES");
        let close = a
            .add_field("close", DType::F64, FieldTier::Values)
            .expect("information field is legal at VALUES");
        let err = a
            .add_field("lineage_hash", DType::DictStr, FieldTier::Full)
            .unwrap_err();
        assert_eq!(err.field, "lineage_hash");
        assert_eq!(err.field_tier, FieldTier::Full);
        assert_eq!(err.artifact_tier, ArtifactTier::Values);
        // Columns added before the violation are untouched; the violating
        // field is never silently downgraded or stubbed.
        assert_eq!(a.columns.len(), 2);
        assert_eq!(a.columns[sid].name, "state_id");
        assert_eq!(a.columns[close].name, "close");

        // The same field is legal at FULL (the top tier satisfies every
        // FieldTier).
        let mut f =
            state_artifact(ArtifactTier::Full, "SOLUSDT", "15m", &generator_tag(), &test_rc());
        assert!(f.add_field("lineage_hash", DType::DictStr, FieldTier::Full).is_ok());
    }

    #[test]
    fn identity_only_artifact_rejects_information_field() {
        let mut a = state_artifact(
            ArtifactTier::IdentityOnly,
            "SOLUSDT",
            "15m",
            &generator_tag(),
            &test_rc(),
        );
        assert!(a
            .add_field("state_id", DType::DictStr, FieldTier::IdentityOnly)
            .is_ok());
        let err = a.add_field("close", DType::F64, FieldTier::Values).unwrap_err();
        assert_eq!(err.artifact_tier, ArtifactTier::IdentityOnly);
        assert_eq!(err.field_tier, FieldTier::Values);
    }

    #[test]
    fn headers_carry_required_run_constants_for_all_kinds() {
        // Header completeness (§8 test #2): every S5 kind binds the full §3
        // run-constant set plus symbol/interval/generator, hash_encoding, and
        // tier.
        let rc = test_rc();
        let artifacts = [
            (
                "state",
                state_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &rc),
            ),
            (
                "candidate",
                candidate_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &rc),
            ),
            (
                "outcome",
                outcome_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &rc),
            ),
            (
                "evaluation",
                evaluation_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &rc),
            ),
            (
                "cube",
                cube_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &rc),
            ),
        ];
        let dir = std::env::temp_dir();
        for (kind, art) in artifacts {
            let p = dir.join(format!("v82-hdr-{kind}.v82"));
            art.write(&p).unwrap();
            let h = read_header(&p).unwrap();
            assert_eq!(h["artifact_kind"], kind, "{kind}: artifact_kind");
            assert_eq!(h["hash_encoding"], HASH_ENCODING, "{kind}: hash_encoding");
            assert_eq!(h["tier"], "VALUES", "{kind}: tier");
            for k in RunConstants::REQUIRED_KEYS {
                assert!(h["run_constants"].get(k).is_some(), "{kind}: missing {k}");
            }
            for k in ["symbol", "interval", "generator"] {
                assert!(h["run_constants"].get(k).is_some(), "{kind}: missing {k}");
            }
            assert_eq!(h["run_constants"]["symbol"], "SOLUSDT", "{kind}: symbol");
            assert_eq!(h["run_constants"]["interval"], "15m", "{kind}: interval");
            assert!(
                h["run_constants"]["generator"]
                    .as_str()
                    .unwrap()
                    .starts_with("v8-core/"),
                "{kind}: generator tag"
            );
            std::fs::remove_file(&p).ok();
        }
    }

    #[test]
    fn state_artifact_round_trips_through_disk() {
        let mut a =
            state_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), &test_rc());
        let sid = a.add_field("state_id", DType::DictStr, FieldTier::IdentityOnly).unwrap();
        let as_of = a.add_field("as_of", DType::I64, FieldTier::IdentityOnly).unwrap();
        let close = a.add_field("close", DType::F64, FieldTier::Values).unwrap();
        for _ in 0..2 {
            a.columns[sid].push_str("state-001");
            a.columns[as_of].push_i64(1_700_000_000_000);
            a.columns[close].push_f64(101.5);
            a.end_row();
        }
        let dir = std::env::temp_dir();
        let p = dir.join("v82-state-rt.v82");
        a.write(&p).unwrap();

        // Header read-back (write + read) matches what was written.
        let h = read_header(&p).unwrap();
        assert_eq!(h["artifact_kind"], "state");
        assert_eq!(h["tier"], "VALUES");
        assert_eq!(h["hash_encoding"], HASH_ENCODING);
        assert_eq!(h["row_count"], 2);
        assert_eq!(h["column_count"], 3);
        assert_eq!(h["run_constants"]["symbol"], "SOLUSDT");
        assert_eq!(h["run_constants"]["interval"], "15m");

        // Fingerprint is content-addressed and stable across re-reads.
        assert_eq!(fingerprint(&p).unwrap(), fingerprint(&p).unwrap());
        std::fs::remove_file(&p).ok();
    }

    #[test]
    fn s5_artifacts_are_byte_stable() {
        let rc = test_rc();
        let build = || {
            let mut a = outcome_artifact(ArtifactTier::Values, "BTCUSDT", "1h", &generator_tag(), &rc);
            let status = a.add_field("cell_status", DType::DictStr, FieldTier::Values).unwrap();
            let gap = a.add_field("gap", DType::F64, FieldTier::Values).unwrap();
            a.columns[status].push_str("EXPLORABLE");
            a.columns[gap].push_f64(0.25);
            a.end_row();
            a
        };
        let dir = std::env::temp_dir();
        let p1 = dir.join("v82-oc-1.v82");
        let p2 = dir.join("v82-oc-2.v82");
        build().write(&p1).unwrap();
        build().write(&p2).unwrap();
        assert_eq!(
            std::fs::read(&p1).unwrap(),
            std::fs::read(&p2).unwrap(),
            "two identical requests must write byte-identical artifacts (G4)"
        );
        std::fs::remove_file(&p1).ok();
        std::fs::remove_file(&p2).ok();
    }
}
