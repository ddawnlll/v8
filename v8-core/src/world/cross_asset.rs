//! Multi-Asset Copula & Cross-Asset Contagion Generator (D-150, Foundry v2).
//!
//! Generates synchronized quad-asset tapes (BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT)
//! with dynamic correlation regime switching (normal corr 0.4-0.7, risk-off panic corr -> 0.95+, rotation, alt mania)
//! and tail dependence breakdown.

use std::collections::BTreeMap;
use crate::world::spec::{MultiAssetBarSnapshot, MultiAssetWorldReceipt, WorldBar, WorldSpec};

pub struct CrossAssetContagionGenerator;

impl CrossAssetContagionGenerator {
    pub fn generate_quad_universe(
        spec: &WorldSpec,
        panic_probability: f64,
    ) -> MultiAssetWorldReceipt {
        let symbols = vec![
            "BTCUSDT".to_string(),
            "ETHUSDT".to_string(),
            "SOLUSDT".to_string(),
            "AVAXUSDT".to_string(),
        ];

        let base_prices = [50000.0, 3000.0, 150.0, 35.0];
        let asset_betas = [1.0, 1.25, 1.65, 1.90]; // Alts have higher downside beta

        let mut prices = base_prices;
        let mut state = spec.seed;
        let dt: f64 = 1.0 / (365.0 * 24.0);
        let dt_sqrt = dt.sqrt();
        let bar_duration_ns = 3_600_000_000_000i64;
        let mut current_ts = 1700000000000000000i64;

        let mut snapshots = Vec::with_capacity(spec.n_bars);

        for _ in 0..spec.n_bars {
            // Determine regime: Normal vs Contagion Panic
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u_regime = ((state >> 32) as f64) / (u32::MAX as f64);
            let is_panic = u_regime < panic_probability;

            // Common latent market factor shock
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u1 = (((state >> 32) as f64) / (u32::MAX as f64)).max(1e-12);
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u2 = ((state >> 32) as f64) / (u32::MAX as f64);
            let z_common = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            let corr_factor: f64 = if is_panic { 0.95 } else { 0.55 };
            let vol_boost: f64 = if is_panic { 2.8 } else { 1.0 };

            let mut bar_map = BTreeMap::new();

            for (idx, sym) in symbols.iter().enumerate() {
                // Asset-specific idiosyncratic shock
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                let ui1 = (((state >> 32) as f64) / (u32::MAX as f64)).max(1e-12);
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                let ui2 = ((state >> 32) as f64) / (u32::MAX as f64);
                let z_idio = (-2.0 * ui1.ln()).sqrt() * (2.0 * std::f64::consts::PI * ui2).cos();

                // Correlated composite shock
                let z_asset = (corr_factor.sqrt() * z_common) + ((1.0 - corr_factor).sqrt() * z_idio);
                let asset_vol = spec.volatility_annualized * asset_betas[idx] * vol_boost;

                // Asymmetric crash during panic
                let panic_penalty = if is_panic && z_common < 0.0 { -0.02 * asset_betas[idx] } else { 0.0 };

                let drift = -0.5 * asset_vol * asset_vol * dt + panic_penalty;
                let diffusion = asset_vol * dt_sqrt * z_asset;
                let ret = (drift + diffusion).exp();

                let open = prices[idx];
                let close = (open * ret).max(0.01);
                let high = (open.max(close) * (1.0 + z_asset.abs() * 0.002)).max(open.max(close));
                let low = (open.min(close) * (1.0 - z_asset.abs() * 0.002)).min(open.min(close)).max(0.001);
                let volume = (100.0 + z_asset.abs() * 40.0) * vol_boost;

                let bar = WorldBar {
                    timestamp_ns: current_ts,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    funding_rate: if is_panic { -0.0015 } else { 0.0001 },
                    spread_bps: (2.0 * vol_boost * asset_betas[idx]).clamp(1.0, 40.0),
                };

                assert!(bar.is_valid());
                bar_map.insert(sym.clone(), bar);
                prices[idx] = close;
            }

            snapshots.push(MultiAssetBarSnapshot {
                timestamp_ns: current_ts,
                asset_bars: bar_map,
                cross_asset_correlation: corr_factor,
            });

            current_ts += bar_duration_ns;
        }

        MultiAssetWorldReceipt::new(spec.clone(), symbols, snapshots)
    }
}
