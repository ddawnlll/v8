# V8 → V9 Responsibility Delta

**Status:** `DESIGN_INFERENCE` / `NOT_STARTED`. Adapted from
`V9_ARCHITECTURE_MONOGRAPH.md` §XIV. No code change is implied by this table;
every path and symbol must be re-verified against the pinned commit during
P0-A before any refactor is authorised.

**Pinned baseline:** GitHub `main` at the V9-foundation commit. V8 evidence and
accounting fixes are integrated; unresolved correctness and evidence gaps are
tracked in [`../V9_BACKLOG.md`](../V9_BACKLOG.md).

| V8-next path | V8 role | V9 target | Decision | Acceptance measure |
|---|---|---|---|---|
| `world/`, `domain/market.py` | Market, causal representation | MarketBelief / transition / uncertainty view | `REFINE` | PIT validity; state version; UNKNOWN is legal |
| `experts/` | Behaviour observer | Habitat-conditional stance, independent contribution | `REFINE` | Non-degenerate ablation; baseline default unchanged |
| `opportunities/book.py`, `models.py` | Canonical OpportunityBook | Immutable birth snapshot + append-only evaluation views | `REFINE` | Persistence without mandatory retest wait |
| `economics/decisions.py`, `observer_policy.py` | Decision economics | DecisionPolicyV0 canonical action/intent/event vocabulary | `REFACTOR` | DEC-001..010 fixtures; unknown/priority/idempotency; baseline parity |
| `risk/admission.py`, `sizing.py` | Hard limits | Revalidate every intent and order adjustment | `KEEP+REFINE` | Risk and venue rejection fail closed |
| `economics/allocation.py`, `domain/positioning.py` | Portfolio / exposure | Occupancy-aware policy and attribution | `REFINE` | Every blocked candidate has an exact reason |
| `adapters/` | Nautilus strategy and order path | Entry / position policy adapters | `KEEP+REFINE` | Native callback, fill and protection identity |
| `audit/pipeline.py`, `audit/reconciliation.py` | Forensic audit | Independent oracle; wrong-but-complete join and MFE time-bound detection | `P0 REPAIR` | Native joins independently correct, not merely zero orphans |
| `evaluation/store.py` | Trials / lineage | Append-only research memory | `KEEP` | All variants and failed attempts retained |
| `evaluation/gate_registry.py`, `kaizen_delta.py` | Gates and benchmark deltas | Separate correctness from economic promotion | `REFINE` | Reproducible outcome under fixed hashes |
| `oracle/utility.py` | Economic feasibility contract | Retain economic constraints | `KEEP` | No unsupported EV auto-promotion |
| `system_proving/` | Receipt / proving tools | Fault injection and structural qualification | `REFINE` | Invalid joins and gates are rejected |
| `app/cli.py` | Unified CLI | Bounded research / adaptation commands | `SMALL EXTENSION` | No second CLI or hidden native path |
| `research_ops/` (conditional) | Not canonical | Pi queue/lease/budget/GitHub reconciliation only if a pilot proves need | `ADD_IF_NEEDED` | One full bounded issue → trial → receipt pilot |

## Explicit non-goals for the first V9 slice

- No new engine, second OpportunityBook, economics ledger, auditor registry or
  trading brain.
- No live LLM controller in any trading callback.
- No default-on dynamic stop policy, allocator, router, consensus or learned
  scorer.
- No change to V8 trading defaults in the baseline-equivalence phase.
