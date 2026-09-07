# Runnable Rust baseline

From the repository root:

```sh
cargo run --locked --manifest-path v8-core/Cargo.toml --bin check_local
```

Verification runs only locally. This command runs the oracle-boundary,
anti-synthetic, economic-claim and forbidden-name audits, then `cargo check`,
the Rust test suite, and Clippy with warnings denied. It stops on failure.
There are no GitHub Actions workflows or required GitHub CI checks.

The explicit real-data acceptance check requires the existing Binance BTCUSDT
hourly tape, adjacent `source.json`, and the source ZIP archives. It fails if
these inputs are missing; it never generates replacement market observations.
Choose a new output directory for each verification:

```sh
V8_REAL_TAPE="$PWD/research/tape/btcusdt-1h-12m/tape.jsonl" \
V8_ACCEPTANCE_OUT=/tmp/v8-main-acceptance \
cargo test --locked --manifest-path v8-core/Cargo.toml \
  --test runnable_main -- --ignored --nocapture
```

This runs the CLI twice with one fixed expert (`trend_continuation`), a 1,000
USDT simulated account, 0.5% risk fraction, and one concurrent position. It
checks archive digests against the source manifest, source labels and row count,
funding settlement, cashflow arithmetic, terminal account reconciliation, and
byte-identical receipt/ledger replay. `verification.json` fingerprints the tape,
binary, receipt, and ledger. ZIP verification does not independently reconstruct
the tape from those archives.

The generated `first/portfolio_receipt.json` and `first/economic-cashflow.jsonl`
are historical simulation diagnostics. Admission rejections remain visible in
the receipt. Missing optional data or unavailable venue fidelity is not proof of
live readiness. Funding is booked from observed settlement events when available,
using bar-open notional in the existing bar execution model; this is not venue
mark-price parity. Delayed events across closed positions require a richer event
execution model before live certification.

This baseline makes no profitability, live-execution, or recovery certification
claim. Outputs retain `promotion_authority: NONE`. The real-data check is ignored
by default so ordinary local checks do not silently depend on private or
untracked data. Run it explicitly when validating a runnable baseline.

GPU and release checks are explicit local operations when needed:

```sh
cargo check --locked --manifest-path v8-core/Cargo.toml --features gpu
cargo test --locked --manifest-path v8-core/Cargo.toml --release
```

Hardware GPU parity requires a suitable Linux/Vulkan device. Release packaging,
frozen-oracle differential checks, and monograph generation are manual local
operations; pushing a branch or tag triggers no GitHub workflow.
