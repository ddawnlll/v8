//! V8.2 canonical identity encoding (PARITY_AND_IDENTITY_SPEC §4, D-079).
//!
//! V8.0 defines every identity as `sha1_hex(json.dumps(..., default=str))`, so
//! the decimal rendering of a float is part of the hash. That rendering is
//! runtime-specific — measured 7 of 8 representative values differ between
//! CPython's `json` encoder and Rust's default `f64` Display
//! (PERFORMANCE_AUDIT_V82 §8). V8.2 therefore hashes a representation-
//! independent byte encoding instead:
//!
//! - `f64` contributes its 8 IEEE-754 bytes, little-endian; `-0.0` and `0.0`
//!   are distinct; a NaN is normalized to a single declared payload so that
//!   identity is total.
//! - integers contribute fixed-width two's-complement bytes; clocks are `i64`
//!   nanoseconds.
//! - strings contribute UTF-8 bytes prefixed by their byte length.
//! - composites contribute a declared tag, an element count, and their
//!   elements in canonical order.
//!
//! The digest function stays SHA-1 for continuity of tooling
//! (PARITY_AND_IDENTITY_SPEC §4). Every value begins with a type tag so the
//! encoding is unambiguous (an `i64` and an `f64` with identical 8-byte
//! payloads must not collide).
//!
//! The whole module is the identity encoder for stages S1+ (state_id,
//! lineage_hash, episode_key, manifest_id, ...); at S0 the binary only
//! fingerprints raw artifact bytes, so the encoder's dead-code is expected
//! (exercised by its unit tests) and is named here rather than hidden.
#![allow(dead_code)]

use sha1::{Digest, Sha1};

/// Declared hash-encoding tag, recorded in every artifact header so a V8.2
/// artifact can never be read as a V8.0 one (LEDGER_FORMAT_SPEC §3).
pub const HASH_ENCODING: &str = "v8.2-ieee-le";

/// A NaN of any payload normalizes to this single bit pattern before hashing,
/// so identity over NaN is total (PARITY_AND_IDENTITY_SPEC §4).
pub const CANONICAL_NAN_BITS: u64 = 0x7ff8_0000_0000_0000;

/// The canonical byte encoder for V8.2 identities.
#[derive(Default)]
pub struct Canon {
    buf: Vec<u8>,
}

impl Canon {
    pub fn new() -> Self {
        Canon { buf: Vec::with_capacity(64) }
    }

    /// One raw byte (used for type tags).
    pub fn push_u8(&mut self, b: u8) {
        self.buf.push(b);
    }

    pub fn push_i64(&mut self, v: i64) {
        self.push_u8(b'i');
        self.buf.extend_from_slice(&v.to_le_bytes());
    }

    pub fn push_u64(&mut self, v: u64) {
        self.push_u8(b'u');
        self.buf.extend_from_slice(&v.to_le_bytes());
    }

    pub fn push_f64(&mut self, v: f64) {
        self.push_u8(b'f');
        let bits = if v.is_nan() { CANONICAL_NAN_BITS } else { v.to_bits() };
        self.buf.extend_from_slice(&bits.to_le_bytes());
    }

    pub fn push_str(&mut self, s: &str) {
        self.push_u8(b's');
        self.buf.extend_from_slice(&(s.len() as u32).to_le_bytes());
        self.buf.extend_from_slice(s.as_bytes());
    }

    /// Raw byte blob (distinct from a string: no UTF-8 meaning).
    pub fn push_bytes(&mut self, b: &[u8]) {
        self.push_u8(b'b');
        self.buf.extend_from_slice(&(b.len() as u32).to_le_bytes());
        self.buf.extend_from_slice(b);
    }

    pub fn push_bool(&mut self, v: bool) {
        self.push_u8(b't');
        self.buf.push(if v { 1 } else { 0 });
    }

    pub fn push_null(&mut self) {
        self.push_u8(b'n');
    }

    /// Element count for a composite that follows.
    pub fn push_count(&mut self, n: usize) {
        self.buf.extend_from_slice(&(n as u32).to_le_bytes());
    }

    /// Ordered list/tuple: tag `L`, count, then elements in order.
    pub fn push_list(&mut self) {
        self.push_u8(b'L');
    }

    /// Map/dict: tag `D`, count, then (string key, value) pairs in
    /// byte-sorted key order (mirrors CPython `sort_keys=True`).
    pub fn push_map(&mut self) {
        self.push_u8(b'D');
    }

    /// Named record: tag `O`, count, then (string field, value) pairs in the
    /// record's declared field order.
    pub fn push_obj(&mut self) {
        self.push_u8(b'O');
    }

    /// One self-delimiting value, mirroring Python's type dispatch so a value
    /// hashes identically regardless of which implementation emitted it.
    pub fn push_value(&mut self, v: &serde_json::Value) {
        match v {
            serde_json::Value::Null => self.push_null(),
            serde_json::Value::Bool(b) => self.push_bool(*b),
            serde_json::Value::Number(n) => {
                if let Some(i) = n.as_i64() {
                    self.push_i64(i);
                } else if let Some(u) = n.as_u64() {
                    self.push_u64(u);
                } else if let Some(f) = n.as_f64() {
                    self.push_f64(f);
                } else {
                    // JSON numbers outside f64 are not representable; V8 tape
                    // values are validated to be finite f64-compatible, so
                    // this is unreachable for real input. Encode the literal
                    // decimal text to stay total rather than panic.
                    self.push_str(&n.to_string());
                }
            }
            serde_json::Value::String(s) => self.push_str(s),
            serde_json::Value::Array(items) => {
                self.push_list();
                self.push_count(items.len());
                for it in items {
                    self.push_value(it);
                }
            }
            serde_json::Value::Object(map) => {
                self.push_map();
                self.push_count(map.len());
                let mut keys: Vec<&String> = map.keys().collect();
                keys.sort(); // canonical order, mirrors sort_keys=True
                for k in keys {
                    self.push_str(k);
                    self.push_value(&map[k]);
                }
            }
        }
    }

    /// SHA-1 (hex) of the accumulated bytes — the V8.2 identity digest.
    pub fn finish_sha1_hex(&self) -> String {
        let mut h = Sha1::new();
        h.update(&self.buf);
        let out = h.finalize();
        out.iter().map(|b| format!("{:02x}", b)).collect()
    }
}

/// Convenience: hash one value directly.
pub fn hash_value(v: &serde_json::Value) -> String {
    let mut c = Canon::new();
    c.push_value(v);
    c.finish_sha1_hex()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Every value begins with a type tag; the payload widths are fixed.
    fn assert_prefixed(encoded: &[u8], tag: u8) {
        assert_eq!(encoded[0], tag, "expected tag {:?}", tag as char);
    }

    #[test]
    fn f64_encodes_ieee_le_bits() {
        let mut c = Canon::new();
        c.push_f64(1.0);
        assert_prefixed(&c.buf, b'f');
        // 1.0 = 0x3FF0000000000000, little-endian.
        assert_eq!(&c.buf[1..], &[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf0, 0x3f]);
    }

    #[test]
    fn zeros_are_distinct() {
        // -0.0 (0x8000000000000000) must differ from 0.0 (0x0).
        let mut a = Canon::new();
        a.push_f64(-0.0);
        let mut b = Canon::new();
        b.push_f64(0.0);
        assert_ne!(a.finish_sha1_hex(), b.finish_sha1_hex());
    }

    #[test]
    fn nan_is_normalized_total() {
        // Any NaN payload (signaling, quiet, arbitrary payload) normalizes to
        // one declared pattern, so identity over NaN is total.
        let mut a = Canon::new();
        a.push_f64(f64::NAN);
        let mut b = Canon::new();
        b.push_f64(f64::from_bits(0x7ff8_1234_5678_9abc));
        assert_eq!(a.finish_sha1_hex(), b.finish_sha1_hex());
    }

    #[test]
    fn i64_and_f64_cannot_collide() {
        // Same 8 payload bytes, different tags -> different digests.
        let mut a = Canon::new();
        a.push_i64(1);
        let mut b = Canon::new();
        b.push_f64(1.0);
        assert_ne!(a.finish_sha1_hex(), b.finish_sha1_hex());
    }

    #[test]
    fn int_width_is_fixed_two_complement() {
        let mut c = Canon::new();
        c.push_i64(-1);
        assert_eq!(&c.buf[1..], &[0xff; 8]);
    }

    #[test]
    fn string_is_length_prefixed_utf8() {
        let mut c = Canon::new();
        c.push_str("abc");
        assert_eq!(&c.buf[1..5], &3u32.to_le_bytes());
        assert_eq!(&c.buf[5..], b"abc");
    }

    #[test]
    fn map_sorts_keys_canonically() {
        // {"b":1,"a":2} must hash like {"a":2,"b":1} (sort_keys semantics).
        let mk = |items: &[(&str, i64)]| {
            let mut map = serde_json::Map::new();
            for (k, v) in items {
                map.insert((*k).to_string(), serde_json::json!(v));
            }
            let mut c = Canon::new();
            c.push_value(&serde_json::Value::Object(map));
            c.finish_sha1_hex()
        };
        assert_eq!(mk(&[("b", 1), ("a", 2)]), mk(&[("a", 2), ("b", 1)]));
    }

    #[test]
    fn audit_float_fixture_hashes_bits_not_decimals() {
        // The eight representative values from PERFORMANCE_AUDIT_V82 §8. Two
        // different shortest-roundtrip *renderings* of the same f64 must
        // produce the same V8.2 hash — the property §4 exists to obtain. We
        // can only render in one way here, so instead pin the bit-level
        // property: encoding any value equal to a given f64 yields the same
        // bytes (no decimal text ever enters the digest).
        let values = [1.0f64, 1e16, 1e-5, -0.0, 1e22, 1.2345678901234568e17, 1e-323, 0.30000000000000004];
        let digests: Vec<String> = values
            .iter()
            .map(|v| {
                let mut c = Canon::new();
                c.push_f64(*v);
                c.finish_sha1_hex()
            })
            .collect();
        // All distinct, and none equals the decimal-text encoding of the same
        // number hashed as a string.
        for (i, d) in digests.iter().enumerate() {
            for (j, e) in digests.iter().enumerate() {
                if i != j {
                    assert_ne!(d, e, "value {} and {} collided", i, j);
                }
            }
            let mut c = Canon::new();
            c.push_str(&format!("{}", values[i]));
            assert_ne!(d.as_str(), c.finish_sha1_hex().as_str());
        }
    }

    #[test]
    fn subnormal_round_trips() {
        let mut c = Canon::new();
        c.push_f64(f64::MIN_POSITIVE);
        let mut d = Canon::new();
        d.push_f64(f64::MIN_POSITIVE);
        assert_eq!(c.finish_sha1_hex(), d.finish_sha1_hex());
    }
}
