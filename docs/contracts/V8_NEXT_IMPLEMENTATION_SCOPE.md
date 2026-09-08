# V8-next implementation scope

Status: owner-authorized development architecture; not a release or economic
certification. Started 2026-09-08. This document does not amend economic claim
requirements in `site/index.html`. The current explicit owner instruction
supersedes Rust-only development for `v8-next/`; legacy Python and Rust remain
untouched reference implementations. No legacy runtime imports or compilation.

## Boundary

Python owns opportunity identity, observer stances, reconciliation, utility,
exposure admission, experiment lineage and claim gating. Nautilus owns generic
event processing, simulated execution, orders, positions and accounts. Polars
owns dataframe computation. Standard libraries own persistence primitives.
No custom simulator, OMS, scheduler or engine fork is authorized by this design.

The intended flow is real data → PIT frame → opportunity grammar/book ← expert
stances → reconciliation → utility → portfolio admission → execution campaign
→ Nautilus → accounting and evaluation. A Nautilus strategy is an adapter, not
an expert with capital authority. Initial universe is narrow Binance USD-M;
no live private execution, money movement or account changes are enabled.

## Engine checkpoint

The initially present package skeleton pinned 1.231.0. Development now pins
2.0.0rc4: this is explicitly a prerelease dependency, not a stability claim.
The Python 3.12 wheel installs without compiling legacy Rust. Tagged source
`https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/backtest/src/exchange.rs`
contains native funding settlement and duplicate settlement tracking.
`tests/test_native_engine.py` qualifies a synthetic long position, commission,
funding debit and duplicate funding event through the public engine API.
It is test-only arithmetic evidence, never economic evidence.

Real captured data was replayed through the native engine: 499 closed candles,
62 funding records (with source mark prices), 623 engine iterations, no strategy
and no orders. Local raw manifest: `/tmp/v8-next-capture-20260908-initial/manifest.json`;
native diagnostic output: `/tmp/v8-next-native-real.log`. These temporary paths
are development evidence, not permanent release artifacts. Explicit fee inputs
were simulation assumptions 0.0002 maker / 0.0005 taker and initial balance
10000 USDT. No measured fee schedule or economic result is claimed.

Exact Binance margin brackets, liquidation and sandbox funding remain UNVERIFIED.
Bounded local replay recovery and public-data prospective no-trade operation now
exist; these do not establish live venue recovery or position-bearing prospective
economic qualification. A passing unit checkpoint does not satisfy those remaining
acceptance requirements.
The generic NETTING/MARGIN test is not evidence of exact venue isolated-margin
behavior. A dependency fork is not the default remedy for missing capabilities.

## Data and clocks

Capture stores original public REST responses, source URLs, request/receipt
timestamps and SHA-256 hashes. Existing capture directories cannot be replaced.
A manifest is only written after every request succeeds. Partial directories
without a manifest are not valid runs. Hashes detect substitution relative to
the manifest; they do not authenticate Binance or make the manifest tamper-proof.

Historical REST availability is UNKNOWN, not inferred from candle close or ETL
time. The decoded historical candle therefore cannot enter an authoritative
historical PIT frame. Current incomplete candles are excluded. Prospective
observation requires separately recorded receipt knowledge and a frozen policy.
Any research-only historical timing model must be explicitly labeled and cannot
silently upgrade these records to certified simulation.

## Constitutional mapping and remaining work

| Requirement | Executable evidence / remaining implementation |
|---|---|
| PIT/non-interference | `test_causality.py`; `test_historical_observer.py` checks changed future suffix against prior decisions. Historical modeled clocks remain diagnostic. |
| Feed clone invariance | Exact duplicate bars deduplicated; conflicting versions rejected; dependency groups deduplicated in reconciliation. |
| No fictitious artifacts | Capture verifier rejects absent/substituted/external references; hashes do not authenticate the source. |
| Fee/funding conservation | Native open/close/duplicate/late-settlement qualification; position-bearing prospective coverage remains unqualified. |
| Opportunity independent of observers | `opportunity_at` binds grammar/exposure/instrument/direction/bar boundary; economic tests cover clone invariance. |
| Observer lacks execution authority | Frozen `Stance` contains observations; separate controller creates `PaperCampaign`, native adapter submits orders. |
| Utility and exposure admission | Controller/risk tests cover missing calibration, costs, stale state, exposure caps, quantity rounding and duplicate campaigns. Real calibration provider is absent. |
| Claim/receipt/verdict separation | Capture, decisions, evaluation and accounting retain NO_ECONOMIC_CLAIM; no promotion path exists. Full qualified calibration/claim receipts remain absent. |
| Holdout/search-family accounting | SQLite frozen comparison trials, immutable burn records and idempotent decisions; full statistical evaluation remains missing. |
| Lifecycle | Atomic observation/decision lifecycle with terminal-state and time-order tests; broader campaign lifecycle integration remains incomplete. |
| Recovery and telemetry | Paper restart reconstructs native and revised accounting, validates policy/source boundaries and rejects divergence before new capture; structured step logs exist. Concurrent writers and durable crash boundaries remain unqualified. |

Runtime checks, Python typing and adversarial tests replace Rust-specific
implementation mechanisms, not the economic requirements. They are not claimed
equivalent to Rust compile-time enforcement. No claim promotion path may open
until its required constitutional receipts and independent checks exist.

## Delivery requirements still active

Complete the economic slice, genuine native execution adapter, prospective
paper path, restart/reconciliation, telemetry, methodology-preserving evaluator,
dependency/latency evidence and operator commands. A no-trade result is valid
when calibration is absent, but does not establish execution qualification.
Actual fills must be qualified independently without forcing production trades.
Live entry points remain disabled. No profitability or readiness claim follows
from this development milestone.

## Initial economic definitions

`economics/decisions.py` implements an observer-independent 48-prior-bar breakout
grammar for BTC/USD linear perpetual exposure. Identity binds the grammar,
instrument, exposure, direction and breakout candle end, never observer identity
or delayed observation clock. Each breakout candle is a discrete episode in this
initial grammar; competing grammar definitions would constitute research trials.

The observer is derived from `v8-core/src/experts/squeeze_swing.rs`: compressed
20-bar bandwidth, volume expansion and efficiency filtering. It retains default
0.35 bandwidth-rank, 1.30 volume-ratio and 0.18 efficiency thresholds as hypothesis
definitions, not computed confidence or proven edge. Complete 20-bar windows
over 50 bandwidth values require 69 closes. Undefined volume/bandwidth abstains;
legacy fallback values of one and partial warmup windows are not reproduced.
The opportunity lookback explicitly means 48 PRIOR candles rather than the
legacy slice's 47 prior candles. This is a versioned semantic choice, not parity.
The immediately simpler comparison is the same breakout grammar without the
compression observer. Neither is automatically eligible for execution.

Reconciliation deduplicates dependency groups and abstains/rejects contradictory
stances, without vote-based confidence. Utility arithmetic subtracts all provided
costs and uncertainty and rejects missing calibration. Portfolio/campaign authorization is implemented in the controller and qualified
with isolated native tests. Real calibration receipt verification remains
outstanding; the arithmetic function alone cannot authorize execution. No custom capital or expected-edge defaults
are embedded in runtime code.

## Measured development feedback (2026-09-08)

`tests/measure_feedback.py` creates a separate environment, installs the locked
wheel-based dependencies, runs imports and scoped verification, and records exact
commands, exit codes and installed versions. A fresh environment can use cached
downloads and must not be described as a cold-network installation.

Verified local artifact: `/tmp/v8-next-feedback-verified.json`. Observed wall
times in that run: cached fresh-environment setup 0.303 s; first native import
process 3.429 s; subsequent native import process 0.074 s; scoped economic tests
5.587 s; native integration tests 1.341 s; Ruff 0.486 s; mypy 2.172 s. All command
exit codes were zero. These are process wall times on this host, not engine
throughput or equivalent Rust/Python speedup estimates. Initial imports and OS
caches materially affect the measurements. The earlier measurement captured a
real mypy failure that was corrected before this successful run.

Paper CLI now logs structured completion/failure events with measured duration
and observed capture/order/position counts. Funding status is incomplete for
any session with position history until online settlement integration exists;
the zero-exposure status cannot be reused for a funded session.

## Final funding and revised accounting

Executable qualification found that 2.0.0rc4 rejects a final funding update whose
settlement boundary precedes its replay receipt timestamp (`Late funding boundary`).
Passing late REST history into the ordinary online event path is therefore invalid.
The product must not substitute an estimated rate or invent timely availability.

`adapters/settlements.py` retains settlement time and actual receipt time separately.
Its boundary-timed native events are exclusively for accounting replay at a cutoff
where the final record was already received. `adapters/accounting_replay.py` owns
that boundary: it creates only the fixed-campaign execution adapter and runs no
observers, calibration, allocator, or historical decision callbacks. Thus revised
simulated cash accounting cannot retroactively change a prospective decision.
The paper checkpoint records this view separately from its original native state.

The isolated native test proves that a late record replayed this way charges the
position held at settlement, including when the position has since closed, and
matches the timely settlement balance. This is test-only semantic qualification.
Real prospective runs have so far had no admitted positions, and their accounting
view makes no position-bearing funding claim. Coverage is explicitly limited to
observed final records, not a certified assertion that no settlement is missing.
Using revised accounting to admit subsequent real paper campaigns still requires
the calibration/authority boundary and complete funding coverage policy; those
requirements are not satisfied by the zero-position demonstration.


## Historical observer diagnostic and current acceptance evidence

`python -m v8_next.app.backtest` connects native bar callbacks to the same
opportunity and squeeze observer functions. It retains original unknown historical
availability in every output, alongside explicitly modeled close-time availability.
It never authorizes orders from uncalibrated observations. This is an observer
diagnostic, not a qualified economic backtest or a replacement for prospective
measurements. Current metadata and assumed fees remain visible limitations.

Actual captured input `/tmp/v8-next-capture-20260908-initial/manifest.json`
produced `/tmp/v8-next-historical-observer.json`: 499 decisions, 19 breakout
opportunities, four compression-breakout stances, zero orders. These are observed
counts from that file, not expected performance or independent statistical trials.
The CLI writes the JSON artifact separately from native engine logs.

The subsequent full local suite passed 33 tests in 0.89 seconds of pytest-reported
time (`/tmp/v8-next-tests-current.log`); this is not process wall time or a Rust
comparison. Ruff passed. The preceding implementation type check passed for
20 source files. The callback-prefix test is separate from the real native-run
check: neither alone establishes all execution or statistical requirements.

## Prospective continuation check

A fresh frozen-policy session at `/tmp/v8-next-prospective-current` completed:
first public Binance capture → native paper replay → separate-process
`--replay-only` restart → second public capture → evaluation. The restart
recomputed both the native state and the revised fixed-campaign accounting
before advancing. Evaluation retained two decisions for two captures (not three
for the intervening replay); native state retained two quote observations and
zero orders/positions. No calibration or opportunity was manufactured.

Physical evidence: `paper-state.json`, `policy.json`, `research.sqlite` and raw
capture manifests in that directory; process logs at
`/tmp/v8-next-prospective-current-first.log`,
`/tmp/v8-next-prospective-current-restart.log`, and
`/tmp/v8-next-prospective-current-second.log`; evaluation at
`/tmp/v8-next-prospective-current-evaluation.json`.
This establishes bounded no-position session continuation only. It does not
qualify position-bearing funding coverage, long-running recovery, profitability,
or real-money operation. Statistical outputs remain null and promotion blocked.

## Development delivery audit (not completion certification)

The full current test suite passed 45 tests in 1.01 s pytest-reported time;
log `/tmp/v8-next-full-current.log`. Recent type checking covers 21 source files.
Paper inputs now use one Pydantic contract before directory creation; the same
contract applies to direct replay calls. Local paper writers use an OS advisory
lock and checkpoint fsync/atomic replacement. Neither proves network-filesystem
or power-loss recovery of the entire artifact directory.

Current executable paths are capture, historical observer diagnostic, prospective
observe/paper, read-only evaluation and outcome-source inspection. Positive
observer-to-native-fill and late-funding behavior are qualified in isolated tests;
real prospective samples currently have no admitted trades. That absence must
not be repaired with invented utility inputs. The source inspector recomputes
campaign decisions before accounting and distinguishes open from closed outcomes.
It still does not implement an eligible calibrated forecast provider.

Remaining delivery work is specifically:

- Finish methodology-to-code/source mapping for the initial benchmark: null,
  loss alignment, dependence unit, chronological split and family scope. Existing
  null statistics are honest missing outputs, not implemented inference.
- Resolve the real-data economic execution acceptance boundary without forced
  trades or false calibration; preserve independently tested positive adapter
  behavior and explicitly qualify any chosen narrower operational scope.
- Establish the supported funding coverage/admission policy for subsequent
  position-bearing operation. Current code blocks readmission after position
  history because the online account is not reconciled by revised accounting.
- Consolidate final operator instructions, exact installed dependency versions,
  authoritative product navigation and durable evidence references. Temporary
  developer artifacts are not release receipts.
- Perform a requirement-by-requirement final audit after the above; current green
  tests and the development commit do not establish goal completion.

## Initial statistical methodology boundary

Source anchors:

- `TARGET_ORACLE_SPEC.md` §§13.1–13.4 separates historical replication,
  prospective shadow and live realization. Its header is NORMATIVE REFERENCE /
  IMPLEMENTATION-READY / ECONOMICALLY UNVALIDATED, not evidence of profitability.
- That specification §§14.1–14.3 requires chronological partitions, dependence
  awareness and registration of economically selected grammar, policy, cost and
  execution changes. Overlapping opportunities are not independent IID trades.
- `EXPERT_PROTOCOL.md` family/variant section retains within-family variant
  correction by White's block-bootstrap max statistic. Its older Expert-produced
  Candidate taxonomy must not override the current observer/opportunity boundary.
- `V85_ARCHITECTURE_SPEC.md` V85-P0-005 explicitly retains WRC + genuine DSR +
  Hansen SPA until ratified substitution. Its suggestion that other methods may
  eventually be appropriate is not authorization to drop those gates here.

For the initial observer comparison, the baseline is the identical 48-prior-bar
breakout opportunity grammar without the squeeze filter. Comparison must use
identical opportunity identities, causal decision timestamps, execution scope,
cost inputs and capital constraints. Snapshot counts currently emitted by
`app/evaluate.py` describe coverage only; neither support frequency nor a
no-trade account balance estimates utility improvement.

A future executable family test must define its economic loss before inspecting
protected outcomes. With a declared loss L, improvement is d[k,t] = L[baseline,t]
- L[variant_k,t], so positive differential favors the variant. The family null is
that no evaluated variant has positive expected differential. This equation is
an interface/sign convention, not an implemented WRC or a substitution for the
constitutional scorecard. Missing outcomes cannot be filled with zero. No-trade
cash returns can be zero only when an actual reconciled account interval supports
that value; absence of markout, funding or execution evidence remains missing.

Loss rows must be aligned on the same declared chronology across all variants.
Do not independently resample variant columns or overlapping opportunity trades.
The resampling block/cluster unit and length require a preregistered dependence
plan; the current capture sample establishes neither. No default block length,
alpha spend, sample-size threshold or confidence estimate is invented by this
slice. No inference library is installed merely to label missing work as complete.

Current persistence records the baseline and observer as two comparisons in the
local compression-breakout family. It does not prove the repository's full search
history contains only two trials. Future threshold, grammar, cost or execution
selection must remain in the relevant family/lineage; cloning an observer is not
a new independent observation. A holdout is lineage-relative and use burns its
protected role. The SQLite burn primitive exists, but no protected-OOS inference
command yet consumes data, so no OOS certification is claimed.

Current output contract: WRC/SPA/DSR/PBO, calibrated edge, uncertainty and economic
comparison stay null until their real eligible samples and actual methods exist.
Promotional gates remain closed. This preserves missingness; it is not completion
of the statistical implementation or evidence that the null was accepted.

## Installed-package acceptance

A distributable wheel was built at
`/tmp/v8-next-wheel-check/v8_next-0.1.0-py3-none-any.whl`, installed with the locked
runtime dependency export in `/tmp/v8-next-wheel-env`, and invoked from `/tmp`
using Python `-I` (isolated imports). This exposed and corrected a repository-only
`uv.lock` path assumption in policy initialization. Source mode binds the lock
and actual runtime dependency versions; wheel mode binds package Python sources
and actual runtime dependency versions. Neither authenticates native binaries.
Changing a dependency version prevents reuse of a frozen policy, covered by
`test_policy_identity.py`. Source-mode and wheel-mode hashes intentionally differ.

The installed wheel completed a real public-data paper step and separate-process
restart at `/tmp/v8-next-wheel-paper`; logs are
`/tmp/v8-next-wheel-paper.log` and `/tmp/v8-next-wheel-paper-restart.log`.
This validates installed-package execution on this macOS host without legacy
runtime imports/builds, not cross-platform or profitable trading qualification.

### Upstream multiple-comparison API finding

Official `arch` documentation/source was inspected at
https://arch.readthedocs.io/en/latest/multiple-comparison/generated/arch.bootstrap.SPA.html
and https://arch.readthedocs.io/en/latest/_modules/arch/bootstrap/multiple_comparison.html.
The exposed API consumes T baseline losses and a T-by-k alternative loss matrix,
with explicit bootstrap scheme, block size, replication count, studentization and
seed controls. It emits lower/consistent/upper p-values. The documented source
implements `RealityCheck` as a shallow subclass of `SPA`; the class name alone
therefore does not establish V8's historical WRC settings or method equivalence.

Next integration must pin an installable release and inspect that installed
source, choose explicit settings from the preregistered method, preserve joint
row resampling across the family, and label the exact returned p-value variant.
The latest-docs finding is API research, not installed-release qualification.
No p-value was calculated from the current missing economic outcome sample.

`evaluation/alignment.py` now enforces a complete shared half-open interval
chronology and strictly pre-decision outcome availability before calculating
paired loss differences. It rejects missing/nonfinite losses and cannot validate
source authority, holdout pristine status or an estimator by itself. Its isolated
fixture test checks sign, missing rows, reordering, future knowledge and boundaries.

### Installed SPA adapter

The installed `arch` 8.0.0 source was inspected, confirming the shallow
RealityCheck alias and lower/consistent/upper outputs. `evaluation/inference.py`
now delegates a specifically labeled stationary, studentized, non-nested SPA
calculation, with required caller-supplied block length, repetitions and seed.
It records the null sign convention, sample interval count and actual numerical
dependency versions. This is not a constitutional WRC substitution or an economic
receipt issuer. Exact duplicate alternative loss columns preserve returned
p-values in the qualification test; missing and degenerate inputs fail closed.
The optional research extra is locked. No real sample inference has been claimed;
connecting verified account outcomes and preregistered lineage remains unfinished.

### Updated feedback after optional inference integration

Fresh isolated dev environment measurements in
`/tmp/v8-next-feedback-final-scope.json`: cached setup 0.216 s, first native import
2.314 s, subsequent import 0.074 s, focused economic tests 4.165 s, native
integration tests 1.125 s, Ruff 0.484 s, mypy 2.130 s. All exited zero. The dev
measurement deliberately excludes the optional research dependencies.

Separately, `/tmp/v8-next-research-feedback.json` records cached research-extra
setup 0.118 s in the existing project environment, SPA qualification 1.546 s
process wall time, and the full research-enabled suite 2.072 s process wall time
(48 tests passed; pytest reported 1.83 s). These scopes/environments differ and
must not be presented as equivalent speed comparisons. No Rust speedup is inferred.

### Bounded prospective funding acquisition

Paper capture now requests funding history from the frozen session start through
an explicit request-time end, with limit 1000, retaining the exact query in the
hashed source manifest. It rejects a saturated response rather than silently
assuming the earliest 1000 records exhaust the window. Such sessions require a
bounded pagination extension; they cannot continue with truncated funding history.
Duplicate/out-of-order and out-of-window funding timestamps also reject capture.
Standalone historical capture retains its previous recent-history behavior.

Official Binance funding-history documentation specifies inclusive start/end
milliseconds, ascending results and truncation at the limit:
https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
(Get Funding Rate History). This supports bounded acquisition, not a guarantee
that the venue never publishes late records. A response window ends before its
receipt and before subsequent quote receipt; coverage must not be extended to
those later times. Funding coverage classification is not yet upgraded by this
change. No calibration or admission gate is relaxed.

Capture boundary tests exercise exact query parameters and saturated-response
failure without a valid manifest. Full local suite passed 56 tests in 2.42 s
pytest time (`/tmp/v8-next-bounded-funding-tests.log`); Ruff and mypy passed.

Revised accounting now exposes verified `funding_query_windows`: inclusive query
start/end, actual response receipt and source hash. It rechecks the persisted URL,
request clocks, response limit, instrument and timestamp ordering rather than
trusting a serialized completeness flag. Responses unavailable at the accounting
cutoff are excluded; old unbounded requests supply no explicit interval. Query
coverage is never extended to the later accounting cutoff. The output is labeled
`BOUNDED_RESPONSE_NOT_FINALITY_CERTIFICATE`; overall funding qualification and
readmission remain unchanged. Six focused capture/settlement tests passed in
0.54 s (`/tmp/v8-next-funding-windows.log`), and mypy passed for 24 source files.

Each revised native position now includes a query-coverage assessment against its
actual open/close timestamps and instrument. An open position requires a response
covering through the accounting cutoff; a closed position requires coverage through
its native close. The current session-prefix acquisition requires one bounded
response covering the whole position, and does not infer coverage across disjoint
windows. Future-received responses cannot establish past coverage. Source hashes
are retained. `BOUNDED_RESPONSE_COVERS_EXPOSURE` remains separate from cashflow
finality, which stays UNQUALIFIED. This supports identifying the exact data gap;
it does not authorize economic claims or readmission. Seven focused tests passed
in 0.49 s (`/tmp/v8-next-exposure-funding-tests.log`); mypy passed.

### Descriptive terminal cash return

The combined report now derives each simulated terminal cash return as
`(native terminal balance - initial balance) / initial balance`. Native commissions
and observed funding are already included and are never subtracted again. This
fixed-capital diagnostic rejects open orders, leaves open-position results missing
without a qualified equity mark, and requires bounded funding history covering
every closed exposure plus no unresolved announcement reconciliation. A no-position
account can report its actual cash change; it is not an edge observation.

This is a descriptive result under the observed venue history, explicitly subject
to later revisions, not cashflow finality, calibrated utility, constitutional
scorecard substitution or a paired statistical sample. All inference/claim gates
remain unchanged. The native close test produces the expected test-only return
including both commissions and funding once, and rejects missing coverage/open
positions. Eleven focused native/report tests passed in 1.54 s pytest time
(`/tmp/v8-next-cash-return-tests.log`); Ruff and mypy passed (25 source files).

### Protected outcome read boundary

The read-only evaluator now checks registered HOLDOUT trials before reading any
decision payload. Each requires an existing consumption record for its own family
and dataset, with a timestamp no earlier than registration and no later than the
current read. A burn in another family does not grant access. The check and outcome
reads share one SQLite transaction snapshot. The evaluator does not silently burn
a holdout, and an existing burn does not certify first-use OOS validity or permit
claims. This is an access boundary on the local registry, not complete protected
inference orchestration. Tests prove rejection occurs before even a deliberately
corrupted outcome is decoded, and access after a matching record still preserves
claim gates. Ten focused tests passed in 0.12 s (`/tmp/v8-next-holdout-access.log`);
Ruff and mypy passed.

### Capture-prefix economic trajectory

`report --trajectory` connects verified source sessions to a paired baseline/squeeze
cash trajectory. For each chronological capture prefix it reruns economic decisions
and fixed-campaign native accounting using the same cutoff for both policies.
Incremental change uses adjacent cumulative values only; either missing endpoint
makes the increment missing. No later capture or funding receipt enters an earlier
row. The series remains a descriptive irregular-interval cash diagnostic, not a
qualified loss sample or an estimator. Full-prefix replay is deliberately optional
because total work grows quadratically with capture count; no scheduler/cache
framework was added.

The source-prefix/missingness test and report test passed (2 tests, 0.36 s pytest;
`/tmp/v8-next-trajectory-tests.log`). Actual two-capture public data produced
`/tmp/v8-next-real-trajectory.json` via the production report command: both policies
had zero observed cash change in both intervals and inference eligibility remained
false. Native process log: `/tmp/v8-next-trajectory-real.log`. Ruff and mypy passed
for the implementation (26 source files).

### Exploratory source-to-SPA integration

The optional report flag `--exploratory-spa BLOCK REPS SEED` now connects the
source-verified, prefix-recomputed paired cash series to the genuine arch SPA
adapter. It declares negative incremental cash return as the diagnostic loss,
checks chronology through `paired_differentials`, propagates missing intervals,
and refuses a p-value for a constant paired difference. Caller parameters are
explicit but not asserted to be preregistered. This exploratory operation does
not change `inference_eligible` on the source trajectory or provide calibrated
utility/claim authority; it is not the missing protected-inference certification.

Three focused inference/report tests passed in 1.50 s pytest time
(`/tmp/v8-next-exploratory-spa-tests.log`); Ruff and mypy passed. Actual two-capture
input produced `/tmp/v8-next-exploratory-real.json` with
`DEGENERATE_DIFFERENTIAL_NO_PVALUE`, null result and NO_ECONOMIC_CLAIM. No fixture
p-value entered the production artifact. The positive calculation test remains
isolated test data and asserts exact scope rather than an invented expected p-value.
