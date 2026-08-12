//! ExpertPlane shared surface (COMPUTE_CORE_SPEC §6; EXPERT_PROTOCOL §2-3).
//! One behaviour family per module mirrors D-033; this module holds the
//! draft machinery every evaluate() port shares: the per-bar feature view,
//! the D-026 setup-anchor finder, the risk_geometry builder, and the
//! ExpertEval constructors. Values are the parity target; identities are
//! V8.2-encoded (D-079).

use std::collections::HashMap;

use crate::simulator::Draft;
use crate::state::{Feature, HistBar};

/// One per-bar evaluation, mirroring `ExpertEvaluation`.
#[derive(Debug, Clone)]
pub struct ExpertEval {
    pub applicability: String, // APPLICABLE | NOT_APPLICABLE
    pub decision: String,      // CANDIDATE | NO_SETUP | NO_HABITAT
    pub draft: Option<Draft>,
    /// D-026 setup anchor (event id) — part of the candidate identity.
    pub setup_anchor_event_id: Option<String>,
    /// The Python setup_fingerprint string (value parity target).
    pub setup_fingerprint: Option<String>,
}

/// The per-bar feature view the experts read (the state's feature dict).
pub struct FeatMap<'a> {
    pub features: &'a HashMap<String, Feature>,
    pub history: Vec<HistBar>,
    pub as_of: i64,
    /// Request symbol (the Python `state.universe[0]` read); the fingerprint
    /// prefix. The ported pilots hardcoded "SOLUSDT" here — that broke value
    /// parity on any non-SOLUSDT tape (issue #101); the loop now passes the
    /// request symbol through.
    pub symbol: &'a str,
}

impl<'a> FeatMap<'a> {
    /// The numeric value of a bare feature name (e.g. "close", "atr").
    /// The map is keyed by the bare name, matching state_features' emission.
    pub fn value(&self, name: &str) -> Option<f64> {
        self.features.get(name).and_then(|f| f.value.as_f64())
    }
}

/// D-026 anchor: event_id of the first closed bar of the current consecutive
/// run in which `pred` holds (newest false bar + 1, bounded to the window's
/// oldest; newest-bar fallback).
pub fn find_setup_anchor(hist: &[HistBar], pred: &dyn Fn(usize, &HistBar) -> bool) -> String {
    if hist.is_empty() {
        panic!("setup anchor requires non-empty history");
    }
    let mut newest_false = -1i64;
    for i in (0..hist.len()).rev() {
        if !pred(i, &hist[i]) {
            newest_false = i as i64;
            break;
        }
    }
    let mut start = newest_false + 1;
    if start == hist.len() as i64 {
        start = hist.len() as i64 - 1;
    }
    hist[start as usize].event_id.clone()
}

/// Python-style `f"{v:.6f}"` — the setup_fingerprint's fixed-6 formatting.
#[allow(dead_code)]
pub fn f6(v: f64) -> String {
    // Python's `:.6f` rounds half-even; Rust `{:.6}` also rounds half-even on
    // the correctly-rounded decimal expansion, so the digits agree.
    format!("{v:.6}")
}

pub fn geom(entries: Vec<(&str, serde_json::Value)>) -> serde_json::Map<String, serde_json::Value> {
    let mut m = serde_json::Map::new();
    for (k, v) in entries {
        m.insert(k.to_string(), v);
    }
    m
}

pub fn no_habitat(_expert_id: &str, _version: &str, as_of: i64) -> ExpertEval {
    ExpertEval { applicability: "NOT_APPLICABLE".into(), decision: "NO_HABITAT".into(),
                 draft: None, setup_anchor_event_id: None, setup_fingerprint: None }
}
pub fn no_setup(_expert_id: &str, _version: &str, as_of: i64) -> ExpertEval {
    ExpertEval { applicability: "NOT_APPLICABLE".into(), decision: "NO_SETUP".into(),
                 draft: None, setup_anchor_event_id: None, setup_fingerprint: None }
}
pub fn candidate(_expert_id: &str, _version: &str, _as_of: i64, draft: Draft,
                  anchor: String, fingerprint: String) -> ExpertEval {
    ExpertEval { applicability: "APPLICABLE".into(), decision: "CANDIDATE".into(),
                 draft: Some(draft), setup_anchor_event_id: Some(anchor),
                 setup_fingerprint: Some(fingerprint) }
}
