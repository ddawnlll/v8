//! Backend-1 SIMD backend (D-096 Backend-1, #133).
//!
//! The SIMD replay kernel behind the same `ReplayKernel` boundary as the
//! scalar reference and the task-parallel CPU backend. It must reproduce the
//! Backend-0 scalar reference bit-for-bit (COMPUTE_SCHEDULING_SPEC §5, §8.2):
//! the exit-walk price math is computed lane-wise with `f64x2` NEON/SSE2 over
//! pairs of bars (K4 barrier comparisons and extremes — the value-safe SIMD
//! domain), then consumed by a sequential walk in the declared order. SIMD is
//! only engaged where D-088 says it cannot change a value; every other draft
//! class delegates to the exact scalar kernel (see
//! `ScalarKernel::run_simd`'s guard). Thread count and backend choice appear
//! in no hash and no manifest (D-084, G5).
//!
//! No speed claim: the gate is correctness (D-087).
//!
//! D-032 file-family registration: `backend/simd.rs` — Backend-1 SIMD kernel
//! (K1/K2 window reductions live in `simd.rs`, wired into `state`; K4 lives
//! here and in `ScalarKernel::exit_loop_simd`).

use crate::backend::scalar::ScalarKernel;
use crate::backend::{ReplayCell, ReplayKernel};
use crate::data::Dataset;
use crate::simulator::{FillPolicy, Outcome};
use crate::state::FeatureStore;

/// The SIMD backend: evaluates a cell batch with `ScalarKernel::run_simd`,
/// which uses the SIMD exit walk where value-safe and falls back to the exact
/// scalar reference otherwise. Cell-order output, bit-identical to the scalar
/// backend.
pub struct SimdBackend<'a> {
    round_trip_cost_r: f64,
    funding_rate_r: f64,
    funding_hours: i64,
    fill_policy: FillPolicy,
    funding_schedule: &'a [(i64, f64)],
    round_trip_cost_bps: Option<f64>,
    stores: &'a [FeatureStore],
}

impl<'a> SimdBackend<'a> {
    pub fn new(
        round_trip_cost_r: f64,
        funding_rate_r: f64,
        funding_hours: i64,
        fill_policy: FillPolicy,
        funding_schedule: &'a [(i64, f64)],
        round_trip_cost_bps: Option<f64>,
        stores: &'a [FeatureStore],
    ) -> SimdBackend<'a> {
        SimdBackend {
            round_trip_cost_r,
            funding_rate_r,
            funding_hours,
            fill_policy,
            funding_schedule,
            round_trip_cost_bps,
            stores,
        }
    }
}

impl<'a> ReplayKernel for SimdBackend<'a> {
    fn evaluate(
        &self,
        dataset: &Dataset,
        cells: &[ReplayCell],
        output: &mut [Outcome],
    ) -> Result<(), String> {
        if cells.len() != output.len() {
            return Err(format!(
                "simd evaluate: cell batch size {} does not match output size {}",
                cells.len(),
                output.len()
            ));
        }
        for (cell, slot) in cells.iter().zip(output.iter_mut()) {
            let bars = dataset
                .bars
                .iter()
                .find(|b| b.symbol == cell.symbol)
                .ok_or_else(|| format!("simd evaluate: no bars for symbol {}", cell.symbol))?;
            let store = self
                .stores
                .iter()
                .find(|s| s.symbol == cell.symbol)
                .ok_or_else(|| format!("simd evaluate: no store for symbol {}", cell.symbol))?;
            let kernel = ScalarKernel {
                round_trip_cost_r: self.round_trip_cost_r,
                funding_rate_r: self.funding_rate_r,
                funding_hours: self.funding_hours,
                fill_policy: self.fill_policy,
                funding_schedule: self.funding_schedule,
                round_trip_cost_bps: self.round_trip_cost_bps,
                bars,
                store,
            };
            *slot = kernel.run_simd(&cell.draft, cell.start, cell.end, cell.thesis.as_ref())?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::backend::scalar::ScalarBackend;
    use crate::data::TapeRow;
    use crate::simulator::{Draft, HOUR_NS};
    use crate::state::build_stores;
    use serde_json::Value;

    /// A kline tape row (mirror of backend/mod.rs's fixture, in-value
    /// identical).
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

    fn fixture(symbol: &str, closes: &[f64]) -> (Dataset, Vec<crate::state::FeatureStore>) {
        let rows: Vec<Value> = closes
            .iter()
            .enumerate()
            .map(|(i, &c)| bar(c, c + 0.5, c - 0.5, c, symbol, i))
            .collect();
        let parsed: Vec<TapeRow> = rows
            .iter()
            .map(|v| TapeRow::from_parts(v, vec![]).unwrap())
            .collect();
        let ds = Dataset::from_rows(parsed).unwrap();
        let stores = build_stores(&ds);
        (ds, stores)
    }

    fn draft(
        direction: &str,
        target_r: f64,
        stop_r: f64,
        expiry_bars: i64,
        extra: &[(&str, serde_json::Value)],
    ) -> Draft {
        let mut g = serde_json::Map::new();
        g.insert("atr_ref".to_string(), serde_json::json!(10.0));
        g.insert("target_r".to_string(), serde_json::json!(target_r));
        g.insert("stop_r".to_string(), serde_json::json!(stop_r));
        g.insert("expiry_bars".to_string(), serde_json::json!(expiry_bars));
        for (k, v) in extra {
            g.insert(k.to_string(), v.clone());
        }
        Draft {
            direction: direction.to_string(),
            birth_time: 0,
            risk_geometry: g,
        }
    }

    fn cell<'a>(symbol: &'a str, d: Draft, start: usize, end: usize) -> ReplayCell<'a> {
        ReplayCell {
            symbol,
            draft: d,
            start,
            end,
            thesis: None,
        }
    }

    fn new_outcomes(n: usize) -> Vec<Outcome> {
        vec![
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
            n
        ]
    }

    fn scalar<'a>(stores: &'a [crate::state::FeatureStore]) -> ScalarBackend<'a> {
        ScalarBackend {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0001,
            funding_hours: 1,
            fill_policy: FillPolicy::BarClose,
            funding_schedule: &[],
            round_trip_cost_bps: None,
            stores,
        }
    }

    fn simd<'a>(stores: &'a [crate::state::FeatureStore]) -> SimdBackend<'a> {
        SimdBackend::new(
            0.07,
            0.0001,
            1,
            FillPolicy::BarClose,
            &[],
            None,
            stores,
        )
    }

    fn assert_bit_identical(a: &Outcome, b: &Outcome, ctx: &str) {
        assert_eq!(a.endpoint, b.endpoint, "{ctx}: endpoint");
        assert_eq!(a.net_r.to_bits(), b.net_r.to_bits(), "{ctx}: net_r");
        assert_eq!(a.label_status, b.label_status, "{ctx}: label_status");
        assert_eq!(a.horizon_bars, b.horizon_bars, "{ctx}: horizon_bars");
        assert_eq!(
            a.label_available_time, b.label_available_time,
            "{ctx}: label_available_time"
        );
        assert_eq!(a.mae_r.to_bits(), b.mae_r.to_bits(), "{ctx}: mae_r");
        assert_eq!(a.mfe_r.to_bits(), b.mfe_r.to_bits(), "{ctx}: mfe_r");
        assert_eq!(
            a.ambiguous_bars, b.ambiguous_bars,
            "{ctx}: ambiguous_bars"
        );
        assert_eq!(a.entry_price.to_bits(), b.entry_price.to_bits(), "{ctx}: entry_price");
        assert_eq!(
            a.risk_unit_price.to_bits(),
            b.risk_unit_price.to_bits(),
            "{ctx}: risk_unit_price"
        );
        assert_eq!(
            a.market_move_r.to_bits(),
            b.market_move_r.to_bits(),
            "{ctx}: market_move_r"
        );
        assert_eq!(a.cost_r.to_bits(), b.cost_r.to_bits(), "{ctx}: cost_r");
        assert_eq!(a.funding_r.to_bits(), b.funding_r.to_bits(), "{ctx}: funding_r");
    }

    /// K4 backend invariance (COMPUTE_SCHEDULING_SPEC §8.2): the SIMD backend
    /// is bit-identical to the scalar reference on a cell batch exercising
    /// every endpoint and both directions — TARGET/STOP gap-through, plain
    /// TARGET/STOP, EXPIRY, ambiguous bars, and a non-entry EXPIRY.
    #[test]
    fn simd_backend_bit_identical_to_scalar_across_endpoints() {
        let (ds, stores) = fixture(
            "SOLUSDT",
            &[100.0, 101.0, 102.0, 130.0, 70.0, 100.5, 103.0, 99.0, 110.0, 90.0, 100.0, 100.2, 100.4, 99.8],
        );
        let cells = vec![
            // Favorable gap straight through the 110 target -> TARGET at open.
            cell("SOLUSDT", draft("LONG", 1.0, 1.0, 2, &[]), 0, 14),
            // Adverse gap through the 90 stop -> STOP at open.
            cell("SOLUSDT", draft("LONG", 1.0, 1.0, 2, &[]), 4, 14),
            // SHORT adverse gap (stop 110) -> STOP.
            cell("SOLUSDT", draft("SHORT", 1.0, 1.0, 2, &[]), 7, 14),
            // Short expiry window: entry bar + 2 bars, never terminal -> EXPIRY.
            cell("SOLUSDT", draft("LONG", 1.0, 1.0, 2, &[]), 10, 14),
            // start == end -> the empty EXPIRY convention.
            cell("SOLUSDT", draft("LONG", 1.0, 1.0, 2, &[]), 13, 13),
        ];
        let mut so = new_outcomes(cells.len());
        let mut sm = new_outcomes(cells.len());
        scalar(&stores).evaluate(&ds, &cells, &mut so).unwrap();
        simd(&stores).evaluate(&ds, &cells, &mut sm).unwrap();
        for (i, (a, b)) in so.iter().zip(sm.iter()).enumerate() {
            assert_bit_identical(a, b, &format!("cell {i}"));
        }
    }

    /// The D-088 guard: drafts whose stop level can move (trail / breakeven /
    /// scale-out) are NOT SIMD-eligible and must still be bit-identical —
    /// through the scalar fallback, not through a SIMD path that would be
    /// value-unsafe.
    #[test]
    fn simd_falls_back_for_stop_moving_drafts_bit_identical() {
        let (ds, stores) = fixture(
            "SOLUSDT",
            &[100.0, 104.0, 108.0, 106.0, 102.0, 100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0],
        );
        let cells = vec![
            cell(
                "SOLUSDT",
                draft("LONG", 1.0, 1.0, 8, &[("trail_stop_atr", serde_json::json!(2.0))]),
                0,
                12,
            ),
            cell(
                "SOLUSDT",
                draft(
                    "LONG",
                    1.0,
                    1.0,
                    8,
                    &[("breakeven_roll_at_mfe_r", serde_json::json!(1.0))],
                ),
                0,
                12,
            ),
            cell(
                "SOLUSDT",
                draft(
                    "LONG",
                    1.0,
                    1.0,
                    8,
                    &[("scale_out_ratio", serde_json::json!(0.5))],
                ),
                0,
                12,
            ),
        ];
        let mut so = new_outcomes(cells.len());
        let mut sm = new_outcomes(cells.len());
        scalar(&stores).evaluate(&ds, &cells, &mut so).unwrap();
        simd(&stores).evaluate(&ds, &cells, &mut sm).unwrap();
        for (i, (a, b)) in so.iter().zip(sm.iter()).enumerate() {
            assert_bit_identical(a, b, &format!("guarded cell {i}"));
        }
    }

    /// Bit-identity across the entry-trigger gate (D-057), thesis
    /// invalidation (a compiled `compare` IR that is false at the first
    /// stepped bar), and a TIME_EXIT horizon — the entry/exit machinery that
    /// shares `run_impl` and the sequential walk.
    #[test]
    fn simd_bit_identical_trigger_thesis_and_time_exit() {
        let (ds, stores) = fixture(
            "SOLUSDT",
            &[100.0, 101.0, 102.0, 130.0, 70.0, 100.5, 103.0, 99.0, 110.0, 90.0, 100.0, 100.2],
        );
        // trigger_ref 101.5 CLOSE_ABOVE: close 102 at bar 2 confirms, entry
        // at bar 3's close (130), then bar 4 gaps through the 120 stop.
        let trigger = draft(
            "LONG",
            1.0,
            1.0,
            3,
            &[
                ("trigger_ref", serde_json::json!(101.5)),
                ("trigger_side", serde_json::json!("CLOSE_ABOVE")),
            ],
        );
        // A thesis that is false from the first stepped bar (1.0 > 2.0 is
        // false): entry at bar 0's close, invalidated at bar 1.
        let invalidating_thesis = serde_json::json!({
            "type": "compare",
            "lhs": {"type": "const", "v": 1.0},
            "rhs": {"type": "const", "v": 2.0},
            "op": "GT",
        });
        // time_exit_bars = 2: bar 2 (bars_held == 2) exits at its close.
        let time_exit = draft(
            "LONG",
            1.0,
            1.0,
            8,
            &[("time_exit_bars", serde_json::json!(2))],
        );

        let mut cells: Vec<ReplayCell> = vec![
            cell("SOLUSDT", trigger, 0, 12),
            cell("SOLUSDT", draft("LONG", 1.0, 1.0, 3, &[]), 0, 12),
            cell("SOLUSDT", time_exit, 0, 12),
        ];
        cells[1].thesis = Some(invalidating_thesis);
        let mut so = new_outcomes(cells.len());
        let mut sm = new_outcomes(cells.len());
        scalar(&stores).evaluate(&ds, &cells, &mut so).unwrap();
        simd(&stores).evaluate(&ds, &cells, &mut sm).unwrap();
        // The trigger cell must actually reach a STOP (proves the trigger
        // fired in both paths), and the thesis cell a THESIS_INVALIDATED.
        assert_eq!(so[0].endpoint, "STOP");
        assert_eq!(so[1].endpoint, "THESIS_INVALIDATED");
        assert_eq!(so[2].endpoint, "TIME_EXIT");
        for (i, (a, b)) in so.iter().zip(sm.iter()).enumerate() {
            assert_bit_identical(a, b, &format!("trigger/thesis/time_exit cell {i}"));
        }
    }

    /// FillPolicy::Limit is outside the SIMD value-safety guard (the fill
    /// scan is a distinct entry path): the SimdBackend must delegate to the
    /// scalar reference and stay bit-identical.
    #[test]
    fn simd_limit_fill_delegates_to_scalar_bit_identical() {
        let (ds, stores) = fixture(
            "SOLUSDT",
            &[100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0],
        );
        let cells = vec![
            // LONG buy-limit 99.5: low 98.5 at bar 1 fills at 99.5, then a
            // 90 stop (atr 10, 1R) is hit at bar 7 (low 92.5 < 90? no — low
            // 92.5... bar 8 low 91.5, bar 9 low 90.5, no stop) -> EXPIRY.
            cell(
                "SOLUSDT",
                draft(
                    "LONG",
                    1.0,
                    1.0,
                    8,
                    &[("limit_price", serde_json::json!(99.5))],
                ),
                0,
                10,
            ),
            // SHORT sell-limit 100.5: high 100.5 at bar 0 fills, target 90.5
            // at bar 9 (high 91.5 > 90.5... close 91) — EXPIRY again.
            cell(
                "SOLUSDT",
                draft(
                    "SHORT",
                    1.0,
                    1.0,
                    8,
                    &[("limit_price", serde_json::json!(100.5))],
                ),
                0,
                10,
            ),
        ];
        let sb = ScalarBackend {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0001,
            funding_hours: 1,
            fill_policy: FillPolicy::Limit,
            funding_schedule: &[],
            round_trip_cost_bps: None,
            stores: &stores,
        };
        let sm = SimdBackend::new(0.07, 0.0001, 1, FillPolicy::Limit, &[], None, &stores);
        let mut so = new_outcomes(cells.len());
        let mut sm_out = new_outcomes(cells.len());
        sb.evaluate(&ds, &cells, &mut so).unwrap();
        sm.evaluate(&ds, &cells, &mut sm_out).unwrap();
        for (i, (a, b)) in so.iter().zip(sm_out.iter()).enumerate() {
            assert_bit_identical(a, b, &format!("limit cell {i}"));
        }
    }
}
