# GitHub Copilot Custom Instructions

## 🚨 STRICT INVARIANT: RUST ONLY (`v8-core/`)

- **Authoritative Runtime:** `v8-core/` (Rust) is the sole active runtime and development codebase.
- **Python is FROZEN:** `src/v8/` and `tests/` are frozen historical parity oracles (`docs/legacy/PYTHON_ORACLE_POLICY.md`).
- **NEVER MODIFY PYTHON CODE:** Never edit, create, or refactor Python code in `src/v8/` or `tests/`. Any edit to `src/v8/` breaks the git tree hash lock (`tools/audit_python_boundary.py`).
- **All new code, features, fixes, and tests must be in Rust inside `v8-core/`.**
- Build & test: `cargo test --manifest-path v8-core/Cargo.toml`
