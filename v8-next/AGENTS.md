# v8-next — V8.7 owner-authorized scope

On 2026-09-11 the owner explicitly confirmed that v8-next is the intended
codebase and instructed agents to replace the Rust-scoped V8.7 issues after
inspecting this implementation. For V8.7 NX00–NX11, implementation and tests
belong in v8-next (Python/Nautilus). This supersedes the historical freeze and
Rust-only wording below for this scope; no further reactivation approval is
required. Follow `../docs/contracts/V87_SWING_BENCHMARK_SPEC.md` and the NX issue
acceptance criteria. Preserve unrelated changes and all evidence/no-real-money
constraints. The paragraphs below describe the previous boundary where they
conflict with this explicit owner correction.

As of 2026-09-10, the active project implementation has returned to the Rust
codebase in `../v8-core/`. The root Rust-only instructions are authoritative.
This directory is a frozen experimental Python prototype/reference, not the
active product path. Do not add, edit, refactor, or extend its implementation or
tests unless the owner explicitly reactivates `v8-next/` in a later instruction.
Preserve unrelated user changes.

Commands in this directory may be run read-only for comparison, forensic
inspection, or reproducibility checks. They do not authorize new features,
economic claims, paper/live activation, or changes to the active architecture.

Read `../docs/contracts/V8_NEXT_IMPLEMENTATION_SCOPE.md` and the economic source
contracts relevant to the change. `../site/index.html` remains the constitutional
entry point; distinguish enacted requirements from historical decisions/drafts.
This file does not grant economic-claim or real-money authority.

Do not treat `v8-next/` as the source of truth for runtime, experts, execution,
evaluation, or reports. The active Rust source of truth is `../v8-core/`.

Use Python 3.12 and `uv.lock`. From the repository root:

```sh
uv sync --project v8-next --locked --extra dev
uv run --project v8-next --extra dev ruff check v8-next/src v8-next/tests
uv run --project v8-next --extra dev mypy v8-next/src
uv run --project v8-next --extra dev pytest -q v8-next/tests/RELEVANT_TEST.py
```

Run relevant checks during editing and integration checks at affected boundaries.
Use the owner-authorized tiered reset in `../docs/GOVERNANCE_RESET_V86_2026-09-07.md`.
A development commit is not a release receipt or goal-completion claim.

Synthetic data belongs only in tests, never in capture/evaluation artifacts.
Evaluation-claim tests (firing counts, scores, gates, PnL, certificates) MUST
run BenchmarkCase on a real population via BenchmarkRunner and MUST skip when
the tape is absent. Synthetic candles are allowed ONLY for mechanics/arithmetic
unit tests (pattern triggers, lifecycle transitions, ledger math) explicitly
marked MECHANICS ONLY with zero evaluative weight. No test may assert economic
performance on synthetic data.
Missing calibration, funding coverage, timestamps or statistical outputs must
stay missing. Do not force trades to make an acceptance run look successful.
Historical close-time availability is a labeled diagnostic model, never measured
availability. Simulated accounting is never actual venue cash settlement.
No private order client, transfer, account modification or live activation is
authorized. Public market capture and local paper simulation are permitted.
