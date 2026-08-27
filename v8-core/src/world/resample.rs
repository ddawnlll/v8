//! Block & Regime-Aware Resampling Engine (D-147, D-149, M2b).
//!
//! Preserves empirical dependency and volatility autocorrelation while scrambling macroeconomic ordering.

use crate::world::spec::{WorldBar, WorldReceipt, WorldSpec};

pub struct BlockResampleGenerator;

impl BlockResampleGenerator {
    pub fn resample(source_bars: &[WorldBar], block_size: usize, seed: u64, spec: &WorldSpec) -> WorldReceipt {
        assert!(block_size > 0 && !source_bars.is_empty());
        let mut bars = Vec::with_capacity(spec.n_bars);
        let n_blocks = source_bars.len() / block_size;
        let mut state = seed;
        let bar_duration_ns = 3_600_000_000_000i64;
        let mut current_ts = 1700000000000000000i64;

        let mut current_price = spec.base_price;

        while bars.len() < spec.n_bars {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let block_idx = ((state >> 32) as usize) % n_blocks.max(1);
            let start = block_idx * block_size;
            let end = (start + block_size).min(source_bars.len());

            for b in &source_bars[start..end] {
                if bars.len() >= spec.n_bars {
                    break;
                }
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
            }
        }

        WorldReceipt::new(spec.clone(), bars)
    }
}
