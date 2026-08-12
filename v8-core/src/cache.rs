//! S5 content-addressed DAG cache (issue #107; COMPUTE_CORE_SPEC §8 S5).
//! The missing node is cube level — (candidate_id, action_id,
//! simulator_hash, data_hash) -> outcome; a hit must never change the
//! ledger identity (the gate).
pub fn cache_check(args: &[String]) -> i32 {
    eprintln!("S5 cache-check not implemented yet (issue #107): args={args:?}");
    1
}
