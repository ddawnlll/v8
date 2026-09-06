//! CandidateBuffer, lifecycle transitions, ExposureBook, RiskGate
//! (CANDIDATE_LIFECYCLE_SPEC §1-6; COMPUTE_CORE_SPEC §4).
//!
//! The candidate machinery of the compute plane, mirroring
//! `src/v8/{lifecycle,risk}.py`. Identities (episode_key, candidate_id,
//! geometry_version, event_hash) are V8.2 bit-encoded (D-079) and are
//! excluded from the value-level parity comparison (PARITY_AND_IDENTITY_SPEC
//! §3); the VALUE fields (direction, reason_code, endpoint, net_r, ...) are
//! the parity target.

// Candidate lifecycle and risk APIs are shared by the S4 evaluate loop and
// reconciliation paths; some fields remain part of the contract projection.
#![allow(dead_code)]

use std::collections::{HashMap, HashSet};
use std::io::{BufRead, Write};

use crate::hash::Canon;

/// The durable, replayable portion of a candidate lifecycle event.
///
/// Execution-specific fields are intentionally absent: this record can prove
/// only the lifecycle transition observed by the compute plane. In particular,
/// counterfactual outcomes never create `EXECUTED` or `CLOSED` transitions.
#[derive(Clone, Debug, Eq, PartialEq, serde::Deserialize, serde::Serialize)]
pub struct TransitionRecord {
    pub candidate_id: String,
    pub sequence: i64,
    pub from_state: Option<String>,
    pub to_state: String,
    pub reason_code: String,
    pub knowledge_time: i64,
    pub event_hash: String,
    pub event_id: String,
}

impl TransitionRecord {
    fn order_key(&self) -> (i64, i64) {
        (self.knowledge_time, self.sequence)
    }
}

/// Strongly-typed candidate lifecycle state (Issue #208).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Deserialize, serde::Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CandidateState {
    Detected,
    Pending,
    Triggered,
    Accepted,
    OrderSubmitted,
    Executed,
    Rejected,
    Expired,
    Invalidated,
    Cancelled,
    Closed,
    Archived,
}

impl CandidateState {
    pub fn as_str(&self) -> &'static str {
        match self {
            CandidateState::Detected => "DETECTED",
            CandidateState::Pending => "PENDING",
            CandidateState::Triggered => "TRIGGERED",
            CandidateState::Accepted => "ACCEPTED",
            CandidateState::OrderSubmitted => "ORDER_SUBMITTED",
            CandidateState::Executed => "EXECUTED",
            CandidateState::Rejected => "REJECTED",
            CandidateState::Expired => "EXPIRED",
            CandidateState::Invalidated => "INVALIDATED",
            CandidateState::Cancelled => "CANCELLED",
            CandidateState::Closed => "CLOSED",
            CandidateState::Archived => "ARCHIVED",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "DETECTED" => Some(CandidateState::Detected),
            "PENDING" => Some(CandidateState::Pending),
            "TRIGGERED" => Some(CandidateState::Triggered),
            "ACCEPTED" => Some(CandidateState::Accepted),
            "ORDER_SUBMITTED" => Some(CandidateState::OrderSubmitted),
            "EXECUTED" => Some(CandidateState::Executed),
            "REJECTED" => Some(CandidateState::Rejected),
            "EXPIRED" => Some(CandidateState::Expired),
            "INVALIDATED" => Some(CandidateState::Invalidated),
            "CANCELLED" => Some(CandidateState::Cancelled),
            "CLOSED" => Some(CandidateState::Closed),
            "ARCHIVED" => Some(CandidateState::Archived),
            _ => None,
        }
    }

    pub fn is_terminal(&self) -> bool {
        matches!(
            self,
            CandidateState::Rejected
                | CandidateState::Expired
                | CandidateState::Invalidated
                | CandidateState::Cancelled
                | CandidateState::Closed
                | CandidateState::Archived
        )
    }

    pub fn can_transition_to(&self, to: CandidateState) -> bool {
        legal_typed(Some(*self), to)
    }
}

pub const TERMINAL: [&str; 6] = [
    "REJECTED",
    "EXPIRED",
    "INVALIDATED",
    "CANCELLED",
    "CLOSED",
    "ARCHIVED",
];

/// Legal transitions with strongly-typed states (Issue #208).
pub fn legal_typed(from: Option<CandidateState>, to: CandidateState) -> bool {
    matches!(
        (from, to),
        (None, CandidateState::Detected)
            | (Some(CandidateState::Detected), CandidateState::Pending)
            | (Some(CandidateState::Detected), CandidateState::Rejected)
            | (Some(CandidateState::Pending), CandidateState::Triggered)
            | (Some(CandidateState::Pending), CandidateState::Expired)
            | (Some(CandidateState::Pending), CandidateState::Invalidated)
            | (Some(CandidateState::Pending), CandidateState::Rejected)
            | (Some(CandidateState::Triggered), CandidateState::Accepted)
            | (Some(CandidateState::Triggered), CandidateState::Invalidated)
            | (Some(CandidateState::Triggered), CandidateState::Rejected)
            | (Some(CandidateState::Accepted), CandidateState::OrderSubmitted)
            | (Some(CandidateState::Accepted), CandidateState::Rejected)
            | (Some(CandidateState::OrderSubmitted), CandidateState::Executed)
            | (Some(CandidateState::OrderSubmitted), CandidateState::Cancelled)
            | (Some(CandidateState::Executed), CandidateState::Closed)
            | (Some(CandidateState::Invalidated), CandidateState::Archived)
            | (Some(CandidateState::Expired), CandidateState::Archived)
            | (Some(CandidateState::Rejected), CandidateState::Archived)
            | (Some(CandidateState::Cancelled), CandidateState::Archived)
            | (Some(CandidateState::Closed), CandidateState::Archived)
    )
}

/// Legal transitions (CANDIDATE_LIFECYCLE_SPEC §2).
pub fn legal(from: Option<&str>, to: &str) -> bool {
    let edge = (from.unwrap_or(""), to);
    matches!(
        edge,
        ("", "DETECTED")
            | ("DETECTED", "PENDING")
            | ("DETECTED", "REJECTED")
            | ("PENDING", "TRIGGERED")
            | ("PENDING", "EXPIRED")
            | ("PENDING", "INVALIDATED")
            | ("PENDING", "REJECTED")
            | ("TRIGGERED", "ACCEPTED")
            | ("TRIGGERED", "INVALIDATED")
            | ("TRIGGERED", "REJECTED")
            | ("ACCEPTED", "ORDER_SUBMITTED")
            | ("ACCEPTED", "REJECTED")
            | ("ORDER_SUBMITTED", "EXECUTED")
            | ("ORDER_SUBMITTED", "CANCELLED")
            | ("EXECUTED", "CLOSED")
            | ("INVALIDATED", "ARCHIVED")
            | ("EXPIRED", "ARCHIVED")
            | ("REJECTED", "ARCHIVED")
            | ("CANCELLED", "ARCHIVED")
            | ("CLOSED", "ARCHIVED")
    )
}

/// `episode_key(expert_id, expert_version, instrument, direction,
/// setup_anchor_event_id, geometry_version)` — anchored to the setup EVIDENCE
/// event, never the decision clock (D-026).
pub fn episode_key(
    expert_id: &str,
    expert_version: &str,
    instrument: &str,
    direction: &str,
    setup_anchor_event_id: &str,
    geometry_version: &str,
) -> String {
    let mut c = Canon::new();
    c.push_list();
    c.push_count(6);
    c.push_str(expert_id);
    c.push_str(expert_version);
    c.push_str(instrument);
    c.push_str(direction);
    c.push_str(setup_anchor_event_id);
    c.push_str(geometry_version);
    c.finish_sha1_hex()
}

/// Structural risk geometry only: `atr_ref`, the `prior_*_ref` invalidation
/// levels and the frozen band refs are data-dependent and excluded from
/// episode identity (src/v8/lab.py `_geometry_version`).
pub const EXCLUDED_GEOMETRY_KEYS: [&str; 7] = [
    "atr_ref",
    "prior_high_ref",
    "prior_low_ref",
    "lower_3sd_ref",
    "upper_3sd_ref",
    "stop_ref",
    "stop_r",
];

pub fn geometry_version(risk_geometry: &serde_json::Map<String, serde_json::Value>) -> String {
    let mut c = Canon::new();
    c.push_map();
    let mut keys: Vec<&String> = risk_geometry
        .keys()
        .filter(|k| !EXCLUDED_GEOMETRY_KEYS.contains(&k.as_str()))
        .collect();
    keys.sort();
    c.push_count(keys.len());
    for k in keys {
        c.push_str(k);
        c.push_value(&risk_geometry[k]);
    }
    c.finish_sha1_hex()
}

/// The append-only candidate registry (projection of the transition log).
#[derive(Debug, Default)]
pub struct CandidateRegistry {
    current: HashMap<String, String>, // candidate_id -> current state
    seq: HashMap<String, i64>,
    detected: HashSet<String>, // ids that reached DETECTED
    records: Vec<TransitionRecord>,
    event_ids: HashSet<String>,
}

impl CandidateRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn is_duplicate(&self, key: &str) -> bool {
        self.detected.contains(key)
    }

    /// Transitions in append order. The caller may persist this immutable log.
    pub fn records(&self) -> &[TransitionRecord] {
        &self.records
    }

    /// Append the lifecycle records as JSONL without rewriting prior records.
    pub fn append_jsonl(&self, path: &std::path::Path) -> Result<(), String> {
        // `CandidateRegistry` is a materialized projection, so a caller may
        // legitimately invoke this method more than once after adding a new
        // transition.  Replaying the whole projection into an append-only file
        // would duplicate every historical event.  Read only the durable event
        // ids and publish the missing suffix.  A malformed existing line is a
        // hard failure rather than a reason to append beside an untrusted log.
        let mut persisted = HashSet::new();
        if path.exists() {
            let file = std::fs::File::open(path)
                .map_err(|e| format!("open existing transition log {path:?}: {e}"))?;
            for (line_no, line) in std::io::BufReader::new(file).lines().enumerate() {
                let line = line.map_err(|e| format!("read transition line {}: {e}", line_no + 1))?;
                if line.trim().is_empty() {
                    continue;
                }
                let record: TransitionRecord = serde_json::from_str(&line)
                    .map_err(|e| format!("parse transition line {}: {e}", line_no + 1))?;
                if !persisted.insert(record.event_id.clone()) {
                    return Err(format!(
                        "duplicate event id already published in transition log: {}",
                        record.event_id
                    ));
                }
            }
        }

        let file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|e| format!("open transition log {path:?}: {e}"))?;
        let mut out = std::io::BufWriter::new(file);
        for record in &self.records {
            if persisted.contains(&record.event_id) {
                continue;
            }
            serde_json::to_writer(&mut out, record).map_err(|e| e.to_string())?;
            out.write_all(b"\n").map_err(|e| e.to_string())?;
            persisted.insert(record.event_id.clone());
        }
        out.flush().map_err(|e| e.to_string())?;
        out.get_ref()
            .sync_data()
            .map_err(|e| format!("sync transition log {path:?}: {e}"))
    }

    /// Read a JSONL transition log and rebuild its materialized projection.
    pub fn replay_jsonl(path: &std::path::Path) -> Result<Self, String> {
        let file =
            std::fs::File::open(path).map_err(|e| format!("open transition log {path:?}: {e}"))?;
        let mut records = Vec::new();
        for (line_no, line) in std::io::BufReader::new(file).lines().enumerate() {
            let line = line.map_err(|e| format!("read transition line {}: {e}", line_no + 1))?;
            if line.trim().is_empty() {
                continue;
            }
            records.push(
                serde_json::from_str(&line)
                    .map_err(|e| format!("parse transition line {}: {e}", line_no + 1))?,
            );
        }
        Self::replay(records)
    }

    /// Rebuild the projection from a durable transition log.
    ///
    /// Records are ordered by `(knowledge_time, sequence)` as required by the
    /// lifecycle contract. Duplicate event IDs are idempotently ignored; a
    /// conflicting or malformed record fails closed.
    pub fn replay<I>(records: I) -> Result<Self, String>
    where
        I: IntoIterator<Item = TransitionRecord>,
    {
        let mut ordered: Vec<_> = records.into_iter().collect();
        ordered.sort_by_key(TransitionRecord::order_key);
        let mut registry = Self::new();
        for record in ordered {
            if registry.event_ids.contains(&record.event_id) {
                if registry.records.iter().any(|existing| existing == &record) {
                    continue;
                }
                return Err(format!(
                    "conflicting duplicate transition event: {}",
                    record.event_id
                ));
            }
            let (hash, sequence, event_id) = registry.apply_inner(
                &record.candidate_id,
                record.from_state.as_deref(),
                &record.to_state,
                &record.reason_code,
                record.knowledge_time,
            )?;
            if hash != record.event_hash
                || sequence != record.sequence
                || event_id != record.event_id
            {
                return Err(format!(
                    "transition record does not match canonical event: {}",
                    record.event_id
                ));
            }
        }
        Ok(registry)
    }

    /// Apply one transition, mirroring `CandidateRegistry.apply`. Returns the
    /// (event_hash, sequence, event_id) for the ledger record.
    #[allow(clippy::too_many_arguments)]
    pub fn apply(
        &mut self,
        cid: &str,
        from: Option<&str>,
        to: &str,
        reason: &str,
        knowledge_time: i64,
    ) -> Result<(String, i64, String), String> {
        self.apply_inner(cid, from, to, reason, knowledge_time)
    }

    fn apply_inner(
        &mut self,
        cid: &str,
        from: Option<&str>,
        to: &str,
        reason: &str,
        knowledge_time: i64,
    ) -> Result<(String, i64, String), String> {
        let cur = self.current.get(cid).map(|s| s.as_str());
        if cur != from {
            return Err(format!(
                "illegal transition {from:?}->{to} for {cid}: current is {cur:?}"
            ));
        }
        if !legal(from, to) {
            return Err(format!("illegal transition {from:?}->{to} for {cid}"));
        }
        let seq = self.seq.get(cid).copied().unwrap_or(0) + 1;
        let mut c = Canon::new();
        c.push_list();
        c.push_count(6);
        c.push_str(cid);
        c.push_i64(seq);
        c.push_str(from.unwrap_or(""));
        c.push_str(to);
        c.push_str(reason);
        c.push_i64(knowledge_time);
        let event_hash = c.finish_sha1_hex();
        self.seq.insert(cid.to_string(), seq);
        self.current.insert(cid.to_string(), to.to_string());
        if to == "DETECTED" {
            self.detected.insert(cid.to_string());
        }
        let event_id = format!("{cid}:{seq}");
        self.event_ids.insert(event_id.clone());
        self.records.push(TransitionRecord {
            candidate_id: cid.to_string(),
            sequence: seq,
            from_state: from.map(str::to_owned),
            to_state: to.to_string(),
            reason_code: reason.to_string(),
            knowledge_time,
            event_hash: event_hash.clone(),
            event_id: event_id.clone(),
        });
        Ok((event_hash, seq, event_id))
    }
}

/// One active exposure per (instrument, direction) (rule 16).
#[derive(Debug, Default)]
pub struct ExposureBook {
    active: HashSet<(String, String)>,
}

impl ExposureBook {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn acquire(&mut self, instrument: &str, direction: &str) -> bool {
        self.active
            .insert((instrument.to_string(), direction.to_string()))
    }
    pub fn release(&mut self, instrument: &str, direction: &str) {
        self.active
            .remove(&(instrument.to_string(), direction.to_string()));
    }
}

pub const DEFAULT_CLUSTERS: [(&str, &str); 6] = [
    ("BTCUSDT", "btc"),
    ("ETHUSDT", "btc"),
    ("SOLUSDT", "major"),
    ("BNBUSDT", "major"),
    ("XRPUSDT", "major"),
    ("DOGEUSDT", "major"),
];

/// Deterministic risk admission (D-023; src/v8/risk.py RiskGate).
pub struct RiskGate {
    pub max_heat: f64,
    pub max_cluster_heat: f64,
    pub clusters: Vec<(String, String)>,
    heat: HashMap<String, f64>,
    book: ExposureBook,
}

pub struct RiskVerdict {
    pub ok: bool,
    pub reason_code: Option<String>,
    pub detail: Option<String>,
    pub size: f64,
    pub stop_r: f64,
}

impl RiskGate {
    pub fn new(max_heat: f64, max_cluster_heat: f64, clusters: Vec<(String, String)>) -> Self {
        RiskGate {
            max_heat,
            max_cluster_heat,
            clusters,
            heat: HashMap::new(),
            book: ExposureBook::new(),
        }
    }

    fn cluster_of(&self, instrument: &str) -> String {
        self.clusters
            .iter()
            .find(|(s, _)| s == instrument)
            .map(|(_, c)| c.clone())
            .unwrap_or_else(|| "other".to_string())
    }

    pub fn admit(
        &mut self,
        instrument: &str,
        direction: &str,
        size: f64,
        stop_r: f64,
    ) -> RiskVerdict {
        if !self.book.acquire(instrument, direction) {
            return RiskVerdict {
                ok: false,
                reason_code: Some("EXISTING_EXPOSURE_CONFLICT".into()),
                detail: None,
                size,
                stop_r,
            };
        }
        let heat = size * stop_r;
        let cluster = self.cluster_of(instrument);
        let cluster_heat = self.heat.get(&cluster).copied().unwrap_or(0.0);
        if cluster_heat + heat > self.max_cluster_heat {
            self.book.release(instrument, direction);
            return RiskVerdict {
                ok: false,
                reason_code: Some("PORTFOLIO_HEAT_EXCEEDED".into()),
                detail: Some(format!("cluster:{cluster}")),
                size,
                stop_r,
            };
        }
        let total: f64 = self.heat.values().sum();
        if total + heat > self.max_heat {
            self.book.release(instrument, direction);
            return RiskVerdict {
                ok: false,
                reason_code: Some("PORTFOLIO_HEAT_EXCEEDED".into()),
                detail: Some("total".into()),
                size,
                stop_r,
            };
        }
        *self.heat.entry(cluster).or_insert(0.0) += heat;
        RiskVerdict {
            ok: true,
            reason_code: None,
            detail: None,
            size,
            stop_r,
        }
    }

    pub fn release(&mut self, instrument: &str, direction: &str, size: f64, stop_r: f64) {
        self.book.release(instrument, direction);
        let cluster = self.cluster_of(instrument);
        let heat = size * stop_r;
        let e = self.heat.entry(cluster).or_insert(0.0);
        *e = (*e - heat).max(0.0);
    }
}

pub fn tradability_mask_veto(
    bar: &serde_json::Map<String, serde_json::Value>,
    state_quality: &str,
    entry_fill_time_ns: i64,
    max_bar_range_frac: f64,
    funding_window_bars: i64,
    funding_hours: i64,
    interval_ns: i64,
) -> (bool, Option<String>) {
    let f = |k: &str| bar.get(k).and_then(|v| v.as_f64());
    let high = f("high").unwrap_or(0.0);
    let low = f("low").unwrap_or(0.0);
    let close = f("close").unwrap_or(0.0);
    if close <= 0.0 || (high - low) / close > max_bar_range_frac {
        return (true, Some("BAR_RANGE".into()));
    }
    if state_quality == "DEGRADED" {
        return (true, Some("DEGRADED".into()));
    }
    if funding_hours > 0 && funding_window_bars > 0 && interval_ns > 0 {
        let period = funding_hours * crate::simulator::HOUR_NS;
        let window = funding_window_bars * interval_ns;
        let remainder = entry_fill_time_ns % period;
        if remainder >= period - window {
            return (true, Some("FUNDING_WINDOW".into()));
        }
    }
    (false, None)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn log() -> Vec<TransitionRecord> {
        let mut registry = CandidateRegistry::new();
        registry
            .apply("c-1", None, "DETECTED", "setup_detected", 20)
            .unwrap();
        registry
            .apply(
                "c-1",
                Some("DETECTED"),
                "PENDING",
                "hypothesis_completed",
                30,
            )
            .unwrap();
        registry.records().to_vec()
    }

    #[test]
    fn replay_sorts_ingestion_order_and_reproduces_projection() {
        let records = log();
        let mut shuffled = records.clone();
        shuffled.reverse();
        let replayed = CandidateRegistry::replay(shuffled).unwrap();
        assert_eq!(
            replayed.current.get("c-1").map(String::as_str),
            Some("PENDING")
        );
        assert_eq!(replayed.records(), records.as_slice());
    }

    #[test]
    fn replay_is_idempotent_for_duplicate_event_id() {
        let mut records = log();
        records.push(records[1].clone());
        let replayed = CandidateRegistry::replay(records).unwrap();
        assert_eq!(replayed.records().len(), 2);
        assert_eq!(
            replayed.current.get("c-1").map(String::as_str),
            Some("PENDING")
        );
    }

    #[test]
    fn jsonl_persistence_replays_the_durable_projection() {
        let registry = CandidateRegistry::replay(log()).unwrap();
        let path = std::env::temp_dir().join(format!("v8-lifecycle-{}.jsonl", std::process::id()));
        let _ = std::fs::remove_file(&path);
        registry.append_jsonl(&path).unwrap();
        let replayed = CandidateRegistry::replay_jsonl(&path).unwrap();
        let _ = std::fs::remove_file(&path);
        assert_eq!(
            replayed.current.get("c-1").map(String::as_str),
            Some("PENDING")
        );
        assert_eq!(replayed.records(), registry.records());
    }

    #[test]
    fn replay_rejects_counterfactual_execution_transition() {
        let mut records = log();
        let pending = records.last().unwrap();
        records.push(TransitionRecord {
            candidate_id: "c-1".into(),
            sequence: 3,
            from_state: Some("PENDING".into()),
            to_state: "EXECUTED".into(),
            reason_code: "counterfactual_fill".into(),
            knowledge_time: pending.knowledge_time + 1,
            event_hash: "not-canonical".into(),
            event_id: "c-1:3".into(),
        });
        assert!(CandidateRegistry::replay(records).is_err());
    }
}
