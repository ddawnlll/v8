//! Compiled post-entry thesis (`still_valid`) IR evaluator (PREDICATE_IR_SPEC).
//!
//! The control plane compiles each Expert's `still_valid` into an IR tree
//! (`tools/predicate_ir.py`) serialized as canonical JSON; the kernel
//! evaluates it natively so the compute plane never re-enters Python
//! (no-callback invariant, D-078). Semantics are normative because they
//! reproduce V8.0 behaviour exactly:
//!
//! 1. **Fail-open on absence.** If any operand resolves to absent — a missing
//!    geometry key, a feature not present, or an absent value — the rule
//!    yields `true` (thesis still valid); price governs the exit.
//! 2. **FLIP_ON_SHORT** applies the comparison as written for LONG and with
//!    the operator reversed for SHORT; direction is frozen on the Candidate.
//! 3. **Dispatch is ordered**: the first case whose geometry key is present
//!    wins, mirroring the `if 'x' in geom ... elif ...` chains in the sources.
//! 4. **Frozen references are values** captured at birth, never re-read from
//!    state — that is what keeps the cell's read set bounded.
//! 5. Live features are read at the stepped bar, never later.

use serde_json::Value;

/// The epistemic evaluation status of a candidate thesis.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum InvalidationReason {
    ConditionFailed { rule_type: String, detail: String },
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum UnknownReason {
    MissingFeature(String),
    MissingGeometryKey(String),
    AbsentValue,
    UnsupportedPredicate(String),
    DegradedStateQuality,
    StaleFeature(String),
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ThesisStatus {
    Valid,
    Invalid { reason: InvalidationReason },
    Unknown(UnknownReason),
}

/// Operational policy derived from epistemic belief state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum PositionPolicy {
    Hold,
    Exit,
    Refuse,
}

/// Map epistemic belief state into operational execution policy.
///
/// Under V8 operational baseline, epistemic uncertainty (`Unknown`) maps to `Hold`
/// (fail-open operational action), preserving price-governed exit without falsely
/// declaring the thesis `Valid`.
pub fn evaluate_position_policy(status: &ThesisStatus) -> PositionPolicy {
    match status {
        ThesisStatus::Valid => PositionPolicy::Hold,
        ThesisStatus::Unknown(_) => PositionPolicy::Hold,
        ThesisStatus::Invalid { .. } => PositionPolicy::Exit,
    }
}

/// A feature value at the stepped bar (or its absence).
pub struct FeatCtx<'a> {
    pub live: &'a dyn Fn(&str) -> Option<f64>,
    /// `window_high_{n}` / `window_low_{n}` live channel features.
    pub live_window: &'a dyn Fn(&str, usize) -> Option<f64>,
    /// The history window (oldest first) of [o, h, l, c, ema_fast, ema_slow].
    pub history: &'a dyn Fn() -> Option<Vec<[f64; 6]>>,
}

/// Evaluate a compiled predicate into its three-valued epistemic status (`ThesisStatus`).
pub fn evaluate_status(
    ir: &Value,
    geom: &serde_json::Map<String, Value>,
    dir: &str,
    ctx: &FeatCtx,
) -> ThesisStatus {
    rule_status(ir, geom, dir, ctx)
}

/// Evaluate a compiled predicate (canonical JSON tree) against a frozen
/// geometry and a per-bar feature context, returning whether the operational
/// policy continues to hold.
pub fn evaluate(
    ir: &Value,
    geom: &serde_json::Map<String, Value>,
    dir: &str,
    ctx: &FeatCtx,
) -> bool {
    let status = evaluate_status(ir, geom, dir, ctx);
    evaluate_position_policy(&status) == PositionPolicy::Hold
}

fn rule_status(v: &Value, geom: &serde_json::Map<String, Value>, dir: &str, ctx: &FeatCtx) -> ThesisStatus {
    match v.get("type").and_then(|t| t.as_str()) {
        Some("failopen") => ThesisStatus::Valid,
        Some("compare") => compare_status(v, geom, dir, ctx),
        Some("asym_compare") => asym_compare_status(v, geom, dir, ctx),
        Some("guard") => {
            // Whole-condition fail-open (trend_pullback_depth, rsi_stoch
            // variant b): if ANY declared operand is absent, the epistemic state
            // is Unknown (which maps to Hold under evaluate_position_policy).
            for op in v["operands"].as_array().unwrap_or(&Vec::new()) {
                if let Err(u) = operand_status(op, geom, dir, ctx) {
                    return ThesisStatus::Unknown(u);
                }
            }
            rule_status(&v["rule"], geom, dir, ctx)
        }
        Some("all_of") => {
            let mut unknown = None;
            if let Some(rules) = v["rules"].as_array() {
                for r in rules {
                    match rule_status(r, geom, dir, ctx) {
                        ThesisStatus::Invalid { reason } => return ThesisStatus::Invalid { reason },
                        ThesisStatus::Unknown(u) => {
                            if unknown.is_none() {
                                unknown = Some(u);
                            }
                        }
                        ThesisStatus::Valid => {}
                    }
                }
            }
            if let Some(u) = unknown {
                ThesisStatus::Unknown(u)
            } else {
                ThesisStatus::Valid
            }
        }
        Some("any_of") => {
            let mut unknown = None;
            if let Some(rules) = v["rules"].as_array() {
                let mut all_invalid = true;
                for r in rules {
                    match rule_status(r, geom, dir, ctx) {
                        ThesisStatus::Valid => return ThesisStatus::Valid,
                        ThesisStatus::Unknown(u) => {
                            all_invalid = false;
                            if unknown.is_none() {
                                unknown = Some(u);
                            }
                        }
                        ThesisStatus::Invalid { .. } => {}
                    }
                }
                if let Some(u) = unknown {
                    ThesisStatus::Unknown(u)
                } else if all_invalid {
                    ThesisStatus::Invalid {
                        reason: InvalidationReason::ConditionFailed {
                            rule_type: "any_of".into(),
                            detail: "no condition satisfied".into(),
                        },
                    }
                } else {
                    ThesisStatus::Valid
                }
            } else {
                ThesisStatus::Valid
            }
        }
        Some("dispatch") => {
            // Ordered: first case whose geometry key is present wins.
            if let Some(cases) = v["cases"].as_array() {
                for case in cases {
                    let key = case["key"].as_str().unwrap_or("");
                    if let Some(eq) = case.get("equals").and_then(|e| e.as_str()) {
                        // Value-equality case (e.g. variant == 'b').
                        if geom.get(key).and_then(|v| v.as_str()) == Some(eq) {
                            return rule_status(&case["rule"], geom, dir, ctx);
                        }
                    } else if geom.contains_key(key) {
                        return rule_status(&case["rule"], geom, dir, ctx);
                    }
                }
            }
            rule_status(&v["default"], geom, dir, ctx)
        }
        _ => ThesisStatus::Unknown(UnknownReason::UnsupportedPredicate(
            v.get("type").and_then(|t| t.as_str()).unwrap_or("unknown").to_string(),
        )),
    }
}

/// Resolve an operand into a value or an explicit epistemic `UnknownReason`.
fn operand_status(
    v: &Value,
    geom: &serde_json::Map<String, Value>,
    dir: &str,
    ctx: &FeatCtx,
) -> Result<f64, UnknownReason> {
    match v.get("type").and_then(|t| t.as_str()) {
        Some("live") => {
            let name = match v.get("name").and_then(|n| n.as_str()) {
                Some(n) => n,
                None => return Err(UnknownReason::AbsentValue),
            };
            (ctx.live)(name).ok_or_else(|| UnknownReason::MissingFeature(name.to_string()))
        }
        Some("live_window") => {
            let name = match v.get("name").and_then(|n| n.as_str()) {
                Some(n) => n,
                None => return Err(UnknownReason::AbsentValue),
            };
            let n = match v.get("n").and_then(|n| n.as_u64()) {
                Some(n) => n as usize,
                None => return Err(UnknownReason::AbsentValue),
            };
            (ctx.live_window)(name, n)
                .ok_or_else(|| UnknownReason::MissingFeature(format!("{name}_{n}")))
        }
        Some("ref") => {
            let key = match v.get("key").and_then(|k| k.as_str()) {
                Some(k) => k,
                None => return Err(UnknownReason::AbsentValue),
            };
            geom.get(key)
                .and_then(|g| g.as_f64())
                .ok_or_else(|| UnknownReason::MissingGeometryKey(key.to_string()))
        }
        Some("ref_dir") => {
            let key = if dir == "SHORT" {
                match v.get("short_key").and_then(|k| k.as_str()) {
                    Some(k) => k,
                    None => return Err(UnknownReason::AbsentValue),
                }
            } else {
                match v.get("long_key").and_then(|k| k.as_str()) {
                    Some(k) => k,
                    None => return Err(UnknownReason::AbsentValue),
                }
            };
            geom.get(key)
                .and_then(|g| g.as_f64())
                .ok_or_else(|| UnknownReason::MissingGeometryKey(key.to_string()))
        }
        Some("live_window_dir") => {
            let name = if dir == "SHORT" {
                match v.get("short").and_then(|s| s.as_str()) {
                    Some(s) => s,
                    None => return Err(UnknownReason::AbsentValue),
                }
            } else {
                match v.get("long").and_then(|l| l.as_str()) {
                    Some(l) => l,
                    None => return Err(UnknownReason::AbsentValue),
                }
            };
            let n = v
                .get("n_ref")
                .and_then(|r| r.as_str())
                .and_then(|k| geom.get(k).and_then(|g| g.as_i64()))
                .map(|x| x as usize)
                .or_else(|| v.get("n_default").and_then(|n| n.as_u64()).map(|x| x as usize));
            let n = match n {
                Some(n) => n,
                None => return Err(UnknownReason::AbsentValue),
            };
            (ctx.live_window)(name, n)
                .ok_or_else(|| UnknownReason::MissingFeature(format!("{name}_{n}")))
        }
        Some("window_agg_dir") => {
            let side = if dir == "SHORT" {
                &v["short"]
            } else {
                &v["long"]
            };
            let node = serde_json::json!({
                "type": "window_agg",
                "feature": side.get("feature").and_then(|f| f.as_str()).unwrap_or(""),
                "n": v.get("n").and_then(|n| n.as_u64()).unwrap_or(0),
                "agg": side.get("agg").and_then(|a| a.as_str()).unwrap_or("MAX"),
                "end": v.get("end").and_then(|e| e.as_str()).unwrap_or("INCLUSIVE"),
            });
            window_agg(&node, ctx).ok_or(UnknownReason::AbsentValue)
        }
        Some("const") => v.get("v").and_then(|x| x.as_f64()).ok_or(UnknownReason::AbsentValue),
        Some("window_agg") => window_agg(v, ctx).ok_or(UnknownReason::AbsentValue),
        Some("mean_of2") => {
            let a = operand_status(&v["a"], geom, dir, ctx)?;
            let b = operand_status(&v["b"], geom, dir, ctx)?;
            Ok((a + b) / 2.0)
        }
        _ => Err(UnknownReason::UnsupportedPredicate(
            v.get("type").and_then(|t| t.as_str()).unwrap_or("unknown").to_string(),
        )),
    }
}

/// Legacy helper for raw f64 option.
#[allow(dead_code)]
fn operand(
    v: &Value,
    geom: &serde_json::Map<String, Value>,
    dir: &str,
    ctx: &FeatCtx,
) -> Option<f64> {
    operand_status(v, geom, dir, ctx).ok()
}

/// `WindowAgg { feature, n, agg, end }` over the history window ending at the
/// stepped bar. `feature` names the history field (high/low/open/close/
/// ema_fast/ema_slow); `end` is INCLUSIVE (default) or EXCLUSIVE of the newest
/// bar (donchian e/f).
fn window_agg(v: &Value, ctx: &FeatCtx) -> Option<f64> {
    let hist = (ctx.history)()?;
    let n = v["n"].as_u64()? as usize;
    let feat = v["feature"].as_str()?;
    let exclusive = v.get("end").and_then(|e| e.as_str()) == Some("EXCLUSIVE");
    let hi = if exclusive {
        hist.len().saturating_sub(1)
    } else {
        hist.len()
    };
    if exclusive && hist.len() < n {
        return None;
    }
    let count = if exclusive { n.saturating_sub(1) } else { n };
    let lo = hi.saturating_sub(count);
    if lo >= hi {
        return None;
    }
    let idx = |b: &[f64; 6]| -> Option<f64> {
        match feat {
            "open" => Some(b[0]),
            "high" => Some(b[1]),
            "low" => Some(b[2]),
            "close" => Some(b[3]),
            "ema_fast" => Some(b[4]),
            "ema_slow" => Some(b[5]),
            _ => None,
        }
    };
    let mut acc: Option<f64> = None;
    for b in &hist[lo..hi] {
        let x = idx(b)?;
        acc = Some(match (v["agg"].as_str(), acc) {
            (Some("MAX"), Some(a)) => a.max(x),
            (Some("MIN"), Some(a)) => a.min(x),
            (Some("MAX"), None) => x,
            (Some("MIN"), None) => x,
            _ => return None,
        });
    }
    acc
}

fn resolve_op(op: &str) -> fn(f64, f64) -> bool {
    match op {
        "GT" => |a, b| a > b,
        "LT" => |a, b| a < b,
        "GTE" => |a, b| a >= b,
        "LTE" => |a, b| a <= b,
        _ => |_, _| true,
    }
}

fn compare_status(
    v: &Value,
    geom: &serde_json::Map<String, Value>,
    dir: &str,
    ctx: &FeatCtx,
) -> ThesisStatus {
    let lhs = match operand_status(&v["lhs"], geom, dir, ctx) {
        Ok(x) => x,
        Err(u) => return ThesisStatus::Unknown(u),
    };
    let rhs = match operand_status(&v["rhs"], geom, dir, ctx) {
        Ok(x) => x,
        Err(u) => return ThesisStatus::Unknown(u),
    };
    let op = v["op"].as_str().unwrap_or("");
    let cmp = resolve_op(op);
    let valid = match v.get("orient").and_then(|o| o.as_str()) {
        Some("FLIP_ON_SHORT") => {
            if dir == "SHORT" {
                resolve_op(&flip(op))(lhs, rhs)
            } else {
                cmp(lhs, rhs)
            }
        }
        _ => cmp(lhs, rhs),
    };
    if valid {
        ThesisStatus::Valid
    } else {
        ThesisStatus::Invalid {
            reason: InvalidationReason::ConditionFailed {
                rule_type: "compare".into(),
                detail: format!("lhs={lhs} op={op} rhs={rhs} failed (dir={dir})"),
            },
        }
    }
}

fn asym_compare_status(
    v: &Value,
    geom: &serde_json::Map<String, Value>,
    dir: &str,
    ctx: &FeatCtx,
) -> ThesisStatus {
    let lhs = match operand_status(&v["lhs"], geom, dir, ctx) {
        Ok(x) => x,
        Err(u) => return ThesisStatus::Unknown(u),
    };
    let side = if dir == "SHORT" {
        &v["short"]
    } else {
        &v["long"]
    };
    let rhs = match operand_status(&side["rhs"], geom, dir, ctx) {
        Ok(x) => x,
        Err(u) => return ThesisStatus::Unknown(u),
    };
    let op = side["op"].as_str().unwrap_or("");
    let cmp = resolve_op(op);
    if cmp(lhs, rhs) {
        ThesisStatus::Valid
    } else {
        ThesisStatus::Invalid {
            reason: InvalidationReason::ConditionFailed {
                rule_type: "asym_compare".into(),
                detail: format!("lhs={lhs} op={op} rhs={rhs} failed (dir={dir})"),
            },
        }
    }
}

fn flip(op: &str) -> String {
    match op {
        "GT" => "LT".to_string(),
        "LT" => "GT".to_string(),
        "GTE" => "LTE".to_string(),
        "LTE" => "GTE".to_string(),
        _ => op.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unobservable_operand_yields_epistemic_unknown_not_valid() {
        // Issue #160 property test gate: Withholding an observation must yield
        // ThesisStatus::Unknown, never ThesisStatus::Valid.
        let ir = serde_json::json!({
            "type": "compare",
            "op": "GT",
            "lhs": { "type": "live", "name": "rsi14" },
            "rhs": { "type": "const", "v": 50.0 }
        });
        let geom = serde_json::Map::new();
        // Context withholds rsi14 (returns None)
        let ctx = FeatCtx {
            live: &|_| None,
            live_window: &|_, _| None,
            history: &|| None,
        };

        let status = evaluate_status(&ir, &geom, "LONG", &ctx);
        assert_eq!(
            status,
            ThesisStatus::Unknown(UnknownReason::MissingFeature("rsi14".to_string())),
            "withheld feature must return ThesisStatus::Unknown, never ThesisStatus::Valid"
        );

        // However, operational policy maps Unknown to Hold
        let policy = evaluate_position_policy(&status);
        assert_eq!(
            policy,
            PositionPolicy::Hold,
            "operational baseline maps epistemic uncertainty to PositionPolicy::Hold"
        );
    }

    #[test]
    fn observed_operands_yield_valid_or_invalid() {
        let ir = serde_json::json!({
            "type": "compare",
            "op": "GT",
            "lhs": { "type": "live", "name": "close" },
            "rhs": { "type": "const", "v": 100.0 }
        });
        let geom = serde_json::Map::new();
        let ctx_valid = FeatCtx {
            live: &|name| if name == "close" { Some(105.0) } else { None },
            live_window: &|_, _| None,
            history: &|| None,
        };
        let ctx_invalid = FeatCtx {
            live: &|name| if name == "close" { Some(95.0) } else { None },
            live_window: &|_, _| None,
            history: &|| None,
        };

        assert_eq!(
            evaluate_status(&ir, &geom, "LONG", &ctx_valid),
            ThesisStatus::Valid
        );
        match evaluate_status(&ir, &geom, "LONG", &ctx_invalid) {
            ThesisStatus::Invalid { .. } => {}
            other => panic!("expected Invalid, got {other:?}"),
        }
    }
}
