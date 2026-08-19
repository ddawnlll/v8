//! Simulation ontology (COMPUTE_CORE_SPEC §4; SIMULATION_TRUTH_SPEC).
//!
//! The ontology types the replay path speaks: `Draft` (the frozen Candidate
//! geometry), `Outcome` (the counterfactual result), `FillPolicy`, and the
//! request-level `SimulatorParams`, plus the geometry validators `risk_unit`
//! and `validate_geometry`. None of these depends on a backend (D-096): the
//! kernel boundary that consumes them lives in `crate::backend` (Backend-0
//! scalar reference in `backend::scalar`, and the CPU/GPU backends in
//! `backend::cpu`).
//!
//! The scalar replay kernel itself moved to `backend::scalar::ScalarKernel`
//! byte-for-byte (D-096 Backend-0). Its semantics remain:
//!
//! - R-multiples only; one R = the geometry's declared `risk_unit`
//!   (`atr_ref`, else `entry * risk_frac`); a stop-out is exactly -1R - cost.
//! - FILL_AT_BAR_CLOSE entry at the first bar's close; FILL_AT_LIMIT barrier
//!   entry (fill = the limit exactly, never-filling orders never enter).
//! - The entry bar is inspected for a FILL only, never for exits.
//! - Funding settles BEFORE any order/exit event (`SETTLEMENT_BEFORE_ORDERS`).
//! - STOP_FIRST on same-bar ambiguity with `ambiguous_bars` counted; gap-through
//!   exits fill at the opening price (SIMULATION_TRUTH_SPEC §6), symmetric at
//!   the declared barrier (issue #71); THESIS_INVALIDATED / TIME_EXIT / EXPIRY
//!   exit at bar close; `mae_r`/`mfe_r` are recorded BEFORE the exit decision.
//! - `net_r = realized_r + remaining*(sign*(exit-entry)/unit) - cost_r -
//!   funding_paid_r`; cost resolves through one `cost_r(entry, unit)`.

use serde_json::Value;

/// The frozen Candidate geometry the kernel replays.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Draft {
    pub direction: String,
    #[allow(dead_code)] // placeholder id in sim.run's cf: prefix (oracle parity)
    pub birth_time: i64,
    pub risk_geometry: serde_json::Map<String, Value>,
}

/// One deterministic pyramiding instruction.  Pyramiding is deliberately a
/// narrow replay primitive rather than a second position model: exactly one
/// additional unit is bought/sold at the close of the first non-terminal bar
/// whose favorable excursion reaches `at_mfe_r`.  The initial target remains
/// in force and the protective stop becomes the midpoint of the two entries.
///
/// The JSON form is `pyramid_add_rules: [{"at_mfe_r": 1.0}]`.  Keeping the
/// outer array makes the geometry forward-compatible with a later, separately
/// certified multi-add action surface without accepting ambiguous rules today.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PyramidAddRule {
    pub at_mfe_r: f64,
}

impl Draft {
    pub fn geom_f64(&self, key: &str) -> Option<f64> {
        self.risk_geometry.get(key).and_then(|v| v.as_f64())
    }
    pub fn geom_i64(&self, key: &str) -> Option<i64> {
        self.risk_geometry.get(key).and_then(|v| v.as_i64())
    }
    pub fn has_geom(&self, key: &str) -> bool {
        self.risk_geometry.contains_key(key)
    }
}

pub const HOUR_NS: i64 = 3_600_000_000_000;

/// Price distance of one R (mirror of `simulator.risk_unit`).
pub fn risk_unit(draft: &Draft, entry_price: f64) -> Result<f64, String> {
    if let Some(atr) = draft.geom_f64("atr_ref") {
        if !(atr > 0.0) {
            return Err(format!(
                "risk_unit must be > 0 (got {atr:?}); geometry declares neither a positive atr_ref nor a positive risk_frac"));
        }
        return Ok(atr);
    }
    if draft.has_geom("risk_frac") {
        let frac = draft.geom_f64("risk_frac").ok_or_else(|| {
            format!(
                "risk_frac must be numeric ({:?})",
                draft.risk_geometry.get("risk_frac")
            )
        })?;
        let unit = entry_price * frac;
        if !(unit > 0.0) {
            return Err(format!(
                "risk_unit must be > 0 (got {unit:?}); geometry declares neither a positive atr_ref nor a positive risk_frac"));
        }
        return Ok(unit);
    }
    Err(format!(
        "risk_unit: geometry declares neither atr_ref nor risk_frac ({:?})",
        draft.risk_geometry
    ))
}

/// Fail closed on a geometry that cannot produce a meaningful outcome
/// (mirror of `simulator.validate_geometry`, issue #70). A non-positive
/// `target_r` puts the target on the losing side and the kernel would book
/// the loss as a TARGET endpoint (a win in any downstream hit-rate /
/// profit-factor statistic); a non-positive `stop_r` is not a position; an
/// `expiry_bars` below 1 is not a horizon.
///
/// A key that is present but not a number fails closed too: `geom_f64`
/// returns `None` for a string value, and the replay path defaults a missing
/// `target_r` to 0.0 — target = entry — which books the first bar as a TARGET
/// exit. The oracle's `float(target_r)` raises for the same input; this guard
/// mirrors that.
pub fn validate_geometry(draft: &Draft) -> Result<(), String> {
    let geom = &draft.risk_geometry;
    if let Some(v) = geom.get("target_r") {
        match v.as_f64() {
            Some(t) if t > 0.0 => {}
            Some(t) => return Err(format!("risk_geometry target_r must be > 0 (got {t:?})")),
            None => {
                return Err(format!(
                    "risk_geometry target_r must be numeric (got {v:?})"
                ))
            }
        }
    }
    if let Some(v) = geom.get("stop_r") {
        match v.as_f64() {
            Some(s) if s > 0.0 => {}
            Some(s) => return Err(format!("risk_geometry stop_r must be > 0 (got {s:?})")),
            None => return Err(format!("risk_geometry stop_r must be numeric (got {v:?})")),
        }
    }
    if let Some(v) = geom.get("expiry_bars") {
        match v.as_i64() {
            Some(e) if e >= 1 => {}
            Some(e) => {
                return Err(format!(
                    "risk_geometry expiry_bars must be >= 1 (got {e:?})"
                ))
            }
            None => {
                return Err(format!(
                    "risk_geometry expiry_bars must be an integer (got {v:?})"
                ))
            }
        }
    }
    let _ = pyramid_add_rule(draft)?;
    Ok(())
}

/// Decode the only currently certified pyramiding grammar.  Invalid or
/// partially specified instructions fail before a replay starts; accepting an
/// unknown instruction would silently change the size/risk ledger.
pub fn pyramid_add_rule(draft: &Draft) -> Result<Option<PyramidAddRule>, String> {
    let Some(value) = draft.risk_geometry.get("pyramid_add_rules") else {
        return Ok(None);
    };
    let rules = value.as_array().ok_or_else(|| {
        "pyramid_add_rules must be an array with exactly one {at_mfe_r} rule".to_string()
    })?;
    if rules.len() != 1 {
        return Err("pyramid_add_rules currently supports exactly one add rule".into());
    }
    let rule = rules[0].as_object().ok_or_else(|| {
        "pyramid_add_rules[0] must be an object with numeric at_mfe_r".to_string()
    })?;
    if rule.len() != 1 || !rule.contains_key("at_mfe_r") {
        return Err("pyramid_add_rules[0] must contain only at_mfe_r".into());
    }
    let at_mfe_r = rule["at_mfe_r"]
        .as_f64()
        .ok_or_else(|| "pyramid_add_rules[0].at_mfe_r must be numeric".to_string())?;
    if !(at_mfe_r > 0.0) || !at_mfe_r.is_finite() {
        return Err(format!(
            "pyramid_add_rules[0].at_mfe_r must be finite and > 0 (got {at_mfe_r:?})"
        ));
    }
    for incompatible in [
        "breakeven_roll_at_mfe_r",
        "trail_stop_atr",
        "scale_out_ratio",
    ] {
        if draft.has_geom(incompatible) {
            return Err(format!(
                "pyramid_add_rules cannot be combined with {incompatible}; combined position management is not certified"
            ));
        }
    }
    Ok(Some(PyramidAddRule { at_mfe_r }))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FillPolicy {
    BarClose,
    Limit,
}

/// Explicit semantic intervention manifest bound to counterfactual artifacts (D-105, Issue #161).
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct InterventionManifest {
    /// Factual rejection or invalidation reason (e.g. CAPACITY_REJECTED, THESIS_INVALIDATED)
    pub why_not_traded: String,
    /// Exact rule or gate overridden (e.g. REMOVE_CAPACITY_CONSTRAINT, OVERRIDE_THESIS_INVALIDATION)
    pub counterfactual_intervention: String,
    /// Invariants held fixed (market path, execution rules, risk geometry)
    pub what_was_held_fixed: Vec<String>,
}

impl InterventionManifest {
    #[allow(dead_code)]
    pub fn new(
        why_not_traded: impl Into<String>,
        counterfactual_intervention: impl Into<String>,
        what_was_held_fixed: Vec<String>,
    ) -> Self {
        Self {
            why_not_traded: why_not_traded.into(),
            counterfactual_intervention: counterfactual_intervention.into(),
            what_was_held_fixed,
        }
    }
}

/// The counterfactual outcome (mirror of `schema.CounterfactualOutcome`, hash
/// fields excluded — identities are V8.2-encoded elsewhere).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Outcome {
    pub endpoint: String,
    pub net_r: f64,
    pub label_status: String,
    pub horizon_bars: i64,
    pub label_available_time: i64,
    pub mae_r: f64,
    pub mfe_r: f64,
    pub ambiguous_bars: i64,
    pub entry_price: f64,
    pub risk_unit_price: f64,
    pub market_move_r: f64,
    /// The round-trip cost charged (R units) — the S6 phase-1 join carries it
    /// (the oracle's cube rows have cost_r/funding_r; the reconciliation
    /// surface deliberately does not).
    pub cost_r: f64,
    /// Cumulative funding paid (R units).
    pub funding_r: f64,
    /// Semantic causal intervention manifest for counterfactual trajectories.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub intervention_manifest: Option<InterventionManifest>,
}

impl Default for Outcome {
    fn default() -> Self {
        Self {
            endpoint: String::new(),
            net_r: 0.0,
            label_status: String::new(),
            horizon_bars: 0,
            label_available_time: 0,
            mae_r: 0.0,
            mfe_r: 0.0,
            ambiguous_bars: 0,
            entry_price: 0.0,
            risk_unit_price: 0.0,
            market_move_r: 0.0,
            cost_r: 0.0,
            funding_r: 0.0,
            intervention_manifest: None,
        }
    }
}

/// Simulator configuration parsed from the compiled request's manifest.
pub struct SimulatorParams {
    pub round_trip_cost_r: f64,
    pub funding_rate_r: f64,
    pub funding_hours: i64,
    pub fill_policy: FillPolicy,
    pub round_trip_cost_bps: Option<f64>,
}

impl SimulatorParams {
    pub fn from_json(m: &Value) -> SimulatorParams {
        SimulatorParams {
            round_trip_cost_r: m
                .get("round_trip_cost_r")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.07),
            funding_rate_r: m
                .get("funding_rate_r")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0),
            funding_hours: m.get("funding_hours").and_then(|v| v.as_i64()).unwrap_or(8),
            fill_policy: match m.get("fill_policy").and_then(|f| f.as_str()) {
                Some("FILL_AT_LIMIT") => FillPolicy::Limit,
                _ => FillPolicy::BarClose,
            },
            round_trip_cost_bps: m.get("round_trip_cost_bps").and_then(|v| v.as_f64()),
        }
    }
}
