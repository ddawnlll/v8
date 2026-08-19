# Rust Only Runtime Rule

- **Authoritative Codebase:** `v8-core/` (Rust)
- **Frozen Python Codebase:** `src/v8/` and `tests/`
- AI agents must NEVER edit, add, or delete files in `src/v8/` or `tests/`. All development must be done in `v8-core/`.
