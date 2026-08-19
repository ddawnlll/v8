# V8 Build Agent Guide

## 🚨 MANDATORY ARCHITECTURE RULE: RUST ONLY (`v8-core/`)

- **Authoritative Runtime:** `v8-core/` (Rust) is the sole active runtime, evaluation, and compute codebase.
- **Python is FROZEN:** `src/v8/` and `tests/` are frozen historical parity oracles (`docs/legacy/PYTHON_ORACLE_POLICY.md`).
- **NEVER MODIFY PYTHON CODE:** AI agents are strictly prohibited from creating, editing, or refactoring Python code in `src/v8/` or `tests/`. Any edit to `src/v8/` invalidates the git tree hash lock (`tools/audit_python_boundary.py`).
- **Verification:**
  - `cargo test --manifest-path v8-core/Cargo.toml`
  - `cargo check --manifest-path v8-core/Cargo.toml`
  - `.venv/bin/python tools/audit_python_boundary.py`

## 🚨 WORK-ITEM & PR GOVERNANCE (v1.2)
- All development follows `docs/WORK_ITEM_POLICY.md` and `CONTRIBUTING.md`.
- Universal context-completeness contract (`R#` traceability, reused types, invariants, failure semantics, dependency map, OPEN_PIN triggers) required for all work items.
- Full requirement-to-receipt traceability required on PRs.
- Zero synthetic data / zero-tolerance anti-hallucination directive.

