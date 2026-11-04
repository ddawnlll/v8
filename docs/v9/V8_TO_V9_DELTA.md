# V8 → V9 Responsibility Delta — RFC 1.4 Derived Mapping

**Status:** `DESIGN_INFERENCE / SOURCE_MAPPING_NOT_STARTED`. **Only authoritative product architecture:** [V9_ARCHITECTURE_MONOGRAPH.md](V9_ARCHITECTURE_MONOGRAPH.md). This table is a **derivative implementation inventory**, not a parallel normative spec. Every path, symbol, current code SHA and test entry point must be pinned and verified before coding.

| Existing V8-next surface to inspect | V9 required product responsibility | First acceptance proof | Implementation disposition |
|---|---|---|---|
| `world/`, `domain/market.py` | Multi-horizon, event-driven, PIT `MarketBelief` with uncertainty/transition | Belief before/after changed market; no future inputs | `REFINE`, no redundant service |
| `experts/` | **All 28 existing experts** as contextual stance/abstention evidence sources, lineage and de-correlation | Complete 28 inventory, changed stance and clone invariance | `REFINE`, no wholesale deletion |
| `opportunities/book.py`, models | Canonical immutable birth + recurrent opportunity evaluation | One episode survives multiple market/expert updates | `REFINE`, no duplicate book |
| `economics/decisions.py`, `observer_policy.py` | **Unified V9TraderPolicy** with flat/open `WAIT ENTER HOLD REDUCE EXIT ABSTAIN` | `V9-INT-001..006` with typed reasons, no orders | `REFACTOR`; V0 only migration bridge |
| `domain/positioning.py`, native position snapshots | Active PositionThesis and PositionEvaluation | Thesis invalidation and decision change | `REFINE` |
| `economics/allocation.py`, `risk/admission.py`, sizing | Competing opportunity/capital constraints + hard risk | Two candidates, one open position; blocked/feasible reasons | `KEEP+REFINE`, no new risk authority |
| `adapters/` | Single Nautilus entry/exit/stop/native authority | Correct quantity, reduce-only, partial fill and no blind retry | `P0 SAFETY_REPAIR` before activated risk |
| `audit/pipeline.py`, `audit/reconciliation.py` | Independent native lineage/fees/funding/mark/equity oracle | Wrong-but-complete join mutant FAIL; #491 scope | `P0 AUDIT_REPAIR` |
| `evaluation/store.py`, gate registry and economics/oracle | Append-only scientific/claim evidence and promotion status | Reproduce negative trial, chosen producer, blocked claim | `KEEP/REFINE` |
| `system_proving/`, `app/cli.py` | Integrated deterministic fixture harness, read-only CLI | `V9-INT-001..006` and no native side effects | `REFINE` |
| `research_ops/` (optional) | Offline Kaizen research only | No live callback or OOS access | `ADD_IF_NEEDED` |

**Non-goals for the first native-risk activation:** second engine/OMS/book, learned EV invented from labels, uncontrolled stop widen, mandatory agent swarm, automatic live LLM, untested portfolio rotation. **Required V9 shadow target:** MarketBelief + 28 expert intelligence + OpportunityBook + unified TraderPolicy + active position + portfolio, in one continuous replayable decision loop.

**No evidence claims:** these are possible code path surfaces, not a verified module/function map. P0-A must provide exact `module:line:symbol`, pinned SHA, tests and source-of-truth reconciliation.
