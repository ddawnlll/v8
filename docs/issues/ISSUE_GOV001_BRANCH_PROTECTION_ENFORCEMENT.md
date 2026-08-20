# [GOV/DEFECT] Issue #GOV-001: Branch Protection Enforcement & Policy Parity

**Status:** READY / PROPOSED  
**Issue Type:** `GOVERNANCE` / `DEFECT`  
**Change Class:** `GOVERNANCE`  
**Labels:** `type:defect`, `type:governance`, `triage`, `risk`  
**Owning Authority:** `WORK_ITEM_POLICY.md` §1–6 (Branch Protection & Direct Push Prohibition), Decision `D-099`, Decision `D-117`.

---

## 1. Objective
Audit and enforce GitHub repository branch protection rules on `main` to ensure direct pushes are technically blocked on the remote repository, requiring all future changes to strictly follow the canonical `feature-branch -> PR -> verification check -> owner review -> merge` governance workflow.

---

## 2. Owning Authority
- **Primary Policy:** [`docs/WORK_ITEM_POLICY.md`](docs/WORK_ITEM_POLICY.md) §1–6 (Collaborative Workflow & Merge Rules).
- **Contributing Guide:** [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 3. Current State
- `WORK_ITEM_POLICY.md` mandates that direct pushes to `main` are prohibited. However, local pushes were accepted directly without triggering remote PR branch protection rejection, revealing a divergence between declared policy and repository configuration.

---

## 4. Required End State
1. **Branch Protection Alignment:**
   - Enforce branch protection on `origin/main` requiring status checks to pass and direct pushes to be rejected.
2. **Local Workflow Enforcement:**
   - All subsequent audit implementation issues must branch from `main` (e.g. `feat/aud-002-lineage`), create PRs, and merge only after green CI checks.

---

## 5. Verification Gates
1. GitHub branch protection rules enabled for `main`.
2. Direct push attempt to `main` correctly returns a remote rejection error.

---

## 6. Required Evidence Artifacts
- Branch protection configuration receipt.

---

## 7. Non-Goals / Forbidden Scope
- Does not modify runtime Rust codebase.
