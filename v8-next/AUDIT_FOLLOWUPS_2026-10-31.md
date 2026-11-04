# v8-next audit follow-ups (2026-10-31, status updated 2026-11-04)

> **Status update (2026-11-04):** items 1, 3, 4, 5, 6, 7 and 8 are resolved and verified;
> item 2 is partially resolved. Evidence: `audit_out/followup_remediation_2026-11-04/`
> (`REPORT.md`, `ACCEPTANCE_MATRIX.md`, `BEFORE_AFTER.json`, `SHA256SUMS`).
> No economic claim is minted by these changes.

Items below were **not** changed in the current bug-fix pass. Each needs a
product/spec decision, an unavailable data fixture, or a reproduction that does
not belong in the fast loop. They are not claims that the current behaviour is
correct.

| # | Location | Finding | Status 2026-11-04 |
|---|---|---|---|
| 1 | `swing_engine.py` | Bracket orders before position id | **PASS** - bracket identity and reduce-only verified by `tests/test_execution_safety_20261103.py` (10 passed). |
| 2 | `app/paper.py` | Late funding re-timed to receipt and applied to a later position | **PARTIAL** - replay charges at `max(boundary, receipt)`, refuses charges knowable only after the window, de-duplicates repeated boundaries; the paper path attributes when one position spans both instants and refuses when the exposure changed. Splitting one settlement across two exposures needs a boundary snapshot the capture does not hold. |
| 3 | `adapters/portfolio_backtest.py` | Funding mark could select a future close | **PASS** - causal as-of mark bounded to one bar of staleness; a missing mark is counted, not filled. |
| 4 | `evaluation/gate_resolution.py` | G5 Bonferroni covers only the four constructed variants | **PASS** - `SelectionFamily` (members + registration instant + basis, identity derived) is the only PASS route and its size must equal the pinned multiplicity; without one G5 returns `BLOCKED` / `MISSING_PROVENANCE_BOUND_SELECTION_HISTORY`. |
| 5 | `evaluation/reality_check.py` | `p_value = exceed / reps` can be exactly 0 | **PASS** - versioned reporting: `PLUS_ONE_V1` default, `LEGACY_EXCEED_OVER_REPS_V1` preserved for existing receipts, resolution and limitation published. |
| 6 | `evaluation/store.py` | Partial SQLite copy then fallback collision | **PASS** - fault-injection test proves the destination survives a mid-copy plus fallback failure and the temp file is removed. |
| 7 | `catalog_tape.py`, `test_swing_costs.py`, 26 test files | Hardcoded `/Users/hootie/src/v8` paths | **PASS** - one resolver (`adapters/tape_paths.py`) serves src and tests; 0 occurrences of the old prefix remain (was 47 in 32 files); a missing tape raises `FileNotFoundError`. |
| 8 | `adapters/portfolio_backtest.py` | Duplicate `_native_fill_records` | **PASS** - shared helper retained. |


Resolved in this pass and therefore absent from the table: Windows `fcntl`/
`resource`, the `/tmp` funding fixture, NX10 `.jsonl` tracking, evidence CRLF
hashes, empty `books/` skip, LONG signed slippage, denied-entry plan wedge,
stop-only bracket fail-open, duplicate/missing/off-grid funding charges,
settlement inclusive-end/contiguity, holdout burn lineage, G4 fabricated
balance, G7 same-bar look-ahead, DSR alphabetical selection, and the mypy gate.
