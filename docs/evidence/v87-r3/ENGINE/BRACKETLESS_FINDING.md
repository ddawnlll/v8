# Revision 3 — engine lane: the swing family was stopped out at its own entry reference

**Status:** diagnostic finding from the engine lane, on a real window. Revision 1 and 2
evidence is untouched. No number here is an economic claim.

## What the engine lane forced into the open

The Nautilus adapter (`adapters/swing_engine.py`) inserts a decision as a market entry and
sizes it from the stop distance. On the real window 2025-01-01 → 2025-01-08 (264 bars,
96 bars of history, `plain_swing`, warmup 49) **every one of the 11 decisions carried
`stop_price == entry_reference`**: the squeeze protection did not form, so the decision has
no bracket and no risk distance.

Two consequences, both measured:

1. The replay (`replay_bracket`) decides bracketing from the **policy's name**
   (`has_bracket = protection_policy not in (None, "timeout-only-v1")`), not from the
   decision. A bracketless decision therefore enters the bracket branch, where
   `stop_touched = candle.low <= decision.stop_price` is true as soon as the next bar dips
   below the previous close — with `stop_price == entry_reference` that is a stop-out **at
   the entry price on the very next bar**.
2. That is exactly what the family's frozen measurement reports: `plain_swing` records
   `30 STOP / 1 TARGET`, `holding_median = 1` bar, `gross ≈ 0` and `net = −0.031358`,
   which is **precisely the fee bill** for 31 campaigns (31 × 2 × 0.0005 = 0.031000). The
   "STOP" column in NX06/NX09 is therefore not describing protective stops; it is
   describing instant round-trips at the entry reference.

The engine lane surfaced this by refusing the same decision: with a zero risk distance
there is no quantity to size, which is how a degenerate bracket became visible instead of
being averaged into a return.

## What the engine lane does instead (declared, per decision)

`ENGINE_LANE_SEMANTICS` now states that bracketing is decided **per decision**:
`stop_price == entry_reference` means no protection formed, so the position is inserted
**unprotected** and held to its declared expiry (336 bars for the squeeze protection),
never stopped out at its own entry. Sizing falls back to the declared notional divided by
the entry reference, and the basis (`STOP_DISTANCE` or
`DECLARED_NOTIONAL_AT_ENTRY_REFERENCE`) is recorded per campaign.

Measured on the same window with that contract: 2 decisions inserted, 1 fill
(`OrderInitialized → OrderSubmitted → OrderFilled`), position opened at the entry and held
open at the cutoff — one campaign that actually takes risk, instead of 11 instant
round-trips.

An earlier version of this adapter sized the unprotected decision as
`risk_notional / 1` (100 units of BTC ≈ 9.5M USDT notional) and the engine's risk model
denied the order (`OrderDenied`). That was a real defect in the adapter, found by the
engine and fixed; it is recorded here rather than quietly corrected.

## The two readings, kept apart (not reconciled away)

* **Reading A — the replay's current contract:** a policy that declares a protection is
  always treated as bracketed; a decision whose protection did not form stops out at its
  entry. The family's measured result stands as recorded: it loses, in 7 of 8 fold-symbol
  cells, and the loss is a fee bill.
* **Reading B — the engine's contract:** bracketing is a property of the decision. The same
  decisions become unprotected positions held to expiry, which take real risk, and their
  result is unknown until the four folds are run under this contract.

Which reading the pre-registered family should carry is an owner decision, because it
changes the interpretation of the registered result rather than its arithmetic. The
reconciliation tool must report the difference as a declared divergence class
(`BRACKET_CONTRACT_DIVERGENCE`) with per-campaign detail; neither reading is to be deleted
to make the two models agree.

## Still missing after this revision

* The engine–replay reconciliation tool: per-campaign comparison of entry/exit time and
  price, quantity, cash flow and position state, with tolerances tied to the instrument's
  tick (0.01) and lot (0.001) — and the divergence table that names Reading A vs Reading B.
* Partial-fill coverage on a window where the engine actually fills more than once.
* The four-fold run under the engine lane (small window first: this note).
* Funding/slippage on the engine lane: the engine's simulated venue models fill and fee;
  funding is not fed to it yet, so the engine lane's cash flow and the cost lane's totals
  are not yet comparable line by line.
