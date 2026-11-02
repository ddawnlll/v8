# V9 Backlog — preserved requirements from the V8 issue queue

**Status:** `PROVISIONAL_DECISION` (backlog only; grants no authority, no economic claim)
**Created:** 2026-11-03
**Analysis base:** triage ran against `origin/main` at `033cab6f`. The V8 integration that
landed before this file was merged into main: PRs #506, #505, #504, #503, #502 and #501
(see the V8 close report for the final SHA).
**Working tree:** `integration/v9-minimal-baseline` (this file is uncommitted; the coordinator lands it)

## 1. Preamble

### 1.1 Purpose

This file preserves every still-valuable requirement from the 29 open GitHub issues of
`ddawnlll/v8` that is **not being fixed now**, so the queue can be closed without losing a
unique requirement, acceptance criterion, or evidence obligation. Each entry names its source
issue, why it is not in the V9 start slice, the concrete blocker, and the acceptance criteria
that would close it.

Nothing here is an economic or release claim. Every verdict remains `NO_ECONOMIC_CLAIM`
(Constitution Rule 12). No requirement below authorizes synthetic data, sealed-OOS access,
live-money activation, or a substitute artifact.

### 1.2 What V9 is (sources: V9 monograph + ROADMAP)

The owner-supplied V9 architecture monograph is preserved in this repository at
[`docs/v9/V9_ARCHITECTURE_MONOGRAPH.md`](v9/V9_ARCHITECTURE_MONOGRAPH.md)
(`V9-ARCH-RFC-1.1-REVISED`, status `REVISED ARCHITECTURE TARGET / OWNER
APPROVAL PENDING / UNVALIDATED POLICIES`). It is a target architecture and a
set of candidate executable contracts, not an implementation or an economic
claim.

`docs/ROADMAP.md` (Version semantics, lines 13-20) states the governance
consequence:

> A `V9` would require a break in that ontology: a learned proposal architecture as the
> baseline, a different Candidate ontology, the system ceasing to be Candidate-constrained, a
> router or scorer becoming part of the policy, or a different epistemic architecture.

So V9 is an **ontology break**, not a Rust/GPU port and not a feature release.
The monograph keeps the V8 value core (PIT market state, expert-observer,
canonical OpportunityBook, risk/utility separation, native NautilusTrader
execution, evidence lineage) and adds a continuous trader decision cycle on
top. The first executable slice is P0-C `DecisionPolicyV0` baseline
equivalence, after P0-A inventory and P0-B audit/venue safety repair.

### 1.3 V9 start slice vs. deferred backlog

The issues deferred here are **not** required to *start* the ontology break. The requirements
that are required to start it are listed in **§3 (V9 foundation requirements F1-F7)** and are
carried either by a merged PR, by a FIX_NOW defect, or by an explicitly BLOCKED entry. A
deferred item is valuable but can be built/measured after the V9 baseline exists; several
depend on the new Candidate ontology itself.

### 1.4 Status vocabulary

| Status | Meaning |
|---|---|
| `DEFERRED_TO_V9` | Requirement is sound and buildable, but not start-blocking; preserved here. |
| `BLOCKED` | The requirement is sound but needs external evidence that does not exist in this checkout. The exact missing evidence is named in §4; no surrogate is authorized. |
| `DEPENDENCY` | Cannot start until another deferred item exists (named per entry). |

### 1.5 Evidence rule used for this triage

Every "already fixed" claim in the companion disposition table was verified on a fetched tree
(`origin/main` or the cited PR head) with `git grep`/`git show`, not from an author's prose.
No full test suite was run for this triage. A fix that exists only on an **open** PR is labelled
as such and must not be closed before that PR merges.

## 2. Deferred items

| ID | Source | Title | Why deferred | Blocker | Acceptance criteria (short) |
|---|---|---|---|---|---|
| B01 | #377 | Protected one-shot OOS and complete search-family evidence | V9's ontology break replaces the family/search surface; V8's protected window is already burned. | `BLOCKED` — unburned holdout + complete external search history (`EXT-OOS`). | Immutable pre-window OOS plan; atomic burn incl. failures; second-access/relabel rejection; full family comparison with roles+hashes; `NO_ECONOMIC_CLAIM` retained. |
| B02 | #378 | MinTRL estimator | Diagnostic estimator, not start-blocking; can be built on V9 return intervals later. | None (buildable); depends on real aligned intervals only for reporting. | Reproducible required horizon from declared target/null/confidence/power/dependence; `UNDERPOWERED`/`UNSUPPORTED` on missing assumptions; reference-value and determinism tests. |
| B03 | #379 | Venue fills, latency, shortfall, account reconciliation | Needs live venue evidence that V9 does not yet have; execution stays `SIM_ONLY`. | `BLOCKED` — venue order/fill/account exports with source+receipt clocks (`EXT-VENUE`). | Ordered decision/submission/acceptance/fill/rejection/account clocks; model-vs-real fill, latency drag, adverse selection, missed-fill opportunity cost; cash/position/funding/commission/P&L reconciliation without double counting. |
| B04 | #380 | Funding finality and coverage | Public funding capture exists, but venue settlement finality and all-leg reconciliation are unproven. | `BLOCKED` (finality half) — venue funding/settlement statements (`EXT-FUNDING`). | Every funding row bound to event time, receipt time, source mark, position interval, instrument; settled payment applied exactly once with sign/boundary semantics; distinguish no-exposure / unavailable / incomplete / verified zero; reconcile across strategy, benchmark, portfolio, venue account. |
| B05 | #381 | Joint P+E portfolio execution and shared capital | Large, strategy-coupled; the V9 baseline may change what P and P+E mean. | Dependency: V9 baseline policy shape. | One joint account under declared capital/allocation/concurrency/margin/heat/fee rules; opposing-order netting and rejected/unfilled accounting; incremental return/risk/turnover/drawdown/cost from the same joint account; equal-budget P vs P+E reruns. |
| B06 | #382 | Capacity and market impact from L2 data | No L2/tick/venue-fill dataset in this environment; linear OHLCV extrapolation is already refused. | `BLOCKED` — sequenced trade/quote/L2 + venue fills for all evaluated instruments (`EXT-L2`). | Scale-specific fill probability, impact, spread, participation, capacity floor, uncertainty; price-time ordering, venue constraints, participation/impact calibration, scale monotonicity; `DATA_BLOCKED` and no invented coefficient when data absent. |
| B07 | #383 | Two-ledger external parity into the evaluator | Needs a second physically produced ledger; valuable but not start-blocking. | Dependency: an independent reference ledger under the V9 contract. | Benchmark manifest requires native+reference ledgers; versioned semantic mapping; bit-pattern comparison; unpaired/missing semantics explicit, never zero; parity receipt bound to policy/case/mapping/engine/artifact hashes/method version; parity non-sovereign. |
| B08 | #384 | Complete candidate lifecycle bound to economic evaluation | The Candidate ontology is exactly what V9 breaks; binding V8's lifecycle now would bind a superseded ontology. | Dependency: V9 Candidate/opportunity ontology. | One immutable identity per candidate episode/transition; trigger, rejection, invalidation, expiry, cancel, partial fill, fill reasons in evaluator input; reconcile candidate→campaign→order→fill→position→cashflow including terminal non-fills; reasoned coverage counts before metrics. |
| B09 | #385 | Real operating net and venue-cost calibration | Needs actual fee-tier/fill-vs-mid/OPEX receipts; V8 has assumptions only. | `BLOCKED` — venue fee/tier receipts, fill observations, OPEX source artifacts (`EXT-COST`). | Separate transaction P&L, funding/carry, explicit fees, strategy net, operating net; calibrate fee/slippage from physical receipts without double-counting spread; bind OPEX period/currency/allocation/source; fail closed on any unmeasurable component. |
| B10 | #392 | Resolve UNKNOWN and MISSING gate states with explicit evidence | Gate taxonomy is sound but broad; partially present, not a one-line defect. | None; overlaps B18 wiring and the V9 receipt contract. | Canonical gate state taxon (`BLOCKED`/`NOT_APPLICABLE`/`UNRUN`/`MISSING`/`FAIL` distinguished); `UNKNOWN` only for unresolved evidence/method; every non-PASS gate exposes its next required artifact/check; aggregate stays fail-closed. |
| B11 | #393 | Close the economic evidence gate without weakening `NO_ECONOMIC_CLAIM` | This is the umbrella program over B01/B03/B04/B07/B09 and cannot precede them. | `BLOCKED` — union of `EXT-OOS`, `EXT-VENUE`, `EXT-FUNDING`, `EXT-COST`. | Preregistered gate→evidence matrix; eligible real outcome samples before interpretation; WRC/DSR/SPA on provenance-bound data; protected-OOS/funding/parity/prospective evidence tracked without double use; claim firewall closed until a valid authority receipt exists. |
| B12 | #451 | Port chain 2/7: attribution language (veto + analysis + telemetry) | Code is IMPLEMENTED and green; only the consumer edge into the P2/benchmark path is missing, tracked by B18/#476. | `DEPENDENCY` — B18 consumer edges. | Refused campaigns/decisions recorded with canonical reason beside lost-what-and-why; reconciliation phases charge each losing trade to exactly one domain with conservation; belief/span/identity trail hash-bound and consumable by `explain`; `regret_o4` absent. |
| B13 | #452 | Port chain 3/7: Hindsight/Target oracle substrate | Code is IMPLEMENTED (9 modules, 32 tests); zero importers outside its package/tests, tracked by B18/#476. | `DEPENDENCY` — B18 consumer edges. | O1 causal non-overlapping swings; O0 evaluator-only; versioned `UtilityContract` with NetUtility primary and lexicographic hard constraints; opportunity-universe vs proposals coverage; support validation; recoverability monotonicity/utility ordering; future information provably evaluator-only. |
| B14 | #453 | Port chain 4/7: proving ground (world foundry + full-chain runner + battery) | Code is IMPLEMENTED; `proving_battery` is only a CLI passthrough string, tracked by B18/#476. | `DEPENDENCY` — B18 consumer edges; synthetic worlds stay `SYNTHETIC:*`. | Seed-pinned world specs+receipts; full-chain runner over `BacktestEngine` with double-entry ledger and `SystemProvingGroundReceipt`; adversarial mutation/PIT battery with named failures; slippage lane uses a pinned probabilistic fill model behind the modelled column. |
| B15 | #454 | Port chain 5/7: benchmark pipeline (orchestration + D-153 delta + report) | Code is IMPLEMENTED and partially wired (PR #504 added projection/Minerva); remaining D-153 delta consumers open, tracked by B18/#476. | `DEPENDENCY` — B18 consumer edges. | One `run` orchestration sweeping pillars→receipts→HTML+tearsheet; D-153 delta (scoring/parity/external/certificate/ledger, observation/population/projection/minerva) consumed; every return row carries cost columns+SNU count; synthetic inputs stay `SYNTHETIC_*`; ledger verify + regression in the sweep. |
| B16 | #455 | Port chain 6/7: scoring closure | Partially delivered; labelled `state:blocked` on foreign reds (doc-path refs, mypy) and not start-blocking. | `BLOCKED`-ish: foreign guard/doc-path failures must be owned elsewhere; then V9 score contract. | Published score is a function of receipt-bound evidence; synthetic labels end-to-end and rejected from evaluative aggregates; research-delta verified against `ResearchStore`; disjoint temporal id types; gates incl. leakage audit and doc-path guard green. |
| B17 | #456 | Port chain 7/7: expert lifecycle (delta + D-141 + kaizen/assurance/governance) | Not started; terminal chain item measured against B16, and the V9 expert baseline will change. | `DEPENDENCY` — B16. | EEO + file-by-file expert-delta mapping before code; expert delta ported with no per-expert perf regression; qualification falsification surface with no economic verdict type; kaizen feed cannot open orders/live paths; assurance/EEO/governance in priority order. |
| B18 | #476 | 451-454 outputs IMPLEMENTED but unwired to the benchmark path | Partial: PR #504 delivered R2/R3/R4, but R1 (named consumer edges for oracle/attribution/proving-ground/D-153 delta modules) is open. | None missing externally; needs the consumer edges + E2E proof. | Each of the four outputs gains a named consumer edge into `BenchmarkRunner→BenchmarkReceipt→PolicyCertificate→forensic HTML/readiness/regression`, or the closed issue is reopened with the wiring R in Remaining; `PolicyCertificate.generate` receives produced projection/Minerva/MinTRL or a named refusal; `tools/audit_wiring.py` blocking with no allowlist; API issues cannot bypass the wiring manifest. |
| B19 | #491 | Equity path drops closed campaign exit P&L | Partial: PR #503 marks the exit leg (R1/R3/R4) but the residual equality (R2) fails on real data and is published as a named non-reconciling state. | `BLOCKED` for R2 — canonical 12-month `quad-1h-12m` tape absent; only single-leg BTCUSDT exists (`EXT-TAPE`). | Exit price from `closed_positions[].avg_px_close` enters `equity_mtm`; residual no longer contains a dropped trade; unexplained residual publishes a named non-reconciling state, never a cost graft; no imputed value (`bar_close_proxy_exits` named); terminal identity `Σ(equity[i]−equity[i−1]) = balance_total − capital` exact. |
| B20 | #478 | Ledger keeps a superseded cost verdict | Supersession is a ledger-evidence obligation that V9 inherits; not start-blocking. | None external; needs a machine-readable `superseded_by`/governing declaration (no byte edit, D-164). | One governing entry per `(case_id, policy_id, tape_sha256, window, bars)`; contradicted `seq 21` cells named superseded with replacing entry hash; test fails on today's tree; ledger hash chain unchanged. |
| B21 | #494 | DSR subject chosen by alphabetical sort | The alphabetical pick is already replaced by max-excess selection, but the pinned plan still does not declare its subject; identity churn needs a versioned decision. | None external; changes every `plan_id`/receipt identity, so it needs an explicit authority decision. | `StatisticsPlan` carries the DSR subject inside `identity()` (or `run_statistics` requires an explicit champion); absent subject fails closed as `MISSING_DSR_SUBJECT`; permutation and sorting invariance; direct-DSR equality; no `sorted()[0]` fallback. |
| B22 | #500 | Canonical P+E verdict ignores its own mix | Changes canonical portfolio verdict semantics and needs a comparison-basis decision; not start-blocking. | None external; needs measured `p_vol`/`pe_vol`/`comparison_basis` from the run's own equity series. | `build_verdicts` receives the published `portfolio_mix` object; basis measured or `INCONCLUSIVE`; `UNNORMALIZED_NOT_RISK_MATCHED` labelled; stripped-mix regression; `claim_status` stays `NO_ECONOMIC_CLAIM`. |

## 3. V9 foundation requirements (must hold before/while the ontology break lands)

These seven requirements are the honest-evidence floor V9 inherits. They are not optional
"V8 polish"; each has a start-slice carrier (merged fix, FIX_NOW defect, or a named blocked
obligation) so that V9 does not begin on a receipt it cannot defend.

### F1 — Ledger integrity and evidence-chain truth

- **Requirement:** Every stored ledger entry verifies from the first entry onward; a broken or
  stale chain is quarantined and can never be summarized as valid evidence; supersession of a
  contradicted cell is declared, never achieved by editing bytes; a gate cell's field name
  states the measurement it actually takes.
- **Carriers:** #389 (PR #501 quarantine + non-zero exit; merge pending), #478 (FIX_NOW:
  declare `seq 21` superseded), #495 (merged: G3 cell renamed `g3_scenario_robustness` with
  typed basis).
- **Acceptance:** `cli status` on a broken chain exits non-zero and prints `EVIDENCE CHAIN:
  QUARANTINED`; ledger hash chain and receipt sha256 unchanged by the fix; no consumer can
  read a superseded cell as current; the G3 state and its scenario basis travel together.

### F2 — Opportunity / campaign / order / fill identity

- **Requirement:** One immutable identity per candidate episode and every lifecycle
  transition (trigger, reject, invalidate, expire, cancel, partial fill, fill, position,
  cashflow), reconciled across populations with terminal non-fills retained. Attribution and
  telemetry trails attach to the decision, not to a side CLI.
- **Carriers:** #384 (deferred to the V9 Candidate ontology, B08), #451 (B12), #476 (B18).
- **Acceptance:** candidate→campaign→order→fill→position→cashflow joins reconcile with
  explicit reasoned coverage counts; a filled-only view cannot hide non-traded candidates;
  refused campaigns carry canonical reasons; every wired module has a consumer outside its own
  package/tests.

### F3 — Equity reconciliation

- **Requirement:** The published equity path is the measured path. A closed campaign's exit
  leg is marked at its engine exit price; a residual not explainable by fees+funding publishes
  a named non-reconciling state instead of being smeared as cost. Capacity bounds at scales the
  run never observed carry a contract status, never `MEASURED_*`.
- **Carriers:** #491 (B19, partial PR #503), #477 (merged fix: every capacity entry carries
  `DATA_BLOCKED | UNRESOLVED | NO_ECONOMIC_CLAIM`).
- **Acceptance:** `Σ(equity[i]−equity[i−1]) = balance_total − capital` exact; `cost_basis`
  states the truth (`VERIFIED_ENGINE_FUNDING`/`MISMATCH`/`UNKNOWN`); `bar_close_proxy_exits`
  named, never zero-filled; every `capacity_scenarios[*]` entry has a status.

### F4 — Funding finality

- **Requirement:** Funding is applied once per settled payment with explicit sign, boundary,
  position-interval and instrument binding; no-exposure, unavailable history, incomplete
  coverage and verified zero are four distinct states; funding reconciles across strategy,
  benchmark, portfolio and venue-account views.
- **Carriers:** #380 (B04, finality half BLOCKED on venue statements), #385 (B09, operating
  net BLOCKED on cost receipts).
- **Acceptance:** duplicate/late/out-of-window records refused or resolved by declared rule;
  restart replay identical; all-leg reconciliation exact; a funding cell carries a number only
  on the curve the engine measured.

### F5 — Native execution and protection safety

- **Requirement:** Execution evidence distinguishes decision, submission, acceptance, fill,
  rejection and account clocks and reconciles model against venue-settled outcomes. Protective
  orders (stop/bracket) must be proven on venue artifacts; a bracketless or proxy exit is named,
  never presented as native protection. Execution stays `SIM_ONLY`/`EXECUTION_UNPROVEN` until
  the evidence exists.
- **Carriers:** #379 (B03, `BLOCKED` on venue fills/latency/account exports), #453 R4
  (probabilistic fill model only behind the modelled column), adjacent open PR #497 (#483
  bracket replay, cost lane; not merged, not evidence of protection).
- **Acceptance:** partial/rejected/unfilled orders and adverse selection measured from physical
  artifacts; missed-fill opportunity cost included in shortfall; account cash/position/funding/
  commission/P&L reconciled without double counting; no code path labels simulated protection
  as venue protection.

### F6 — Honest economic receipts

- **Requirement:** A receipt publishes only what its own run measured and on the basis it was
  measured. The object a verdict describes is the object published (no stripped copy); the DSR
  authority condition names a declared subject, not a sort order; a contradicted ledger cell is
  declared superseded; a gate's name matches its measurement; no `SUPPORTS_EDGE` without the
  full authority receipt.
- **Carriers:** #500 (FIX_NOW: P+E verdict must read its own published mix), #494 (FIX_NOW:
  declared DSR subject in the pinned plan), #478 (FIX_NOW), #495 (merged), #493/#490/#480
  (already in PR #506 baseline).
- **Acceptance:** `portfolio_mix.scope == ENGINE_LEVEL_SAME_BUDGET` cannot coexist with a
  `BASIS_UNSTATED` verdict; `p_vol`/`pe_vol`/`comparison_basis` recomputable from the receipt's
  own per-bar returns; DSR subject declared in the plan and permutation-invariant; missing
  basis fails closed to `INCONCLUSIVE`.

### F7 — Point-in-time integrity

- **Requirement:** Decision inputs are point-in-time recoverable; future information is
  evaluator-only; temporal identities (bar / funding event / decision time) are disjoint types;
  a protected OOS window is frozen, burned once, and never relabelled; search-family accounting
  includes failed and omitted attempts.
- **Carriers:** #377 (B01, `BLOCKED` on an unburned protected window and complete external
  search history), #455 R4 (temporal ids, B16), #384 (B08).
- **Acceptance:** decision features identical under future-suffix mutation; frozen OOS plan
  frozen before its window; atomic burn including failed attempts; second access/relabel/tune
  rejected; family comparison complete with roles and hashes.

## 4. BLOCKED register — exact missing external evidence

No item below may substitute a synthetic, inferred, or re-labelled artifact. When the evidence
is absent the run must publish `BLOCKED`/`DATA_BLOCKED`/`UNKNOWN` with the reason, never a
number.

| Code | Blocks | Exact missing evidence | Current state in tree |
|---|---|---|---|
| `EXT-OOS` | B01, B11 | An **unburned** chronological holdout window for the evaluated family + the complete external search history (all failed/omitted trials with roles and hashes). | V8's protected tail is burned (`TAIL_BURNED`; D-164 records `NO_PROTECTED_FINAL` as metadata). No protected final window remains. |
| `EXT-VENUE` | B03, B11, F5 | Venue order/fill/account exports with source and receipt clocks, including partial/rejected/unfilled orders, for the evaluated window and venue/instrument. | No venue-settled fill ledger is consumed; `shadow_live` fields are `UNRUN`; real-money activation is forbidden. |
| `EXT-FUNDING` | B04, B11 | Venue funding/settlement statements and account records proving finality, lateness and coverage (public funding history is not finality). | Public funding capture and isolated tests exist; benchmark passes no settlements and reports `funding_cost = MISSING`. |
| `EXT-L2` | B06, B11 | Sequenced trade/quote/L2 capture + venue fills for all evaluated instruments over the window. | `docs/evidence/archive/l2/README.md` defines the contract only; no sealed L2/tick tape in the checkout. |
| `EXT-COST` | B09, B11 | Fee-tier receipts, real fill-vs-mid observations, and OPEX source artifacts with period/currency/allocation. | Configured fee assumptions and a monthly OPEX limitation note only; no business-net measurement. |
| `EXT-TAPE` | B19 | The canonical 12-month `quad-1h-12m` tape. | Absent; the only in-repo real tape is single-leg BTCUSDT, which the quad basket refuses (`missing leg(s): ETHUSDT, SOLUSDT, AVAXUSDT`). |
| `EXT-PARITY` | B07 | A physically produced independent reference ledger for the same window/contract. | `parity.py` defines bindings/mapping/receipts; no reference ledger is required or consumed by the economic command. |

## 5. Per-item detail

### B01 — #377 Protected one-shot OOS and complete search-family evidence

- **Source:** <https://github.com/ddawnlll/v8/issues/377> (`type:implementation`, state:triage)
- **Why deferred:** V9 replaces the Candidate/search surface; the V8 protected window is
  already burned, so the one-shot workflow cannot be demonstrated on V8 data. The *principle*
  (freeze → burn once → reject reuse) is a V9 foundation (F7) and must be re-implemented on the
  V9 family, not carried as a V8 claim.
- **Requirement (from issue):**
  - R1 — Freeze an immutable OOS plan before its window starts.
  - R2 — Burn the dataset/family lineage atomically on first evaluation, including failed attempts.
  - R3 — Reject any second access, relabeling, tuning, or reuse of revealed OOS.
  - R4 — Compare every locally registered family member with explicit roles and hashes.
  - R5 — Keep all outputs `NO_ECONOMIC_CLAIM` until a separate authority receipt exists.
- **Acceptance / verification gates (from issue):** pre-window registration; atomic burn;
  failed-after-burn recovery; duplicate/relabel rejection; missing-family rejection;
  deterministic two-process replay; STORE/receipt hashes bound to the plan.
- **Expected surface:** `v8-next/src/v8_next/evaluation/{forward_plan,family,store}.py`,
  `app/forward.py`, `tests/test_forward_plan.py`, `tests/test_family.py`.
- **Blocker:** `EXT-OOS` (§4). `TAIL_BURNED` means no unburned protected window exists for the
  V8 family; complete external search history is not proven.
- **Evidence state:** `Remaining R IDs: R1-R5`, evidence `PENDING`.

### B02 — #378 MinTRL estimator

- **Source:** <https://github.com/ddawnlll/v8/issues/378> (`type:research`)
- **Why deferred:** A diagnostic horizon estimator, not needed to start the ontology break. It
  becomes meaningful once V9 has real aligned return intervals and a declared target Sharpe.
- **Requirement (H1/H0, from issue):** given a preregistered target Sharpe, null Sharpe,
  confidence, power, dependence model, interval unit and variance assumptions, return a
  reproducible required horizon; if assumptions/data are missing return
  `UNDERPOWERED`/`UNSUPPORTED`, never a universal trade-count or calendar threshold.
- **Acceptance / gates:** analytic cases against independently calculated reference values;
  unit and annualization semantics; dependence and power sensitivity; invalid/degenerate
  inputs; deterministic serialization; run only on real aligned return intervals for economic
  reporting; `NO_ECONOMIC_CLAIM`.
- **Expected surface:** new `evaluation/mintrl.py`, `evaluation/inference.py`,
  `evaluation/economic_benchmark.py`, new `tests/test_mintrl.py`, `tests/test_inference.py`.
- **Blocker:** none for the estimator; real intervals required before any economic reading.
- **Evidence state:** `Remaining R IDs: R1-R5`, `PENDING`.

### B03 — #379 Venue fills, latency, shortfall, account reconciliation

- **Source:** <https://github.com/ddawnlll/v8/issues/379> (`type:implementation`)
- **Why deferred:** Requires live/venue evidence that cannot be manufactured; V8 execution is
  `SIM_ONLY`. It is F5-critical for V9 but starts only when venue artifacts exist.
- **Requirement (from issue):**
  - R1 — Ingest physically produced venue order/fill/account artifacts with source and receipt clocks.
  - R2 — Measure model fill vs real fill, latency drag, adverse selection, fees, missed-fill opportunity cost.
  - R3 — Reconcile venue account cash, position, funding, commission, realized/unrealized P&L without double counting.
  - R4 — Keep execution `SIM_ONLY`/`EXECUTION_UNPROVEN` until all required evidence exists.
- **Acceptance / gates:** event-clock ordering; partial/rejected/unfilled orders; adverse
  selection; fee/funding reconciliation; tamper/missing-artifact blocking; exact rerun
  determinism with physical fixtures only in tests.
- **Expected surface:** `adapters/shadow_ingest.py`, `evaluation/economic_benchmark.py`,
  `evaluation/parity.py`, `app/economic.py`, new `tests/test_shortfall_reconciliation.py`.
- **Blocker:** `EXT-VENUE` — no venue-settled fill/account ledger.
- **Evidence state:** `PENDING`; `shadow_live` `UNRUN`.

### B04 — #380 Funding finality and coverage

- **Source:** <https://github.com/ddawnlll/v8/issues/380> (`type:implementation`)
- **Why deferred:** The capture half is buildable, but the finality half needs venue
  statements; V9 must inherit the four-state distinction (no exposure / unavailable /
  incomplete / verified zero) even if only the first two can be measured now.
- **Requirement (from issue):**
  - R1 — Bind every funding row to venue event time, receipt time, source mark, position interval, instrument.
  - R2 — Apply each settled payment exactly once with explicit sign and boundary semantics.
  - R3 — Distinguish no exposure, unavailable history, incomplete coverage and verified zero.
  - R4 — Reconcile funding in strategy, benchmark, portfolio and venue-account views.
- **Acceptance / gates:** duplicate/late/out-of-window records; partial coverage;
  position open/close boundaries; sign conventions; restart replay; exact reconciliation
  across all benchmark legs; run against physically captured funding responses.
- **Expected surface:** `adapters/funding_history.py`, `adapters/settlements.py`,
  `evaluation/economic_benchmark.py`, `app/economic.py`, new `tests/test_funding_finality.py`.
- **Blocker:** `EXT-FUNDING` for R1/R2/R4 finality; R3 and the binding can start on captured
  public funding rows without claiming finality.
- **Evidence state:** `funding_cost = MISSING`; no settlements passed to the engine.

### B05 — #381 Joint P+E portfolio execution and shared capital

- **Source:** <https://github.com/ddawnlll/v8/issues/381> (`type:implementation`)
- **Why deferred:** The current P+E comparison is allocator-level; making it joint execution is
  a large change whose sleeve definitions V9 may redefine. Valuable, not start-blocking.
- **Requirement (from issue):**
  - R1 — Run P and P+E under the same declared capital, allocation, concurrency, margin, heat and fee rules.
  - R2 — Net opposing orders and account for rejected/unfilled orders in the shared ledger.
  - R3 — Report incremental portfolio return, risk, turnover, drawdown and cost from the same joint account.
  - R4 — Prove the comparison isolates the declared component change.
- **Acceptance / gates:** shared-wallet conservation; overlapping instruments; opposing-order
  netting; max concurrency; margin/heat contention; rejected orders; equal-budget P/P+E reruns;
  deterministic incremental attribution.
- **Expected surface:** `evaluation/economic_benchmark.py`, `adapters/portfolio_backtest.py`,
  `adapters/portfolio_equity.py`, `economics/allocation.py`, new
  `tests/test_joint_portfolio_execution.py`.
- **Blocker:** dependency on the V9 policy/sleeve shape; no external evidence.
- **Evidence state:** `allocator_mix` discloses allocator-level mixing.

### B06 — #382 Capacity and market impact from L2 data

- **Source:** <https://github.com/ddawnlll/v8/issues/382> (`type:research`)
- **Why deferred:** No L2/tick/venue-fill dataset; the issue's own H0 says the result is
  `DATA_BLOCKED` without it. V9 must not inherit a linear extrapolation as capacity.
- **Requirement (H1/H0):** with a declared venue/instrument/time window, order size and
  participation materially affect fill probability, shortfall and net portfolio outcome; if
  L2/tick/ADV/venue fill data are absent or not identifiable, capacity is `DATA_BLOCKED` and no
  coefficient is invented. Report scale-specific fill, impact, spread, participation, capacity
  floor and uncertainty.
- **Acceptance / gates:** real sequenced trade/quote/L2 data; price-time ordering; venue
  constraints; participation/impact calibration; scale monotonicity; sensitivity; missing-data
  refusal; no synthetic series outside isolated tests.
- **Expected surface:** new `evaluation/capacity.py`, `evaluation/economic_benchmark.py`,
  `adapters/shadow_ingest.py`, new `tests/test_capacity.py`, research manifests/reports.
- **Blocker:** `EXT-L2`.
- **Evidence state:** `PENDING`; current capacity block is a labelled projection after #477.

### B07 — #383 Two-ledger external parity into the economic evaluator

- **Source:** <https://github.com/ddawnlll/v8/issues/383> (`type:implementation`)
- **Why deferred:** Needs an independent reference ledger that does not exist yet; parity is
  diagnostic and non-sovereign, so it does not block the V9 start.
- **Requirement (from issue):**
  - R1 — Require native and reference ledgers declared by a benchmark manifest.
  - R2 — Pair records by the versioned mapping and compare exact bit-pattern values where required.
  - R3 — Record missing/unpaired/unsupported semantics explicitly, never zero differences.
  - R4 — Bind parity receipt identity to policy, case, mapping, engine, artifact hashes and method version.
  - R5 — Keep parity diagnostic and non-sovereign.
- **Acceptance / gates:** missing/tampered/empty artifacts; schema/mapping mismatch; unpaired
  records; bit-pattern divergence; policy identity binding; receipt grafting; economic CLI
  integration with two physical ledgers.
- **Expected surface:** `evaluation/parity.py`, `evaluation/economic_benchmark.py`,
  `app/economic.py`, `evaluation/benchmark_receipt.py`, new
  `tests/test_economic_parity_wiring.py`.
- **Blocker:** `EXT-PARITY` (reference ledger); the native ledger exists.
- **Evidence state:** parity adapter exists, default economic command does not require it.

### B08 — #384 Complete candidate lifecycle bound to economic evaluation

- **Source:** <https://github.com/ddawnlll/v8/issues/384> (`type:implementation`)
- **Why deferred:** V9 changes the Candidate ontology itself. Binding V8's lifecycle semantics
  into the evaluator now would encode the ontology V9 replaces; the requirement must be
  re-expressed against the V9 Candidate contract.
- **Requirement (from issue):**
  - R1 — Persist one immutable identity for every candidate episode and lifecycle transition.
  - R2 — Include trigger, rejection, invalidation, expiry, cancellation, partial fill and fill reasons in evaluator input.
  - R3 — Reconcile candidate, campaign, order, fill, position and cashflow populations without dropping terminal non-fills.
  - R4 — Produce reasoned coverage counts and explicit missingness before any metric.
- **Acceptance / gates:** every transition; terminality; duplicate prevention; candidate→order
  joins; filled-only view cannot hide non-traded candidates; coverage counts reconcile.
- **Expected surface:** `opportunities/book.py`, `evaluation/store.py`,
  `evaluation/outcomes.py`, `evaluation/family.py`, `app/trial.py`, new
  `tests/test_candidate_lifecycle_evaluator.py`.
- **Blocker:** V9 Candidate ontology; no external evidence.
- **Evidence state:** local lifecycle paths exist; evaluator population not proven complete.

### B09 — #385 Real operating net and venue-cost calibration

- **Source:** <https://github.com/ddawnlll/v8/issues/385> (`type:implementation`)
- **Why deferred:** Needs real fee-tier/fill/OPEX evidence; V8 only has configured
  assumptions. It is a V9 business-honesty requirement, not a start gate.
- **Requirement (from issue):**
  - R1 — Produce separate transaction P&L, funding/carry, explicit fees, strategy net and operating net.
  - R2 — Calibrate fee and slippage assumptions from physical venue receipts; never reuse spread/slippage twice.
  - R3 — Bind OPEX period, currency, allocation rule and source artifacts to the run.
  - R4 — Report business-net uncertainty and fail closed when any component is unmeasurable.
- **Acceptance / gates:** component conservation; maker/taker tier selection; fill-vs-mid
  calibration; funding inclusion; fixed-cost period allocation; currency/unit checks;
  double-count prevention; missing-source refusal.
- **Expected surface:** `evaluation/economic_benchmark.py`, new `evaluation/costs.py`,
  `evaluation/report.py`, `adapters/shadow_ingest.py`, new `tests/test_operating_net.py`.
- **Blocker:** `EXT-COST`.
- **Evidence state:** configured fees + OPEX limitation note only; funding `MISSING`.

### B10 — #392 Resolve UNKNOWN and MISSING gate states with explicit evidence

- **Source:** <https://github.com/ddawnlll/v8/issues/392> (`type:implementation`)
- **Why deferred:** The gate taxon is partially present (`GateState` already carries
  `BLOCKED`/`NOT_APPLICABLE`/`MISSING`/`UNKNOWN`; no `UNRUN`), but the full "every non-PASS
  gate exposes its next required artifact" contract is broader than a defect fix and interacts
  with B18 wiring. It should be re-pinned once against the V9 receipt contract.
- **Requirement (from issue):**
  - R1 — Every gate has an explicit state and reason; `UNKNOWN` only for unresolved evidence/method; `MISSING` only for absent required evidence; `BLOCKED`/`NOT_APPLICABLE`/`UNRUN`/`FAIL` distinguished.
  - R2 — The aggregate verdict stays fail-closed and cannot become an economic claim merely because a gate was evaluated.
  - R3 — The dashboard exposes the next required artifact/check for every non-PASS gate.
- **Acceptance / gates:** coverage for each canonical state and for incomplete/contradictory
  inputs; `status`/`benchmark --diagnostic-only` stay `NO_ECONOMIC_CLAIM`.
- **Expected surface:** `evaluation/benchmark_receipt.py`, `evaluation/gate_resolution.py`,
  `evaluation/runner.py`, `evaluation/scoring.py`, `app/cli.py`.
- **Blocker:** none externally; dependency on the V9 receipt contract and B18 wiring.
- **Evidence state:** G0-G2 PASS / G3-G7 UNKNOWN / G8-G9 MISSING as of issue creation; #495
  merged changes G3 naming only.

### B11 — #393 Close the economic evidence gate without weakening NO_ECONOMIC_CLAIM

- **Source:** <https://github.com/ddawnlll/v8/issues/393> (`type:research`)
- **Why deferred:** This is the program that *consumes* B01/B03/B04/B07/B09; it cannot precede
  them and cannot be scheduled until their evidence exists.
- **Requirement (from issue):**
  - R1 — Map every economic gate to its required input and artifact (preregistered matrix).
  - R2 — Preserve complete trial and lineage accounting.
  - R3 — Use only eligible real outcomes.
  - R4 — Keep the claim firewall closed until receipt verification passes.
  - R5 — Report missing, failed and underpowered evidence separately.
- **Acceptance / gates:** preregistered gate/evidence matrix; real-data manifests and hashes;
  statistical outputs with method/version/plan identity; protected-OOS and lineage receipts;
  parity and venue/funding reconciliation artifacts; independent review/verification log; fail
  closed on absent/mismatched/underpowered/non-independent input.
- **Forbidden (from issue):** no fabricated p-value/Sharpe/PBO/DSR/effect size; no synthetic or
  offset outcome inputs; no protected-OOS opening without authority; no live-money activation;
  no conversion of `NO_ECONOMIC_CLAIM` via dashboard scoring.
- **Expected surface:** `evaluation/{runner,gate_resolution,economic_benchmark,parity,overfitting,store}.py`.
- **Blocker:** `EXT-OOS` + `EXT-VENUE` + `EXT-FUNDING` + `EXT-COST` (union).
- **Evidence state:** `PENDING`.

### B12 — #451 Port chain 2/7: attribution language (veto + analysis + telemetry)

- **Source:** <https://github.com/ddawnlll/v8/issues/451> (`type:implementation`, reopened)
- **Current state:** **IMPLEMENTED** in the tree (`analysis/` planes, `telemetry/{belief,span,identity}`
  and `execution_telemetry` extension; evidence: 1306 campaigns reconciled against the frozen
  artifact, 35+27+20 tests green). It was **reopened under #476 R1** because these modules have
  no consumer in the benchmark path (`tools/audit_wiring.py` reports
  `analysis.reconcile`, `analysis.veto_attribution`, `telemetry.belief`, `telemetry.identity`,
  `telemetry.span` as ORPHAN).
- **Why deferred:** The unique requirement left is a wiring edge, which is B18's acceptance,
  not a new attribution feature. Keeping it as a separate V9 item would duplicate B18.
- **Requirement (from issue):**
  - R1 — Every refused campaign/decision recorded with canonical reason; P2 report prints refused-what-and-why beside lost-what-and-why.
  - R2 — Reconciliation phases run over a 4y report; each losing trade charged to exactly one domain; conservation verified.
  - R3 — Belief/span/identity trail attached to decisions, structured and hash-bound, consumable by `explain`.
  - R4 — Gates green; `regret_o4` explicitly not ported.
- **Acceptance:** named consumer edge into `BenchmarkRunner→BenchmarkReceipt→PolicyCertificate`
  (B18 R1); P2 columns populated from the analysis plane; ORPHAN count zero in
  `tools/audit_wiring.py`; report keys byte-equal modulo run metadata.
- **Blocker / dependency:** B18 consumer edges.
- **Surface:** `analysis/`, `telemetry/`, `adapters/execution_telemetry.py`, `app/explain.py`, tests.

### B13 — #452 Port chain 3/7: Hindsight/Target oracle substrate

- **Source:** <https://github.com/ddawnlll/v8/issues/452> (`type:implementation`, reopened)
- **Current state:** **IMPLEMENTED** — 9 oracle modules + 32 tests; future-information tests pass;
  reopened under #476 R1 because the oracle modules are ORPHAN outside `v8_next/oracle/` and tests.
- **Why deferred:** Same as B12: only the consumer edge remains, owned by B18.
- **Requirement (from issue):**
  - R1 — O1 extractor: causal, non-overlapping directional swings (pure function over polars); O0 evaluator-only, never a decision feature.
  - R2 — `UtilityContract`: versioned lexicographic contract (fee/funding/slippage/impact model ids); NetUtility primary with hard constraints.
  - R3 — Coverage reconciliation: frozen opportunity universe vs same-event expert proposals, `NO_ECONOMIC_CLAIM` receipts.
  - R4 — Support validation: unsupported profitable hindsight paths are model-derived/unknown, never opportunities.
  - R5 — Recoverability chain with monotonic-subset and utility-ordering invariants.
  - R6 — Gates green; future information provably evaluator-only.
- **Acceptance:** a named benchmark consumer for the coverage/recoverability receipts; ORPHAN
  zero; decision features identical with/without future bars (already tested).
- **Blocker / dependency:** B18.
- **Surface:** `oracle/` (9 modules), `tests/test_oracle_*.py`.

### B14 — #453 Port chain 4/7: proving ground

- **Source:** <https://github.com/ddawnlll/v8/issues/453> (`type:implementation`, reopened)
- **Current state:** **IMPLEMENTED** — `world/`, `system_proving/run.py`,
  `evaluation/proving_battery.py`, tests; `regression` green under D-166 correction; reopened
  under #476 R1 because `proving_battery` is only a CLI passthrough string and
  `BenchmarkRunner` never invokes the world foundry.
- **Why deferred:** Wiring only (B18); the synthetic-world/evidence work is done and must not
  be re-done in V9.
- **Requirement (from issue):**
  - R1 — World foundry: stationary-bootstrap, stochastic-vol/Hawkes/copula/surgery worlds; seed-pinned spec + receipt each.
  - R2 — Full-chain runner over `BacktestEngine` (discovery→reconciliation→risk gate→sizing→double-entry ledger); `SystemProvingGroundReceipt`-compatible.
  - R3 — Adversarial battery: mutation/property/PIT fault injection; failures named, never silent.
  - R4 — Slippage lane legitimized via `ProbabilisticFillModel` + pinned seed behind the modelled column.
  - R5 — Gates green.
- **Acceptance:** `BenchmarkRunner` consumes the proving-ground receipt (or refuses by name);
  worlds carry `SYNTHETIC:*` tags and never enter evaluative aggregates; ORPHAN zero.
- **Blocker / dependency:** B18.
- **Surface:** `world/`, `system_proving/run.py`, `evaluation/proving_battery.py`, `app/cli.py`.

### B15 — #454 Port chain 5/7: benchmark pipeline

- **Source:** <https://github.com/ddawnlll/v8/issues/454> (`type:implementation`, reopened)
- **Current state:** **IMPLEMENTED** — 8 D-153 delta modules, single `run` sweep, static report;
  PR #504 wired `projection`/`Minerva`/MinTRL into `PolicyCertificate.generate`, closing part
  of the gap. Still open: `evaluation.external`, `evaluation.kaizen_delta`,
  `evaluation.observation`, `evaluation.population`, `evaluation.projection`,
  `evaluation.synthetic`, `evaluation.minerva` have no consumer outside tests.
- **Why deferred:** Same wiring residual as B12-B14, now split between B15 and B18.
- **Requirement (from issue):**
  - R1 — One orchestration entry (CLI `run`) sweeping pillars→receipts→HTML+tearsheet; no new per-NX script surface.
  - R2 — D-153 delta ported: scoring/parity/external/certificate/ledger + observation/population/projection + minerva robustness; synthetic inputs stay `SYNTHETIC_*`.
  - R3 — Report carries every return with cost columns + SNU count + attribution summary.
  - R4 — Tearsheet visuals embedded where offline-safe; no plotly dependency forced into evaluative paths.
  - R5 — Gates green; ledger chain verify + regression compare in the sweep.
- **Acceptance:** forensic HTML stops rendering `MISSING` for factors that have producers; a
  named refusal where unmeasured; ORPHAN zero for the seven delta modules; sweep re-run
  determinism.
- **Blocker / dependency:** B18.
- **Surface:** `evaluation/` delta modules, `app/benchmark.py`, `app/cli.py`, report/certificate.

### B16 — #455 Port chain 6/7: scoring closure

- **Source:** <https://github.com/ddawnlll/v8/issues/455> (`type:implementation`, `state:blocked`)
- **Current state:** Partially delivered (`domain/temporal_ids.py`, score-binding tests, leakage
  audit); labelled blocked on two foreign reds: `audit_doc_path_refs.py` cites a moved
  `v8-core/tests/integration/` path in `ISSUE_PERF008…md:60`, and full `mypy evaluation` has 6
  pre-existing errors in `benchmark_receipt.py`, `scenarios.py`, `trajectory.py`.
- **Why deferred:** Blocked on foreign ownership/workstream; re-pin against V9 scoring after
  the foreign guards are fixed. It is the dependency of B17.
- **Requirement (from issue):**
  - R1 — Published capability score is a function of the evidence the receipt binds (no bypass).
  - R2 — Synthetic inputs carry `SYNTHETIC_*` labels end-to-end and are rejected from evaluative aggregates.
  - R3 — Research-delta verified against `ResearchStore` (burn/lineage honored; frozen OOS never reopened).
  - R4 — Temporal separation: disjoint id types for bars/funding/decisions; future-suffix mutation tests.
  - R5 — Gates green incl. `audit_synthetic_leakage.py` and the doc-path-refs guard.
- **Acceptance:** every published score traceable to a receipt-bound measurement; leakage audit
  green; the two foreign reds owned and closed by their workstreams (not by weakening the
  guards or excluding paths).
- **Blocker:** foreign doc-path/mypy reds; then the V9 score contract.
- **Surface:** `evaluation/{scoring,gate_resolution,store,statistics_plan,...}.py`, `domain/temporal_ids.py`.

### B17 — #456 Port chain 7/7: expert lifecycle

- **Source:** <https://github.com/ddawnlll/v8/issues/456> (`type:implementation`, `state:triage`)
- **Current state:** Not started (`Remaining R IDs: R1-R6`). Depends on B16 (closed scoring) and
  on the V9 expert/proposal baseline.
- **Why deferred:** Terminal chain item; meaningless before B16 and likely re-scoped by the V9
  learned-proposal baseline.
- **Requirement (from issue):**
  - R1 — EEO + expert-delta mapping published file-by-file (ported / delta / wont-port-with-reason) before code.
  - R2 — Expert delta ported (logic handmade, vectorization via polars; no per-expert perf regression).
  - R3 — Qualification falsification surface separates semantic evidence from real-tape attribution; no economic verdict type.
  - R4 — Kaizen robustness/validation feed to P3 scenarios; controller/loop last with explicit no-autonomy guard.
  - R5 — Assurance/EEO/governance remainder in priority order; judiciary/tevv accountability-plane only.
  - R6 — Gates green incl. perf tests where touched.
- **Acceptance:** qualification output contains no economic verdict type (type/field absence
  test); expert delta preserves trigger semantics on golden fixtures; kaizen feed has no
  execution import/live path.
- **Blocker / dependency:** B16.
- **Surface:** `experts/`, `qualification`, `kaizen/`, `assurance/`, `eeo/`, governance remainder.

### B18 — #476 451-454 outputs are IMPLEMENTED but unwired

- **Source:** <https://github.com/ddawnlll/v8/issues/476> (`type:defect`, `state:in-progress`)
- **Current state:** **PARTIAL, R2-R4 now on main** — PR #504 merged (`a00debdb`) delivered R2
  (projection/Minerva/MinTRL passed to `PolicyCertificate.generate` or named refusal), R3
  (`tools/audit_wiring.py` blocking, no allowlist), R4 (API issue wiring-manifest enforcement).
  **R1 is open**: #451-#454 were reopened, but the orphan modules still have no consumer edge
  into the benchmark path.
- **Why deferred:** The remaining work is a wiring change set (producer→consumer→final
  surface→E2E) across four issue surfaces; it is the single carrier for B12-B15's residuals and
  must be done as one slice, not four.
- **Requirement (from issue):**
  - R1 — Each of the four outputs gains a named consumer edge into the benchmark path (`benchmark`→`BenchmarkRunner`→`BenchmarkReceipt`→`PolicyCertificate`→forensic HTML/`readiness`/`regression`), **or** the closed issue is reopened with the unwired R back in Remaining (already done for #451-#454).
  - R2 — `PolicyCertificate.generate` receives produced `projection`/`minerva` (or a named refusal).
  - R3 — `tools/audit_wiring.py` fails on any module with no importer outside its own package/tests; blocking in the local gate loop.
  - R4 — API-created issues cannot bypass the wiring manifest.
- **Acceptance / E2E:** `audit_wiring.py` ORPHAN count zero for
  `{oracle,evaluation,world,system_proving}/` surfaces (explicit allowlist forbidden); a real
  `benchmark` run shows the four outputs in the final HTML/readiness surface; a synthetic-only
  test proves the refusal path; W1-W7 manifest present on the wiring issue.
- **Blocker:** none external; blocked on owner prioritization of the slice order (issue's own
  dependency note).
- **Surface:** `evaluation/{runner,certificate,report,benchmark_receipt}.py`, `app/{portfolio,cli}.py`, `tools/audit_wiring.py`.

### B19 — #491 Equity path drops closed campaign exit P&L

- **Source:** <https://github.com/ddawnlll/v8/issues/491> (`type:defect`, `state:in-progress`)
- **Current state:** **PARTIAL, now on main** — PR #503 merged (`edd557e2`, `033cab6f`): the
  exit leg is marked with `closed_positions[].avg_px_close` (R1), the exit-leg identity is
  published (R3), and the residual identity is published without claiming it holds (R4).
  **R2 still fails on real data:** on a real 4-leg July-2025 tape the residual is
  `UNEXPLAINED_RESIDUAL`, `portfolio_P gap=37.4161 expected=31.6111 unexplained=5.8050`,
  `portfolio_PE gap=39.5225 expected=17.0185 unexplained=22.5040` USDT. The graft's
  "commissions + rounding" reading is therefore false; the receipt now says so.
- **Why deferred:** The remaining defect is the mark path's residual equality and the missing
  canonical tape; it is an equity-reconciliation foundation item (F3) that cannot be closed by
  the partial PR and must not be glossed.
- **Requirement (from issue):**
  - R1 — Book each closed campaign's exit leg into the published equity path (measured exit price, never a dropped position).
  - R2 — A residual not explainable by fees + funding publishes a named non-reconciling state instead of a graft presented as cost.
  - R3 — The terminal identity `Σ(equity[i]−equity[i−1]) = balance_total − capital` holds exactly.
  - R4 — No imputed value: an unmeasurable exit stays named (`bar_close_proxy_exits`), never 0-filled or dropped.
- **Acceptance / gates:** real-window producer run where `cost_reconciliation` carries the exit
  leg identity and either reconciles or names the unexplained residual with its terms; no test
  asserts today's smeared values; `max_drawdown`/`sharpe`/`tail_mean`/`excess_vs_primary`/
  readiness monthly-return cell recomputed on the corrected path; `claim_status` stays
  `NO_ECONOMIC_CLAIM`.
- **Blocker:** `EXT-TAPE` (canonical 12-month `quad-1h-12m` tape) + an owner decision on the
  residual/spread convention (issue §16 says the uniform amortisation is out of scope; the
  residual's meaning is not).
- **Surface:** `evaluation/economic_benchmark.py` (`strategy_series_from_engine`,
  `portfolio_series_from_engine`, `published_cost_reconciliation`).

### B20 — #478 Ledger keeps a superseded cost verdict

**Source:** https://github.com/ddawnlll/v8/issues/478
**Status:** `DEFERRED_TO_V9` · **V9 phase:** P0-B
**Why deferred:** the requirement is a ledger-evidence obligation V9 inherits, not a prerequisite for starting the ontology break; it needs a declared supersession mechanism rather than an in-place edit.
**Blocker:** none external; requires a machine-readable `superseded_by`/governing declaration and an authority entry, with no byte edit or re-hash (D-164).

**Required end state:** A declaration names `seq 21` by `entry_hash`/`receipt_digest` as superseded for exactly the cells the `seq 23` measurement contradicts (`cost_basis`, `cost_reconciliation` identity/residual/tolerance/`ok`/`named_reason`, `verdicts.execution` + note, `oos_metrics[*].cost_basis`), names the replacing entry and receipt hash, and states those cells count toward no clause, readiness input, capability surface or comparison. The supersession is machine-readable (`DECLARED_CORRECTIONS` or an equivalent published field) so a consumer resolving one window identity names the governing entry without "newest sequence wins". A regression test fails on today's tree and passes after. No stored ledger byte is edited, re-hashed or deleted; the hash chain recomputes.

### B21 — #494 DSR subject is not declared in the pinned plan

**Source:** https://github.com/ddawnlll/v8/issues/494
**Status:** `DEFERRED_TO_V9` · **V9 phase:** P1-A
**Why deferred:** the literal alphabetical `sorted(...)[0]` is already gone on main, but the pinned `StatisticsPlan` still has no subject field; adding it changes every pinned `plan_id`/receipt identity and needs a versioned authority decision.
**Blocker:** none external; identity/authority decision required before changing pinned receipt identities.

**Required end state:** (1) `StatisticsPlan` gains the DSR subject (e.g. `dsr_subject` / `selected_variant`) inside `identity()`, or `run_statistics` takes an explicit champion argument the caller must supply. (2) A missing/unknown subject fails closed and named (`MISSING_DSR_SUBJECT`), never a silent `sorted()[0]`, matching `gate_resolution.py`'s `MISSING_CHAMPION_PVALUE`. (3) `statistics.dsr.selected_variant` still publishes and states it came from the plan, not ordering.

**Verification gates:** permuting family curve names leaves `selected_variant`/`dsr_confidence` unchanged; adding an earlier-sorting variant does not change the subject; `statistics.dsr` for `portfolio_P` equals a direct `deflated_sharpe_diagnostic(..., DSRPlan(selected_variant="portfolio_P"))`; a plan whose subject is absent blocks by name; existing economic-benchmark/statistics tests keep their outcomes.

### B22 — #500 Canonical P+E verdict ignores its own mix

**Source:** https://github.com/ddawnlll/v8/issues/500
**Status:** `DEFERRED_TO_V9` · **V9 phase:** P0-B/P1-C
**Why deferred:** it changes canonical portfolio verdict semantics and needs a comparison-basis decision; it is not required to start V9.
**Blocker:** none external; the canonical mix must measure `p_vol`/`pe_vol`/`comparison_basis` from the run's own equity series.

**Required end state:** The object handed to `build_verdicts` is the object published as `portfolio_mix` (one construction, one identity). The canonical mix publishes a measured basis from `p_ser["equity"]`, `pe_ser["equity"]` and `per_bar_returns`: `p_vol`, `pe_vol`, `vol_unit`, `comparison_basis`, and `incremental_net_basis = UNNORMALIZED_NOT_RISK_MATCHED` when not risk-matched. A `scope` string alone must not exempt a mix from measurement; no `incremental_net` without its basis label; the verdict follows that basis or is `INCONCLUSIVE` with measured vols named.

**Verification gates:** the canonical benchmark receipt can no longer carry `ENGINE_LEVEL_SAME_BUDGET` beside a `BASIS_UNSTATED` note; the mix carries recomputable vols and basis; a stripped mix (`{"incremental_net": x}` only) cannot reach any portfolio verdict but `INCONCLUSIVE`, with an identity assertion at the call site; the published sign of the risk-adjusted difference is reported and `claim_status` stays `NO_ECONOMIC_CLAIM`.

## Appendix A — non-deferred dispositions (coordinator closure sheet)

These are recorded here only so the queue can be closed with proof. They are not V9 backlog
requirements.

### A.1 `ALREADY_FIXED` (verified on `origin/main` or a cited PR head)

| Issue | Evidence | Closing comment (one line) |
|---|---|---|
| #390 | `v8-next/pyproject.toml:35` pins `duckdb>=1.0` in the locked `research` extra (`uv.lock` duckdb 1.5.5); `v8-next/tests/test_store_models_and_duckdb.py:340` is `pytest.importorskip("duckdb", reason="duckdb not installed (research extra)")` — explicit optional-integration contract, default `--extra dev` path passes; fix commit `6c4bdce4`. | Closed: the dev path no longer fails — DuckDB is pinned in the locked `research` extra and the integration test is an explicit, reasoned optional test (`test_store_models_and_duckdb.py:340`). |
| #391 | `v8-next/tests/test_portfolio_benchmark.py:9-11` now orders `import json` before the stdlib `from` imports; `uv run --project v8-next --extra dev ruff check v8-next/tests/test_portfolio_benchmark.py` → `All checks passed!`; fix commit `e1c75488`. | Closed: Ruff `I001` is resolved (`test_portfolio_benchmark.py:9-11`), and `ruff check v8-next/tests/test_portfolio_benchmark.py` passes with the rule set unchanged. |
| #409 | D-162 (`docs/decisions/DECISION_REGISTER.md:165`) is the authority record; the V9-foundation commit additionally aligns `v8-next/AGENTS.md` and `CLAUDE.md` with the owner V9 boundary (`v8-next/` active, `v8-core/` archived read-only) and with the V9 monograph. Residual, not a blocker: the physical `legacy/v8-core/` move named in D-162 is not executed (`v8-core/` remains at root, read-only). | Closed: D-162 and the V9-foundation boundary alignment reconcile the conflicting declarations; the remaining directory move is a named residual, not an unanchored rewrite. |
| #495 | Merged on main: `6571383a`, `ea0f543a`, `12e0dc28`; `v8-next/src/v8_next/evaluation/benchmark_receipt.py:450,579` publishes `g3_scenario_robustness` with `AliasChoices` read fallback for pre-rename ledger entries; `G3_SCENARIO_BASIS_ABSENT` at `:646`; tests `v8-next/tests/test_dashboard_gate_keys_495.py` and `test_gate_resolution.py` pin both halves. | Closed: fixed by #505 (merged) — the G3 cell is published as `g3_scenario_robustness` with its typed scenario basis, legacy ledger entries are still read via `AliasChoices`, and the dashboard asks for the published key. |
| #389 | PR #501 head (open, `Fixes #389`): `v8-next/src/v8_next/app/cli.py:47` `EXIT_LEDGER_QUARANTINED = 3`, `:102` prints `EVIDENCE CHAIN: QUARANTINED`, `:124` returns the quarantine exit; test `v8-next/tests/test_cli_status_ledger_quarantine_389.py`. PR #501 merged into main during the V8 close. | Closed: fixed by PR #501 — a broken ledger chain is quarantined and exits non-zero instead of rendering a certificate; verified by `test_cli_status_ledger_quarantine_389.py`. |
| #477 | PR #502 head (open, `Fixes #477`): `v8-next/src/v8_next/app/portfolio.py:209` imports `measure_capacity_bounds_from_participation`; every `capacity_scenarios[*]` entry carries `status` (`UNRESOLVED` for unobserved scales, `NO_ECONOMIC_CLAIM`/`HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED` for scenarios, `DATA_BLOCKED` when sigma/peak unmeasured). Limitation: R4's re-take used a rebuilt July-2025 quad tape because the canonical 12-month tape is absent. PR #502 merged into main during the V8 close. | Closed: fixed by PR #502 — the canonical capacity path routes through the swing-capacity contract, and every published entry carries `DATA_BLOCKED`/`UNRESOLVED`/`NO_ECONOMIC_CLAIM`; no extrapolation publishes a `MEASURED_*` kind. |

### A.2 `NOT_NEEDED`

| Issue | Explanation | Closing comment (one line) |
|---|---|---|
| #434 | Governance broadcast only ("autonomous merge authority granted"), no code/evidence requirement; its content is landed as D-163 in `docs/decisions/DECISION_REGISTER.md:172` and `docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md`, with the prohibition on direct `push` to `main` and the unchanged evidence/firewall rules. Nothing remains to implement or verify. | Closed: this was an authority announcement, not a work item; D-163 and `docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md` are the standing record, and the merge/evidence rules they left unchanged remain in force. |

### A.3 Not fixed now — preserved as B20–B22

1. **#500 — canonical P+E verdict ignores its own mix (now B22).** On `origin/main`, `app/portfolio.py:911`
   passes `{"incremental_net": mix["incremental_net"]}` to `build_verdicts` while `:923`
   publishes the full `portfolio_mix`; the `ENGINE_LEVEL_SAME_BUDGET` exemption in
   `economic_benchmark.py:4874-4896` is therefore unreachable on the canonical path. Fix: pass
   the published object, measure `p_vol`/`pe_vol`/`comparison_basis` from the run's own equity
   series, label `UNNORMALIZED_NOT_RISK_MATCHED`, fail to `INCONCLUSIVE` for a stripped mix.
2. **#494 — DSR subject is not declared in the pinned plan (now B21).** `origin/main` no longer takes
   `sorted(...)[0]` (`economic_benchmark.py:3544` selects max excess), but
   `StatisticsPlan` has no `selected_variant` field, so the plan identity does not name the
   subject; the issue's gates (permutation invariance, direct-DSR equality, fail-closed absent
   subject) are unmet. Fix: add the declared subject to `StatisticsPlan`/`as_dict`/`identity`,
   name the champion at the call sites, fail closed when the subject is absent.
3. **#478 — ledger keeps a superseded cost verdict (now B20).** `app/readiness.py:790`
   `DECLARED_CORRECTIONS` declares only `gate_passes`; `seq 21`'s `cost_basis = MISMATCH` /
   `EXECUTION_UNPROVEN` is still readable as current beside `seq 23`'s
   `VERIFIED_ENGINE_FUNDING` for the same window. Fix: declare the `seq 21 → seq 23`
   supersession with authority and reason (no byte edit, no re-hash, no number moved).

Acceptance criteria for these three (from the issues; they are *not* deferred and must land
before V9 receipts are trusted — if the owner instead chooses to defer, each has no external
blocker and can be re-scoped into this backlog without new evidence):

- **#500:** (1) a canonical re-run derives `verdicts.portfolio` from the published
  `portfolio_mix`, so `scope == ENGINE_LEVEL_SAME_BUDGET` cannot coexist with a
  `BASIS_UNSTATED` note; (2) `portfolio_mix` carries `p_vol`, `pe_vol`, `vol_unit`,
  `comparison_basis`, and (`comparison_basis != RISK_MATCHED ⇒
  incremental_net_basis == UNNORMALIZED_NOT_RISK_MATCHED`), all recomputable from the
  receipt's own `portfolio_P`/`portfolio_PE` per-bar returns; (3) a regression pins that a
  stripped mix (`{"incremental_net": x}` only) reaches no verdict but `INCONCLUSIVE`, and
  asserts call-site object identity; (4) the published sign of the risk-adjusted difference is
  reported and, if it disagrees with raw `incremental_net`, the receipt says which governs;
  gates unchanged, `claim_status` stays `NO_ECONOMIC_CLAIM`.
- **#494:** (1) permuting the family's curve names leaves `selected_variant` and
  `dsr_confidence` unchanged; (2) adding a variant whose name sorts before the champion does
  not change the published DSR subject; (3) the `portfolio_P` DSR equals
  `deflated_sharpe_diagnostic(..., DSRPlan(selected_variant="portfolio_P"))` on the same
  losses; (4) a plan whose subject is absent from the family blocks by name — no fallback to
  `sorted()[0]`; no estimator/threshold/seed change and a no-op on today's canonical numbers.
- **#478:** (1) a committed-ledger-only read shows `seq 21 cost_basis == "MISMATCH"` beside
  `seq 23 cost_basis == "VERIFIED_ENGINE_FUNDING"` for the same
  `(period_start_ns, period_end_ns, tape_sha256, n_bars)`; (2) after the fix the same read
  resolves to one governing entry and names `seq 21`'s contradicted cells superseded; (3)
  ledger hash chain and `seq 23` receipt sha256 are byte-identical before/after; (4) targeted
  test + ruff + mypy on the touched file.
