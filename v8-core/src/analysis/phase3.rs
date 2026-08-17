//! S6 regret phase 3 — recoverability evaluation (issue #120).
//!
//! Port of `tools/regret_phase3.py` (RECOVERABLE_REGRET_PROTOCOL §4 Phase 3,
//! §5) to V8.2. The module is pure computation: it consumes the certified
//! Phase-0 cube rows (discovery/confirmation halves) plus each Candidate's OWN
//! birth-state features (FT001), enumerates the declared decision-time policy
//! class, selects the best policy on the discovery half, and estimates
//! `V_A`, `V_R`, `G_R = V_R - V_A` on the untouched confirmation half with
//! the same block bootstrap as the Python oracle.
//!
//! Parity contract (PARITY_AND_IDENTITY_SPEC §3): every float below is
//! bit-identical to the frozen oracle. `fsum` is CPython's `sum()`,
//! `powf` is libm `pow` (the oracle's `** 2` / `** (1/3)`), the bootstrap
//! draws come from `mt19937` (bit-exact CPython `random.Random`), the policy
//! id embeds `format!("{:.6g}")` — replicated here (`format_g6`) because
//! Rust's default float Display is shortest-roundtrip, not %g. No wall clock,
//! no RNG source other than the per-slice sha1 seed.

use std::collections::HashMap;
use std::path::Path;

use serde_json::{json, Value};
use sha1::Digest as _;

use crate::jsonx;
use crate::mt19937::MT19937;
use crate::state::fsum;

// FCR-V8RR-009 FT002 — frozen, declared BEFORE any slice is scored.
pub const FEATURES: [&str; 3] = ["rsi14", "bb_pct_b", "adx14"];
pub const GATE_DIRECTIONS: [&str; 2] = ["NO_TRADE_BELOW", "NO_TRADE_ABOVE"];
pub const QUANTILES: [f64; 4] = [0.2, 0.4, 0.6, 0.8];

pub const RECOVERABLE_WITHIN_CLASS: &str = "RECOVERABLE_WITHIN_CLASS";
pub const NOT_RECOVERABLE_WITHIN_CLASS: &str = "NOT_RECOVERABLE_WITHIN_CLASS";

// FCR-V8RR-007 FT004/FT007 — shared with phase 2 (frozen constants imported
// from tools.regret_phase2 by the oracle).
pub const N_RESAMPLES: usize = 2000;
pub const CI: f64 = 0.90;
pub const MIN_NET_R: f64 = 0.05;

/// One declared decision-time policy (mirrors `PolicySpec` verbatim).
#[derive(Debug, Clone, PartialEq)]
pub struct PolicySpec {
    pub policy_id: String,
    pub kind: &'static str, // ALWAYS_TRADE | THRESHOLD_GATE
    pub feature: Option<String>,
    pub direction: Option<String>,
    pub threshold: Option<f64>,
}

// ---------------------------------------------------------------------------
// estimators (bit-exact ports; the oracle reuses v8.statistics in full)
// ---------------------------------------------------------------------------

/// CPython `round()` — round-half-even on the exact binary value. Rust's
/// `f64::round` is half-away-from-zero, so the parity port needs this.
fn py_round(x: f64) -> i64 {
    let f = x.floor();
    let frac = x - f;
    if frac > 0.5 {
        (f + 1.0) as i64
    } else if frac < 0.5 {
        f as i64
    } else {
        let fi = f as i64;
        if fi % 2 == 0 {
            fi
        } else {
            fi + 1
        }
    }
}

/// `select_block_size(episode_net_r, threshold=0.10)` (statistics.py D-052):
/// `round(n**(1/3))`, doubled when |lag-1 autocorr| > 0.10, capped at `n//2`.
pub fn select_block_size(episode_net_r: &[f64]) -> usize {
    let threshold = 0.10;
    let n = episode_net_r.len();
    if n < 4 {
        return 1;
    }
    let mean = fsum(episode_net_r) / n as f64;
    let c0 = fsum(
        &episode_net_r
            .iter()
            .map(|x| (x - mean).powf(2.0))
            .collect::<Vec<f64>>(),
    );
    let base = py_round((n as f64).powf(1.0 / 3.0)).max(1) as usize;
    if c0 == 0.0 {
        return base.min(n / 2).max(1);
    }
    let c1 = fsum(
        &(0..n - 1)
            .map(|i| (episode_net_r[i] - mean) * (episode_net_r[i + 1] - mean))
            .collect::<Vec<f64>>(),
    );
    let lag1 = c1 / c0;
    let block = if lag1.abs() > threshold {
        2 * base
    } else {
        base
    };
    block.min(n / 2).max(1)
}

/// One circular fixed-block bootstrap draw of length n (statistics.py
/// `_block_bootstrap_indices`), including the D-052 fail-closed invariant.
fn block_bootstrap_indices(n: usize, block_size: usize, rng: &mut MT19937) -> Vec<usize> {
    if n == 0 {
        return Vec::new();
    }
    assert!(block_size > 0, "block_size must be positive");
    assert!(
        n < 2 || block_size < n,
        "block_size {block_size} >= n {n}: degenerate block bootstrap \
         (every resample is a rotation of the whole series)"
    );
    let mut out = Vec::with_capacity(n + block_size);
    while out.len() < n {
        let start = rng.randrange(n as u64) as usize;
        for j in 0..block_size {
            out.push((start + j) % n);
        }
    }
    out.truncate(n);
    out
}

fn block_bootstrap_means(
    net_rs: &[f64],
    block_size: usize,
    n_resamples: usize,
    seed: u64,
) -> Vec<f64> {
    let n = net_rs.len();
    if n == 0 {
        return Vec::new();
    }
    let mut rng = MT19937::new(seed);
    let mut means = Vec::with_capacity(n_resamples);
    for _ in 0..n_resamples {
        let idx = block_bootstrap_indices(n, block_size, &mut rng);
        let picked: Vec<f64> = idx.iter().map(|&i| net_rs[i]).collect();
        means.push(fsum(&picked) / n as f64);
    }
    means
}

/// `bootstrap_ci(net_r_series, block_size, n_resamples, seed, ci=0.90)` —
/// percentile interval over the sorted resample means.
pub fn bootstrap_ci(
    net_r_series: &[f64],
    block_size: usize,
    n_resamples: usize,
    seed: u64,
    ci: f64,
) -> (f64, f64) {
    assert!((0.0..1.0).contains(&ci), "ci must be in (0, 1)");
    let means = block_bootstrap_means(net_r_series, block_size, n_resamples, seed);
    if means.is_empty() {
        return (0.0, 0.0);
    }
    let mut sorted = means;
    sorted.sort_by(|a, b| a.partial_cmp(b).expect("finite bootstrap means"));
    let tail = ((n_resamples as f64 * (1.0 - ci)) / 2.0) as usize;
    let n = sorted.len();
    (sorted[tail], sorted[n - 1 - tail])
}

/// `_seed_for(key)`: `int(sha1_hex(key)[:8], 16)` where `sha1_hex` is the
/// canonical sha1 of the JSON-encoded string (CPython `json.dumps` of the
/// string — quotes included). Deterministic, never wall-clock (FT004).
pub fn seed_for(suffix_key: &str) -> u64 {
    let canonical = serde_json::to_string(suffix_key).expect("JSON-encodable seed key");
    let mut h = sha1::Sha1::new();
    h.update(canonical.as_bytes());
    let hex: String = h.finalize().iter().map(|b| format!("{b:02x}")).collect();
    u64::from_str_radix(&hex[..8], 16).expect("hex seed")
}

/// Python/printf `%.6g` for the policy id — 6 significant digits, `%e` style
/// when the (rounded) exponent is < -4 or >= 6, else `%f` style, trailing
/// zeros stripped. Built on Rust's correctly-rounded `{:.5e}` so the rounding
/// (incl. round-half-even ties) matches CPython's dtoa.
pub fn format_g6(x: f64) -> String {
    if x.is_nan() {
        return "nan".to_string();
    }
    if x.is_infinite() {
        return if x > 0.0 {
            "inf".to_string()
        } else {
            "-inf".to_string()
        };
    }
    let neg = x.is_sign_negative();
    let sci = format!("{:.5e}", x.abs());
    let (mant, exp) = sci.split_once('e').expect("e-notation split");
    let e: i32 = exp.parse().expect("exponent parse");
    let digits: String = mant.chars().filter(|c| *c != '.').collect();
    let mut out = String::new();
    if neg {
        out.push('-');
    }
    if !(-4..6).contains(&e) {
        out.push_str(&strip_mantissa(mant));
        out.push('e');
        if e < 0 {
            out.push('-');
        } else {
            out.push('+');
        }
        out.push_str(&format!("{:02}", e.abs()));
    } else {
        let (integer, fraction): (String, String) = if e >= 0 {
            let ie = e as usize;
            (digits[..ie + 1].to_string(), digits[ie + 1..].to_string())
        } else {
            let mut f = String::new();
            for _ in 0..(-e - 1) {
                f.push('0');
            }
            f.push_str(&digits);
            ("0".to_string(), f)
        };
        let fraction = fraction.trim_end_matches('0').to_string();
        out.push_str(&integer);
        if !fraction.is_empty() {
            out.push('.');
            out.push_str(&fraction);
        }
    }
    out
}

fn strip_mantissa(mant: &str) -> String {
    let mut s = mant.to_string();
    while s.ends_with('0') {
        s.pop();
    }
    if s.ends_with('.') {
        s.pop();
    }
    s
}

// ---------------------------------------------------------------------------
// birth-state feature extraction (FT001)
// ---------------------------------------------------------------------------

/// `_feature_value`: `state.features["{symbol}.{feature}"]["value"]` as a
/// float; any non-numeric value (null, absent, string) is None.
pub fn feature_value(state_rec: &Value, symbol: &str, feature: &str) -> Option<f64> {
    let feats = state_rec.get("features")?;
    let key = format!("{symbol}.{feature}");
    let fv = feats.get(&key)?;
    fv.get("value").and_then(|v| v.as_f64())
}

fn read_lines(path: &Path) -> Result<Vec<String>, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    Ok(text
        .lines()
        .map(|l| l.to_string())
        .filter(|l| !l.trim().is_empty())
        .collect())
}

/// `_load_birth_features`: candidate_id -> {feature: Option<f64>}, read from
/// each candidate's OWN `birth_state_id` (candidates.jsonl DETECTED edges +
/// states.jsonl), parsed with the Python-json-compatible parser (the store is
/// written by CPython `json.dumps`, which may emit NaN/Infinity literals).
pub fn load_birth_features(
    store_dir: &Path,
    symbol: &str,
) -> Result<HashMap<String, HashMap<&'static str, Option<f64>>>, String> {
    let mut birth_state: HashMap<String, String> = HashMap::new();
    for line in read_lines(&store_dir.join("candidates.jsonl"))? {
        let rec = jsonx::parse_line(&line)
            .map_err(|e| format!("candidates.jsonl: {e}"))?
            .value;
        if rec.get("to_state").and_then(|t| t.as_str()) != Some("DETECTED") {
            continue;
        }
        let cid = rec.get("candidate_id").and_then(|c| c.as_str());
        let sid = rec.get("state_id").and_then(|s| s.as_str());
        if let (Some(cid), Some(sid)) = (cid, sid) {
            birth_state.insert(cid.to_string(), sid.to_string());
        }
    }
    let mut states: HashMap<String, Value> = HashMap::new();
    for line in read_lines(&store_dir.join("states.jsonl"))? {
        let rec = jsonx::parse_line(&line)
            .map_err(|e| format!("states.jsonl: {e}"))?
            .value;
        if let Some(sid) = rec.get("state_id").and_then(|s| s.as_str()) {
            states.insert(sid.to_string(), rec);
        }
    }
    let mut out: HashMap<String, HashMap<&'static str, Option<f64>>> = HashMap::new();
    for (cid, sid) in &birth_state {
        if let Some(st) = states.get(sid) {
            let mut feats: HashMap<&'static str, Option<f64>> = HashMap::new();
            for f in FEATURES {
                feats.insert(f, feature_value(st, symbol, f));
            }
            out.insert(cid.clone(), feats);
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// the declared policy class (FT002) and its application
// ---------------------------------------------------------------------------

/// `declare_policies`: ALWAYS_TRADE + 3*2*4 = 25 policies. Thresholds are the
/// DISCOVERY-half quantile of each feature — computed once per slice, never
/// per-candidate.
pub fn declare_policies(
    discovery_series_by_feature: &HashMap<&'static str, Vec<Option<f64>>>,
) -> Vec<PolicySpec> {
    let mut policies = vec![PolicySpec {
        policy_id: "ALWAYS_TRADE".to_string(),
        kind: "ALWAYS_TRADE",
        feature: None,
        direction: None,
        threshold: None,
    }];
    for feature in FEATURES {
        let mut values: Vec<f64> = discovery_series_by_feature
            .get(feature)
            .map(|v| v.iter().filter_map(|x| *x).collect())
            .unwrap_or_default();
        values.sort_by(|a, b| a.partial_cmp(b).expect("finite feature values"));
        if values.is_empty() {
            continue;
        }
        for q in QUANTILES {
            let idx = ((values.len() as f64) * q) as usize;
            let idx = idx.min(values.len() - 1);
            let threshold = values[idx];
            for direction in GATE_DIRECTIONS {
                let pid = format!(
                    "THRESHOLD_GATE|{feature}|{direction}|{}|q{}",
                    format_g6(threshold),
                    q
                );
                policies.push(PolicySpec {
                    policy_id: pid,
                    kind: "THRESHOLD_GATE",
                    feature: Some(feature.to_string()),
                    direction: Some(direction.to_string()),
                    threshold: Some(threshold),
                });
            }
        }
    }
    policies
}

/// `apply_policy`: THRESHOLD_GATE selects NO_TRADE (utility 0.0) when it
/// fires; a feature unavailable at this clock means the gate cannot fire and
/// the Candidate's already-replayed utility is used.
pub fn apply_policy(
    policy: &PolicySpec,
    feature_values: &HashMap<&'static str, Option<f64>>,
    actual_utility: f64,
) -> f64 {
    if policy.kind == "ALWAYS_TRADE" {
        return actual_utility;
    }
    let feature = match &policy.feature {
        Some(f) => f,
        None => return actual_utility,
    };
    let v = match feature_values.get(feature.as_str()).copied().flatten() {
        Some(v) => v,
        None => return actual_utility,
    };
    let threshold = policy.threshold.unwrap_or(0.0);
    let fires = if policy.direction.as_deref() == Some("NO_TRADE_BELOW") {
        v < threshold
    } else {
        v > threshold
    };
    if fires {
        0.0
    } else {
        actual_utility
    }
}

// ---------------------------------------------------------------------------
// slice evaluation + phase composition
// ---------------------------------------------------------------------------

/// One cube row as consumed by phase 3 (the reduced-row fields that Phase 2
/// certifies; identity strings excluded from value parity).
#[derive(Debug, Clone)]
struct Row {
    expert_id: String,
    symbol: String,
    direction: String,
    gap_status: String,
    actual_utility: f64,
    candidate_id: String,
}

impl Row {
    fn from_value(v: &Value) -> Option<Row> {
        Some(Row {
            expert_id: v.get("expert_id")?.as_str()?.to_string(),
            symbol: v.get("symbol")?.as_str()?.to_string(),
            direction: v.get("direction")?.as_str()?.to_string(),
            gap_status: v.get("gap_status")?.as_str()?.to_string(),
            actual_utility: v.get("actual_utility")?.as_f64()?,
            candidate_id: v.get("candidate_id")?.as_str()?.to_string(),
        })
    }
}

fn rows_for(rows: &[Value], expert_id: &str, symbol: &str, direction: &str) -> Vec<Row> {
    rows.iter()
        .filter_map(Row::from_value)
        .filter(|r| {
            r.expert_id == expert_id
                && r.symbol == symbol
                && r.direction == direction
                && r.gap_status == "COMPUTED"
        })
        .collect()
}

fn policy_json(p: &PolicySpec) -> Value {
    json!({
        "policy_id": p.policy_id,
        "kind": p.kind,
        "feature": p.feature,
        "direction": p.direction,
        "threshold": p.threshold,
    })
}

fn policy_row(slice_key: &str, p: &PolicySpec, n: usize, mean_utility: Option<f64>) -> Value {
    json!({
        "slice_key": slice_key,
        "stage": "discovery_selection",
        "policy_id": p.policy_id,
        "kind": p.kind,
        "feature": p.feature,
        "direction": p.direction,
        "threshold": p.threshold,
        "n": n,
        "mean_utility": mean_utility,
    })
}

/// `evaluate_slice_recoverability`: returns (discovery attempt rows, result).
/// Mirrors the oracle's dict field-for-field; the confirmation half is touched
/// only for `V_A`/`V_R`/`G_R` and the bootstrap.
#[allow(clippy::too_many_arguments)]
pub fn evaluate_slice_recoverability(
    slice_key: &str,
    expert_id: &str,
    symbol: &str,
    direction: &str,
    store_dir: &Path,
    discovery_rows: &[Value],
    confirmation_rows: &[Value],
) -> Result<(Vec<Value>, Value), String> {
    let disc = rows_for(discovery_rows, expert_id, symbol, direction);
    let conf = rows_for(confirmation_rows, expert_id, symbol, direction);
    let birth = load_birth_features(store_dir, symbol)?;
    let feats_of = |cid: &str| -> HashMap<&'static str, Option<f64>> {
        birth.get(cid).cloned().unwrap_or_default()
    };
    let disc_features: Vec<HashMap<&'static str, Option<f64>>> =
        disc.iter().map(|r| feats_of(&r.candidate_id)).collect();
    let disc_series: HashMap<&'static str, Vec<Option<f64>>> = FEATURES
        .iter()
        .map(|f| {
            (
                *f,
                disc.iter()
                    .zip(&disc_features)
                    .map(|(_, m)| m.get(f).copied().flatten())
                    .collect(),
            )
        })
        .collect();
    let policies = declare_policies(&disc_series);

    let mut attempt_rows = Vec::new();
    let mut best_policy: Option<PolicySpec> = None;
    let mut best_mean: Option<f64> = None;
    for policy in &policies {
        let utils: Vec<f64> = disc
            .iter()
            .zip(&disc_features)
            .map(|(r, m)| apply_policy(policy, m, r.actual_utility))
            .collect();
        let mean_u = if utils.is_empty() {
            None
        } else {
            Some(fsum(&utils) / utils.len() as f64)
        };
        attempt_rows.push(policy_row(slice_key, policy, utils.len(), mean_u));
        if let Some(m) = mean_u {
            if best_mean.is_none() || m > best_mean.unwrap() {
                best_mean = Some(m);
                best_policy = Some(policy.clone());
            }
        }
    }

    let conf_features: Vec<HashMap<&'static str, Option<f64>>> =
        conf.iter().map(|r| feats_of(&r.candidate_id)).collect();
    let deltas: Vec<f64> = match &best_policy {
        Some(p) => conf
            .iter()
            .zip(&conf_features)
            .map(|(r, m)| apply_policy(p, m, r.actual_utility) - r.actual_utility)
            .collect(),
        None => Vec::new(),
    };
    let v_a = if conf.is_empty() {
        None
    } else {
        let actuals: Vec<f64> = conf.iter().map(|r| r.actual_utility).collect();
        Some(fsum(&actuals) / conf.len() as f64)
    };
    let g_r = if deltas.is_empty() {
        None
    } else {
        Some(fsum(&deltas) / deltas.len() as f64)
    };
    let v_r = if let (Some(v_a), Some(g_r)) = (v_a, g_r) {
        Some(v_a + g_r)
    } else {
        None
    };

    let (ci_lower, ci_upper) = if !deltas.is_empty() && deltas.iter().any(|d| *d != 0.0) {
        let block = select_block_size(&deltas);
        let seed = seed_for(&format!("{slice_key}|phase3"));
        bootstrap_ci(&deltas, block, N_RESAMPLES, seed, CI)
    } else {
        (0.0, 0.0)
    };

    let verdict = if g_r.is_some() && ci_lower > 0.0 && g_r.unwrap() >= MIN_NET_R {
        RECOVERABLE_WITHIN_CLASS
    } else {
        NOT_RECOVERABLE_WITHIN_CLASS
    };

    let result = json!({
        "slice_key": slice_key,
        "expert_id": expert_id,
        "symbol": symbol,
        "direction": direction,
        "n_discovery": disc.len(),
        "n_confirmation": conf.len(),
        "selected_policy": best_policy.as_ref().map(policy_json).unwrap_or(Value::Null),
        "discovery_selection_mean_utility": best_mean,
        "confirmation_v_a": v_a,
        "confirmation_v_r": v_r,
        "confirmation_g_r": g_r,
        "confirmation_g_r_ci_lower": ci_lower,
        "confirmation_g_r_ci_upper": ci_upper,
        "recoverability_verdict": verdict,
    });
    Ok((attempt_rows, result))
}

fn append_jsonl(path: &Path, rows: &[Value]) -> Result<(), String> {
    use std::io::Write;
    let mut text = String::new();
    for r in rows {
        text.push_str(&serde_json::to_string(r).map_err(|e| e.to_string())?);
        text.push('\n');
    }
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| format!("open {}: {e}", path.display()))?;
    file.write_all(text.as_bytes())
        .map_err(|e| format!("write {}: {e}", path.display()))?;
    Ok(())
}

/// `run_phase3`: compose per-slice recoverability over the confirmed slice
/// keys, append the attempt ledger, and write `phase3_summary.json`.
pub fn run_phase3(
    confirmed_slice_keys: &[String],
    discovery_rows: &[Value],
    confirmation_rows: &[Value],
    store_dirs: &HashMap<String, String>,
    out_dir: &Path,
) -> Result<Value, String> {
    std::fs::create_dir_all(out_dir).map_err(|e| format!("out_dir: {e}"))?;
    let mut results: Vec<Value> = Vec::new();
    let mut all_rows: Vec<Value> = Vec::new();
    for key in confirmed_slice_keys {
        let parts: Vec<&str> = key.split('|').collect();
        if parts.len() < 4 {
            return Err(format!(
                "bad slice_key {key:?}: expected expert|symbol|direction|estimand"
            ));
        }
        let (expert_id, symbol, direction) = (parts[0], parts[1], parts[2]);
        let store_dir = store_dirs
            .get(symbol)
            .ok_or_else(|| format!("no store_dir for symbol {symbol}"))?;
        let (attempts, result) = evaluate_slice_recoverability(
            key,
            expert_id,
            symbol,
            direction,
            Path::new(store_dir),
            discovery_rows,
            confirmation_rows,
        )?;
        all_rows.extend(attempts);
        let mut conf_row = result.clone();
        conf_row
            .as_object_mut()
            .expect("result is an object")
            .insert(
                "stage".to_string(),
                Value::String("confirmation_result".to_string()),
            );
        all_rows.push(conf_row);
        results.push(result);
    }
    append_jsonl(&out_dir.join("recoverability_attempts.jsonl"), &all_rows)?;

    let recoverable: Vec<&Value> = results
        .iter()
        .filter(|r| {
            r.get("recoverability_verdict").and_then(|v| v.as_str())
                == Some(RECOVERABLE_WITHIN_CLASS)
        })
        .collect();
    let summary = json!({
        "n_slices_tested": results.len(),
        "n_recoverable_within_class": recoverable.len(),
        "n_not_recoverable_within_class": results.len() - recoverable.len(),
        "recoverable_slices": recoverable
            .iter()
            .map(|r| r.get("slice_key").cloned().unwrap_or(Value::Null))
            .collect::<Vec<Value>>(),
        "results": results,
    });
    let text = serde_json::to_string_pretty(&summary).map_err(|e| e.to_string())?;
    std::fs::write(out_dir.join("phase3_summary.json"), text + "\n")
        .map_err(|e| format!("write phase3_summary.json: {e}"))?;
    Ok(summary)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Write as _;
    use std::path::PathBuf;

    // -----------------------------------------------------------------
    // Reference constants captured from the frozen oracle
    // (tools/regret_phase3.py via .venv/bin/python on synthetic input).
    // -----------------------------------------------------------------

    const POLICIES_JSON: &str = r#"[
{"direction":null,"feature":null,"kind":"ALWAYS_TRADE","policy_id":"ALWAYS_TRADE","threshold":null},
{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|42|q0.2","threshold":42.0},
{"direction":"NO_TRADE_ABOVE","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_ABOVE|42|q0.2","threshold":42.0},
{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|55|q0.4","threshold":55.0},
{"direction":"NO_TRADE_ABOVE","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_ABOVE|55|q0.4","threshold":55.0},
{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|65|q0.6","threshold":65.0},
{"direction":"NO_TRADE_ABOVE","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_ABOVE|65|q0.6","threshold":65.0},
{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|68.5|q0.8","threshold":68.5},
{"direction":"NO_TRADE_ABOVE","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_ABOVE|68.5|q0.8","threshold":68.5},
{"direction":"NO_TRADE_BELOW","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_BELOW|0.3|q0.2","threshold":0.3},
{"direction":"NO_TRADE_ABOVE","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_ABOVE|0.3|q0.2","threshold":0.3},
{"direction":"NO_TRADE_BELOW","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_BELOW|0.6|q0.4","threshold":0.6},
{"direction":"NO_TRADE_ABOVE","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_ABOVE|0.6|q0.4","threshold":0.6},
{"direction":"NO_TRADE_BELOW","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_BELOW|0.73|q0.6","threshold":0.73},
{"direction":"NO_TRADE_ABOVE","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_ABOVE|0.73|q0.6","threshold":0.73},
{"direction":"NO_TRADE_BELOW","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_BELOW|0.85|q0.8","threshold":0.85},
{"direction":"NO_TRADE_ABOVE","feature":"bb_pct_b","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|bb_pct_b|NO_TRADE_ABOVE|0.85|q0.8","threshold":0.85},
{"direction":"NO_TRADE_BELOW","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_BELOW|15.5|q0.2","threshold":15.5},
{"direction":"NO_TRADE_ABOVE","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_ABOVE|15.5|q0.2","threshold":15.5},
{"direction":"NO_TRADE_BELOW","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_BELOW|22|q0.4","threshold":22.0},
{"direction":"NO_TRADE_ABOVE","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_ABOVE|22|q0.4","threshold":22.0},
{"direction":"NO_TRADE_BELOW","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_BELOW|25.5|q0.6","threshold":25.5},
{"direction":"NO_TRADE_ABOVE","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_ABOVE|25.5|q0.6","threshold":25.5},
{"direction":"NO_TRADE_BELOW","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_BELOW|35|q0.8","threshold":35.0},
{"direction":"NO_TRADE_ABOVE","feature":"adx14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|adx14|NO_TRADE_ABOVE|35|q0.8","threshold":35.0}
]"#;

    const RESULT1_JSON: &str = r#"{
"confirmation_g_r":0.1125,"confirmation_g_r_ci_lower":0.025,"confirmation_g_r_ci_upper":0.2,
"confirmation_v_a":-0.018749999999999996,"confirmation_v_r":0.09375,
"direction":"LONG","discovery_selection_mean_utility":0.20625,
"expert_id":"trend_pullback","n_confirmation":8,"n_discovery":8,
"recoverability_verdict":"RECOVERABLE_WITHIN_CLASS",
"selected_policy":{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|55|q0.4","threshold":55.0},
"slice_key":"trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap","symbol":"BTCUSDT"}"#;

    const RESULT2_JSON: &str = r#"{
"confirmation_g_r":0.0,"confirmation_g_r_ci_lower":0.0,"confirmation_g_r_ci_upper":0.0,
"confirmation_v_a":0.0,"confirmation_v_r":0.0,
"direction":"SHORT","discovery_selection_mean_utility":0.14,
"expert_id":"failed_breakout","n_confirmation":5,"n_discovery":5,
"recoverability_verdict":"NOT_RECOVERABLE_WITHIN_CLASS",
"selected_policy":{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|50|q0.4","threshold":50.0},
"slice_key":"failed_breakout|SOLUSDT|SHORT|mean_legal_hindsight_gap","symbol":"SOLUSDT"}"#;

    const SUMMARY_JSON: &str = r#"{
"n_not_recoverable_within_class":1,"n_recoverable_within_class":1,"n_slices_tested":2,
"recoverable_slices":["trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap"],
"results":[
{"confirmation_g_r":0.1125,"confirmation_g_r_ci_lower":0.025,"confirmation_g_r_ci_upper":0.2,"confirmation_v_a":-0.018749999999999996,"confirmation_v_r":0.09375,"direction":"LONG","discovery_selection_mean_utility":0.20625,"expert_id":"trend_pullback","n_confirmation":8,"n_discovery":8,"recoverability_verdict":"RECOVERABLE_WITHIN_CLASS","selected_policy":{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|55|q0.4","threshold":55.0},"slice_key":"trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap","symbol":"BTCUSDT"},
{"confirmation_g_r":0.0,"confirmation_g_r_ci_lower":0.0,"confirmation_g_r_ci_upper":0.0,"confirmation_v_a":0.0,"confirmation_v_r":0.0,"direction":"SHORT","discovery_selection_mean_utility":0.14,"expert_id":"failed_breakout","n_confirmation":5,"n_discovery":5,"recoverability_verdict":"NOT_RECOVERABLE_WITHIN_CLASS","selected_policy":{"direction":"NO_TRADE_BELOW","feature":"rsi14","kind":"THRESHOLD_GATE","policy_id":"THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|50|q0.4","threshold":50.0},"slice_key":"failed_breakout|SOLUSDT|SHORT|mean_legal_hindsight_gap","symbol":"SOLUSDT"}
]}"#;

    const BIRTH_BTC_JSON: &str = r#"{
"btc-c0":{"adx14":12.0,"bb_pct_b":0.2,"rsi14":30.0},
"btc-c1":{"adx14":35.0,"bb_pct_b":0.85,"rsi14":65.0},
"btc-c2":{"adx14":15.5,"bb_pct_b":0.3,"rsi14":48.0},
"btc-c3":{"adx14":40.0,"bb_pct_b":0.9,"rsi14":70.25},
"btc-c4":{"adx14":null,"bb_pct_b":0.45,"rsi14":42.0},
"btc-c5":{"adx14":22.0,"bb_pct_b":0.6,"rsi14":55.0},
"btc-c6":{"adx14":30.0,"bb_pct_b":0.73456,"rsi14":58.5},
"btc-c7":{"adx14":25.5,"bb_pct_b":0.73,"rsi14":68.5},
"btc-s0":{"adx14":25.5,"bb_pct_b":0.73,"rsi14":68.5},
"btc-s1":{"adx14":18.0,"bb_pct_b":0.45,"rsi14":42.0},
"btc-s2":{"adx14":40.0,"bb_pct_b":0.9,"rsi14":70.25},
"btc-s3":{"adx14":12.0,"bb_pct_b":0.2,"rsi14":55.0},
"btc-s4":{"adx14":30.0,"bb_pct_b":0.6,"rsi14":30.0},
"btc-s5":{"adx14":22.0,"bb_pct_b":0.73456,"rsi14":65.0},
"btc-s6":{"adx14":15.5,"bb_pct_b":0.3,"rsi14":null},
"btc-s7":{"adx14":35.0,"bb_pct_b":0.85,"rsi14":58.5}}"#;

    const BIRTH_SOL_JSON: &str = r#"{
"sol-s0":{"adx14":20.0,"bb_pct_b":0.5,"rsi14":50.0},
"sol-s1":{"adx14":15.0,"bb_pct_b":0.3,"rsi14":40.0},
"sol-s2":{"adx14":25.0,"bb_pct_b":0.7,"rsi14":60.0},
"sol-s3":{"adx14":18.0,"bb_pct_b":0.4,"rsi14":45.0},
"sol-s4":{"adx14":22.0,"bb_pct_b":0.6,"rsi14":55.0},
"sol-t0":{"adx14":16.0,"bb_pct_b":0.35,"rsi14":42.0},
"sol-t1":{"adx14":28.0,"bb_pct_b":0.75,"rsi14":58.0},
"sol-t2":{"adx14":19.0,"bb_pct_b":0.45,"rsi14":48.0},
"sol-t3":{"adx14":30.0,"bb_pct_b":0.8,"rsi14":63.0},
"sol-t4":{"adx14":21.0,"bb_pct_b":0.55,"rsi14":52.0}}"#;

    // Captured: `select_block_size(deltas1)` = 4; `bootstrap_ci(..., seed1)` = (0.025, 0.2).
    const DELTAS1: [f64; 8] = [0.3, 0.0, 0.5, 0.0, 0.1, 0.0, 0.0, 0.0];
    const SEED1: u64 = 3216311728;
    const SEED2: u64 = 674598930;

    // (value, '%.6g' % value) captured from CPython 3.14.
    const G_BATTERY: &[(f64, &str)] = &[
        (-0.5, "-0.5"),
        (0.0001, "0.0001"),
        (0.2, "0.2"),
        (0.3333333333333333, "0.333333"),
        (0.4, "0.4"),
        (0.5, "0.5"),
        (0.6, "0.6"),
        (0.73, "0.73"),
        (0.73456, "0.73456"),
        (0.8, "0.8"),
        (0.9999999, "1"),
        (1.0, "1"),
        (1.23456789012345, "1.23457"),
        (1.23456789e-05, "1.23457e-05"),
        (1000000.0, "1e+06"),
        (12.345678, "12.3457"),
        (1234.5, "1234.5"),
        (123456789.0, "1.23457e+08"),
        (1e-05, "1e-05"),
        (1e-08, "1e-08"),
        (2.0, "2"),
        (2.5, "2.5"),
        (3.0, "3"),
        (3.5, "3.5"),
        (42.0, "42"),
        (55.0, "55"),
        (68.5, "68.5"),
        (7.5, "7.5"),
        (999999.0, "999999"),
        (1.234565, "1.23456"),
        (1.234575, "1.23457"),
        (1234567.0, "1.23457e+06"),
        (-0.0, "-0"),
        (0.0, "0"),
        (999999.95, "1e+06"),
        (0.30000000000000004, "0.3"),
        (100.0, "100"),
        (10.0, "10"),
        (0.000123456, "0.000123456"),
        (123456.5, "123456"),
    ];

    // -----------------------------------------------------------------
    // synthetic store fixture (identical to the capture script's)
    // -----------------------------------------------------------------

    fn features_map(
        symbol: &str,
        rsi: Option<f64>,
        bb: Option<f64>,
        adx: Option<f64>,
    ) -> serde_json::Map<String, Value> {
        let mut m = serde_json::Map::new();
        m.insert(format!("{symbol}.rsi14"), json!({"value": rsi}));
        m.insert(format!("{symbol}.bb_pct_b"), json!({"value": bb}));
        if let Some(v) = adx {
            m.insert(format!("{symbol}.adx14"), json!({"value": v}));
        }
        m
    }

    const BTC_STATES: &[(&str, Option<f64>, Option<f64>, Option<f64>)] = &[
        ("btc-s0", Some(68.5), Some(0.73), Some(25.5)),
        ("btc-s1", Some(42.0), Some(0.45), Some(18.0)),
        ("btc-s2", Some(70.25), Some(0.9), Some(40.0)),
        ("btc-s3", Some(55.0), Some(0.2), Some(12.0)),
        ("btc-s4", Some(30.0), Some(0.6), Some(30.0)),
        ("btc-s5", Some(65.0), Some(0.73456), Some(22.0)),
        ("btc-s6", None, Some(0.3), Some(15.5)),
        ("btc-s7", Some(58.5), Some(0.85), Some(35.0)),
        ("btc-c0", Some(30.0), Some(0.2), Some(12.0)),
        ("btc-c1", Some(65.0), Some(0.85), Some(35.0)),
        ("btc-c2", Some(48.0), Some(0.3), Some(15.5)),
        ("btc-c3", Some(70.25), Some(0.9), Some(40.0)),
        ("btc-c4", Some(42.0), Some(0.45), None),
        ("btc-c5", Some(55.0), Some(0.6), Some(22.0)),
        ("btc-c6", Some(58.5), Some(0.73456), Some(30.0)),
        ("btc-c7", Some(68.5), Some(0.73), Some(25.5)),
    ];

    const SOL_STATES: &[(&str, Option<f64>, Option<f64>, Option<f64>)] = &[
        ("sol-s0", Some(50.0), Some(0.5), Some(20.0)),
        ("sol-s1", Some(40.0), Some(0.3), Some(15.0)),
        ("sol-s2", Some(60.0), Some(0.7), Some(25.0)),
        ("sol-s3", Some(45.0), Some(0.4), Some(18.0)),
        ("sol-s4", Some(55.0), Some(0.6), Some(22.0)),
        ("sol-t0", Some(42.0), Some(0.35), Some(16.0)),
        ("sol-t1", Some(58.0), Some(0.75), Some(28.0)),
        ("sol-t2", Some(48.0), Some(0.45), Some(19.0)),
        ("sol-t3", Some(63.0), Some(0.8), Some(30.0)),
        ("sol-t4", Some(52.0), Some(0.55), Some(21.0)),
    ];

    fn write_store(
        dir: &Path,
        symbol: &str,
        states: &[(&str, Option<f64>, Option<f64>, Option<f64>)],
    ) {
        std::fs::create_dir_all(dir).unwrap();
        let mut states_f = File::create(dir.join("states.jsonl")).unwrap();
        for (sid, rsi, bb, adx) in states {
            let rec = json!({
                "source": "phase3-capture",
                "event_id": sid.to_string(),
                "state_id": sid.to_string(),
                "features": features_map(symbol, *rsi, *bb, *adx),
            });
            writeln!(states_f, "{}", serde_json::to_string(&rec).unwrap()).unwrap();
        }
        let mut cand_f = File::create(dir.join("candidates.jsonl")).unwrap();
        for (sid, _, _, _) in states {
            let rec = json!({
                "source": "phase3-capture",
                "event_id": format!("cand-{sid}"),
                "candidate_id": sid.to_string(),
                "state_id": sid.to_string(),
                "to_state": "DETECTED",
            });
            writeln!(cand_f, "{}", serde_json::to_string(&rec).unwrap()).unwrap();
        }
    }

    fn row(cid: &str, expert: &str, symbol: &str, direction: &str, u: f64) -> Value {
        json!({
            "expert_id": expert,
            "symbol": symbol,
            "direction": direction,
            "gap_status": "COMPUTED",
            "actual_utility": u,
            "candidate_id": cid,
        })
    }

    /// Build the full fixture; returns (btc_dir, sol_dir, all discovery rows,
    /// all confirmation rows). `tag` keeps parallel tests on disjoint dirs
    /// (the store files are truncated on write, so a shared path would race).
    fn fixture(tag: &str) -> (PathBuf, PathBuf, Vec<Value>, Vec<Value>) {
        let base = std::env::temp_dir().join(format!("v8core-phase3-{tag}-{}", std::process::id()));
        let btc = base.join("BTCUSDT");
        let sol = base.join("SOLUSDT");
        write_store(&btc, "BTCUSDT", BTC_STATES);
        write_store(&sol, "SOLUSDT", SOL_STATES);

        let disc1_u = [0.5, -0.2, 0.3, 0.1, -0.4, 0.6, -0.1, 0.25];
        let conf1_u = [-0.3, 0.2, -0.5, 0.4, -0.1, 0.35, 0.05, -0.25];
        let disc2_u = [0.2, -0.3, 0.4, -0.1, 0.1];
        let conf2_u = [0.0, 0.0, 0.0, 0.0, 0.0];

        let mut disc_all = Vec::new();
        let mut conf_all = Vec::new();
        for (i, u) in disc1_u.iter().enumerate() {
            disc_all.push(row(
                &format!("btc-s{i}"),
                "trend_pullback",
                "BTCUSDT",
                "LONG",
                *u,
            ));
        }
        for (i, u) in conf1_u.iter().enumerate() {
            conf_all.push(row(
                &format!("btc-c{i}"),
                "trend_pullback",
                "BTCUSDT",
                "LONG",
                *u,
            ));
        }
        for (i, u) in disc2_u.iter().enumerate() {
            disc_all.push(row(
                &format!("sol-s{i}"),
                "failed_breakout",
                "SOLUSDT",
                "SHORT",
                *u,
            ));
        }
        for (i, u) in conf2_u.iter().enumerate() {
            conf_all.push(row(
                &format!("sol-t{i}"),
                "failed_breakout",
                "SOLUSDT",
                "SHORT",
                *u,
            ));
        }
        (btc, sol, disc_all, conf_all)
    }

    fn birth_to_value(b: &HashMap<String, HashMap<&'static str, Option<f64>>>) -> Value {
        let mut m = serde_json::Map::new();
        for (cid, feats) in b {
            let mut fm = serde_json::Map::new();
            for f in FEATURES.iter().copied() {
                fm.insert(f.to_string(), json!(feats.get(f).copied().flatten()));
            }
            m.insert(cid.clone(), Value::Object(fm));
        }
        Value::Object(m)
    }

    fn policies_to_value(p: &[PolicySpec]) -> Value {
        Value::Array(p.iter().map(policy_json).collect())
    }

    // -----------------------------------------------------------------
    // tests
    // -----------------------------------------------------------------

    #[test]
    fn format_g6_matches_cpython_percent_g() {
        for &(v, want) in G_BATTERY {
            assert_eq!(format_g6(v), want, "%.6g of {v}");
        }
    }

    #[test]
    fn seed_for_matches_oracle() {
        assert_eq!(
            seed_for("trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap|phase3"),
            SEED1
        );
        assert_eq!(
            seed_for("failed_breakout|SOLUSDT|SHORT|mean_legal_hindsight_gap|phase3"),
            SEED2
        );
    }

    #[test]
    fn select_block_size_and_bootstrap_ci_match_oracle() {
        assert_eq!(select_block_size(&DELTAS1), 4);
        let (lo, hi) = bootstrap_ci(&DELTAS1, 4, N_RESAMPLES, SEED1, CI);
        assert_eq!(lo, 0.025);
        assert_eq!(hi, 0.2);
        // small-n rule: n < 4 -> 1
        assert_eq!(select_block_size(&[0.5]), 1);
        assert_eq!(select_block_size(&[0.3, -0.1, 0.2]), 1);
        // zero-variance series -> the constant c0==0 branch, block = base
        let flat = vec![0.25; 27];
        assert_eq!(select_block_size(&flat), 3);
    }

    #[test]
    fn birth_features_match_oracle() {
        let (btc, sol, _, _) = fixture("birth");
        let birth_btc = load_birth_features(&btc, "BTCUSDT").unwrap();
        let birth_sol = load_birth_features(&sol, "SOLUSDT").unwrap();
        assert_eq!(
            birth_to_value(&birth_btc),
            serde_json::from_str::<Value>(BIRTH_BTC_JSON).unwrap()
        );
        assert_eq!(
            birth_to_value(&birth_sol),
            serde_json::from_str::<Value>(BIRTH_SOL_JSON).unwrap()
        );
        // btc-s6 has rsi14 absent and btc-c4 has adx14 absent -> None
        assert_eq!(birth_btc["btc-s6"].get("rsi14").copied().flatten(), None);
        assert_eq!(birth_btc["btc-c4"].get("adx14").copied().flatten(), None);
    }

    #[test]
    fn declare_policies_matches_oracle() {
        let (btc, _, disc_all, _) = fixture("policies");
        let birth = load_birth_features(&btc, "BTCUSDT").unwrap();
        let disc: Vec<Row> = rows_for(&disc_all, "trend_pullback", "BTCUSDT", "LONG");
        let feats = |cid: &str| birth.get(cid).cloned().unwrap_or_default();
        let series: HashMap<&'static str, Vec<Option<f64>>> = FEATURES
            .iter()
            .copied()
            .map(|f| {
                (
                    f,
                    disc.iter()
                        .map(|r| feats(&r.candidate_id).get(f).copied().flatten())
                        .collect(),
                )
            })
            .collect();
        let policies = declare_policies(&series);
        assert_eq!(policies.len(), 25);
        assert_eq!(
            policies_to_value(&policies),
            serde_json::from_str::<Value>(POLICIES_JSON).unwrap()
        );
        // ALWAYS_TRADE is always element 0
        assert_eq!(policies[0].policy_id, "ALWAYS_TRADE");
        assert_eq!(policies[0].kind, "ALWAYS_TRADE");
    }

    #[test]
    fn apply_policy_matches_oracle() {
        let gate: PolicySpec = PolicySpec {
            policy_id: "THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|42|q0.2".to_string(),
            kind: "THRESHOLD_GATE",
            feature: Some("rsi14".to_string()),
            direction: Some("NO_TRADE_BELOW".to_string()),
            threshold: Some(42.0),
        };
        let always: PolicySpec = PolicySpec {
            policy_id: "ALWAYS_TRADE".to_string(),
            kind: "ALWAYS_TRADE",
            feature: None,
            direction: None,
            threshold: None,
        };
        let m = |rsi: Option<f64>,
                 bb: Option<f64>,
                 adx: Option<f64>|
         -> HashMap<&'static str, Option<f64>> {
            let mut h = HashMap::new();
            h.insert("rsi14", rsi);
            h.insert("bb_pct_b", bb);
            h.insert("adx14", adx);
            h
        };
        // captured cases
        assert_eq!(
            apply_policy(&always, &m(Some(68.5), Some(0.73), Some(25.5)), 0.5),
            0.5
        );
        assert_eq!(
            apply_policy(&always, &m(None, Some(0.3), Some(15.5)), 0.5),
            0.5
        );
        assert_eq!(
            apply_policy(&gate, &m(Some(68.5), Some(0.73), Some(25.5)), 0.5),
            0.5
        );
        assert_eq!(
            apply_policy(&gate, &m(None, Some(0.3), Some(15.5)), 0.5),
            0.5
        );
        assert_eq!(
            apply_policy(&gate, &m(Some(42.0), Some(0.45), Some(18.0)), 0.5),
            0.5
        );
        // a firing gate returns 0.0 (cross-checked by DELTAS1: btc-c0 rsi=30 fires)
        let gate55: PolicySpec = PolicySpec {
            policy_id: "THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|55|q0.4".to_string(),
            kind: "THRESHOLD_GATE",
            feature: Some("rsi14".to_string()),
            direction: Some("NO_TRADE_BELOW".to_string()),
            threshold: Some(55.0),
        };
        assert_eq!(
            apply_policy(&gate55, &m(Some(30.0), Some(0.6), Some(30.0)), -0.4),
            0.0
        );
        // NO_TRADE_ABOVE fires above the threshold
        let gate_above: PolicySpec = PolicySpec {
            policy_id: "THRESHOLD_GATE|rsi14|NO_TRADE_ABOVE|55|q0.4".to_string(),
            kind: "THRESHOLD_GATE",
            feature: Some("rsi14".to_string()),
            direction: Some("NO_TRADE_ABOVE".to_string()),
            threshold: Some(55.0),
        };
        assert_eq!(
            apply_policy(&gate_above, &m(Some(68.5), Some(0.73), Some(25.5)), 0.5),
            0.0
        );
        assert_eq!(
            apply_policy(&gate_above, &m(Some(42.0), Some(0.45), Some(18.0)), 0.5),
            0.5
        );
    }

    #[test]
    fn evaluate_slice_recoverability_matches_oracle() {
        let (btc, sol, disc_all, conf_all) = fixture("eval");
        let key1 = "trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap";
        let (attempts1, r1) = evaluate_slice_recoverability(
            key1,
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            &btc,
            &disc_all,
            &conf_all,
        )
        .unwrap();
        assert_eq!(r1, serde_json::from_str::<Value>(RESULT1_JSON).unwrap());
        // 1 ALWAYS_TRADE + 24 THRESHOLD_GATE discovery rows
        assert_eq!(attempts1.len(), 25);
        assert_eq!(attempts1[0]["policy_id"], "ALWAYS_TRADE");
        assert_eq!(
            attempts1[0]["mean_utility"].as_f64().unwrap(),
            0.13124999999999998
        );
        // the best policy's discovery row
        let best_row = attempts1
            .iter()
            .find(|a| a["policy_id"] == "THRESHOLD_GATE|rsi14|NO_TRADE_BELOW|55|q0.4")
            .expect("best policy row present");
        assert_eq!(best_row["mean_utility"].as_f64().unwrap(), 0.20625);

        let key2 = "failed_breakout|SOLUSDT|SHORT|mean_legal_hindsight_gap";
        let (_attempts2, r2) = evaluate_slice_recoverability(
            key2,
            "failed_breakout",
            "SOLUSDT",
            "SHORT",
            &sol,
            &disc_all,
            &conf_all,
        )
        .unwrap();
        assert_eq!(r2, serde_json::from_str::<Value>(RESULT2_JSON).unwrap());
    }

    #[test]
    fn run_phase3_matches_oracle() {
        let (btc, sol, disc_all, conf_all) = fixture("run");
        let keys: Vec<String> = vec![
            "trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap".to_string(),
            "failed_breakout|SOLUSDT|SHORT|mean_legal_hindsight_gap".to_string(),
        ];
        let store_dirs = HashMap::from([
            ("BTCUSDT".to_string(), btc.to_string_lossy().to_string()),
            ("SOLUSDT".to_string(), sol.to_string_lossy().to_string()),
        ]);
        let out_dir = std::env::temp_dir().join(format!(
            "v8core-phase3-out-{}-{}",
            "run",
            std::process::id()
        ));
        let summary = run_phase3(&keys, &disc_all, &conf_all, &store_dirs, &out_dir).unwrap();
        assert_eq!(
            summary,
            serde_json::from_str::<Value>(SUMMARY_JSON).unwrap()
        );
        // both artifacts are written (attempt ledger + summary)
        assert!(out_dir.join("recoverability_attempts.jsonl").exists());
        assert!(out_dir.join("phase3_summary.json").exists());
        let attempts_text =
            std::fs::read_to_string(out_dir.join("recoverability_attempts.jsonl")).unwrap();
        let n_lines = attempts_text
            .lines()
            .filter(|l| !l.trim().is_empty())
            .count();
        // 25 discovery attempts + 1 confirmation result per slice
        assert_eq!(n_lines, 52);
    }
}
