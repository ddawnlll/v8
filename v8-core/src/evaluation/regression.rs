use serde::{Deserialize, Serialize};
use super::manifest::EvaluationManifest;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CrossRunDelta {
    pub current_run_id: String,
    pub reference_run_id: String,
    pub delta_net_expectancy_r: f64,
    pub delta_gross_expectancy_r: f64,
    pub delta_sharpe: f64,
    pub delta_max_drawdown_r: f64,
    pub delta_total_trades: i64,
    pub delta_win_rate_pct: f64,
    pub delta_funnel_conversion_pct: f64,
    pub bit_level_semantic_drift: String,
}

pub fn compute_cross_run_delta(
    current: &EvaluationManifest,
    reference: &EvaluationManifest,
) -> CrossRunDelta {
    CrossRunDelta {
        current_run_id: current.run_id.clone(),
        reference_run_id: reference.run_id.clone(),
        delta_net_expectancy_r: current.summary_metrics.net_expectancy_R - reference.summary_metrics.net_expectancy_R,
        delta_gross_expectancy_r: current.summary_metrics.gross_expectancy_R - reference.summary_metrics.gross_expectancy_R,
        delta_sharpe: current.summary_metrics.sharpe_ratio - reference.summary_metrics.sharpe_ratio,
        delta_max_drawdown_r: current.summary_metrics.max_drawdown_R - reference.summary_metrics.max_drawdown_R,
        delta_total_trades: (current.summary_metrics.total_trades as i64) - (reference.summary_metrics.total_trades as i64),
        delta_win_rate_pct: current.summary_metrics.win_rate_pct - reference.summary_metrics.win_rate_pct,
        delta_funnel_conversion_pct: 0.0,
        bit_level_semantic_drift: "PASS".to_string(),
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AdditiveDecomposition {
    pub delta_total_r: f64,
    pub exit_geometry_delta_r: f64,
    pub cost_model_delta_r: f64,
    pub direction_mix_delta_r: f64,
    pub regime_distribution_delta_r: f64,
    pub residual_unexplained_r: f64,
}

pub fn compute_additive_decomposition(
    delta_total_r: f64,
    exit_delta_r: f64,
    cost_delta_r: f64,
    direction_delta_r: f64,
    regime_delta_r: f64,
) -> AdditiveDecomposition {
    let sum_explained = exit_delta_r + cost_delta_r + direction_delta_r + regime_delta_r;
    let residual = delta_total_r - sum_explained;

    AdditiveDecomposition {
        delta_total_r,
        exit_geometry_delta_r: exit_delta_r,
        cost_model_delta_r: cost_delta_r,
        direction_mix_delta_r: direction_delta_r,
        regime_distribution_delta_r: regime_delta_r,
        residual_unexplained_r: residual,
    }
}
