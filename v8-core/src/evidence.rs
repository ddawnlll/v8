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

use std::io;
use std::path::Path;

use sha1::{Digest, Sha1};

use crate::hash::HASH_ENCODING;

pub const MAGIC: &[u8; 8] = b"V82LDRG1";

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
}
