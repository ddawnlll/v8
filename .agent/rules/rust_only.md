---
description: Enforces Rust-only development and forbids modifying the frozen Python oracle.
always_on: true
---

# Rust-Only Runtime Invariant

- **The sole runtime codebase is `v8-core/` (Rust).**
- All feature additions, bug fixes, evaluations, analysis, and tests must be implemented in Rust under `v8-core/`.
- `src/v8/` and `tests/` (Python) are **FROZEN & DEPRECATED** historical parity oracles. Agents must NEVER modify, create, or delete files in `src/v8/` or `tests/`.
- CI and local checks use `cargo test --manifest-path v8-core/Cargo.toml`.
