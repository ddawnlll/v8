# Runnable Rust baseline

From the repository root:

```sh
cargo run --locked --manifest-path v8-core/tools/check-local/Cargo.toml
```

Verification runs only locally. This command runs the oracle-boundary,
anti-synthetic, economic-claim and forbidden-name audits, then all-target Clippy
with warnings denied and the Rust test suite. Clippy includes typechecking. It stops on failure.
There are no GitHub Actions workflows or required GitHub CI checks.

USD-M simulator acceptance tests have been retired by owner direction as
production execution moves to NautilusTrader. Shared risk, cashflow, causality
and authority checks remain. This does not certify the replacement engine.

Historical H4 diagnostics now require explicit inputs and output:

```sh
cargo run --locked --manifest-path v8-core/Cargo.toml --bin v8-core -- \
  h4-decomposition --tape research/tape/btcusdt-1h-12m/tape.jsonl --out /tmp/h4.txt
```

See [performance changes](PERFORMANCE.md) for validation scope, cache boundaries
and measured results.

GPU and release checks are explicit local operations when needed:

```sh
cargo check --locked --manifest-path v8-core/Cargo.toml --features gpu
cargo test --locked --manifest-path v8-core/Cargo.toml --release
```

Hardware GPU parity requires a suitable Linux/Vulkan device. Release packaging,
frozen-oracle differential checks, and monograph generation are manual local
operations; pushing a branch or tag triggers no GitHub workflow.
