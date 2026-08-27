//! Metamorphic Relation & Symmetry Stress Generator (D-150, Foundry v2).
//!
//! Evaluates policy behavioral consistency across fundamental mathematical transforms:
//! 1. Scale Invariance: P -> P * k
//! 2. Sign Inversion / Mirror Symmetry: Long returns -> Short returns
//! 3. Time Inversion: Reversed chronologies
//! 4. Permutation Invariance: Preserving marginal moments under randomized ordering

use crate::world::spec::{WorldBar, WorldReceipt, WorldSpec};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MetamorphicTransform {
    Scale(u32), // Multiply all price levels by factor (e.g. 10x)
    MirrorInversion, // Invert price changes (P_t = P_0 * exp(-log(P_orig / P_0)))
    TimeReversal, // Reverse time sequence
}

pub struct MetamorphicWorldGenerator;

impl MetamorphicWorldGenerator {
    pub fn transform(source_bars: &[WorldBar], transform: MetamorphicTransform, spec: &WorldSpec) -> WorldReceipt {
        assert!(!source_bars.is_empty());
        let mut bars = Vec::with_capacity(source_bars.len());

        match transform {
            MetamorphicTransform::Scale(factor) => {
                let k = factor.max(1) as f64;
                for b in source_bars {
                    let bar = WorldBar {
                        timestamp_ns: b.timestamp_ns,
                        open: b.open * k,
                        high: b.high * k,
                        low: b.low * k,
                        close: b.close * k,
                        volume: b.volume,
                        funding_rate: b.funding_rate,
                        spread_bps: b.spread_bps,
                    };
                    assert!(bar.is_valid());
                    bars.push(bar);
                }
            }
            MetamorphicTransform::MirrorInversion => {
                let p0 = spec.base_price;
                let mut current_price = p0;
                let bar_duration_ns = 3_600_000_000_000i64;
                let mut current_ts = 1700000000000000000i64;

                for b in source_bars {
                    let inv_ret = b.open / b.close.max(1e-6); // Inverse return
                    let open = current_price;
                    let close = (open * inv_ret).max(0.01);
                    let high = (open.max(close) * (b.open / b.low.max(1e-6))).max(open.max(close));
                    let low = (open.min(close) * (b.open / b.high.max(1e-6))).min(open.min(close)).max(0.001);

                    let bar = WorldBar {
                        timestamp_ns: current_ts,
                        open,
                        high,
                        low,
                        close,
                        volume: b.volume,
                        funding_rate: -b.funding_rate,
                        spread_bps: b.spread_bps,
                    };
                    assert!(bar.is_valid());
                    bars.push(bar);
                    current_price = close;
                    current_ts += bar_duration_ns;
                }
            }
            MetamorphicTransform::TimeReversal => {
                let bar_duration_ns = 3_600_000_000_000i64;
                let mut current_ts = 1700000000000000000i64;
                for b in source_bars.iter().rev() {
                    let bar = WorldBar {
                        timestamp_ns: current_ts,
                        open: b.close,
                        high: b.high,
                        low: b.low,
                        close: b.open,
                        volume: b.volume,
                        funding_rate: b.funding_rate,
                        spread_bps: b.spread_bps,
                    };
                    assert!(bar.is_valid());
                    bars.push(bar);
                    current_ts += bar_duration_ns;
                }
            }
        }

        WorldReceipt::new(spec.clone(), bars)
    }
}
