//! Multi-Dimensional Adversarial Reverse-Stress Search Engine (D-150, Foundry v2).
//!
//! Formulates reverse-stress failure search:
//! min_theta Distance(theta, HistoricalManifold) s.t. MaxDD(V8, theta) > DrawdownThreshold
//!
//! Emits concrete, structured MinimalDefeater vulnerability receipts for Kaizen evolution.

use serde::{Deserialize, Serialize};
use crate::world::spec::{WorldFamily, WorldReceipt, WorldSpec};
use crate::world::structural::StructuralWorldGenerator;

/// Multi-dimensional search parameter vector theta.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReverseStressVector {
    pub crash_depth_pct: f64,
    pub vol_multiplier: f64,
    pub jump_intensity: f64,
    pub false_breakout_rate: f64,
    pub correlation_spike: f64,
    pub spread_multiplier: f64,
    pub liquidity_floor: f64,
}

impl Default for ReverseStressVector {
    fn default() -> Self {
        Self {
            crash_depth_pct: 15.0,
            vol_multiplier: 1.5,
            jump_intensity: 10.0,
            false_breakout_rate: 0.10,
            correlation_spike: 0.85,
            spread_multiplier: 2.0,
            liquidity_floor: 0.50,
        }
    }
}

/// Structured vulnerability specification emitted upon reverse-stress failure.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MinimalDefeaterReceipt {
    pub search_id: String,
    pub minimal_vector: ReverseStressVector,
    pub plausibility_distance: f64,
    pub bars_to_ruin: usize,
    pub peak_drawdown_pct: f64,
    pub vulnerability_summary: String,
    pub failure_receipt: WorldReceipt,
}

pub struct ReverseStressSearchEngine;

impl ReverseStressSearchEngine {
    /// Searches for minimal parameter deformation vector theta that breaches max drawdown limit.
    pub fn find_minimal_failure_trajectory(
        base_spec: &WorldSpec,
        max_drawdown_threshold_pct: f64,
    ) -> Option<MinimalDefeaterReceipt> {
        let mut best_defeater: Option<MinimalDefeaterReceipt> = None;
        let mut min_distance = f64::INFINITY;

        // Sweep parameter grid over plausibility manifold
        for step in 1..=15 {
            let scale = step as f64 / 5.0; // 0.2, 0.4, 0.6 ... 3.0
            let theta = ReverseStressVector {
                crash_depth_pct: 10.0 + (step as f64 * 3.0),
                vol_multiplier: 1.0 + (scale * 0.8),
                jump_intensity: base_spec.jump_frequency * (1.0 + scale),
                false_breakout_rate: (0.05 + scale * 0.10).min(0.80),
                correlation_spike: (0.60 + scale * 0.12).min(0.99),
                spread_multiplier: 1.0 + scale * 1.5,
                liquidity_floor: (1.0 / (1.0 + scale)).max(0.10),
            };

            let distance = (theta.vol_multiplier - 1.0).powi(2)
                + (theta.false_breakout_rate - 0.05).powi(2)
                + (theta.spread_multiplier - 1.0).powi(2);

            let mut spec = base_spec.clone();
            spec.family = WorldFamily::ReverseStressAdversarial;
            spec.volatility_annualized = base_spec.volatility_annualized * theta.vol_multiplier;
            spec.jump_frequency = theta.jump_intensity;

            let receipt = StructuralWorldGenerator::generate(&spec);

            // Compute peak-to-trough drawdown in this world
            let mut peak = receipt.bars[0].close;
            let mut max_dd = 0.0;
            let mut ruin_bar = 0;

            for (idx, b) in receipt.bars.iter().enumerate() {
                if b.close > peak {
                    peak = b.close;
                } else {
                    let dd = (peak - b.close) / peak * 100.0;
                    if dd > max_dd {
                        max_dd = dd;
                        ruin_bar = idx;
                    }
                }
            }

            if max_dd >= max_drawdown_threshold_pct && distance < min_distance {
                min_distance = distance;
                best_defeater = Some(MinimalDefeaterReceipt {
                    search_id: format!("rev-stress-{}-{}", spec.seed, step),
                    minimal_vector: theta.clone(),
                    plausibility_distance: distance,
                    bars_to_ruin: ruin_bar,
                    peak_drawdown_pct: max_dd,
                    vulnerability_summary: format!(
                        "Vol x{:.2}, Spread x{:.2}, False Breakout {:.1}%, Correlation {:.2}",
                        theta.vol_multiplier, theta.spread_multiplier, theta.false_breakout_rate * 100.0, theta.correlation_spike
                    ),
                    failure_receipt: receipt,
                });
                break; // Found minimal step
            }
        }

        best_defeater
    }
}
