//! V8 Evaluation Evidence System — Counterfactual Robustness Surfaces (v8.eval.v1 §9).
//!
//! Evaluates continuous response surfaces across:
//! - Cost surface: E[R](friction_bps) in [0, 20 bps]
//! - Stop surface: E[R](Stop_R) in [0.2R, 3.0R]
//! - Target surface: E[R](Target_R) in [0.5R, 10.0R]
//! - Expiry surface: E[R](Expiry_Bars)
//! - Joint fragility metrics: Plateau width, Performance cliff, Local fragility index

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

pub const COST_GRID_BPS: [f64; 10] = [0.0, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0];
pub const STOP_MULTIPLIERS: [f64; 6] = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
pub const TARGET_MULTIPLIERS: [f64; 6] = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CostSurfacePoint {
    pub friction_bps: f64,
    pub net_expectancy_r: f64,
    pub profit_factor: f64,
    pub sharpe_ratio: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ExitSurfacePoint {
    pub stop_multiplier: f64,
    pub target_multiplier: f64,
    pub expiry_bars: usize,
    pub net_expectancy_r: f64,
    pub win_rate_pct: f64,
    pub n_trades: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FragilityMetrics {
    pub plateau_width: f64,
    pub performance_cliff: f64,
    pub local_fragility_index: f64,
    pub break_even_friction_bps: f64,
}

#[derive(Debug, Clone)]
pub struct TradeOutcomeInput {
    pub gross_r: f64,
    pub net_r: f64,
    pub mfe_r: f64,
    pub mae_r: f64,
    pub duration_bars: usize,
    pub risk_r: f64,
}

pub fn compute_cost_surface(
    trades: &[TradeOutcomeInput],
) -> (Vec<CostSurfacePoint>, f64) {
    if trades.is_empty() {
        let pts = COST_GRID_BPS
            .iter()
            .map(|&c| CostSurfacePoint {
                friction_bps: c,
                net_expectancy_r: 0.0,
                profit_factor: 0.0,
                sharpe_ratio: 0.0,
            })
            .collect();
        return (pts, 0.0);
    }

    let mut points = Vec::with_capacity(COST_GRID_BPS.len());
    let mut break_even_bps = 0.0;

    for &bps in &COST_GRID_BPS {
        let friction_r = (bps * 0.0001) / 0.01;
        let mut net_rs = Vec::with_capacity(trades.len());
        let mut pos_sum = 0.0;
        let mut neg_sum = 0.0;

        for t in trades {
            let nr = t.gross_r - friction_r;
            net_rs.push(nr);
            if nr > 0.0 {
                pos_sum += nr;
            } else {
                neg_sum += nr.abs();
            }
        }

        let n = net_rs.len() as f64;
        let mean = net_rs.iter().sum::<f64>() / n;
        let variance = if net_rs.len() > 1 {
            net_rs.iter().map(|r| (r - mean).powi(2)).sum::<f64>() / (n - 1.0)
        } else {
            0.0
        };
        let std = variance.sqrt();
        let sharpe = if std > 1e-9 { (mean / std) * n.sqrt() } else { 0.0 };
        let pf = if neg_sum > 1e-9 { pos_sum / neg_sum } else if pos_sum > 0.0 { 100.0 } else { 0.0 };

        points.push(CostSurfacePoint {
            friction_bps: bps,
            net_expectancy_r: mean,
            profit_factor: pf,
            sharpe_ratio: sharpe,
        });
    }

    // Zero-crossing search
    for i in 0..points.len().saturating_sub(1) {
        let (p1, p2) = (&points[i], &points[i + 1]);
        if p1.net_expectancy_r >= 0.0 && p2.net_expectancy_r <= 0.0 {
            let diff = p2.net_expectancy_r - p1.net_expectancy_r;
            if diff.abs() > 1e-9 {
                break_even_bps = p1.friction_bps + (0.0 - p1.net_expectancy_r) * (p2.friction_bps - p1.friction_bps) / diff;
            } else {
                break_even_bps = p1.friction_bps;
            }
            break;
        }
    }
    if break_even_bps == 0.0 && !points.is_empty() && points.last().unwrap().net_expectancy_r > 0.0 {
        break_even_bps = 50.0;
    }

    (points, break_even_bps)
}

pub fn compute_exit_surface(
    trades: &[TradeOutcomeInput],
) -> Vec<ExitSurfacePoint> {
    let mut points = Vec::new();
    if trades.is_empty() {
        return points;
    }

    for &sm in &STOP_MULTIPLIERS {
        for &tm in &TARGET_MULTIPLIERS {
            let mut sim_rs = Vec::with_capacity(trades.len());
            let mut wins = 0;

            for t in trades {
                let cost_r = (t.gross_r - t.net_r).max(0.0);
                let r = if t.mae_r >= sm {
                    -sm - cost_r
                } else if t.mfe_r >= tm {
                    tm - cost_r
                } else {
                    t.net_r
                };
                if r > 0.0 {
                    wins += 1;
                }
                sim_rs.push(r);
            }

            let n = sim_rs.len() as f64;
            let mean_r = sim_rs.iter().sum::<f64>() / n;
            let win_pct = (wins as f64 / n) * 100.0;

            points.push(ExitSurfacePoint {
                stop_multiplier: sm,
                target_multiplier: tm,
                expiry_bars: trades.first().map(|t| t.duration_bars).unwrap_or(24),
                net_expectancy_r: mean_r,
                win_rate_pct: win_pct,
                n_trades: trades.len(),
            });
        }
    }

    points
}

pub fn compute_fragility_metrics(
    exit_surface: &[ExitSurfacePoint],
    break_even_bps: f64,
) -> FragilityMetrics {
    if exit_surface.is_empty() {
        return FragilityMetrics {
            plateau_width: 0.0,
            performance_cliff: 0.0,
            local_fragility_index: 0.0,
            break_even_friction_bps: break_even_bps,
        };
    }

    let exp_vals: Vec<f64> = exit_surface.iter().map(|p| p.net_expectancy_r).collect();
    let profitable = exp_vals.iter().filter(|&&v| v > 0.0).count();
    let plateau_width = profitable as f64 / exp_vals.len() as f64;

    let mut cliff = 0.0f64;
    for i in 0..exp_vals.len().saturating_sub(1) {
        cliff = cliff.max((exp_vals[i + 1] - exp_vals[i]).abs());
    }

    let n = exp_vals.len() as f64;
    let mean = exp_vals.iter().sum::<f64>() / n;
    let variance = exp_vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;

    FragilityMetrics {
        plateau_width,
        performance_cliff: cliff,
        local_fragility_index: variance,
        break_even_friction_bps: break_even_bps,
    }
}
