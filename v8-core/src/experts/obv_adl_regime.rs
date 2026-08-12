//! obv_adl_regime: OBV/ADL regime-gate (volume_oscillator_regime family) —
//! four variants d/c/b/a in priority order, one draft per bar from the first
//! firing gate. Mirrors src/v8/experts/obv_adl_regime.py bit-for-bit
//! (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).
//!
//! STATUS: implementation complete and verified bit-for-bit against the Python
//! source evaluated on the FULL state (120 bars, 43 candidates, 0 mismatches),
//! but check_one_expert.py cannot PASS: the Python expert declares
//! `requires = ('participation', 'trend')`, whose D-053 group closure
//! (participation/trend/raw) does NOT cover `atr` (volatility group) or
//! `history` (history group) that its `_need` reads. The lab therefore feeds
//! the oracle a projected view withholding both, so the Python oracle emits
//! NO_HABITAT on every bar and the check's ">=1 candidate" guard is
//! unsatisfiable (a faithful port mismatches decisions; a projection-mimicking
//! port yields 0 candidates). PORTED stays false so the S4 parity suite does
//! not include this expert until the Python-side `requires` is fixed.

use crate::experts::base::*;
use crate::state::HistBar;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v1";
pub const REQUIRES: &[&str] = &["participation", "trend"];

// Declared, LOCKED constants (D-036): mirror the Python class constants.
const OBV_WINDOW: usize = 10; // up-bar-count window for the OBV slope sign
const OBV_MAJORITY: i32 = 3;  // net up-bars >= +3 -> OBV rising (of OBV_WINDOW)
const CMF_OVERSOLD: f64 = -0.15; // CMF oversold level (variant d)

/// Sign of the OBV slope proxy (Python `_obv_dir`): net up-close count over
/// the last OBV_WINDOW adjacent bar pairs, >= +OBV_MAJORITY -> +1.0,
/// <= -OBV_MAJORITY -> -1.0, else 0.0. `start = max(1, len - OBV_WINDOW)`.
fn obv_dir(hist: &[HistBar]) -> f64 {
    let n = hist.len();
    let start = std::cmp::max(1, n.saturating_sub(OBV_WINDOW));
    let mut net: i32 = 0;
    for i in start..n {
        let c = hist[i].close;
        let pc = hist[i - 1].close;
        net += if c > pc { 1 } else if c < pc { -1 } else { 0 };
    }
    if net >= OBV_MAJORITY {
        1.0
    } else if net <= -OBV_MAJORITY {
        -1.0
    } else {
        0.0
    }
}

pub fn obv_adl_regime(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // Python `_need`: every requested key must be present (bare names — the
    // Rust state emits features keyed by bare name, matching the Python reads
    // that prepend `{sym}.`). Absent key -> NO_HABITAT.
    for k in ["close", "ema_fast", "ema_slow", "atr", "cmf_20", "history"] {
        if !fm.features.contains_key(k) {
            return no_habitat(expert_id, version, fm.as_of);
        }
    }
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
    // _evaluate_variants: cmf_20 missing/null -> 0.0 (Python's f.get fallback);
    // ema_fast/ema_slow missing/null -> None -> NO_SETUP.
    let d = obv_dir(&fm.history);
    let cmf_v = fm.value("cmf_20").unwrap_or(0.0);
    let fast_v = match fm.value("ema_fast") {
        Some(v) => v,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let slow_v = match fm.value("ema_slow") {
        Some(v) => v,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    // First firing gate wins, in declared priority order d, c, b, a; each
    // variant carries the setup predicate for find_setup_anchor.
    let mut hit: Option<(&str, &str, Box<dyn Fn(usize, &HistBar) -> bool>)> = None;
    for variant in ["d", "c", "b", "a"] {
        match variant {
            "d" => {
                if cmf_v < CMF_OVERSOLD && close < slow_v {
                    hit = Some(("d", "LONG", Box::new(|_i, b: &HistBar| b.close < b.ema_slow)));
                }
            }
            "c" => {
                if close < slow_v && close > fast_v && cmf_v > 0.0 {
                    hit = Some(("c", "LONG", Box::new(|_i, b: &HistBar| b.close < b.ema_slow && b.close > b.ema_fast)));
                } else if close > slow_v && close < fast_v && cmf_v < 0.0 {
                    hit = Some(("c", "SHORT", Box::new(|_i, b: &HistBar| b.close > b.ema_slow && b.close < b.ema_fast)));
                }
            }
            "b" => {
                if close < slow_v && close <= fast_v && d > 0.0 && cmf_v > 0.0 {
                    hit = Some(("b", "LONG", Box::new(|_i, b: &HistBar| b.close < b.ema_slow && b.close <= b.ema_fast)));
                } else if close > slow_v && close >= fast_v && d < 0.0 && cmf_v < 0.0 {
                    hit = Some(("b", "SHORT", Box::new(|_i, b: &HistBar| b.close > b.ema_slow && b.close >= b.ema_fast)));
                }
            }
            _ => {
                if d > 0.0 && cmf_v > 0.0 && fast_v > slow_v {
                    hit = Some(("a", "LONG", Box::new(|_i, b: &HistBar| b.ema_fast > b.ema_slow)));
                } else if d < 0.0 && cmf_v < 0.0 && fast_v < slow_v {
                    hit = Some(("a", "SHORT", Box::new(|_i, b: &HistBar| b.ema_fast < b.ema_slow)));
                }
            }
        }
        if hit.is_some() {
            break;
        }
    }
    let (variant, direction, pred) = match hit {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    let last = fm.history.last().unwrap();
    // Freeze the regime bar's extreme at detection: LONG regime dead below the
    // detection bar's low, SHORT above its high.
    let (level, ref_key) = if direction == "LONG" {
        (last.low, "prior_low_ref")
    } else {
        (last.high, "prior_high_ref")
    };
    let anchor = find_setup_anchor(&fm.history, &*pred);
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(1.0)),
            ("stop_r", serde_json::json!(1.0)),
            ("expiry_bars", serde_json::json!(8)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!(variant)),
            (ref_key, serde_json::json!(level)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}:{}", close, level, variant);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
