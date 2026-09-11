# Revision 3 — engine ↔ decision-plane reconciliation, small real window

Same policy (`plain_swing`), tape (`multi-1h-4y`), warmup (declared 49), window
(2025-01-01 → 2025-02-01, 840 bars including 96 of history), instrument
(`BTCUSDT-PERP.BINANCE`) and capital identity (10 000 USDT, 1 % risk) on both lanes.
Artifact: `engine_replay_reconciliation.json` sha256 `61a8cce9…`.

## Measured

| | engine lane | decision-plane replay |
|---|---|---|
| campaigns | **3** | **29** |
| fills | 6 | — (return-based) |
| positions closed | 3 | — |
| open at end | none | — |

Campaign matching by decision instant:

| status | count |
|---|---|
| RECONCILED (no divergence) | 1 |
| DIVERGENT | 1 |
| REPLAY_ONLY_CAMPAIGN | **27** |
| ENGINE_ONLY_CAMPAIGN | 1 |

Divergence classes observed: `EXIT_TIME_DIVERGENCE` ×1,
`EXIT_PRICE_BEYOND_ONE_TICK` ×1, `EXIT_KIND_DIVERGENCE_BRACKETLESS_ENGINE` ×1. The residual
resting order `O-20250129-210000-001-000-7` is published: the stop filled on the last bar,
so the engine had no further event with which to process the sibling cancellation. It is an
end-of-data artefact, not a hidden position — and it is now reported by
`orders_open_at_end` instead of being assumed absent.

## What this reconciliation establishes

**Coverage is where the two models part company, not prices.** One campaign matched
exactly, one diverged at the exit, and **27 decisions exist only in the replay**. That is
the bracket-contract difference expressed in campaign counts, and it is the honest
statement of the open question:

* under the replay's current contract (bracketing decided by the *policy's name*), every
  decision becomes a one-bar round-trip at its own entry reference — 29 campaigns, gross
  ≈ 0, net ≈ the fee bill;
* under the engine's contract (bracketing decided by the *decision*), a decision that
  formed no protection is held to its expiry — 3 real positions that take risk, and the
  engine is occupied while they are open, so it does not act on the decisions the replay
  pounces on.

Neither number is an economic claim, and neither may be abandoned to make the two agree.
What the reconciliation says today is: **the family's registered result is a statement about
the bracket contract, not about the strategy**, because the contract choice changes the
campaign count by an order of magnitude on the same window.

## Tolerances and their basis

Price: one tick (0.01). Size: one lot (0.001). Time: one bar. A price beyond one tick, an
exit at a different instant, or an engine exit with no bracket leg filled is reported as a
divergence class rather than folded into an average. The replay is return-based over unit
notional, so quantities are not comparable line by line; cash flow is published per lane.

## Still missing (next increments)

* The four-fold run under this reconciliation (NX09's fold windows and purge), not just the
  single January window.
* Engine-lane regression tests over the adapter's semantics (bracket sibling cancellation,
  bracketless insertion, timeout close, leftover-order reporting).
* Funding on the engine lane: the simulated venue charges maker/taker fees, but funding is
  not fed to it, so the engine's cash flow and the cost lane's funding column are not yet
  comparable line by line.
* The owner's decision on the bracket contract (reading A vs reading B) — the reconciliation
  reports both; it does not choose.
