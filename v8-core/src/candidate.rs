//! CandidateBuffer, lifecycle transitions, ExposureBook, RiskGate
//! (CANDIDATE_LIFECYCLE_SPEC §1-6; COMPUTE_CORE_SPEC §4).
//!
//! The candidate machinery of the compute plane, mirroring
//! `src/v8/{lifecycle,risk}.py`. Identities (episode_key, candidate_id,
//! geometry_version, event_hash) are V8.2 bit-encoded (D-079) and are
//! excluded from the value-level parity comparison (PARITY_AND_IDENTITY_SPEC
//! §3); the VALUE fields (direction, reason_code, endpoint, net_r, ...) are
//! the parity target.

// The candidate machinery is the S4 evaluate-loop substrate; until the loop
// subcommand is wired it is exercised only by its unit tests.
#![allow(dead_code)]

use std::collections::{HashMap, HashSet};

use crate::hash::Canon;

pub const TERMINAL: [&str; 6] = [
    "REJECTED",
    "EXPIRED",
    "INVALIDATED",
    "CANCELLED",
    "CLOSED",
    "ARCHIVED",
];

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
}

impl CandidateRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn current(&self, cid: &str) -> Option<&str> {
        self.current.get(cid).map(|s| s.as_str())
    }

    pub fn is_duplicate(&self, key: &str) -> bool {
        self.detected.contains(key)
    }

    /// Apply one transition, mirroring `CandidateRegistry.apply`. Returns the
    /// (event_hash, sequence, event_id) for the ledger record.
    pub fn apply(
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
        Ok((event_hash, seq, format!("{cid}:{seq}")))
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
    pub fn is_active(&self, instrument: &str, direction: &str) -> bool {
        self.active
            .contains(&(instrument.to_string(), direction.to_string()))
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

/// D-024 mechanical tradability mask (src/v8/risk.py `tradability_mask_veto`).
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
