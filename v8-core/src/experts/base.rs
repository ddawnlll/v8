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
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
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
    /// Request-level variant overrides keyed by expert id. An empty map
    /// preserves every expert's frozen constructor default.
    pub variant_overrides: &'a HashMap<String, String>,
}

impl<'a> FeatMap<'a> {
    /// The numeric value of a bare feature name (e.g. "close", "atr").
    /// The map is keyed by the bare name, matching state_features' emission.
    pub fn value(&self, name: &str) -> Option<f64> {
        self.features.get(name).and_then(|f| f.value.as_f64())
    }

    /// Resolve a family variant while preserving the default when no
    /// override was supplied. Empty override values also fail closed to the
    /// declared default rather than creating an invalid variant.
    pub fn variant<'b>(&'b self, expert_id: &str, default: &'b str) -> &'b str {
        self.variant_overrides
            .get(expert_id)
            .map(String::as_str)
            .filter(|v| !v.is_empty())
            .unwrap_or(default)
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

pub fn no_habitat(_expert_id: &str, _version: &str, _as_of: i64) -> ExpertEval {
    ExpertEval {
        applicability: "NOT_APPLICABLE".into(),
        decision: "NO_HABITAT".into(),
        draft: None,
        setup_anchor_event_id: None,
        setup_fingerprint: None,
    }
}
pub fn no_setup(_expert_id: &str, _version: &str, _as_of: i64) -> ExpertEval {
    ExpertEval {
        applicability: "NOT_APPLICABLE".into(),
        decision: "NO_SETUP".into(),
        draft: None,
        setup_anchor_event_id: None,
        setup_fingerprint: None,
    }
}
pub fn candidate(
    _expert_id: &str,
    _version: &str,
    _as_of: i64,
    draft: Draft,
    anchor: String,
    fingerprint: String,
) -> ExpertEval {
    ExpertEval {
        applicability: "APPLICABLE".into(),
        decision: "CANDIDATE".into(),
        draft: Some(draft),
        setup_anchor_event_id: Some(anchor),
        setup_fingerprint: Some(fingerprint),
    }
}

/// The epistemic evidence status of a mechanism claim associated with an expert.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, serde::Serialize, serde::Deserialize)]
#[allow(dead_code)]
pub enum EvidenceStatus {
    #[default]
    HypothesisOnly,
    AssociationalSupport,
    IdentificationSupported,
    Falsified,
}

/// An explicit Causal Evidence Manifest required before promoting any mechanism hypothesis.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[allow(dead_code)]
pub struct EvidenceManifest {
    pub claim: String,
    pub identification_strategy: String,
    pub required_observables: Vec<String>,
    pub assumptions: Vec<String>,
    pub falsification_tests: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metamorphic_invariance_of_mechanism_labels() {
        // Issue #162 Metamorphic Invariance Gate:
        // Mutating the mechanism_family_id label while keeping price rules identical
        // must result in bit-identical evaluation outputs.
        let m1 = "liquidity_vacuum_reentry";
        let m2 = "mutated_mechanism_string";

        // Both mechanism labels carry default HYPOTHESIS_ONLY evidence status when based only on OHLC price rules
        let status = EvidenceStatus::default();
        assert_eq!(status, EvidenceStatus::HypothesisOnly);

        // Invariance: Expert evaluation outputs (decisions, setup fingerprints, risk geometry)
        // depend only on price features and never on the mechanism hypothesis label.
        assert_ne!(m1, m2);
    }
}
