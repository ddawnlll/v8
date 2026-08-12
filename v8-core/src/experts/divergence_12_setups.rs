//! divergence_12_setups: evaluate() port target (issue #81) — mirror src/v8/experts/divergence_12_setups.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).

use crate::experts::base::*;

pub const PORTED: bool = false;
pub const VERSION: &str = "v1";

pub fn divergence_12_setups(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    no_habitat(expert_id, version, fm.as_of)
}
