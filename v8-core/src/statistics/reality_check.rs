//! S7 block-bootstrap Reality-Check (issue #128): White 2000 Procedure RC
//! max-statistic over a family's episode series (D-044). `select_block_size`
//! implements preregistration section 9's mechanical rule with Python
//! half-even `round()`; `block_bootstrap_means` is the single block sampler of
//! record (METH-4 / EV_METHODS E-04), shared with the detrended null's
//! percentile test.
//!
//! Parity contract (PARITY_AND_IDENTITY_SPEC §3): every reduction mirrors the
//! frozen oracle `statistics.py` — `sum()` is compensated summation
//! (`crate::state::fsum`), `x**2` / `n**(1/3)` go through libm `powf`, and
//! the bootstrap draws come from `crate::mt19937` (bit-exact CPython
//! `random.Random`), so the seed flow matches `random.Random(seed)` exactly.
//!
//! The only recentering here is the WRC compound-null recentering; position-
//! bias detrending is the caller's job (`detrended` module).

#![allow(dead_code)] // verdict wiring lands in a later integration step (issues #116/#128)

use crate::mt19937::MT19937;
use crate::state::fsum;

/// One executed episode's net_R plus the exposure that produced it.
///
/// Mirrors `EpisodeExposure` (D-045) and `CounterfactualOutcome` records.
/// `net_r` alone cannot be detrended: the benchmark must be expressed in the
/// SAME R unit the simulator used, and that unit depends on the fill whenever
/// a draft declares `risk_frac` instead of `atr_ref`.
#[derive(Debug, Clone, PartialEq)]
pub struct EpisodeExposure {
    pub net_r: f64,
    pub direction: String, // LONG | SHORT
    pub entry_price: f64,
    pub risk_unit_price: f64, // price distance of one R at the entry fill
    pub horizon_bars: i64,
}

/// Python 3 `round(x)`: nearest integer, ties to even (banker's rounding).
///
/// NOT `f64::round()` (half away from zero) and NOT `floor(x + 0.5)` (wrong
/// for negatives). Mirrors CPython `_Py_double_round`: values in (-0.5, 0.5)
/// round to zero; a value whose fractional part is exactly 0.5 goes to the
/// nearest even integer. The return is the rounded value as an `f64` (Python
/// returns an int; the caller converts, which is exact while the magnitude
/// stays within the integer range — true for every `round(n**(1/3))` a block
/// size can produce).
pub fn py_round(x: f64) -> f64 {
    if x > -0.5 && x < 0.5 {
        return 0.0;
    }
    let n = x.floor();
    let frac = x - n;
    if frac < 0.5 {
        n
    } else if frac > 0.5 {
        n + 1.0
    } else {
        // exact half: round toward the nearest even integer
        let even = (n / 2.0).floor() * 2.0;
        if n == even {
            n
        } else {
            n + 1.0
        }
    }
}

/// Preregistration section 9's mechanical block-size rule (D-052).
///
/// Two tiers selected by the lag-1 autocorrelation of episode `net_R`: the
/// standard block-bootstrap rate `round(n**(1/3))` in episode units, doubled
/// when the gate fires. The `n // 2` cap keeps the estimator defined: at
/// `block_size >= n` the circular sampler returns a rotation of the whole
/// series and the bootstrap collapses to a point mass at the sample mean
/// (`block_bootstrap_indices` enforces that invariant independently).
pub fn select_block_size(episode_net_r: &[f64], threshold: f64) -> i64 {
    let n = episode_net_r.len();
    if n < 4 {
        return 1;
    }
    let nf = n as f64;
    let mean = fsum(episode_net_r) / nf;
    let c0 = fsum(&squared_diffs(episode_net_r, mean));
    let base = (py_round(nf.powf(1.0 / 3.0)) as i64).max(1);
    if c0 == 0.0 {
        return base.min(n as i64 / 2).max(1);
    }
    let mut c1_terms = Vec::with_capacity(n - 1);
    for i in 0..n - 1 {
        c1_terms.push((episode_net_r[i] - mean) * (episode_net_r[i + 1] - mean));
    }
    let c1 = fsum(&c1_terms);
    let lag1 = c1 / c0;
    let block = if lag1.abs() > threshold { 2 * base } else { base };
    block.min(n as i64 / 2).max(1)
}

fn squared_diffs(values: &[f64], mean: f64) -> Vec<f64> {
    values.iter().map(|x| (x - mean).powf(2.0)).collect()
}

/// One circular fixed-block bootstrap draw of length `n` over `[0, n)`.
///
/// Repeatedly picks a uniform start point and appends a contiguous run of
/// `block_size` indices (wrapping past the end) until length `n` is reached,
/// then truncates. Contiguous within a block, independent across blocks —
/// the same episode-block dependence unit as preregistration section 9.
///
/// D-052 fail-closed invariant: with `block_size >= n` (and `n >= 2`) one
/// block already covers the series, every resample is a rotation holding each
/// index exactly once, and the bootstrap distribution is a point mass — a
/// zero-width interval. That must raise, exactly as the oracle's ValueError.
pub fn block_bootstrap_indices(
    n: usize,
    block_size: i64,
    rng: &mut MT19937,
) -> Result<Vec<usize>, String> {
    if n == 0 {
        return Ok(Vec::new());
    }
    if block_size <= 0 {
        return Err("block_size must be positive".to_string());
    }
    if n >= 2 && block_size >= n as i64 {
        return Err(format!(
            "block_size {block_size} >= n {n}: degenerate block bootstrap \
             (every resample is a rotation of the whole series)"
        ));
    }
    let bs = block_size as usize;
    let mut out: Vec<usize> = Vec::with_capacity(n + bs);
    while out.len() < n {
        let start = rng.randrange(n as u64) as usize;
        for j in 0..bs {
            out.push((start + j) % n);
        }
    }
    out.truncate(n);
    Ok(out)
}

/// Output of `reality_check_p_value`. `argmax_config` is the only
/// configuration that can pass preregistration section 11's within-family
/// test on this record; every other evaluated configuration fails by
/// construction of the max statistic, regardless of its own mean.
#[derive(Debug, Clone, PartialEq)]
pub struct RealityCheckResult {
    pub observed_max: f64,
    pub argmax_config: String,
    pub p_value: f64,
    pub n_resamples: i64,
    pub block_size: i64,
    pub seed: u64,
}

/// White (2000) Procedure RC max-statistic bootstrap p-value, extended to N
/// within-family configurations (D-044).
///
/// `episode_net_r` maps each evaluated `variant_id` to its ordered episode
/// `net_R` series; the slice preserves insertion order so a mean tie resolves
/// to the first configuration, exactly as the oracle's dict does. All series
/// must share the same length and episode order — true within one family
/// because every variant fires on the same setup predicate (rule 13) — which
/// lets a single per-round block draw be applied identically to every series,
/// preserving whatever correlation the shared episodes carry.
///
/// Each round recenters every configuration's resampled mean on its own
/// observed mean (the compound null), then takes the max recentered statistic
/// across configurations. The p-value is the fraction of resampled max
/// statistics that reach or exceed the observed max of the raw means. The
/// oracle raises ValueError on invalid inputs; this returns `Err` instead.
pub fn reality_check_p_value(
    episode_net_r: &[(&str, &[f64])],
    block_size: i64,
    n_resamples: i64,
    seed: u64,
) -> Result<RealityCheckResult, String> {
    if episode_net_r.is_empty() {
        return Err("no configurations supplied".to_string());
    }
    let n = episode_net_r[0].1.len();
    for (name, series) in episode_net_r {
        if series.len() != n {
            return Err(format!(
                "all configuration episode series must share length (aligned by \
                 episode index): {name} has {} but the first has {n}",
                series.len()
            ));
        }
    }
    if n == 0 {
        return Err("empty episode series".to_string());
    }
    if n_resamples <= 0 {
        return Err("n_resamples must be positive".to_string());
    }

    let nf = n as f64;
    let mut means: Vec<f64> = Vec::with_capacity(episode_net_r.len());
    for (_, series) in episode_net_r {
        means.push(fsum(series) / nf);
    }
    let observed_max = means
        .iter()
        .cloned()
        .fold(f64::NEG_INFINITY, |a, b| if b > a { b } else { a });
    let argmax_config = episode_net_r
        .iter()
        .zip(means.iter())
        .find(|(_, m)| **m == observed_max)
        .map(|(name, _)| name)
        .expect("observed_max is one of the means")
        .0
        .to_string();

    let mut rng = MT19937::new(seed);
    let mut exceed: i64 = 0;
    for _ in 0..n_resamples {
        let idx = block_bootstrap_indices(n, block_size, &mut rng)?;
        let mut round_max = f64::NEG_INFINITY;
        for (ci, (_, series)) in episode_net_r.iter().enumerate() {
            let drawn: Vec<f64> = idx.iter().map(|&i| series[i]).collect();
            let stat = fsum(&drawn) / nf - means[ci];
            if stat > round_max {
                round_max = stat;
            }
        }
        if round_max >= observed_max {
            exceed += 1;
        }
    }
    let p_value = exceed as f64 / n_resamples as f64;

    Ok(RealityCheckResult {
        observed_max,
        argmax_config,
        p_value,
        n_resamples,
        block_size,
        seed,
    })
}

/// The section-9 circular fixed-block bootstrap resample means.
///
/// One rng from `seed` drives every resample; each resample is a length-n
/// draw from `block_bootstrap_indices` — the SAME sampler
/// `reality_check_p_value` uses (METH-4 / EV_METHODS E-04): the single-config
/// percentile test and the WRC must resample identically. Bootstrap theorem:
/// resample size = original n (Aronson Ch5 p234-238). An empty series returns
/// `Ok([])`.
pub fn block_bootstrap_means(
    net_rs: &[f64],
    block_size: i64,
    n_resamples: i64,
    seed: u64,
) -> Result<Vec<f64>, String> {
    let n = net_rs.len();
    if n == 0 {
        return Ok(Vec::new());
    }
    if n_resamples <= 0 {
        return Err("n_resamples must be positive".to_string());
    }
    let mut rng = MT19937::new(seed);
    let mut means = Vec::with_capacity(n_resamples as usize);
    for _ in 0..n_resamples {
        let idx = block_bootstrap_indices(n, block_size, &mut rng)?;
        let drawn: Vec<f64> = idx.iter().map(|&i| net_rs[i]).collect();
        means.push(fsum(&drawn) / n as f64);
    }
    Ok(means)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `round()` battery captured from CPython 3.14 (`round(v)`), including
    /// exact halves, near-halves, negative halves, libm cube roots, and large
    /// magnitudes where the half is not representable.
    #[test]
    fn py_round_matches_cpython() {
        let cases: &[(f64, f64)] = &[
            (2.5, 2.0),
            (3.5, 4.0),
            (-2.5, -2.0),
            (-3.5, -4.0),
            (0.5, 0.0),
            (-0.5, 0.0),
            (1.5, 2.0),
            (-1.5, -2.0),
            (2.4999999999999996, 2.0),
            (2.5000000000000004, 3.0),
            (-2.4999999999999996, -2.0),
            (8.0_f64.powf(1.0 / 3.0), 2.0),
            (10.0_f64.powf(1.0 / 3.0), 2.0),
            (20.0_f64.powf(1.0 / 3.0), 3.0),
            (27.0_f64.powf(1.0 / 3.0), 3.0),
            (64.0_f64.powf(1.0 / 3.0), 4.0),
            (1000.0_f64.powf(1.0 / 3.0), 10.0),
            (26.0_f64.powf(1.0 / 3.0), 3.0),
            (1e30 + 0.5, 1e30),
            (9007199254740993.0, 9007199254740992.0),
            (0.0, 0.0),
            (-0.0, 0.0),
        ];
        for &(v, expected) in cases {
            assert_eq!(py_round(v), expected, "round({v})");
        }
    }

    /// `select_block_size` vs the oracle on the fixed series: the doubling
    /// tier (v1, s20, trend24), the zero-variance fallback, and the n < 4
    /// short-circuit. `threshold` defaults to 0.10 in the oracle.
    #[test]
    fn select_block_size_matches_cpython() {
        let v1 = [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2];
        assert_eq!(select_block_size(&v1, 0.10), 4);

        let v2 = [0.05, -0.15, 0.2, 0.1, 0.0, 0.1, -0.05, 0.15];
        assert_eq!(select_block_size(&v2, 0.10), 4);

        // zero variance: c0 == 0 -> base tier only
        assert_eq!(select_block_size(&[0.5; 8], 0.10), 2);

        // n < 4 short-circuit
        assert_eq!(select_block_size(&[0.1, 0.2, 0.3], 0.10), 1);

        // weak-autocorrelation 20-episode series -> base = round(20^(1/3)) = 3,
        // doubled (|lag1| > 0.10) -> 6
        let s20 = [
            -0.365636, 0.347434, 0.263775, -0.244931, -0.004565, -0.050509,
            0.151593, 0.288723, -0.40614, -0.471653, 0.335765, -0.067233,
            0.26228, -0.497894, -0.054613, 0.22154, -0.271238, 0.445271,
            0.401427, -0.46941,
        ];
        assert_eq!(select_block_size(&s20, 0.10), 6);

        // strong trend, n=24 -> base = round(24^(1/3)) = 3, doubled -> 6
        let trend24: Vec<f64> = (0..24).map(|i| 0.05 * i as f64).collect();
        assert_eq!(select_block_size(&trend24, 0.10), 6);
    }

    /// Intermediate lag-1 autocorrelation internals, bit-for-bit vs the
    /// oracle (c0 / c1 / lag1 are the exact doubles the oracle printed).
    #[test]
    fn select_block_size_internals_match_cpython() {
        let v1 = [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2];
        let mean = fsum(&v1) / 8.0;
        assert_eq!(mean, 0.08125);
        let c0 = fsum(&squared_diffs(&v1, mean));
        assert_eq!(c0, 0.2246875);
        let mut c1_terms = Vec::with_capacity(7);
        for i in 0..7 {
            c1_terms.push((v1[i] - mean) * (v1[i + 1] - mean));
        }
        let c1 = fsum(&c1_terms);
        assert_eq!(c1, -0.1350390625);
        assert_eq!(c1 / c0, -0.6010083449235049);

        let s20 = [
            -0.365636, 0.347434, 0.263775, -0.244931, -0.004565, -0.050509,
            0.151593, 0.288723, -0.40614, -0.471653, 0.335765, -0.067233,
            0.26228, -0.497894, -0.054613, 0.22154, -0.271238, 0.445271,
            0.401427, -0.46941,
        ];
        let mean20 = fsum(&s20) / 20.0;
        assert_eq!(mean20, -0.009300700000000002);
        assert_eq!(fsum(&squared_diffs(&s20, mean20)), 2.0178940095542);
        let trend24: Vec<f64> = (0..24).map(|i| 0.05 * i as f64).collect();
        let mean24 = fsum(&trend24) / 24.0;
        assert_eq!(mean24, 0.5750000000000001);
        assert_eq!(fsum(&squared_diffs(&trend24, mean24)), 2.8750000000000004);
    }

    /// The bootstrap sampler on a fresh `random.Random(42)`: the index
    /// sequence is the exact list the oracle printed for (n=8, block=4).
    #[test]
    fn block_bootstrap_indices_matches_cpython() {
        let mut rng = MT19937::new(42);
        let idx = block_bootstrap_indices(8, 4, &mut rng).unwrap();
        assert_eq!(idx, vec![1, 2, 3, 4, 0, 1, 2, 3]);
    }

    /// The WRC max-statistic test vs the oracle: fixed family, block_size
    /// from the mechanical rule, 2000 resamples, seed 42.
    #[test]
    fn reality_check_p_value_matches_cpython() {
        let a = [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2];
        let b = [0.05, -0.15, 0.2, 0.1, 0.0, 0.1, -0.05, 0.15];
        let fam: &[(&str, &[f64])] = &[("v1", &a), ("v2", &b)];
        let res = reality_check_p_value(fam, 4, 2000, 42).unwrap();
        assert_eq!(res.observed_max, 0.08125);
        assert_eq!(res.argmax_config, "v1");
        assert_eq!(res.p_value, 0.0145);
        assert_eq!(res.n_resamples, 2000);
        assert_eq!(res.block_size, 4);
        assert_eq!(res.seed, 42);
    }

    /// Mean tie: argmax resolves to the first configuration in insertion
    /// order, exactly as the oracle's dict does.
    #[test]
    fn reality_check_argmax_tie_goes_to_first_config() {
        let x = [0.2, -0.1, 0.05];
        let y = [0.1, 0.05, -0.1];
        let fam: &[(&str, &[f64])] = &[("x", &x), ("y", &y)];
        let res = reality_check_p_value(fam, 1, 100, 5).unwrap();
        assert_eq!(res.observed_max, 0.05000000000000001);
        assert_eq!(res.argmax_config, "x");
        assert_eq!(res.p_value, 0.32);
    }

    /// Zero-variance single config: every resample recentered mean equals the
    /// observed max, so the p-value saturates at 1.0.
    #[test]
    fn reality_check_zero_variance_p_is_one() {
        let ones = [0.0, 0.0, 0.0, 0.0];
        let fam: &[(&str, &[f64])] = &[("c", &ones)];
        let res = reality_check_p_value(fam, 2, 50, 3).unwrap();
        assert_eq!(res.observed_max, 0.0);
        assert_eq!(res.argmax_config, "c");
        assert_eq!(res.p_value, 1.0);
    }

    /// `block_bootstrap_means` vs the oracle for both fixed series.
    #[test]
    fn block_bootstrap_means_matches_cpython() {
        let a = [0.1, -0.2, 0.3, 0.15, -0.05, 0.25, -0.1, 0.2];
        let b = [0.05, -0.15, 0.2, 0.1, 0.0, 0.1, -0.05, 0.15];
        assert_eq!(
            block_bootstrap_means(&a, 4, 8, 7).unwrap(),
            vec![
                0.1375,
                0.04375,
                0.04999999999999999,
                0.1,
                0.075,
                0.024999999999999994,
                0.024999999999999994,
                0.056249999999999994,
            ]
        );
        assert_eq!(
            block_bootstrap_means(&b, 4, 5, 9).unwrap(),
            vec![0.0625, 0.075, 0.07500000000000001, 0.0625, 0.05]
        );
        assert_eq!(block_bootstrap_means(&[], 4, 5, 1).unwrap(), Vec::<f64>::new());
    }

    /// Fail-closed validation mirroring the oracle's ValueError paths.
    #[test]
    fn validation_matches_oracle_raises() {
        // no configurations
        assert!(reality_check_p_value(&[], 4, 100, 42).is_err());
        // misaligned series lengths
        let a = [0.1, -0.2, 0.3, 0.15];
        let b = [0.05, -0.15, 0.2];
        let fam: &[(&str, &[f64])] = &[("v1", &a), ("v2", &b)];
        assert!(reality_check_p_value(fam, 2, 100, 42).is_err());
        // empty series
        let e: &[(&str, &[f64])] = &[("v1", &[])];
        assert!(reality_check_p_value(e, 2, 100, 42).is_err());
        // non-positive resamples
        assert!(reality_check_p_value(&[("v1", &a)], 2, 0, 42).is_err());
        assert!(block_bootstrap_means(&a, 2, -1, 42).is_err());
        // degenerate block_size >= n (n >= 2)
        assert!(block_bootstrap_indices(8, 8, &mut MT19937::new(42)).is_err());
        assert!(reality_check_p_value(&[("v1", &a)], 4, 10, 42).is_err());
        // non-positive block_size
        assert!(block_bootstrap_indices(8, 0, &mut MT19937::new(42)).is_err());
        // n == 0 returns empty, not an error
        assert_eq!(
            block_bootstrap_indices(0, 4, &mut MT19937::new(42)).unwrap(),
            Vec::<usize>::new()
        );
    }
}
