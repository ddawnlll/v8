//! Path Topology & Trajectory Geometry Generator (D-150, Foundry v2).
//!
//! Generates paths with IDENTICAL terminal return (e.g. +30%) across divergent path topologies:
//! - Path A: Monotonic Steady Trend
//! - Path B: Excursion, Sharp Crash, then Recovery
//! - Path C: Immediate Deep Drawdown, then Slow Grind Up
//!
//! Tests trailing stops, re-entries, MFE/MAE retention, and campaign recovery.

use crate::world::spec::{WorldBar, WorldReceipt, WorldSpec};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PathGeometryType {
    MonotonicTrend,
    ExcursionCrashRecovery,
    ImmediateDrawdownGrind,
}

pub struct PathTopologyGenerator;

impl PathTopologyGenerator {
    pub fn generate(
        spec: &WorldSpec,
        terminal_return_mult: f64, // e.g. 1.30 for +30%
        geometry: PathGeometryType,
    ) -> WorldReceipt {
        assert!(spec.n_bars >= 10);
        let mut bars = Vec::with_capacity(spec.n_bars);
        let base_price = spec.base_price;
        let terminal_target = base_price * terminal_return_mult;

        let bar_duration_ns = 3_600_000_000_000i64;
        let mut current_ts = 1700000000000000000i64;
        let n = spec.n_bars as f64;

        let mut current_price = base_price;

        for i in 0..spec.n_bars {
            let t = i as f64 / (n - 1.0); // progress in [0, 1]

            let expected_price = match geometry {
                PathGeometryType::MonotonicTrend => {
                    // Smooth linear/exponential interpolation to target
                    base_price * (terminal_return_mult).powf(t)
                }
                PathGeometryType::ExcursionCrashRecovery => {
                    // Massive early run-up to 1.45x at t=0.4, crash to 0.85x at t=0.7, surge to target at t=1.0
                    if t <= 0.40 {
                        let sub_t = t / 0.40;
                        base_price + (base_price * 0.45 * sub_t)
                    } else if t <= 0.70 {
                        let sub_t = (t - 0.40) / 0.30;
                        (base_price * 1.45) - (base_price * 0.60 * sub_t)
                    } else {
                        let sub_t = (t - 0.70) / 0.30;
                        (base_price * 0.85) + ((terminal_target - base_price * 0.85) * sub_t)
                    }
                }
                PathGeometryType::ImmediateDrawdownGrind => {
                    // Deep early crash to 0.75x at t=0.2, then slow steady grind up to target at t=1.0
                    if t <= 0.20 {
                        let sub_t = t / 0.20;
                        base_price - (base_price * 0.25 * sub_t)
                    } else {
                        let sub_t = (t - 0.20) / 0.80;
                        (base_price * 0.75) + ((terminal_target - base_price * 0.75) * sub_t)
                    }
                }
            };

            let open = current_price;
            let close = expected_price.max(0.01);
            let high = open.max(close) * 1.003;
            let low = (open.min(close) * 0.997).max(0.001);
            let volume = 120.0;

            let bar = WorldBar {
                timestamp_ns: current_ts,
                open,
                high,
                low,
                close,
                volume,
                funding_rate: 0.0001,
                spread_bps: 2.0,
            };

            assert!(bar.is_valid());
            bars.push(bar);

            current_price = close;
            current_ts += bar_duration_ns;
        }

        // Verify final bar reaches terminal target within 0.1% tolerance
        let final_close = bars.last().unwrap().close;
        assert!((final_close - terminal_target).abs() / terminal_target < 0.001, "Path topology failed to anchor terminal target");

        WorldReceipt::new(spec.clone(), bars)
    }
}
