# AGENTS.md — Agent Guidelines & Invariants

## 🚨 STRICT RULE: RUST ONLY — PYTHON CODEBASE IS FROZEN & DEPRECATED

### 1. Authoritative Runtime is Rust (`v8-core/`)
- **`v8-core/` is the ONLY active, authoritative codebase** for the entire project (runtime, compute plane, experts, scheduler, backends, analysis, verdict, evaluation, reports).
- **All code edits, bug fixes, new features, and tests MUST be written in Rust inside `v8-core/`.**

### 2. Python (`src/v8/` and `tests/`) is Strictly FROZEN
- `src/v8/` is a historical parity oracle locked via `docs/legacy/PYTHON_ORACLE_LOCK.json`.
- `tests/` is the historical Python harness, NOT the CI runtime gate.
- **AGENTS ARE STRICTLY PROHIBITED FROM MODIFYING `src/v8/` OR `tests/`.**
- Do NOT add, edit, or refactor Python code in `src/v8/`. Any modification to `src/v8/` breaks the git tree hash verification (`tools/audit_python_boundary.py`) and is considered a critical contract violation.

### 3. Allowed Python Usages
Only standalone documentation / tooling scripts in `tools/` may use Python:
- `tools/build_monograph.py`
- `tools/audit_python_boundary.py`
- `tools/forbidden_names.py`

### 4. Verification Commands
- `cargo test --manifest-path v8-core/Cargo.toml`
- `cargo check --manifest-path v8-core/Cargo.toml`
- `cargo clippy --manifest-path v8-core/Cargo.toml`
- `.venv/bin/python tools/audit_python_boundary.py`
