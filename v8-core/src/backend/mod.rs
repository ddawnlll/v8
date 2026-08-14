//! Backend-agnostic kernel boundary (D-096 Backend-0).
//!
//! The ontology (Candidate/Expert/Replay/Outcome) never depends on a backend:
//! the replay interface speaks only in `Dataset`, `ReplayCell`, and `Outcome`.
//! Backend and thread count are internal details and appear in no hash and no
//! manifest (D-084, G5) — swapping a backend must not change a value.
//!
//! Backend-0 is the in-core scalar reference (`scalar`); the frozen Python
//! `src/v8/` remains the parity oracle (D-087). Backend-1 (task parallelism
//! + SIMD) lands on a separate card and leaves this interface unchanged.
//!
//! D-032 file-family registration (recorded in-tree per D-096; the
//! DECISION_REGISTER/CHANGELOG entry is the docs-side of the same record):
//! - `backend/mod.rs` — this boundary (the `ReplayKernel` trait + `ReplayCell`)
//! - `backend/scalar.rs` — Backend-0 scalar reference
//! - `backend/cpu.rs` — Backend-1 CPU skeleton (parallelism on a separate card)

pub mod cpu;
pub mod scalar;

use serde_json::Value;

use crate::data::Dataset;
use crate::simulator::{Draft, Outcome};

/// One (candidate, action) replay cell: the compiled unit of work handed to a
/// backend.
pub struct ReplayCell<'a> {
    pub symbol: &'a str,
    pub draft: Draft,
    /// Entry bar index (absolute).
    pub start: usize,
    /// Window end (absolute).
    pub end: usize,
    /// Compiled post-entry thesis (predicate IR), if any.
    pub thesis: Option<Value>,
}

/// The backend-agnostic replay kernel. A backend fills `output` with one
/// `Outcome` per `cells` entry, in cell order. Determinism is non-negotiable:
/// any backend must reproduce the scalar reference bit-for-bit
/// (COMPUTE_SCHEDULING_SPEC §5, §8). The batch fails closed on the first
/// error — partial results are never emitted (§7).
pub trait ReplayKernel {
    fn evaluate(
        &self,
        dataset: &Dataset,
        cells: &[ReplayCell],
        output: &mut [Outcome],
    ) -> Result<(), String>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::backend::cpu::CpuBackend;
    use crate::backend::scalar::{ScalarBackend, ScalarKernel};
    use crate::data::TapeRow;
    use crate::simulator::{FillPolicy, HOUR_NS};
    use crate::state::build_stores;

    /// One kline tape row (mirror of runloop's test fixture, kept in-value
    /// identical so a backend-invariance comparison is meaningful).
    fn bar(o: f64, h: f64, l: f64, c: f64, symbol: &str, i: usize) -> Value {
        let open_time = 1_750_000_000_000_000_000i64 + (i as i64) * HOUR_NS;
        let close_time = open_time + HOUR_NS - 1_000_000;
        let available = close_time + 1_000_000_000;
        serde_json::json!({
            "source": "binance-um",
            "channel": "kline",
            "instrument": symbol,
            "event_time": close_time,
            "available_time": available,
            "ingested_time": available,
            "venue_sequence": i as i64 + 1,
            "event_id": format!("{symbol}:{}", i + 1),
            "payload": {
                "open": o, "high": h, "low": l, "close": c,
                "volume": 1.0, "closed": true,
            },
        })
    }

    fn fixture() -> (Dataset, Vec<crate::state::FeatureStore>) {
        // 14 bars: flat 100, then a gap through the target (mirror of the
        // simulator gap tests, so the kernel exercises the same endpoint).
        let rows: Vec<Value> = (0..14)
            .map(|i| {
                let c = if i < 8 { 100.0 } else { 130.0 };
                bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i)
            })
            .collect();
        let parsed: Vec<TapeRow> = rows
            .iter()
            .map(|v| TapeRow::from_parts(v, vec![]).unwrap())
            .collect();
        let ds = Dataset::from_rows(parsed).unwrap();
        let stores = build_stores(&ds);
        (ds, stores)
    }

    /// 1R geometry at atr_ref=10 with a 2-bar horizon (mirror of simulator's
    /// `gap_draft`).
    fn draft() -> Draft {
        let mut g = serde_json::Map::new();
        g.insert("atr_ref".to_string(), serde_json::json!(10.0));
        g.insert("target_r".to_string(), serde_json::json!(1.0));
        g.insert("stop_r".to_string(), serde_json::json!(1.0));
        g.insert("expiry_bars".to_string(), serde_json::json!(2));
        Draft {
            direction: "LONG".to_string(),
            birth_time: 0,
            risk_geometry: g,
        }
    }

    fn cells() -> Vec<ReplayCell<'static>> {
        vec![ReplayCell {
            symbol: "SOLUSDT",
            draft: draft(),
            start: 0,
            end: 14,
            thesis: None,
        }]
    }

    fn backend<'a>(stores: &'a [crate::state::FeatureStore]) -> ScalarBackend<'a> {
        ScalarBackend {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: FillPolicy::BarClose,
            funding_schedule: &[],
            round_trip_cost_bps: None,
            stores,
        }
    }

    /// Backend invariance (COMPUTE_SCHEDULING_SPEC §8.2): where a second
    /// backend exists, K4 outputs are bit-identical to the CPU backend. The
    /// CPU backend is a skeleton that today delegates to the scalar reference
    /// — this test pins that the boundary preserves behavior, so a parallel
    /// backend cannot silently change a value.
    #[test]
    fn scalar_and_cpu_backends_are_bit_identical() {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut scalar_out = vec![
            Outcome {
                endpoint: String::new(),
                net_r: 0.0,
                label_status: String::new(),
                horizon_bars: 0,
                label_available_time: 0,
                mae_r: 0.0,
                mfe_r: 0.0,
                ambiguous_bars: 0,
                entry_price: 0.0,
                risk_unit_price: 0.0,
                market_move_r: 0.0,
                cost_r: 0.0,
                funding_r: 0.0,
            };
            cells.len()
        ];
        let mut cpu_out = scalar_out.clone();
        let scalar = backend(&stores);
        let cpu = CpuBackend::new(0.07, 0.0, 0, FillPolicy::BarClose, &[], None, &stores);
        scalar.evaluate(&ds, &cells, &mut scalar_out).unwrap();
        cpu.evaluate(&ds, &cells, &mut cpu_out).unwrap();
        for (a, b) in scalar_out.iter().zip(cpu_out.iter()) {
            assert_eq!(a.endpoint, b.endpoint);
            assert_eq!(
                a.net_r.to_bits(),
                b.net_r.to_bits(),
                "net_r must be bit-identical across backends"
            );
            assert_eq!(a.label_status, b.label_status);
            assert_eq!(a.horizon_bars, b.horizon_bars);
            assert_eq!(a.label_available_time, b.label_available_time);
            assert_eq!(a.mae_r.to_bits(), b.mae_r.to_bits());
            assert_eq!(a.mfe_r.to_bits(), b.mfe_r.to_bits());
            assert_eq!(a.ambiguous_bars, b.ambiguous_bars);
            assert_eq!(a.entry_price.to_bits(), b.entry_price.to_bits());
            assert_eq!(a.risk_unit_price.to_bits(), b.risk_unit_price.to_bits());
            assert_eq!(a.market_move_r.to_bits(), b.market_move_r.to_bits());
            assert_eq!(a.cost_r.to_bits(), b.cost_r.to_bits());
            assert_eq!(a.funding_r.to_bits(), b.funding_r.to_bits());
        }
    }

    /// The batch trait boundary must equal the direct per-cell scalar run:
    /// routing a request through `ReplayKernel::evaluate` cannot change a
    /// value relative to the kernel's own `run` (behavior preservation is the
    /// whole point of Backend-0).
    #[test]
    fn trait_evaluate_matches_direct_scalar_run() {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut batch_out = vec![
            Outcome {
                endpoint: String::new(),
                net_r: 0.0,
                label_status: String::new(),
                horizon_bars: 0,
                label_available_time: 0,
                mae_r: 0.0,
                mfe_r: 0.0,
                ambiguous_bars: 0,
                entry_price: 0.0,
                risk_unit_price: 0.0,
                market_move_r: 0.0,
                cost_r: 0.0,
                funding_r: 0.0,
            };
            cells.len()
        ];
        backend(&stores)
            .evaluate(&ds, &cells, &mut batch_out)
            .unwrap();

        let kernel = ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: FillPolicy::BarClose,
            funding_schedule: &[],
            round_trip_cost_bps: None,
            bars: &ds.bars[0],
            store: &stores[0],
        };
        let direct = kernel
            .run(&draft(), 0, ds.bars[0].closes.len(), None)
            .unwrap();
        assert_eq!(batch_out[0].endpoint, direct.endpoint);
        assert_eq!(
            batch_out[0].net_r.to_bits(),
            direct.net_r.to_bits(),
            "batch evaluate must be bit-identical to the direct scalar run"
        );
        assert_eq!(
            batch_out[0].entry_price.to_bits(),
            direct.entry_price.to_bits()
        );
        assert_eq!(
            batch_out[0].risk_unit_price.to_bits(),
            direct.risk_unit_price.to_bits()
        );
        assert_eq!(
            batch_out[0].label_available_time,
            direct.label_available_time
        );
        assert_eq!(
            batch_out[0].market_move_r.to_bits(),
            direct.market_move_r.to_bits()
        );
        assert_eq!(batch_out[0].cost_r.to_bits(), direct.cost_r.to_bits());
        assert_eq!(batch_out[0].funding_r.to_bits(), direct.funding_r.to_bits());
    }
}
