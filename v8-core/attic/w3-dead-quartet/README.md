# W3 dead-code quartet (issue #346)

Four provably unreferenced files moved here from the live tree (git tracks
the renames; history preserved via `git log --follow`):

| Attic file | Original path | LOC | Consumer-scan receipt |
|---|---|---|---|
| `checkpoint.rs` | `v8-core/src/checkpoint.rs` | 77 | `SimulationCheckpoint` unused outside own file; `error.rs::Checkpoint` nominal only; `lib.rs`/`main.rs` mod decls removed |
| `world_learned.rs` | `v8-core/src/world/learned.rs` | 11 | Disabled stub (`is_enabled() == false`); sole ref was `world/mod.rs` re-export, removed; zero `LearnedChallengerGenerator` users |
| `analysis_scorecard.rs` | `v8-core/src/analysis/scorecard.rs` | 248 | Zero callers outside own test; `analysis/mod.rs` decl removed |
| `opportunity_harness_t1_t12.rs` | `v8-core/src/opportunity/harness_t1_t12.rs` | 236 | Zero production users; 13 internal tests moved with the file; `opportunity/mod.rs` decl removed |

These files are NOT compiled (no `mod` declaration references this directory).
Gate: `cargo check` green (see `.audit/w3/`).
