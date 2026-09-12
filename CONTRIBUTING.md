# Development workflow

The authoritative runtime, evaluation and test surface is the Python product in
`v8-next/`. The Rust tree is quarantined under `legacy/v8-core/` as a frozen
non-canonical reference (read-only parity oracle at most), and the Python oracle
under `src/v8/` plus its historical `tests/` harness remain frozen.

Follow the [owner-authorized governance reset](docs/GOVERNANCE_RESET_V86_2026-09-07.md):
ordinary work uses `edit → relevant checks → commit to main`. Issues, PRs,
monograph regeneration and release certificates are not per-edit gates.

For an affected test from the repository root:

```sh
uv run --project v8-next --extra dev pytest -q v8-next/tests/FILE.py::test_name
```

For the local correctness gate on the product tree:

```sh
uv run --project v8-next --extra dev ruff check v8-next/src v8-next/tests
uv run --project v8-next --extra dev mypy v8-next/src
```

The boundary is registered as D-162 (issue #409): `v8-next/` is the product,
`legacy/v8-core/` is historical. Do not restore Rust-first wording anywhere;
a boundary change without a registered decision is the #409 defect.
GitHub Actions are retired; verification is local.

## Merge authority (2026-09-11 / D-163)

**Autonomous merge is authorized.** Agents and workers may merge verified work
into `main` locally without human approval, including clearing a blocked
dependency. The former PR-first / "no autonomous merge" rules are void. Full
text: [governance notice](docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md).

Preconditions: the change is verified; the target tree is clean for the touched
paths; the branch is not stale-and-superseded; conflicts are resolved in the
worktree. Direct `git push` to `main` remains the human owner's action — agents
merge locally and never publish.

Format touched Python code, and retain causality, arithmetic, cache integrity,
durability and authority checks. Do not fabricate market/economic evidence or
weaken assertions to improve timings. Quarantined Rust receipts and baselines
are historical evidence and must never be cited as current product behavior.

GPU, release, frozen-oracle differential, and monograph checks belong to their
explicit risk/release boundaries. See [the product boundary](v8-next/AGENTS.md)
and [the quarantined Rust reference](legacy/v8-core/README.md).
