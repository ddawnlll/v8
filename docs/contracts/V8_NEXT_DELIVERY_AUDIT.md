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
| Lifecycle/rejections/abstention/expiry | Transactional decisions/lifecycle; deadline sweep; restart/idempotence tests | Observation lifecycle implemented; submitted campaign lifecycle not yet written to research store |
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
