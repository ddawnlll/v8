# V9 Implementation Plan — Product-First, Evidence-Gated

**Status:** `NOT_STARTED / V9-ARCH-RFC-1.4 CANONICAL TARGET / IMPLEMENTATION UNVERIFIED`.

**Only normative architecture:** [V9_ARCHITECTURE_MONOGRAPH.md](V9_ARCHITECTURE_MONOGRAPH.md). This plan is *derived* from that file; in case of ambiguity its ``A–B, 4–12, 16–17` product and native safety contracts control. Do not fetch absent `V9_ARCHITECTURE_MONOGRAPH_v1.md`. The historical original lives in Git provenance, not as a second authority.

**Success is a genuinely continuous adaptive trader:** multi-horizon belief, 28 expert candidates, canonical opportunity reevaluation, unified flat/open decisions, position thesis, competing opportunities and capacity. **V0 parity and a single entry veto cannot close the V9 product.**

| Milestone | Scope | Evidence / exact closure |
|---|---|---|
| **M0 Foundation & Safety** | Pin actual V8 strategy/config/SHA/rc4 and code symbol map; legacy-gate parity; used-path cancel/partial-fill/stop/idempotency, funding/mark/equity and #491 producer qualification | Native `DEC/ORD/POS` fixture, independent two-campaign oracle, duplicate/crash/`BLOCKED` protection tests, claim-scoped gate verdicts. No live proof asserted |
| **M1 Market & Expert Intelligence** | `MarketBelief` PIT multi-horizon view, event-driven invalidation and uncertainty; **28 existing experts inventoried** and adapted to context stance/support/contradict/abstain, dependency dedup | All 28 classified `INVENTORIED/EXECUTABLE/INCOMPATIBLE_WITH_REASON`; synthetic changed-regime tests, clone invariance, 0 native side effects |
| **M2 Continuous Trader Brain** | One canonical OpportunityBook with recurrent immutable evaluations; one unified TraderDecisionPolicy producing `WAIT ENTER HOLD REDUCE EXIT ABSTAIN`; active PositionThesis; portfolio constraints | `V9-INT-001..006` E2E scenario with market/expert/opportunity/position/portfolio feedback, determinism and **no native adaptive orders**; `V9_INTEGRATED_SHADOW_VERIFIED` |
| **M3 Adaptive Trade Management** | Price-bounded entry, position HOLD/REDUCE/EXIT/amend candidates, context-aware expert policy and constrained portfolio allocation | Each candidate default-off, individual prereg, native risk/stop/qty/venue tests; 20 USDT symbol-specific feasibility with rejects |
| **M4 Integrated Validation** | Integrated joint policy, interaction-aware replay, matched baseline/cash/no-trade/raw thresholds, full fee/slippage/funding/mark and same-capital equity; OOS and shadow | `V9_INTEGRATED_ECONOMICALLY_EVALUATED` or honest `NO_EDGE/INCONCLUSIVE/BLOCKED`. No production authority without separate qualification |

## Critical dependencies — separate code from live permissions

**M0** used-path safety is required before any newly activated native risk; **M1/M2 read-only or synthetic shadow** work may progress without waiting for unrelated economic claims to qualify. M3 policy families and M4 economic comparison require the *relevant* `claim × producer × dataset × execution_profile` gates and a pinned native replay. A single failed mark/equity producer cannot be bypassed by choosing a convenient alternate.

A V8 legacy decision callback that already writes state must **not** be invoked twice as a “pure V0” wrapper. Existing native order execution remains a single writer. A `BLOCKED` state stops new risk and blind retries but does **not** stop existing protective order/fill events and bounded read-only reconciliation. Native `NOT_FOUND` alone is not proof no order was ever submitted.

## Initial vertical proof — no orders

Start with a deterministic event tape: two symbols with 15m/1h/4h completed bars, one open native-like position, two competing opportunity IDs, qualified and contradictory expert stances, and changed regime/volatility. Demonstrate: (a) MarketBelief changes with new PIT data, (b) 28-expert manifest processes relevant experts with typed abstain, (c) opportunity evaluation updates, (d) position thesis changes but history remains immutable, (e) portfolio capacity affects reasons, (f) full replay has identical decision IDs and **zero native adaptive orders**.

## Issue creation protocol

First agent runs **READ-ONLY** and returns pinned code symbol inventory, a product-to-source traceability table, the M0–M4 issue dependency graph and **10–15 actionable first issues**. Include owner, touched path, preconditions, acceptance fixture, no-go evidence, and blocked classification for each. No code or issue/milestone writes without owner review. Afterwards **one issue → one focused agent PR → independent fixture/audit**. Merge order follows actual dependencies, not the agent's convenience.

## Invariants for all issues

- Single authority for native risk, execution, order ID and protected exposure; no exchange exactly-once assumption.
- Only PIT-available information and event-driven deterministic idempotent policies; `STOP-FIRST` is a bar-only diagnostic convention.
- Funding, fees, marks, realized/unrealized, margin and native fills must reconcile before related net equity claims.
- Sealed final OOS physically inaccessible to autonomous agent worktrees; preregister trials, keep failures and `NO_EDGE`.
- No live LLM in trading callbacks, no automatic agent promotion, no forced 28-expert consensus or false calibration.
- **No V9 acceptance from V0 parity + a single veto.** Integrated shadow product proof is mandatory.
- 20 USDT altcoin min-notional/quantization/liquidation must be symbol-specific and fail closed; no policy-risk rounding up.
