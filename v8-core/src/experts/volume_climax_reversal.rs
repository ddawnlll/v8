//! volume_climax_reversal: fade a volume climax / overextension at a local
//! extreme. Five variants in declared priority e > d > c > b > a, ONE draft per
//! bar for the highest-priority gate that fires. The climax extreme is FROZEN
//! at detection; the D-026 anchor is the DETECTION bar (the newest closed bar,
//! never the trend-run start — D-055 semantics). Ported at S4; draft parity
//! proven.

use crate::experts::base::*;
use crate::simulator::Draft;

pub const PORTED: bool = true;
pub const VERSION: &str = "v2";
pub const REQUIRES: &[&str] = &["trend", "volatility", "participation", "history"];
// Declared risk geometry (EXPERT_PROTOCOL §1: risk geometry is "Predeclared
// entry, stop, target, timeout and sizing inputs"; SIMULATION_TRUTH_SPEC D-028:
// R is a declared price distance). Fixed values are declared here, never
// re-literalized inside evaluate(); a structural target/stop is computed at
// the call site and overrides the key.
pub const TARGET_R: f64 = 1.0;
pub const STOP_R: f64 = 1.0;
pub const EXPIRY_BARS: i64 = 8;

const CLIMAX_Z: f64 = 2.0;          // 2-sigma volume overextension (book, N=100)
const CLIMAX_Z_STRICT: f64 = 3.0;   // D-055 strict-climax challenger
const LOW_VOL_PROXIMITY_MAX: f64 = 0.4;
const HIGH_VOL_REVERSAL_BAR: f64 = 1.0; // bar_class value: high-volume reversal bar

pub fn volume_climax_reversal(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    let sym = fm.symbol;
    // _need: close, ema_fast, ema_slow, atr, volume, history — any absent -> NO_HABITAT.
    let close = match fm.value("close") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let fast = match fm.value("ema_fast") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let slow = match fm.value("ema_slow") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let atr = match fm.value("atr") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    let _volume = match fm.value("volume") { Some(v) => v, None => return no_habitat(expert_id, version, fm.as_of) };
    // Empty history or None atr -> NO_HABITAT (the history gate is the non-empty
    // window itself; the "history" feature key rides the same window).
    if fm.history.is_empty() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    // The 100-bar volume-stat features are this family's habitat: a tape
    // without either cannot express a volume-climax predicate at all.
    let zs = fm.value("vol_zscore");
    let prox = fm.value("vol_min_proximity");
    if zs.is_none() && prox.is_none() {
        return no_habitat(expert_id, version, fm.as_of);
    }
    let z_over = zs.is_some_and(|v| v >= CLIMAX_Z);
    let z_strict = zs.is_some_and(|v| v >= CLIMAX_Z_STRICT);
    // _evaluate_variants: first variant whose gate fires, in declared priority
    // order e, d, c, b, a.
    let mut hit: Option<(&str, &str)> = None;
    if z_strict {
        // e: 3-sigma strict climax owns every 3-sigma bar; fade in the trend
        // direction (LONG after a selling climax, SHORT after a buying climax).
        if fast < slow {
            hit = Some(("e", "LONG"));
        } else if fast > slow {
            hit = Some(("e", "SHORT"));
        }
    }
    if hit.is_none() && z_over {
        // d: 2-sigma overextension confirmed by a High-Vol Reversal bar; the
        // reversal bar's own direction decides the fade.
        if let Some(bc) = fm.value("bar_class") {
            if bc == HIGH_VOL_REVERSAL_BAR {
                let o = fm.history.last().unwrap().open;
                if close > o {
                    hit = Some(("d", "LONG"));
                } else if close < o {
                    hit = Some(("d", "SHORT"));
                }
            }
        }
    }
    if hit.is_none() {
        // c: volume near its historical minimum at a local extreme.
        if let Some(p) = prox {
            if p < LOW_VOL_PROXIMITY_MAX {
                if close < slow {
                    hit = Some(("c", "LONG"));
                } else if close > slow {
                    hit = Some(("c", "SHORT"));
                }
            }
        }
    }
    if hit.is_none() && z_over {
        // b: buying-climax top in an uptrend.
        if fast > slow {
            hit = Some(("b", "SHORT"));
        }
    }
    if hit.is_none() && z_over {
        // a: selling-climax bottom in a downtrend.
        if fast < slow {
            hit = Some(("a", "LONG"));
        }
    }
    let (variant, direction) = match hit {
        Some(h) => h,
        None => return no_setup(expert_id, version, fm.as_of),
    };
    // The climax extreme is FROZEN at detection: the selling-climax low (LONG)
    // / buying-climax high (SHORT) of the newest closed bar.
    let last = fm.history.last().unwrap();
    let level = if direction == "LONG" { last.low } else { last.high };
    let ref_key = if direction == "LONG" { "prior_low_ref" } else { "prior_high_ref" };
    // D-026 anchor: the DETECTION bar (the climax bar itself), so a second
    // climax inside one trend re-enters instead of being suppressed as a
    // duplicate (episode_key hashes the anchor).
    let anchor = last.event_id.clone();
    let draft = Draft {
        direction: direction.to_string(),
        birth_time: fm.as_of,
        risk_geometry: geom(vec![
            ("entry", serde_json::json!("NEXT_BAR_CLOSE")),
            ("target_r", serde_json::json!(TARGET_R)),
            ("stop_r", serde_json::json!(STOP_R)),
            ("expiry_bars", serde_json::json!(EXPIRY_BARS)),
            ("atr_ref", serde_json::json!(atr)),
            ("variant", serde_json::json!(variant)),
            (ref_key, serde_json::json!(level)),
        ]),
    };
    let fingerprint = format!("{sym}:{:.6}:{:.6}:{}", close, level, variant);
    candidate(expert_id, version, fm.as_of, draft, anchor, fingerprint)
}
