//! S7 remaining verdict surface (issue #129): METH-3..METH-6.
//!
//! Bit-for-bit port of the frozen Python oracle `src/v8/statistics.py`
//! (PARITY_AND_IDENTITY_SPEC §3): the Masters' permutation Reality-Check
//! (`monte_carlo_permutation_p_value`, METH-3 / E-02), the bootstrap
//! percentile CI (`bootstrap_ci`, METH-4 / E-01), `effective_independent_episodes`
//! (METH-4 / E-04), the METH-5 regime/streak surface (`regime_slices`,
//! `streak_vs_null`), and the METH-5/METH-6 estimators (`practical_significance`,
//! `expected_false_positives`) plus the METH-2 search-size report
//! (`effective_search_size`).
//!
//! Parity mechanics:
//! * every `sum(...)` mirrors CPython 3.14's compensated `sum()` through
//!   `state::fsum` (a plain left fold drifts by ulps);
//! * every `/ n` is an IEEE double division of the compensated sum, and every
//!   `int(...)` truncation mirrors CPython's toward-zero cast;
//! * all seeded draws go through `mt19937::MT19937` (CPython `random.Random`);
//!   the permutation draw is `sample(range(n), n)` (pool-branch Fisher-Yates,
//!   no `k == n` short-circuit on 3.14).
//!
//! `block_bootstrap_indices` / `block_bootstrap_means` are the ONE block
//! sampler of record (METH-4 / EV_METHODS E-04): the WRC (issue #128) must
//! reuse these, never keep a second sampler.
//!
//! All functions fail closed with `Err` mirroring the oracle's `ValueError`
//! text. The `u64` signatures make the oracle's vacuous "must be a
//! non-negative int / >= 0" checks type-level.
#![allow(dead_code)]

use crate::mt19937::MT19937;
use crate::state::fsum;

/// Python's `repr(float)` for error texts: CPython always shows a decimal
/// point for integral floats ("0.0", "1.0") while Rust's Display omits it
/// ("0", "1"); the digits themselves are shortest-round-trip in both.
fn py_float_repr(x: f64) -> String {
    let s = format!("{x}");
    if s.contains('.') || s.contains('e') || s.contains('E') || s.contains('n') || s.contains('i')
    {
        s
    } else {
        format!("{s}.0")
    }
}

/// One circular fixed-block bootstrap draw of length n over [0, n): repeatedly
/// picks a uniform start point and appends a contiguous run of `block_size`
/// indices (wrapping past the end) until length n is reached, then truncates.
/// Contiguous within a block, independent across blocks — the same episode-block
/// dependence unit as preregistration section 9.
///
/// Fail-closed invariant (D-052): `block_size >= n` collapses the bootstrap to
/// a point mass at the sample mean, so it raises rather than degrade. Mirrors
/// the oracle's `_block_bootstrap_indices` exactly (error texts included).
pub(crate) fn block_bootstrap_indices(
    n: usize,
    block_size: usize,
    rng: &mut MT19937,
) -> Result<Vec<usize>, String> {
    if n == 0 {
        return Ok(Vec::new());
    }
    if block_size == 0 {
        return Err("block_size must be positive".to_string());
    }
    if n >= 2 && block_size >= n {
        return Err(format!(
            "block_size {block_size} >= n {n}: degenerate block bootstrap \
             (every resample is a rotation of the whole series)"
        ));
    }
    let mut out: Vec<usize> = Vec::with_capacity(n);
    while out.len() < n {
        let start = rng.randrange(n as u64) as usize;
        for j in 0..block_size {
            out.push((start + j) % n);
        }
    }
    out.truncate(n);
    Ok(out)
}

/// The section-9 circular fixed-block bootstrap resample means. One rng from
/// `seed` drives every resample; each resample is a length-n draw from
/// `block_bootstrap_indices`. This is the one block sampler of record
/// (METH-4 / EV_METHODS E-04): the single-config percentile test and the WRC
/// must resample identically. Resample size = original n (bootstrap theorem,
/// Aronson Ch5 p234-238).
pub(crate) fn block_bootstrap_means(
    net_rs: &[f64],
    block_size: usize,
    n_resamples: u64,
    seed: u64,
) -> Result<Vec<f64>, String> {
    let n = net_rs.len();
    if n == 0 {
        return Ok(Vec::new());
    }
    if n_resamples == 0 {
        return Err("n_resamples must be positive".to_string());
    }
    let mut rng = MT19937::new(seed);
    let mut means: Vec<f64> = Vec::with_capacity(n_resamples as usize);
    let mut sel = Vec::with_capacity(n);
    for _ in 0..n_resamples {
        let idx = block_bootstrap_indices(n, block_size, &mut rng)?;
        sel.clear();
        for &i in &idx {
            sel.push(net_rs[i]);
        }
        means.push(fsum(&sel) / n as f64);
    }
    Ok(means)
}

/// Bootstrap percentile confidence interval on mean episode net_R
/// (METH-4 / EV_METHODS E-01; Aronson Ch5 p245-253): circular fixed-block
/// bootstrap, mean per resample, sort; `tail = int(B*(1-ci)/2)`;
/// `lower = means[tail]`, `upper = means[-tail-1]`. An empty series returns
/// `(0.0, 0.0)`; `block_size` must respect the E-04 rule (>= max episode hold).
pub fn bootstrap_ci(
    net_r_series: &[f64],
    block_size: usize,
    n_resamples: u64,
    seed: u64,
    ci: f64,
) -> Result<(f64, f64), String> {
    if !(0.0 < ci && ci < 1.0) {
        return Err(format!("ci must be in (0, 1) (got {})", py_float_repr(ci)));
    }
    let mut means = block_bootstrap_means(net_r_series, block_size, n_resamples, seed)?;
    if means.is_empty() {
        return Ok((0.0, 0.0));
    }
    means.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap());
    let tail = (n_resamples as f64 * (1.0 - ci) / 2.0) as usize;
    Ok((means[tail], means[means.len() - tail - 1]))
}

/// Effective number of independent episodes under overlap: `n / max_hold_bars`,
/// the conservative upper bound on independent observations when blocks must be
/// at least the longest hold (METH-4 / EV_METHODS E-04; Aronson Ch7 n43 p504).
pub fn effective_independent_episodes(n_episodes: u64, max_hold_bars: u64) -> Result<f64, String> {
    if max_hold_bars == 0 {
        return Err(format!("max_hold_bars must be positive (got {max_hold_bars})"));
    }
    if n_episodes == 0 {
        return Ok(0.0);
    }
    Ok(n_episodes as f64 / max_hold_bars as f64)
}

/// One consecutive window of the episode net_R series (METH-5 / G-06).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RegimeSlice {
    /// inclusive
    pub start_idx: usize,
    /// exclusive
    pub end_idx: usize,
    pub n: usize,
    pub mean_net_r: f64,
}

/// Per-slice mean net_R strata over the ordered episode series (METH-5 /
/// EV_METHODS G-06; Aronson Ch3 p123-124, Ch7 p352/355): split into consecutive
/// non-overlapping windows of `slice_bars` episodes and report each window's
/// mean. Report-only; never a gate.
pub fn regime_slices(episode_net_r: &[f64], slice_bars: usize) -> Result<Vec<RegimeSlice>, String> {
    if slice_bars == 0 {
        return Err(format!("slice_bars must be positive (got {slice_bars})"));
    }
    let mut out: Vec<RegimeSlice> = Vec::new();
    let mut start = 0usize;
    while start < episode_net_r.len() {
        let end = (start + slice_bars).min(episode_net_r.len());
        let chunk = &episode_net_r[start..end];
        out.push(RegimeSlice {
            start_idx: start,
            end_idx: end,
            n: chunk.len(),
            mean_net_r: fsum(chunk) / chunk.len() as f64,
        });
        start = end;
    }
    Ok(out)
}

/// Longest run of strictly positive values (the oracle's `_longest_positive_run`).
fn longest_positive_run(xs: &[f64]) -> usize {
    let mut best = 0usize;
    let mut cur = 0usize;
    for &x in xs {
        if x > 0.0 {
            cur += 1;
            if cur > best {
                best = cur;
            }
        } else {
            cur = 0;
        }
    }
    best
}

/// Observed best-of-family winning streak vs the no-edge bootstrap null
/// (METH-5 / EV_METHODS G-08).
#[derive(Debug, Clone, PartialEq)]
pub struct StreakVsNullResult {
    pub observed_streak: usize,
    pub p_value: f64,
    /// longest positive run per resample
    pub null_best_streaks: Vec<usize>,
    pub block_size: usize,
    pub n_resamples: u64,
    pub seed: u64,
}

/// Observed streak of profitable episodes vs the no-edge bootstrap null
/// (METH-5 / EV_METHODS G-08): zero-center the series (E-03: x'_i = x_i -
/// mean(x)), circular block resample with the same §9 sampler, and report the
/// fraction of null streaks at least as long as the observed one. Report-only,
/// never a gate (prereg §11).
pub fn streak_vs_null(
    episode_net_r: &[f64],
    block_size: usize,
    n_resamples: u64,
    seed: u64,
) -> Result<StreakVsNullResult, String> {
    if episode_net_r.is_empty() {
        return Err("empty episode series".to_string());
    }
    if n_resamples == 0 {
        return Err("n_resamples must be positive".to_string());
    }
    let observed = longest_positive_run(episode_net_r);
    let n = episode_net_r.len();
    let mu = fsum(episode_net_r) / n as f64;
    let centered: Vec<f64> = episode_net_r.iter().map(|&x| x - mu).collect();
    let mut rng = MT19937::new(seed);
    let mut nulls: Vec<usize> = Vec::with_capacity(n_resamples as usize);
    let mut exceed: u64 = 0;
    let mut sel = Vec::with_capacity(n);
    for _ in 0..n_resamples {
        let idx = block_bootstrap_indices(n, block_size, &mut rng)?;
        sel.clear();
        for &i in &idx {
            sel.push(centered[i]);
        }
        let s = longest_positive_run(&sel);
        nulls.push(s);
        if s >= observed {
            exceed += 1;
        }
    }
    let p_value = exceed as f64 / n_resamples as f64;
    Ok(StreakVsNullResult {
        observed_streak: observed,
        p_value,
        null_best_streaks: nulls,
        block_size,
        n_resamples,
        seed,
    })
}

/// Statistical significance is not practical significance (METH-5 /
/// EV_METHODS G-12; Aronson Ch8 p394, Ch9 p443): the composite verdict gates
/// on `mean(net_R) >= min_net_r` AND `n >= min_trades`, and returns `(meets,
/// note)` where the note states both observed values. Report-only — a note for
/// the authority-receipt verdict path, never a hard fail.
pub fn practical_significance(
    net_r: &[f64],
    min_net_r: f64,
    min_trades: u64,
) -> Result<(bool, String), String> {
    if !(min_net_r > 0.0) {
        return Err(format!(
            "min_net_r must be > 0 (got {})",
            py_float_repr(min_net_r)
        ));
    }
    if min_trades == 0 {
        return Err(format!("min_trades must be positive (got {min_trades})"));
    }
    let n = net_r.len() as u64;
    let mean = if n > 0 { fsum(net_r) / n as f64 } else { 0.0 };
    let meets = n >= min_trades && mean >= min_net_r;
    let note = format!(
        "mean net_R {:.4} vs economic floor {} ({}); episodes {} vs minimum coverage {} ({})",
        mean,
        min_net_r,
        if mean >= min_net_r { "meets" } else { "below" },
        n,
        min_trades,
        if n >= min_trades { "meets" } else { "below" },
    );
    Ok((meets, note))
}

/// Expected false positives under the null: N rules at alpha -> N*alpha
/// (METH-6 / EV_METHODS E-05; Aronson Ch9 p443 — 6,402 rules at 0.05 give
/// 320.1). A count near expectation is evidence of NO edge.
pub fn expected_false_positives(n_rules: u64, alpha: f64) -> Result<f64, String> {
    if !(0.0 < alpha && alpha < 1.0) {
        return Err(format!("alpha must be in (0, 1) (got {})", py_float_repr(alpha)));
    }
    Ok(n_rules as f64 * alpha)
}

/// The honest family size for multiplicity-sensitive report lines
/// (METH-2 / EV_METHODS G-01; D-046): `max(variants_evaluated,
/// search_universe_size)` so the reported size can never understate the
/// declared search; when the two differ the caller surfaces
/// `multiplicity_undercounted` so the optimism is visible.
pub fn effective_search_size(
    variants_evaluated: u64,
    search_universe_size: u64,
) -> Result<u64, String> {
    if search_universe_size < variants_evaluated {
        return Err(format!(
            "search_universe_size {search_universe_size} < variants_evaluated \
             {variants_evaluated}: the declared search cannot be smaller than \
             what it retained (D-046)"
        ));
    }
    Ok(variants_evaluated.max(search_universe_size))
}

/// Output of `monte_carlo_permutation_p_value` (METH-3 / EV_METHODS E-02).
/// `argmax_config` is the only configuration whose observed performance the
/// null is judged against, mirroring the WRC result.
#[derive(Debug, Clone, PartialEq)]
pub struct PermutationRealityCheckResult {
    pub observed_max: f64,
    pub argmax_config: String,
    pub p_value: f64,
    pub n_permutations: u64,
    pub seed: u64,
}

/// Monte-Carlo permutation Reality-Check p-value (Masters' method, METH-3 /
/// EV_METHODS E-02; Aronson Ch5 p239-240, Ch6 p327-328, Ch9 p442): the
/// signal-content null — the rules' long/short positions are randomly paired
/// with the market's per-episode move.
///
/// Each round draws ONE permutation pi of {0..n-1} without replacement
/// (`sample(range(n), n)`) and applies it to every variant
/// (`mean_c = (1/n) sum_e direction_c[pi(e)] * episode_moves[e]`), preserving
/// cross-configuration correlation by construction; the round statistic is the
/// max over configurations. `p = #{rounds: round_stat >= observed_max} /
/// n_permutations`. No recentering — the null is "randomly correlated with
/// future market behavior".
///
/// Configuration order is significant: `argmax_config` resolves ties toward
/// the first configuration in `episode_net_r` order (dict insertion order).
pub fn monte_carlo_permutation_p_value(
    episode_moves: &[f64],
    episode_directions: &[(&str, &[i32])],
    episode_net_r: &[(&str, &[f64])],
    n_permutations: u64,
    seed: u64,
) -> Result<PermutationRealityCheckResult, String> {
    if episode_net_r.is_empty() {
        return Err("no configurations supplied".to_string());
    }
    // set(episode_directions) != set(episode_net_r): order-independent key set.
    let mut dir_names: Vec<&str> = episode_directions.iter().map(|(n, _)| *n).collect();
    let mut net_names: Vec<&str> = episode_net_r.iter().map(|(n, _)| *n).collect();
    dir_names.sort_unstable();
    net_names.sort_unstable();
    if dir_names != net_names {
        return Err(
            "episode_directions and episode_net_r must cover the same variants".to_string()
        );
    }
    let n = episode_moves.len();
    if n == 0 {
        return Err("empty episode series".to_string());
    }
    let lengths_ok = episode_net_r.iter().all(|(_, v)| v.len() == n)
        && episode_directions.iter().all(|(_, v)| v.len() == n);
    if !lengths_ok {
        return Err(
            "episode_moves, every direction series and every net_R series must \
             share length (aligned by episode index — the D-045 grid)"
                .to_string(),
        );
    }
    // Python iterates configs in episode_net_r order and looks up directions,
    // so a multi-invalid family reports the net_R order's first offender.
    for (c, _) in episode_net_r {
        let dirs = episode_directions
            .iter()
            .find(|(n, _)| *n == *c)
            .expect("directions/net_r cover the same variants (checked above)")
            .1;
        for &d in dirs.iter() {
            if d != 1 && d != -1 {
                let mut vals: Vec<i32> = dirs.to_vec();
                vals.sort_unstable();
                vals.dedup();
                return Err(format!(
                    "{c}: directions must be +1 (LONG) or -1 (SHORT), got {vals:?}"
                ));
            }
        }
    }
    if n_permutations == 0 {
        return Err("n_permutations must be positive".to_string());
    }

    // means in episode_net_r order; argmax resolves ties to the first config.
    let means: Vec<(f64, &str)> = episode_net_r
        .iter()
        .map(|(c, v)| (fsum(v) / n as f64, *c))
        .collect();
    let observed_max = means.iter().map(|(m, _)| *m).fold(f64::NEG_INFINITY, f64::max);
    let mut best = means[0];
    for &(m, c) in means.iter().skip(1) {
        if m > best.0 {
            best = (m, c);
        }
    }
    let argmax_config = best.1.to_string();

    let mut rng = MT19937::new(seed);
    let mut exceed: u64 = 0;
    let mut acc = Vec::with_capacity(n);
    for _ in 0..n_permutations {
        let perm = rng.sample(n as u64); // one pi for every variant
        let mut round_max = f64::NEG_INFINITY;
        for (_, dirs) in episode_directions {
            acc.clear();
            for e in 0..n {
                acc.push(dirs[perm[e] as usize] as f64 * episode_moves[e]);
            }
            let rm = fsum(&acc) / n as f64;
            if rm > round_max {
                round_max = rm;
            }
        }
        if round_max >= observed_max {
            exceed += 1;
        }
    }
    let p_value = exceed as f64 / n_permutations as f64;

    Ok(PermutationRealityCheckResult {
        observed_max,
        argmax_config,
        p_value,
        n_permutations,
        seed,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const MOVES: [f64; 10] = [
        0.001, -0.0005, 0.002, -0.001, 0.0008, -0.0003, 0.0015, -0.0009, 0.0006, -0.0002,
    ];
    const DIRS_A: [i32; 10] = [1, -1, 1, -1, 1, 1, -1, 1, -1, 1];
    const DIRS_B: [i32; 10] = [-1, 1, 1, -1, -1, 1, 1, -1, 1, -1];
    const NET_A: [f64; 10] = [
        0.002, -0.001, 0.001, -0.0005, 0.0007, 0.0012, -0.0008, 0.0011, -0.0006, 0.0009,
    ];
    const NET_B: [f64; 10] = [
        0.001, 0.0008, -0.0012, 0.0006, -0.0009, 0.0013, -0.0007, 0.001, -0.0011, 0.0004,
    ];
    /// Captured CPython: seed 42, first two `random.sample(range(10), 10)`.
    const PERM0: [u64; 10] = [1, 0, 4, 9, 6, 5, 8, 2, 3, 7];
    const PERM1: [u64; 10] = [0, 9, 1, 7, 6, 4, 8, 2, 3, 5];
    /// Captured CPython per-round max statistic over both configs, seed 42.
    const ROUND_STATS: [f64; 50] = [
        0.00012000000000000002, 0.00034, 0.00054, 0.00035999999999999997, 0.00038,
        -4.000000000000001e-05, 0.0004, 0.00088, 0.00062, 0.00054, 0.00014, 0.0002, 0.00034,
        0.00028, 0.0004, 0.0008399999999999999, 0.00035999999999999997, 0.00041999999999999996,
        -8e-05, 0.0001, 0.00026, 4.000000000000001e-05, 0.0002, 0.00033999999999999997,
        0.00015999999999999999, 0.00032, 0.00024000000000000003, -0.00011999999999999999,
        0.0001, 0.00022, 0.00030000000000000003, 0.00028, 0.00038, 0.00036, 0.00016,
        0.00026000000000000003, 0.0007199999999999999, 0.00041999999999999996, 0.00026, 0.0001,
        -2e-05, 0.00014000000000000001, 0.00066, 0.00046, -6.000000000000001e-05,
        -0.00017999999999999998, 4.000000000000001e-05, 0.00028, 0.00046, 0.00017999999999999998,
    ];

    #[test]
    fn permutation_sample_matches_cpython() {
        // rng.sample(range(10), 10) must match `random.sample(range(n), n)`
        // (pool-branch Fisher-Yates) so every permutation draw is identical.
        let mut rng = MT19937::new(42);
        assert_eq!(rng.sample(10), PERM0.to_vec());
        assert_eq!(rng.sample(10), PERM1.to_vec());
    }

    #[test]
    fn permutation_round_stats_match_cpython() {
        // Every per-round max must match the captured oracle, pinning the
        // sample() stream, fsum, and the / n division jointly.
        let mut rng = MT19937::new(42);
        let dirs: [(&str, &[i32]); 2] = [("A", &DIRS_A), ("B", &DIRS_B)];
        let mut got: Vec<f64> = Vec::with_capacity(50);
        let mut acc = Vec::with_capacity(10);
        for _ in 0..50 {
            let perm = rng.sample(10);
            let mut round_max = f64::NEG_INFINITY;
            for (_, d) in &dirs {
                acc.clear();
                for e in 0..10 {
                    acc.push(d[perm[e] as usize] as f64 * MOVES[e]);
                }
                let rm = fsum(&acc) / 10.0;
                if rm > round_max {
                    round_max = rm;
                }
            }
            got.push(round_max);
        }
        assert_eq!(got, ROUND_STATS.to_vec());
    }

    #[test]
    fn permutation_rc_matches_cpython() {
        let dirs: [(&str, &[i32]); 2] = [("A", &DIRS_A), ("B", &DIRS_B)];
        let net: [(&str, &[f64]); 2] = [("A", &NET_A), ("B", &NET_B)];
        let r = monte_carlo_permutation_p_value(&MOVES, &dirs, &net, 50, 42).unwrap();
        // CPython: PermutationRealityCheckResult(observed_max=0.0004,
        // argmax_config='A', p_value=0.26, n_permutations=50, seed=42).
        assert_eq!(r.observed_max, 0.0004);
        assert_eq!(r.argmax_config, "A");
        assert_eq!(r.p_value, 0.26);
        assert_eq!(r.n_permutations, 50);
        assert_eq!(r.seed, 42);
    }

    #[test]
    fn permutation_rc_fails_closed() {
        let dirs: [(&str, &[i32]); 1] = [("A", &DIRS_A)];
        let net: [(&str, &[f64]); 1] = [("A", &NET_A)];
        assert_eq!(
            monte_carlo_permutation_p_value(&MOVES, &dirs, &net, 0, 1),
            Err("n_permutations must be positive".to_string())
        );
        assert_eq!(
            monte_carlo_permutation_p_value(&MOVES, &[], &[], 5, 1),
            Err("no configurations supplied".to_string())
        );
        let other: [(&str, &[f64]); 1] = [("B", &NET_B)];
        assert_eq!(
            monte_carlo_permutation_p_value(&MOVES, &dirs, &other, 5, 1),
            Err("episode_directions and episode_net_r must cover the same variants".to_string())
        );
        let short_moves: [f64; 1] = [0.001];
        assert_eq!(
            monte_carlo_permutation_p_value(&short_moves, &dirs, &net, 5, 1),
            Err(
                "episode_moves, every direction series and every net_R series must \
                 share length (aligned by episode index — the D-045 grid)"
                    .to_string()
            )
        );
        // 2-element family with an invalid direction, matching the captured
        // oracle call (moves/dirs/net all length 2).
        let short_moves: [f64; 2] = [0.001, -0.0005];
        let bad_dir: [(&str, &[i32]); 1] = [("A", &[2, -1])];
        let short_net: [(&str, &[f64]); 1] = [("A", &[0.001, -0.0005])];
        assert_eq!(
            monte_carlo_permutation_p_value(&short_moves, &bad_dir, &short_net, 5, 1),
            Err("A: directions must be +1 (LONG) or -1 (SHORT), got [-1, 2]".to_string())
        );
    }

    #[test]
    fn block_bootstrap_indices_match_cpython() {
        // Captured CPython `_block_bootstrap_indices` draws.
        let mut rng = MT19937::new(7);
        for exp in [
            vec![5, 6, 7, 2, 3, 4, 6, 7, 8, 10, 11, 0],
            vec![0, 1, 2, 1, 2, 3, 8, 9, 10, 1, 2, 3],
            vec![5, 6, 7, 9, 10, 11, 0, 1, 2, 8, 9, 10],
            vec![3, 4, 5, 0, 1, 2, 1, 2, 3, 6, 7, 8],
        ] {
            assert_eq!(block_bootstrap_indices(12, 3, &mut rng).unwrap(), exp);
        }
        let mut rng2 = MT19937::new(99);
        for exp in [
            vec![6, 7, 8, 9, 6, 7, 8, 9, 3, 4, 5, 6, 9, 10, 11],
            vec![2, 3, 4, 5, 3, 4, 5, 6, 3, 4, 5, 6, 2, 3, 4],
            vec![12, 13, 14, 0, 1, 2, 3, 4, 4, 5, 6, 7, 11, 12, 13],
            vec![6, 7, 8, 9, 8, 9, 10, 11, 10, 11, 12, 13, 11, 12, 13],
        ] {
            assert_eq!(block_bootstrap_indices(15, 4, &mut rng2).unwrap(), exp);
        }
        // fail-closed: block_size >= n and block_size == 0
        let mut rng3 = MT19937::new(1);
        assert!(block_bootstrap_indices(12, 12, &mut rng3).is_err());
        assert!(block_bootstrap_indices(12, 0, &mut rng3).is_err());
    }

    #[test]
    fn block_bootstrap_means_match_cpython() {
        const SERIES: [f64; 12] = [
            0.001, -0.0005, 0.002, -0.001, 0.0008, -0.0003, 0.0015, -0.0009, 0.0006, -0.0002,
            0.0011, -0.0007,
        ];
        let means = block_bootstrap_means(&SERIES, 3, 200, 7).unwrap();
        assert_eq!(
            &means[..6],
            &[
                0.0003916666666666667,
                0.0004166666666666667,
                0.00037500000000000006,
                0.00030833333333333337,
                0.00014166666666666668,
                0.00045000000000000004,
            ]
        );
        assert_eq!(
            &means[194..],
            &[
                0.0002,
                0.00023333333333333333,
                8.333333333333333e-05,
                0.000125,
                0.00037500000000000006,
                0.00035,
            ]
        );
        assert_eq!(means.len(), 200);
        // n == 0 -> empty (no rng consumed); n_resamples == 0 fail-closed.
        assert_eq!(block_bootstrap_means(&[], 3, 200, 7).unwrap(), Vec::<f64>::new());
        assert_eq!(
            block_bootstrap_means(&SERIES, 3, 0, 7),
            Err("n_resamples must be positive".to_string())
        );
    }

    #[test]
    fn bootstrap_ci_matches_cpython() {
        const SERIES: [f64; 12] = [
            0.001, -0.0005, 0.002, -0.001, 0.0008, -0.0003, 0.0015, -0.0009, 0.0006, -0.0002,
            0.0011, -0.0007,
        ];
        // CPython: (2.2587545260114674e-21, 0.0006083333333333333)
        let lo_hi = bootstrap_ci(&SERIES, 3, 200, 7, 0.90).unwrap();
        assert_eq!(lo_hi.0, 2.2587545260114674e-21);
        assert_eq!(lo_hi.1, 0.0006083333333333333);
        // CPython: (-5.833333333333333e-05, 0.0006583333333333334)
        let lo_hi = bootstrap_ci(&SERIES, 3, 200, 7, 0.95).unwrap();
        assert_eq!(lo_hi.0, -5.833333333333333e-05);
        assert_eq!(lo_hi.1, 0.0006583333333333334);
        // empty series -> (0.0, 0.0)
        assert_eq!(bootstrap_ci(&[], 3, 200, 7, 0.90).unwrap(), (0.0, 0.0));
        // ci outside (0, 1) fail-closed
        assert_eq!(
            bootstrap_ci(&SERIES, 3, 10, 5, 1.5),
            Err("ci must be in (0, 1) (got 1.5)".to_string())
        );
    }

    #[test]
    fn effective_independent_episodes_matches_cpython() {
        // CPython: 200/8=25.0, 0->0.0, 200/1=200.0, 7/2=3.5
        assert_eq!(effective_independent_episodes(200, 8).unwrap(), 25.0);
        assert_eq!(effective_independent_episodes(0, 8).unwrap(), 0.0);
        assert_eq!(effective_independent_episodes(200, 1).unwrap(), 200.0);
        assert_eq!(effective_independent_episodes(7, 2).unwrap(), 3.5);
        assert_eq!(
            effective_independent_episodes(10, 0),
            Err("max_hold_bars must be positive (got 0)".to_string())
        );
    }

    #[test]
    fn regime_slices_match_cpython() {
        const SERIES: [f64; 8] = [0.001, -0.0005, 0.002, -0.001, 0.0008, -0.0003, 0.0015, -0.0009];
        let slices = regime_slices(&SERIES, 3).unwrap();
        assert_eq!(slices.len(), 3);
        assert_eq!(slices[0].start_idx, 0);
        assert_eq!(slices[0].end_idx, 3);
        assert_eq!(slices[0].n, 3);
        assert_eq!(slices[0].mean_net_r, 0.0008333333333333334);
        assert_eq!(slices[1].mean_net_r, -0.00016666666666666666);
        assert_eq!(slices[2].start_idx, 6);
        assert_eq!(slices[2].end_idx, 8);
        assert_eq!(slices[2].n, 2);
        assert_eq!(slices[2].mean_net_r, 0.00030000000000000003);
        // slice_bars = 4
        let slices = regime_slices(&SERIES, 4).unwrap();
        assert_eq!(slices[0].mean_net_r, 0.000375);
        assert_eq!(slices[1].mean_net_r, 0.000275);
        // empty series -> no slices; slice_bars == 0 fail-closed
        assert!(regime_slices(&[], 3).unwrap().is_empty());
        assert_eq!(
            regime_slices(&SERIES, 0),
            Err("slice_bars must be positive (got 0)".to_string())
        );
    }

    #[test]
    fn longest_positive_run_matches_cpython() {
        const SERIES: [f64; 15] = [
            0.002, 0.001, -0.001, 0.0008, 0.0006, 0.0004, -0.0005, 0.0012, 0.001, -0.0009,
            0.0007, 0.0005, 0.0003, -0.0002, 0.0011,
        ];
        assert_eq!(longest_positive_run(&SERIES), 3);
        assert_eq!(longest_positive_run(&[-1.0, -2.0]), 0);
        assert_eq!(longest_positive_run(&[1.0]), 1);
    }

    #[test]
    fn streak_vs_null_matches_cpython() {
        const SERIES: [f64; 15] = [
            0.002, 0.001, -0.001, 0.0008, 0.0006, 0.0004, -0.0005, 0.0012, 0.001, -0.0009,
            0.0007, 0.0005, 0.0003, -0.0002, 0.0011,
        ];
        // Captured CPython null_best_streaks (100 resamples, block 4, seed 99).
        const NULLS: [usize; 100] = [
            2, 2, 3, 4, 3, 2, 5, 3, 5, 3, 3, 4, 2, 4, 5, 5, 3, 3, 2, 3, 4, 4, 3, 3, 2, 2, 3, 3,
            2, 3, 4, 4, 3, 3, 2, 3, 3, 4, 3, 2, 3, 5, 2, 2, 3, 4, 3, 4, 5, 2, 4, 3, 3, 5, 3, 4,
            3, 3, 3, 2, 2, 2, 3, 5, 4, 3, 3, 4, 2, 4, 4, 3, 4, 3, 4, 3, 4, 4, 4, 3, 3, 2, 2, 4,
            3, 3, 2, 3, 3, 4, 3, 3, 6, 2, 3, 3, 3, 4, 2, 4,
        ];
        let r = streak_vs_null(&SERIES, 4, 100, 99).unwrap();
        assert_eq!(r.observed_streak, 3);
        assert_eq!(r.p_value, 0.78);
        assert_eq!(r.null_best_streaks, NULLS.to_vec());
        assert_eq!(r.block_size, 4);
        assert_eq!(r.n_resamples, 100);
        assert_eq!(r.seed, 99);
        // CPython mu of the series: 0.00046666666666666666
        assert_eq!(fsum(&SERIES) / SERIES.len() as f64, 0.00046666666666666666);
        // fail-closed paths
        assert_eq!(
            streak_vs_null(&[], 4, 100, 99),
            Err("empty episode series".to_string())
        );
        assert_eq!(
            streak_vs_null(&SERIES, 4, 0, 99),
            Err("n_resamples must be positive".to_string())
        );
    }

    #[test]
    fn practical_significance_matches_cpython() {
        const PS1: [f64; 8] = [
            0.002, 0.001, -0.001, 0.0008, 0.0006, 0.0004, -0.0005, 0.0012,
        ];
        let (meets, note) = practical_significance(&PS1, 0.0005, 8).unwrap();
        assert!(meets);
        assert_eq!(
            note,
            "mean net_R 0.0006 vs economic floor 0.0005 (meets); episodes 8 vs \
             minimum coverage 8 (meets)"
        );
        let (meets, note) = practical_significance(&PS1, 0.001, 100).unwrap();
        assert!(!meets);
        assert_eq!(
            note,
            "mean net_R 0.0006 vs economic floor 0.001 (below); episodes 8 vs \
             minimum coverage 100 (below)"
        );
        let (meets, note) = practical_significance(&[], 0.0005, 1).unwrap();
        assert!(!meets);
        assert_eq!(
            note,
            "mean net_R 0.0000 vs economic floor 0.0005 (below); episodes 0 vs \
             minimum coverage 1 (below)"
        );
        const PS3: [f64; 10] = [
            0.002, 0.001, -0.001, 0.0008, 0.0006, 0.0004, -0.0005, 0.0012, 0.003, 0.002,
        ];
        let (meets, note) = practical_significance(&PS3, 0.0007, 10).unwrap();
        assert!(meets);
        assert_eq!(
            note,
            "mean net_R 0.0009 vs economic floor 0.0007 (meets); episodes 10 vs \
             minimum coverage 10 (meets)"
        );
        assert_eq!(
            practical_significance(&PS1, 0.0, 5),
            Err("min_net_r must be > 0 (got 0.0)".to_string())
        );
        assert_eq!(
            practical_significance(&PS1, 0.01, 0),
            Err("min_trades must be positive (got 0)".to_string())
        );
    }

    #[test]
    fn expected_false_positives_matches_cpython() {
        // CPython: 6402*0.05=320.1, 2*0.025=0.05, 0*0.1=0.0
        assert_eq!(expected_false_positives(6402, 0.05).unwrap(), 320.1);
        assert_eq!(expected_false_positives(2, 0.025).unwrap(), 0.05);
        assert_eq!(expected_false_positives(0, 0.1).unwrap(), 0.0);
        assert_eq!(
            expected_false_positives(10, 1.0),
            Err("alpha must be in (0, 1) (got 1.0)".to_string())
        );
    }

    #[test]
    fn effective_search_size_matches_cpython() {
        // CPython: (3,10)->10, (5,5)->5, (0,0)->0
        assert_eq!(effective_search_size(3, 10).unwrap(), 10);
        assert_eq!(effective_search_size(5, 5).unwrap(), 5);
        assert_eq!(effective_search_size(0, 0).unwrap(), 0);
        assert_eq!(
            effective_search_size(5, 3),
            Err(
                "search_universe_size 3 < variants_evaluated 5: the declared search \
                 cannot be smaller than what it retained (D-046)"
                    .to_string()
            )
        );
    }
}
