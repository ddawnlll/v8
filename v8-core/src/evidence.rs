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

use std::collections::HashMap;
use std::io;
use std::io::Write;
use std::path::{Path, PathBuf};

use serde_json::Value;
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

/// SHA-1 (hex) over raw bytes — the V8.2 digest used by fingerprint, the
/// ledger-fixture identities, and the default fixture tape hash.
pub fn sha1_hex(bytes: &[u8]) -> String {
    let mut h = Sha1::new();
    Digest::update(&mut h, bytes);
    h.finalize().iter().map(|b| format!("{:02x}", b)).collect()
}

/// SHA-1 (hex) over the raw artifact bytes — the artifact identity used for
/// byte-stability (G4) and cache keys. Content-addressed, no wall clock.
pub fn fingerprint(path: &Path) -> io::Result<String> {
    let bytes = std::fs::read(path)?;
    Ok(sha1_hex(&bytes))
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

/// A full artifact read-back (S5 ledger §8 test #1): the header plus every
/// column's values in file order. Absent cells read as `None` from the
/// validity bit — absence is never a sentinel number (MARKET_STATE_CONTRACT
/// §4).
pub struct ReadBack {
    pub header: Value,
    /// `(column name, per-row value)` in file order.
    pub columns: Vec<(String, Vec<Option<Value>>)>,
}

impl ReadBack {
    /// The per-row values of the named column, or `None` if absent.
    pub fn column(&self, name: &str) -> Option<&Vec<Option<Value>>> {
        self.columns.iter().find(|(n, _)| n == name).map(|(_, v)| v)
    }

    /// Row count = the first column's length (columns are rectangular).
    pub fn row_count(&self) -> usize {
        self.columns.first().map(|(_, v)| v.len()).unwrap_or(0)
    }
}

/// Bounds-checked slice take for the artifact walk; a truncated file is an
/// explicit `Err`, never a panic.
fn take<'a>(bytes: &'a [u8], off: &mut usize, n: usize) -> io::Result<&'a [u8]> {
    if *off + n > bytes.len() {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "truncated artifact data"));
    }
    let s = &bytes[*off..*off + n];
    *off += n;
    Ok(s)
}

/// Read an artifact back in full: header plus every row of every column,
/// decoding values per the declared dtype and applying the validity bitmask.
/// This is the reader side of §8 test #1 — the round-trip regenerates each
/// dropped field from the identity and compares it against what the write
/// path stored.
pub fn read_artifact(path: &Path) -> io::Result<ReadBack> {
    let bytes = std::fs::read(path)?;
    if bytes.len() < 12 || &bytes[..8] != MAGIC {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "not a V82LDRG1 artifact"));
    }
    let header_len = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
    if 12 + header_len > bytes.len() {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "truncated artifact header"));
    }
    let header: Value = serde_json::from_slice(&bytes[12..12 + header_len])
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    let column_count = header["column_count"].as_u64().unwrap_or(0) as usize;
    let mut off = 12 + header_len;
    let mut columns = Vec::with_capacity(column_count);
    for _ in 0..column_count {
        let name_len = u16::from_le_bytes(take(&bytes, &mut off, 2)?.try_into().unwrap()) as usize;
        let name = String::from_utf8_lossy(take(&bytes, &mut off, name_len)?).to_string();
        let dtype = take(&bytes, &mut off, 1)?[0];
        let n = u32::from_le_bytes(take(&bytes, &mut off, 4)?.try_into().unwrap()) as usize;
        let mask = take(&bytes, &mut off, (n + 7) / 8)?;
        let valid: Vec<bool> = (0..n).map(|i| mask[i / 8] & (1 << (i % 8)) != 0).collect();
        let mut values = Vec::with_capacity(n);
        match DType::from_tag(dtype) {
            Some(DType::I64) => {
                let raw = take(&bytes, &mut off, 8 * n)?;
                for i in 0..n {
                    let v = i64::from_le_bytes(raw[8 * i..8 * i + 8].try_into().unwrap());
                    values.push(if valid[i] { Some(serde_json::json!(v)) } else { None });
                }
            }
            Some(DType::F64) => {
                let raw = take(&bytes, &mut off, 8 * n)?;
                for i in 0..n {
                    let v = f64::from_bits(u64::from_le_bytes(raw[8 * i..8 * i + 8].try_into().unwrap()));
                    values.push(if valid[i] { Some(serde_json::json!(v)) } else { None });
                }
            }
            Some(DType::Bool) => {
                let raw = take(&bytes, &mut off, n)?;
                for i in 0..n {
                    let v = raw[i] != 0;
                    values.push(if valid[i] { Some(serde_json::json!(v)) } else { None });
                }
            }
            Some(DType::DictStr) => {
                let ids = take(&bytes, &mut off, 2 * n)?;
                let dict_len = u32::from_le_bytes(take(&bytes, &mut off, 4)?.try_into().unwrap()) as usize;
                let mut dict = Vec::with_capacity(dict_len);
                for _ in 0..dict_len {
                    let s_len = u32::from_le_bytes(take(&bytes, &mut off, 4)?.try_into().unwrap()) as usize;
                    let s = String::from_utf8_lossy(take(&bytes, &mut off, s_len)?).to_string();
                    dict.push(s);
                }
                for i in 0..n {
                    let id = u16::from_le_bytes(ids[2 * i..2 * i + 2].try_into().unwrap()) as usize;
                    values.push(if valid[i] { Some(serde_json::json!(dict[id])) } else { None });
                }
            }
            None => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("column {name}: unknown dtype {dtype}"),
                ));
            }
        }
        columns.push((name, values));
    }
    Ok(ReadBack { header, columns })
}

/// Header-completeness check (LEDGER_FORMAT_SPEC §8 test #2). A header must
/// carry `hash_encoding`, `tier`, and every §3 run-constant plus the
/// per-artifact bindings (`symbol`, `interval`, `generator`). A missing field
/// fails closed — an `Err` naming the gap — never a header that would silently
/// produce rows with a missing field.
pub fn validate_header(header: &Value) -> Result<(), String> {
    let mut missing: Vec<String> = Vec::new();
    for k in ["artifact_kind", "hash_encoding", "tier", "row_count", "column_count", "ordering"] {
        if header.get(k).is_none() {
            missing.push(k.to_string());
        }
    }
    let rc = match header.get("run_constants") {
        Some(v) if v.is_object() => v,
        _ => return Err("header: run_constants missing or not an object".to_string()),
    };
    for k in RunConstants::REQUIRED_KEYS {
        if rc.get(k).is_none() {
            missing.push(format!("run_constants.{k}"));
        }
    }
    for k in ["symbol", "interval", "generator"] {
        if rc.get(k).is_none() {
            missing.push(format!("run_constants.{k}"));
        }
    }
    if missing.is_empty() {
        Ok(())
    } else {
        Err(format!("header missing: {}", missing.join(", ")))
    }
}

/// §8 test #5: does a byte region contain a text-encoded decimal float — an
/// ASCII `.` adjacent to an ASCII digit? Fixed-width IEEE-754 / two's
/// complement values never contain that pattern, so a hit means decimal text
/// reached a numeric column.
pub fn has_decimal_float_text(region: &[u8]) -> bool {
    for (i, b) in region.iter().enumerate() {
        if *b == b'.' {
            let prev_digit = i > 0 && region[i - 1].is_ascii_digit();
            let next_digit = i + 1 < region.len() && region[i + 1].is_ascii_digit();
            if prev_digit || next_digit {
                return true;
            }
        }
    }
    false
}

/// §8 test #5: scan the raw bytes of every numeric column's value region for
/// text-encoded decimal floats. Returns the names of the columns that contain
/// one (empty = pass). The header, column names, and string dictionaries are
/// not value regions and are deliberately not scanned — the header legitimately
/// carries run-constant floats (e.g. `slippage`) in decimal text.
pub fn find_decimal_float_text(path: &Path) -> io::Result<Vec<String>> {
    let bytes = std::fs::read(path)?;
    if bytes.len() < 12 || &bytes[..8] != MAGIC {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "not a V82LDRG1 artifact"));
    }
    let header_len = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
    if 12 + header_len > bytes.len() {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "truncated artifact header"));
    }
    let header: Value = serde_json::from_slice(&bytes[12..12 + header_len])
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    let column_count = header["column_count"].as_u64().unwrap_or(0) as usize;
    let mut off = 12 + header_len;
    let mut hits = Vec::new();
    for _ in 0..column_count {
        let name_len = u16::from_le_bytes(take(&bytes, &mut off, 2)?.try_into().unwrap()) as usize;
        let name = String::from_utf8_lossy(take(&bytes, &mut off, name_len)?).to_string();
        let dtype = take(&bytes, &mut off, 1)?[0];
        let n = u32::from_le_bytes(take(&bytes, &mut off, 4)?.try_into().unwrap()) as usize;
        off += (n + 7) / 8; // validity bitmask
        match dtype {
            0 | 1 => {
                // I64 / F64: fixed-width binary — decimal text is a violation.
                let region = take(&bytes, &mut off, 8 * n)?;
                if has_decimal_float_text(region) {
                    hits.push(name);
                }
            }
            2 => {
                // Bool: one byte per row, still fixed-width binary.
                let region = take(&bytes, &mut off, n)?;
                if has_decimal_float_text(region) {
                    hits.push(name);
                }
            }
            3 => {
                // DictStr: ids then the dictionary; the dictionary is text by
                // design and is not a numeric value column.
                off += 2 * n;
                let dict_len = u32::from_le_bytes(take(&bytes, &mut off, 4)?.try_into().unwrap()) as usize;
                for _ in 0..dict_len {
                    let s_len = u32::from_le_bytes(take(&bytes, &mut off, 4)?.try_into().unwrap()) as usize;
                    off += s_len;
                }
            }
            other => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!("column {name}: unknown dtype {other}"),
                ));
            }
        }
    }
    Ok(hits)
}

/// One tape-retention record (LEDGER_FORMAT_SPEC §6): a tape hash and whether
/// that tape is retained. A tape referenced by any retained artifact is itself
/// retained — retention is what makes the VALUES tier legal (§6.1).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RetentionRecord {
    pub tape_hash: String,
    pub retained: bool,
}

/// The tape-retention store: one JSONL record per tape hash, appended on
/// insert so a later process resolves the same tapes (same pattern as the
/// cache store).
pub struct RetentionStore {
    map: HashMap<String, bool>,
    log_path: Option<PathBuf>,
}

impl RetentionStore {
    pub fn new() -> Self {
        RetentionStore { map: HashMap::new(), log_path: None }
    }

    /// Open a store backed by `log_path`, loading any existing records.
    pub fn open(log_path: &Path) -> io::Result<Self> {
        let mut store = RetentionStore::new();
        store.log_path = Some(log_path.to_path_buf());
        if log_path.exists() {
            let text = std::fs::read_to_string(log_path)?;
            for (i, line) in text.lines().enumerate() {
                if line.trim().is_empty() {
                    continue;
                }
                let rec: RetentionRecord = serde_json::from_str(line).map_err(|e| {
                    io::Error::new(io::ErrorKind::InvalidData, format!("retention line {}: {e}", i + 1))
                })?;
                store.map.insert(rec.tape_hash.clone(), rec.retained);
            }
        }
        Ok(store)
    }

    /// Record a tape's retention state, appending to the JSONL log first so a
    /// failed write leaves the in-memory map untouched (fail closed).
    pub fn insert(&mut self, tape_hash: &str, retained: bool) -> io::Result<()> {
        let rec = RetentionRecord { tape_hash: tape_hash.to_string(), retained };
        if let Some(path) = &self.log_path {
            let mut bytes = serde_json::to_vec(&rec)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            bytes.push(b'\n');
            let mut f = std::fs::OpenOptions::new().create(true).append(true).open(path)?;
            f.write_all(&bytes)?;
        }
        self.map.insert(tape_hash.to_string(), retained);
        Ok(())
    }

    /// §8 test #6: an artifact whose header references `tape_hash` resolves
    /// iff the tape is retained. A missing record — or a `retained: false`
    /// record — is reported by the audit tool, never silently accepted.
    pub fn resolves(&self, tape_hash: &str) -> Result<(), String> {
        match self.map.get(tape_hash) {
            Some(true) => Ok(()),
            Some(false) => Err(format!("tape {tape_hash} is marked not retained")),
            None => Err(format!("tape {tape_hash} has no retention record — not retained")),
        }
    }
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

// ---------------------------------------------------------------------------
// S5 ledger §8 cheap-test battery (LEDGER_FORMAT_SPEC §8; issue #109)
//
// The six tests run against a deterministic self-built VALUES-tier state
// fixture; a request may override the out_dir and the referenced tape hash.
// Every test is value-level, no wall clock enters any artifact (G5).
// ---------------------------------------------------------------------------

/// Fixture size in rows.
const FIXTURE_BARS: usize = 3;
/// Fixture first as-of clock.
const FIXTURE_AS_OF_BASE: i64 = 1_700_000_000_000;

/// The `close` value at bar `i` is a pure function of the as-of clock — the
/// fixture's stand-in for "a dropped field regenerated from (tape, code)".
fn ledger_fixture_close(as_of: i64) -> f64 {
    100.5 + (as_of - FIXTURE_AS_OF_BASE) as f64
}

/// The fixture's stored identity: SHA-1 of the regenerable fields, so §8 test
/// #1's "each regenerated field's hash equals the stored identity" is exact.
fn ledger_fixture_id(as_of: i64, close: f64) -> String {
    sha1_hex(format!("{as_of}|{close}").as_bytes())
}

/// Deterministic fixture row: (state_id, as_of, close).
fn ledger_fixture_row(i: usize) -> (String, i64, f64) {
    let as_of = FIXTURE_AS_OF_BASE + i as i64;
    let close = ledger_fixture_close(as_of);
    (ledger_fixture_id(as_of, close), as_of, close)
}

/// Write the ledger fixture to `dir/{name}.v82` and return its path. The same
/// request always writes the same bytes (G4); the fixture uses the production
/// tier machinery (state_artifact + add_field) so tier honesty and header
/// completeness are exercised on the real write path.
fn write_ledger_fixture(dir: &Path, rc: &RunConstants, name: &str) -> io::Result<PathBuf> {
    let mut a = state_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), rc);
    let sid = a
        .add_field("state_id", DType::DictStr, FieldTier::IdentityOnly)
        .map_err(io::Error::other)?;
    let as_of = a
        .add_field("as_of", DType::I64, FieldTier::IdentityOnly)
        .map_err(io::Error::other)?;
    let close = a
        .add_field("close", DType::F64, FieldTier::Values)
        .map_err(io::Error::other)?;
    for i in 0..FIXTURE_BARS {
        let (state_id, as_of_v, close_v) = ledger_fixture_row(i);
        a.columns[sid].push_str(&state_id);
        a.columns[as_of].push_i64(as_of_v);
        a.columns[close].push_f64(close_v);
        a.end_row();
    }
    let path = dir.join(format!("{name}.v82"));
    a.write(&path)?;
    Ok(path)
}

/// §8 test #1 (round-trip): a VALUES artifact is written, read back, and every
/// dropped field regenerated from the identity equals the stored value, with
/// its hash equal to the stored identity.
fn battery_round_trip(dir: &Path, rc: &RunConstants) -> Result<(), String> {
    let path = write_ledger_fixture(dir, rc, "rt-fixture").map_err(|e| e.to_string())?;
    let back = read_artifact(&path).map_err(|e| e.to_string())?;
    if back.header["artifact_kind"].as_str() != Some("state") {
        return Err("read-back artifact_kind is not 'state'".into());
    }
    if back.header["tier"].as_str() != Some("VALUES") {
        return Err("read-back tier is not VALUES".into());
    }
    if back.header["hash_encoding"].as_str() != Some(HASH_ENCODING) {
        return Err("read-back hash_encoding is not the declared encoding".into());
    }
    if back.row_count() != FIXTURE_BARS {
        return Err(format!("read-back row count {} != {FIXTURE_BARS}", back.row_count()));
    }
    let sid = back.column("state_id").ok_or("no state_id column")?;
    let asof = back.column("as_of").ok_or("no as_of column")?;
    let close = back.column("close").ok_or("no close column")?;
    for i in 0..FIXTURE_BARS {
        let (exp_sid, exp_asof, exp_close) = ledger_fixture_row(i);
        if sid[i].as_ref().and_then(Value::as_str) != Some(exp_sid.as_str()) {
            return Err(format!("row {i}: stored identity {sid:?} != {exp_sid}"));
        }
        if asof[i].as_ref().and_then(Value::as_i64) != Some(exp_asof) {
            return Err(format!("row {i}: stored as_of {asof:?} != {exp_asof}"));
        }
        if close[i].as_ref().and_then(Value::as_f64).map(f64::to_bits) != Some(exp_close.to_bits()) {
            return Err(format!("row {i}: stored close {close:?} != {exp_close} (bits)"));
        }
        // Regeneration: close is a pure function of as_of, and re-hashing it
        // reproduces the stored identity exactly.
        let regen_close = ledger_fixture_close(exp_asof);
        if regen_close.to_bits() != exp_close.to_bits() {
            return Err(format!("row {i}: regenerated close != stored close"));
        }
        if ledger_fixture_id(exp_asof, regen_close) != exp_sid {
            return Err(format!("row {i}: regenerated field's hash != stored identity"));
        }
    }
    Ok(())
}

/// §8 test #2 (header completeness): the header carries every run-constant;
/// removing any one of them fails closed instead of producing a row with a
/// missing field.
fn battery_header_completeness(dir: &Path, rc: &RunConstants) -> Result<(), String> {
    let path = write_ledger_fixture(dir, rc, "hdr-fixture").map_err(|e| e.to_string())?;
    let h = read_header(&path).map_err(|e| e.to_string())?;
    validate_header(&h)?;
    let rc_keys: Vec<String> = RunConstants::REQUIRED_KEYS
        .iter()
        .map(|s| s.to_string())
        .chain(["symbol".into(), "interval".into(), "generator".into()])
        .collect();
    for key in &rc_keys {
        let mut corrupt = h.clone();
        corrupt["run_constants"]
            .as_object_mut()
            .ok_or("run_constants is not an object")?
            .remove(key);
        if validate_header(&corrupt).is_ok() {
            return Err(format!("header without run-constant {key} did not fail closed"));
        }
    }
    for field in ["hash_encoding", "tier"] {
        let mut corrupt = h.clone();
        corrupt.as_object_mut().ok_or("header is not an object")?.remove(field);
        if validate_header(&corrupt).is_ok() {
            return Err(format!("header without {field} did not fail closed"));
        }
    }
    Ok(())
}

/// §8 test #3 (byte-stability): two runs of the same request write
/// byte-identical artifacts with identical fingerprints (G4).
fn battery_byte_stability(dir: &Path, rc: &RunConstants) -> Result<(), String> {
    let p1 = write_ledger_fixture(dir, rc, "bs-fixture-1").map_err(|e| e.to_string())?;
    let p2 = write_ledger_fixture(dir, rc, "bs-fixture-2").map_err(|e| e.to_string())?;
    let b1 = std::fs::read(&p1).map_err(|e| e.to_string())?;
    let b2 = std::fs::read(&p2).map_err(|e| e.to_string())?;
    if b1 != b2 {
        return Err("two runs of the same request are not byte-identical".into());
    }
    let f1 = fingerprint(&p1).map_err(|e| e.to_string())?;
    let f2 = fingerprint(&p2).map_err(|e| e.to_string())?;
    if f1 != f2 {
        return Err(format!("fingerprints differ: {f1} vs {f2}"));
    }
    Ok(())
}

/// §8 test #4 (tier honesty): a VALUES artifact rejects a FULL-only field
/// with an explicit TierViolation, and no tier below a field's requirement
/// can serve it — the failure is explicit, never an empty column.
fn battery_tier_honesty(rc: &RunConstants) -> Result<(), String> {
    let mut v = state_artifact(ArtifactTier::Values, "SOLUSDT", "15m", &generator_tag(), rc);
    v.add_field("state_id", DType::DictStr, FieldTier::IdentityOnly)
        .map_err(|e| e.to_string())?;
    v.add_field("close", DType::F64, FieldTier::Values)
        .map_err(|e| e.to_string())?;
    match v.add_field("lineage_hash", DType::DictStr, FieldTier::Full) {
        Err(TierViolation { field, field_tier, artifact_tier }) => {
            if field != "lineage_hash"
                || field_tier != FieldTier::Full
                || artifact_tier != ArtifactTier::Values
            {
                return Err(format!("unexpected TierViolation: {field}"));
            }
        }
        Ok(_) => return Err("VALUES artifact accepted a FULL-only field".into()),
    }
    if ArtifactTier::IdentityOnly.can_serve(FieldTier::Values) {
        return Err("IDENTITY_ONLY artifact claims to serve a VALUES field".into());
    }
    if ArtifactTier::Values.can_serve(FieldTier::Full) {
        return Err("VALUES artifact claims to serve a FULL field".into());
    }
    if !ArtifactTier::Full.can_serve(FieldTier::Full) {
        return Err("FULL artifact cannot serve a FULL field".into());
    }
    Ok(())
}

/// §8 test #5 (no decimal floats): no numeric value column contains text
/// encoding of a float; the scan is value-region scoped, so the header's
/// run-constant decimal (slippage 0.5) is not a hit.
fn battery_no_decimal_floats(dir: &Path, rc: &RunConstants) -> Result<(), String> {
    let path = write_ledger_fixture(dir, rc, "ndf-fixture").map_err(|e| e.to_string())?;
    let hits = find_decimal_float_text(&path).map_err(|e| e.to_string())?;
    if !hits.is_empty() {
        return Err(format!("decimal float text in numeric columns: {}", hits.join(", ")));
    }
    // Prove the scan is region-scoped: the artifact bytes DO contain a '.'
    // (the header's slippage 0.5) yet no numeric value column tripped.
    let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
    if !bytes.contains(&b'.') {
        return Err("fixture must carry a header decimal for the region-scope claim".into());
    }
    Ok(())
}

/// §8 test #6 (retention): the artifact header carries the referenced tape
/// hash; when a retention record exists the artifact resolves, and when none
/// exists the audit tool reports it rather than silently accepting it.
fn battery_retention(dir: &Path, rc: &RunConstants) -> Result<(), String> {
    let store_path = dir.join("retention.jsonl");
    let mut store = RetentionStore::open(&store_path).map_err(|e| e.to_string())?;
    store.insert(&rc.data_hash, true).map_err(|e| e.to_string())?;
    store.resolves(&rc.data_hash).map_err(|e| e.to_string())?;
    if store.resolves("missing0000000000000000000000000000000000").is_ok() {
        return Err("artifact referencing an unretained tape was silently accepted".into());
    }
    // Persistence: a fresh store over the same JSONL still resolves.
    let store2 = RetentionStore::open(&store_path).map_err(|e| e.to_string())?;
    store2.resolves(&rc.data_hash).map_err(|e| e.to_string())?;
    Ok(())
}

/// Run the six-test §8 battery; each entry is `(test name, result)`.
fn run_ledger_battery(dir: &Path, rc: &RunConstants) -> Vec<(&'static str, Result<(), String>)> {
    vec![
        ("round-trip", battery_round_trip(dir, rc)),
        ("header-completeness", battery_header_completeness(dir, rc)),
        ("byte-stability", battery_byte_stability(dir, rc)),
        ("tier-honesty", battery_tier_honesty(rc)),
        ("no-decimal-floats", battery_no_decimal_floats(dir, rc)),
        ("retention", battery_retention(dir, rc)),
    ]
}

/// The run-constants for the ledger fixture. `data_hash` is the referenced
/// tape hash (§6), so retention binds the artifact to the store.
fn ledger_run_constants(tape_hash: &str) -> RunConstants {
    RunConstants {
        data_hash: tape_hash.to_string(),
        code_hash: sha1_hex(b"v8-core-ledger-code"),
        config_hash: sha1_hex(b"v8-core-ledger-config"),
        simulator_hash: sha1_hex(b"v8-core-ledger-sim"),
        risk_gate_hash: sha1_hex(b"v8-core-ledger-risk-gate"),
        evaluator_version: "evaluate/0.9.1".to_string(),
        platform: "cpu".to_string(),
        utility_unit: "quote".to_string(),
        cost_form: "taker-bps".to_string(),
        slippage: 0.5,
        action_manifest_id: "manifest-ledger-fixture".to_string(),
    }
}

/// S5 ledger §8 cheap-test driver (issue #109): round-trip, header
/// completeness, byte-stability, tier honesty, no-decimal-floats scan,
/// retention — extended to verdict artifacts at S7 (issue #123).
///
/// Accepts an optional request.json (only `out_dir` and `tape_hash` are
/// consumed; the battery is otherwise self-built) and prints one PASS/FAIL
/// line per test. Returns 0 only if all six pass.
pub fn ledger_check(args: &[String]) -> i32 {
    if args.len() > 1 {
        eprintln!("usage: v8-core ledger-check [request.json]");
        return 2;
    }
    let default_tape = || sha1_hex(b"v8-ledger-fixture-tape");
    let (out_dir, tape_hash) = match args.first() {
        Some(path) => {
            let req: Value = match std::fs::read(path)
                .map_err(|e| format!("cannot read request {path}: {e}"))
                .and_then(|b| serde_json::from_slice(&b).map_err(|e| format!("cannot parse request {path}: {e}")))
            {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("error: {e}");
                    return 1;
                }
            };
            let dir = req
                .get("out_dir")
                .and_then(Value::as_str)
                .map(PathBuf::from)
                .unwrap_or_else(|| std::env::temp_dir().join("v82-ledger-check"));
            let tape = req
                .get("tape_hash")
                .and_then(Value::as_str)
                .map(|s| s.to_string())
                .unwrap_or_else(default_tape);
            (dir, tape)
        }
        None => (std::env::temp_dir().join("v82-ledger-check"), default_tape()),
    };
    if let Err(e) = std::fs::create_dir_all(&out_dir) {
        eprintln!("error: out_dir {out_dir:?}: {e}");
        return 1;
    }
    let rc = ledger_run_constants(&tape_hash);
    let results = run_ledger_battery(&out_dir, &rc);
    let mut all_pass = true;
    for (name, res) in &results {
        match res {
            Ok(()) => println!("ledger-check: {name}: PASS"),
            Err(e) => {
                eprintln!("ledger-check: {name}: FAIL — {e}");
                all_pass = false;
            }
        }
    }
    if all_pass {
        println!("ledger-check: all {} tests passed", results.len());
        0
    } else {
        eprintln!("ledger-check: FAILED");
        1
    }
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

    // ---------------------------------------------------------------------
    // S5 ledger §8 battery (issue #109): the six cheap tests run end to end
    // against the deterministic fixture.
    // ---------------------------------------------------------------------

    const BATTERY_FILES: [&str; 5] = [
        "rt-fixture.v82",
        "hdr-fixture.v82",
        "ndf-fixture.v82",
        "bs-fixture-1.v82",
        "bs-fixture-2.v82",
    ];

    #[test]
    fn ledger_battery_all_six_cheap_tests_pass() {
        let dir = std::env::temp_dir();
        let results = run_ledger_battery(&dir, &test_rc());
        assert_eq!(results.len(), 6, "the battery is the six §8 tests");
        for (name, res) in &results {
            assert!(res.is_ok(), "{name} failed: {:?}", res);
        }
        for f in BATTERY_FILES {
            std::fs::remove_file(dir.join(f)).ok();
        }
        std::fs::remove_file(dir.join("retention.jsonl")).ok();
    }

    #[test]
    fn round_trip_regenerates_dropped_fields_and_identity() {
        // §8 test #1 at value level: write the fixture, read it back, and
        // regenerate every dropped field from the identity — its hash must
        // equal the stored identity (bit-exact).
        let dir = std::env::temp_dir();
        let path = write_ledger_fixture(&dir, &test_rc(), "rt-solo").unwrap();
        let back = read_artifact(&path).unwrap();
        assert_eq!(back.header["artifact_kind"], "state");
        assert_eq!(back.header["tier"], "VALUES");
        assert_eq!(back.header["hash_encoding"], HASH_ENCODING);
        assert_eq!(back.row_count(), FIXTURE_BARS);
        let sid = back.column("state_id").unwrap();
        let asof = back.column("as_of").unwrap();
        let close = back.column("close").unwrap();
        for i in 0..FIXTURE_BARS {
            let (exp_sid, exp_asof, exp_close) = ledger_fixture_row(i);
            assert_eq!(sid[i].as_ref().and_then(Value::as_str), Some(exp_sid.as_str()));
            assert_eq!(asof[i].as_ref().and_then(Value::as_i64), Some(exp_asof));
            assert_eq!(
                close[i].as_ref().and_then(Value::as_f64).map(f64::to_bits),
                Some(exp_close.to_bits())
            );
            let regen_close = ledger_fixture_close(exp_asof);
            assert_eq!(regen_close.to_bits(), exp_close.to_bits());
            assert_eq!(ledger_fixture_id(exp_asof, regen_close), exp_sid);
        }
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn removing_any_run_constant_fails_closed() {
        // §8 test #2: the complete header validates; removing any one
        // run-constant (or hash_encoding / tier) fails closed with the missing
        // key named.
        let dir = std::env::temp_dir();
        let path = write_ledger_fixture(&dir, &test_rc(), "hdr-solo").unwrap();
        let h = read_header(&path).unwrap();
        validate_header(&h).expect("complete header must validate");
        let mut keys: Vec<&str> = RunConstants::REQUIRED_KEYS.to_vec();
        keys.extend(["symbol", "interval", "generator"]);
        for key in keys {
            let mut corrupt = h.clone();
            corrupt["run_constants"].as_object_mut().unwrap().remove(key);
            let err = validate_header(&corrupt).unwrap_err();
            assert!(err.contains(key), "error must name the missing key: {err}");
        }
        for field in ["hash_encoding", "tier"] {
            let mut corrupt = h.clone();
            corrupt.as_object_mut().unwrap().remove(field);
            let err = validate_header(&corrupt).unwrap_err();
            assert!(err.contains(field), "error must name the missing field: {err}");
        }
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn ledger_fixture_two_writes_are_byte_identical() {
        // §8 test #3: same request, byte-identical artifacts and fingerprints.
        let dir = std::env::temp_dir();
        let rc = test_rc();
        let p1 = write_ledger_fixture(&dir, &rc, "bs-a").unwrap();
        let p2 = write_ledger_fixture(&dir, &rc, "bs-b").unwrap();
        assert_eq!(std::fs::read(&p1).unwrap(), std::fs::read(&p2).unwrap());
        assert_eq!(fingerprint(&p1).unwrap(), fingerprint(&p2).unwrap());
        std::fs::remove_file(&p1).ok();
        std::fs::remove_file(&p2).ok();
    }

    #[test]
    fn numeric_value_regions_contain_no_decimal_float_text() {
        // §8 test #5: the scan finds nothing in the numeric value regions,
        // even though the header legitimately carries a decimal (slippage 0.5)
        // — the scan is region-scoped.
        let dir = std::env::temp_dir();
        let path = write_ledger_fixture(&dir, &test_rc(), "ndf-solo").unwrap();
        assert_eq!(find_decimal_float_text(&path).unwrap(), Vec::<String>::new());
        let bytes = std::fs::read(&path).unwrap();
        assert!(bytes.contains(&b'.'), "header decimal must exist to prove scoping");
        // Pattern-level checks on the scan function itself.
        assert!(has_decimal_float_text(b"0.5"));
        assert!(has_decimal_float_text(b"12.5"));
        assert!(has_decimal_float_text(b".5"));
        assert!(!has_decimal_float_text(&[0x00, 0x2E, 0x00])); // '.' not digit-adjacent
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn retention_requires_a_retained_record() {
        // §8 test #6: no record -> reported; retained:true -> resolves;
        // retained:false -> reported; records survive a reopen.
        let dir = std::env::temp_dir();
        let store_path = dir.join("retention-test.jsonl");
        std::fs::remove_file(&store_path).ok();
        let mut store = RetentionStore::open(&store_path).unwrap();
        assert!(store.resolves("abcd").is_err(), "no record yet — must not resolve");
        store.insert("abcd", true).unwrap();
        store.resolves("abcd").expect("retained tape resolves");
        store.insert("efgh", false).unwrap();
        let err = store.resolves("efgh").unwrap_err();
        assert!(err.contains("not retained"), "{err}");
        let store2 = RetentionStore::open(&store_path).unwrap();
        store2.resolves("abcd").expect("record survives reopen");
        std::fs::remove_file(&store_path).ok();
    }

    #[test]
    fn fixture_identity_is_a_hash_of_regenerable_fields() {
        // The fixture's stored identity must be deterministic and change when
        // the regenerable fields change (the round-trip regeneration anchor).
        let (sid0, asof0, close0) = ledger_fixture_row(0);
        let (sid1, asof1, close1) = ledger_fixture_row(1);
        assert_ne!(sid0, sid1);
        assert_ne!(asof0, asof1);
        assert_ne!(close0.to_bits(), close1.to_bits());
        assert_eq!(sid0, ledger_fixture_id(asof0, close0));
        assert_ne!(sid0, ledger_fixture_id(asof0, close0 + 1.0));
    }
}
