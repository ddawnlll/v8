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

/// A feature value at the stepped bar (or its absence).
pub struct FeatCtx<'a> {
    pub live: &'a dyn Fn(&str) -> Option<f64>,
    /// `window_high_{n}` / `window_low_{n}` live channel features.
    pub live_window: &'a dyn Fn(&str, usize) -> Option<f64>,
    /// The history window (oldest first) of [o, h, l, c, ema_fast, ema_slow].
    pub history: &'a dyn Fn() -> Option<Vec<[f64; 6]>>,
}

/// Evaluate a compiled predicate (canonical JSON tree) against a frozen
/// geometry and a per-bar feature context.
pub fn evaluate(ir: &Value, geom: &serde_json::Map<String, Value>,
                dir: &str, ctx: &FeatCtx) -> bool {
    rule(ir, geom, dir, ctx)
}

fn rule(v: &Value, geom: &serde_json::Map<String, Value>, dir: &str,
        ctx: &FeatCtx) -> bool {
    match v.get("type").and_then(|t| t.as_str()) {
        Some("failopen") => true,
        Some("compare") => compare(v, geom, dir, ctx),
        Some("asym_compare") => asym_compare(v, geom, dir, ctx),
        Some("guard") => {
            // Whole-condition fail-open (trend_pullback_depth, rsi_stoch
            // variant b): if ANY declared operand is absent, the thesis is
            // true (the code returns True before the AND). This differs from
            // per-rule fail-open, where one rule can fail open while another
            // still evaluates.
            for op in v["operands"].as_array().unwrap_or(&Vec::new()) {
                if operand(op, geom, dir, ctx).is_none() {
                    return true;
                }
            }
            rule(&v["rule"], geom, dir, ctx)
        }
        Some("all_of") => v["rules"].as_array().map(|rs| rs.iter().all(|r| rule(r, geom, dir, ctx)))
            .unwrap_or(true),
        Some("any_of") => v["rules"].as_array().map(|rs| rs.iter().any(|r| rule(r, geom, dir, ctx)))
            .unwrap_or(true),
        Some("dispatch") => {
            // Ordered: first case whose geometry key is present wins.
            if let Some(cases) = v["cases"].as_array() {
                for case in cases {
                    let key = case["key"].as_str().unwrap_or("");
                    if let Some(eq) = case.get("equals").and_then(|e| e.as_str()) {
                        // Value-equality case (e.g. variant == 'b').
                        if geom.get(key).and_then(|v| v.as_str()) == Some(eq) {
                            return rule(&case["rule"], geom, dir, ctx);
                        }
                    } else if geom.contains_key(key) {
                        return rule(&case["rule"], geom, dir, ctx);
                    }
                }
            }
            rule(&v["default"], geom, dir, ctx)
        }
        _ => true, // unknown node: fail open (an unexpressible rule is not a dead thesis)
    }
}

/// Resolve an operand; `None` = absent -> the containing comparison fails open.
fn operand(v: &Value, geom: &serde_json::Map<String, Value>, dir: &str, ctx: &FeatCtx) -> Option<f64> {
    match v.get("type").and_then(|t| t.as_str()) {
        Some("live") => {
            let name = v["name"].as_str()?;
            (ctx.live)(name)
        }
        Some("live_window") => {
            let name = v["name"].as_str()?;
            let n = v["n"].as_u64()? as usize;
            (ctx.live_window)(name, n)
        }
        Some("ref") => {
            let key = v["key"].as_str()?;
            geom.get(key).and_then(|g| g.as_f64())
        }
        Some("ref_dir") => {
            // Direction-selected frozen reference: LONG reads long_key,
            // SHORT reads short_key (each absent -> fail open).
            let key = if dir == "SHORT" { v["short_key"].as_str()? } else { v["long_key"].as_str()? };
            geom.get(key).and_then(|g| g.as_f64())
        }
        Some("live_window_dir") => {
            // Direction-selected live channel feature (donchian): LONG reads
            // window_low_{n}, SHORT reads window_high_{n}; n from n_ref or
            // n_default.
            let name = if dir == "SHORT" { v["short"].as_str()? } else { v["long"].as_str()? };
            let n = v.get("n_ref").and_then(|r| r.as_str())
                .and_then(|k| geom.get(k).and_then(|g| g.as_i64()))
                .map(|x| x as usize)
                .or_else(|| v["n_default"].as_u64().map(|x| x as usize))?;
            (ctx.live_window)(name, n)
        }
        Some("window_agg_dir") => {
            // Direction-selected window aggregate (donchian e/f): LONG
            // aggregates {feature, agg} over the last n history bars
            // (EXCLUSIVE of the newest), SHORT the other.
            let side = if dir == "SHORT" { &v["short"] } else { &v["long"] };
            let node = serde_json::json!({
                "type": "window_agg",
                "feature": side["feature"].as_str().unwrap_or(""),
                "n": v["n"].as_u64().unwrap_or(0),
                "agg": side["agg"].as_str().unwrap_or("MAX"),
                "end": v.get("end").and_then(|e| e.as_str()).unwrap_or("INCLUSIVE"),
            });
            window_agg(&node, ctx)
        }
        Some("const") => v["v"].as_f64(),
        Some("window_agg") => window_agg(v, ctx),
        Some("mean_of2") => {
            let a = operand(&v["a"], geom, dir, ctx)?;
            let b = operand(&v["b"], geom, dir, ctx)?;
            Some((a + b) / 2.0)
        }
        _ => None,
    }
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
    let hi = if exclusive { hist.len().saturating_sub(1) } else { hist.len() };
    let lo = hi.saturating_sub(n);
    if lo >= hi {
        return None;
    }
    let idx = |b: &[f64; 6]| -> Option<f64> { match feat {
        "open" => Some(b[0]),
        "high" => Some(b[1]),
        "low" => Some(b[2]),
        "close" => Some(b[3]),
        "ema_fast" => Some(b[4]),
        "ema_slow" => Some(b[5]),
        _ => None,
    } };
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
        _ => |_, _| true, // unknown operator: fail open
    }
}

fn compare(v: &Value, geom: &serde_json::Map<String, Value>, dir: &str,
           ctx: &FeatCtx) -> bool {
    let lhs = match operand(&v["lhs"], geom, dir, ctx) {
        Some(x) => x,
        None => return true, // fail open
    };
    let rhs = match operand(&v["rhs"], geom, dir, ctx) {
        Some(x) => x,
        None => return true, // fail open
    };
    let op = v["op"].as_str().unwrap_or("");
    let cmp = resolve_op(op);
    match v.get("orient").and_then(|o| o.as_str()) {
        Some("FLIP_ON_SHORT") => {
            if dir == "SHORT" {
                resolve_op(&flip(op))(lhs, rhs)
            } else {
                cmp(lhs, rhs)
            }
        }
        _ => cmp(lhs, rhs),
    }
}

/// rsi_stoch_reversion-style: LONG compares against one bound, SHORT against
/// another (not a flipped operator — asymmetric constants).
fn asym_compare(v: &Value, geom: &serde_json::Map<String, Value>, dir: &str,
                ctx: &FeatCtx) -> bool {
    let lhs = match operand(&v["lhs"], geom, dir, ctx) {
        Some(x) => x,
        None => return true,
    };
    let side = if dir == "SHORT" { &v["short"] } else { &v["long"] };
    let rhs = match operand(&side["rhs"], geom, dir, ctx) {
        Some(x) => x,
        None => return true,
    };
    let cmp = resolve_op(side["op"].as_str().unwrap_or(""));
    cmp(lhs, rhs)
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
