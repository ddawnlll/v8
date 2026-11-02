# V9 Implementation Plan — Evidence-Gated

**Status:** `NOT_STARTED`. This plan schedules work; it is not implementation,
validation, or economic authority. The normative architecture is
[`V9_ARCHITECTURE_MONOGRAPH.md`](V9_ARCHITECTURE_MONOGRAPH.md) (v1.1).

Each phase is closed only by its evidence gate. A green unit test is not a
venue-safety certificate, and a mechanical pass is not an economic result.
Unmet gates are recorded as `BLOCKED` in [`../V9_BACKLOG.md`](../V9_BACKLOG.md),
never silently skipped.

| Phase | Scope | Exit evidence |
|---|---|---|
| **P0-A** | Repo-grounded inventory: pinned HEAD, dirty state, symbol-level map, `KEEP/REFINE/REFACTOR/ADD/DEFER` traceability, test ownership | Every path in `V8_TO_V9_DELTA.md` verified at a pinned SHA; no work recorded against the wrong branch |
| **P0-B** | Audit and venue safety repair: opportunity → decision → order → fill → campaign → cashflow lineage; funding, mark and equity reconciliation; protection and restart races | Independent hand-computed oracle plus mutation fixtures reject wrong-but-complete joins; historical F01–F08 findings classified against current HEAD |
| **P0-C** | `DecisionPolicyV0` vertical slice: canonical action/intent/reason vocabulary, immutable decision receipt, idempotency, venue snapshot | DEC-001..010, ORD-001..009, POS-001..010 pass; Pi-off baseline parity; duplicate replay produces no extra side effect |
| **P1-A** | One PIT market-intelligence challenger (`V9-M1`), diagnostic view only | Preregistered single-change family; changed-decision accounting; no economic claim without costed calendar equity |
| **P1-B** | Separate entry / expert / position ablations (`V9-E1`, `V9-I1`, `V9-P1`) | Each family has its own baseline, fill authority and churn/coverage budget |
| **P1-C** | Occupancy, capacity and margin telemetry; altcoin feasibility dataset | No hindsight rotation; 20 USDT live feasibility tested separately, `FEASIBILITY_NOT_ESTABLISHED` until then |
| **P2** | Offline Pi/Kaizen pilot, one bounded task, same-budget manual baseline | Trading core runs identically with Pi stopped; no OOS or live-order access |
| **P3** | Production qualification: venue lifecycle, reconciliation, on-call | Separate owner authorisation; this monograph is not a live mandate |

## Invariants that every phase must preserve

- `policy_feature_off` reproduces V8 baseline behaviour.
- Same-event replay is idempotent; duplicate callbacks never double-count cash,
  fills or orders.
- `STOP-FIRST` is a bar-only diagnostic convention, never a claim about the
  historical intrabar path.
- A native stop without a reconciled position identity is not verified
  protection.
- Realised and unrealised P&L are never mixed; missing marks make the equity
  estimand `BLOCKED`.
- Sealed OOS is unreachable from any agent worktree.
- Negative and inconclusive trials are append-only and never deleted.

## First action

Run P0-A as a read-only inventory against the pinned `main` SHA, then select the
smallest P0-B defect that blocks honest accounting. Do not start P1 economic
experiments before P0-B and P0-C pass.
