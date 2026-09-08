# V8-next (development, NO_ECONOMIC_CLAIM)

Python economic control plane over NautilusTrader. Legacy Rust and Python are
not imported, compiled or modified by these commands.

From the repository root:

```sh
uv sync --project v8-next --extra dev --locked
uv run --project v8-next python -m v8_next.adapters.binance_capture /tmp/v8-capture-new
uv run --project v8-next python -m v8_next.adapters.native_tape /tmp/v8-capture-new/manifest.json --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000
uv run --project v8-next --extra dev pytest -q v8-next/tests
uv run --project v8-next --extra dev ruff check v8-next/src v8-next/tests
uv run --project v8-next --extra dev mypy v8-next/src
```

The example fee rates and initial balance are explicit simulation assumptions,
not a statement of the user's actual commission schedule or capital. Capture
uses public REST only. Choose a new directory for each capture. Historical
availability remains unknown. The native replay is explicitly diagnostic-only,
uses current instrument metadata, and currently has no economic strategy attached.
It therefore creates no orders. This is not yet the completed paper product.

The pinned engine is **2.0.0rc4**, a prerelease. The native test qualifies fees,
funding and duplicate funding settlement using isolated synthetic test inputs.
It does not establish venue liquidation or live correctness. Polars calculates
the squeeze observer's features; missing calibration rejects utility admission.

See [full scope](../docs/contracts/V8_NEXT_IMPLEMENTATION_SCOPE.md) for the
constitutional mapping, remaining work and source/version rationale.

Prospective decision observation (execution is not attached yet):

```sh
uv run --project v8-next python -m v8_next.app.observe /tmp/v8-observation-new
uv run --project v8-next python -m v8_next.app.observe /tmp/v8-observation-new --replay-capture /tmp/v8-observation-new/capture-REPLACE_WITH_ACTUAL_ID/manifest.json
```

The first command freezes source/config/lock identity before requesting new data.
Each response becomes known at its actual local receipt for future decisions;
this does not establish historical availability. Identical capture replay after
restart does not duplicate the decision. Different code requires a new run.
Missing calibration stays missing, with no engine order submission. This command
is a prospective observation precursor, not the completed funded paper service.

Read-only diagnostic evaluation of a recorded run:

```sh
uv run --project v8-next python -m v8_next.app.evaluate /tmp/v8-observation-new
```

This verifies policy, decision and source hashes, counts recorded observations,
and explicitly leaves unsupported economic/statistical results absent. Snapshot
counts are not independent samples. It cannot authorize economic promotion.

Bounded native paper account (currently no verified calibration, so no campaigns):

```sh
uv run --project v8-next python -m v8_next.app.paper /tmp/v8-paper-new --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000 --max-notional 100 --max-exposure-fraction 0.1
uv run --project v8-next python -m v8_next.app.paper /tmp/v8-paper-new --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000 --max-notional 100 --max-exposure-fraction 0.1 --replay-only
```

Each non-replay invocation captures another real snapshot. Before extending a
session, it recreates the previously recorded native account and compares its
economic state. Historical bars are not injected into the prospective account.
Quotes retain venue event time and local receipt time. These sparse REST snapshots
are not a continuous execution feed. The positive admission-to-fill route is qualified with test-only calibration;
production calibration verification and online funding remain outstanding; a zero-position account does not qualify either behavior.

Historical observer diagnostic (real captured bars, explicitly modeled close-time
availability; not a qualified PIT/economic backtest):

```sh
uv run --project v8-next python -m v8_next.app.backtest \
  /path/to/capture/manifest.json /path/to/new-result.json \
  --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000
```

Fees and starting capital above are explicit simulation assumptions. The native
bar callback evaluates every causal prefix, records baseline/opportunity/stance
and missing-calibration rejection, and exports native account state. No strategy
order is authorized without calibration. Historical availability stays unknown
in the output; modeled frames cannot support prospective or profitability claims.

Inspect prospective outcome sources before a proposed decision timestamp:

```sh
uv run --project v8-next python -m v8_next.evaluation.calibration \
  /path/to/paper-run /path/to/new-inspection.json --decision-ns DECISION_UNIX_NS
```

This read-only command verifies inputs and recomputes native accounting. It
separates open and closed positions, preserves simulated realization and funding
coverage, and requires the accounting cutoff to precede the proposed decision.
It is a source inspector, not a calibrated estimator: absent qualified outcomes
leave utility eligibility false and edge/uncertainty null. The timestamp argument
is an evaluation cutoff request, not evidence that a prospective decision occurred.

Verified local environment (Python 3.12.12; exact resolution in `uv.lock`):

| Dependency | Installed version | Used responsibility |
|---|---|---|
| NautilusTrader | 2.0.0rc4 | Native simulation, orders, positions, accounts |
| Polars | 1.44.1 | Observer rolling features |
| NumPy | 2.5.3 | Native ecosystem dependency; no custom estimator yet |
| Pydantic | 2.13.5 | External paper configuration validation |
| pytest | 9.1.1 | Qualification tests |
| Hypothesis | 6.167.1 | Causal property tests |
| Ruff | 0.16.6 | Formatting and lint |
| mypy | 2.3.1 | Python type checks |

These versions were read from the locked installed environment, not inferred
from upstream latest documentation. macOS ARM64 execution is demonstrated here;
Linux installation/execution has not been exercised in this workspace. Local
writer locking uses POSIX `flock`; Windows is not a qualified target.

Optional numerical research integration:

```sh
uv sync --project v8-next --locked --extra dev --extra research
uv run --project v8-next --extra dev --extra research pytest -q v8-next/tests/test_inference.py
```

`evaluation.inference.spa_diagnostic` delegates stationary-bootstrap SPA to
`arch` 8.0.0 with explicit block size, repetitions and seed. It consumes paired
chronological losses and returns all three named p-value variants with dependency
versions. It does not verify data provenance, complete search history or pristine
holdout status, and cannot authorize utility or claims. Real outcome ingestion is
not yet connected; the integration test uses isolated synthetic loss fixtures.
WRC/DSR/PBO remain missing. Optional dependencies include SciPy, pandas and
statsmodels through arch; normal paper commands do not require the research extra.

Combined paper report, including recomputed outcome provenance:

```sh
uv run --project v8-next python -m v8_next.app.report \
  /path/to/paper-run /path/to/new-report.json --decision-ns DECISION_UNIX_NS
```

This combines observation/lineage evaluation and campaign/accounting replay. It
fails if either source verification fails. It explicitly reports why no paired
economic comparison is available; it does not turn no-trade observations into
artificial loss samples or call SPA on missing outcomes. Native logs remain on
stdout/stderr while the result is written to the requested new JSON file.

The combined report also executes the frozen breakout baseline through the same
admission/native engine path, then revalues its own campaigns using the same
funding cutoff as the squeeze variant. Both native and revised accounting views
are retained. `baseline_cash_return` and `variant_cash_return` are descriptive
fixed-capital terminal cash returns only: open positions or unqueried funding
exposure leave them missing. They are not calibrated edge estimates or samples
for SPA. Zero return from a verified no-position account does not establish skill.

Paper captures request an explicit funding-history interval from session freeze
to request time. A response at the 1000-record limit rejects the capture; pagination
for longer sessions remains unsupported. Revised accounting reports query windows
and per-position coverage separately from cashflow finality. It does not assume
an eight-hour funding schedule or use forecast rates as settled payments.

Latest integrated local check (2026-09-08): real public capture, separate-process
restart, another capture, and combined report all completed. Artifacts are under
`/var/folders/db/04433_v94tv8xpr31czl2j200000gn/T/v8-next-integrated-zdmhjllz/`
(`acceptance.json`, `report.json`, captures, checkpoint, SQLite and per-stage logs).
There were two decisions and no positions. Measured process times were 3.935 s
first capture/paper, 0.433 s replay-only restart and 3.553 s continuation. These
include different work and are not language-speed comparisons. Full suite passed
58 tests in 2.30 s pytest time (`/tmp/v8-next-integrated-suite.log`). Temporary
artifacts are development evidence, not permanent release certificates.

Add `--trajectory` to the combined report command to replay every capture prefix
for both policies. Each row exposes cumulative and incremental cash change using
only that prefix's available records. Missing values propagate across the affected
increment; they are never imputed or skipped. The initial cash change is zero in
the fixed-capital simulator before its first event. This optional diagnostic
replays prefixes repeatedly and becomes expensive on long sessions. Irregular
capture intervals, unqualified equity marks and venue revisions prevent automatic
use as a statistical loss sample; the option does not call SPA or authorize claims.
