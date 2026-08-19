# Workspace Rules

## 🚨 MANDATORY INVARIANT: RUST ONLY (`v8-core/`)

- **Authoritative Runtime:** `v8-core/` (Rust) is the ONLY active codebase for runtime, compute, experts, evaluation, and tests.
- **Python is FROZEN & DEPRECATED:** `src/v8/` and `tests/` are locked historical oracles.
- **AGENTS MUST NOT MODIFY PYTHON CODE:** Modifying `src/v8/` breaks git tree hashes and CI boundary checks (`tools/audit_python_boundary.py`).
- All work must be conducted in Rust inside `v8-core/`.

## Computation Budget (D-099)

Compute is evidence work, not a ritual. Run commands only when expected marginal decision value exceeds its cost.
Keep verification passes focused. CI and test gate is `cargo test --manifest-path v8-core/Cargo.toml`.
