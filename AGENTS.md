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

## WORKFLOW: TRUNK-BASED, TIERED GOVERNANCE (reset 2026-09-07, owner-authorized)

### 6. Canonical Workflow
- **Default:** `edit → relevant checks → commit to main → continue` (Tier A/B).
  PRs and issues are NOT normal development primitives in this solo-dev + agent
  workflow. Full policy in [`docs/GOVERNANCE_RESET_V86_2026-09-07.md`](docs/GOVERNANCE_RESET_V86_2026-09-07.md).
- **Fast development gate (Tier A/B):** fmt clean on touched lines + `cargo clippy`/
  compile + relevant tests. Full suite / heavy evidence gates run at milestones,
  releases, or risk boundaries — not per commit.
- **Tier C/D (evidence & release claims)** keep the heavy machinery: issues with
  `R#` traceability, reproducible evidence, receipts/certificates where the
  owning spec requires them. See [`docs/WORK_ITEM_POLICY.md`](docs/WORK_ITEM_POLICY.md).
- **Authority Precedence:** current explicit project objective > minimal safety/
  evidence constitution (§§1–5) > physical evidence + executable checks > active
  technical spec > historical D-xxx/ADR > old audit notes. Historical decisions
  NEVER veto normal implementation. On genuine safety conflicts (data loss,
  security, real-money paths, fabricated claims), STOP and escalate.

### 7. Branches (Exceptional, Not Mandatory)
- Work directly on `main`. `main` = latest coherent dev state, not a certified release.
- Short-lived scratch branches are allowed ONLY when `main` cannot stay
  compilable during an atomic migration; merge back promptly. No mandatory PR,
  no approval ceremony for ordinary development.

## TIER-D REGISTRATION (release-boundary only)

### 8. Decision / Monograph Registration at the Release Boundary
Tier A/B implementation needs NO D-xxx, layout mapping, monograph rebuild, or
CHANGELOG entry. The items below apply at Tier D (release/economic-claim
boundary) only:
1. **D-Series Decision Registration:** release-scope architectural decisions are
   recorded in [`docs/decisions/DECISION_REGISTER.md`](docs/decisions/DECISION_REGISTER.md).
2. **Contract & Layout Traceability:** release-scope modules/interfaces are mapped
   in [`docs/contracts/IMPLEMENTATION_LAYOUT.md`](docs/contracts/IMPLEMENTATION_LAYOUT.md).
3. **Monograph Synchronization:** EN/TR monographs are regenerated at release via
   `tools/build_monograph.py` — not per commit.
4. **CHANGELOG Entry:** release-scope changes are recorded in [`docs/CHANGELOG.md`](docs/CHANGELOG.md).
5. **Zero Tolerance for Shadow Architecture:**
   - Unregistered code paths, hidden heuristics, undocumented data structures, or silent layout changes are classified as severe contract violations and block PR merge.
6. **Mandatory Full-Text Specification Preservation (`NO_UNANCHORED_SPEC_ACCEPTANCE` / Rule 44):**
   - Every draft bill, constitutional amendment, or architectural proposal MUST be committed as an unabridged, full-text specification in `docs/` (`docs/contracts/`, `docs/charter/`, etc.).
   - Monographs and decision registers present summaries and MUST link directly to the authoritative full-text specification. Unanchored proposals or summaries lacking a committed full-text document are strictly prohibited from ratification.




