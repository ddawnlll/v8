//! S7 verdict statistics (D-091; COMPUTE_CORE_SPEC §6): block-bootstrap
//! Reality-Check, detrended null, METH-3..METH-6. Consumes mt19937 for
//! bit-exact seeded RNG parity.
//!
//! The `verdict` subcommand reads one evaluation request — either an episode
//! net_R series supplied directly (`{net_r: [...], config: ..., seed: ...}`)
//! or the cube-reduced artifact (`{out_dir: ...}`) — and prints the verdict
//! JSON: the WRC max-statistic p-value (issue #128), the Appendix A
//! detrended-null invariant (issue #124), and the METH-2..6 surface (issue
//! #129). No wall clock ever enters a verdict (G5); every bootstrap /
//! permutation / placebo draw is seeded from the request, never the clock.

pub mod detrended;
pub mod reality_check;
pub mod remaining;

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde_json::Value;

use crate::regret;

/// The verdict's economic claim until a statistics verdict and an authority
/// receipt exist (rule 12 — never a claimed edge); mirrors
/// `report::REPORT_VERDICT`. The statistics themselves are reported beside it
/// without ever upgrading the claim.
pub const VERDICT_NO_ECONOMIC_CLAIM: &str = "NO_ECONOMIC_CLAIM";

/// The lag-1 autocorrelation threshold of the block-size mechanical rule
/// (prereg §9; the oracle's default `threshold=0.10`).
pub const BLOCK_SIZE_THRESHOLD: f64 = 0.10;

/// The cube-reduced artifact filename an `out_dir`-mode request reads.
pub const CUBE_REDUCED_FILENAME: &str = "cube-reduced.v82";

/// The verdict request. The family series comes from one of three sources:
/// `configs` (a multi-config family map), `net_r` + `config` (one
/// configuration's episode series), or `out_dir` (the cube-reduced artifact's
/// COMPUTED `legal_hindsight_gap` series). `seed` is required — the oracle's
/// draws are always seeded, never the wall clock (PERSISTENCE_REPLAY_SPEC
/// section 4).
///
/// Every statistic section is optional in the sense that the driver emits it
/// with the same schema whether or not the request supplied the extra inputs
/// (`closes` + placebo params for the detrended null, `moves` + `directions`
/// for the METH-3 null); a section whose inputs are absent is emitted as
/// `{"run": false}` rather than omitted, so the schema is stable.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct VerdictRequest {
    #[serde(default)]
    pub net_r: Vec<f64>,
    #[serde(default = "default_config")]
    pub config: String,
    #[serde(default)]
    pub configs: HashMap<String, Vec<f64>>,
    pub seed: u64,
    #[serde(default = "default_n_resamples")]
    pub n_resamples: i64,
    /// Optional block-size override; absent => the §9 mechanical rule
    /// (`select_block_size` with `BLOCK_SIZE_THRESHOLD`).
    #[serde(default)]
    pub block_size: Option<i64>,
    #[serde(default)]
    pub out_dir: Option<PathBuf>,
    // Detrended null / Appendix A placebo family (optional).
    #[serde(default)]
    pub closes: Vec<f64>,
    #[serde(default = "default_long_share")]
    pub long_share: f64,
    #[serde(default = "default_horizon_bars")]
    pub horizon_bars: i64,
    #[serde(default = "default_risk_unit_frac")]
    pub risk_unit_frac: f64,
    #[serde(default = "default_n_placebo")]
    pub n_placebo: usize,
    // METH-3 permutation null (optional).
    #[serde(default)]
    pub moves: Vec<f64>,
    #[serde(default)]
    pub directions: HashMap<String, Vec<i32>>,
    #[serde(default = "default_n_permutations")]
    pub n_permutations: u64,
    // METH-4.
    #[serde(default = "default_ci")]
    pub ci: f64,
    #[serde(default = "default_max_hold_bars")]
    pub max_hold_bars: u64,
    // METH-5.
    #[serde(default = "default_slice_bars")]
    pub slice_bars: usize,
    #[serde(default = "default_min_net_r")]
    pub min_net_r: f64,
    #[serde(default = "default_min_trades")]
    pub min_trades: u64,
    // METH-6 / METH-2.
    #[serde(default = "default_alpha")]
    pub alpha: f64,
    /// Number of rules for the expected-false-positive count; defaults to the
    /// family size (the evaluated configurations).
    #[serde(default)]
    pub n_rules: Option<u64>,
    /// The total search extent (D-046); defaults to `variants_evaluated` so a
    /// request that does not declare one reports no multiplicity undercount.
    #[serde(default)]
    pub search_universe_size: Option<u64>,
}

fn default_config() -> String {
    "v1".to_string()
}
fn default_n_resamples() -> i64 {
    2000
}
fn default_long_share() -> f64 {
    0.65
}
fn default_horizon_bars() -> i64 {
    8
}
fn default_risk_unit_frac() -> f64 {
    0.01
}
fn default_n_placebo() -> usize {
    200
}
fn default_n_permutations() -> u64 {
    2000
}
fn default_ci() -> f64 {
    0.90
}
fn default_max_hold_bars() -> u64 {
    8
}
fn default_slice_bars() -> usize {
    8
}
fn default_min_net_r() -> f64 {
    0.05
}
fn default_min_trades() -> u64 {
    50
}
fn default_alpha() -> f64 {
    0.05
}

/// Resolve the family series from the request's three sources, in order:
/// `configs` map, `net_r` + `config`, or the cube-reduced artifact in
/// `out_dir`. A `configs` map is iterated in sorted-name order so two
/// identical requests always resolve the same family (G4 determinism); a
/// multi-config mean tie therefore resolves toward the lexicographically
/// first name, which is a documented divergence from the Python dict's
/// insertion order on exact ties only.
fn resolve_family(req: &VerdictRequest) -> Result<Vec<(String, Vec<f64>)>, String> {
    let mut family: Vec<(String, Vec<f64>)> = Vec::new();
    if !req.configs.is_empty() {
        let mut names: Vec<&String> = req.configs.keys().collect();
        names.sort_unstable();
        for name in names {
            family.push((name.clone(), req.configs[name].clone()));
        }
    } else if !req.net_r.is_empty() {
        family.push((req.config.clone(), req.net_r.clone()));
    } else if let Some(dir) = &req.out_dir {
        let path = dir.join(CUBE_REDUCED_FILENAME);
        let series = cube_reduced_series(&path)?;
        if series.is_empty() {
            return Err(format!(
                "{} has no COMPUTED legal_hindsight_gap rows — nothing to test",
                path.display()
            ));
        }
        family.push((req.config.clone(), series));
    } else {
        return Err(
            "request has no episode net_R series: set net_r (with config) or configs, \
             or out_dir pointing at a cube-reduced artifact"
                .to_string(),
        );
    }
    Ok(family)
}

/// The COMPUTED `legal_hindsight_gap` series of a cube-reduced artifact — the
/// per-episode net_R series of the reduced tables (report.rs summarizes the
/// same column). Absent cells and non-COMPUTED rows are skipped: an abstained
/// candidate has no gap, and no gap is ever a sentinel zero.
fn cube_reduced_series(path: &Path) -> Result<Vec<f64>, String> {
    let back = crate::evidence::read_artifact(path).map_err(|e| e.to_string())?;
    let statuses = back
        .column("gap_status")
        .ok_or("cube-reduced artifact has no gap_status column")?;
    let gaps = back
        .column("legal_hindsight_gap")
        .ok_or("cube-reduced artifact has no legal_hindsight_gap column")?;
    let mut out = Vec::new();
    for i in 0..back.row_count() {
        let status = statuses[i].as_ref().and_then(Value::as_str).unwrap_or("");
        if status == regret::GAP_COMPUTED {
            if let Some(v) = gaps[i].as_ref().and_then(Value::as_f64) {
                out.push(v);
            }
        }
    }
    Ok(out)
}

/// Compute the full S7 verdict JSON over the resolved family series: the WRC
/// (issue #128), the Appendix A detrended-null invariant (issue #124), and
/// the METH-2..6 surface (issue #129). Every oracle `ValueError` propagates
/// as `Err` — the driver fails closed, never a partial verdict.
pub fn compute_verdict(req: &VerdictRequest) -> Result<Value, String> {
    let family = resolve_family(req)?;
    let n = family[0].1.len();
    if n == 0 {
        return Err("empty episode series".to_string());
    }
    if req.n_resamples <= 0 {
        return Err("n_resamples must be positive".to_string());
    }
    for (name, series) in &family {
        if series.len() != n {
            return Err(format!(
                "all configuration episode series must share length (aligned by \
                 episode index): {name} has {} but the first has {n}",
                series.len()
            ));
        }
    }
    let refs: Vec<(&str, &[f64])> = family
        .iter()
        .map(|(name, series)| (name.as_str(), series.as_slice()))
        .collect();
    // The mechanical §9 rule on the first configuration's series — a family
    // property, since every series is aligned to the same episode grid.
    let block_size = match req.block_size {
        Some(b) => b,
        None => reality_check::select_block_size(refs[0].1, BLOCK_SIZE_THRESHOLD),
    };
    let seed = req.seed;

    let rc = reality_check::reality_check_p_value(&refs, block_size, req.n_resamples, seed)?;

    let detrended = if req.closes.is_empty() {
        Value::from(serde_json::json!({ "run": false }))
    } else {
        let ic = detrended::appendix_a_invariant(
            &req.closes,
            req.long_share,
            req.horizon_bars,
            req.risk_unit_frac,
            req.n_placebo,
            seed,
        )?;
        serde_json::json!({
            "run": true,
            "placebo_mean_raw": ic.placebo_mean_raw,
            "placebo_mean_detrended": ic.placebo_mean_detrended,
            "long_share": ic.long_share,
            "horizon_bars": ic.horizon_bars,
            "n_episodes": ic.n_episodes,
            "seed": ic.seed,
            "holds": ic.holds,
        })
    };

    let permutation = if req.moves.is_empty() || req.directions.is_empty() {
        Value::from(serde_json::json!({ "run": false }))
    } else {
        let mut dirs: Vec<(&str, &[i32])> = Vec::with_capacity(refs.len());
        for (name, _) in &refs {
            let d = req.directions.get(*name).ok_or_else(|| {
                format!(
                    "no directions for configuration {name:?}: the METH-3 null needs \
                     every variant's per-episode direction"
                )
            })?;
            dirs.push((name, d.as_slice()));
        }
        let pr = remaining::monte_carlo_permutation_p_value(
            &req.moves,
            &dirs,
            &refs,
            req.n_permutations,
            seed,
        )?;
        serde_json::json!({
            "run": true,
            "observed_max": pr.observed_max,
            "argmax_config": pr.argmax_config,
            "p_value": pr.p_value,
            "n_permutations": pr.n_permutations,
            "seed": pr.seed,
        })
    };

    let (ci_lower, ci_upper) = remaining::bootstrap_ci(
        refs[0].1,
        block_size as usize,
        req.n_resamples as u64,
        seed,
        req.ci,
    )?;
    let eff_n = remaining::effective_independent_episodes(n as u64, req.max_hold_bars)?;
    let slices = remaining::regime_slices(refs[0].1, req.slice_bars)?;
    let streak = remaining::streak_vs_null(
        refs[0].1,
        block_size as usize,
        req.n_resamples as u64,
        seed,
    )?;
    let (practical_meets, practical_note) =
        remaining::practical_significance(refs[0].1, req.min_net_r, req.min_trades)?;
    let n_rules = req.n_rules.unwrap_or(refs.len() as u64);
    let efp = remaining::expected_false_positives(n_rules, req.alpha)?;
    let variants_evaluated = refs.len() as u64;
    let search_universe_size = req.search_universe_size.unwrap_or(variants_evaluated);
    let ess = remaining::effective_search_size(variants_evaluated, search_universe_size)?;

    let source = if req.out_dir.is_some() && req.net_r.is_empty() && req.configs.is_empty() {
        "cube-reduced"
    } else {
        "net_r"
    };

    Ok(serde_json::json!({
        "subcommand": "verdict",
        "verdict": VERDICT_NO_ECONOMIC_CLAIM,
        "source": source,
        "seed": seed,
        "family": {
            "configs": family.iter().map(|(name, _)| name.clone()).collect::<Vec<_>>(),
            "n_configs": refs.len(),
            "n_episodes": n,
        },
        "reality_check": {
            "observed_max": rc.observed_max,
            "argmax_config": rc.argmax_config,
            "p_value": rc.p_value,
            "n_resamples": rc.n_resamples,
            "block_size": rc.block_size,
            "seed": rc.seed,
        },
        "detrended_null": detrended,
        "permutation": permutation,
        "bootstrap_ci": {
            "ci": req.ci,
            "block_size": block_size,
            "n_resamples": req.n_resamples,
            "lower": ci_lower,
            "upper": ci_upper,
        },
        "effective_independent_episodes": eff_n,
        "regime_slices": slices.iter().map(|s| serde_json::json!({
            "start_idx": s.start_idx,
            "end_idx": s.end_idx,
            "n": s.n,
            "mean_net_r": s.mean_net_r,
        })).collect::<Vec<_>>(),
        "streak_vs_null": {
            "observed_streak": streak.observed_streak,
            "p_value": streak.p_value,
            "block_size": streak.block_size,
            "n_resamples": streak.n_resamples,
            "seed": streak.seed,
        },
        "practical_significance": {
            "meets": practical_meets,
            "note": practical_note,
        },
        "expected_false_positives": efp,
        "effective_search_size": ess,
        "multiplicity_undercounted": search_universe_size > variants_evaluated,
        "n_rules": n_rules,
        "variants_evaluated": variants_evaluated,
        "search_universe_size": search_universe_size,
    }))
}

/// The `verdict` subcommand (issue #128): read one request file, print the
/// verdict JSON, and fail closed on any statistics error. Returns 0 only when
/// every requested statistic computed.
pub fn verdict(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core verdict <request.json>");
        return 2;
    }
    let req: VerdictRequest = match std::fs::read(&args[0])
        .map_err(|e| format!("cannot read request {}: {e}", args[0]))
        .and_then(|b| {
            serde_json::from_slice(&b).map_err(|e| format!("cannot parse request {}: {e}", args[0]))
        })
    {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    match compute_verdict(&req) {
        Ok(v) => {
            println!("{}", serde_json::to_string(&v).unwrap());
            0
        }
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn req(value: serde_json::Value) -> VerdictRequest {
        serde_json::from_value(value).unwrap()
    }

    /// The parity fixture: the WRC on the fixed v1 series reproduces the
    /// oracle's captured RealityCheckResult (block 4, 2000 resamples, seed 42).
    #[test]
    fn verdict_reality_check_matches_cpython() {
        let v = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2],
            "config": "v1",
            "seed": 42,
            "n_resamples": 2000,
            "block_size": 4,
        })))
        .unwrap();
        let rc = &v["reality_check"];
        assert_eq!(rc["observed_max"], 0.08125);
        assert_eq!(rc["argmax_config"], "v1");
        assert_eq!(rc["p_value"], 0.0145);
        assert_eq!(rc["n_resamples"], 2000);
        assert_eq!(rc["block_size"], 4);
        assert_eq!(rc["seed"], 42);
        assert_eq!(v["verdict"], VERDICT_NO_ECONOMIC_CLAIM);
        assert_eq!(v["source"], "net_r");
    }

    /// The §9 mechanical rule auto-selects the same block size as the oracle.
    #[test]
    fn verdict_auto_selects_block_size() {
        let v = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2],
            "seed": 42,
        })))
        .unwrap();
        assert_eq!(v["reality_check"]["block_size"], 4);
    }

    /// The Appendix A detrended-null section reproduces the oracle's captured
    /// placebo family values (long_share=0.65, horizon 3, frac 0.01, 8 eps).
    #[test]
    fn verdict_detrended_null_matches_cpython() {
        let v = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2],
            "seed": 42,
            "closes": [100.0, 102.0, 101.5, 105.0, 103.0, 107.5, 106.0, 110.0, 109.0, 112.0],
            "long_share": 0.65,
            "horizon_bars": 3,
            "risk_unit_frac": 0.01,
            "n_placebo": 8,
        })))
        .unwrap();
        let d = &v["detrended_null"];
        assert_eq!(d["run"], true);
        assert_eq!(d["placebo_mean_raw"], 2.28946297417138);
        assert_eq!(d["placebo_mean_detrended"], -0.5979485535951792);
        assert_eq!(d["long_share"], 0.65);
        assert_eq!(d["horizon_bars"], 3);
        assert_eq!(d["n_episodes"], 8);
        assert_eq!(d["seed"], 42);
        assert_eq!(d["holds"], false);
    }

    /// The METH-3 permutation section reproduces the oracle's captured result.
    #[test]
    fn verdict_permutation_matches_cpython() {
        let v = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2],
            "seed": 42,
            "block_size": 4,
            "moves": [0.001, -0.0005, 0.002, -0.001, 0.0008, -0.0003, 0.0015, -0.0009],
            "directions": {"v1": [1, -1, 1, -1, 1, 1, -1, 1]},
            "n_permutations": 50,
        })))
        .unwrap();
        let p = &v["permutation"];
        assert_eq!(p["run"], true);
        assert_eq!(p["observed_max"], 0.08125);
        assert_eq!(p["argmax_config"], "v1");
        assert_eq!(p["p_value"], 0.0);
        assert_eq!(p["n_permutations"], 50);
        assert_eq!(p["seed"], 42);
    }

    /// METH-4/5/6/2 sections on the fixture, with the oracle's captured values.
    #[test]
    fn verdict_meth4_5_6_2_matches_cpython() {
        let v = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2],
            "seed": 42,
            "block_size": 4,
            "ci": 0.90,
            "max_hold_bars": 8,
            "slice_bars": 3,
            "min_net_r": 0.05,
            "min_trades": 8,
            "alpha": 0.05,
            "n_rules": 2,
            "search_universe_size": 28,
        })))
        .unwrap();
        let ci = &v["bootstrap_ci"];
        assert_eq!(ci["lower"], 0.024999999999999994);
        assert_eq!(ci["upper"], 0.13125);
        assert_eq!(v["effective_independent_episodes"], 1.0);
        let slices = v["regime_slices"].as_array().unwrap();
        assert_eq!(slices.len(), 3);
        assert_eq!(slices[0]["start_idx"], 0);
        assert_eq!(slices[0]["end_idx"], 3);
        assert_eq!(slices[0]["mean_net_r"], 0.06666666666666667);
        assert_eq!(slices[2]["n"], 2);
        let st = &v["streak_vs_null"];
        assert_eq!(st["observed_streak"], 2);
        assert_eq!(st["p_value"], 0.951);
        let ps = &v["practical_significance"];
        assert_eq!(ps["meets"], true);
        assert_eq!(
            ps["note"],
            "mean net_R 0.0813 vs economic floor 0.05 (meets); episodes 8 vs \
             minimum coverage 8 (meets)"
        );
        assert_eq!(v["expected_false_positives"], 0.1);
        assert_eq!(v["effective_search_size"], 28);
        assert_eq!(v["multiplicity_undercounted"], true);
    }

    /// A section whose inputs are absent is emitted as `{"run": false}`, never
    /// silently dropped.
    #[test]
    fn verdict_absent_inputs_are_marked_not_run() {
        let v = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2],
            "seed": 42,
        })))
        .unwrap();
        assert_eq!(v["detrended_null"]["run"], false);
        assert_eq!(v["permutation"]["run"], false);
    }

    /// The METH-3 null requires every variant's directions — an incomplete
    /// directions map fails closed with the missing config named.
    #[test]
    fn verdict_permutation_missing_directions_fails_closed() {
        let err = compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, -0.2, 0.3, 0.15],
            "seed": 42,
            "moves": [0.001, -0.0005, 0.002, -0.001],
            "directions": {"other": [1, -1, 1, -1]},
        })))
        .unwrap_err();
        assert!(err.contains("v1"), "{err}");
    }

    /// The cube-reduced mode reads the COMPUTED gap series and skips abstained
    /// rows (no sentinel zeros).
    #[test]
    fn verdict_cube_reduced_mode_reads_computed_gaps() {
        let dir = std::env::temp_dir().join(format!("v82-verdict-cube-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let mut a = crate::evidence::Artifact::new(
            "cube-reduced",
            "VALUES",
            serde_json::json!({ "hash_encoding": crate::hash::HASH_ENCODING }),
            "candidate_id",
        );
        let c_gs = a.add_column("gap_status", crate::evidence::DType::DictStr);
        let c_gap = a.add_column("legal_hindsight_gap", crate::evidence::DType::F64);
        let rows: [(&str, Option<f64>); 3] = [
            (regret::GAP_COMPUTED, Some(0.1)),
            (regret::GAP_COMPUTED, Some(0.2)),
            (regret::GAP_ABSTAINED_CENSORED, None),
        ];
        for (status, gap) in rows {
            a.columns[c_gs].push_str(status);
            match gap {
                Some(v) => a.columns[c_gap].push_f64(v),
                None => {
                    a.columns[c_gap].push_f64(0.0);
                    a.columns[c_gap].push_absent();
                }
            }
            a.end_row();
        }
        let p = dir.join(CUBE_REDUCED_FILENAME);
        a.write(&p).unwrap();
        let v = compute_verdict(&req(serde_json::json!({
            "out_dir": dir.to_string_lossy(),
            "config": "v1",
            "seed": 42,
            "block_size": 1,
        })))
        .unwrap();
        assert_eq!(v["source"], "cube-reduced");
        assert_eq!(v["family"]["n_episodes"], 2);
        // mean of [0.1, 0.2] — 0.15000000000000002, the exact double sum/2.
        assert_eq!(v["reality_check"]["observed_max"], 0.15000000000000002);
        std::fs::remove_dir_all(&dir).ok();
    }

    /// Fail-closed paths: a missing series, a missing seed, and a request
    /// naming a missing cube-reduced artifact all error rather than emit a
    /// partial verdict.
    #[test]
    fn verdict_fails_closed_on_bad_requests() {
        assert!(compute_verdict(&req(serde_json::json!({ "seed": 1 }))).is_err());
        assert!(compute_verdict(&req(serde_json::json!({
            "seed": 42,
            "out_dir": "/nonexistent/v82-verdict-missing",
        })))
        .is_err());
        // non-positive resamples
        assert!(compute_verdict(&req(serde_json::json!({
            "net_r": [0.1, 0.2, 0.3, 0.4],
            "seed": 42,
            "n_resamples": 0,
        })))
        .is_err());
        // misaligned family lengths
        assert!(compute_verdict(&req(serde_json::json!({
            "configs": {"a": [0.1, 0.2, 0.3, 0.4], "b": [0.1, 0.2, 0.3]},
            "seed": 42,
        })))
        .is_err());
        // missing seed fails at deserialization
        assert!(serde_json::from_value::<VerdictRequest>(serde_json::json!({
            "net_r": [0.1, 0.2, 0.3],
        }))
        .is_err());
    }
}
