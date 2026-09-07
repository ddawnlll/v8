# #71 Gap-asymmetry conservatism budget — protocol note (no new numbers claimed)

Source of numbers: issue #71 body only (BTCUSDT 1h: TR>(H−L) bars 64/8759 = 0.7%;
AVAXUSDT 1h: 1.1%). No re-measurement is claimed here.

## What Rust already enforces

- Fills are symmetric at the declared barrier: `v8-core/src/simulator.rs:22-23`
  and `:278`; asymmetry discussion anchored at `:1150`.
- The Python `simulator.py:403-409` asymmetry (STOP = worse-of barrier/open,
  TARGET = exact barrier) has no counterpart in the Rust execution path.

## What "conservatism budget" would mean (protocol, for a future preregistered run)

1. Take the sealed Rust ledger for a frozen config over the certified quad tape.
2. Recompute the same ledger with `target_fill = max(target, open)` (LONG;
   mirror for SHORT) — i.e. credit favorable gaps at the open instead of the barrier.
3. Report Δ = recomputed_net − sealed_net in R and in bps, per symbol and per
   volatility regime (liquidation-cascade bars flagged separately, since the
   conditional distribution of gaps is not uniform — issue #71).
4. Record the result in `SIMULATION_TRUTH_SPEC` as a signed conservatism budget,
   not as a performance claim. Verdict stays `NO_ECONOMIC_CLAIM` either way
   (Constitution Rule 12).

## Why this is queued, not executed, in this lane

Step 2–3 is a real experiment: it needs a preregistered config, a frozen tape
revision, and a receipted run (`usdm-sim` + artifact hashes). Running an ad-hoc
variant and pasting the delta here would be exactly the unregistered-shadow-analysis
pattern AGENTS.md §8 prohibits. The protocol above is the autonomous contribution;
execution awaits a registered work item with R# traceability.
