# Runnable Rust baseline

From the repository root:

```sh
cargo check --locked --manifest-path v8-core/Cargo.toml
cargo test --locked --manifest-path v8-core/Cargo.toml
cargo clippy --locked --manifest-path v8-core/Cargo.toml --all-targets -- -D warnings
```

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
by default so ordinary CI does not silently depend on a developer's private or
untracked data. Run it explicitly when validating a runnable baseline.

The ordinary CI registry gate is Rust. Frozen Python differential parity and
monograph checks remain available on manual CI dispatch or release tags, rather
than gating ordinary Rust development.
