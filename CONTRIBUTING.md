# Development workflow

The authoritative runtime and tests are Rust in `v8-core/`. The Python oracle
under `src/v8/` and its historical `tests/` harness are frozen.

Follow the [owner-authorized governance reset](docs/GOVERNANCE_RESET_V86_2026-09-07.md):
ordinary work uses `edit → relevant checks → commit to main`. Issues, PRs,
monograph regeneration and release certificates are not per-edit gates.

For an affected library test from the repository root:

```sh
cargo test --locked --manifest-path v8-core/Cargo.toml --lib FILTER
```

For the complete local correctness gate:

```sh
cargo run --locked --manifest-path v8-core/tools/check-local/Cargo.toml
```

This dependency-free launcher runs the policy audits, all-target Clippy and the
Rust test suite. Clippy includes typechecking; a separate `cargo check` is useful
when requested on its own, but is not repeated inside the full gate. Both root
and `v8-core/` commands inherit the same compiler flags from `.cargo/config.toml`.
GitHub Actions are retired; verification is local.

Format touched Rust code and retain causality, arithmetic, cache integrity,
durability and authority checks. Do not fabricate market/economic evidence or
weaken assertions to improve timings. USD-M-specific tests are retired by owner
direction during the Nautilus migration; this does not certify the new engine.

GPU, release, frozen-oracle differential, and monograph checks belong to their
explicit risk/release boundaries. See [the Rust runbook](v8-core/README.md) and
[performance notes](v8-core/PERFORMANCE.md) for commands and measured limitations.
