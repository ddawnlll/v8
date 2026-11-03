# V9 Implementation Plan — Evidence-Gated

**Status:** `NOT_STARTED / COUNCIL_REVIEW_PENDING`. This plan schedules work; it is not implementation,
validation, or economic authority. The normative architecture is
[`V9_ARCHITECTURE_MONOGRAPH.md`](V9_ARCHITECTURE_MONOGRAPH.md) (RFC 1.3.1 — independent council review candidate, implementation unverified).

Each phase is closed only by its evidence gate. A green unit test is not a
venue-safety certificate, and a mechanical pass is not an economic result.
Unmet **claim × producer × dataset × execution_profile** gates are recorded as `BLOCKED` in [`../V9_BACKLOG.md`](../V9_BACKLOG.md),
never silently skipped.

| Phase | Scope | Exit evidence |
|---|---|---|
| **P0-A** | Choose exactly one `strategy_class + config_hash + code_sha + execution_profile`; pin HEAD, dirty state, legacy expert gate and symbol-level map, `KEEP/REFINE/REFACTOR/ADD/DEFER` traceability, test ownership | Every path in `V8_TO_V9_DELTA.md` verified at a pinned SHA; no work recorded against the wrong branch |
| **P0-B** | Used-path `SAFETY_REPAIR` / `AUDIT_REPAIR` (not V9 alpha): rc4 cancel API, partial-fill bracket quantities, no risk-minimum uplift, fill multiset and opportunity → decision → order → fill → campaign → cashflow lineage; funding, mark and equity reconciliation; protection and restart races | Independent hand-computed oracle plus mutation fixtures reject wrong-but-complete joins; historical F01–F08 findings classified against current HEAD |
| **P0-C** | Side-effect-free `DecisionPolicyV0` proposal + existing native execution writer's atomic intent/outbox, partial-fill-pending precedence, pinli baseline parity | DEC-001..010, ORD-001..009, POS-001..010 pass; Pi-off baseline parity; duplicate replay produces no extra side effect |
| **P1-A** | One PIT challenger (`V9-M1`), diagnostic-only until economic gates | Preregistered changed decisions; full same-capital replay, cash/no-trade, random-veto and raw-threshold controls; no costed economic claim without qualified equity |
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

Run P0-A as a read-only inventory against the actually checked-out pinned SHA and select a single baseline. Run targeted used-path safety/audit repair issues; mark unresolved #491 equity producer `BLOCKED` for affected economic estimands, not unrelated mechanical fixtures. Begin side-effect-free V0 fixtures once the mapped baseline is known; do not activate P1 economic policies without producer-scoped safety, parity and economic evidence.
