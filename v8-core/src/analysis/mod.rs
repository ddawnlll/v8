//! S6 analysis plane (D-091; COMPUTE_CORE_SPEC §6): reconciliation + regret
//! phases 1-3. One module per concern so the stages port in parallel.

pub mod outcome;
pub mod phase1;
pub mod phase2;
pub mod phase3;
pub mod reconcile;

pub fn reconcile(args: &[String]) -> i32 {
    reconcile::run(args)
}

/// S6 composition: phases 1-3 over the reconciled tables (issue #116).
pub fn analysis(args: &[String]) -> i32 {
    eprintln!("S6 analysis composition not implemented yet (issue #116): args={args:?}");
    1
}
