//! 9-State Markov Regime & Hawkes Jump Self-Exciting Structural Market Generator (D-147, D-149, D-150, Foundry v2).
//!
//! Models latent market regimes:
//! R_t in { TREND_UP, TREND_DOWN, LOW_VOL_RANGE, HIGH_VOL_CHOP, EUPHORIA, CAPITULATION, LIQUIDATION_CASCADE, RECOVERY, SLOW_BLEED }
//! with dynamic transition matrix, Hawkes clustered jump intensity, and asymmetric tail returns.

use serde::{Deserialize, Serialize};
use crate::world::spec::{WorldBar, WorldReceipt, WorldSpec};

/// Latent market regime states (9 states).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum MarketRegimeState {
    TrendUp,
    TrendDown,
    LowVolRange,
    HighVolChop,
    Euphoria,
    Capitulation,
    LiquidationCascade,
    Recovery,
    SlowBleed,
}

impl MarketRegimeState {
    pub fn all() -> [MarketRegimeState; 9] {
        [
            MarketRegimeState::TrendUp,
            MarketRegimeState::TrendDown,
            MarketRegimeState::LowVolRange,
            MarketRegimeState::HighVolChop,
            MarketRegimeState::Euphoria,
            MarketRegimeState::Capitulation,
            MarketRegimeState::LiquidationCascade,
            MarketRegimeState::Recovery,
            MarketRegimeState::SlowBleed,
        ]
    }

    pub fn base_drift(&self) -> f64 {
        match self {
            MarketRegimeState::TrendUp => 0.45,
            MarketRegimeState::TrendDown => -0.40,
            MarketRegimeState::LowVolRange => 0.0,
            MarketRegimeState::HighVolChop => -0.05,
            MarketRegimeState::Euphoria => 1.20,
            MarketRegimeState::Capitulation => -1.50,
            MarketRegimeState::LiquidationCascade => -2.80,
            MarketRegimeState::Recovery => 0.80,
            MarketRegimeState::SlowBleed => -0.15,
        }
    }

    pub fn vol_multiplier(&self) -> f64 {
        match self {
            MarketRegimeState::TrendUp => 0.90,
            MarketRegimeState::TrendDown => 1.30,
            MarketRegimeState::LowVolRange => 0.45,
            MarketRegimeState::HighVolChop => 1.60,
            MarketRegimeState::Euphoria => 2.20,
            MarketRegimeState::Capitulation => 3.50,
            MarketRegimeState::LiquidationCascade => 5.00,
            MarketRegimeState::Recovery => 1.80,
            MarketRegimeState::SlowBleed => 0.60,
        }
    }

    pub fn jump_intensity_multiplier(&self) -> f64 {
        match self {
            MarketRegimeState::TrendUp => 0.5,
            MarketRegimeState::TrendDown => 1.5,
            MarketRegimeState::LowVolRange => 0.1,
            MarketRegimeState::HighVolChop => 1.8,
            MarketRegimeState::Euphoria => 2.5,
            MarketRegimeState::Capitulation => 4.0,
            MarketRegimeState::LiquidationCascade => 8.0,
            MarketRegimeState::Recovery => 1.2,
            MarketRegimeState::SlowBleed => 0.3,
        }
    }

    pub fn volume_multiplier(&self) -> f64 {
        match self {
            MarketRegimeState::TrendUp => 1.4,
            MarketRegimeState::TrendDown => 1.8,
            MarketRegimeState::LowVolRange => 0.5,
            MarketRegimeState::HighVolChop => 1.5,
            MarketRegimeState::Euphoria => 3.5,
            MarketRegimeState::Capitulation => 4.5,
            MarketRegimeState::LiquidationCascade => 6.0,
            MarketRegimeState::Recovery => 2.2,
            MarketRegimeState::SlowBleed => 0.4,
        }
    }

    pub fn funding_rate(&self) -> f64 {
        match self {
            MarketRegimeState::TrendUp => 0.0003,
            MarketRegimeState::TrendDown => -0.0001,
            MarketRegimeState::LowVolRange => 0.00005,
            MarketRegimeState::HighVolChop => 0.0001,
            MarketRegimeState::Euphoria => 0.0015,
            MarketRegimeState::Capitulation => -0.0010,
            MarketRegimeState::LiquidationCascade => -0.0025,
            MarketRegimeState::Recovery => 0.0002,
            MarketRegimeState::SlowBleed => 0.0001,
        }
    }
}

/// 9x9 Markov Transition Probability Matrix.
pub struct RegimeTransitionMatrix;

impl RegimeTransitionMatrix {
    pub fn next_state(current: MarketRegimeState, u: f64) -> MarketRegimeState {
        // Diagonal persistence: ~85% chance to stay in same regime
        if u < 0.85 {
            return current;
        }

        let rem = (u - 0.85) / 0.15;
        match current {
            MarketRegimeState::TrendUp => {
                if rem < 0.40 { MarketRegimeState::Euphoria }
                else if rem < 0.70 { MarketRegimeState::HighVolChop }
                else { MarketRegimeState::SlowBleed }
            }
            MarketRegimeState::Euphoria => {
                if rem < 0.50 { MarketRegimeState::Capitulation }
                else if rem < 0.80 { MarketRegimeState::LiquidationCascade }
                else { MarketRegimeState::HighVolChop }
            }
            MarketRegimeState::Capitulation | MarketRegimeState::LiquidationCascade => {
                if rem < 0.60 { MarketRegimeState::Recovery }
                else if rem < 0.85 { MarketRegimeState::HighVolChop }
                else { MarketRegimeState::SlowBleed }
            }
            MarketRegimeState::Recovery => {
                if rem < 0.50 { MarketRegimeState::TrendUp }
                else if rem < 0.80 { MarketRegimeState::LowVolRange }
                else { MarketRegimeState::HighVolChop }
            }
            MarketRegimeState::LowVolRange => {
                if rem < 0.40 { MarketRegimeState::TrendUp }
                else if rem < 0.70 { MarketRegimeState::TrendDown }
                else { MarketRegimeState::SlowBleed }
            }
            MarketRegimeState::HighVolChop => {
                if rem < 0.35 { MarketRegimeState::LowVolRange }
                else if rem < 0.65 { MarketRegimeState::TrendDown }
                else { MarketRegimeState::Capitulation }
            }
            MarketRegimeState::TrendDown | MarketRegimeState::SlowBleed => {
                if rem < 0.40 { MarketRegimeState::Capitulation }
                else if rem < 0.70 { MarketRegimeState::LowVolRange }
                else { MarketRegimeState::Recovery }
            }
        }
    }
}

/// Deterministic structural market generator with 9-state Markov regime & Hawkes jumps.
pub struct StructuralWorldGenerator;

impl StructuralWorldGenerator {
    pub fn generate(spec: &WorldSpec) -> WorldReceipt {
        let mut bars = Vec::with_capacity(spec.n_bars);
        let mut price = spec.base_price;
        let mut state = spec.seed;

        let dt: f64 = 1.0 / (365.0 * 24.0); // 1 hour steps
        let dt_sqrt = dt.sqrt();
        let bar_duration_ns = 3_600_000_000_000i64;
        let mut current_ts = 1700000000000000000i64;

        let mut current_regime = MarketRegimeState::LowVolRange;
        let mut hawkes_intensity: f64 = 0.0;
        let hawkes_decay: f64 = 0.85; // beta decay per step
        let hawkes_alpha: f64 = 1.5;  // self-exciting jump booster

        for _ in 0..spec.n_bars {
            // Step LCG PRNG
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u_regime = ((state >> 32) as f64) / (u32::MAX as f64);
            current_regime = RegimeTransitionMatrix::next_state(current_regime, u_regime);

            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u1 = (((state >> 32) as f64) / (u32::MAX as f64)).max(1e-12);
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u2 = ((state >> 32) as f64) / (u32::MAX as f64);

            // Box-Muller normal transform
            let z0 = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            // Regime-adjusted annualized drift and volatility
            let eff_drift = current_regime.base_drift();
            let eff_vol = spec.volatility_annualized * current_regime.vol_multiplier();

            let drift_step = (eff_drift - 0.5 * eff_vol * eff_vol) * dt;
            let diff_step = eff_vol * dt_sqrt * z0;
            let mut ret = (drift_step + diff_step).exp();

            // Hawkes Jump Process: lambda(t) = mu * mult + hawkes_intensity
            hawkes_intensity *= hawkes_decay;
            let base_lambda = spec.jump_frequency * current_regime.jump_intensity_multiplier() * dt;
            let total_jump_prob = (base_lambda + hawkes_intensity * dt).clamp(0.0, 0.95);

            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let jump_u = ((state >> 32) as f64) / (u32::MAX as f64);

            if jump_u < total_jump_prob {
                // Self-exciting Hawkes boost
                hawkes_intensity += hawkes_alpha;
                // Asymmetric jump magnitude: negative cascades during Capitulation/Cascade
                let jump_mean = match current_regime {
                    MarketRegimeState::LiquidationCascade => -0.06,
                    MarketRegimeState::Capitulation => -0.04,
                    MarketRegimeState::Euphoria => 0.04,
                    _ => spec.jump_mean,
                };
                let jump_magnitude = jump_mean + spec.jump_std * z0;
                ret *= jump_magnitude.exp();
            }

            let open = price;
            let close = (open * ret).max(0.01);
            let wick_high_mult = 1.0 + (z0.abs() * 0.003 * current_regime.vol_multiplier());
            let wick_low_mult = 1.0 - (z0.abs() * 0.003 * current_regime.vol_multiplier());

            let high = (open.max(close) * wick_high_mult).max(open.max(close));
            let low = (open.min(close) * wick_low_mult).min(open.min(close)).max(0.001);
            let volume = (100.0 + (z0.abs() * 60.0)) * current_regime.volume_multiplier();

            let bar = WorldBar {
                timestamp_ns: current_ts,
                open,
                high,
                low,
                close,
                volume,
                funding_rate: current_regime.funding_rate(),
                spread_bps: (2.0 * current_regime.vol_multiplier()).clamp(1.0, 30.0),
            };

            assert!(bar.is_valid(), "Generated structural bar violated OHLC invariants");
            bars.push(bar);

            price = close;
            current_ts += bar_duration_ns;
        }

        WorldReceipt::new(spec.clone(), bars)
    }
}
