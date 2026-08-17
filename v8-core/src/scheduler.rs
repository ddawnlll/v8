//! Task scheduler: real thread-level parallelism for the K4 replay batch
//! (D-096 Backend-1, issue #132).
//!
//! Backend-0 was the in-core scalar reference; the parallel decomposition is
//! Backend-1's task-parallelism step (COMPUTE_SCHEDULING_SPEC §4.1): cells
//! within a Candidate and Candidates across symbols are fully independent, so
//! a `ReplayCell` batch is partitioned into contiguous worker chunks and
//! evaluated on `threads` OS threads. This module owns CPU task partitioning;
//! backend selection (including the optional GPU) lives in `backend::mod`.
//!
//! Determinism (G5). The partition shape depends only on `(n, workers)`,
//! never on completion order: worker `w` owns the contiguous `[lo, hi)` slice
//! of both the cell batch and the output, and the caller splices per-worker
//! results back in worker order. `output[i]` is always the outcome of
//! `cells[i]`, so 1 thread and N threads produce byte-identical artifacts
//! (COMPUTE_SCHEDULING_SPEC §8.1). A backend/thread count appears in no hash
//! and no manifest (D-084).
//!
//! Failure (§7). A worker fault — a kernel `Err` on the batch path, or a
//! worker panic on either path — fails the whole request; the scheduler
//! returns `Err` and no partial result is handed back. On the per-task path
//! (`parallel_map`) a task's own `Err` is a task RESULT, not a fault: the
//! caller owns the failure policy (e.g. the cube's NOT_EVALUABLE_ACTION
//! downgrade) and still sees every task outcome in index order.
//!
//! No speed claim: the gate is correctness (D-087).
//!
//! D-032 file-family registration: `scheduler.rs` — the K4 cell-batch task
//! scheduler (Backend-1). The DECISION_REGISTER/CHANGELOG entry is the
//! docs-side of the same record.

use crate::backend::{ReplayCell, ReplayKernel};
use crate::data::Dataset;
use crate::simulator::Outcome;

/// Contiguous worker-chunk boundaries: worker `w` owns `[bounds[w],
/// bounds[w+1])`. The shape depends only on `(n, workers)` — never on thread
/// completion order, which is what keeps the parallel decomposition
/// value-identical to the sequential reference.
fn chunk_bounds(n: usize, workers: usize) -> Vec<usize> {
    if n == 0 {
        return vec![0];
    }
    let workers = workers.min(n).max(1);
    let base = n / workers;
    let rem = n % workers;
    let mut bounds = Vec::with_capacity(workers + 1);
    bounds.push(0);
    for w in 0..workers {
        let prev = bounds[w];
        bounds.push(prev + base + usize::from(w < rem));
    }
    bounds
}

/// Evaluate a `ReplayCell` batch through `kernel` on up to `threads` worker
/// threads (COMPUTE_SCHEDULING_SPEC §8.1 thread invariance).
///
/// - `threads <= 1` (or an empty/single-cell batch): the sequential reference
///   path — the kernel is called once over the whole batch, unchanged.
/// - `threads > 1`: `min(threads, cells.len())` scoped worker threads, each
///   owning a contiguous `[lo, hi)` slice of both the cells and `output`; the
///   scope joins every worker before returning.
///
/// Fails closed (§7): a chunk `Err` or a worker panic returns `Err`; no
/// partial outcome batch is ever produced.
pub fn evaluate<K: ReplayKernel + Sync>(
    threads: usize,
    kernel: &K,
    dataset: &Dataset,
    cells: &[ReplayCell],
    output: &mut [Outcome],
) -> Result<(), String> {
    if cells.len() != output.len() {
        return Err(format!(
            "scheduler evaluate: cell batch size {} does not match output size {}",
            cells.len(),
            output.len()
        ));
    }
    if threads <= 1 || cells.len() <= 1 {
        // Single-threaded: the sequential scalar reference path, unchanged.
        return kernel.evaluate(dataset, cells, output);
    }
    let workers = threads.min(cells.len());
    let bounds = chunk_bounds(cells.len(), workers);
    // Split `output` into disjoint per-worker slices once, up front
    // (split_at_mut is the only borrow the scope needs to see).
    let mut chunks: Vec<&mut [Outcome]> = Vec::with_capacity(workers);
    let mut rest = &mut output[..];
    for w in 0..workers {
        let (lo, hi) = (bounds[w], bounds[w + 1]);
        let (head, tail) = rest.split_at_mut(hi - lo);
        chunks.push(head);
        rest = tail;
    }
    std::thread::scope(|s| -> Result<(), String> {
        let mut handles = Vec::with_capacity(workers);
        // into_iter moves each disjoint `&mut [Outcome]` out of `chunks` one
        // at a time — the borrows were created by split_at_mut, so no worker
        // can alias another's output slice.
        let mut chunk_iter = chunks.into_iter();
        for w in 0..workers {
            let (lo, hi) = (bounds[w], bounds[w + 1]);
            let chunk = &cells[lo..hi];
            let out = chunk_iter.next().expect("one output chunk per worker");
            handles.push(s.spawn(move || kernel.evaluate(dataset, chunk, out)));
        }
        for h in handles {
            match h.join() {
                Ok(Ok(())) => {}
                Ok(Err(e)) => return Err(e),
                Err(_) => {
                    return Err(
                        "scheduler: worker fault while evaluating a cell chunk — partial results are never published"
                            .to_string(),
                    )
                }
            }
        }
        Ok(())
    })
}

/// Run `f` over indices `0..n` on up to `threads` threads, collecting the
/// results in index order.
///
/// A task's own `Err` is a task RESULT — the caller owns the failure policy
/// (a per-cell replay error becomes the cube's NOT_EVALUABLE_ACTION cell, it
/// does not fail the batch). An infrastructure fault — a worker panic or a
/// join failure — fails the whole call (§7): `Err` is returned and no partial
/// result list is produced.
#[allow(dead_code)]
pub fn parallel_map<T: Send, F: Fn(usize) -> Result<T, String> + Sync>(
    threads: usize,
    n: usize,
    f: &F,
) -> Result<Vec<Result<T, String>>, String> {
    if threads <= 1 || n <= 1 {
        return Ok((0..n).map(f).collect());
    }
    let workers = threads.min(n);
    let bounds = chunk_bounds(n, workers);
    let mut results: Vec<Result<T, String>> = Vec::with_capacity(n);
    std::thread::scope(|s| -> Result<(), String> {
        let mut handles = Vec::with_capacity(workers);
        for w in 0..workers {
            let (lo, hi) = (bounds[w], bounds[w + 1]);
            handles.push(s.spawn(move || {
                let mut chunk = Vec::with_capacity(hi - lo);
                for i in lo..hi {
                    chunk.push(f(i));
                }
                chunk
            }));
        }
        for (w, h) in handles.into_iter().enumerate() {
            let chunk = match h.join() {
                Ok(c) => c,
                Err(_) => {
                    return Err(
                        "scheduler: worker fault while evaluating a task — partial results are never published"
                            .to_string(),
                    )
                }
            };
            // Workers are joined in worker order and each produced a
            // contiguous [lo, hi) slice, so extend preserves index order.
            debug_assert_eq!(chunk.len(), bounds[w + 1] - bounds[w]);
            results.extend(chunk);
        }
        Ok(())
    })?;
    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::backend::scalar::ScalarBackend;
    use crate::data::TapeRow;
    use crate::simulator::{Draft, FillPolicy, HOUR_NS};
    use crate::state::build_stores;
    use serde_json::Value;

    /// One kline tape row (mirror of backend/mod.rs's fixture, kept in-value
    /// identical so a thread-invariance comparison is meaningful).
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
        // 3 symbols x 14 bars; SOL gaps through the target (mirror of the
        // backend/mod.rs fixture) so the kernel exercises the same endpoint;
        // ETH and BTC get their own ramp shapes so cells differ per symbol.
        let mut rows = Vec::new();
        for (s, shape) in [
            ("SOLUSDT", 0usize),
            ("BTCUSDT", 1usize),
            ("ETHUSDT", 2usize),
        ] {
            for i in 0..14 {
                let c = match shape {
                    0 => {
                        if i < 8 {
                            100.0
                        } else {
                            130.0
                        }
                    } // gap-through
                    1 => 200.0 + 0.5 * (i as f64),  // slow ramp
                    _ => 3000.0 - 0.5 * (i as f64), // slow decay
                };
                rows.push(bar(c, c + 0.5, c - 0.5, c, s, i));
            }
        }
        let parsed: Vec<TapeRow> = rows
            .iter()
            .map(|v| TapeRow::from_parts(v, vec![]).unwrap())
            .collect();
        let ds = Dataset::from_rows(parsed).unwrap();
        let stores = build_stores(&ds);
        (ds, stores)
    }

    /// 1R geometry at atr_ref=10 with a horizon that reaches the SOL gap bar
    /// (bar 8) so the fixture's cells end in distinguishable endpoints.
    fn draft(direction: &str) -> Draft {
        let mut g = serde_json::Map::new();
        g.insert("atr_ref".to_string(), serde_json::json!(10.0));
        g.insert("target_r".to_string(), serde_json::json!(1.0));
        g.insert("stop_r".to_string(), serde_json::json!(1.0));
        g.insert("expiry_bars".to_string(), serde_json::json!(10));
        Draft {
            direction: direction.to_string(),
            birth_time: 0,
            risk_geometry: g,
        }
    }

    /// A batch that spans symbols, directions and entry windows — enough
    /// cells that a >1-thread partition actually splits the work, and enough
    /// variety that an order scramble would be visible.
    fn cells() -> Vec<ReplayCell<'static>> {
        let symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"];
        let mut out = Vec::new();
        for (i, symbol) in symbols.iter().enumerate() {
            for k in 0..4 {
                out.push(ReplayCell {
                    symbol,
                    draft: draft(if (i + k) % 2 == 0 { "LONG" } else { "SHORT" }),
                    start: 0,
                    end: 14,
                    thesis: None,
                });
            }
        }
        out
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

    fn zero() -> Outcome {
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
        }
    }

    fn run(threads: usize) -> Vec<Outcome> {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut out = vec![zero(); cells.len()];
        evaluate(threads, &backend(&stores), &ds, &cells, &mut out).unwrap();
        out
    }

    /// G5 thread invariance on the real parallel path (COMPUTE_SCHEDULING_SPEC
    /// §8.1): threads=1, 2 and 3 must produce byte-identical outcome batches.
    /// Pre-scheduler, the parallel path did not exist at all — parallelism was
    /// nominal; this test runs the actual `std::thread::scope` workers.
    #[test]
    fn threads_1_2_3_are_byte_identical() {
        let one = run(1);
        let two = run(2);
        let three = run(3);
        assert_eq!(one.len(), 12);
        for (a, b) in one.iter().zip(two.iter()) {
            assert_bit_identical(a, b);
        }
        for (a, b) in one.iter().zip(three.iter()) {
            assert_bit_identical(a, b);
        }
    }

    /// The parallel partition must not reorder: output[i] is the outcome of
    /// cells[i] even when a worker finishes late. Pinned by comparing each
    /// cell's draft signature against its output slot.
    #[test]
    fn parallel_output_stays_in_cell_order() {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut out = vec![zero(); cells.len()];
        evaluate(4, &backend(&stores), &ds, &cells, &mut out).unwrap();
        // The order contract is structural: cell k of symbol s lands in slot
        // k. entry_price pins the symbol (SOL 100, BTC 200, ETH 3000 — each
        // symbol's entry close); the SOL LONG cell additionally ends TARGET
        // because the bar-8 gap is inside its expiry window. Assert anchors
        // rather than re-derive every value.
        assert_eq!(out[0].endpoint, "TARGET"); // SOLUSDT LONG, gap-through target
        assert_eq!(out[0].entry_price, 100.0);
        assert_eq!(out[4].entry_price, 200.0); // BTCUSDT cell lands in slot 4
        assert_eq!(out[8].entry_price, 3000.0); // ETHUSDT cell lands in slot 8
    }

    /// Failure semantics (§7): a worker panic on the batch path fails the
    /// whole call — the caller receives `Err`, not a partial batch.
    #[test]
    fn batch_worker_panic_fails_closed() {
        let (ds, _stores) = fixture();
        let cells = cells();
        let mut out = vec![zero(); cells.len()];
        // A kernel that panics for one symbol: the batch must return Err.
        struct Panicky;
        impl ReplayKernel for Panicky {
            fn evaluate(
                &self,
                _dataset: &Dataset,
                cells: &[ReplayCell],
                output: &mut [Outcome],
            ) -> Result<(), String> {
                for (cell, slot) in cells.iter().zip(output.iter_mut()) {
                    if cell.symbol == "BTCUSDT" {
                        panic!("injected worker fault");
                    }
                    *slot = zero();
                }
                Ok(())
            }
        }
        let err = evaluate(3, &Panicky, &ds, &cells, &mut out).unwrap_err();
        assert!(
            err.contains("worker fault"),
            "a worker panic must surface as a scheduler Err: {err}"
        );
    }

    /// Failure semantics (§7) on the per-task path: a task's own Err is a task
    /// result, but a worker panic fails the whole call.
    #[test]
    fn task_errors_are_results_but_panics_fail_closed() {
        // Task errors are data: index order preserved, per-task Err reported.
        let results = parallel_map(3, 7, &|i| -> Result<i64, String> {
            if i == 2 {
                Err("task failed".to_string())
            } else {
                Ok(i as i64)
            }
        })
        .unwrap();
        assert_eq!(results.len(), 7);
        for (i, r) in results.iter().enumerate() {
            if i == 2 {
                assert!(r.is_err());
            } else {
                assert_eq!(r.as_ref().unwrap(), &(i as i64));
            }
        }

        // A worker panic fails the whole call.
        let err = parallel_map(3, 7, &|i| -> Result<i64, String> {
            if i == 5 {
                panic!("injected worker panic");
            }
            Ok(i as i64)
        })
        .unwrap_err();
        assert!(
            err.contains("worker fault"),
            "a worker panic must surface as a scheduler Err: {err}"
        );
    }

    /// threads=1 must take the exact sequential reference path (it delegates
    /// to the kernel's own batch evaluate) — the Backend-0 identity is
    /// preserved even though the scheduler now owns the dispatch.
    #[test]
    fn single_thread_is_the_sequential_reference() {
        let (ds, stores) = fixture();
        let cells = cells();
        let mut parallel_out = vec![zero(); cells.len()];
        evaluate(1, &backend(&stores), &ds, &cells, &mut parallel_out).unwrap();
        let mut direct_out = vec![zero(); cells.len()];
        backend(&stores)
            .evaluate(&ds, &cells, &mut direct_out)
            .unwrap();
        for (a, b) in parallel_out.iter().zip(direct_out.iter()) {
            assert_bit_identical(a, b);
        }
    }

    /// The chunk partition is deterministic and total: every index lands in
    /// exactly one worker, and the per-worker slices tile the batch.
    #[test]
    fn chunk_bounds_tile_the_batch() {
        for (n, workers) in [(1usize, 1usize), (7, 3), (12, 4), (5, 9), (0, 2)] {
            if n == 0 {
                continue;
            }
            let b = chunk_bounds(n, workers);
            assert_eq!(b[0], 0);
            assert_eq!(*b.last().unwrap(), n);
            assert_eq!(b.len(), n.min(workers).max(1) + 1);
            let mut total = 0;
            for w in 0..b.len() - 1 {
                assert!(b[w] < b[w + 1], "workers must be non-empty");
                total += b[w + 1] - b[w];
            }
            assert_eq!(total, n);
        }
    }

    fn assert_bit_identical(a: &Outcome, b: &Outcome) {
        assert_eq!(a.endpoint, b.endpoint);
        assert_eq!(
            a.net_r.to_bits(),
            b.net_r.to_bits(),
            "net_r must be bit-identical across thread counts"
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
