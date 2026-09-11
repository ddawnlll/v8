# V8-next (FROZEN EXPERIMENTAL PROTOTYPE, NO_ECONOMIC_CLAIM)

> **Active project boundary (2026-09-10):** Active development has returned to
> the Rust implementation in [`../v8-core/`](../v8-core/). This Python tree is
> retained for reference and read-only diagnostics; do not add new product
> implementation here without an explicit owner reset.

Python economic control plane over NautilusTrader. Legacy Rust and Python are
not imported, compiled or modified by these commands. The commands below are
historical/prototype diagnostics and are not the active project workflow.

From the repository root:

```sh
uv sync --project v8-next --extra dev --locked
uv run --project v8-next python -m v8_next.app.cli status
uv run --project v8-next python -m v8_next.app.cli benchmark --diagnostic-only
```

`cli status` is the project dashboard: git revision, tape inventory,
code/test footprint, and the latest benchmark receipt rendered as the
canonical readiness table (no engine run, no claims). `cli benchmark`
delegates to the D-153 end-to-end battery and refuses synthetic fallback
when the real tape is absent. The per-module commands below remain for
narrow manual steps; new evaluative workflows go through the CLI.

```sh
uv run --project v8-next python -m v8_next.app.cli capture /tmp/v8-capture-new
uv run --project v8-next python -m v8_next.app.cli native-tape /tmp/v8-capture-new/manifest.json --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000
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
uv run --project v8-next python -m v8_next.app.cli observe /tmp/v8-observation-new
uv run --project v8-next python -m v8_next.app.cli observe /tmp/v8-observation-new --replay-capture /tmp/v8-observation-new/capture-REPLACE_WITH_ACTUAL_ID/manifest.json
```

The first command freezes source/config/lock identity before requesting new data.
Each response becomes known at its actual local receipt for future decisions;
this does not establish historical availability. Identical capture replay after
restart does not duplicate the decision. Different code requires a new run.
Missing calibration stays missing, with no engine order submission. This command
is a prospective observation precursor, not the completed funded paper service.

Read-only diagnostic evaluation of a recorded run:

```sh
uv run --project v8-next python -m v8_next.app.cli evaluate /tmp/v8-observation-new
```

This verifies policy, decision and source hashes, counts recorded observations,
and explicitly leaves unsupported economic/statistical results absent. Snapshot
counts are not independent samples. It cannot authorize economic promotion.

Bounded native paper account (currently no verified calibration, so no campaigns):

```sh
uv run --project v8-next python -m v8_next.app.cli paper /tmp/v8-paper-new --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000 --max-notional 100 --max-exposure-fraction 0.1
uv run --project v8-next python -m v8_next.app.cli paper /tmp/v8-paper-new --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000 --max-notional 100 --max-exposure-fraction 0.1 --replay-only
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
uv run --project v8-next python -m v8_next.app.cli backtest \
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
uv run --project v8-next python -m v8_next.app.cli calibration \
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
uv run --project v8-next python -m v8_next.app.cli report \
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

For explicitly exploratory research, `report --exploratory-spa BLOCK REPS SEED`
computes the trajectory and requests the optional arch SPA adapter. Install the
`research` extra and pass all three parameters; no plan defaults are invented.
Loss is negative incremental simulated cash return per capture interval. Missing
intervals and degenerate differentials produce an explicit absent result, not a
p-value. A calculated result remains `NOT_VERIFIED_EXPLORATORY_ONLY`: irregular
sampling, full search history, funding revisions and preregistration are unresolved.
It cannot supply utility, satisfy the constitutional WRC gate or promote a claim.

First-slice acceptance and current installed artifact evidence:
[requirement-by-requirement audit](../docs/contracts/V8_NEXT_FIRST_SLICE_ACCEPTANCE.md).
This is a working research/prospective no-trade slice, not calibrated or live-money
readiness. Explicit missing-calibration, funding and claim gates remain closed.

### Offline policy experiments on real captures

`v8_next.app.trial` runs an explicitly DEVELOPMENT-only counterfactual policy
through Nautilus historical bars. It measures what the frozen rule would do;
it does not mint utility estimates or authorize production trades. Use a JSON
PaperConfig with explicit fees, balance, notional/exposure caps and selected
observer_policy, grammar_policy and campaign_policy:

```sh
uv run --project v8-next --extra dev --extra research python -m v8_next.app.cli trial \
  /absolute/path/capture/manifest.json /absolute/path/policy.json \
  /absolute/path/trial-result.json \
  --store /absolute/path/research.sqlite --family declared-development-family
```

The trial is registered before replay, including source/lock hash, config,
execution model and dataset hash. A dataset registered HOLDOUT in that store
cannot be consumed here. Output creation is exclusive. Use the same research
store to preserve the attempted-trial count, including unsuccessful choices.
Native callbacks execute prior selections on a later real bar; no synthetic
quotes or fabricated calibration enter this path. Outputs include campaigns,
order events, native account state and explicit limitations. OHLC path assumptions,
unmeasured historical spread/slippage, current metadata and incomplete funding
qualification make these outputs **ineligible for calibration or edge claims**.
The production paper controller still requires separately verified calibration.

Compare all recorded members of one development family with an explicit baseline:

```sh
uv run --project v8-next --extra dev --extra research python -m v8_next.app.cli compare \
  /absolute/path/baseline.json /absolute/path/variant.json \
  --store /absolute/path/research.sqlite --family declared-development-family \
  --baseline BASELINE_TRIAL_ID --block-size 12 --reps 999 --seed 42 \
  --output /absolute/path/comparison.json
```

Bootstrap values above are examples, not approved statistical plans. Include every
trial registered in that family; missing/failed attempts block comparison. Sources,
runtime, fees and capital must match. SPA/WRC use complete aligned marked-equity
intervals, including open exposure. Outputs retain input hashes and remain
DEVELOPMENT_EXPLORATION_NOT_OOS and NO_ECONOMIC_CLAIM. Undefined statistics reject
without dropping candidates. PBO/DSR and protected OOS plans are not inferred.

Optional `--pbo-plan /absolute/path/cscv.json` adds CSCV/PBO. The JSON must
contain exactly `partitions` (even integer), `metric` (`mean_return` or `sharpe`),
`max_splits` (integer budget), and `registered_variants` (all non-baseline trial
IDs). At least two candidates in addition to the baseline are required. The
interval count must divide evenly; no truncation or sampled substitute occurs.
Plan bytes are hashed in the comparison inputs. This remains exploratory PBO,
not protected OOS or proof of complete external search history.

Optional `--dsr-reference /absolute/path/reference.json` enables DSR only with
an explicit reference series and independence plan. Required fields:
`currency` = `USDT`, `convention` =
`NEGATIVE_REFERENCE_RETURN_OVER_FIXED_INITIAL_CAPITAL`, `capital` matching the
trials, `selected_variant`, `registered_variants` (all non-baseline IDs),
`effective_independent_trials`, `independence_basis`, `reference_basis`,
`source_identity`, and `intervals`. Each interval requires `start_ns`, `end_ns`,
`available_ns` and decimal `loss` (negative reference return). Supply actual
aligned reference observations; no default zero series is inserted. The artifact
hash, metadata and reference values are retained. Schema validation does not
certify the reference source or independent-trial assumption. DSR is confidence,
not a p-value, and does not promote these development observations.

Freeze a future hourly experiment with `python -m v8_next.app.cli plan plan.json
--id NAME --store research.sqlite` (using the same uv environment). The JSON
requires `instrument_id`, future UTC-hour-aligned `start_ns`/`end_ns`, `policies`
(a name-to-PaperConfig mapping), member `baseline`, `block_size`, `reps`, `seed`.
The registry stores the full plan, source/lock hash and actual registration clock.
Changed plans cannot reuse an ID; identical retries retain the original clock.
Recording a plan does not run the experiment or establish protected OOS evidence.

After that future source window completes, execute the frozen family:

```sh
uv run --project v8-next --extra dev --extra research python -m v8_next.app.cli forward \
  /absolute/path/capture/manifest.json --plan-id NAME \
  --store /absolute/path/research.sqlite --output /absolute/path/forward.json
```

The capture must contain exactly the declared hourly source window. Code/lock
must match the frozen plan. Its first bar supplies the first equity mark, so N
bars yield N-1 measured intervals; no pre-window balance is invented. All planned
policies run; degenerate comparisons reject rather than drop candidates. A plan
binds permanently to one dataset even if later execution fails; same-data retries
are reproducibility attempts, not fresh holdouts. The result is
PREREGISTERED_FORWARD_WINDOW_MODELED_REPLAY, not certified prospective execution:
historical availability, venue fills/costs and outside access remain unqualified.

PaperConfig optionally accepts `stop_budget` with explicit `risk_fraction`,
`max_heat_fraction` and `max_concurrency`. A protected campaign policy is required.
Both offline trials and paper admission then cap requested notional by the
stop-distance budget before venue quantity rounding. Current app scope still
requires an empty native portfolio/order set and no pending campaign; this does
not enable concurrent portfolio allocation or bypass missing calibration/funding.
