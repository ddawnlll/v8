# Follow-up remediation report (2026-11-04)

Run directory: `v8-next/audit_out/followup_remediation_2026-11-04/`
Baseline commit: `1fa78e89612a7728e8d86a85c44797bd2b6e1e48` on
`fix/v8-next-critical-execution-gate-integrity`. The working tree was preserved; nothing was
reset, cleaned, or stashed.

## Headline

Seven follow-ups are resolved and verified (#1, #3, #4, #5, #6, #7, #8). #4 resolves by making
provenance-bound family membership the only route to a PASS and failing closed without it. #2 is
partial: the replay and paper paths now refuse a charge that would land on a different trade, but
splitting one settlement across two exposures still needs an exposure snapshot the capture does
not hold. Nothing here mints an economic claim; `NO_ECONOMIC_CLAIM` stands.

## What changed

| Follow-up | Status | Change |
|---|---|---|
| #1 bracket identity / reduce-only | PASS | Verified only; no code change needed. |
| #2 receipt-time funding attribution | PARTIAL | `_plan_funding_events` charges at `max(boundary, receipt)`, drops charges knowable only after the window, de-duplicates repeated instrument/boundary records, and publishes `funding_receipt_shifted`, `funding_receipt_unknown`, `funding_duplicate_boundary`. The paper path attributes a delayed settlement when the same position spans both instants and refuses when the exposure changed. |
| #3 causal funding marks | PASS | `_causal_funding_proxy`: latest close at or before the boundary with availability not later than the boundary, one-bar staleness bound, explicit `None`, published basis label. |
| #4 G5 selection family | PASS | `SelectionFamily` binds members, registration instant and basis into a derived identity. Without one the gate returns `BLOCKED` / `MISSING_PROVENANCE_BOUND_SELECTION_HISTORY`; with one whose size matches the pinned multiplicity, DSR and Bonferroni decide it. |
| #5 nonzero finite-bootstrap p-values | PASS | `PLUS_ONE_V1` default, `LEGACY_EXCEED_OVER_REPS_V1` preserved, resolution and limitation published, WRC library path labelled a raw diagnostic. |
| #6 DuckDB atomic fallback | PASS | Fault-injection: destination preserved after a mid-copy failure plus a failing fallback; temp file removed; exported table set and row counts reconcile. |
| #7 portable tape paths | PASS | One resolver (`v8_next/adapters/tape_paths.py`) covers src and tests: explicit > `V8_DATA_ROOT` / `V8_TAPE_ROOT` / `V8_TAPE_PATH` > repository-relative default, with `FileNotFoundError` on a missing tape. The old absolute prefix now occurs 0 times (was 47 in 32 files). |
| #8 shared fill helper | PASS | Verified only. |

## Before and after (measured, not asserted)

`BEFORE_AFTER.json` is produced by executing both expressions on the same inputs:

- Reality check, 0 exceedances in 19 replications: `0.0` before, `0.05` after. 2/3: `0.6667`
  before, `0.75` after (the legacy test value changed accordingly).
- G5 on a passing stress diagnostic: `PASS` before, `BLOCKED` after, with
  `stress_diagnostic_passed = true` proving the block is about provenance, not performance.
- HEAD's own tests still pass against HEAD's source (`HEAD_baseline_behaviour.log`, 4 passed),
  so the legacy behaviour is genuinely different and not a test-side illusion.

## Verification

- Fast suite: 1125 passed, 9 skipped, 506 deselected.
- Full suite (slow included): 1575 passed, 64 skipped, 1 failed (pre-existing).
- Ruff: clean.
- Full suite (slow included): 1577 passed, 64 skipped, 1 failed — the failure reproduces at
  HEAD, so it is pre-existing and recorded `FAIL`.
- mypy: 19 errors both at HEAD and now, in the same files (pre-existing `pywin32`, `Decimal`
  conversions, one `float | None`); no new type errors.
- Performance: funding planning 7.12 s -> 0.0043 s on a 35,040-bar / 4,379-row case after
  bisecting bar end timestamps and caching them per instrument; semantics unchanged.
- DuckDB 2.0.0 and arch 8.0.0 were installed into `v8-next/.venv` for this run so the optional
  tests executed rather than skipped.

## Open items and why they are not PASS

1. **#2 exposure split.** When two exposures share one settlement, the charge must be split by
   the time each was open. The capture holds no boundary snapshot, so the code refuses instead
   of guessing and the follow-up stays partial.
2. **#4 default state.** No provenance-bound family exists in this repository, so G5 still
   returns `BLOCKED` in practice even though the capability and its refusal rules are tested.
3. **Full suite.** `tests/test_economic_benchmark.py::test_mechanics_metrics_and_capacity`
   fails on a `data_resolution` string assertion. It fails identically at HEAD
   (`HEAD_preexisting_failure.log`), so it is pre-existing, but it is recorded `FAIL`, not PASS.
4. **Real-tape economic verification.** `NOT_APPLICABLE` for this run: no protected window was
   opened and no OOS data was read.

## Artifacts

`ACCEPTANCE.md`, `ACCEPTANCE_MATRIX.md`, `BEFORE_AFTER.json`, `MEASURED.json`, `REPORT.md`,
`SHA256SUMS`, `SPEC_DECISIONS.md`, `TEST_RESULTS.md`, `FINAL_DELIVERY_TR.md`, plus the raw
`*.log` files and `build_artifacts.py` that derives the tables from those logs.
