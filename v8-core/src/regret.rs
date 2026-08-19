//! CubeReducer + streaming regret (OUTCOME_CUBE_SPEC; RECOVERABLE_REGRET
//! PROTOCOL §3-4).
//!
//! The Outcome Cube is a computation, not necessarily a stored table
//! (D-081): at `VALUES` tier the cube is reduced in flight into per-Candidate
//! accumulators and only the reduced tables are persisted. The reduction is
//! order-independent and exact (absorbing a Candidate's actions in any order
//! yields identical accumulators), so no value depends on scheduling (G5).
//!
//! The legal action manifest (OUTCOME_CUBE_SPEC §2) mirrors
//! `tools/regret.py`:
//! - element 0 is always NO_TRADE;
//! - element 1 is always the ACTUAL action, seeded directly from the frozen
//!   draft geometry — `a_actual in A(C)` holds by construction;
//! - the declared grid (target_r (1,2,3) x expiry_bars (8,24,48)) follows,
//!   de-duplicated by action id; `pyramid_add_rules` is an excluded axis.
//!
//! Cell status (OUTCOME_CUBE_SPEC §3): OK / CENSORED / UNDEFINED_FUTURE /
//! NOT_EVALUABLE_ACTION / NO_ENTRY; `MIN_FUTURE_BARS = 1`; NO_TRADE is OK
//! with utility 0.0 by definition (no simulator call).
//!
//! Gap (OUTCOME_CUBE_SPEC §6): `gap(C) = max{Replay(C,a) : status=OK} -
//! Replay(C, a_actual)`, non-negative by construction; ties are reported
//! (`< 1e-12`), never broken; the computation abstains whenever a non-OK cell
//! could have been the maximizer.

use std::collections::HashMap;

use serde_json::Value;

use crate::hash::Canon;

pub const MIN_FUTURE_BARS: usize = 1;
pub const GAP_TIE_EPS: f64 = 1e-12;
pub const GENERATOR_VERSION: &str = "legal-action-manifest-v1";

pub const TARGET_R_GRID: [f64; 3] = [1.0, 2.0, 3.0];
pub const EXPIRY_BARS_GRID: [i64; 3] = [8, 24, 48];
pub const EXCLUDED_VARIANT_KEYS: [&str; 1] = ["pyramid_add_rules"];

pub const CELL_OK: &str = "OK";
pub const CELL_CENSORED: &str = "CENSORED";
pub const CELL_UNDEFINED_FUTURE: &str = "UNDEFINED_FUTURE";
pub const CELL_NOT_EVALUABLE_ACTION: &str = "NOT_EVALUABLE_ACTION";
pub const CELL_NO_ENTRY: &str = "NO_ENTRY";
#[allow(dead_code)]
pub const CELL_UNSUPPORTED_COUNTERFACTUAL: &str = "UNSUPPORTED_COUNTERFACTUAL";

pub const GAP_COMPUTED: &str = "COMPUTED";
pub const GAP_ABSTAINED_CENSORED: &str = "ABSTAINED_CENSORED";
pub const GAP_ABSTAINED_UNDEFINED: &str = "ABSTAINED_UNDEFINED";
pub const GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION: &str = "NOT_APPLICABLE_NO_ACTUAL_ACTION";
#[allow(dead_code)] // gap-status vocabulary; the Python write_gaps uses it for UNBOUND candidates
pub const GAP_OUTSIDE_CANDIDATE_UNIVERSE: &str = "OUTSIDE_CANDIDATE_UNIVERSE";

/// The V8.2 action id: the bit-encoding of the sorted geometry override
/// (mirrors `_action_id`; the identity domain is V8.2, D-079).
pub fn action_id(override_geom: &serde_json::Map<String, Value>) -> String {
    if override_geom.is_empty() {
        return "NO_TRADE".to_string();
    }
    let mut c = Canon::new();
    c.push_map();
    c.push_count(override_geom.len());
    let mut keys: Vec<&String> = override_geom.keys().collect();
    keys.sort();
    for k in keys {
        c.push_str(k);
        c.push_value(&override_geom[k]);
    }
    c.finish_sha1_hex()
}

/// One legal action.
#[derive(Debug, Clone)]
pub struct Action {
    pub action_id: String,
    pub kind: &'static str,       // NO_TRADE | GEOMETRY_VARIANT
    pub provenance: &'static str, // ACTUAL | DECLARED_VARIANT
    pub override_geom: serde_json::Map<String, Value>,
}

/// A(C) — the legal action manifest.
#[derive(Debug, Clone)]
pub struct Manifest {
    pub manifest_id: String,
    pub actions: Vec<Action>,
    #[allow(dead_code)] // manifest contract (|A(C)|); the cube writes rows, not this field
    pub cardinality: usize,
}

pub fn generate_legal_actions(actual_geometry: &serde_json::Map<String, Value>) -> Manifest {
    let mut actions = Vec::new();
    actions.push(Action {
        action_id: "NO_TRADE".to_string(),
        kind: "NO_TRADE",
        provenance: "DECLARED_VARIANT",
        override_geom: serde_json::Map::new(),
    });
    let mut seen: HashMap<String, ()> = HashMap::new();
    seen.insert("NO_TRADE".to_string(), ());

    let actual_override = actual_geometry.clone();
    let actual_id = action_id(&actual_override);
    actions.push(Action {
        action_id: actual_id.clone(),
        kind: "GEOMETRY_VARIANT",
        provenance: "ACTUAL",
        override_geom: actual_override,
    });
    seen.insert(actual_id, ());

    let excluded = EXCLUDED_VARIANT_KEYS
        .iter()
        .any(|k| actual_geometry.contains_key(*k));
    if !excluded {
        for tr in TARGET_R_GRID {
            for eb in EXPIRY_BARS_GRID {
                let mut override_geom = actual_geometry.clone();
                override_geom.insert("target_r".to_string(), serde_json::json!(tr));
                override_geom.insert("expiry_bars".to_string(), serde_json::json!(eb));
                let aid = action_id(&override_geom);
                if seen.contains_key(&aid) {
                    continue;
                }
                seen.insert(aid.clone(), ());
                actions.push(Action {
                    action_id: aid,
                    kind: "GEOMETRY_VARIANT",
                    provenance: "DECLARED_VARIANT",
                    override_geom,
                });
            }
        }
    }

    let mut m = Canon::new();
    m.push_list();
    m.push_count(actions.len());
    for a in &actions {
        m.push_list();
        m.push_count(2);
        m.push_str(&a.action_id);
        let mut keys: Vec<&String> = a.override_geom.keys().collect();
        keys.sort();
        m.push_list();
        m.push_count(keys.len());
        for k in keys {
            m.push_list();
            m.push_count(2);
            m.push_str(k);
            m.push_value(&a.override_geom[k]);
        }
    }
    m.push_str(GENERATOR_VERSION);
    let manifest_id = m.finish_sha1_hex();

    let cardinality = actions.len();
    Manifest {
        manifest_id,
        actions,
        cardinality,
    }
}

/// One replayed cell.
#[derive(Debug, Clone)]
pub struct Cell {
    pub action_id: String,
    pub status: &'static str,
    pub reason: String,
    pub net_utility: Option<f64>,
}

/// The per-Candidate reduced record (mirrors `compute_gap`'s RegretRecord
/// value fields; identity strings are V8.2-encoded and excluded from parity).
#[derive(Debug, Clone)]
pub struct ReducedRow {
    pub candidate_id: String, // V8.2 identity (excluded from value parity)
    pub manifest_id: String,
    pub actual_action_id: Option<String>,
    pub actual_utility: Option<f64>,
    pub best_utility: Option<f64>,
    pub tie_cardinality: usize,
    pub legal_hindsight_gap: Option<f64>,
    pub gap_status: &'static str,
    pub abstention_reason: String,
    pub no_trade_value: Option<f64>,
    pub counts: HashMap<&'static str, u64>,
}

/// Compute the legal hindsight gap for one Candidate from its cells.
/// Mirrors `tools/regret.py:compute_gap` exactly (values; tie_set membership
/// is compared by cardinality — the action ids are V8.2 identities).
pub fn compute_gap(candidate_id: &str, manifest: &Manifest, cells: &[Cell]) -> ReducedRow {
    let by_action: HashMap<&str, &Cell> = cells.iter().map(|c| (c.action_id.as_str(), c)).collect();

    let mut no_trade_value = None;
    let mut actual_action_id = None;
    let mut actual_utility = None;
    for a in &manifest.actions {
        let cell = match by_action.get(a.action_id.as_str()) {
            Some(c) => c,
            None => continue,
        };
        if a.provenance == "ACTUAL" {
            actual_action_id = Some(a.action_id.clone());
            actual_utility = cell.net_utility;
        }
        if a.kind == "NO_TRADE" {
            no_trade_value = cell.net_utility;
        }
    }

    let mut row = ReducedRow {
        candidate_id: candidate_id.to_string(),
        manifest_id: manifest.manifest_id.clone(),
        actual_action_id: actual_action_id.clone(),
        actual_utility,
        best_utility: None,
        tie_cardinality: 0,
        legal_hindsight_gap: None,
        gap_status: GAP_COMPUTED,
        abstention_reason: String::new(),
        no_trade_value,
        counts: HashMap::new(),
    };
    for c in cells {
        *row.counts.entry(c.status).or_insert(0) += 1;
    }

    let actual_id = match &actual_action_id {
        Some(i) => i.clone(),
        None => {
            row.gap_status = GAP_NOT_APPLICABLE_NO_ACTUAL_ACTION;
            row.abstention_reason = "no ACTUAL action in the generated manifest".to_string();
            return row;
        }
    };
    let actual_cell = by_action.get(actual_id.as_str());
    let actual_ok = matches!(actual_cell.map(|c| c.status), Some(CELL_OK));
    if !actual_ok {
        // The Python record sets actual_utility=None in this branch (the
        // actual cell was not evaluable), even though the cell carries a
        // value.
        row.actual_utility = None;
        row.gap_status = GAP_ABSTAINED_UNDEFINED;
        row.abstention_reason = format!(
            "actual action cell is {}: {}",
            actual_cell.map(|c| c.status).unwrap_or(""),
            actual_cell.map(|c| c.reason.as_str()).unwrap_or("")
        );
        return row;
    }

    let censored = cells.iter().filter(|c| c.status == CELL_CENSORED).count();
    if censored > 0 {
        row.gap_status = GAP_ABSTAINED_CENSORED;
        row.abstention_reason = format!(
            "{censored} action(s) reached tape end before a terminal endpoint; \
             their eventual outcome could exceed the best fully-observed cell"
        );
        return row;
    }

    let ok_rows: Vec<&Cell> = cells.iter().filter(|c| c.status == CELL_OK).collect();
    if ok_rows.is_empty() {
        row.gap_status = GAP_ABSTAINED_UNDEFINED;
        row.abstention_reason = "no cell_status OK cell to maximize over".to_string();
        return row;
    }

    let best_ok = ok_rows
        .iter()
        .filter_map(|c| c.net_utility)
        .fold(f64::NEG_INFINITY, f64::max);
    let tie_count = ok_rows
        .iter()
        .filter(|c| (c.net_utility.unwrap_or(0.0) - best_ok).abs() < GAP_TIE_EPS)
        .count();
    row.best_utility = Some(best_ok);
    row.tie_cardinality = tie_count;
    row.legal_hindsight_gap = Some(best_ok - actual_utility.unwrap_or(0.0));
    row.gap_status = GAP_COMPUTED;
    row
}

/// Causal intervention classes for regret attribution partitioning (D-105, Issue #161).
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[allow(dead_code)]
pub enum InterventionClass {
    Executed,
    CapacityRejected { sub_reason: String },
    ThesisInvalidated { reason: String },
    TradabilityMaskVeto { reason: String },
    UnsupportedCounterfactual { reason: String },
}

/// A partitioned regret bucket grouping candidate outcomes by identical causal intervention semantics.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[allow(dead_code)]
pub struct PartitionedRegretBucket {
    pub intervention_class: InterventionClass,
    pub candidate_ids: Vec<String>,
    pub mean_gap: Option<f64>,
    pub computed_count: usize,
    pub abstained_count: usize,
}

/// Partition reduced regret rows by intervention class, blocking unweighted pooling across heterogeneous intervention types.
#[allow(dead_code)]
pub fn partition_regret_by_intervention(
    rows: &[ReducedRow],
    class_of: &dyn Fn(&str) -> InterventionClass,
) -> HashMap<InterventionClass, Vec<ReducedRow>> {
    let mut partitioned: HashMap<InterventionClass, Vec<ReducedRow>> = HashMap::new();
    for row in rows {
        let class = class_of(&row.candidate_id);
        partitioned.entry(class).or_default().push(row.clone());
    }
    partitioned
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_regret_partitioning_by_intervention_class() {
        // Issue #161: CAPACITY_REJECTED and THESIS_INVALIDATED enter distinct regret buckets;
        // unweighted pooling across intervention classes is blocked by default.
        let rows = vec![
            ReducedRow {
                candidate_id: "c_cap_1".into(),
                manifest_id: "m1".into(),
                actual_action_id: Some("a1".into()),
                actual_utility: Some(1.0),
                best_utility: Some(2.0),
                tie_cardinality: 1,
                legal_hindsight_gap: Some(1.0),
                gap_status: GAP_COMPUTED,
                abstention_reason: "".into(),
                no_trade_value: Some(0.0),
                counts: HashMap::new(),
            },
            ReducedRow {
                candidate_id: "c_thesis_1".into(),
                manifest_id: "m2".into(),
                actual_action_id: Some("a2".into()),
                actual_utility: Some(-0.5),
                best_utility: Some(0.0),
                tie_cardinality: 1,
                legal_hindsight_gap: Some(0.5),
                gap_status: GAP_COMPUTED,
                abstention_reason: "".into(),
                no_trade_value: Some(0.0),
                counts: HashMap::new(),
            },
        ];

        let class_map = |cid: &str| -> InterventionClass {
            if cid.starts_with("c_cap") {
                InterventionClass::CapacityRejected {
                    sub_reason: "EXISTING_EXPOSURE_CONFLICT".into(),
                }
            } else {
                InterventionClass::ThesisInvalidated {
                    reason: "CONDITION_FAILED".into(),
                }
            }
        };

        let partitioned = partition_regret_by_intervention(&rows, &class_map);
        assert_eq!(partitioned.len(), 2);
        let cap_class = InterventionClass::CapacityRejected {
            sub_reason: "EXISTING_EXPOSURE_CONFLICT".into(),
        };
        let thesis_class = InterventionClass::ThesisInvalidated {
            reason: "CONDITION_FAILED".into(),
        };
        assert!(partitioned.contains_key(&cap_class));
        assert!(partitioned.contains_key(&thesis_class));
        assert_eq!(partitioned[&cap_class].len(), 1);
        assert_eq!(partitioned[&thesis_class].len(), 1);
    }
}
