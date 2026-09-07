//! Evaluation-layer statistical adapters.
//!
//! These functions are deliberately thin, fail-closed wrappers around the
//! registered Rust estimators. They never turn an absent or underpowered
//! population into a numeric result and they never expose the DSR proxy as a
//! genuine multiple-testing certificate.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

use crate::mt19937::MT19937;
use crate::state::fsum;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BootstrapResult {
    pub mean_net_r: f64,
    pub ci_lower_95: f64,
    pub ci_upper_95: f64,
    pub sharpe_mean: f64,
    pub sharpe_ci_lower_95: f64,
    pub sharpe_ci_upper_95: f64,
    pub p_value_greater_zero: f64,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NullModelResult {
    pub family_name: String,
    pub benchmark_mean_net_r: Option<f64>,
    pub strategy_mean_net_r: Option<f64>,
    pub delta_net_r: Option<f64>,
    pub p_value: Option<f64>,
    pub statistically_significant: Option<bool>,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PermutationResult {
    pub observed_mean: f64,
    pub p_value: f64,
    pub permuted_p5: f64,
    pub permuted_p95: f64,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProxyStatistic {
    pub value: f64,
    pub status: String,
    pub method_version: String,
    pub claim: String,
}

fn validate_series(series: &[f64], minimum: usize, label: &str) -> Result<(), String> {
    if series.len() < minimum {
        return Err(format!(
            "INCONCLUSIVE_UNDERPOWERED_{label}: observed {} values, need at least {minimum}",
            series.len()
        ));
    }
    if series.iter().any(|value| !value.is_finite()) {
        return Err(format!("DATA_BLOCKED_INVALID_{label}"));
    }
    Ok(())
}

fn percentile(sorted: &[f64], probability: f64) -> f64 {
    let index = (((sorted.len() - 1) as f64) * probability).round() as usize;
    sorted[index.min(sorted.len() - 1)]
}

fn sample_sharpe(sample: &[f64]) -> Option<f64> {
    if sample.len() < 2 {
        return None;
    }
    let mean = fsum(sample) / sample.len() as f64;
    let variance = fsum(
        &sample
            .iter()
            .map(|value| (value - mean).powi(2))
            .collect::<Vec<_>>(),
    ) / (sample.len() - 1) as f64;
    if variance > 0.0 && variance.is_finite() {
        Some(mean / variance.sqrt() * (sample.len() as f64).sqrt())
    } else {
        None
    }
}

pub fn block_bootstrap(
    returns_r: &[f64],
    block_size: usize,
    n_replications: usize,
    seed: u64,
) -> Result<BootstrapResult, String> {
    validate_series(returns_r, 3, "BOOTSTRAP_INPUT")?;
    if block_size == 0 || block_size >= returns_r.len() {
        return Err(format!(
            "BLOCKED_INVALID_BLOCK_SIZE: block_size {block_size} must be positive and smaller than n {}",
            returns_r.len()
        ));
    }
    if n_replications == 0 {
        return Err("BLOCKED_INVALID_BOOTSTRAP_REPLICATIONS".to_string());
    }
    let observed_mean = fsum(returns_r) / returns_r.len() as f64;
    let observed_variance = fsum(
        &returns_r
            .iter()
            .map(|value| (value - observed_mean).powi(2))
            .collect::<Vec<_>>(),
    ) / (returns_r.len() - 1) as f64;
    if observed_variance <= 0.0 || !observed_variance.is_finite() {
        return Err("INCONCLUSIVE_UNDERPOWERED_CONSTANT_RETURN_SERIES".to_string());
    }

    let n = returns_r.len();
    let n_blocks = (n + block_size - 1) / block_size;
    let mut rng = MT19937::new(seed);
    let mut boot_means = Vec::with_capacity(n_replications);
    let mut boot_sharpes = Vec::with_capacity(n_replications);
    for _ in 0..n_replications {
        let mut sample = Vec::with_capacity(n);
        for _ in 0..n_blocks {
            let start = rng.randrange(n as u64) as usize;
            for offset in 0..block_size {
                sample.push(returns_r[(start + offset) % n]);
                if sample.len() == n {
                    break;
                }
            }
            if sample.len() == n {
                break;
            }
        }
        let mean = fsum(&sample) / n as f64;
        boot_means.push(mean);
        if let Some(sharpe) = sample_sharpe(&sample) {
            boot_sharpes.push(sharpe);
        }
    }

    boot_means.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    boot_sharpes.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mean_net_r = fsum(returns_r) / n as f64;
    let p_value_greater_zero = (boot_means.iter().filter(|value| **value <= 0.0).count() + 1)
        as f64
        / (boot_means.len() + 1) as f64;
    if boot_sharpes.is_empty() {
        return Err("INCONCLUSIVE_UNDERPOWERED_CONSTANT_BOOTSTRAP_SERIES".to_string());
    }
    Ok(BootstrapResult {
        mean_net_r,
        ci_lower_95: percentile(&boot_means, 0.025),
        ci_upper_95: percentile(&boot_means, 0.975),
        sharpe_mean: fsum(&boot_sharpes) / boot_sharpes.len() as f64,
        sharpe_ci_lower_95: percentile(&boot_sharpes, 0.025),
        sharpe_ci_upper_95: percentile(&boot_sharpes, 0.975),
        p_value_greater_zero,
        status: "BOOTSTRAP_COMPUTED".to_string(),
    })
}

pub fn run_permutation_test(
    returns_r: &[f64],
    n_permutations: usize,
    seed: u64,
) -> Result<PermutationResult, String> {
    validate_series(returns_r, 2, "PERMUTATION_INPUT")?;
    if n_permutations == 0 {
        return Err("BLOCKED_INVALID_PERMUTATION_REPLICATIONS".to_string());
    }
    let n = returns_r.len() as f64;
    let observed_mean = fsum(returns_r) / n;
    let mut rng = MT19937::new(seed);
    let mut permuted = Vec::with_capacity(n_permutations);
    for _ in 0..n_permutations {
        let signed: Vec<f64> = returns_r
            .iter()
            .map(|value| if rng.randrange(2) == 0 { *value } else { -*value })
            .collect();
        permuted.push(fsum(&signed) / n);
    }
    permuted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let exceedances = permuted
        .iter()
        .filter(|value| **value >= observed_mean)
        .count();
    Ok(PermutationResult {
        observed_mean,
        p_value: (exceedances + 1) as f64 / (n_permutations + 1) as f64,
        permuted_p5: percentile(&permuted, 0.05),
        permuted_p95: percentile(&permuted, 0.95),
        status: "SIGN_PERMUTATION_COMPUTED".to_string(),
    })
}

#[derive(Clone, Copy)]
enum NullTransform {
    Resample,
    SignFlip,
    Invert,
}

fn computed_null_result(
    name: &str,
    returns_r: &[f64],
    n_resamples: usize,
    alpha: f64,
    rng: &mut MT19937,
    transform: NullTransform,
) -> NullModelResult {
    let n = returns_r.len();
    let observed = fsum(returns_r) / n as f64;
    let mut means = Vec::with_capacity(n_resamples);
    for _ in 0..n_resamples {
        let mut sample = Vec::with_capacity(n);
        match transform {
            NullTransform::Resample | NullTransform::Invert => {
                for _ in 0..n {
                    let value = returns_r[rng.randrange(n as u64) as usize];
                    sample.push(if matches!(transform, NullTransform::Invert) {
                        -value
                    } else {
                        value
                    });
                }
            }
            NullTransform::SignFlip => {
                for value in returns_r {
                    sample.push(if rng.randrange(2) == 0 { *value } else { -*value });
                }
            }
        }
        means.push(fsum(&sample) / n as f64);
    }
    means.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let benchmark = fsum(&means) / means.len() as f64;
    let exceedances = means.iter().filter(|value| **value >= observed).count();
    let p_value = (exceedances + 1) as f64 / (means.len() + 1) as f64;
    NullModelResult {
        family_name: name.to_string(),
        benchmark_mean_net_r: Some(benchmark),
        strategy_mean_net_r: Some(observed),
        delta_net_r: Some(observed - benchmark),
        p_value: Some(p_value),
        statistically_significant: Some(p_value < alpha),
        status: "NULL_ESTIMATE_COMPUTED_FROM_EPISODE_RETURNS".to_string(),
    }
}

fn unresolved_null_result(name: &str, strategy_mean: f64, reason: &str) -> NullModelResult {
    NullModelResult {
        family_name: name.to_string(),
        benchmark_mean_net_r: None,
        strategy_mean_net_r: Some(strategy_mean),
        delta_net_r: None,
        p_value: None,
        statistically_significant: None,
        status: reason.to_string(),
    }
}

/// Legacy entry point intentionally refuses to choose a replication count or
/// alpha implicitly. Callers must use the explicit method below.
pub fn run_10_family_null_suite(
    _returns_r: &[f64],
    _bar_closes: &[f64],
    _seed: u64,
) -> Result<Vec<NullModelResult>, String> {
    Err("BLOCKED_EXPLICIT_NULL_SUITE_CONFIGURATION_REQUIRED".to_string())
}

pub fn run_10_family_null_suite_with_resamples(
    returns_r: &[f64],
    bar_closes: &[f64],
    n_resamples: usize,
    alpha: f64,
    seed: u64,
) -> Result<Vec<NullModelResult>, String> {
    validate_series(returns_r, 3, "NULL_SUITE_INPUT")?;
    if n_resamples == 0 || !(0.0 < alpha && alpha < 1.0) {
        return Err("BLOCKED_INVALID_NULL_SUITE_CONFIGURATION".to_string());
    }
    if bar_closes.iter().any(|close| !close.is_finite() || *close <= 0.0) {
        return Err("DATA_BLOCKED_INVALID_BAR_CLOSES".to_string());
    }
    let strategy_mean = fsum(returns_r) / returns_r.len() as f64;
    let mut rng = MT19937::new(seed);
    let mut results = Vec::with_capacity(10);
    results.push(unresolved_null_result(
        "RANDOM_ENTRY_UNIFORM",
        strategy_mean,
        "UNRESOLVED_MISSING_ENTRY_EPISODE_MAPPING",
    ));
    results.push(computed_null_result(
        "RANDOM_DIRECTION",
        returns_r,
        n_resamples,
        alpha,
        &mut rng,
        NullTransform::SignFlip,
    ));
    results.push(unresolved_null_result(
        "RANDOM_TIMESTAMPS_POISSON",
        strategy_mean,
        "UNRESOLVED_MISSING_EPISODE_TIMESTAMPS",
    ));
    results.push(unresolved_null_result(
        "ALWAYS_LONG",
        strategy_mean,
        "UNRESOLVED_MISSING_DIRECTIONAL_BAR_EXECUTION_INPUT",
    ));
    results.push(unresolved_null_result(
        "ALWAYS_SHORT",
        strategy_mean,
        "UNRESOLVED_MISSING_DIRECTIONAL_BAR_EXECUTION_INPUT",
    ));
    results.push(computed_null_result(
        "INVERTED_SIGNAL",
        returns_r,
        n_resamples,
        alpha,
        &mut rng,
        NullTransform::Invert,
    ));
    results.push(computed_null_result(
        "SHUFFLED_EXPERT_LABELS",
        returns_r,
        n_resamples,
        alpha,
        &mut rng,
        NullTransform::Resample,
    ));
    results.push(unresolved_null_result(
        "MATCHED_FREQUENCY_RANDOM",
        strategy_mean,
        "UNRESOLVED_MISSING_EPISODE_FREQUENCY_INPUT",
    ));
    results.push(unresolved_null_result(
        "MATCHED_DURATION_RANDOM",
        strategy_mean,
        "UNRESOLVED_MISSING_EPISODE_DURATION_INPUT",
    ));
    results.push(unresolved_null_result(
        "MATCHED_REGIME_RANDOM",
        strategy_mean,
        "UNRESOLVED_MISSING_EPISODE_REGIME_INPUT",
    ));
    Ok(results)
}

/// A mathematically useful approximation that is explicitly a proxy. It may
/// be displayed diagnostically, but no gate may treat it as DSR authority.
pub fn compute_proxy_deflated_sharpe_ratio(
    raw_sharpe: f64,
    n_samples: usize,
    cumulative_trials_k: usize,
) -> Result<ProxyStatistic, String> {
    if !raw_sharpe.is_finite() || n_samples < 2 || cumulative_trials_k == 0 {
        return Err("BLOCKED_INVALID_PROXY_DSR_INPUT".to_string());
    }
    let gamma = 0.5772156649015329_f64;
    let log_k = (cumulative_trials_k as f64).ln();
    if log_k <= 0.0 {
        return Err("BLOCKED_INVALID_PROXY_DSR_TRIAL_COUNT".to_string());
    }
    let expected_max = (1.0 - gamma) * (2.0 * log_k).powf(-0.5) + (2.0 * log_k).sqrt();
    let variance = (1.0 + 0.5 * raw_sharpe.powi(2)) / (n_samples - 1) as f64;
    let z = (raw_sharpe - expected_max) / variance.sqrt();
    Ok(ProxyStatistic {
        value: 0.5 * (1.0 + erf(z / std::f64::consts::SQRT_2)),
        status: "PROXY_NOT_GENUINE_DSR".to_string(),
        method_version: "D153_PROXY_DSR_V1".to_string(),
        claim: "NO_ECONOMIC_CLAIM".to_string(),
    })
}

/// No genuine DSR estimator and authority receipt are registered in this
/// adapter. Refuse rather than returning a hand-written proxy under a genuine
/// statistic's name.
pub fn compute_deflated_sharpe_ratio(
    _raw_sharpe: f64,
    _n_samples: usize,
    _cumulative_trials_k: usize,
) -> Result<f64, String> {
    Err("BLOCKED_GENUINE_DSR_ESTIMATOR_AND_RECEIPT_REQUIRED".to_string())
}

fn erf(x: f64) -> f64 {
    let a1 = 0.254829592_f64;
    let a2 = -0.284496736_f64;
    let a3 = 1.421413741_f64;
    let a4 = -1.453152027_f64;
    let a5 = 1.061405429_f64;
    let p = 0.3275911_f64;
    let sign = if x < 0.0 { -1.0 } else { 1.0 };
    let t = 1.0 / (1.0 + p * x.abs());
    let y = 1.0
        - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1)
            * t
            * (-x.abs() * x.abs()).exp();
    sign * y
}
