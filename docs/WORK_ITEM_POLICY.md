# V8 Work-Item, Pull-Request & Merge Governance Policy v1.2

**Document Status:** `LOCKED_INVARIANT / PROVISIONAL_DECISION (v1.2 Pilot)`  
**Owning Authority:** V8 Constitution, D-099, D-117  
**Canonical Scope:** Repository-wide collaborative development workflow (Issue → PR → Review → Merge).

---

## 1. Core Principles & Philosophy

V8 is an evidence-bound quantitative research and runtime system. Every change to the repository must be:
1. **Traceable:** Mapped from an actionable work item with requirement-level `R#` identifiers to concrete spec clauses and registered decisions.
2. **Context-Complete:** Containing all mathematical invariants, existing types to reuse, canonical failure semantics, dependency topologies, and OPEN_PIN triggers before implementation begins.
3. **Evidence-Bearing:** Verified by the smallest discriminating check and accompanied by reproducible verification receipts.
4. **Anti-Invention:** Never creating parallel types, rogue error codes, or ad-hoc interfaces where an existing authoritative contract owns the domain.

---

## 2. Authority Precedence Hierarchy

For all repository development and collaboration:

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Domain Semantics                                         │
│    V8 Constitution > Owning Contracts > Decision Register   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Collaborative Workflow                                   │
│    docs/WORK_ITEM_POLICY.md (Canonical Issue/PR/Merge Rules) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Entry Point                                              │
│    CONTRIBUTING.md (Points to policy; never forks semantics)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Session / Autonomous Agents                               │
│    CLAUDE.md / AGENT_RUNBOOK.md / GEMINI.md (Scoped only)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Conflict Resolution                                      │
│    Two active authorities conflict → STOP / OPEN_PIN        │
└─────────────────────────────────────────────────────────────┘
```

Historical or task-specific agent instructions (such as `docs/AGENT_RUNBOOK.md` or `CLAUDE.md`) apply only within their explicitly declared scope and MUST NOT silently override domain contracts or the general collaborative workflow outside that scope.

---

## 3. Work-Item Taxonomy & Universal Issue Contract

All work begins as a GitHub Issue under one of five canonical forms:

### Issue Classes
1. **`[DEFECT]`**: Observed contradiction with an existing specification, invariant, or baseline behavior.
2. **`[IMPL]`**: Implementation or wiring of a pinned decision, contract, or missing module without inventing new semantics.
3. **`[RESEARCH]`**: Preregistration of a falsifiable hypothesis, benchmark, or challenger experiment.
4. **`[PERF]`**: Measured profile-driven compute optimization with bitwise/semantic parity preservation.
5. **`[GOV]`**: Formal decision record (D-series), OPEN_PIN resolution, or registry mutation.

### Universal Context-Completeness Contract
Before any issue is moved to `state:ready` for implementation, it MUST supply:

- **11. Normative Traceability (`R1`, `R2`, ...):** Exact mapping of each requirement to owning spec clauses, D-/O- decisions, registry entries, or tests. Broad range citations (e.g. `SPEC §1–§8`) are invalid when narrower clauses exist.
- **12. Existing Types / Interfaces to Reuse:** Explicit list of types, traits, enums, manifests, hashes, and contracts to reuse.
- **13. Mathematical / Semantic Invariants:** Explicit formulas, ordering rules, immutability constraints, and state transitions.
- **14. Canonical Failure Semantics:** Explicit mapping of invalid or unsupported states to existing canonical error/refusal codes.
- **15. Dependency Map:** Smallest conceptual/data-flow graph showing existing vs new nodes.
- **16. Ambiguity / OPEN_PIN Triggers:** Exact conditions that must halt execution and escalate to governance.

---

## 4. Pull-Request Contract & Verification

Every PR must be opened using `.github/PULL_REQUEST_TEMPLATE.md` and satisfy the following invariants:

### PR Requirements
1. **Change Class Declaration:** Explicitly select one of `CONTRACT_GOVERNANCE`, `CONTRACT_IMPLEMENTATION`, `DEFECT_FIX`, `BEHAVIOR_PRESERVING_REFACTOR`, `CORRECTNESS_SEMANTICS`, `PERF_OPTIMIZATION`, or `RESEARCH_EXPERIMENT`.
2. **Normative Traceability Matrix:**
   ```text
   R# in Issue → Owning Authority → Implementation Surface → Verification Gate → Receipt
   ```
   Every requirement in the linked issue must be accounted for. Unmapped requirements block merge.
3. **Scope & Boundary Closure:** PRs for governance or documentation must touch zero runtime/economic source files.
4. **Active CI Checks:** Must pass the authoritative GitHub Actions check identity: `check` (from `.github/workflows/ci.yml`).
5. **Computation Budget (D-099):** Any check exceeding 5 seconds or repeating an already-green check must justify the marginal decision value versus cost.
6. **No Synthetic Data:** Strict compliance with Constitution Rule 12 (`NO_ECONOMIC_CLAIM`). Zero hardcoded p-values, Sharpe ratios, or synthetic trade excursions.

---

## 5. Label Catalog & Routing

The canonical repository labels are structured as follows:

| Label | Category | Description |
|---|---|---|
| `triage` | Intake | Canonical default intake label applied by all issue forms upon creation |
| `type:defect` | Type | Defect or bug report |
| `type:implementation` | Type | Pinned implementation or wiring |
| `type:research` | Type | Falsifiable hypothesis or experiment |
| `type:performance` | Type | Profile-driven compute optimization |
| `type:governance` | Type | Authority clarification, decision record, or registry change |
| `state:triage` | Lifecycle | Awaiting initial authority and context-completeness review |
| `state:ready` | Lifecycle | Context-complete, R# mapped, authorized for implementation |
| `state:in-progress` | Lifecycle | Branch active and under development |
| `state:review` | Lifecycle | Pull request open and awaiting CODEOWNERS review |
| `state:blocked` | Lifecycle | Execution stopped due to open OPEN_PIN |
| `risk:high` | Risk | Touches core consensus, financial accounting, or mathematical invariants |
| `risk:medium` | Risk | Touches runtime components, adapters, or feature extraction |
| `risk:low` | Risk | Documentation, tooling, or non-runtime governance files |
| `needs:authority` | Blocker | Missing owning decision or spec clause |
| `needs:reproduction`| Blocker | Defect missing minimal discriminating reproduction |
| `needs:review` | Review | Awaiting codeowner sign-off |

---

## 6. CODEOWNERS & Protected Branch Rules

- **Protected Branch:** `main` is protected. Direct pushes are prohibited.
- **Merge Requirements:**
  - Status check `check` (workflow `ci`) must pass.
  - Review approval from designated owners in `.github/CODEOWNERS` (`@ddawnlll`).
  - Linear git history (rebase/merge without dirty merge commits).
- **Surface Routing:** High-risk surfaces (`/docs/charter/`, `/docs/contracts/`, `/docs/decisions/`, `/docs/registries/`, `/v8-core/`) require explicit owner approval.

---

## 7. Canonical Failure & Refusal Semantics

Governance operations use structured lifecycle states rather than runtime exceptions:
- **Unresolved placeholder token:** `BLOCKED / OPEN_PIN`
- **Missing real CODEOWNER identity:** `BLOCKED / OPEN_PIN`
- **Ambiguous or conflicting authority:** `BLOCKED / OPEN_PIN`
- **Missing CI check identity:** `BLOCKED / OPEN_PIN`
- **YAML schema validation failure:** `FAIL`
- **Issue Form rendering failure:** `FAIL` (issue remains open)
- **PR introduces untraced behavior:** `BLOCKED`

---

## 8. Measured 10–20 Issue Pilot

Adoption of v1.2 begins with a measured pilot over the next 10–20 issues tracked in `docs/governance/PILOT_TRACKING_RECORD.md`.

### Measured Metrics:
1. **Zero-Clarification READY Rate:** Fraction of issues that achieve `state:ready` on initial submission without ambiguity rounds.
2. **Triage Latency & Friction:** Time and iterations spent in triage.
3. **Traceability Completeness:** Percentage of merged PRs with 100% `R#` closure.
4. **Review Defect Attribution:** Classification of review rounds into missing requirements vs code bugs.
5. **D-099 Compute Efficiency:** Verification compute spent per PR.

Pilot findings will serve as empirical evidence for the future v1.3 governance revision.
