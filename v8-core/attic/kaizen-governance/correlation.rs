//! Cross-Asset Crypto-Beta Clustering & Portfolio Heat Allocation (Issue #221 / PORT-001).
//! Normative Traceability: D-023, D-110, D-123, VENUE_AND_CAPITAL_SIMULATION_SPEC §2.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetReturnSeries {
    pub symbol: String,
    pub returns: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterAllocationResult {
    pub cluster_name: String,
    pub active_symbols: Vec<String>,
    pub mean_pairwise_correlation: f64,
    pub current_cluster_heat_r: f64,
    pub max_allowed_cluster_heat_r: f64, // D-023 limit: 3.0R
    pub admission_granted: bool,
    pub rejection_reason: Option<String>,
}

pub struct CrossAssetCorrelationClusterer;

impl CrossAssetCorrelationClusterer {
    /// Compute Pearson correlation coefficient between two equal-length return series.
    pub fn compute_correlation(x: &[f64], y: &[f64]) -> f64 {
        if x.len() != y.len() || x.len() < 10 {
            return 1.0; // Fail safe to maximum correlation
        }

        let n = x.len() as f64;
        let mean_x = x.iter().sum::<f64>() / n;
        let mean_y = y.iter().sum::<f64>() / n;

        let mut cov = 0.0;
        let mut var_x = 0.0;
        let mut var_y = 0.0;

        for i in 0..x.len() {
            let dx = x[i] - mean_x;
            let dy = y[i] - mean_y;
            cov += dx * dy;
            var_x += dx * dx;
            var_y += dy * dy;
        }

        if var_x <= 1e-12 || var_y <= 1e-12 {
            return 1.0;
        }

        (cov / (var_x.sqrt() * var_y.sqrt())).clamp(-1.0, 1.0)
    }

    /// Evaluate new asset entry under Crypto-Beta cluster risk ceiling.
    pub fn evaluate_cluster_entry(
        candidate_symbol: &str,
        candidate_risk_r: f64,
        open_symbol_heats_r: &BTreeMap<String, f64>,
        recent_returns_map: &BTreeMap<String, Vec<f64>>,
        max_cluster_heat_r: f64, // e.g. 3.0R
    ) -> ClusterAllocationResult {
        let mut active_symbols: Vec<String> = open_symbol_heats_r.keys().cloned().collect();
        if !active_symbols.contains(&candidate_symbol.to_string()) {
            active_symbols.push(candidate_symbol.to_string());
        }

        // Calculate mean pairwise correlation among active symbols in the crypto cluster
        let mut sum_corr = 0.0;
        let mut pairs = 0;

        for i in 0..active_symbols.len() {
            for j in i + 1..active_symbols.len() {
                let s1 = &active_symbols[i];
                let s2 = &active_symbols[j];

                let corr = match (recent_returns_map.get(s1), recent_returns_map.get(s2)) {
                    (Some(r1), Some(r2)) => Self::compute_correlation(r1, r2),
                    _ => 1.0, // missing data -> worst case correlation = 1.0
                };
                sum_corr += corr;
                pairs += 1;
            }
        }

        let mean_corr = if pairs > 0 { sum_corr / pairs as f64 } else { 1.0 };

        // Current sum of heat across crypto cluster
        let current_heat: f64 = open_symbol_heats_r.values().sum();
        let projected_heat = current_heat + candidate_risk_r;

        if projected_heat > max_cluster_heat_r {
            return ClusterAllocationResult {
                cluster_name: "CRYPTO_BETA_CLUSTER".to_string(),
                active_symbols,
                mean_pairwise_correlation: mean_corr,
                current_cluster_heat_r: current_heat,
                max_allowed_cluster_heat_r: max_cluster_heat_r,
                admission_granted: false,
                rejection_reason: Some(format!(
                    "PROJECTED_CLUSTER_HEAT_EXCEEDED: {:.2}R > {:.2}R (rho={:.2})",
                    projected_heat, max_cluster_heat_r, mean_corr
                )),
            };
        }

        ClusterAllocationResult {
            cluster_name: "CRYPTO_BETA_CLUSTER".to_string(),
            active_symbols,
            mean_pairwise_correlation: mean_corr,
            current_cluster_heat_r: current_heat,
            max_allowed_cluster_heat_r: max_cluster_heat_r,
            admission_granted: true,
            rejection_reason: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_high_correlation_cluster_caps_total_heat() {
        let mut heats = BTreeMap::new();
        heats.insert("BTCUSDT".to_string(), 1.5);
        heats.insert("ETHUSDT".to_string(), 1.0);

        let mut returns = BTreeMap::new();
        returns.insert("BTCUSDT".to_string(), vec![0.01, 0.02, -0.01, 0.03, 0.02]);
        returns.insert("ETHUSDT".to_string(), vec![0.012, 0.021, -0.009, 0.032, 0.021]);
        returns.insert("SOLUSDT".to_string(), vec![0.015, 0.025, -0.012, 0.035, 0.024]);

        // Attempting to add SOL with 1.0R risk (1.5 + 1.0 + 1.0 = 3.5R > 3.0R cap)
        let res = CrossAssetCorrelationClusterer::evaluate_cluster_entry(
            "SOLUSDT",
            1.0,
            &heats,
            &returns,
            3.0,
        );

        assert!(!res.admission_granted);
        assert!(res.rejection_reason.unwrap().contains("PROJECTED_CLUSTER_HEAT_EXCEEDED"));
    }
}
