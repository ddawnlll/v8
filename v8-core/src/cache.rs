//! S5 content-addressed DAG cache (issue #107; COMPUTE_CORE_SPEC §8 S5).
//!
//! The missing node is cube level — (candidate_id, action_id, simulator_hash,
//! data_hash) -> outcome. The store is content-addressed: a canonical string
//! key `{candidate_id}|{action_id}|{simulator_hash}|{data_hash}` is hashed to
//! a SHA-1 content address, and entries are addressable by that digest, never
//! by a run-global id. The gate (COMPUTE_CORE_SPEC §8 S5): a cache hit must
//! never change the ledger identity — a request that hits the cache writes
//! byte-identical artifacts to a request that misses and recomputes.
//! `cache_check` simulates both paths and asserts artifact-fingerprint
//! equality (LEDGER_FORMAT_SPEC §8 test 3). The store is an in-memory map
//! plus an append-only JSONL log, so a later process hits the same entries.

use std::collections::HashMap;
use std::io;
use std::io::Write;
use std::path::{Path, PathBuf};

use serde_json::Value;
use sha1::{Digest, Sha1};

use crate::evidence::{self, Artifact, DType};
use crate::hash::HASH_ENCODING;

/// The canonical string key of a cube-level node. Same inputs always produce
/// the same key; the whole tuple is one cache entry.
pub fn canonical_key(candidate_id: &str, action_id: &str, simulator_hash: &str, data_hash: &str) -> String {
    format!("{candidate_id}|{action_id}|{simulator_hash}|{data_hash}")
}

/// SHA-1 (hex) of the canonical key bytes — the content address that keys the
/// store. Deterministic: no wall clock, no run-global state.
pub fn key_digest(canonical: &str) -> String {
    let mut h = Sha1::new();
    Digest::update(&mut h, canonical.as_bytes());
    h.finalize().iter().map(|b| format!("{:02x}", b)).collect()
}

/// One cache entry: the content address, the canonical key it was derived
/// from, and the outcome payload. Serialized one-per-line into the JSONL log.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CacheEntry {
    pub digest: String,
    pub key: String,
    pub outcome: Value,
}

/// Minimal content-addressed store: `sha1(canonical key)` -> outcome. In
/// memory as a map; when opened at a path, entries are also appended to a
/// JSONL log (one JSON object per line) so a later process can hit them.
pub struct CacheStore {
    map: HashMap<String, CacheEntry>,
    log_path: Option<PathBuf>,
}

impl CacheStore {
    pub fn new() -> Self {
        CacheStore { map: HashMap::new(), log_path: None }
    }

    /// Open a store backed by `log_path`, loading any existing entries (last
    /// line wins for a repeated digest) and appending future inserts.
    pub fn open(log_path: &Path) -> io::Result<Self> {
        let mut store = CacheStore::new();
        store.log_path = Some(log_path.to_path_buf());
        if log_path.exists() {
            let text = std::fs::read_to_string(log_path)?;
            for (i, line) in text.lines().enumerate() {
                if line.trim().is_empty() {
                    continue;
                }
                let entry: CacheEntry = serde_json::from_str(line).map_err(|e| {
                    io::Error::new(io::ErrorKind::InvalidData, format!("cache line {}: {e}", i + 1))
                })?;
                store.map.insert(entry.digest.clone(), entry);
            }
        }
        Ok(store)
    }

    /// Insert (or overwrite) the outcome for a canonical key and return its
    /// content address. The entry is appended to the JSONL log first, so a
    /// failed write leaves the in-memory map untouched (fail closed).
    pub fn insert(&mut self, key: &str, outcome: Value) -> io::Result<String> {
        let digest = key_digest(key);
        let entry = CacheEntry { digest: digest.clone(), key: key.to_string(), outcome };
        if let Some(path) = &self.log_path {
            let mut bytes = serde_json::to_vec(&entry)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            bytes.push(b'\n');
            let mut f = std::fs::OpenOptions::new().create(true).append(true).open(path)?;
            f.write_all(&bytes)?;
        }
        self.map.insert(digest.clone(), entry);
        Ok(digest)
    }

    /// Retrieve the outcome for a canonical key — a hit returns the stored
    /// outcome, a miss returns None.
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.map.get(&key_digest(key)).map(|e| &e.outcome)
    }

    #[allow(dead_code)] // exercised by unit tests
    pub fn len(&self) -> usize {
        self.map.len()
    }
}

/// Simulated cube outcome: a deterministic pure function of the key and its
/// content address, standing in for Replay + CubeReducer. A real request
/// replaces this function; the identity gate only needs the outcome to be a
/// pure function of the key, so a recompute and a cache hit agree.
fn compute_outcome(key: &str, digest: &str) -> Value {
    let seed = u32::from_str_radix(&digest[..8], 16).unwrap_or(0);
    serde_json::json!({
        "cache_key": key,
        "digest": digest,
        "net_pnl_bps": (seed % 10_000) as i64,
    })
}

/// Write one cube outcome artifact. Both the miss path (computed outcome) and
/// the hit path (outcome read back from cache) call this with the same
/// arguments, so the artifact bytes are identical (LEDGER_FORMAT_SPEC §8
/// test 3). Returns the artifact fingerprint.
fn write_outcome_artifact(
    path: &Path,
    candidate_id: &str,
    action_id: &str,
    simulator_hash: &str,
    data_hash: &str,
    digest: &str,
    outcome: &Value,
) -> io::Result<String> {
    let mut art = Artifact::new(
        "cube",
        "VALUES",
        serde_json::json!({
            "hash_encoding": HASH_ENCODING,
            "cache_key": canonical_key(candidate_id, action_id, simulator_hash, data_hash),
        }),
        "candidate_id,action_id,simulator_hash,data_hash",
    );
    let c_cid = art.add_column("candidate_id", DType::DictStr);
    let c_aid = art.add_column("action_id", DType::DictStr);
    let c_sh = art.add_column("simulator_hash", DType::DictStr);
    let c_dh = art.add_column("data_hash", DType::DictStr);
    let c_digest = art.add_column("digest", DType::DictStr);
    let c_pnl = art.add_column("net_pnl_bps", DType::I64);

    art.columns[c_cid].push_str(candidate_id);
    art.columns[c_aid].push_str(action_id);
    art.columns[c_sh].push_str(simulator_hash);
    art.columns[c_dh].push_str(data_hash);
    art.columns[c_digest].push_str(digest);
    art.columns[c_pnl].push_i64(outcome["net_pnl_bps"].as_i64().unwrap_or(0));
    art.end_row();
    art.write(path)?;
    evidence::fingerprint(path)
}

/// S5 gate driver (`cache-check`; COMPUTE_CORE_SPEC §8 S5). Loads a request,
/// derives the cube key, then simulates a miss (compute + store + write) and
/// a hit (fresh store over the same JSONL log + write) and asserts the two
/// artifact fingerprints are identical. Returns 0 on pass, 1 on fail.
pub fn cache_check(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core cache-check <request.json>");
        return 2;
    }
    let path = &args[0];
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

    // Cube key from the request; a request may carry these top-level or under
    // `manifest`. Defaults keep the check runnable on a plain ingest-style
    // request; the gate is identity stability, not the particular key.
    let field = |name: &str, fallback: &str| -> String {
        req.get(name)
            .and_then(Value::as_str)
            .or_else(|| req.get("manifest").and_then(|m| m.get(name)).and_then(Value::as_str))
            .map(|s| s.to_string())
            .unwrap_or_else(|| fallback.to_string())
    };
    let candidate_id = field("candidate_id", "fixture-candidate");
    let action_id = field("action_id", "BUY");
    let simulator_hash = field("simulator_hash", "sim-v0");
    let data_hash = field("data_hash", "tape-v0");
    let out_dir = req
        .get("out_dir")
        .and_then(Value::as_str)
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::temp_dir().join("v82-cache-check"));
    if let Err(e) = std::fs::create_dir_all(&out_dir) {
        eprintln!("error: out_dir {out_dir:?}: {e}");
        return 1;
    }

    let key = canonical_key(&candidate_id, &action_id, &simulator_hash, &data_hash);
    let digest = key_digest(&key);
    let log_path = out_dir.join("cache.jsonl");

    // MISS path: the outcome is computed, stored, and written to an artifact.
    let outcome = compute_outcome(&key, &digest);
    let mut store = match CacheStore::open(&log_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("error: open cache {log_path:?}: {e}");
            return 1;
        }
    };
    if let Err(e) = store.insert(&key, outcome.clone()) {
        eprintln!("error: cache insert: {e}");
        return 1;
    }
    let p_miss = out_dir.join("cube-computed.v82");
    let fp_computed = match write_outcome_artifact(
        &p_miss, &candidate_id, &action_id, &simulator_hash, &data_hash, &digest, &outcome,
    ) {
        Ok(fp) => fp,
        Err(e) => {
            eprintln!("error: write computed artifact: {e}");
            return 1;
        }
    };

    // HIT path: a fresh store over the same log — what a second request in a
    // fresh process would do — retrieves the outcome instead of recomputing.
    let store_hit = match CacheStore::open(&log_path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("error: reopen cache {log_path:?}: {e}");
            return 1;
        }
    };
    let outcome_hit = match store_hit.get(&key) {
        Some(v) => v.clone(),
        None => {
            eprintln!("error: cache hit missed after insert (key {key})");
            return 1;
        }
    };
    let p_hit = out_dir.join("cube-cached.v82");
    let fp_cached = match write_outcome_artifact(
        &p_hit, &candidate_id, &action_id, &simulator_hash, &data_hash, &digest, &outcome_hit,
    ) {
        Ok(fp) => fp,
        Err(e) => {
            eprintln!("error: write cached artifact: {e}");
            return 1;
        }
    };

    println!("cache-check: key={key}");
    println!("cache-check: digest={digest}");
    println!("cache-check: computed artifact fingerprint={fp_computed}");
    println!("cache-check: cached   artifact fingerprint={fp_cached}");
    if fp_computed == fp_cached {
        println!("cache-check: PASS — a cache hit does not change the ledger identity");
        0
    } else {
        eprintln!("cache-check: FAIL — a cache hit changed the artifact identity");
        1
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// (a) Same inputs produce the same canonical key and the same content
    /// address; any single input change produces a different key.
    #[test]
    fn canonical_key_is_stable() {
        let k1 = canonical_key("cand-1", "BUY", "sim-abc", "data-def");
        let k2 = canonical_key("cand-1", "BUY", "sim-abc", "data-def");
        assert_eq!(k1, k2);
        assert_eq!(k1, "cand-1|BUY|sim-abc|data-def");

        assert_ne!(k1, canonical_key("cand-2", "BUY", "sim-abc", "data-def"));
        assert_ne!(k1, canonical_key("cand-1", "SELL", "sim-abc", "data-def"));
        assert_ne!(k1, canonical_key("cand-1", "BUY", "sim-abd", "data-def"));
        assert_ne!(k1, canonical_key("cand-1", "BUY", "sim-abc", "data-dee"));

        let d1 = key_digest(&k1);
        let d2 = key_digest(&k2);
        assert_eq!(d1, d2);
        assert_eq!(d1.len(), 40, "SHA-1 hex is 40 chars");
        assert_eq!(d1, key_digest("cand-1|BUY|sim-abc|data-def"));
    }

    /// (b) A miss (computed outcome) and a hit (outcome read back from the
    /// store) write byte-identical artifacts with identical fingerprints.
    #[test]
    fn hit_and_miss_write_byte_identical_artifacts() {
        let dir = std::env::temp_dir();
        let p_miss = dir.join("v82-cache-miss.v82");
        let p_hit = dir.join("v82-cache-hit.v82");
        let (cid, aid, sh, dh) = ("cand-1", "BUY", "sim-abc", "data-def");
        let key = canonical_key(cid, aid, sh, dh);
        let digest = key_digest(&key);

        // Miss: compute the outcome and write it.
        let outcome = compute_outcome(&key, &digest);
        let fp_miss = write_outcome_artifact(&p_miss, cid, aid, sh, dh, &digest, &outcome).unwrap();

        // Hit: store the outcome, then retrieve it from the cache and write.
        let mut store = CacheStore::new();
        store.insert(&key, outcome.clone()).unwrap();
        let outcome_cached = store.get(&key).unwrap().clone();
        assert_eq!(outcome_cached, outcome);
        let fp_hit = write_outcome_artifact(&p_hit, cid, aid, sh, dh, &digest, &outcome_cached).unwrap();

        assert_eq!(fp_miss, fp_hit, "hit and miss must share the artifact fingerprint");
        let b_miss = std::fs::read(&p_miss).unwrap();
        let b_hit = std::fs::read(&p_hit).unwrap();
        assert_eq!(b_miss, b_hit, "hit and miss must write byte-identical artifacts");
        std::fs::remove_file(&p_miss).ok();
        std::fs::remove_file(&p_hit).ok();
    }

    /// (c) A different outcome key is a different cache entry: different
    /// content address, distinct map slot, correct per-key retrieval.
    #[test]
    fn different_outcome_key_is_a_different_entry() {
        let mut store = CacheStore::new();
        let k1 = canonical_key("cand-1", "BUY", "sim-a", "data-a");
        let k2 = canonical_key("cand-1", "SELL", "sim-a", "data-a");
        assert_ne!(k1, k2);
        assert_ne!(key_digest(&k1), key_digest(&k2));

        store.insert(&k1, serde_json::json!({"net_pnl_bps": 100})).unwrap();
        store.insert(&k2, serde_json::json!({"net_pnl_bps": -50})).unwrap();

        assert_eq!(store.len(), 2);
        assert_eq!(store.get(&k1).unwrap()["net_pnl_bps"], 100);
        assert_eq!(store.get(&k2).unwrap()["net_pnl_bps"], -50);
    }

    /// The JSONL log persists entries: a fresh store over the same path is a
    /// hit for a key only ever inserted by another store instance.
    #[test]
    fn jsonl_store_round_trips_across_reopen() {
        let dir = std::env::temp_dir();
        let log = dir.join("v82-cache-store.jsonl");
        std::fs::remove_file(&log).ok();
        let key = canonical_key("cand-9", "HOLD", "sim-x", "data-y");
        {
            let mut store = CacheStore::open(&log).unwrap();
            store.insert(&key, serde_json::json!({"net_pnl_bps": 7})).unwrap();
            assert!(store.get(&key).is_some());
        }
        let store2 = CacheStore::open(&log).unwrap();
        assert_eq!(store2.get(&key).unwrap()["net_pnl_bps"], 7);
        std::fs::remove_file(&log).ok();
    }
}
