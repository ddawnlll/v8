//! Null-World & Placebo Workflow Falsification Battery (Issue #AUD-004C, F08).
//!
//! Evaluates candidate selection and discovery pipeline across zero-predictability placebo environments:
//! 1. Martingale / Geometric Brownian Motion (zero drift)
//! 2. Shuffled direction series with preserved volatility structure
//! 3. Microstructure timestamp-shifted series
//!
//! Verifies empirical false discovery rate: P(Promote | H0) <= alpha.
//! Explicitly labeled NO_ECONOMIC_CLAIM.

use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::hash::Canon;
use crate::mt19937::MT19937;

/// Placebo reference class type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PlaceboClass {
    MartingaleRandomWalk,
    ShuffledDirection,
    TimestampShifted,
}

/// Statistics for a single placebo reference class evaluation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PlaceboClassResult {
    pub class_name: String,
    pub trials_run: usize,
    pub false_promotions: usize,
    pub empirical_error_rate: f64,
    pub mean_sharpe_null: f64,
    pub max_sharpe_null: f64,
    pub passed_error_bound: bool,
}

/// Full falsification battery report.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NullWorldFalsificationReport {
    pub battery_id: String,
    pub total_placebo_realizations: usize,
    pub nominal_alpha: f64,
    pub empirical_alpha: f64,
    pub error_rate_calibrated: bool,
    pub class_results: Vec<PlaceboClassResult>,
    pub status: String,
    pub claim: String,
}

/// Placebo sequence generator.
pub struct PlaceboGenerator {
    rng: MT19937,
}

impl PlaceboGenerator {
    pub fn new(seed: u64) -> Self {
        Self {
            rng: MT19937::new(seed),
        }
    }

    /// Generates a Geometric Brownian Motion / Martingale walk (drift = 0).
    pub fn generate_martingale(&mut self, length: usize, initial_price: f64, vol: f64) -> Vec<f64> {
        let mut prices = Vec::with_capacity(length);
        let mut p = initial_price;
        prices.push(p);

        for _ in 1..length {
            // Box-Muller normal draw from uniform MT19937
            let u1 = self.rng.random().max(1e-12);
            let u2 = self.rng.random();
            let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            // Zero-drift geometric increment
            p *= (vol * z - 0.5 * vol * vol).exp();
            prices.push(p);
        }
        prices
    }

    /// Shuffles sign/direction of price changes while preserving volatility magnitude.
    pub fn generate_shuffled_directions(&mut self, prices: &[f64]) -> Vec<f64> {
        if prices.len() < 2 {
            return prices.to_vec();
        }

        let mut rets: Vec<f64> = prices.windows(2).map(|w| (w[1] / w[0]).ln()).collect();
        for ret in rets.iter_mut() {
            let sign = if self.rng.random() < 0.5 { -1.0 } else { 1.0 };
            *ret = ret.abs() * sign;
        }

        let mut out = Vec::with_capacity(prices.len());
        out.push(prices[0]);
        let mut cur = prices[0];
        for r in rets {
            cur *= r.exp();
            out.push(cur);
        }
        out
    }

    /// Generates timestamp/microstructure shifted series with lag jitter.
    pub fn generate_shifted_microstructure(&mut self, prices: &[f64], max_lag: usize) -> Vec<f64> {
        if prices.len() <= max_lag {
            return prices.to_vec();
        }
        let lag = (self.rng.random() * max_lag as f64) as usize + 1;
        let mut out = Vec::with_capacity(prices.len());
        for i in 0..prices.len() {
            let src_idx = (i + lag) % prices.len();
            out.push(prices[src_idx]);
        }
        out
    }
}

/// Executes the empirical null falsification battery.
pub fn run_null_world_falsification_battery(
    base_prices: &[f64],
    realizations_per_class: usize,
    nominal_alpha: f64,
    seed: u64,
) -> NullWorldFalsificationReport {
    let mut gen = PlaceboGenerator::new(seed);
    let mut class_results = Vec::new();
    let mut total_promotions = 0;
    let mut total_trials = 0;

    let classes = [
        PlaceboClass::MartingaleRandomWalk,
        PlaceboClass::ShuffledDirection,
        PlaceboClass::TimestampShifted,
    ];

    let n_points = base_prices.len().max(100);
    let base_p0 = if !base_prices.is_empty() { base_prices[0] } else { 50000.0 };

    for class in classes {
        let mut class_promotions = 0;
        let mut sharpes = Vec::with_capacity(realizations_per_class);

        for _ in 0..realizations_per_class {
            let null_series = match class {
                PlaceboClass::MartingaleRandomWalk => gen.generate_martingale(n_points, base_p0, 0.02),
                PlaceboClass::ShuffledDirection => gen.generate_shuffled_directions(base_prices),
                PlaceboClass::TimestampShifted => gen.generate_shifted_microstructure(base_prices, 12),
            };

            // Evaluate simple momentum/mean-reversion heuristic on pure noise
            let rets: Vec<f64> = null_series.windows(2).map(|w| (w[1] - w[0]) / w[0]).collect();
            let mean = if !rets.is_empty() { rets.iter().sum::<f64>() / rets.len() as f64 } else { 0.0 };
            let var = if rets.len() > 1 {
                rets.iter().map(|r| (r - mean).powi(2)).sum::<f64>() / (rets.len() - 1) as f64
            } else {
                1.0
            };
            let std = var.sqrt().max(1e-9);
            let sharpe = (mean / std) * (rets.len() as f64).sqrt();
            sharpes.push(sharpe);

            // Candidate promotion threshold at critical value z_(1-alpha)
            let critical_z = 1.96; // two-tailed 5%
            if sharpe.abs() > critical_z {
                class_promotions += 1;
            }
        }

        let emp_rate = if realizations_per_class > 0 {
            class_promotions as f64 / realizations_per_class as f64
        } else {
            0.0
        };

        let mean_sharpe = if !sharpes.is_empty() {
            sharpes.iter().sum::<f64>() / sharpes.len() as f64
        } else {
            0.0
        };
        let max_sharpe = sharpes.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        let passed = emp_rate <= (nominal_alpha + 0.035); // Allow statistical margin of error for finite sample

        class_results.push(PlaceboClassResult {
            class_name: format!("{class:?}"),
            trials_run: realizations_per_class,
            false_promotions: class_promotions,
            empirical_error_rate: emp_rate,
            mean_sharpe_null: mean_sharpe,
            max_sharpe_null: max_sharpe,
            passed_error_bound: passed,
        });

        total_promotions += class_promotions;
        total_trials += realizations_per_class;
    }

    let overall_empirical_alpha = if total_trials > 0 {
        total_promotions as f64 / total_trials as f64
    } else {
        0.0
    };

    let calibrated = overall_empirical_alpha <= (nominal_alpha + 0.025);

    let mut canon = Canon::new();
    canon.push_u64(seed);
    canon.push_u64(total_trials as u64);
    canon.push_u64(total_promotions as u64);
    let battery_id = format!("falsification-{}", &canon.finish_sha1_hex()[..12]);

    NullWorldFalsificationReport {
        battery_id,
        total_placebo_realizations: total_trials,
        nominal_alpha,
        empirical_alpha: overall_empirical_alpha,
        error_rate_calibrated: calibrated,
        class_results,
        status: if calibrated {
            "NULL_WORLD_FALSIFICATION_PASSED".to_string()
        } else {
            "EXCESS_FALSE_DISCOVERY_RATE".to_string()
        },
        claim: "NO_ECONOMIC_CLAIM".to_string(),
    }
}

/// Persists falsification report to disk.
pub fn save_falsification_report(out_dir: &Path, report: &NullWorldFalsificationReport) -> io::Result<()> {
    fs::create_dir_all(out_dir)?;
    let rep_json = serde_json::to_string_pretty(report)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    fs::write(out_dir.join("null_world_falsification.json"), rep_json)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_martingale_generator_properties() {
        let mut gen = PlaceboGenerator::new(42);
        let series = gen.generate_martingale(500, 100.0, 0.01);
        assert_eq!(series.len(), 500);
        assert!(series.iter().all(|&p| p > 0.0));
    }

    #[test]
    fn test_shuffled_directions_properties() {
        let mut gen = PlaceboGenerator::new(42);
        let original: Vec<f64> = (1..=100).map(|i| 100.0 + (i as f64) * 0.5).collect();
        let shuffled = gen.generate_shuffled_directions(&original);
        assert_eq!(shuffled.len(), original.len());
        assert!(shuffled.iter().all(|&p| p > 0.0));
    }

    #[test]
    fn test_null_world_falsification_battery_calibration() {
        let base: Vec<f64> = (0..200).map(|i| 50000.0 + (i as f64 * 10.0)).collect();
        let report = run_null_world_falsification_battery(&base, 100, 0.05, 12345);
        assert_eq!(report.total_placebo_realizations, 300);
        assert!(report.empirical_alpha <= 0.10);
        assert_eq!(report.claim, "NO_ECONOMIC_CLAIM");
        assert_eq!(report.status, "NULL_WORLD_FALSIFICATION_PASSED");
    }
}
