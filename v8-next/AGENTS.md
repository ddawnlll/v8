# v8-next development boundary

The owner's explicit Python/library-first objective authorizes this directory
as the new product implementation. Root Rust-only instructions remain historical
for this scope; `src/v8/`, root `tests/`, and `v8-core/` remain frozen references
for this task. Do not import their runtime or compile legacy Rust for new-product
checks. Preserve unrelated user changes.

Read `../docs/contracts/V8_NEXT_IMPLEMENTATION_SCOPE.md` and the economic source
contracts relevant to the change. `../site/index.html` remains the constitutional
entry point; distinguish enacted requirements from historical decisions/drafts.
This file does not grant economic-claim or real-money authority.

Search `src/v8_next/` and `tests/` first (paths relative to this directory).
Nautilus owns native engine/orders/fills/accounts; Python owns economic meaning.
Do not recreate an OMS, simulator or scheduler, fork the engine, or migrate old
features for parity. Keep observer stances separate from capital authorization.

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
Missing calibration, funding coverage, timestamps or statistical outputs must
stay missing. Do not force trades to make an acceptance run look successful.
Historical close-time availability is a labeled diagnostic model, never measured
availability. Simulated accounting is never actual venue cash settlement.
No private order client, transfer, account modification or live activation is
authorized. Public market capture and local paper simulation are permitted.
