# V8 Simulation Truth Specification v0.1

**Status:** LOCKED_INVARIANT candidate for semantics; economic certification is
currently blocked by the V7 authority described in `PROJECT_EVIDENCE_AUDIT.md`.
No simulation outcome is asserted here.

## Fidelity ladder and permitted claims

| Level | Truth source | Permitted use | Forbidden claim |
|---|---|---|---|
| 0 | future path/geometry | label research, no fills | executable PnL |
| 1 | causal OHLC/bar events | fixed market-style entry/exit studies | intrabar path or queue priority |
| 2 | trade/tick replay | latency-aware aggressive fills where data supports it | order-book queue position |
| 3 | sequenced L2 + calibrated order/fill data | passive/partial-fill studies | uncalibrated queue/maker fills |

Use the lowest level that can falsify the hypothesis. V8 starts at **Level 1**;
**Level 0** may never support an executable-PnL claim, and **Level 3** is not a
roadmap entitlement. A simulation report binds dataset manifest,
source quality, simulator code hash, configuration hash, seeds, order/fill ledger,
and output hash.

## Units, excursions, and ambiguity

**R is a declared price distance, not a price ratio (D-028).** `stop_r`,
`target_r`, `net_r`, and `round_trip_cost_r` are multiples of one `risk_unit`,
which the Expert's frozen geometry declares explicitly (`atr_ref`, else a
declared `risk_frac` of entry). A non-positive unit is a contract breach and
fails closed. Consequences that are not optional:

* a stop-out is exactly `-1R - cost` for every instrument and stop width;
* outcomes from different geometries are comparable, so a family-level
  summary is meaningful rather than a mixture of unlike quantities;
* portfolio heat (D-023) sums a risk-normalised quantity, which is the only
  reading under which "heat" means risk rather than position count.

Expressing an outcome as a fractional price return while naming it `R` is the
error this rule exists to forbid: it silently rescales every result by the stop
width, understating cost for tight geometries and overstating it for wide ones,
and it makes the heat cap indifferent to actual risk.

**Every position carries `mae_r` and `mfe_r`** — running maximum adverse and
favourable excursion in R, recorded before any exit decision. This is not a
convenience metric. The V7 audit measured excursion ICs of +0.124 and +0.152
against a signed-return IC of +0.015: path magnitude was the only quantity that
campaign found materially predictable. A simulator that reports the exit value
and discards the path throws away the evidence needed to decide whether
post-entry management is worth adding at all (O-013), and the vendored V7
simulator already records both.

**Same-bar ambiguity is counted, not just resolved.** `STOP_FIRST` decides the
exit; `ambiguous_bars` records how many bars needed that decision. Without the
count there is no way to state how much of a result rests on an assumption the
bar data cannot settle.

## Canonical Level-1 event order

1. Ingest only ordered source events; reject a data/sequence gap.
2. At `decision_time`, freeze `MarketState`; Expert and candidate decisions see no
   later data.
3. Create an order only after the candidate's recorded acceptance event.
4. Submit at declared `submission_time`; earliest bar fill is the next eligible
   bar open unless a higher-fidelity source makes another time observable.
5. Apply predeclared funding ordering (`SETTLEMENT_BEFORE_ORDERS` initially),
   fees/slippage per leg, then account/position mutation exactly once.
6. For a bar touching both stop and target, record ambiguity and use `STOP_FIRST`.
   Gap-through market exits fill at the opening price; a timeout exits at its
   declared event; tape end closes or marks censorship exactly as preregistered.
7. Emit immutable order, fill, position, funding, cost and terminal-ledger events.

Partial fills, cancellation and passive limits are unsupported at Level 1 and
must fail closed. Randomization, if used for stress, is seeded, logged and never
the undisclosed default. Distinguish exchange event time, receive/availability
time and simulator processing order.

## Required golden and differential tests

* same-bar stop/target, gaps, timeout boundary, entry-bar counting;
* funding exactly on start/end boundaries and full-tape versus window replay;
* fees/slippage on both legs and accounting/NAV reconciliation;
* no-trade and zero-fill provenance; missing data fail-closed;
* deterministic replay/hash equality for same tape/config/seed;
* scalar reference versus accelerated replica parity before accelerated economics;
* Level N must not silently supply a Level N+1 semantic.

These align with existing `v7/lab/sim.py` semantics and audit finding that a <!-- AUDIT-DOC-PATHS: FOREIGN_REPOSITORY `v7/lab/sim.py` belongs to the audited V7 materials, not to this repository tree. -->
funding terminal-boundary defect required differential replay. They are
**PROJECT_EVIDENCE_SUPPORTED engineering controls**, not market evidence.

## Evidence boundary

Event-driven execution matters because signal, submission, fill and position
events have different times; assuming their simultaneity creates look-ahead and
fill bias. This is a simulation-design fact, not a claim that V8 can trade.
The numerical policies above are deliberately conservative design choices.

## Conservatism budget (issue #71): the gap asymmetry

The stop-fill policy — a stop fill uses the WORSE of the barrier and the bar
open, while a target fill is exactly the barrier — is conservative by design,
but the two-sided gap asymmetry is a MEASURED cost, not a free assumption.
On a synthetic +30/−30 unit gap around a 1R barrier (atr=10, stop/target 1R):
an adverse −30 gap books −3.07R (STOP at open) while a favorable +30 gap books
+0.93R (TARGET at barrier), a **3.30R asymmetry**. This is the conservatism
budget the policy spends on adverse gaps and forgives on favorable ones.

The asymmetry is negligible on the current real tape — the dev window
(`btcusdt-1h-12m`, 2,500 bars) shows TR > (H−L) on 0.6% of bars and
`open == prev_close` on 51.7% — but it concentrates in illiquid symbols and
high-volatility regimes (liquidation cascades), so it must be re-measured per
symbol/interval before any economic reading leans on gap-heavy windows.
