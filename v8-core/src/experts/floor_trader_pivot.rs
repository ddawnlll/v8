//! floor_trader_pivot: daily-pivot S/R reaction, default variant 'a' (the
//! PP-drift rule, Ch8.7 p264). Port of src/v8/experts/floor_trader_pivot.py
//! evaluate() bit-for-bit (PARITY_AND_IDENTITY_SPEC §3). The D-026 anchor is
//! restricted to the current session (day_start = n - bar_of_session): the
//! pivot set is recomputed daily, so a reaction in a later day is a new
//! setup. The parity harness constructs the Python expert with its default
//! variant ('a'), so only that variant is ported here.

use crate::experts::base::*;
use crate::simulator::Draft;
use crate::state::HistBar;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history", "session"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const EXPIRY_BARS: i64 = 8;

pub fn floor_trader_pivot(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // Python `_need`: {sym}.close, {sym}.atr, {sym}.history,
    // {sym}.pivot_points_day, {sym}.bar_of_session — the FeatMap is keyed by
    // the bare names.
    let close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // pivot_points_day is a non-scalar feature: (PP, R1, R2, R3, R4, S1, S2,
    // S3, S4), the Python unpack order.
    let ppv = match fm.features.get("pivot_points_day") {
        Some(f) => match f.value.as_array() {
            Some(a) => a,
            None => return no_habitat(expert_id, version, fm.as_of),
        },
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if ppv.len() < 9 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let fv = |i: usize| ppv[i].as_f64().unwrap();
    let pp = fv(0);
    let r1 = fv(1);
    let _r2 = fv(2);
    let _r3 = fv(3);
    let _r4 = fv(4);
    let s1 = fv(5);
    let _s2 = fv(6);
    let _s3 = fv(7);
    let _s4 = fv(8);
    let bos = match fm.value("bar_of_session") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let n = fm.history.len();
    if n < 2 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // _detect on the newest history bar (bar t-1).
    let o = fm.history[n - 1].open;
    let _h = fm.history[n - 1].high;
    let _l = fm.history[n - 1].low;
    let c = fm.history[n - 1].close;
    // int(bar_of_session) truncates toward zero; the feature is an
    // integer-valued float, so the `as i64` cast is exact.
    let day_start = n as i64 - bos as i64;
    // Variant 'a' only (the Python default the harness evaluates).
    let pred: Box<dyn Fn(usize, &HistBar) -> bool>;
    let (direction, level, stop_price, target_price): (String, f64, f64, f64);
    if o > pp && c > o {
        direction = "LONG".into();
        level = pp;
        stop_price = pp;
        target_price = r1;
        pred = Box::new(move |j, b| (j as i64) >= day_start && b.open > pp && b.close > b.open);
    } else if o < pp && c < o {
        direction = "SHORT".into();
        level = pp;
        stop_price = pp;
        target_price = s1;
        pred = Box::new(move |j, b| (j as i64) >= day_start && b.open < pp && b.close < b.open);
    } else {
        return no_setup(expert_id, version, fm.as_of);
    }
    let (stop_r, target_r) = if direction == "LONG" {
        ((close - stop_price) / atr, (target_price - close) / atr)
    } else {
        ((stop_price - close) / atr, (close - target_price) / atr)
    };
    if stop_r <= 0.0 || target_r <= 0.0 {
        return no_setup(expert_id, version, fm.as_of);
    }
    let anchor = find_setup_anchor(&fm.history, &*pred);
    let mut geometry = geom(vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(target_r)),
        ("stop_r", serde_json::json!(stop_r)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
        ("variant", serde_json::json!("a")),
        ("level_ref", serde_json::json!(level)),
        ("stop_ref", serde_json::json!(stop_price)),
    ]);
    if direction == "LONG" {
        geometry.insert("prior_low_ref".to_string(), serde_json::json!(stop_price));
    } else {
        geometry.insert("prior_high_ref".to_string(), serde_json::json!(stop_price));
    }
    let fingerprint = format!(
        "{sym}:a:{direction}:{:.6}:{:.6}:{:.6}",
        close, level, stop_price
    );
    let draft = Draft {
        direction: direction.clone(),
        birth_time: fm.as_of,
        risk_geometry: geometry,
    };
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
