---
name: v8
description: The canonical V8 trading intelligence & architectural protocol skill. Enforces the 32 constitutional rules, Rule 44 full-text spec invariant, Zero Shadow Architecture (D-xxx), Rust-only compute plane (`v8-core/`), frozen Python boundary, R# traceability matrix (v1.2), and dual monograph compilation.
user-invocable: true
argument-hint: "[audit | work-item <id> | decision <topic> | monograph | <task>]"
---

# V8 Canonical Engineering, Architecture & Constitutional Protocol

> **STATUS:** PRE-EXPERIMENTAL / EVIDENCE-BOUND FALSIFICATION PROGRAM (Crypto Perpetual Futures)  
> **CORE AXIOM:** V8 is a falsification program, not a promise of edge. Never claim profitability, unverified execution edge, or a promoted trading system (Constitution Rule 12).

---

## 1. Non-Negotiable Invariants & Constitutional Core

Every agent (Claude, Antigravity, Codex, subagents, forks, and automated scripts) MUST strictly adhere to the following invariants before reading or mutating code.

### 🚨 1.1. Absolute Rust-Only Runtime (`v8-core/`) — Python is Frozen
- **The authoritative runtime is `v8-core/` (Rust).**
- **ALL** new features, bug fixes, evaluations, refactors, analytics, algorithms, and tests MUST be written in Rust inside `v8-core/`.
- `src/v8/` and `tests/` are a **historical parity oracle** locked cryptographically by `docs/legacy/PYTHON_ORACLE_LOCK.json`.
- **NEVER MODIFY `src/v8/` OR `tests/`.** Any change to `src/v8/` breaks git tree hash verification (`tools/audit_python_boundary.py`) and is an immediate fatal violation.
- Allowed Python usage: Only standalone documentation & build scripts under `tools/` (e.g. `tools/build_monograph.py`, `tools/audit_*.py`, `tools/forbidden_names.py`).

### 🚨 1.2. Zero-Tolerance Anti-Hallucination & Anti-Synthetic Data Directive
1. **No Hardcoded Statistical Metrics:** Strictly forbidden to hardcode p-values (e.g., `0.02`), effect sizes (e.g., `+0.15R`), PBO scores, Sharpe ratios, or win rates in runtime/analysis code. All metrics must be computed via `src/statistics/`, genuine bootstrap, WRC, or Detrended Null.
2. **No Synthesized / Offset Inputs:** Never manufacture or offset trade excursion data (e.g. `mfe_r + 0.8`) to trigger classifiers. Missing data must fail closed or record explicit absence (`None`, `UNRESOLVED`, `NOT_APPLICABLE`).
3. **Synthetic Fixtures Isolation:** Mock data is permitted ONLY inside `#[cfg(test)]` unit tests. Synthetic fixtures must NEVER enter production execution pipelines, evaluation manifests, `findings.jsonl`, or reports.
4. **No Naked Economic Claims (Rule 29):** All economic/statistical values crossing module boundaries must use typed authority wrappers:
   $$\text{ClaimValue}\langle T \rangle = \{ \text{value}: T, \text{authority}: \text{Authority}, \text{receipt\_id}: \text{ReceiptId} \}$$
   Without an authority receipt, economic verdict stays `NO_ECONOMIC_CLAIM`.
5. **No Fictitious Artifacts:** Generating receipts or findings that reference non-existent files or uncomputed tables is a critical failure. Every referenced artifact must physically exist on disk.

### 🚨 1.3. Zero Shadow Architecture (Mandatory Registration)
Every architectural addition, module, structural refactor, or error taxonomy change MUST follow the 5-step registration:
1. Register a new `D-xxx` decision in `docs/decisions/DECISION_REGISTER.md` AND `docs/tr/DECISION_REGISTER.md`.
2. Map the module in `docs/contracts/IMPLEMENTATION_LAYOUT.md` (§1.1 as-built tree, §2 file contract, §4 known divergences).
3. Log the change in `docs/CHANGELOG.md` with date, issue ID, and modified artifacts.
4. Ratify full-text specification under `docs/` (`NO_UNANCHORED_SPEC_ACCEPTANCE` / Rule 44). Unanchored summaries are prohibited.
5. Recompile both monographs:
   - `python tools/build_monograph.py --lang en --docs docs --out site/index.html`
   - `python tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html`

---

## 2. V8 Architecture & Minimum Coherent Pipeline

### 2.1. The Canonical Linear Flow (Rule 6)
$$\text{PIT MarketState} \rightarrow \text{Opportunity Grammar} \rightarrow \text{Canonical Opportunity Book} \leftarrow \text{Expert Stances} \rightarrow \text{Evidence Reconciliation} \rightarrow \text{Selective Utility} \rightarrow \text{Portfolio Feasibility} \rightarrow \text{Execution Campaign} \rightarrow \text{Orders/Fills/Ledger}$$

### 2.2. Gated Components (ABSENT BY DEFAULT — Rules 6, 14)
Do **NOT** implement:
- Shared Global Router / Scorer / Ranker
- Uncertified Reinforcement Learning (RL) execution
- Online parameter learning (learning is offline and registry-gated; Rule 15)

### 2.3. Fundamental Epistemic & Market Ontologies
- **Rule 4 (Economic Object Separation):** `MarketState`, `EconomicExposureStructure`, `OpportunityEpisode`, `ObserverEvidence`, `ReconciledOpportunityState`, `ExecutionCampaign`, `Order / Fill / Position`, and `Outcome` are distinct immutable records. None may proxy for another.
- **Rule 13 (Observer Constitution):** An Expert is an epistemic observer, NOT an economic sovereign. Experts can observe, support, contradict, abstain, and report uncertainty. Experts possess ZERO authority to allocate capital, create positions, or compel execution.
- **Rule 16 & 19 (Identity Constitution):**
  $$\text{Symbol} \neq \text{Instrument} \neq \text{EconomicExposure} \neq \text{Opportunity} \neq \text{Trade}$$
- **Rule 20 (Observer Multiplicity Invariance):** Adding cloned observers or duplicate feeds yields zero marginal evidence ($N_{\text{eff}} = 1.0$).
- **Rule 21 (Habitat & First-Class Abstention):** Outside habitat or under epistemic uncertainty, default action is strictly `ABSTAIN` / `NO_TRADE`. Silence is an active, unpenalized state.
- **Rule 24 (After-Cost Net Economic Value):** Admitted only if expected gross edge exceeds all frictions:
  $$\mathbb{E}[\Delta \text{PnL}_{\text{net}}] = \text{GrossEdge} - \text{Friction} - \text{UncertaintyPenalty} > 0$$
- **Rule 28 (3-Dimensional Authority Tensor):**
  $$\text{Authority} = (\text{EvidenceAuthority}, \text{DecisionAuthority}, \text{RealizationStatus})$$

---

## 3. Work-Item (v1.2) & PR Governance Lifecycle

When implementing any task or PR, follow this deterministic 6-phase lifecycle:

```text
┌─────────────────────────┐
│ Phase 1: Context & R#   │ ➔ Map R# Requirements, Existing Types, Invariants
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Phase 2: D-xxx Registry │ ➔ Register Decision in EN/TR Registers & Layout
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Phase 3: Rust Core Dev  │ ➔ Implement strictly in v8-core/ (No Python edits)
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Phase 4: Test & Verify  │ ➔ cargo test, clippy, boundary & leakage audits
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Phase 5: Monograph Sync │ ➔ Rebuild site/index.html (EN) & site/tr.html (TR)
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Phase 6: Truth Gate PR  │ ➔ PR-first, complete R# matrix, human maintainer merge
└─────────────────────────┘
```

### 3.1. Universal Traceability Matrix (Required for every PR)
Every work item and pull request must provide an explicit `R#` Traceability Matrix:
```markdown
| Requirement ID | Normative Authority | Implementation Location | Verification Method | Receipt / Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `R1` | D-xxx / Rule yy | `v8-core/src/...` | `cargo test test_name` | PASS (stdout) |
```

### 3.2. PR & Branch Rules
- Work MUST be on a dedicated branch (e.g. `feat/v8.5-xxx` or `fix/xxx`).
- Never push directly to `main`.
- **Absolute Ban on Autonomous Merging:** Agents must NEVER merge PRs autonomously. PR merge authority is strictly reserved for human maintainers.

---

## 4. Operational Commands & Action Dispatch

When invoked via `/v8 <action>`, dispatch to the corresponding subroutine:

### Action: `audit` or `check` (`/v8 audit`)
Run the full suite of V8 boundary and semantic integrity checks:
1. Python Boundary Integrity:
   `python tools/audit_python_boundary.py` (or `.venv/bin/python tools/audit_python_boundary.py`)
2. Forbidden Identifier Audit:
   `python tools/forbidden_names.py`
3. Synthetic Leakage Audit:
   `python tools/audit_synthetic_leakage.py`
4. Economic Claim Audit:
   `python tools/audit_economic_claim.py`
5. Rust Core Compilation & Tests:
   `cargo test --manifest-path v8-core/Cargo.toml`
   `cargo clippy --manifest-path v8-core/Cargo.toml --all-targets -- -D warnings`
6. Monograph Build Verification:
   `python tools/build_monograph.py --lang en --docs docs --out site/index.html`
   `python tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html`

### Action: `work-item <id>` (`/v8 work-item D-150`)
1. Read work item requirements and define `R#` traceability items.
2. Check existing types in `v8-core/src/` to prevent contract re-invention.
3. If new structs/subsystems are introduced, allocate next `D-xxx` number.
4. Execute implementation in `v8-core/`.
5. Write targeted unit and integration tests.
6. Rebuild monographs and verify diff.

### Action: `decision <topic>` (`/v8 decision "Topic Title"`)
1. Find latest decision ID in `docs/decisions/DECISION_REGISTER.md`.
2. Format decision entry with: Context, Decision, Invariants, Precedence, Affected Components.
3. Add mirror entry to `docs/tr/DECISION_REGISTER.md`.
4. Update `docs/contracts/IMPLEMENTATION_LAYOUT.md`.
5. Update `docs/CHANGELOG.md`.
6. Run monograph builder.

### Action: `monograph` (`/v8 monograph`)
Rebuild and verify the bilingual monographs:
```bash
python tools/build_monograph.py --lang en --docs docs --out site/index.html
python tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html
```

---

## 5. Truth-Gated Final Deliverable Standard

Every response for engineering tasks must conclude with:
1. **Changed Files:** Exact paths modified.
2. **Commands Run:** Verbatim commands executed.
3. **Pass/Fail Evidence:** Actual compiler, test, or audit output.
4. **Known Limitations & Open Pins:** Any remaining uncertainties or boundary conditions.
5. **No Fake Claims:** If a test or command was not run, explicitly state why.
