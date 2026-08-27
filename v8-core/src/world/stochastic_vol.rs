//! Stochastic Volatility & GARCH(1,1) Volatility Clustering Generator (D-150, Foundry v2).
//!
//! Models discrete-time GARCH(1,1) and continuous Heston-style volatility-of-volatility:
//! sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2

use crate::world::spec::{WorldBar, WorldReceipt, WorldSpec};

pub struct StochasticVolatilityGenerator;

impl StochasticVolatilityGenerator {
    pub fn generate(spec: &WorldSpec, omega: f64, alpha_garch: f64, beta_garch: f64) -> WorldReceipt {
        assert!(alpha_garch + beta_garch < 1.0, "GARCH process must be covariance-stationary");
        let mut bars = Vec::with_capacity(spec.n_bars);
        let mut price = spec.base_price;
        let mut state = spec.seed;

        let dt: f64 = 1.0 / (365.0 * 24.0);
        let dt_sqrt = dt.sqrt();
        let bar_duration_ns = 3_600_000_000_000i64;
        let mut current_ts = 1700000000000000000i64;

        // Long-run unconditional variance
        let mut current_var = omega / (1.0 - alpha_garch - beta_garch);
        let mut prev_epsilon_sq = current_var;

        for _ in 0..spec.n_bars {
            // Update GARCH variance
            current_var = omega + alpha_garch * prev_epsilon_sq + beta_garch * current_var;
            let current_vol = current_var.sqrt().clamp(0.05, 5.0);

            // PRNG steps
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u1 = (((state >> 32) as f64) / (u32::MAX as f64)).max(1e-12);
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u2 = ((state >> 32) as f64) / (u32::MAX as f64);

            let z0 = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

            let drift = -0.5 * current_vol * current_vol * dt;
            let shock = current_vol * dt_sqrt * z0;
            let ret = (drift + shock).exp();

            prev_epsilon_sq = shock * shock / dt;

            let open = price;
            let close = (open * ret).max(0.01);
            let high = (open.max(close) * (1.0 + z0.abs() * 0.002 * (current_vol / 0.5))).max(open.max(close));
            let low = (open.min(close) * (1.0 - z0.abs() * 0.002 * (current_vol / 0.5))).min(open.min(close)).max(0.001);
            let volume = (100.0 + z0.abs() * 50.0) * (current_vol / 0.5);

            let bar = WorldBar {
                timestamp_ns: current_ts,
                open,
                high,
                low,
                close,
                volume,
                funding_rate: 0.0001 * (current_vol / 0.5),
                spread_bps: (2.0 * current_vol).clamp(1.0, 50.0),
            };

            assert!(bar.is_valid());
            bars.push(bar);

            price = close;
            current_ts += bar_duration_ns;
        }

        WorldReceipt::new(spec.clone(), bars)
    }
}
