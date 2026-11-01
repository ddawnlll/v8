# ACCEPTANCE — critical fixes (5 issues, 5 PRs)

Run id: `critical_fixes_20261101` · base `a921da2fdfb8254619b78840f80e969324f7cdf1` (branch `main`)
Goal id: `mvwyd3od-9vyse0`

## Gate enum
`PASS | FAIL | BLOCKED | NOT_APPLICABLE` — nothing else is permitted. No `PASS_WITH_LIMITATION`,
no `NOT_IDENTIFIABLE` in a gate cell (that is a *finding* verdict, used only for #491's claim).

## Scope

| # | title | PR | required end state |
|---|---|---|---|
| 476 | chain outputs IMPLEMENTED but unwired | 1 | named consumer edge into the benchmark path for the orphan modules + `tools/audit_wiring.py` static check (R3). R4 (process) explicitly out of scope. |
| 389 | status ledger fails self-verification yet renders a certificate | 1 | broken chain ⇒ explicit quarantine, no `PolicyCertificate`, non-zero exit |
| 495 | G3 cell measures regime robustness, not coverage | 1 | cell name, resolver and published basis agree |
| 477 | canonical capacity bound bypasses the swing contract | 1 | scaled projection can never publish a measured basis; module gains a real `src/` consumer |
| 491 | equity path drops closed-campaign exit P&L | 0 or 1 | only if rederivation says CONFIRMED |

## Hard rules
- One branch, one PR per issue. Branch name `codex/issue-<n>-<slug>` (matches the two existing PRs #496/#497). PRs are opened, **never merged**.
- Every fix carries a regression test that FAILS on `main` and PASSES on the branch. Both runs are recorded.
- Never write to `v8-core/`, `src/v8/`, or root `tests/`. `v8-next/` only.
- No economic claim, no score-semantics change, no gate forced to `PASS`. Fail closed.
- No hardcoded metrics / synthetic values / placeholder evidence.
- `docs/contracts/WIRING_COMPLETION_CONTRACT.md` referenced by #476 **does not exist** in the repo — do not cite it as authority; derive R3's rule from the issue text.

## Required artifacts
`audit_out/critical_fixes_20261101/`
- `ACCEPTANCE.md` (this file)
- `491_rederivation.md` — CONFIRMED | REFUTED | NOT_IDENTIFIABLE + quoted builder lines
- `<n>_evidence.md` per issue — root cause, diff stat, failing-on-main output, passing-on-branch output, PR URL
- `FINAL_REPORT.md` — per-issue outcome, PR URLs, gates, exit codes

## Verification commands
- `cd v8-next && uv run pytest -q` (full suite)
- `cd v8-next && uv run ruff check src tests`
- `git diff --name-only main...<branch>` (must stay inside `v8-next/`, no archived paths)
- `gh pr list --state open --json number,title,headRefName,url`
