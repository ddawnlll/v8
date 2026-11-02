# V9 Architecture Monograph — Independent Model Council Synthesis

**Date:** 2026-11-02  
**Reviewed artifact:** `V9_ARCHITECTURE_MONOGRAPH_v1.md` (draft)  
**Inputs:** three blind, monograph-only independent model reviews (`Pasted text(10).txt`, `Pasted text (2)(2).txt`, `Pasted text (3).txt`).  
**Scope:** design critique and revision decisions; **not** repo-grounded verification, an economic audit, or authority to deploy.

## 1. Council verdict

All three reviews independently state **PROMISING BUT REQUIRES REVISION** and reject treating the current paper as a comprehensive implementable RFC. All three agree that the central problem is **not** the supplementary Pi/Kaizen layer: it is the missing executable semantics of the adaptive trading decision loop and unreliable or unverified economic attribution. Agreement is a useful review signal, not independent empirical validation: reviewers worked from the same monograph.

**Editorial decision: MAJOR REVISION — retain V9 target architecture, withhold broad implementation authorization.**

## 2. Findings and dispositions

| Finding | Convergence | Evidence class | Disposition | Specific revision |
|---|---|---|---|---|
| `Trader Decision Policy` argmax lacks identified estimators/horizon/unknown fallback | 3/3 | Documented specification gap | **ACCEPT — P0** | Define a complete deterministic baseline-equivalent decision procedure, legal actions by state, priority, reproducibility, and `UNKNOWN` behavior; keep argmax as future research objective |
| Action vocabulary `WAIT` vs `WATCH`, `MODIFY` vs `ADJUST` inconsistent; status/intent/event conflated | 3/3 | Documented defect in monograph | **ACCEPT — P0** | Canonical four-level vocabulary: decision, order/position intent, venue event, reason code; separate opportunity/order/position state machines |
| Historical 89 cashflow/campaign and protection join concerns, MFE/MAE timing, contradictory PASS | 3/3 | Prior-audit claims in monograph; current implementation unknown | **ACCEPT INVESTIGATION — P0** | Verify on pinned local commit, reproduce counterexamples, attach independent cashflow oracle and mutation tests; label affected old results provisional until resolved |
| Funding absent, realistic fill profile invalid, same-close OHLCV cannot substantiate live fills | 3/3 | Reported experiment limitations | **ACCEPT — P0** | Execution-profile authority matrix; no economic claim when a required cost/fill/mark source is unsupported |
| `MarketBelief` currently a feature/schema proposal, not demonstrated market understanding | 3/3 | Scientific open question | **ACCEPT — P1** | Define one falsifiable incremental decision use case and raw-feature/simple-threshold baselines; maintain market-intelligence target in long-term design |
| Expert votes may double-count correlated OHLCV evidence | 3/3 | Design risk + A1 DEV observation | **ACCEPT — P1** | Dependency-group ablation, clone tests, changed decision count, portfolio economic delta; do not purge 28 experts without evidence |
| Dynamic position management may create amendment churn and uncovered risk | 3/3 | Design risk | **ACCEPT — P0 safety / P1 policy** | Native protection, partial-fill and cancel/replace state invariants first; static brackets retained; one default-off challenger at a time |
| Order/position lifecycle is incorrectly linear | 3/3 | Documented diagram limitation | **ACCEPT — P0** | Orthogonal intent/order/position state machines, partial fills, unknown-at-venue, restart reconciliation, idempotent event handling |
| Occupancy observation is not ex ante opportunity-cost estimate | 3/3 | Scientific open question | **ACCEPT — P1** | Keep factual `blocked_by_position`; classify alternative portfolio policy outputs as simulated counterfactual; postpone capital rotation without valid estimates |
| Multiplicity/OOS/DEV comparison protocol not fully specified | 3/3 | Missing experimental contract | **ACCEPT — P0 prereg / P1 testing** | One baseline, one behavior change, matched calendar equity, explicit costs, family size, data role, stopping and `NO_EDGE/INCONCLUSIVE/INVALID` |
| Pi/Kaizen possibly becomes second product | 3/3 | Scope/complexity risk | **PARTIALLY ACCEPT** | Keep as independent small extension; pilot one bounded research task; no automatic promotion; do not remove Kaizen from V9's *target* architecture |
| Abandon MarketBelief/PositionManager/Allocator altogether | Some reviewers favor maximal minimalism | Proposed simplification, not proof of redundancy | **PARTIALLY REJECT** | Do not activate unproven policies in v1, but retain these responsibilities as V9 research targets; prioritize tests and use existing code |

## 3. Corrected architectural interpretation

Two deliberately separate loops must appear in the revised monograph:

**TRADING (primary):** point-in-time market/venue observations → bounded market-state representation → canonical opportunity/independent expert evidence → deterministic versioned trader policy → risk-approved entry/position/order intents → NautilusTrader/accounting → next observation and measured outcomes.

**KAIZEN (supplementary):** evidence and observed failures → Pi research task → preregistered native experiment → independent deterministic validation → tracked issue/PR → operator approval of new **versioned** policy. Pi never enters live market callbacks. The trading core operates without Pi.

Keep V8's native engine, PIT boundaries, OpportunityBook, observer/economic authority separation, existing gate/evaluation/store and audit components wherever verified. No mandatory new microservices, new backtester, learned router, LLM inference in live decision path, or large agent swarm.

## 4. Proposed *illustrative* minimum executable decision semantics

This is a design direction requiring repo-grounded RFC and invariant tests, **not** an implemented policy and **not** an approved trading rule.

1. **Reconcile first:** if venue order/position/protection state is unknown or inconsistent, block new risk; determine corrective action from a documented safety procedure, not a heuristic LLM output.
2. **Risk safety precedes economic preferences:** kill switch, verified protection and critical exposure limit checks are independent of the policy's estimated utility.
3. **If an order is pending:** reconcile fills and submit/cancel state before considering additional risk; use stable idempotency keys; never assume cancellation on timeout.
4. **If a position is open:** default to existing verified bracket/protective policy. `HOLD` is not an instruction to cancel protection. Dynamic amendments remain disabled until bounded and tested.
5. **If flat:** use V8's preserved baseline policy as a diagnostic comparator. A new V9 entry-changing candidate only runs in a preregistered experiment; absent required inputs/uncertified economic estimates do not manufacture positive expectancy.
6. **For every decision:** attach source snapshot availability time, policy/config hash, opportunity reference when present, reasons, predicted and realized intent states. Repeated events do not duplicate orders.

**Suggested vocabulary separation (to be ratified by repository review):** high-level `ABSTAIN/WAIT/ENTER/HOLD/REDUCE/EXIT`; `WATCHING/EXPIRED` are opportunity states; `SUBMIT/CANCEL/AMEND_PROTECTION` are intents; `ACCEPTED/PARTIAL_FILL/REJECTED/UNKNOWN_AT_VENUE` are venue outcomes; `PRICE_UNFAVORABLE/TIME_STOP/STALE_DATA` are reason codes. `MODIFY` and `ADJUST` must not compete as synonyms. `REJECT` must be typed by rejection authority rather than a universal action.

## 5. Ordered changes to the monograph

### P0 — Revise before approval of an implementable RFC

1. **Status:** label the present paper `ARCHITECTURE TARGET / UNVALIDATED POLICIES` and separate architecture approval, mechanical verification, scientific evidence, and live authorization.
2. **Repository truth:** inspect exact current `v8-next` commit, active local branches and historical D4 differences; distinguish existing code from proposals.
3. **Audit truth:** verify potentially broken attribution using *independent* hand-calculated multi-campaign ledger examples and fault injection, not just zero orphan joins.
4. **State and authority contracts:** define decision/action/intent/event/outcome vocabularies; event ordering, position and protection ownership; partial-fill, reject, timeout, restart handling.
5. **First executable policy:** write pseudocode + fixtures for a baseline-equivalent v0 with named inputs, priorities, fallbacks, idempotency and a defined decision trigger. Do not run the symbolic argmax in production.
6. **Execution authority:** version and qualify bar diagnostic versus next-observable/L1/L2 execution assumptions; funding accrual, realized settlement and cost accounting separate.
7. **Experimental plan:** freeze one initial comparison, primary calendar-aligned equity estimand, acceptable uncertainty, explicit costs, exposure and research family budget.

### P1 — Research-backed trading capabilities

8. One MarketBelief decision-use ablation; retain only incrementally justified active features.
9. Expert feature-lineage/dependency/ablation and selection effect tests.
10. Entry price-discipline challenger under certified execution assumptions.
11. One isolated position amendment challenger with hard protection, cooldown and turnover budgets.
12. Occupancy measurement first; allocation/rotation policy later and only with ex ante estimates.
13. Point-in-time altcoin universe, listing/delisting, min-notional and liquidation constraints before extrapolating BTC test evidence.

### P2 — Optional improvements after measured need

14. Kaizen one-task pilot compared with a bounded manual/script baseline. Persistent queue/lease only after demonstrated benefit.
15. Learned utility/regime routing, advanced market belief and cross-position rotation only after incremental economic evidence.
16. Live deployment qualification is a separate operational decision, not a monograph pass.

## 6. Council-to-repo execution contract

- **Architecture author:** revise scientific target and exact contracts; do not invent code facts.
- **Independent reviewers:** critique the revised spec without seeing author's unshared reasoning.
- **Repository agent (read only, first):** produce path+symbol+test mapped architecture inventory against the active `v8-next` branch and local D4 work; report contradictions and unavailable data.
- **Implementer (after owner approval):** implement one bounded slice per issue/PR, retaining baseline parity and native replay tests.
- **Deterministic validators:** own scientific/mechanical gates; LLM reviews cannot grant economic authority.
- **Owner:** approve policy promotion, sealed OOS access, merge and deployment separately.

## 7. Final disposition

**MAJOR REVISION** is warranted. The three blind reviews identify real document defects and actionable safety gaps, but do **not** falsify V9's strategic premise. Do not collapse V9 into a mere event logger or an agent-management framework. Keep the long-term market-aware adaptive trading vision and make its first integration small, causal, testable and economically honest. A validated mechanism and a positive economic finding are different claims.
