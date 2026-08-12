//! S7 verdict statistics (D-091; COMPUTE_CORE_SPEC §6): block-bootstrap
//! Reality-Check, detrended null, METH-3..METH-6. Consumes mt19937 for
//! bit-exact seeded RNG parity.

pub mod detrended;
pub mod reality_check;
pub mod remaining;

pub fn verdict(args: &[String]) -> i32 {
    eprintln!("S7 verdict not implemented yet (issue #128): args={args:?}");
    1
}
