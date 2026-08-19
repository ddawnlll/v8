## 1. Summary & Objective

<!-- Brief description of the change and what it accomplishes. -->

**PR Title Convention:** `[<CHANGE_CLASS>] <Brief imperative summary>`  
**Linked Issue:** Ref #<!-- issue number. DO NOT use 'Fixes/Closes' if post-merge default-branch smoke receipts are required before closing the issue -->

---

## 2. Change Class

- [ ] `CONTRACT_GOVERNANCE` — Governance policy, decision records, or process templates.
- [ ] `CONTRACT_IMPLEMENTATION` — Wiring/implementation of pinned decisions/contracts.
- [ ] `DEFECT_FIX` — Resolving observed defect or spec contradiction.
- [ ] `BEHAVIOR_PRESERVING_REFACTOR` — Structural cleanups with invariant/bitwise parity.
- [ ] `CORRECTNESS_SEMANTICS` — Algorithmic correctness or mathematical fixes.
- [ ] `PERF_OPTIMIZATION` — Profile-driven compute/memory optimization.
- [ ] `RESEARCH_EXPERIMENT` — Preregistered research evaluation.

---

## 3. Scope & Boundary Declaration

**Expected file surface:**
<!-- Explicit list of files created or modified -->

- [ ] **No runtime/economic source touched** (for governance, documentation, or tooling PRs).
- [ ] **No out-of-scope files modified.** All touched files are directly owned by the requirements below.
- [ ] **No frozen OOS opened** unless authorized with an explicit receipt.
- [ ] **Python/Rust ownership boundary intact** (`tools/audit_python_boundary.py`).

---

## 4. Normative Requirement Traceability Matrix

Every requirement `R#` from the linked issue MUST terminate in an owning authority, implementation surface, verification gate, and evidence receipt.

| Req ID | Owning Authority | Implementation Surface | Verification Gate | Evidence Receipt / Status |
|---|---|---|---|---|
| `R1` | `docs/...` / `D-xxx` | `...` | `cargo test ...` / `...` | `PASS` / Receipt attached |
| `R2` | `docs/...` / `D-xxx` | `...` | `...` | `PASS` / Receipt attached |

---

## 5. Invariants & Failure Semantics

- **Mathematical / Semantic Invariants Verified:**
  - `I1`: <!-- Invariant formula / identity verified -->
  - `I2`: <!-- Invariant verified -->
- **Canonical Failure Semantics Verified:**
  - <!-- e.g. Invalid state -> canonical error code / OPEN_PIN -->

---

## 6. Verification Gates & CI Receipts

Exact active CI check identity on GitHub Actions: `check` (workflow: `ci`).

- [ ] `python3 tools/forbidden_names.py` (Gate 3) — **PASS**
- [ ] `python3 tools/audit_python_boundary.py` — **PASS**
- [ ] `cargo test --manifest-path v8-core/Cargo.toml` — **PASS** (<!-- test count --> passed)
- [ ] `cargo clippy --manifest-path v8-core/Cargo.toml --all-targets -- -D warnings` — **PASS**
- [ ] Monograph byte-identity probe (`tools/build_monograph.py`) — **PASS** / N/A

### Computation Budget (D-099)
<!-- For any check exceeding 5s or repeating an already-green suite, state the decision it could change and new semantic risk resolved -->
- **Check run:** 
- **Decision at risk:** 
- **Marginal decision value vs cost:** 

---

## 7. Evidence Artifacts

- [ ] PR requirement traceability table complete.
- [ ] Terminal test logs / receipts attached or recorded.
- [ ] Monograph rebuild verified if docs changed.
- [ ] No synthetic data or uncomputed metric references included.

---

## 8. Ambiguities & Disclosures

- **OPEN_PINs opened / escalated:** None / <!-- list if any -->
- **Divergences / Deviations:** None / <!-- list if any -->

---

## 9. V8 Guards & Merge Checklist

- [ ] I have not invented a new canonical error code, ontology, or parallel interface unless authorized by an `R#`.
- [ ] No uncertified economic claims (`NO_ECONOMIC_CLAIM` per Constitution Rule 12).
- [ ] No synthetic statistical metrics or fabricated trade markouts.
- [ ] CODEOWNERS review obtained from real repository maintainers (`@ddawnlll`).
- [ ] This PR does not auto-close the tracking issue if post-merge default-branch smoke validation is pending.
