# V8 Hypothesis Lab Protocol v0.1

**Purpose:** cheaply reject weak behavior hypotheses before learned routing,
scoring, ranking, richer data or execution learning. **Status:**
PROVISIONAL_DECISION; thresholds are experiment-specific and must be
preregistered, never tuned after inspecting the frozen holdout.

## Hypothesis record

Each H1–H8 record contains: formal null/alternative; economic mechanism or an
explicit `mechanism unknown`; behavior and deterministic detection rule; universe
as-of membership; data/source manifest; decision/knowledge/availability clocks;
canonical geometry and costs; dependence unit; primary metric; test; minimum
event/asset coverage; development/frozen partitions; and rejection consequence.

The four screening states are: `NO_OPPORTUNITY`, `HINDSIGHT_ONLY`,
`WEAKLY_SELECTABLE`, `FORMALIZATION_CANDIDATE`. They are labels for the stated
experiment, not market truths. The oracle statistic `E[max(U_long,U_short,0)]`
is forbidden as evidence of selectable edge because it chooses direction after
the outcome.

## Cheap-to-expensive ladder

| Stage | Question | Required control | Output |
|---|---|---|---|
| Screening | Is a fixed detector distinguishable from null after costs? | chronology, conservative Level-1 simulation, simple null | reject/replication proposal |
| Replication | Does it persist by asset/time regime? | untouched chronological slice, block bootstrap | replicated or reject |
| Promotion | Does an add-on beat the simpler fixed baseline? | paired OOS difference, multiplicity control | admit/defer/reject component |
| Shadow/live | Does the paper result survive operational reality? | frozen code/data + realized ledger | operational evidence only |

Use blocked time splits, with purging/embargo only when labels/holding intervals
overlap training observations. Block or stationary bootstrap at a declared
dependence unit (at least day/session; longer if autocorrelation dictates) gives
uncertainty without assuming IID trades. Permutation must preserve volatility and
time structure where the null requires it (e.g. block/sign or direction scramble),
and must not shuffle away the structure being tested. Candidate-overlap and
cross-asset dependence require cluster-aware summaries or a hierarchical model;
do not present naive trade-level t statistics.

## Baselines and gates

Every behavior starts with: no-trade; deterministic raw candidate; same candidate
under cost stress; direction/label-scrambled control; and, where a global model is
claimed, an equal-information global baseline. All geometry/cost choices are fixed
before frozen OOS. A pass requires its preregistered net-utility effect, uncertainty
interval/test, operational validity, and replication conditions. A fail/insufficient
event count blocks downstream component work; it does not prove the opposite
market hypothesis.

Multiple explored Expert variants form a family: report all trials, control FDR or
apply a Reality Check/SPA-style family comparison as appropriate, and reserve a
final untouched evaluation. Deflated Sharpe and PBO are diagnostics for selection
bias, not substitutes for a frozen holdout or an economic model.

## Attribution validity gate

V8 already fails closed on **data** (an unavailable input rejects the state) and
on **authority** (a missing receipt blocks an economic verdict, `V8_CONSTITUTION`
rules 8–9). It has had no equivalent guard on **attribution validity**: whether
the population a report measured is the population the ledger actually traded.

Deterministic admission makes this a structural, not accidental, risk. Once the
exposure rule and the portfolio heat cap (D-023) are enforced against a stepped
ledger, rejection is the *designed* outcome for most simultaneous Candidates —
and in a universe whose instruments correlate 0.8–0.95, cluster caps bind often.
A run can therefore compute after-cost statistics over a candidate population
that is overwhelmingly counterfactual, and report them as though a portfolio had
been traded. Nothing currently blocks that verdict.

**D-027 — every `LabReport` carries `execution_share` and a divergence
statistic, and both gate the economic verdict.**

```text
execution_share = n_executed / (n_executed + n_portfolio_rejected)
```

The denominator counts only **portfolio-state rejections** — `CAPACITY_REJECTED`
with `EXISTING_EXPOSURE_CONFLICT` or `PORTFOLIO_HEAT_EXCEEDED`. Rejections that
express the strategy itself (cost gates, invalidation, expiry) are not selection
bias; they are the hypothesis. Conflating the two would make the gate fire on
healthy runs and teach the operator to ignore it.

Verdict rules, all preregistered before the frozen slice is opened:

| Condition | Verdict |
|---|---|
| `execution_share` below the declared floor | `ATTRIBUTION_UNSAFE_LOW_COVERAGE` |
| executed vs portfolio-rejected `net_R` distributions diverge beyond the declared threshold | `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE` |
| both within declared bounds, authority receipt present | economic verdict permitted |

An `ATTRIBUTION_UNSAFE_*` verdict is **not** a failed hypothesis and must never
be reported as one. It states that this run cannot support an economic claim in
either direction, exactly as a missing authority receipt does. The correct
responses are to widen capacity, narrow the universe, or reduce Expert overlap —
never to reinterpret the counterfactual population as a traded one.

**Why a refusal rather than a correction.** The honest correction for a logged
population selected by a deterministic policy is off-policy evaluation, and OPE
needs action propensities that a deterministic admission rule does not produce
(a rejected Candidate had probability 0, not a small probability — the
deficient-support case). Independent searches of the OPE and competing-risk
literature returned no admissible finance application and no method valid under
deterministic filtering; that gap is recorded rather than papered over
(`EVIDENCE_MATRIX`, `OPEN_DECISIONS` O-014). Where the bias cannot be corrected,
the program's own rules require declining the claim, not estimating through it.
This gate is therefore a validity guard in the family of rules 8–9 — it adds no
component to the decision path and does not touch the complexity budget
(rule 14).

Cheap tests:

* A run whose Candidates are all heat-rejected returns
  `ATTRIBUTION_UNSAFE_LOW_COVERAGE`, never a net-utility figure.
* Shrinking the universe until conflicts vanish raises `execution_share` and
  restores an ordinary verdict on the same tape.
* Removing the authority receipt still blocks first: authority and attribution
  are independent gates, and neither substitutes for the other.

## Sources and scope

* **LITERATURE_SUPPORTED:** White’s Reality Check addresses data-snooping across
  a tested rule family; Hansen’s SPA improves practical behavior for weak/poor
  alternatives ([White 2000](https://doi.org/10.1111/1468-0262.00152),
  [Hansen 2005](https://doi.org/10.1198/073500104000000631)).
* **LITERATURE_SUPPORTED:** stationary bootstrap resamples dependent series in
  blocks ([Politis & Romano 1994](https://doi.org/10.1080/01621459.1994.10476870)).
* **LITERATURE_SUPPORTED (limited):** deflated Sharpe adjusts for non-normality
  and selection/backtest-overfitting risks; its assumptions and trial count must
  be disclosed ([Bailey & López de Prado 2014](https://doi.org/10.3905/jpm.2014.40.5.094)).
* **PROJECT_EVIDENCE_SUPPORTED:** V7’s day-clustered uncertainty and scrambled
  direction control found its stated P1 setting failed; that result is not evidence
  about V8 Experts (`PROJECT_EVIDENCE_AUDIT.md`).
