# Execution setup — 5 parallel fixes

## Worktrees (one per issue, all based on `a921da2`)

| issue | branch | worktree |
|---|---|---|
| 476 | `codex/issue-476-wiring-closure` | `C:/Users/dresden/Documents/v8-wt-476` |
| 389 | `codex/issue-389-ledger-quarantine` | `C:/Users/dresden/Documents/v8-wt-389` |
| 495 | `codex/issue-495-g3-cell-honesty` | `C:/Users/dresden/Documents/v8-wt-495` |
| 477 | `codex/issue-477-capacity-routing` | `C:/Users/dresden/Documents/v8-wt-477` |
| 491 | `codex/issue-491-exit-leg-mark` | `C:/Users/dresden/Documents/v8-wt-491` |

The shared checkout `C:/Users/dresden/Documents/v8` is back on `main` holding the user's own
pre-existing uncommitted work (`baseline_git_state.txt`), and no agent works there.

## Incident (resolved, nothing lost)

The first launch did not set worktree isolation, so several agents shared the primary
checkout and `git switch -c` moved the tree under each other. All five were halted within
~3 minutes, before any commit was created. Consequences and disposition:

- **No commits were lost or misbranched** — every `codex/issue-*` branch was still at
  `a921da2` with zero commits ahead when checked.
- The agent working #495 stashed its own WIP as `issue-495 g3 work in progress`; that stash was
  applied into `v8-wt-495`, and the original entry is retained as a backup.
- The agent working #491 stashed the *pre-existing* worktree changes to get a clean baseline.
  That stash (`On main: pre-existing unrelated worktree changes`, 5 files) was popped back into
  `main`; `git status` now matches `baseline_git_state.txt` exactly.
- Relaunched with a real worktree per issue.

## Pre-existing repo condition worth noting

Local `main` (`a921da2`) is **7 commits ahead of `origin/main`** (`e1c7548`):

```
094dc6d  v8-next research: enforce cross-deliverable status agreement
75f2f80  v8-next research: pin arm config + repro command in run manifests
ddae043  v8-next research: ignore archived (superseded) arms
1ff0c67  v8-next research: verify real joins, per-arm audit gates
d6f43e6  v8-next research: validate arms.json against rendered metrics
0f0acf6  v8-next research: causal arm harness + audit lineage repair
a921da2  v8-next research: verify executed arms against the contract's effective registry
```

These are the user's own unpushed research commits, not part of any fix. Consequence: a PR
from a branch based on `a921da2` targeting `main` will show those 7 commits in its diff until
`git push origin main` is run. This goal does **not** push `main` — that is not part of the
brief. Recommended before review:

```bash
cd C:/Users/dresden/Documents/v8 && git push origin main
```

After that each PR's diff reduces to its own fix.
