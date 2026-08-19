# Contributing to V8

Welcome to the V8 research and development repository.

V8 operates under strict evidence-based, contract-first governance. All collaborative work follows the canonical **[V8 Work-Item, Pull-Request & Merge Governance Policy](docs/WORK_ITEM_POLICY.md)**.

## 1. Filing Work Items

All changes originate from a structured issue filed under one of the 5 Issue Forms:
- **`[DEFECT]`**: Observed contradiction with an existing contract, invariant, or baseline.
- **`[IMPL]`**: Implementation or wiring of a pinned decision/contract without inventing new semantics.
- **`[RESEARCH]`**: Preregistration of a falsifiable hypothesis, benchmark, or challenger experiment.
- **`[PERF]`**: Measured profile-driven compute optimization with bitwise/semantic parity invariants.
- **`[GOV]`**: Formal decision record (D-series), OPEN_PIN resolution, or registry mutation.

Blank issues are disabled. Every work item must satisfy the **Universal Context-Completeness Contract** (R# traceability, reused contracts, invariants, canonical failure semantics, dependency map, OPEN_PIN triggers) before reaching `READY` state.

## 2. Collaborative PR Workflow

1. Create a focused branch from `main`: `<type>/<issue-number>-<short-description>`.
2. Ensure every PR implements requirements directly mapped to the linked issue via the **PR Traceability Matrix** (`R# → Owning Authority → Implementation Surface → Verification Gate → Receipt`).
3. Maintain zero runtime changes for governance/documentation PRs.
4. Pass all active verification gates (`tools/forbidden_names.py`, `tools/audit_python_boundary.py`, `cargo test`, `cargo clippy`, and monograph byte-identity probe).
5. Obtain review from authoritative domain owners defined in [`.github/CODEOWNERS`](.github/CODEOWNERS).

## 3. Precedence & Governance Authority

- **Semantic Domain Rule:** The [V8 Constitution](docs/charter/V8_CONSTITUTION.md), owning contracts in [`docs/contracts/`](docs/contracts/), and the [Decision Register](docs/decisions/DECISION_REGISTER.md) own semantic truth.
- **Collaborative Workflow Rule:** [`docs/WORK_ITEM_POLICY.md`](docs/WORK_ITEM_POLICY.md) owns the Issue → PR → review → merge process.
- **Session / Runbook Rule:** Task-specific instructions (`CLAUDE.md`, `docs/AGENT_RUNBOOK.md`) apply only within their explicitly declared scope.
- **Conflict Rule:** If active authorities conflict, implementation stops immediately and opens an `OPEN_PIN`. Unknown owning semantics are not implementer discretion.

For detailed guidelines, labels, merge rules, and verification requirements, read the canonical **[WORK_ITEM_POLICY.md](docs/WORK_ITEM_POLICY.md)**.
