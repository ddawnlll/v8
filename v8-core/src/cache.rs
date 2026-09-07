//! S5 content-addressed DAG cache (issue #107; COMPUTE_CORE_SPEC §8 S5).
//!
//! The missing node is cube level — (candidate_id, action_id, simulator_hash,
//! data_hash) -> outcome. The store is content-addressed: a canonical string
//! key `{cache_version}|{candidate_id}|{action_id}|{simulator_hash}|{data_hash}` is hashed to
//! a SHA-1 content address, and entries are addressable by that digest, never
//! by a run-global id. The gate (COMPUTE_CORE_SPEC §8 S5): a cache hit must
//! never change the ledger identity — a request that hits the cache writes
//! byte-identical artifacts to a request that misses and recomputes.
//! `cache_check` simulates both paths and asserts artifact-fingerprint
//! equality (LEDGER_FORMAT_SPEC §8 test 3). Production storage uses redb's
//! transactional single-table adapter. The legacy JSONL representation is
//! read once and migrated without changing the canonical key or digest.

use std::collections::HashMap;
use std::io;
use std::path::{Path, PathBuf};

use redb::{Database, ReadableTable, ReadableTableMetadata, TableDefinition};
use serde_json::Value;
use sha1::{Digest, Sha1};

use crate::evidence::{self, Artifact, DType};
use crate::hash::HASH_ENCODING;
use crate::simulator::Outcome;

pub fn outcome_to_value(outcome: &Outcome) -> Value {
    serde_json::json!({
        "endpoint": outcome.endpoint,
        "net_r": outcome.net_r,
        "label_status": outcome.label_status,
        "horizon_bars": outcome.horizon_bars,
        "label_available_time": outcome.label_available_time,
        "mae_r": outcome.mae_r,
        "mfe_r": outcome.mfe_r,
        "ambiguous_bars": outcome.ambiguous_bars,
        "entry_price": outcome.entry_price,
        "risk_unit_price": outcome.risk_unit_price,
        "market_move_r": outcome.market_move_r,
        "cost_r": outcome.cost_r,
        "funding_r": outcome.funding_r,
    })
}

pub fn outcome_from_value(value: &Value) -> Result<Outcome, String> {
    let number = |name: &str| {
        value
            .get(name)
            .and_then(Value::as_f64)
            .ok_or_else(|| format!("cache outcome missing numeric field {name}"))
    };
    let integer = |name: &str| {
        value
            .get(name)
            .and_then(Value::as_i64)
            .ok_or_else(|| format!("cache outcome missing integer field {name}"))
    };
    let string = |name: &str| {
        value
            .get(name)
            .and_then(Value::as_str)
            .map(str::to_string)
            .ok_or_else(|| format!("cache outcome missing string field {name}"))
    };
    let intervention_manifest = value
        .get("intervention_manifest")
        .and_then(|v| serde_json::from_value(v.clone()).ok());
    Ok(Outcome {
        endpoint: string("endpoint")?,
        net_r: number("net_r")?,
        label_status: string("label_status")?,
        horizon_bars: integer("horizon_bars")?,
        label_available_time: integer("label_available_time")?,
        mae_r: number("mae_r")?,
        mfe_r: number("mfe_r")?,
        ambiguous_bars: integer("ambiguous_bars")?,
        entry_price: number("entry_price")?,
        risk_unit_price: number("risk_unit_price")?,
        market_move_r: number("market_move_r")?,
        cost_r: number("cost_r")?,
        funding_r: number("funding_r")?,
        intervention_manifest,
    })
}

/// Version of the semantic cube-cache key and serialized outcome contract.
/// Bumping it makes entries from an incompatible implementation unreachable.
pub const CACHE_KEY_VERSION: &str = "cube-cache-v1";

/// The canonical string key of a cube-level node. Same inputs always produce
/// the same key; the whole tuple is one cache entry.
pub fn canonical_key(
    candidate_id: &str,
    action_id: &str,
    simulator_hash: &str,
    data_hash: &str,
) -> String {
    format!("{CACHE_KEY_VERSION}|{candidate_id}|{action_id}|{simulator_hash}|{data_hash}")
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
const CACHE_TABLE: TableDefinition<&str, &[u8]> = TableDefinition::new("cache_entries");

enum CacheBackend {
    Memory(HashMap<String, CacheEntry>),
    Durable(Database),
}

pub struct CacheStore {
    backend: CacheBackend,
}

impl CacheStore {
    pub fn new() -> Self {
        CacheStore {
            backend: CacheBackend::Memory(HashMap::new()),
        }
    }

    /// Open a durable redb store. If `path` is a legacy JSONL file, valid
    /// records are migrated to a sibling `.redb` file and malformed/stale
    /// records are excluded from the cache. The legacy file remains as an
    /// audit source until an operator removes it.
    pub fn open(path: &Path) -> io::Result<Self> {
        let legacy_jsonl = path.exists() && looks_like_jsonl(path)?;
        let db_path = if legacy_jsonl
            || path.extension().and_then(|ext| ext.to_str()) == Some("jsonl")
        {
            path.with_extension("redb")
        } else {
            path.to_path_buf()
        };
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let database = if db_path.exists() {
            Database::open(&db_path).map_err(redb_io_error)?
        } else {
            Database::create(&db_path).map_err(redb_io_error)?
        };
        let store = Self {
            backend: CacheBackend::Durable(database),
        };
        if legacy_jsonl {
            store.migrate_legacy_jsonl(path)?;
        }
        Ok(store)
    }

    /// Insert (or overwrite) the outcome for a canonical key and return its
    /// content address. Durable inserts commit as one redb transaction, so a
    /// partial write is never visible to readers.
    pub fn insert(&mut self, key: &str, outcome: Value) -> io::Result<String> {
        if !key.starts_with(&format!("{CACHE_KEY_VERSION}|")) {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "cache key has unsupported version",
            ));
        }
        let digest = key_digest(key);
        let entry = CacheEntry {
            digest: digest.clone(),
            key: key.to_string(),
            outcome,
        };
        let bytes = serde_json::to_vec(&entry)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        match &mut self.backend {
            CacheBackend::Memory(map) => {
                map.insert(digest.clone(), entry);
            }
            CacheBackend::Durable(database) => {
                let write_txn = database.begin_write().map_err(redb_io_error)?;
                {
                    let mut table = write_txn.open_table(CACHE_TABLE).map_err(redb_io_error)?;
                    table
                        .insert(digest.as_str(), bytes.as_slice())
                        .map_err(redb_io_error)?;
                }
                write_txn.commit().map_err(redb_io_error)?;
            }
        }
        Ok(digest)
    }

    /// Retrieve an owned outcome for a canonical key. Every persisted value is
    /// revalidated against both the requested key and its content address.
    pub fn get(&self, key: &str) -> Option<Value> {
        let digest = key_digest(key);
        match &self.backend {
            CacheBackend::Memory(map) => map
                .get(&digest)
                .and_then(|entry| valid_entry(entry, key, &digest))
                .map(|entry| entry.outcome.clone()),
            CacheBackend::Durable(database) => {
                let read_txn = database.begin_read().ok()?;
                let table = read_txn.open_table(CACHE_TABLE).ok()?;
                let value = table.get(digest.as_str()).ok()??;
                let entry: CacheEntry = serde_json::from_slice(value.value()).ok()?;
                valid_entry(&entry, key, &digest).map(|entry| entry.outcome.clone())
            }
        }
    }

    #[allow(dead_code)] // exercised by unit tests
    pub fn len(&self) -> usize {
        match &self.backend {
            CacheBackend::Memory(map) => map.len(),
            CacheBackend::Durable(database) => database
                .begin_read()
                .ok()
                .and_then(|txn| txn.open_table(CACHE_TABLE).ok())
                .and_then(|table| table.len().ok())
                .and_then(|len| usize::try_from(len).ok())
                .unwrap_or(0),
        }
    }

    /// Compact the durable database without changing cache identity.
    pub fn compact(&mut self) -> io::Result<bool> {
        match &mut self.backend {
            CacheBackend::Memory(_) => Ok(false),
            CacheBackend::Durable(database) => database.compact().map_err(redb_io_error),
        }
    }

    fn migrate_legacy_jsonl(&self, path: &Path) -> io::Result<()> {
        let text = std::fs::read_to_string(path)?;
        for line in text.lines() {
            if line.trim().is_empty() {
                continue;
            }
            let entry: CacheEntry = match serde_json::from_str(line) {
                Ok(entry) => entry,
                Err(_) => continue,
            };
            if valid_entry(&entry, &entry.key, &entry.digest).is_none() {
                continue;
            }
            let bytes = serde_json::to_vec(&entry)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            if let CacheBackend::Durable(database) = &self.backend {
                let write_txn = database.begin_write().map_err(redb_io_error)?;
                {
                    let mut table = write_txn.open_table(CACHE_TABLE).map_err(redb_io_error)?;
                    table
                        .insert(entry.digest.as_str(), bytes.as_slice())
                        .map_err(redb_io_error)?;
                }
                write_txn.commit().map_err(redb_io_error)?;
            }
        }
        Ok(())
    }
}

fn valid_entry<'a>(
    entry: &'a CacheEntry,
    requested_key: &str,
    digest: &str,
) -> Option<&'a CacheEntry> {
    if entry.key != requested_key
        || entry.digest != digest
        || !entry.key.starts_with(&format!("{CACHE_KEY_VERSION}|"))
        || key_digest(&entry.key) != entry.digest
    {
        return None;
    }
    Some(entry)
}

fn looks_like_jsonl(path: &Path) -> io::Result<bool> {
    let bytes = std::fs::read(path)?;
    Ok(bytes
        .iter()
        .copied()
        .find(|byte| !byte.is_ascii_whitespace())
        == Some(b'{'))
}

fn redb_io_error(error: impl std::fmt::Display) -> io::Error {
    io::Error::new(io::ErrorKind::Other, error.to_string())
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
        .and_then(|b| {
            serde_json::from_slice(&b).map_err(|e| format!("cannot parse request {path}: {e}"))
        }) {
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
            .or_else(|| {
                req.get("manifest")
                    .and_then(|m| m.get(name))
                    .and_then(Value::as_str)
            })
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
    let log_path = out_dir.join("cache.redb");

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
        &p_miss,
        &candidate_id,
        &action_id,
        &simulator_hash,
        &data_hash,
        &digest,
        &outcome,
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
        &p_hit,
        &candidate_id,
        &action_id,
        &simulator_hash,
        &data_hash,
        &digest,
        &outcome_hit,
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
        assert_eq!(k1, "cube-cache-v1|cand-1|BUY|sim-abc|data-def");

        assert_ne!(k1, canonical_key("cand-2", "BUY", "sim-abc", "data-def"));
        assert_ne!(k1, canonical_key("cand-1", "SELL", "sim-abc", "data-def"));
        assert_ne!(k1, canonical_key("cand-1", "BUY", "sim-abd", "data-def"));
        assert_ne!(k1, canonical_key("cand-1", "BUY", "sim-abc", "data-dee"));

        let d1 = key_digest(&k1);
        let d2 = key_digest(&k2);
        assert_eq!(d1, d2);
        assert_eq!(d1.len(), 40, "SHA-1 hex is 40 chars");
        assert_eq!(d1, key_digest(&k1));
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
        let fp_hit =
            write_outcome_artifact(&p_hit, cid, aid, sh, dh, &digest, &outcome_cached).unwrap();

        assert_eq!(
            fp_miss, fp_hit,
            "hit and miss must share the artifact fingerprint"
        );
        let b_miss = std::fs::read(&p_miss).unwrap();
        let b_hit = std::fs::read(&p_hit).unwrap();
        assert_eq!(
            b_miss, b_hit,
            "hit and miss must write byte-identical artifacts"
        );
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

        store
            .insert(&k1, serde_json::json!({"net_pnl_bps": 100}))
            .unwrap();
        store
            .insert(&k2, serde_json::json!({"net_pnl_bps": -50}))
            .unwrap();

        assert_eq!(store.len(), 2);
        assert_eq!(store.get(&k1).unwrap()["net_pnl_bps"], 100);
        assert_eq!(store.get(&k2).unwrap()["net_pnl_bps"], -50);
    }

    /// The durable store persists entries: a fresh store over the same path is a
    /// hit for a key only ever inserted by another store instance.
    #[test]
    fn durable_store_round_trips_across_reopen() {
        let dir = std::env::temp_dir();
        let log = dir.join(format!("v82-cache-store-{}.redb", std::process::id()));
        std::fs::remove_file(&log).ok();
        let key = canonical_key("cand-9", "HOLD", "sim-x", "data-y");
        {
            let mut store = CacheStore::open(&log).unwrap();
            store
                .insert(&key, serde_json::json!({"net_pnl_bps": 7}))
                .unwrap();
            assert!(store.get(&key).is_some());
        }
        let store2 = CacheStore::open(&log).unwrap();
        assert_eq!(store2.get(&key).unwrap()["net_pnl_bps"], 7);
        std::fs::remove_file(&log).ok();
    }

    #[test]
    fn stale_or_corrupt_entries_are_not_cache_hits() {
        let dir = std::env::temp_dir();
        let log = dir.join(format!("v82-cache-stale-{}.jsonl", std::process::id()));
        let migrated = log.with_extension("redb");
        std::fs::remove_file(&log).ok();
        std::fs::remove_file(&migrated).ok();
        let key = canonical_key("cand-stale", "BUY", "sim-v1", "data-v1");
        let old_key = "cube-cache-v0|cand-stale|BUY|sim-v1|data-v1";
        let stale = serde_json::json!({
            "digest": key_digest(old_key),
            "key": old_key,
            "outcome": {"net_pnl_bps": 99}
        });
        let corrupt = serde_json::json!({
            "digest": key_digest("cube-cache-v1|different|BUY|sim-v1|data-v1"),
            "key": key,
            "outcome": {"net_pnl_bps": 88}
        });
        std::fs::write(&log, format!("{}\n{}\n", stale, corrupt)).unwrap();
        let store = CacheStore::open(&log).unwrap();
        assert!(store.get(&key).is_none());
        assert_eq!(store.len(), 0);
        std::fs::remove_file(&log).ok();
        std::fs::remove_file(&migrated).ok();
    }

    #[test]
    fn cache_key_version_changes_content_address() {
        let current = canonical_key("cand", "BUY", "sim", "data");
        let old = "cube-cache-v0|cand|BUY|sim|data";
        assert_ne!(current, old);
        assert_ne!(key_digest(&current), key_digest(old));
    }

    #[test]
    fn typed_outcome_round_trips_all_semantic_fields() {
        let source = Outcome {
            endpoint: "TARGET".into(),
            net_r: -0.125,
            label_status: "MATURE".into(),
            horizon_bars: 3,
            label_available_time: 123,
            mae_r: 0.5,
            mfe_r: 1.25,
            ambiguous_bars: 1,
            entry_price: 100.0,
            risk_unit_price: 2.0,
            market_move_r: 0.75,
            cost_r: 0.07,
            funding_r: -0.01,
            intervention_manifest: None,
        };
        let value = outcome_to_value(&source);
        let restored = outcome_from_value(&value).unwrap();
        assert_eq!(restored.endpoint, source.endpoint);
        assert_eq!(restored.label_status, source.label_status);
        assert_eq!(restored.horizon_bars, source.horizon_bars);
        assert_eq!(restored.net_r.to_bits(), source.net_r.to_bits());
        assert_eq!(restored.mfe_r.to_bits(), source.mfe_r.to_bits());
        assert_eq!(restored.funding_r.to_bits(), source.funding_r.to_bits());
    }
}
