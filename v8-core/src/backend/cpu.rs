//! Backend-1: the CPU backend (D-096).
//!
//! Task parallelism and SIMD land on a separate card (#132). This module is
//! the skeleton of that backend: it is selected by the same `ReplayKernel`
//! boundary and must reproduce the Backend-0 scalar reference bit-for-bit
//! (COMPUTE_SCHEDULING_SPEC §5). Today the CPU backend IS the sequential
//! scalar reference — `threads`/backend choice appears in no hash and no
//! manifest (D-084, G5).
//!
//! D-032 file-family registration: `backend/cpu.rs` — Backend-1 CPU skeleton.
//! No `std::thread`, rayon, or `target_feature` exists anywhere in
//! `v8-core/src/` (D-096: parallelism is a separate card, not this one).

use crate::backend::scalar::ScalarBackend;
use crate::backend::{ReplayCell, ReplayKernel};
use crate::data::Dataset;
use crate::simulator::{FillPolicy, Outcome};
use crate::state::FeatureStore;

/// The CPU backend. A thin sequential wrapper over the scalar reference today;
/// task parallelism lands inside `evaluate` on a separate card and must not
/// change a value (G5).
///
/// `allow(dead_code)`: Backend-1 is a skeleton in this card — it exists as the
/// named second slot on the `ReplayKernel` boundary and is exercised by the
/// backend-invariance test (COMPUTE_SCHEDULING_SPEC §8.2) plus `evaluate`;
/// no request path selects it yet (parallelism is a separate card, #132).
#[allow(dead_code)]
pub struct CpuBackend<'a> {
    scalar: ScalarBackend<'a>,
}

#[allow(dead_code)]
impl<'a> CpuBackend<'a> {
    pub fn new(
        round_trip_cost_r: f64,
        funding_rate_r: f64,
        funding_hours: i64,
        fill_policy: FillPolicy,
        funding_schedule: &'a [(i64, f64)],
        round_trip_cost_bps: Option<f64>,
        stores: &'a [FeatureStore],
    ) -> CpuBackend<'a> {
        CpuBackend {
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
        // Sequential today. #132 adds task parallelism here — it must keep the
        // cell-order output and stay bit-identical to the scalar reference.
        self.scalar.evaluate(dataset, cells, output)
    }
}
