# AGENTS.md — Agent Guidelines & Invariants

## 🚨 STRICT RULE: RUST ONLY — PYTHON CODEBASE IS FROZEN & DEPRECATED

### 1. Authoritative Runtime is Rust (`v8-core/`)
- **`v8-core/` is the ONLY active, authoritative codebase** for the entire project (runtime, compute plane, experts, scheduler, backends, analysis, verdict, evaluation, reports).
- **All code edits, bug fixes, new features, and tests MUST be written in Rust inside `v8-core/`.**

### 2. Python (`src/v8/` and `tests/`) is Strictly FROZEN
- `src/v8/` is a historical parity oracle locked via `docs/legacy/PYTHON_ORACLE_LOCK.json`.
- `tests/` is the historical Python harness, NOT the CI runtime gate.
- **AGENTS ARE STRICTLY PROHIBITED FROM MODIFYING `src/v8/` OR `tests/`.**
- Do NOT add, edit, or refactor Python code in `src/v8/`. Any modification to `src/v8/` breaks the git tree hash verification (`tools/audit_python_boundary.py`) and is considered a critical contract violation.

### 3. Allowed Python Usages
Only standalone documentation / tooling scripts in `tools/` may use Python:
- `tools/build_monograph.py`
- `tools/audit_python_boundary.py`
- `tools/audit_synthetic_leakage.py`
- `tools/audit_economic_claim.py`
- `tools/forbidden_names.py`

### 4. Verification Commands
- `cargo test --manifest-path v8-core/Cargo.toml`
- `cargo check --manifest-path v8-core/Cargo.toml`
- `cargo clippy --manifest-path v8-core/Cargo.toml`
- `.venv/bin/python tools/audit_python_boundary.py`
- `python3 tools/audit_synthetic_leakage.py`
- `python3 tools/audit_economic_claim.py`

## 🚨 STRICT RULE: ZERO-TOLERANCE ANTI-HALLUCINATION & ANTI-SYNTHETIC DATA DIRECTIVE

### 5. Absolute Ban on Synthetic Data, Hardcoded Metrics & Fabricated Inputs in Production/Evaluation Pipelines
1. **No Hardcoded Statistical Metrics:**
   - It is strictly forbidden to hardcode p-values (e.g. `0.02`, `0.04`), effect sizes (e.g. `0.15R`), PBO scores, confidence values, or expected improvements (e.g. `+0.12R`) in any runtime, analysis, agent, or evaluation module.
   - All statistical metrics must be derived exclusively from real computations (`src/statistics/`, genuine bootstrap, WRC, Detrended Null).
2. **No Synthesized / Offset Inputs:**
   - It is strictly forbidden to manufacture or offset trade excursion data (e.g. `mfe_r + 0.8`, arbitrary lookback constants) to trigger diagnostic classifiers or agent hypotheses.
   - If future data or trade markouts are unavailable, the system MUST fail closed or record explicit absence (`None`, `UNRESOLVED`, `NOT_APPLICABLE`) — never a synthetic placeholder.
3. **Strict Isolation of Synthetic Fixtures:**
   - Mock or synthetic data is permissible ONLY inside test harnesses (`#[cfg(test)]`) to test edge-case code paths and arithmetic contracts.
   - Synthetic fixtures must NEVER enter production execution pipelines, evaluation manifests, findings ledgers (`findings.jsonl`), or report generators.
4. **Enforcement of Constitution Rule 12 (`NO_ECONOMIC_CLAIM`):**
   - No module or agent may emit `SUPPORTED_EDGE` or claim predictive profitability without certified multiple-testing adjustments (WRC, DSR, Hansen SPA) and a valid authority receipt. All uncertified verdicts must remain `NO_ECONOMIC_CLAIM`.
5. **No Fictitious Artifact References:**
   - Generating findings or receipts that reference non-existent files or uncomputed tables (e.g. fictitious parquet paths) is classified as a critical system hallucination. Every referenced artifact must be physically produced and verified on disk.

## 🚨 WORK-ITEM & PR GOVERNANCE (v1.2)

### 6. Canonical Workflow & Requirement Traceability
- **Canonical Policy:** All collaborative development follows [`docs/WORK_ITEM_POLICY.md`](docs/WORK_ITEM_POLICY.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Universal Issue Contract:** All work items must specify:
  1. `R#` Normative Traceability (mapped to exact spec clauses / D-series decisions).
  2. Existing types / traits / contracts to reuse (anti-invention rule).
  3. Mathematical & semantic invariants.
  4. Canonical failure semantics.
  5. Dependency & composition topology.
  6. Explicit `OPEN_PIN` triggers.
- **PR Traceability Matrix:** Every PR must account for all issue `R#` requirements (`R# → Authority → Implementation → Verification → Receipt`). Unmapped requirements block merge.
- **Authority Precedence:** Constitution & Registered Decisions > `WORK_ITEM_POLICY.md` > `CONTRIBUTING.md` > Scoped Agent Instructions. If active authorities conflict, STOP and escalate an `OPEN_PIN`.

### 7. Pull Request Governance & Merge Authority (Human Direction Only)
- **Always PR First:** All code edits, fixes, and features must be implemented on a feature branch and submitted as a Pull Request for maintainer review.
- **PR Actions Under Human Direction Only:** Agents create and update PRs strictly under human direction / task assignment.
- **Absolute Ban on Autonomous Merging:** Agents must NEVER merge pull requests (e.g. `gh pr merge`, `git merge`, or squash merge) autonomously. Merging PRs is strictly reserved for human maintainers or requires explicit, standalone human maintainer direction.
- **No Direct Pushes to Main:** Agents must NEVER push directly to `main`.

## 🚨 STRICT RULE: ZERO-SHADOW ARCHITECTURE & MANDATORY DECISION / MONOGRAPH REGISTRATION

### 8. Absolute Ban on Unregistered Architectural Decisions & Shadow Implementations
1. **Mandatory D-Series Decision Registration:**
   - Any architectural extension, structural refactor, new subsystem/module, error taxonomy, cryptographic upgrade, streaming protocol, or IPC/checkpoint mechanism MUST be explicitly registered with a new `D-xxx` decision in [`docs/decisions/DECISION_REGISTER.md`](docs/decisions/DECISION_REGISTER.md) and its Turkish mirror [`docs/tr/DECISION_REGISTER.md`](docs/tr/DECISION_REGISTER.md).
2. **Contract & Layout Traceability:**
   - Every newly created Rust module or significant interface MUST be mapped in [`docs/contracts/IMPLEMENTATION_LAYOUT.md`](docs/contracts/IMPLEMENTATION_LAYOUT.md) (§1.1 as-built tree, §2 file-by-file contract, and §4 known divergences table).
3. **Mandatory Monograph Synchronization:**
   - When documentation, decisions, contracts, or audits are modified, both English and Turkish single-file monographs MUST be regenerated via:
     `uv run --with markdown tools/build_monograph.py --lang en --docs docs --out site/index.html`
     `uv run --with markdown tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html`
4. **Mandatory CHANGELOG Entry:**
   - Every architectural change MUST be recorded in [`docs/CHANGELOG.md`](docs/CHANGELOG.md) with date, associated issue IDs, and modified artifacts list.
5. **Zero Tolerance for Shadow Architecture:**
   - Unregistered code paths, hidden heuristics, undocumented data structures, or silent layout changes are classified as severe contract violations and block PR merge.




