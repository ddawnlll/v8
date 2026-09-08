# V8-next first-slice acceptance — 2026-09-08

This audit evaluates the owner's implementation objective, not a release or
profitability claim. Code evaluated: b9a7e007. The objective explicitly permits
NO_TRADE when actual data/calibration is insufficient and missing statistical
outputs where the required method/evidence is absent. Acceptance does not assert
that a calibrated predictor, certified OOS test or live financial system exists.

## Requirement-to-evidence check

| Owner requirement | Inspected implementation and executable evidence | Result and limit |
|---|---|---|
| Independent Python product; preserve legacy/user work | pyproject.toml, uv.lock, source import search, git status; isolated wheel below | No legacy runtime/import/build dependency; unrelated Rust work remains untouched |
| Thin production-library composition | native_tape, campaign, economic_paper, decisions, inference, store | Nautilus owns engine/OMS/accounts; Polars features, arch SPA, SQLite storage; no engine fork or custom scheduler |
| Explicit authority and constitution mapping | local AGENTS.md; V8_NEXT_IMPLEMENTATION_SCOPE.md; governance reset and referenced source contracts | New-directory authorization; claims stay gated; no constitutional amendment |
| Wheel and exact environment | Final clean environment installation, versions.json and locked requirements.txt below | Python 3.12/macOS ARM64 demonstrated; rc4 prerelease disclosed |
| Actual Binance USD-M data and metadata | Final wheel capture's original JSONs, URLs, request/receipt clocks, hashes and manifest | Public REST only, BTC linear perpetual; historical availability remains unknown |
| PIT and temporal non-interference | domain/market, captured_market, observe; causality and historical-prefix tests | Receipt-based prospective knowledge; modeled historical close clocks visibly diagnostic |
| Economic identities and observer-only authority | Opportunity/Stance/PaperCampaign; controller; identity/clone tests | Instrument/exposure/opportunity/campaign separation; stances cannot place orders |
| Deterministic repo-derived observer and baseline | squeeze semantics source mapping; observe_breakout_baseline; native observer parametrization | Squeeze warmup 69 bars, baseline grammar 49; same downstream admission |
| Lifecycle, abstention, rejection, invalidation, expiry | SQLite decisions/lifecycle, terminality and expiry tests; native campaign snapshots | Records retained; terminal opportunities cannot reopen; engine order state remains separate |
| Reconciliation, after-cost admission and exposure risk | controller, utility_admission, risk/admission; controller/admission/economics tests | Missing verification rejects; capacity/rounding/reservations enforced; no fabricated utility |
| Authorized campaign → native order/fill/position | Native positive observer/controller test; entry/expiry-close tests | Positive path qualified with isolated test calibration; production has no calibrated provider and submits no orders |
| Fees and funding | Native commission, duplicate/late funding tests; revised fixed-campaign replay; cash-return test | Costs charged once; late final records cannot change old decisions; simulation is not venue cash settlement |
| Margin/position scope | native_tape configuration and native tests | Generic 1x NETTING/MARGIN; venue liquidation/brackets not qualified, not advertised |
| Paper/shadow executable path | app.paper capture and restart processes below | Real public input/local simulation; sparse snapshots, no continuous-feed claim |
| Recovery and duplicate prevention | Checkpoint native/revised comparisons; process replay, divergence-before-capture and writer-lock tests | Bounded local replay verified; no live venue recovery claim |
| Telemetry | Actual paper success logs; failure path and measured process durations | Structured local process logging; no unused telemetry services added |
| Accounting/evaluation outputs | evaluate, report, calibration inspector, cash_return, trajectory; actual JSON report below | Native decisions persist; source/accounting recomputed; missing/open-exposure values remain absent |
| Statistical methodology | Source mapping, loss alignment and inference modules/tests | Explicit loss/null/block/reps/seed and joint SPA; exploratory scope, no WRC substitution; DSR/PBO absent |
| Family/holdout/chronology | Immutable trial registry/burn records; evaluator access preflight; loss-boundary tests | Local lineage preserved; no assertion of complete historical search family or pristine certified OOS |
| Anti-fabrication/claim separation | Runtime NO_ECONOMIC_CLAIM outputs, simulation checks, absent results and promotion guards | No synthetic production input, false p-value or claim promotion; fixtures stay in tests |
| Real-money boundary | Source inspection and actual commands | No private client, order submission to venue, transfer or account mutation; no live activation |
| Documentation, commands and feedback measurements | README, full scope, evidence below | Delivered; measurements identify host/cache/test scope and make no Rust speedup claim |

## Current physical evidence

Final installed-wheel directory:
`/var/folders/db/04433_v94tv8xpr31czl2j200000gn/T/v8-next-final-wheel-j2anb76t/`.

- `dist/v8_next-0.1.0-py3-none-any.whl`, `requirements.txt`, `versions.json`,
  `source-commit.txt`, `setup.log` and isolated `env/`.
- `paper/` contains actual captures, frozen policy, SQLite and native/revised
  checkpoint. `capture.log` and `restart.log` record separate Python processes.
- `report.json` and `report.log` were produced from the installed wheel using
  `python -I`, working directory `/tmp`, including `--exploratory-spa 1 99 7`.
  One decision remained after restart. Actual no-position cash change was zero;
  SPA returned DEGENERATE_DIFFERENTIAL_NO_PVALUE with null result. No p-value was
  inferred from the test fixture or from the absence of trades.

Current full suite: **61 passed in 2.23 s** pytest time,
`/tmp/v8-next-current-delivery-tests.log`. Ruff passed; mypy passed for 26 source
files. Scoped development measurements remain physically available at
`/tmp/v8-next-feedback-final-scope.json` and
`/tmp/v8-next-research-feedback.json`; these are earlier scoped measurements,
not represented as timing of the current 61-test suite. Setup/import/economic/
native-test scopes and exact commands are recorded there.

Historical real-input diagnostic remains at
`/tmp/v8-next-historical-observer.json`: 499 bars with explicitly unknown measured
historical availability and separately modeled callback clocks. The two-capture
paired prefix diagnostic is `/tmp/v8-next-real-trajectory.json`; its exploratory
missing-result output is `/tmp/v8-next-exploratory-real.json`. These temporary
artifacts are inspected development evidence, not permanent release receipts.

## Accepted scope and continuing limits

The requested first working economic research/prospective paper slice is present:
real data → causal observations/opportunities → reconciliation and rejection-safe
utility/risk → native campaign connection → accounting → bounded evaluation and
prospective/restart commands. Production correctly remains NO_TRADE without
qualified calibration; independent native positive tests establish the adapter's
execution behavior rather than inventing an economic signal to force an order.

Not delivered or claimed: a calibrated economic forecast provider, certified
protected-OOS/multiplicity release evidence, complete venue funding finality,
position-bearing readmission after unresolved online funding, continuous live
feed recovery, exact venue liquidation or real-money readiness. Their absence is
explicit in code and output. The objective's no-calibration/no-claim allowance is
not evidence that these future capabilities are implemented.

This conclusion supersedes the earlier delivery audit's interpretation that full
production calibration and certified statistical operation were necessarily required
to finish this first slice. It does not supersede those requirements for any later
qualified economic claim or financial operation. No feature-parity or profitability
requirement has been added, and no safety/claim gate has been removed to obtain
acceptance. Future work should target those economic prerequisites rather than
repeatedly extending infrastructure or treating zero-trade replay as new evidence
of edge.
