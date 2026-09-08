# V8-next delivery audit

Development audit against the owner implementation objective; not an economic
certificate. Evidence reviewed at development commit cc026bd7 and its ancestors.
The source objective explicitly permits NO_TRADE for missing data/calibration
and missing DSR/PBO/sequential results where a real method does not exist. Neither
permission excuses incorrect implemented behavior or fabricated qualification.

| Objective requirement | Evidence | Assessment |
|---|---|---|
| New independent Python product | Installed wheel invoked using `python -I` outside repo; no old runtime import/build | Demonstrated on local macOS ARM64 |
| Preserve user/legacy work | Commits touch v8-next and new scope documentation only; preexisting Rust changes remain outside commits | Preserved in reviewed commit history |
| Real Binance USD-M input and metadata | Raw capture manifests, SHA verification and complete-capture validation; installed-wheel paper run | Demonstrated, public REST snapshots |
| Clock distinction/PIT | Immutable Candle/CausalFrame, unknown historical availability, prospective receipt conversion, prefix tests | Implemented for current response versions; historical replay explicitly modeled |
| Economic identity and observer boundary | Opportunity hash independent of observer, frozen Stance; separate controller and campaign adapter | Implemented for BTC linear exposure grammar |
| Clone invariance | Feed dedup/conflict test; stance group reconciliation; campaign opportunity dedup; SPA duplicate-column test | Covered within narrow single-instrument scope |
| Lifecycle/rejections/abstention/expiry | Transactional decisions/lifecycle; deadline sweep; restart/idempotence tests | Observation lifecycle implemented; native entry events and order snapshots now persist and survive SQLite reopen/evaluation; exit association remains incomplete |
| After-cost utility and exposure limits | Utility and risk/controller tests; real app supplies no calibrated edge | Missing calibration fails closed; positive path qualified only in isolated tests |
| Native orders/fills/positions | Test observer → controller → native fill; fee, expiry close and deterministic subprocess state tests | Native positive semantics demonstrated with test fixtures, no real-input admitted fill |
| Fees/funding and account outputs | Native commission and duplicate/late funding tests; fixed-campaign revised accounting | Accounting replay implemented; complete funding coverage is unqualified and subsequent exposure admission blocked |
| Recovery/duplicate prevention | Real no-position restart; synthetic position replay across processes; checkpoint comparisons and OS writer lock | Bounded local replay demonstrated; online venue recovery not claimed |
| Evaluation and claims | Combined report verifies decisions and accounting; NO_ECONOMIC_CLAIM and explicit null results | Working diagnostic output; complete calibrated economic comparison absent |
| Benchmark/null/family/OOS discipline | Source-linked scope; local trials/burns; loss alignment; optional genuine arch SPA | Numerical kernel and primitives exist; verified paired account-loss ingestion and protected-evaluation orchestration absent |
| Telemetry | Structured paper success/failure logs with wall times and counts | Implemented for manual step process |
| Exact dependencies and iteration measurements | uv.lock, installed version listing, scoped timing JSONs, 48-test research suite | Demonstrated on current host; optional research costs reported separately |
| No real-money action | Public REST capture only; no private execution client or live command configured | Preserved |
| Full-text spec and commands | V8_NEXT_IMPLEMENTATION_SCOPE.md, v8-next README and AGENTS, local commits | Delivered development documents |

## Work still required for full objective closure

The current system is a working prospective observation/no-trade paper slice,
not a completed position-bearing economic system. Do not mark the broad goal
complete based solely on its no-trade allowance. The concrete integration gaps
are (1) campaign lifecycle persistence, (2) verified paired economic outcome
input to evaluation/calibration, and (3) a supported funding-completeness policy
for position-bearing continuation. Inference calculations on isolated fixture
losses do not close (2), and full financial readiness is not inferred from tests.

Continue with those integrations rather than adding additional wrappers or
repeating no-position capture demonstrations. Any unavailable empirical quantity
must remain absent, and no production calibration may be fabricated to force
entry. A genuine external blocker must be identified specifically; missing
implementation alone is not an external blocker.

## Campaign persistence checkpoint

The shared `PaperCampaignAdapter.campaign_observations` projection now carries
native entry callbacks and the native entry-order snapshot into paper checkpoint
state and the transactional SQLite campaign observation history. Replaying the
same observation is idempotent; conflicting contents at the same observation time
are rejected. Evaluation checks the stored payload hash and retains SIMULATED
classification. A submission flag is not converted into a fill.

`test_native_order_callbacks_survive_store_restart_and_evaluation` executes a
native test-only fill, uses that production projection, writes SQLite, closes and
reopens the store, repeats the observation, and reads the unchanged fill through
the production evaluator. The focused native/store/evaluator suite passed 16 tests
in 1.41 s pytest time; `/tmp/v8-next-campaign-persistence-tests.log`. Ruff and mypy
passed (24 source files). These are fixture-based integration checks, not real
market economic evidence or process-crash durability qualification.

This closes the entry-event persistence gap only. Generated closing-order IDs are
not yet bound to campaign history; position settlement and funding completeness
must not be inferred from these entry snapshots. The paired-outcome and funding
continuation gaps above remain open.

### Native exit association

Closing orders now carry a native order tag binding the originating campaign.
The adapter reads the engine-generated client IDs from tagged cached orders and
projects both exit callbacks and exit-order state into the same persisted
observation. It does not infer ownership from fill timestamps or instrument alone,
and does not implement a second order state machine. The installed rc4 public
`close_all_positions(..., tags=...)` API was exercised by the native test.

The persistence/evaluation test now covers both an open position and an expired
campaign with a native close fill. Eight native tests passed in 1.45 s
(`/tmp/v8-next-exit-tests.log`). Entry and exit evidence survive store reopening
without duplicate observations; this supersedes the missing closing-ID association
noted above. Complete funding coverage, production calibration and paired economic
outcome ingestion remain separate unfinished requirements.

### Funding cutoff correction

Revised accounting previously bounded settlement selection and missing-announcement
checks by the last quote receipt. This omitted a funding boundary after that quote
but before the declared accounting cutoff while a position remained open. Both
ranges now extend through the accounting cutoff. Final-record availability is
still independently enforced; no decision callbacks run on revised funding events.

`test_revised_accounting_settles_after_last_quote_before_cutoff` runs the real
capture decoding and native accounting with test-only instrument/data fixtures.
Before final receipt, the announced settlement remains missing and the balance
includes only entry commission; after receipt, native funding debits the position.
Four focused tests passed in 0.50 s (`/tmp/v8-next-funding-cutoff-tests.log`). This
corrects omitted known cashflows; it does not certify global funding completeness
or authorize readmission/calibration. Open-position mark-to-market freshness is
also distinct from the revised cash balance.

### Executable baseline comparison

The frozen range-breakout baseline now runs through the same economic controller,
portfolio admission and native campaign adapter as the squeeze observer, omitting
only the compression filter. Its stance retains no execution authority. The
native test parametrizes both observers; the baseline uses 49 grammar bars and
therefore does not inherit the squeeze observer's 69-bar warmup requirement.

The combined report recomputes baseline native state using the source-verified
capture set and the same simulation configuration, beside the recorded and
recomputed variant state. Missing calibration remains missing in both paths.
It does not turn matching no-trade balances into a paired loss sample or p-value;
qualified account intervals, funding coverage and inference integration remain open.

Actual public-data execution produced
`/var/folders/db/04433_v94tv8xpr31czl2j200000gn/T/v8-next-baseline-gtocueq3/comparison.json`.
Both paths recorded zero orders and NO_ECONOMIC_CLAIM. This is the first native
baseline report check, not evidence of economic equivalence. Process log:
`/tmp/v8-next-baseline-report.log`. Full suite: 53 passed in 1.99 s pytest time
(`/tmp/v8-next-baseline-full.log`); Ruff and mypy passed.
