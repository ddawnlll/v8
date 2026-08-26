# D-141 rebuild command receipt — diagnostic only

## Status

`INVALID_FOR_D140_ECONOMIC_BASELINE_COMPARISON`

This run invoked the low-level `v8-core usdm-sim` subcommand.  It did **not**
invoke a recorded D-140 release manifest, and therefore must not be read as a
reproduction, confirmation, or refutation of D-140's published `+$227.48`
result.  The D-140 release commit does not include the exact command/request
manifest that produced that aggregate result.

## Compared revisions

| cohort | revision |
| --- | --- |
| baseline | `5832286da495afe9751a77a3bdcf3a5f1ca13ad8` |
| candidate | `3f605d34f89b26c1fa5c9a6839a1bea94f98373e` |

## Fixed input

| field | value |
| --- | --- |
| tape | `/Users/hootie/src/v8/research/tape/quad-1h-12m/tape.jsonl` |
| SHA-256 | `695eaec7d726b20c70e3a4d836e69206015d522753381e92f2fb2406414220e1` |
| exit arm | `struct24h` (`Structural24hTrail`) |
| symbols | `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `AVAXUSDT` |
| unpassed CLI defaults | `initial_balance=1000`, `risk_fraction=0.005`, `leverage=10`, `max_concurrency=3`, `max_heat=0.05`, all ported experts |

## Exact execution commands

The pre-D-141 revision was built in an isolated detached worktree.  BTCUSDT
was compiled and run with:

```sh
CARGO_TARGET_DIR=/private/tmp/v8-d141-target.RBM1gQ \\
  cargo run --release \\
  --manifest-path /private/tmp/v8-d141-baseline.uVtFIx/v8-core/Cargo.toml \\
  --bin v8-core -- \\
  usdm-sim \\
  --tape /Users/hootie/src/v8/research/tape/quad-1h-12m/tape.jsonl \\
  --out /Users/hootie/src/v8/.audit/d141-rebuild-20260824/baseline/BTCUSDT \\
  --exit-arm struct24h \\
  --symbol BTCUSDT
```

The other baseline symbols were run using the resulting binary:

```sh
/private/tmp/v8-d141-target.RBM1gQ/release/v8-core usdm-sim \\
  --tape /Users/hootie/src/v8/research/tape/quad-1h-12m/tape.jsonl \\
  --out /Users/hootie/src/v8/.audit/d141-rebuild-20260824/baseline/<SYMBOL> \\
  --exit-arm struct24h --symbol <SYMBOL>
```

The D-141 candidate was built with:

```sh
CARGO_TARGET_DIR=/private/tmp/v8-d141-candidate-target.diB9eb \\
  cargo build --quiet --release \\
  --manifest-path /Users/hootie/src/v8/v8-core/Cargo.toml \\
  --bin v8-core
```

Each candidate symbol was then run using:

```sh
/private/tmp/v8-d141-candidate-target.diB9eb/release/v8-core usdm-sim \\
  --tape /Users/hootie/src/v8/research/tape/quad-1h-12m/tape.jsonl \\
  --out /Users/hootie/src/v8/.audit/d141-rebuild-20260824/candidate/<SYMBOL> \\
  --exit-arm struct24h --symbol <SYMBOL>
```

Here `<SYMBOL>` was substituted once each with `BTCUSDT`, `ETHUSDT`,
`SOLUSDT`, and `AVAXUSDT`.

## Output integrity

For each symbol, baseline and candidate `portfolio_receipt.json` and
`economic-cashflow.jsonl` were byte-identical.  Receipt SHA-256 values:

| symbol | SHA-256 |
| --- | --- |
| BTCUSDT | `8d30db4636c501d50a56f4cd0f43e65fd71cf5bd901e8adf1817dd3855e76a47` |
| ETHUSDT | `05d1767c045b0c588f067a038fa6f0e70c87c8ad7d04ae7cd8726e701b65264b` |
| SOLUSDT | `e0cf602222096e3d7c0cb47f30969cad3fa57ea3244bb7310fc7cdb0155428ff` |
| AVAXUSDT | `1cadf592363f98d76a4e9c9c1d348f787b25adeb323c61d7baae1dd30d439594` |

