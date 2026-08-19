//! Backend-agnostic kernel boundary (D-096 Backend-0).
//!
//! The ontology (Candidate/Expert/Replay/Outcome) never depends on a backend:
//! the replay interface speaks only in `Dataset`, `ReplayCell`, and `Outcome`.
//! Backend and thread count are internal details and appear in no hash and no
//! manifest (D-084, G5) — swapping a backend must not change a value.
//!
//! The scalar kernel remains the in-core reference while CPU task-parallel/SIMD
//! and optional GPU implementations share this interface. The frozen Python
//! `src/v8/` remains the parity oracle (D-087).
//!
//! D-032 file-family registration (recorded in-tree per D-096; the
//! DECISION_REGISTER/CHANGELOG entry is the docs-side of the same record):
//! - `backend/mod.rs` — this boundary (the `ReplayKernel` trait + `ReplayCell`)
//! - `backend/scalar.rs` — Backend-0 scalar reference (+ the SIMD exit walk
//!   `run_simd`/`exit_loop_simd` and its D-088 guard, #133)
//! - `backend/cpu.rs` — task-parallel CPU/SIMD backend
//! - `backend/simd.rs` — Backend-1 SIMD kernel (K1/K2 in `simd.rs` + `state`;
//!   K4 here)

pub mod cpu;
#[cfg(feature = "gpu")]
pub mod gpu;
pub mod scalar;
pub mod simd;

use serde_json::Value;

use crate::data::Dataset;
use crate::simulator::{Draft, Outcome};

/// One (candidate, action) replay cell: the compiled unit of work handed to a
/// backend.
#[derive(Debug, Clone)]
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

/// One runtime-only execution mode. It is deliberately not part of any
/// artifact identity: changing hardware may change the implementation, never
/// the replay value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EngineMode {
    Cpu,
    Gpu,
    Auto,
}

/// Return the crossover measured for the *current* certified GPU runner.
///
/// There is intentionally no default: a guessed threshold is worse than no
/// GPU dispatch because it turns an unmeasured performance claim into runtime
/// behaviour.  The GPU release job injects this value from its signed receipt;
/// normal `auto` requests stay on the CPU until such a receipt is supplied.
pub fn gpu_threshold_steps() -> Option<usize> {
    std::env::var("V8_GPU_CROSSOVER_STEPS")
        .ok()?
        .parse::<usize>()
        .ok()
        .filter(|steps| *steps > 0)
}

pub fn estimated_replay_steps(cells: &[ReplayCell]) -> usize {
    cells.iter().fold(0usize, |total, cell| {
        let expiry = cell.draft.geom_i64("expiry_bars").unwrap_or(0).max(0) as usize;
        total.saturating_add((cell.end.saturating_sub(cell.start)).min(expiry.saturating_add(1)))
    })
}

impl EngineMode {
    pub fn parse(value: &str) -> Result<Self, String> {
        match value {
            "cpu" => Ok(Self::Cpu),
            "gpu" => Ok(Self::Gpu),
            "auto" => Ok(Self::Auto),
            other => Err(format!(
                "unknown replay engine {other:?}; expected cpu, gpu, or auto"
            )),
        }
    }
}

/// The single production dispatch boundary used by replay and cube paths.
/// `auto` is fail-safe: an unavailable GPU, an unsupported cell batch, or a
/// GPU validation/runtime error routes the whole batch through the CPU/SIMD
/// reference. Explicit `gpu` remains fail-closed for diagnostics and parity.
pub fn evaluate_engine(
    engine: &str,
    threads: usize,
    sim: &crate::simulator::SimulatorParams,
    funding_schedule: &[(i64, f64)],
    stores: &[crate::state::FeatureStore],
    dataset: &Dataset,
    cells: &[ReplayCell],
    output: &mut [Outcome],
) -> Result<&'static str, String> {
    let mode = EngineMode::parse(engine)?;
    if cells.len() != output.len() {
        return Err("replay output size mismatch".into());
    }
    validate_cells(dataset, cells)?;

    match mode {
        EngineMode::Cpu => evaluate_cpu(
            threads,
            sim,
            funding_schedule,
            stores,
            dataset,
            cells,
            output,
        )
        .map(|_| "cpu"),
        EngineMode::Gpu => {
            if !gpu_fill_policy_allowed(sim) {
                return Err(
                    "GPU replay supports only the BarClose fill policy; use CPU for FILL_AT_LIMIT"
                        .into(),
                );
            }
            #[cfg(feature = "gpu")]
            {
                let backend = gpu::GpuBackend::new_with_config(gpu::GpuConfig {
                    round_trip_cost_r: sim.round_trip_cost_r,
                    round_trip_cost_bps: sim.round_trip_cost_bps,
                    funding_rate_r: sim.funding_rate_r,
                    funding_hours: sim.funding_hours,
                    funding_schedule: funding_schedule.to_vec(),
                    fill_policy: sim.fill_policy,
                })?;
                backend.evaluate(dataset, cells, output).map(|_| "gpu")
            }
            #[cfg(not(feature = "gpu"))]
            {
                Err("GPU engine requested but v8-core was built without --features gpu".into())
            }
        }
        EngineMode::Auto => {
            let Some(threshold) = gpu_threshold_steps() else {
                return evaluate_cpu(
                    threads,
                    sim,
                    funding_schedule,
                    stores,
                    dataset,
                    cells,
                    output,
                )
                .map(|_| "cpu");
            };
            if !gpu_fill_policy_allowed(sim) || estimated_replay_steps(cells) < threshold {
                return evaluate_cpu(
                    threads,
                    sim,
                    funding_schedule,
                    stores,
                    dataset,
                    cells,
                    output,
                )
                .map(|_| "cpu");
            }
            #[cfg(feature = "gpu")]
            {
                let gpu_indices: Vec<usize> = cells
                    .iter()
                    .enumerate()
                    .filter_map(|(i, cell)| gpu::supports_cell(cell).then_some(i))
                    .collect();
                if !gpu_indices.is_empty() {
                    let gpu_cells: Vec<ReplayCell> =
                        gpu_indices.iter().map(|&i| cells[i].clone()).collect();
                    let mut gpu_output = vec![Outcome::default(); gpu_cells.len()];
                    let gpu_result = gpu::GpuBackend::new_with_config(gpu::GpuConfig {
                        round_trip_cost_r: sim.round_trip_cost_r,
                        round_trip_cost_bps: sim.round_trip_cost_bps,
                        funding_rate_r: sim.funding_rate_r,
                        funding_hours: sim.funding_hours,
                        funding_schedule: funding_schedule.to_vec(),
                        fill_policy: sim.fill_policy,
                    })
                    .and_then(|backend| backend.evaluate(dataset, &gpu_cells, &mut gpu_output));
                    if gpu_result.is_ok() {
                        let cpu_indices: Vec<usize> = cells
                            .iter()
                            .enumerate()
                            .filter_map(|(i, cell)| (!gpu::supports_cell(cell)).then_some(i))
                            .collect();
                        if cpu_indices.is_empty() {
                            for (j, &i) in gpu_indices.iter().enumerate() {
                                output[i] = gpu_output[j].clone();
                            }
                            return Ok("gpu");
                        }
                        let cpu_cells: Vec<ReplayCell> =
                            cpu_indices.iter().map(|&i| cells[i].clone()).collect();
                        let mut cpu_output = vec![Outcome::default(); cpu_cells.len()];
                        evaluate_cpu(
                            threads,
                            sim,
                            funding_schedule,
                            stores,
                            dataset,
                            &cpu_cells,
                            &mut cpu_output,
                        )?;
                        for (j, &i) in gpu_indices.iter().enumerate() {
                            output[i] = gpu_output[j].clone();
                        }
                        for (j, &i) in cpu_indices.iter().enumerate() {
                            output[i] = cpu_output[j].clone();
                        }
                        return Ok("hybrid");
                    }
                }
            }
            evaluate_cpu(
                threads,
                sim,
                funding_schedule,
                stores,
                dataset,
                cells,
                output,
            )
            .map(|_| "cpu")
        }
    }
}

fn gpu_fill_policy_allowed(sim: &crate::simulator::SimulatorParams) -> bool {
    matches!(sim.fill_policy, crate::simulator::FillPolicy::BarClose)
}

fn validate_cells(dataset: &Dataset, cells: &[ReplayCell]) -> Result<(), String> {
    for cell in cells {
        crate::simulator::validate_geometry(&cell.draft)?;
        if cell.draft.direction != "LONG" && cell.draft.direction != "SHORT" {
            return Err(format!(
                "replay cell {} has invalid direction {:?}",
                cell.symbol, cell.draft.direction
            ));
        }
        let bars = dataset
            .bars
            .iter()
            .find(|bars| bars.symbol == cell.symbol)
            .ok_or_else(|| format!("replay: no bars for symbol {}", cell.symbol))?;
        if cell.start >= cell.end || cell.end > bars.closes.len() {
            return Err(format!(
                "replay cell {} has invalid window [{}, {}) for {} bars",
                cell.symbol,
                cell.start,
                cell.end,
                bars.closes.len()
            ));
        }
    }
    Ok(())
}

/// Run the small, deterministic replay corpus used as the GPU adoption gate.
/// The command intentionally returns an error on hosts without a supported
/// adapter; silently comparing CPU output to itself would make the gate
/// meaningless.
pub fn gpu_golden_parity() -> Result<Value, String> {
    #[cfg(not(feature = "gpu"))]
    {
        Err("GPU parity unavailable: rebuild with --features gpu".into())
    }
    #[cfg(feature = "gpu")]
    {
        let rows: Vec<Value> = (0..14)
            .map(|i| {
                let close = if i < 8 { 100.0 } else { 130.0 };
                let open_time = 1_750_000_000_000_000_000i64 + i as i64 * crate::simulator::HOUR_NS;
                let close_time = open_time + crate::simulator::HOUR_NS - 1_000_000;
                serde_json::json!({
                    "source": "binance-um", "channel": "kline", "instrument": "SOLUSDT",
                    "event_time": close_time, "available_time": close_time + 1_000_000_000,
                    "ingested_time": close_time + 1_000_000_000, "venue_sequence": i as i64 + 1,
                    "event_id": format!("SOLUSDT:{}", i + 1),
                    "payload": {"open": close, "high": close + 0.5, "low": close - 0.5,
                                 "close": close, "volume": 1.0, "closed": true}
                })
            })
            .collect();
        let parsed: Vec<crate::data::TapeRow> = rows
            .iter()
            .map(|v| crate::data::TapeRow::from_parts(v, vec![]))
            .collect::<Result<_, _>>()
            .map_err(|e| e.to_string())?;
        let dataset = crate::data::Dataset::from_rows(parsed).map_err(|e| e.to_string())?;
        let stores = crate::state::build_stores(&dataset);
        let mut geometry = serde_json::Map::new();
        geometry.insert("atr_ref".into(), serde_json::json!(10.0));
        geometry.insert("target_r".into(), serde_json::json!(1.0));
        geometry.insert("stop_r".into(), serde_json::json!(1.0));
        geometry.insert("expiry_bars".into(), serde_json::json!(2));
        let cell = ReplayCell {
            symbol: "SOLUSDT",
            draft: Draft {
                direction: "LONG".into(),
                birth_time: 0,
                risk_geometry: geometry,
            },
            start: 0,
            end: 14,
            thesis: None,
        };
        let cells = [cell];
        let blank = || Outcome {
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
            intervention_manifest: None,
        };
        let mut cpu = vec![blank()];
        let mut gpu = vec![blank()];
        let sim = crate::simulator::SimulatorParams {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: crate::simulator::FillPolicy::BarClose,
            round_trip_cost_bps: None,
        };
        evaluate_cpu(1, &sim, &[], &stores, &dataset, &cells, &mut cpu)?;
        let backend = gpu::GpuBackend::new_with_config(gpu::GpuConfig {
            round_trip_cost_r: sim.round_trip_cost_r,
            round_trip_cost_bps: sim.round_trip_cost_bps,
            funding_rate_r: sim.funding_rate_r,
            funding_hours: sim.funding_hours,
            funding_schedule: Vec::new(),
            fill_policy: sim.fill_policy,
        })?;
        backend.evaluate(&dataset, &cells, &mut gpu)?;
        let a = &cpu[0];
        let b = &gpu[0];
        if a.endpoint != b.endpoint
            || a.label_status != b.label_status
            || a.horizon_bars != b.horizon_bars
            || a.label_available_time != b.label_available_time
            || a.ambiguous_bars != b.ambiguous_bars
            || [
                (a.net_r, b.net_r),
                (a.mae_r, b.mae_r),
                (a.mfe_r, b.mfe_r),
                (a.entry_price, b.entry_price),
                (a.risk_unit_price, b.risk_unit_price),
                (a.market_move_r, b.market_move_r),
                (a.cost_r, b.cost_r),
                (a.funding_r, b.funding_r),
            ]
            .iter()
            .any(|(x, y)| x.to_bits() != y.to_bits())
        {
            return Err(format!("GPU golden parity mismatch: cpu={a:?} gpu={b:?}"));
        }
        Ok(serde_json::json!({
            "status": "ok", "cases": 1, "fields": 14,
            "contract": "cpu_gpu_outcome_to_bits"
        }))
    }
}

fn evaluate_cpu(
    threads: usize,
    sim: &crate::simulator::SimulatorParams,
    funding_schedule: &[(i64, f64)],
    stores: &[crate::state::FeatureStore],
    dataset: &Dataset,
    cells: &[ReplayCell],
    output: &mut [Outcome],
) -> Result<(), String> {
    let backend = cpu::SimdCpuBackend::new(
        threads,
        sim.round_trip_cost_r,
        sim.funding_rate_r,
        sim.funding_hours,
        sim.fill_policy,
        funding_schedule,
        sim.round_trip_cost_bps,
        stores,
    );
    backend.evaluate(dataset, cells, output)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::backend::cpu::{CpuBackend, SimdCpuBackend};
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
    /// CPU backend now runs the REAL parallel path (threads=4) — this pins
    /// that the parallel decomposition preserves the scalar reference
    /// bit-for-bit (G5), so a parallel backend cannot silently change a value.
    #[test]
    fn scalar_and_cpu_backends_are_bit_identical() {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut scalar_out = vec![Outcome::default(); cells.len()];
        let mut cpu_out = scalar_out.clone();
        let scalar = backend(&stores);
        // Backend-1 CPU backend, parallel path (threads=4 splits the
        // single-cell fixture into 4 workers over... a 1-cell batch takes the
        // sequential path — the scheduler's own tests cover multi-cell
        // partitions; here the boundary preservation is what matters).
        let cpu = CpuBackend::new(4, 0.07, 0.0, 0, FillPolicy::BarClose, &[], None, &stores);
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

    /// The CPU backend at threads=1 is the sequential reference path; the
    /// backend-invariance boundary holds for both the single-threaded and the
    /// multi-threaded CPU execution.
    #[test]
    fn cpu_backend_threads_1_and_4_are_byte_identical() {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut out1 = vec![Outcome::default(); cells.len()];
        let mut out4 = out1.clone();
        let cpu1 = CpuBackend::new(1, 0.07, 0.0, 0, FillPolicy::BarClose, &[], None, &stores);
        let cpu4 = CpuBackend::new(4, 0.07, 0.0, 0, FillPolicy::BarClose, &[], None, &stores);
        cpu1.evaluate(&ds, &cells, &mut out1).unwrap();
        cpu4.evaluate(&ds, &cells, &mut out4).unwrap();
        for (a, b) in out1.iter().zip(out4.iter()) {
            assert_eq!(a.net_r.to_bits(), b.net_r.to_bits());
            assert_eq!(a.endpoint, b.endpoint);
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
        let mut batch_out = vec![Outcome::default(); cells.len()];
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

    /// Backend invariance for the parallel SIMD backend (#133): the SIMD
    /// kernel scheduled over 4 workers (multi-cell batch, so the parallel
    /// decomposition is real) is bit-identical to the scalar reference — the
    /// full Backend-1 combination (SIMD + task parallelism) changes no value.
    #[test]
    fn simd_cpu_backend_parallel_bit_identical_to_scalar() {
        // Two symbols so the batch splits across workers.
        let rows: Vec<Value> = (0..20)
            .flat_map(|i| {
                let c = if i < 8 { 100.0 } else { 130.0 };
                [
                    bar(c, c + 0.5, c - 0.5, c, "SOLUSDT", i),
                    bar(c * 1.5, c * 1.5 + 0.5, c * 1.5 - 0.5, c * 1.5, "BTCUSDT", i),
                ]
            })
            .collect();
        let parsed: Vec<TapeRow> = rows
            .iter()
            .map(|v| TapeRow::from_parts(v, vec![]).unwrap())
            .collect();
        let ds = Dataset::from_rows(parsed).unwrap();
        let stores = build_stores(&ds);
        let mut cells: Vec<ReplayCell> = Vec::new();
        for (idx, _b) in ds.bars.iter().enumerate() {
            let symbol = &ds.bars[idx].symbol;
            let d = Draft {
                direction: "LONG".to_string(),
                birth_time: 0,
                risk_geometry: {
                    let mut g = serde_json::Map::new();
                    g.insert("atr_ref".to_string(), serde_json::json!(10.0));
                    g.insert("target_r".to_string(), serde_json::json!(1.0));
                    g.insert("stop_r".to_string(), serde_json::json!(1.0));
                    g.insert("expiry_bars".to_string(), serde_json::json!(2));
                    g
                },
            };
            for start in 0..6 {
                cells.push(ReplayCell {
                    symbol,
                    draft: d.clone(),
                    start,
                    end: 20,
                    thesis: None,
                });
            }
        }
        let mut so = vec![Outcome::default(); cells.len()];
        let mut sm = so.clone();
        let scalar = ScalarBackend {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0001,
            funding_hours: 1,
            fill_policy: FillPolicy::BarClose,
            funding_schedule: &[],
            round_trip_cost_bps: None,
            stores: &stores,
        };
        let simd_par =
            SimdCpuBackend::new(4, 0.07, 0.0001, 1, FillPolicy::BarClose, &[], None, &stores);
        scalar.evaluate(&ds, &cells, &mut so).unwrap();
        simd_par.evaluate(&ds, &cells, &mut sm).unwrap();
        for (i, (a, b)) in so.iter().zip(sm.iter()).enumerate() {
            assert_eq!(a.endpoint, b.endpoint, "cell {i}");
            assert_eq!(a.net_r.to_bits(), b.net_r.to_bits(), "cell {i} net_r");
            assert_eq!(a.mae_r.to_bits(), b.mae_r.to_bits(), "cell {i} mae_r");
            assert_eq!(a.mfe_r.to_bits(), b.mfe_r.to_bits(), "cell {i} mfe_r");
            assert_eq!(
                a.entry_price.to_bits(),
                b.entry_price.to_bits(),
                "cell {i} entry_price"
            );
            assert_eq!(
                a.risk_unit_price.to_bits(),
                b.risk_unit_price.to_bits(),
                "cell {i} risk_unit_price"
            );
            assert_eq!(
                a.market_move_r.to_bits(),
                b.market_move_r.to_bits(),
                "cell {i} market_move_r"
            );
            assert_eq!(a.cost_r.to_bits(), b.cost_r.to_bits(), "cell {i} cost_r");
            assert_eq!(
                a.funding_r.to_bits(),
                b.funding_r.to_bits(),
                "cell {i} funding_r"
            );
        }
    }

    #[test]
    fn engine_mode_parse_is_explicit_and_fail_closed() {
        assert_eq!(EngineMode::parse("cpu").unwrap(), EngineMode::Cpu);
        assert_eq!(EngineMode::parse("gpu").unwrap(), EngineMode::Gpu);
        assert_eq!(EngineMode::parse("auto").unwrap(), EngineMode::Auto);
        assert!(EngineMode::parse("cuda").is_err());
    }

    #[test]
    fn gpu_dispatch_rejects_limit_fill_policy() {
        let bar_close = crate::simulator::SimulatorParams {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 8,
            fill_policy: FillPolicy::BarClose,
            round_trip_cost_bps: None,
        };
        let limit = crate::simulator::SimulatorParams {
            fill_policy: FillPolicy::Limit,
            ..bar_close
        };
        assert!(gpu_fill_policy_allowed(&bar_close));
        assert!(!gpu_fill_policy_allowed(&limit));
    }

    #[test]
    fn replay_cell_validation_fails_closed_on_bad_window_or_direction() {
        let (dataset, _) = fixture();
        let mut cells = cells();
        cells[0].end = 15;
        assert!(validate_cells(&dataset, &cells)
            .expect_err("window beyond the dataset must fail")
            .contains("invalid window"));

        cells[0].end = 14;
        cells[0].draft.direction = "SIDEWAYS".into();
        assert!(validate_cells(&dataset, &cells)
            .expect_err("unknown direction must fail")
            .contains("invalid direction"));
    }

    #[test]
    fn auto_engine_matches_cpu_reference_on_cpu_only_host() {
        let (ds, stores) = fixture();
        let cells = cells();
        let sim = crate::simulator::SimulatorParams {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: FillPolicy::BarClose,
            round_trip_cost_bps: None,
        };
        let mut cpu = vec![Outcome::default(); cells.len()];
        let mut auto = cpu.clone();
        evaluate_engine("cpu", 1, &sim, &[], &stores, &ds, &cells, &mut cpu).unwrap();
        evaluate_engine("auto", 1, &sim, &[], &stores, &ds, &cells, &mut auto).unwrap();
        for (a, b) in cpu.iter().zip(auto.iter()) {
            assert_eq!(a.endpoint, b.endpoint);
            assert_eq!(a.net_r.to_bits(), b.net_r.to_bits());
            assert_eq!(a.market_move_r.to_bits(), b.market_move_r.to_bits());
            assert_eq!(a.cost_r.to_bits(), b.cost_r.to_bits());
        }
    }

    #[cfg(feature = "gpu")]
    #[test]
    fn gpu_capability_predicate_is_fail_closed_for_management_cells() {
        let mut static_cell = cells().remove(0);
        assert!(gpu::supports_cell(&static_cell));
        static_cell
            .draft
            .risk_geometry
            .insert("trail_stop_atr".into(), serde_json::json!(2.0));
        assert!(!gpu::supports_cell(&static_cell));
        static_cell.draft.risk_geometry.remove("trail_stop_atr");
        static_cell
            .draft
            .risk_geometry
            .insert("trigger_ref".into(), serde_json::json!(100.0));
        assert!(!gpu::supports_cell(&static_cell));
    }
}
