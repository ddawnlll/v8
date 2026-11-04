# Acceptance matrix

Gate enum: `PASS | FAIL | BLOCKED | NOT_APPLICABLE`. A skipped or unavailable verification is never recorded as PASS.

| Follow-up | Status | Evidence |
|---|---|---|
| #1 | `PASS` | Bracket identity and reduce-only enforcement verified by the existing focused tests. |
| #2 | `PARTIAL` | Replay charges a settlement at max(boundary, receipt), refuses a charge only knowable after the window, and de-duplicates repeated instrument/boundary records. The paper path now attributes a delayed settlement when the same position is open at the boundary and at receipt, and refuses when the exposure changed in between. Splitting a charge across two exposures still needs an exposure snapshot the capture does not hold. |
| #3 | `PASS` | Funding marks use the latest bar closed at or before the boundary, bounded to one bar of staleness; a missing mark is counted, never filled, and the basis is labelled a historical model, not a venue mark. |
| #4 | `PASS` | G5 now requires a provenance-bound SelectionFamily whose identity is derived from its member list and registration instant. Without one the gate returns BLOCKED / MISSING_PROVENANCE_BOUND_SELECTION_HISTORY while still publishing the diagnostics; with one whose size matches the pinned multiplicity, DSR and Bonferroni decide the gate. A family narrower or wider than the pinned multiplicity is refused. |
| #5 | `PASS` | Monte Carlo p-values are versioned: PLUS_ONE_V1 is the default, LEGACY_EXCEED_OVER_REPS_V1 reproduces the old 2/3 and 0.0 values, resolution and limitation are published, and the library WRC path is labelled a raw finite-bootstrap diagnostic. |
| #6 | `PASS` | Injected mid-copy scanner failure plus fallback failure preserves the destination bytes and removes the temp file; the earlier partial-copy test also passes with DuckDB installed. |
| #7 | `PASS` | A single resolver (explicit > V8_TAPE_PATH/V8_TAPE_ROOT/V8_DATA_ROOT > repository-relative default) replaces every machine-specific path: 0 occurrences of the old absolute prefix remain in src/ and tests/, a missing tape raises FileNotFoundError, and relative overrides resolve against the repository rather than the shell CWD. |
| #8 | `PASS` | Single shared fill-record helper used by both execution paths; existing tests pass. |

## Acceptance IDs

| ID | Scenario | Result | Evidence |
|---|---|---|---|
| FUND-01 | Delayed settlement is not charged at its venue boundary | `PASS` | `tests/test_funding_boundary_attribution_20261104.py::test_delayed_settlement_is_charged_at_receipt_not_boundary` |
| FUND-02 | A charge only knowable after the window is not applied | `PASS` | `::test_charge_known_only_after_window_is_not_applied` |
| FUND-03 | Repeated instrument/boundary records are not double counted | `PASS` | `::test_each_settlement_is_charged_once` |
| FUND-04 | Paper replay refuses a charge whose exposure changed before receipt | `PASS` | `tests/test_delayed_funding_fail_closed_20261104.py` |
| MARK-01 | Mark uses no future bar | `PASS` | `::test_mark_never_uses_a_future_bar` |
| MARK-02 | Stale mark beyond one bar is refused, not carried | `PASS` | `tests/test_funding_causal_mark_20261104.py` |
| MARK-03 | Missing mark is counted and labelled | `PASS` | `funding_mark_basis` / `funding_missing_mark` in `portfolio_backtest` |
| G5-01 | Missing selection provenance cannot pass | `PASS` | `tests/test_g5_family_block_20261104.py` |
| G5-02 | A 100-trial declared family does not widen the four stress variants | `PASS` | same file, `test_unbound_hundred_trial_family_cannot_pass` |
| G5-03 | Contradictory effective-independent count is rejected | `PASS` | same file |
| G5-04 | A provenance-bound family is the only PASS route; size must match the pinned multiplicity | `PASS` | `::test_provenance_bound_family_is_the_only_pass_route`, `::test_family_size_must_match_pinned_multiplicity` |
| RC-01 | Zero exceedances cannot report p = 0 | `PASS` | `BEFORE_AFTER.json` (0/19 -> 0.05) |
| RC-02 | Legacy convention still reproducible | `PASS` | `::test_legacy_identity_and_invalid_input` |
| RC-03 | Reporting version and resolution are published | `PASS` | `reality_check_diagnostic` output |
| PATH-01 | Explicit > env > repository default resolution | `PASS` | `tests/test_tape_path_resolution_20261104.py` |
| PATH-02 | Missing tape is an explicit failure, not a silent default | `PASS` | same file, `FileNotFoundError` |
| PATH-03 | No machine-specific absolute path remains in src/ or tests/ | `PASS` | `rg` count 0 after the sweep (seeded from 47 occurrences in 32 files) |
| DB-01 | Mid-copy failure preserves destination | `PASS` | `tests/test_duckdb_atomic_20261104.py` |
| DB-02 | Table set and row counts reconcile after export | `PASS` | `tests/test_data_integrity_regressions.py` |
| REG-01 | Fast suite | `PASS` | `fast_suite.log` |
| REG-01b | Full suite including slow tests | `FAIL` (pre-existing, reproduced at HEAD) | `full_suite.log`, `HEAD_preexisting_failure.log` |
| REG-02 | Ruff | `PASS` | `ruff.log` |
| REG-03 | mypy does not regress vs HEAD | `PASS` | 19 errors at HEAD and 19 now, same files |
| REG-04 | Legacy behaviour change is demonstrated, not asserted | `PASS` | `BEFORE_AFTER.json` + `HEAD_baseline_behaviour.log` |

## Explicit non-PASS items

- Follow-up #2 splitting one settlement across two exposures: `BLOCKED` (needs an exposure snapshot).
- Follow-up #4: `BLOCKED` by default; passing requires a provenance-bound family, which this repository does not hold.
- Full suite: `FAIL` on `test_mechanics_metrics_and_capacity`, reproduced unchanged at HEAD.
- Real-tape economic verification: `NOT_APPLICABLE` for this run; no protected window opened.
