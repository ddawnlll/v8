# V8.7 readiness benchmark — locked specification

**Status:** LOCKED contract for the central benchmark. Supersedes the loose "run a
benchmark" reading: from here on a benchmark means *these three pillars, one ledger, one
score, one regression rule*. No economic authority is created by anything in this document:
every verdict stays `NO_ECONOMIC_CLAIM` until a protected paper-trade record exists.

Owner directive that produced this lock (paraphrased from the 2026-09-12 instruction): the
central CLI must carry this workflow instead of one-off scripts; the gates matter and they
feed the score; the 4-year simulated paper-trade report matters; synthetic hypothesis-test
scenarios passing matters; and all of it must move a **0 → 100 production-readiness score**
whose far target is the **red apple: 10 % monthly return**, with regression detection.

## 1. The red apple and what the score is allowed to mean

* **Red apple:** 10 % monthly return, net of measured costs, held out of sample. It is a
  *target*, never a claim. The score's target factor is measured against it, and a target
  factor is only counted when the return came from a window the strategy never saw.
* **Score 0** means "no measured evidence", not "measured zero". **Score 100** requires all
  ten gates resolved (with G8/G9 measured on real venue settlement) plus a protected 4-year
  paper-trade record that meets the declared risk limits and the target.
* A missing measurement contributes **0 to the numerator with its MISSING status printed
  beside it**. It is never filled in to move the number.

## 2. Three pillars, one ledger

| Pillar | What it is | Why it is not optional |
|---|---|---|
| **P1 Gate battery** | G0–G9 resolved on real runs; non-compensable (D-152 §5) | a strategy cannot buy its way past a failed gate with a good return |
| **P2 4-year simulated paper-trade report** | the swing/portfolio path over the four-year tape, engine lane and cost lane, trade by trade | the only place where "we make money" could ever be measured |
| **P3 Synthetic hypothesis scenarios** | model-candle correctness, SNU declarations, overfitting-as-a-hypothesis-test, regime-shift cases | proves the engine itself is correct before any return is believed |
| **Ledger** | every run appends a version-resolved receipt to the hash-chained ledger | evidence that cannot be rewritten; regression needs a baseline |

## 3. P1 — gates feed the score

Gate states come from the resolver, never from prose: `PASS / BLOCKED / UNKNOWN / DEFEATED /
NOT_APPLICABLE / MISSING`. The gate factor is `PASS / required` with `required = 10` and the
per-gate state printed in the same row. G7 (prospective) and G8 (live realization) cannot be
bought with backtest evidence: they need elapsed shadow time and venue settlement.

## 4. P2 — the 4-year paper-trade report must carry these columns

Per run: campaigns, per-trade net with **fees, real funding and modelled slippage in
separate columns** (`execution_shortfall_measured` stays `MISSING` without real-fill records),
win rate per cost basis, exit-kind histogram, exposure, turnover, max drawdown,
hourly OHLCV-derived ADV/participation when available, and the **SNU ledger** (below).
Per trade: entry/exit instants and prices, quantity, the decision identity, the exit rule
that fired, and the attribution record of §6. The primary swing contract does not require
L2/depth or queue data; those captures are archived non-authoritative evidence.

## 5. P3 — synthetic scenarios must pass before any return is believed

1. **Model-candle correctness suite** (after *Correctness of Backtest Engines*,
   arXiv:1509.08248): adversarial candle patterns whose correct outcome is derivable by
   hand — gap through the stop, stop and target inside one bar, exact touch, open beyond the
   stop, expiry at the close, partial fill. An engine that fails any of these cannot report
   a return, whatever the tape says.
2. **SNU declaration** (after *Backtest of Trading Systems on Candle Charts*,
   arXiv:1412.5558): when candle data cannot decide the intrabar path the situation is
   **SNU — Situation Not Unique**. The engine must (a) count it, (b) print the declared
   resolution rule, and (c) never silently pick the flattering branch. Our current rule
   ("stop before target when one bar touches both") becomes a declared SNU resolution and
   every occurrence lands in the SNU ledger.
3. **Overfitting as a hypothesis test** (after arXiv:2209.05559): the probability of
   backtest overfitting is estimated and the family is *rejected* when it exceeds the
   declared threshold; scenarios run across assets and windows, including a crash window.
4. **Protocol stages** (after *AlgoXpert IS–WFA–OOS*, arXiv:2603.09219): in-sample
   plateau stability over single optima, walk-forward with purge gaps and
   majority-pass/catastrophic-veto gates, then a strict parameter-locked holdout. The
   post-validation report is **multi-objective** — the same variants ranked by Sharpe and by
   max drawdown, with rank reversal reported rather than hidden.

## 6. Attribution — why this trade lost (modelled on v8-core)

v8-core already reports failure the right way, and this contract copies it:

* **Disjoint failure domains with a conservation invariant**
  (`v8-core/src/system_proving/attribution.rs:10-18` — the canonical vocabulary):
  every losing trade is charged to exactly one
  domain — `DETECTION`, `REPRESENTATION`, `RECONCILIATION`, `SELECTION`,
  `ALLOCATION`, `EXECUTION`, `EXIT` — and `verify_conservation()` requires the domain counts
  to sum to the total failure count. A loss may not be double-counted or left unattributed.
* **Counterfactual oracle outcome** (`v8-core/src/oracle/authority.rs`): for each trade the
  report states whether the counterfactual was `identified`, `partially_identified`,
  `model_derived` or `unknown` — with `bounds()` and a `refusal_reason()` when the data
  cannot support an answer. "It lost because the stop was hit" is not attribution; "the same
  decision held 24 more bars would have returned X, bounds [a,b]" is.
* **Veto attribution** (`v8-core/src/analysis/veto_attribution.rs`): trades the system
  *refused* are reported with their reason, so the report shows what was avoided as well as
  what was lost.

## 7. The score (explicit formula, four factors always printed together)

```
readiness = 100 × gate_factor × pillar_factor × risk_factor × target_factor
gate_factor    = PASS gates / 10
pillar_factor  = measured pillars / 3            (P1, P2, P3; MISSING contributes 0)
risk_factor    = declared risk limits respected  (max DD, exposure, turnover, fee drag,
                                                   funding drag; any breach = 0)
target_factor  = min(1, protected monthly return / 10 %)  — diagnostic-only on any
                  window that is not protected, and then it contributes 0
```

The factors are printed as four separate numbers next to the result, every time, so the
composite can never be read as a single authority. The score is derived from measurements
only; nothing in the pipeline may set it directly.

## 8. Regression

* Baselines are pinned per pillar (gate vector, paper-trade metrics, scenario results).
* A new run computes per-pillar deltas against the pinned baseline; any drop beyond the
  declared tolerance yields verdict `REGRESSION` with the pillar and the delta named.
* The score may only *rise* through measured evidence. Re-baselining after a regression
  requires an entry in the decision register — a red suite is not "fixed" by moving the
  baseline.
* The existing ledger supplies the chain; a regression report is itself a receipt.

## 9. The central CLI surface (this is the interaction the owner asked for)

```
v8-next readiness                     # score + the four factors + gate vector + what is missing
v8-next run --pillar scenarios|paper-4y|folds|all
v8-next regression [--baseline <receipt-sha>]
v8-next explain --trade <trade-id>    # attribution: domain, oracle bounds, SNU flag
v8-next status                        # existing dashboard, extended with the score factors
```

`run` appends receipts; `readiness` and `regression` only read. No command may print a
return without the cost columns, the SNU count and the attribution summary beside it.

## 10. What this lock forbids

* A return quoted without its cost breakdown, SNU count and attribution.
* L2/depth data as an implicit requirement of the primary hourly swing benchmark.
* A score minted from anything other than the four factors above.
* Filling a missing pillar, gate or measurement with zero to make the score move.
* Re-baselining a regression without a decision-register entry.
* Presenting the target factor from an unprotected window.

## References

* Löw, Maier-Paape, Platen, *Correctness of Backtest Engines*, arXiv:1509.08248 — model
  candles and a correctness proof for candle-driven engines.
* Maier-Paape, Platen, *Backtest of Trading Systems on Candle Charts*, arXiv:1412.5558 —
  SNU: intrabar situations that candle data cannot decide, and the duty to warn.
* Gort et al., *Deep Reinforcement Learning for Cryptocurrency Trading: Practical Approach
  to Address Backtest Overfitting*, arXiv:2209.05559 — overfitting as a hypothesis test,
  rejected agents, crypto windows including crashes.
* Nguyen et al., *AlgoXpert Alpha Research Framework: A Rigorous IS–WFA–OOS Protocol for
  Mitigating Overfitting in Quantitative Strategies*, arXiv:2603.09219 — plateau over
  optimum, purge gaps, majority-pass and catastrophic-veto gates, parameter-locked holdout,
  multi-objective post-validation report with rank reversal.
* v8-core (oracle reference, read-only): `src/system_proving/attribution.rs` (disjoint
  failure domains, conservation), `src/oracle/authority.rs` (identified / partially
  identified / model-derived / unknown + bounds + refusal), `src/analysis/veto_attribution.rs`,
  `src/audit/full_audit.rs`, `src/benchmark/report.rs`.
