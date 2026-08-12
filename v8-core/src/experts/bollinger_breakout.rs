//! bollinger_breakout: evaluate() port target (issue #77) — mirror src/v8/experts/bollinger_breakout.py
//! bit-for-bit (PARITY_AND_IDENTITY_SPEC §3; COMPUTE_CORE_SPEC §8 S4).

use crate::experts::base::*;

pub const PORTED: bool = false;
pub const VERSION: &str = "v1";

pub fn bollinger_breakout(fm: &FeatMap, expert_id: &str, version: &str) -> ExpertEval {
    no_habitat(expert_id, version, fm.as_of)
}
