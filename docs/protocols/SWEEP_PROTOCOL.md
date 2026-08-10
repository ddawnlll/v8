# Variant Sweep Protocol — adaptive search under anytime-valid error control

**Status:** PROVISIONAL_DECISION (D-086). This protocol admits **variant
sweeps** — evaluating many parameterizations of a behaviour family rather than
one hand-declared variant — and specifies the only conditions under which they
are admissible. It is LITERATURE_SUPPORTED in its statistical machinery and
DESIGN_INFERENCE in its application to V8; nothing here is evidence of edge and
the verdict remains `NO_ECONOMIC_CLAIM` (rule 12).

## 1. Why sweeps were excluded, and what changed

V8 has so far declared variants by hand and registered the search universe
before the run: D-076 recorded `search_universe_size` = 2; D-074 deliberately
used a round pre-declared threshold (`bb_pct_b < 0.70`) rather than the four
fitted per-symbol values, precisely to avoid re-fitting into a challenger.

That discipline is correct and the reason is arithmetical. Bailey, Borwein,
López de Prado & Zhu show that on five years of daily data, **no more than ~45
strategy variations** can be tried before a Sharpe ratio of 1.0 arises by
chance alone (the Minimum Backtest Length result). A naive sweep over thousands
of variants does not merely weaken inference; it guarantees a false positive.

Two obstacles kept sweeps out:

1. **Multiplicity.** Bonferroni over thousands of variants annihilates power;
   BH requires independence or positive dependence that sweep variants — all
   reading the same tape, sharing candidates — plainly violate.
2. **Adaptivity.** Any compute-efficient sweep must kill losing variants early.
   Early elimination is peeking plus selection, which invalidates fixed-sample
   inference. So the statistically safe sweep was the computationally
   impossible one, and vice versa.

Recent work removes both obstacles with **one** object. Under e-values:

- FDR control holds under **arbitrary dependence** between hypotheses
  (e-BH: Wang & Ramdas, *False discovery rate control with e-values*,
  arXiv:2009.02824).
- FDR control holds for **arbitrary exploration rules and arbitrary stopping
  times**, including bandit-style adaptive querying of arms
  (Xu, Wang & Ramdas, *A unified framework for bandit multiple testing*,
  NeurIPS 2021).

The consequence for this program is the whole reason to adopt them: **adaptive
compute allocation and valid inference stop being in tension.** Successive
halving over variants — normally a selection crime — becomes licensed, because
an e-process is safe under optional stopping and continuation.

## 2. Structure of an admissible sweep

```text
declared variant grid  V  (registered before any evaluation)
        │
        ▼
stage 1: every v in V on a short chronological slice
        │   e-process per variant accumulates evidence
        ▼
eliminate / promote  (successive halving; exploration rule is free)
        │
        ▼
stage k: survivors on progressively longer slices
        │
        ▼
stopped e-BH over all variants  →  FDR-controlled discovery set
        │
        ▼
confirmation half, queried exactly once   (unchanged from D-072)
        │
        ▼
DSR / PBO diagnostics reported alongside every surviving variant
```

Each variant is one arm and one hypothesis. The null is declared per campaign —
typically `H0: mean net_R(v) <= mean net_R(baseline)` against the family's
existing registered variant, not against zero, so a sweep must beat what it
proposes to replace.

## 3. Requirements

| # | Requirement |
|---|---|
| S1 | The variant grid `V` is **declared and registered before any evaluation**. `search_universe_size = |V|` enters the register (D-046), and the sweep may not be widened mid-campaign; widening starts a new campaign with its own alpha |
| S2 | Evidence per variant is an **e-process**, not a p-value. The construction is declared in the campaign contract |
| S3 | The final rejection set is produced by **e-BH on the stopped e-processes**, giving FDR control under arbitrary dependence between variants |
| S4 | The **exploration/elimination rule is unconstrained** but must be recorded, so the campaign is reproducible; validity does not depend on it, reproducibility does |
| S5 | **MinBTL pre-check:** before the grid is registered, the maximum admissible trial count for the available tape length is computed and reported. A grid exceeding it is refused, not discounted |
| S6 | The confirmation half remains untouched during the entire sweep and is queried **exactly once** for the surviving set (unchanged from D-072) |
| S7 | Every surviving variant is reported with a **Deflated Sharpe Ratio** using the registered `search_universe_size`, and a **PBO** estimate via combinatorially symmetric cross-validation |
| S8 | Across campaigns, alpha is spent under an **online** procedure (online e-BH / SAFFRON-class), so campaign *n+1* cannot silently reuse the budget of campaign *n* |

S7 is diagnostic, not a gate: DSR and PBO are reported to make selection-driven
inflation visible in the finance literature's own vocabulary, and a poor PBO is
grounds for scepticism, not automatic rejection.

## 4. The local/global filtration trap

This is the one condition most likely to be violated silently in V8, and it is
stated here so it is checked before a campaign rather than after.

The stopped e-BH result (*Anytime-valid FDR control with the stopped e-BH
procedure*, arXiv:2502.08539) shows that stopping several e-processes at a
**common** stopping time yields e-values only if the processes and the stopping
time live in the same **global** filtration. E-processes are typically
constructed **locally**, per hypothesis. When streams are dependent, a local
e-process need not be global, and the FDR guarantee fails — information leaks
across streams, one stream effectively learning its own future from another's
past.

**Every V8 sweep variant reads the same tape.** The streams are therefore
dependent by construction, and the naive design — build an e-process per
variant, halve them all at a shared global stopping time — is exactly the
unsafe case.

Two admissible resolutions, one of which must be declared per campaign:

1. **Verify the causal condition.** Show that each variant's e-process update
   at step *n* depends only on that variant's own history and on shared data
   available before *n* — i.e. no unobserved confounding from the past across
   streams. Under that condition local e-processes are global and stopped e-BH
   is valid.
2. **Use variant-local stopping times.** Stop each variant's process on its own
   local rule and apply e-BH to the stopped values. This is always safe, at the
   cost of forbidding stopping decisions that depend on the e-BH output itself
   (no "stop once k variants are rejected").

Resolution 2 is the default. Resolution 1 requires an argument in the campaign
contract, not an assertion.

## 5. Compute consequence

Successive halving changes the sweep's cost from
`O(|V| x full-tape cost)` to roughly `O(|V| x short-slice + log|V| x full)`.
For a 1,000-variant grid this is a one-to-two order of magnitude reduction, and
it composes with the content-addressed DAG cache (D-085): extending a surviving
variant's window is incremental, since its earlier cells are already keyed and
stored.

This matters for the substrate decision. The GPU trigger in
`COMPUTE_SCHEDULING_SPEC` §6 is ~10^9 replay cells, and the naive full-grid
sweep was the only configuration projected to reach it. Under this protocol a
sweep of the same nominal cardinality lands one to two orders of magnitude
lower, i.e. back inside the range a multicore CPU backend serves.

**The statistically correct design is also the cheap one.** That is the reason
to adopt it, and it is why O-028 resolves as it does: sweeps are admitted, and
admitting them does not force experts native from stage S1 nor reopen the GPU
question.

## 6. What stays open

The e-process **construction** for block-dependent financial episode streams is
not settled by this protocol and is the live research item. V8's existing
machinery estimates dependence through block bootstrap
(`select_block_size`, `effective_independent_episodes`), which is a
fixed-sample device; an anytime-valid analogue must be chosen and justified —
betting-style test martingales on block-aggregated episodes are the obvious
candidate, but the mapping from `select_block_size` to a martingale
construction is unproven here. Until it is declared and tested, a sweep
campaign may not run. This is `OPEN_QUESTION`, tracked as O-032.

## 7. Cheap executable tests

1. **Null calibration:** on a detrended / label-shuffled tape where no variant
   has an edge, the sweep's realized FDR over repeated campaigns is at or below
   the declared level.
2. **Adaptivity invariance:** two runs with different elimination schedules over
   the same grid and tape both control FDR; the discovery sets may differ, the
   guarantee may not.
3. **Grid immutability:** widening `V` mid-campaign is rejected by the runner,
   not merely warned about.
4. **MinBTL gate:** a grid larger than the tape admits is refused with the
   computed ceiling in the message.
5. **Confirmation single-query:** a second query of the confirmation half for
   the same slice is a hard error.
6. **Filtration declaration:** a campaign contract that declares neither
   resolution in §4 fails to start.
7. **Online budget:** campaign *n+1* run with the same alpha as campaign *n*,
   without the online procedure, is refused.

## 8. Evidence and citations

- **LITERATURE_SUPPORTED:** e-BH and FDR control under arbitrary dependence
  (Wang & Ramdas, arXiv:2009.02824); bandit multiple testing with e-processes
  under arbitrary exploration and stopping (Xu, Wang & Ramdas, NeurIPS 2021);
  online e-BH / SupFDR at data-adaptive stopping times (Fischer & Ramdas,
  arXiv:2407.20683); the local/global filtration condition (arXiv:2502.08539);
  online FDR alpha-investing (SAFFRON, Ramdas, Zrnic, Wainwright & Jordan,
  arXiv:1802.09098; ADDIS, arXiv:1905.11465); MAB + online FDR
  (Yang, Ramdas, Jamieson & Wainwright, NeurIPS 2017); successive halving for
  non-stochastic best-arm identification (Jamieson & Talwalkar,
  arXiv:1502.07943); Deflated Sharpe Ratio (Bailey & López de Prado, JPM 40(5),
  2014); PBO via CSCV and the Minimum Backtest Length result (Bailey, Borwein,
  López de Prado & Zhu); multiple-testing haircuts for strategy evaluation
  (Harvey & Liu, *Evaluating Trading Strategies*).
- **DESIGN_INFERENCE:** the campaign structure in §2, requirements S1-S8, the
  choice of resolution 2 as default in §4, and the compute projection in §5.
  None of it is measured in this repository yet.
- **Not claimed:** that any sweep will find anything. This protocol governs how
  a search is priced, not whether a search succeeds; and a sweep that survives
  every gate here still produces a MODEL_DERIVED result under an uncertified
  simulator.
