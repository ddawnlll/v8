//! S7 detrended null (issue #124): per-episode passive benchmark, the
//! zero-skill placebo family, and the Appendix A invariant — mirror of
//! `src/v8/statistics.py` (`mean_log_drift_per_bar`, `passive_benchmark_r`,
//! `detrend_net_r`, `placebo_exposures`, `appendix_a_invariant`,
//! `invariant_holds`).
//!
//! Parity contract (PARITY_AND_IDENTITY_SPEC §3): value-level bit equality.
//! - `math.log(cur / prev)` is divide-THEN-log — `(cur / prev).ln()`, NOT
//!   `cur.ln() - prev.ln()` (the two differ in the last ulp; captured).
//! - `math.exp(...)` is `.exp()`; the argument is a runtime value so LLVM
//!   keeps the libm call (unlike the constant-exponent powf folding noted in
//!   `state.rs`).
//! - Python `sum()` is `_PyFloat_Fsum` — reductions go through `state::fsum`,
//!   never a plain left fold.
//! - `placebo_exposures` consumes `random.Random(seed)` via `crate::mt19937`
//!   (bit-exact CPython 3.14 MT19937), same draw order: `randrange` then
//!   `random()` per episode.
//!
//! Error handling: every oracle `raise ValueError` becomes `Err(String)` (the
//! v8-core convention — `simulator.rs risk_unit`, `candidate.rs`). The
//! invariant check never raises on valid input; `Err` only mirrors the
//! oracle's fail-closed paths (bad closes / params, or the empty-placebo
//! `ZeroDivisionError` that the oracle's unhandled `sum()/len()` produces).

use crate::mt19937::MT19937;
use crate::state::fsum;

/// Mirror of `statistics.py EpisodeExposure` (fields of `CounterfactualOutcome`).
#[derive(Debug, Clone, PartialEq)]
pub struct EpisodeExposure {
    pub net_r: f64,
    pub direction: &'static str, // LONG | SHORT
    pub entry_price: f64,
    pub risk_unit_price: f64, // price distance of one R at the entry fill
    pub horizon_bars: i64,
}

/// `mean_log_drift_per_bar`: sample mean of per-bar `log(cur/prev)` over the
/// SAME window the test runs on (Appendix A centering). len < 2 -> 0.0;
/// a non-positive close fails closed.
pub fn mean_log_drift_per_bar(closes: &[f64]) -> Result<f64, String> {
    if closes.len() < 2 {
        return Ok(0.0);
    }
    let mut steps = Vec::with_capacity(closes.len() - 1);
    for w in closes.windows(2) {
        let prev = w[0];
        let cur = w[1];
        if prev <= 0.0 || cur <= 0.0 {
            return Err(format!(
                "non-positive close in the drift window ({prev:?} -> {cur:?}): \
                 a log ratio is undefined; fail closed rather than skipping bars"
            ));
        }
        // Divide THEN log: `math.log(cur / prev)`. `cur.ln() - prev.ln()`
        // differs in the last ulp and is NOT the oracle.
        steps.push((cur / prev).ln());
    }
    Ok(fsum(&steps) / steps.len() as f64)
}

/// `passive_benchmark_r`: what the market handed a zero-skill position over
/// `horizon_bars`, scaled into the episode's own R unit. Costs are never
/// subtracted here — the rule's `net_R` already pays them.
pub fn passive_benchmark_r(exposure: &EpisodeExposure, mean_log_drift: f64) -> Result<f64, String> {
    let sign = match exposure.direction {
        "LONG" => 1.0,
        "SHORT" => -1.0,
        other => {
            return Err(format!(
                "direction must be LONG or SHORT (got {other:?}); a benchmark with an \
                 unknown position bias cannot be centered"
            ));
        }
    };
    if !(exposure.risk_unit_price > 0.0) {
        return Err(format!(
            "risk_unit_price must be > 0 (got {:?}): an episode with no recorded R unit \
             cannot be detrended — fail closed rather than passing its raw net_R through \
             uncentered",
            exposure.risk_unit_price
        ));
    }
    if exposure.horizon_bars <= 0 {
        return Ok(0.0);
    }
    let drift_move =
        exposure.entry_price * ((mean_log_drift * exposure.horizon_bars as f64).exp() - 1.0);
    Ok(sign * drift_move / exposure.risk_unit_price)
}

/// `detrend_net_r`: episode net_R re-centered on the same-exposure passive
/// benchmark. This is the series the hypothesis tests run on; signal
/// generation never sees it.
pub fn detrend_net_r(
    exposures: &[EpisodeExposure],
    mean_log_drift: f64,
) -> Result<Vec<f64>, String> {
    let mut out = Vec::with_capacity(exposures.len());
    for e in exposures {
        out.push(e.net_r - passive_benchmark_r(e, mean_log_drift)?);
    }
    Ok(out)
}

/// `placebo_exposures`: a zero-skill placebo family with a declared long/short
/// occupancy. Entries uniform, directions a biased coin — no predictive power
/// by construction. R unit is a FRACTION of entry price so late episodes do
/// not dwarf early ones on a multiplying tape. Deterministic for a fixed seed.
pub fn placebo_exposures(
    closes: &[f64],
    long_share: f64,
    horizon_bars: i64,
    risk_unit_frac: f64,
    n_episodes: usize,
    seed: u64,
) -> Result<Vec<EpisodeExposure>, String> {
    if !(0.0..=1.0).contains(&long_share) {
        return Err(format!("long_share must be in [0, 1] (got {long_share:?})"));
    }
    if horizon_bars <= 0 {
        return Err(format!(
            "horizon_bars must be positive (got {horizon_bars:?})"
        ));
    }
    if !(risk_unit_frac > 0.0) {
        return Err(format!(
            "risk_unit_frac must be > 0 (got {risk_unit_frac:?})"
        ));
    }
    let last_entry = closes.len() as i64 - horizon_bars - 1;
    if last_entry < 0 {
        return Err(format!(
            "window of {} closes is shorter than horizon_bars {horizon_bars}: no placebo \
             episode can complete",
            closes.len()
        ));
    }
    let mut rng = MT19937::new(seed);
    let mut out = Vec::with_capacity(n_episodes);
    for _ in 0..n_episodes {
        let i = rng.randrange((last_entry + 1) as u64) as usize;
        let direction = if rng.random() < long_share {
            "LONG"
        } else {
            "SHORT"
        };
        let sign = if direction == "LONG" { 1.0 } else { -1.0 };
        let entry = closes[i];
        let exit_close = closes[i + horizon_bars as usize];
        let unit = entry * risk_unit_frac;
        out.push(EpisodeExposure {
            net_r: sign * (exit_close - entry) / unit,
            direction,
            entry_price: entry,
            risk_unit_price: unit,
            horizon_bars,
        });
    }
    Ok(out)
}

/// Result of the Appendix A placebo check on one evaluation window.
#[derive(Debug, Clone, PartialEq)]
pub struct InvariantCheck {
    pub placebo_mean_raw: f64, // zero-skill family's mean net_R, uncentered
    pub placebo_mean_detrended: f64, // ... after subtracting its own benchmark
    pub long_share: f64,
    pub horizon_bars: i64,
    pub n_episodes: usize,
    pub seed: u64,
    pub holds: bool,
}

/// `appendix_a_invariant`: run the placebo family and report whether
/// detrending neutralised it. `holds` is decided by `invariant_holds`; this
/// function NEVER raises on valid input. The empty-placebo `ZeroDivisionError`
/// (`sum()/len()` on no episodes) is mirrored as an `Err` — fail closed, no
/// silent NaN.
pub fn appendix_a_invariant(
    closes: &[f64],
    long_share: f64,
    horizon_bars: i64,
    risk_unit_frac: f64,
    n_episodes: usize,
    seed: u64,
) -> Result<InvariantCheck, String> {
    let drift = mean_log_drift_per_bar(closes)?;
    let placebo = placebo_exposures(
        closes,
        long_share,
        horizon_bars,
        risk_unit_frac,
        n_episodes,
        seed,
    )?;
    if placebo.is_empty() {
        return Err("division by zero: empty placebo family".to_string());
    }
    let net_rs: Vec<f64> = placebo.iter().map(|e| e.net_r).collect();
    let raw = fsum(&net_rs) / placebo.len() as f64;
    let detrended_series = detrend_net_r(&placebo, drift)?;
    let detrended = fsum(&detrended_series) / detrended_series.len() as f64;
    Ok(InvariantCheck {
        placebo_mean_raw: raw,
        placebo_mean_detrended: detrended,
        long_share,
        horizon_bars,
        n_episodes,
        seed,
        holds: invariant_holds(raw, detrended),
    })
}

// METH-1 (EV_METHODS G-02) frozen tolerance for Aronson's Appendix A placebo
// invariant (preregistration choice, never fitted).
pub const INVARIANT_RELATIVE_FRACTION: f64 = 0.25; // |detrended| <= 0.25 * |raw|
pub const INVARIANT_ABSOLUTE_FLOOR_R: f64 = 0.02; // fallback when |raw| ~ 0
pub const INVARIANT_RAW_EPSILON_R: f64 = 0.01; // |raw| below this is "no bias measured"

/// `invariant_holds`: relative reading (`|detrended| <= 0.25 * |raw|`) with an
/// absolute fallback (`|detrended| <= 0.02 R`) when the window measured no
/// bias at all (`|raw| < 0.01`).
pub fn invariant_holds(placebo_mean_raw: f64, placebo_mean_detrended: f64) -> bool {
    if placebo_mean_raw.abs() < INVARIANT_RAW_EPSILON_R {
        return placebo_mean_detrended.abs() <= INVARIANT_ABSOLUTE_FLOOR_R;
    }
    placebo_mean_detrended.abs() <= INVARIANT_RELATIVE_FRACTION * placebo_mean_raw.abs()
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixed window + seed captured from the frozen oracle (src/v8/statistics.py)
    // under .venv/bin/python 3.14. Values are IEEE bit patterns.
    const CLOSES: [f64; 10] = [
        100.0, 102.0, 101.5, 105.0, 103.0, 107.5, 106.0, 110.0, 109.0, 112.0,
    ];

    fn bits(x: f64) -> u64 {
        x.to_bits()
    }

    #[test]
    fn mean_log_drift_matches_oracle() {
        let drift = mean_log_drift_per_bar(&CLOSES).unwrap();
        assert_eq!(bits(drift), 0x3f89c9dfd9dc1ab3); // 0.012592076145222597
        assert_eq!(drift, 0.012592076145222597);
    }

    /// Divide-THEN-log is load-bearing: log(102/100) differs from
    /// log(102)-log(100) in the last ulp (captured).
    #[test]
    fn drift_is_divide_then_log_not_log_diff() {
        let step = (102.0_f64 / 100.0).ln();
        assert_eq!(bits(step), 0x3f944723d272a7f6); // 0.01980262729617973
        let log_diff = 102.0_f64.ln() - 100.0_f64.ln();
        assert_eq!(bits(log_diff), 0x3f944723d272a700); // 0.019802627296178876
        assert_ne!(bits(step), bits(log_diff));
    }

    #[test]
    fn mean_log_drift_short_windows_are_zero() {
        assert_eq!(mean_log_drift_per_bar(&[]).unwrap(), 0.0);
        assert_eq!(mean_log_drift_per_bar(&[42.5]).unwrap(), 0.0);
    }

    #[test]
    fn mean_log_drift_non_positive_fails_closed() {
        let err = mean_log_drift_per_bar(&[100.0, 0.0, 105.0]).unwrap_err();
        assert!(err.contains("non-positive close"), "{err}");
    }

    #[test]
    fn passive_benchmark_matches_oracle() {
        let drift = mean_log_drift_per_bar(&CLOSES).unwrap();
        let e1 = EpisodeExposure {
            net_r: 1.25,
            direction: "LONG",
            entry_price: 100.0,
            risk_unit_price: 1.0,
            horizon_bars: 3,
        };
        let e2 = EpisodeExposure {
            net_r: -0.8,
            direction: "SHORT",
            entry_price: 105.0,
            risk_unit_price: 1.05,
            horizon_bars: 4,
        };
        let e3 = EpisodeExposure {
            net_r: 0.5,
            direction: "LONG",
            entry_price: 101.5,
            risk_unit_price: 0.015,
            horizon_bars: 2,
        };
        assert_eq!(
            bits(passive_benchmark_r(&e1, drift).unwrap()),
            0x400ecc8ef413bdd4
        );
        assert_eq!(
            bits(passive_benchmark_r(&e2, drift).unwrap()),
            0xc014a9d0cc5b6579
        );
        assert_eq!(
            bits(passive_benchmark_r(&e3, drift).unwrap()),
            0x40659274abe856d7
        );
    }

    #[test]
    fn passive_benchmark_zero_horizon_is_zero() {
        let e = EpisodeExposure {
            net_r: 1.0,
            direction: "LONG",
            entry_price: 100.0,
            risk_unit_price: 1.0,
            horizon_bars: 0,
        };
        assert_eq!(passive_benchmark_r(&e, 0.01).unwrap(), 0.0);
    }

    #[test]
    fn passive_benchmark_bad_input_fails_closed() {
        let bad_dir = EpisodeExposure {
            net_r: 1.0,
            direction: "FLAT",
            entry_price: 100.0,
            risk_unit_price: 1.0,
            horizon_bars: 3,
        };
        assert!(passive_benchmark_r(&bad_dir, 0.01)
            .unwrap_err()
            .contains("direction must be LONG or SHORT"));
        let bad_unit = EpisodeExposure {
            net_r: 1.0,
            direction: "LONG",
            entry_price: 100.0,
            risk_unit_price: 0.0,
            horizon_bars: 3,
        };
        assert!(passive_benchmark_r(&bad_unit, 0.01)
            .unwrap_err()
            .contains("risk_unit_price must be > 0"));
    }

    #[test]
    fn detrend_net_r_matches_oracle() {
        let drift = mean_log_drift_per_bar(&CLOSES).unwrap();
        let exposures = vec![
            EpisodeExposure {
                net_r: 1.25,
                direction: "LONG",
                entry_price: 100.0,
                risk_unit_price: 1.0,
                horizon_bars: 3,
            },
            EpisodeExposure {
                net_r: -0.8,
                direction: "SHORT",
                entry_price: 105.0,
                risk_unit_price: 1.05,
                horizon_bars: 4,
            },
            EpisodeExposure {
                net_r: 0.5,
                direction: "LONG",
                entry_price: 101.5,
                risk_unit_price: 0.015,
                horizon_bars: 2,
            },
        ];
        let det = detrend_net_r(&exposures, drift).unwrap();
        let expected_bits = [0xc004cc8ef413bdd4, 0x4011769d99283246, 0xc0658274abe856d7];
        for (got, want) in det.iter().zip(expected_bits) {
            assert_eq!(bits(*got), want);
        }
    }

    #[test]
    fn placebo_exposures_match_oracle_family() {
        // Captured from the oracle: long_share=0.65, horizon_bars=3,
        // risk_unit_frac=0.01, n_episodes=8, seed=12345.
        let pl = placebo_exposures(&CLOSES, 0.65, 3, 0.01, 8, 12345).unwrap();
        let expected: &[(&str, u64, f64, f64)] = &[
            ("SHORT", 0xbfee79e79e79e79e, 105.0, 1.05), // -0.9523809523809523
            ("SHORT", 0xc016a439f656f182, 106.0, 1.06), // -5.660377358490566
            ("SHORT", 0xc017a533b455c0f1, 101.5, 1.0150000000000001), // -5.911330049261083
            ("LONG", 0x3fef5f5f5f5f5f5f, 102.0, 1.02),  // 0.9803921568627451
            ("LONG", 0x3fee79e79e79e79e, 105.0, 1.05),  // 0.9523809523809523
            ("SHORT", 0xc014000000000000, 100.0, 1.0),  // -5.0
            ("LONG", 0x4017a533b455c0f1, 101.5, 1.0150000000000001), // 5.911330049261083
            ("LONG", 0x3fef5f5f5f5f5f5f, 102.0, 1.02),  // 0.9803921568627451
        ];
        assert_eq!(pl.len(), 8);
        for (got, (dir, net_bits, entry, unit)) in pl.iter().zip(expected) {
            assert_eq!(got.direction, *dir, "direction");
            assert_eq!(bits(got.net_r), *net_bits, "net_r {dir}");
            assert_eq!(bits(got.entry_price), bits(*entry), "entry {dir}");
            assert_eq!(bits(got.risk_unit_price), bits(*unit), "unit {dir}");
            assert_eq!(got.horizon_bars, 3);
        }
    }

    #[test]
    fn placebo_exposures_bad_params_fail_closed() {
        assert!(placebo_exposures(&CLOSES, 1.5, 3, 0.01, 4, 1)
            .unwrap_err()
            .contains("long_share must be in [0, 1]"));
        assert!(placebo_exposures(&CLOSES, 0.5, 0, 0.01, 4, 1)
            .unwrap_err()
            .contains("horizon_bars must be positive"));
        assert!(placebo_exposures(&CLOSES, 0.5, 3, -0.1, 4, 1)
            .unwrap_err()
            .contains("risk_unit_frac must be > 0"));
        assert!(placebo_exposures(&CLOSES, 0.5, 20, 0.01, 4, 1)
            .unwrap_err()
            .contains("shorter than horizon_bars"));
        // n_episodes=0 is legal: an empty family.
        assert!(placebo_exposures(&CLOSES, 0.5, 3, 0.01, 0, 7)
            .unwrap()
            .is_empty());
    }

    #[test]
    fn appendix_a_invariant_matches_oracle() {
        let ic = appendix_a_invariant(&CLOSES, 0.65, 3, 0.01, 8, 12345).unwrap();
        assert_eq!(bits(ic.placebo_mean_raw), 0xbff166310f3f8cd5); // -1.0874491305956344
        assert_eq!(bits(ic.placebo_mean_detrended), 0xbff166310f3f8cd5);
        assert_eq!(ic.long_share, 0.65);
        assert_eq!(ic.horizon_bars, 3);
        assert_eq!(ic.n_episodes, 8);
        assert_eq!(ic.seed, 12345);
        assert!(!ic.holds); // |detrended| == |raw|: 25% relative tolerance fails
    }

    #[test]
    fn appendix_a_invariant_empty_family_fails_closed() {
        let err = appendix_a_invariant(&CLOSES, 0.5, 3, 0.01, 0, 7).unwrap_err();
        assert!(err.contains("empty placebo family"), "{err}");
    }

    #[test]
    fn invariant_holds_matches_oracle() {
        // Captured truth table from the oracle.
        assert!(invariant_holds(0.0, 0.0));
        assert!(!invariant_holds(0.005, 0.03)); // raw ~0 -> abs floor 0.02
        assert!(invariant_holds(0.005, 0.019));
        assert!(invariant_holds(1.0, 0.2)); // 0.2 <= 0.25
        assert!(!invariant_holds(1.0, 0.2500001));
        assert!(invariant_holds(-1.0, -0.249)); // abs handles signs
        assert!(!invariant_holds(-1.0, 0.251));
    }
}
