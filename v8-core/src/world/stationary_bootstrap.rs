//! Politis-Romano (1994) Stationary Bootstrap Generator (D-150, Foundry v2).
//!
//! Generates resampled market worlds with geometrically distributed random block lengths.
//! Preserves weak stationary dependency and autocorrelation without fixed block boundary artifacts.

use crate::world::spec::{WorldBar, WorldReceipt, WorldSpec};

pub struct StationaryBootstrapGenerator;

impl StationaryBootstrapGenerator {
    /// Resamples empirical source bars using stationary bootstrap with mean block length p_geom = 1 / mean_block_len.
    pub fn generate(
        source_bars: &[WorldBar],
        mean_block_length: usize,
        seed: u64,
        spec: &WorldSpec,
    ) -> WorldReceipt {
        assert!(!source_bars.is_empty() && mean_block_length > 0);
        let n_src = source_bars.len();
        let p_geom = 1.0 / mean_block_length.max(1) as f64;

        let mut bars = Vec::with_capacity(spec.n_bars);
        let mut state = seed;
        let bar_duration_ns = 3_600_000_000_000i64;
        let mut current_ts = 1700000000000000000i64;
        let mut current_price = spec.base_price;

        // Pick initial random index
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let mut current_src_idx = ((state >> 32) as usize) % n_src;

        while bars.len() < spec.n_bars {
            let b = &source_bars[current_src_idx];
            let ret = b.close / b.open;
            let open = current_price;
            let close = (open * ret).max(0.01);
            let high = open.max(close) * (b.high / b.open.max(b.close));
            let low = (open.min(close) * (b.low / b.open.min(b.close))).max(0.001);

            let bar = WorldBar {
                timestamp_ns: current_ts,
                open,
                high,
                low,
                close,
                volume: b.volume,
                funding_rate: b.funding_rate,
                spread_bps: b.spread_bps,
            };
            bars.push(bar);
            current_price = close;
            current_ts += bar_duration_ns;

            // Geometric decision: start new block or increment index cyclically
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u_geom = ((state >> 32) as f64) / (u32::MAX as f64);

            if u_geom < p_geom {
                // New random starting block
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                current_src_idx = ((state >> 32) as usize) % n_src;
            } else {
                // Increment cyclically
                current_src_idx = (current_src_idx + 1) % n_src;
            }
        }

        WorldReceipt::new(spec.clone(), bars)
    }
}
