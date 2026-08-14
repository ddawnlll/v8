//! Backend-1: the CPU backend (D-096, #132).
//!
//! This is the task-parallel CPU backend: it is selected by the same
//! `ReplayKernel` boundary and must reproduce the Backend-0 scalar reference
//! bit-for-bit (COMPUTE_SCHEDULING_SPEC §5). The parallel decomposition is
//! real — `evaluate` routes the cell batch through `scheduler::evaluate`,
//! which runs `min(threads, cells)` worker threads over contiguous chunks —
//! but `threads`/backend choice appears in no hash and no manifest (D-084,
//! G5). SIMD and GPU remain absent (no `target_feature`, no backend).
//!
//! D-032 file-family registration: `backend/cpu.rs` — Backend-1 CPU backend
//! (task parallelism; SIMD/GPU on later cards).

use crate::backend::scalar::ScalarBackend;
use crate::backend::{ReplayCell, ReplayKernel};
use crate::data::Dataset;
use crate::simulator::{FillPolicy, Outcome};
use crate::state::FeatureStore;

/// The CPU backend: `scheduler::evaluate` over the scalar reference, with
/// `threads` worker threads. `threads <= 1` is the sequential reference path.
pub struct CpuBackend<'a> {
    threads: usize,
    scalar: ScalarBackend<'a>,
}

impl<'a> CpuBackend<'a> {
    pub fn new(
        threads: usize,
        round_trip_cost_r: f64,
        funding_rate_r: f64,
        funding_hours: i64,
        fill_policy: FillPolicy,
        funding_schedule: &'a [(i64, f64)],
        round_trip_cost_bps: Option<f64>,
        stores: &'a [FeatureStore],
    ) -> CpuBackend<'a> {
        CpuBackend {
            threads,
            scalar: ScalarBackend {
                round_trip_cost_r,
                funding_rate_r,
                funding_hours,
                fill_policy,
                funding_schedule,
                round_trip_cost_bps,
                stores,
            },
        }
    }
}

impl<'a> ReplayKernel for CpuBackend<'a> {
    fn evaluate(
        &self,
        dataset: &Dataset,
        cells: &[ReplayCell],
        output: &mut [Outcome],
    ) -> Result<(), String> {
        // Real task parallelism (COMPUTE_SCHEDULING_SPEC §4.1, §8.1): the
        // scheduler keeps cell-order output and stays bit-identical to the
        // scalar reference across thread counts (G5).
        crate::scheduler::evaluate(self.threads, &self.scalar, dataset, cells, output)
    }
}
