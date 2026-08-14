//! fib_projection_reversal: reversal at a measured Fibonacci extension level,
//! rejected by a close (variant 'a', ratio 1.618) — mirror src/v8/experts/
//! fib_projection_reversal.py evaluate() bit-for-bit (PARITY_AND_IDENTITY_SPEC
//! §3; COMPUTE_CORE_SPEC §8 S4). Ported at S4; draft parity proven.

use crate::experts::base::*;
use crate::state::HistBar;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["location", "volatility", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

/// `_RATIO['a']` — the declared variant (fib_projection_reversal.variant_id is
/// 'a' in the Python source; the extension-ratio grid is frozen in code).
const RATIO: f64 = 1.618;

/// `_extension_level`: from the self-describing fib tuple
/// (anchor, direction, retr, ext), the ext-pair whose ratio matches within
/// 1e-9; None when the tuple shape or the ratio is absent.
fn extension_level(fibs: &serde_json::Value, ratio: f64) -> Option<f64> {
    let arr = fibs.as_array()?;
    if arr.len() != 4 {
        return None;
    }
    let ext = arr[3].as_array()?;
    for pair in ext {
        let r = pair[0].as_f64()?;
        let level = pair[1].as_f64()?;
        if (r - ratio).abs() < 1e-9 {
            return Some(level);
        }
    }
    None
}

pub fn fib_projection_reversal(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // `_need`: close, atr, history, fib_levels must all be present.
    let _close = match fm.value("close") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let atr = match fm.value("atr") {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let fibs = match fm.features.get("fib_levels") {
        Some(f) => &f.value,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // `atr is None or fibs not a 4-tuple or hist empty` -> NO_HABITAT.
    let arr = match fibs.as_array() {
        Some(a) if a.len() == 4 => a,
        _ => return no_habitat(expert_id, version, fm.as_of),
    };
    let anchor_price = match arr[0].as_f64() {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    let direction = match arr[1].as_f64() {
        Some(v) => v,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    if (direction != 1.0 && direction != -1.0) || anchor_price <= 0.0 {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let level = match extension_level(fibs, RATIO) {
        Some(l) => l,
        None => return no_habitat(expert_id, version, fm.as_of),
    };
    // Up-impulse (+1) overshoots to the UPSIDE -> short the overextension;
    // down-impulse (-1) overshoots to the DOWNSIDE -> long.
    let (direction_sig, pred): (&str, Box<dyn Fn(usize, &HistBar) -> bool>) =
        if direction == 1.0 {
            ("SHORT", Box::new(move |i, b| i != 0 && b.high >= level && b.close < level))
        } else {
            ("LONG", Box::new(move |i, b| i != 0 && b.low <= level && b.close > level))
        };
    let last = fm.history.len() - 1;
    if !pred(last, &fm.history[last]) {
        return no_setup(expert_id, version, fm.as_of);
    }
    let anchor = find_setup_anchor(&fm.history, &*pred);
    let mut g = vec![
        ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
        ("target_r", serde_json::json!(TARGET_R)),
        ("stop_r", serde_json::json!(STOP_R)),
        ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
        ("atr_ref", serde_json::json!(atr)),
    ];
    // The invalidation reference is FROZEN at detection: LONG -> close below
    // the level invalidates (prior_low_ref); SHORT -> close above (prior_high).
    if direction_sig == "LONG" {
        g.push(("prior_low_ref", serde_json::json!(level)));
    } else {
        g.push(("prior_high_ref", serde_json::json!(level)));
    }
    let draft = Draft {
        direction: direction_sig.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(g),
    };
    let fingerprint = format!("{sym}:{:.3}:{:.6}:{}", RATIO, level, direction_sig);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
