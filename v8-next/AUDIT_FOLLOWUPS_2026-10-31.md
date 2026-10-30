# v8-next audit follow-ups (2026-10-31)

Items below were **not** changed in the current bug-fix pass. Each needs a
product/spec decision, an unavailable data fixture, or a reproduction that does
not belong in the fast loop. They are not claims that the current behaviour is
correct.

| # | Location | Finding | Why not fixed | Evidence required to resolve |
|---|---|---|---|---|
| 1 | `src/v8_next/adapters/swing_engine.py:383` (submitted from `on_order_filled`; `active_position_id` assigned at `:465`) | Bracket stop/target appear to be submitted before the position id is known, so `position_id=None` may make them non-reduce-only. | Unverified: depends on Nautilus `OrderFilled` → `PositionOpened` callback ordering. | A callback-order test (or a run audit showing the native bracket order's `position_id`) and, if confirmed, submission from `on_position_opened` or a deferred bracket queue. |
| 2 | `src/v8_next/app/paper.py:256-280` | Late-received funding settlements are re-timed to receipt and applied to whatever position is open then, rather than the position exposed at the settlement boundary. | Documented design choice in the code ("never backdated"); changing it changes paper accounting semantics. | Spec decision on receipt-time vs boundary-time attribution, plus a test covering closed-before-receipt and opened-after-boundary cases. |
| 3 | `src/v8_next/adapters/portfolio_backtest.py:371` | Funding mark uses the first bar whose `end_ns >= boundary`, which can be a future close on irregular/shifted bars. | Not reproducible on the regular 1h tape used here; only affects off-grid boundaries. | An irregular/shifted-bar fixture proving the boundary is not a bar close, then use the last close with `end_ns <= boundary` or fail closed. |
| 4 | `src/v8_next/evaluation/gate_resolution.py:757,813,828` | G5 records `plan.multiplicity_trials` but its Bonferroni p-value is adjusted only over the four constructed variants. | Could be intentional: DSR uses `effective_independent_trials`; Bonferroni may deliberately cover only the constructed family. | Written G5 spec decision naming which family the Bonferroni correction covers; if trials are intended, adjust and add a `multiplicity_trials=100` regression test. |
| 5 | `src/v8_next/evaluation/reality_check.py:137` | White reality-check reports `p_value = exceed / reps`, which can be exactly `0.0`. | Statistical convention, not a runtime failure; changing it changes published p-values. | Agree the reporting convention (e.g. `(1+exceed)/(1+reps)` or `<1/reps`) and update the receipt contract and downstream readers together. |
| 6 | `src/v8_next/evaluation/store.py:1140-1168` | If the DuckDB SQLite copy fails partway through the per-table loop, the Polars fallback can hit `table already exists` for tables already created. | No existing test/trigger; only the success path is covered. | A fault-injection test that fails the Nth table and proves the fallback is idempotent (drop/recreate or transactionally roll back). |
| 7 | `src/v8_next/adapters/catalog_tape.py:48,54-55`; `tests/test_swing_costs.py:34`; 68 files under `v8-next/` | Hardcoded `/Users/hootie/src/v8` paths. | Portability issue, not a bug on the owner's checkout; slow/tape tests silently skip elsewhere. | Replace with repo-relative defaults or `V8_TAPE_PATH`/fixture overrides; add a path-portability check that does not require the tape. |
| 8 | `src/v8_next/adapters/portfolio_backtest.py:167` | Duplicate `_native_fill_records` definition was removed and replaced by the shared telemetry alias. | **Fixed**; listed only to close the audit item. | No follow-up. |

Resolved in this pass and therefore absent from the table: Windows `fcntl`/
`resource`, the `/tmp` funding fixture, NX10 `.jsonl` tracking, evidence CRLF
hashes, empty `books/` skip, LONG signed slippage, denied-entry plan wedge,
stop-only bracket fail-open, duplicate/missing/off-grid funding charges,
settlement inclusive-end/contiguity, holdout burn lineage, G4 fabricated
balance, G7 same-bar look-ahead, DSR alphabetical selection, and the mypy gate.
