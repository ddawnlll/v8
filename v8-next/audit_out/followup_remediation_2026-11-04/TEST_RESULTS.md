# Test results

Environment: Python 3.12.12, pytest 9.1.1, NautilusTrader 2.0.0rc4, duckdb 2.0.0, arch 8.0.0 (`versions.log`). Baseline commit `1fa78e89612a7728e8d86a85c44797bd2b6e1e48`.

- Full suite including slow tests: **1577 passed, 64 skipped, 1 failed**, exit `1`. The single failure is `tests/test_economic_benchmark.py::test_mechanics_metrics_and_capacity`, reproduced unchanged at HEAD (`HEAD_preexisting_failure.log`), so it is pre-existing and recorded `FAIL`, never PASS.
- Fast suite: **1127 passed, 9 skipped, 506 deselected**, exit `0`.
- Ruff: clean (exit `0`).
- mypy: 19 errors now vs 19 at HEAD, identical files, so no new type regression.
- DuckDB and arch were installed into `v8-next/.venv` with uv for this run; the DuckDB fault-injection and fallback tests executed rather than skipping.

## Per-area logs

| Area | Log | Counts |
|---|---|---|
| Funding boundary attribution | `funding_after.log` / `funding_regressions.log` | 8 passed |
| DuckDB atomic fallback | `duckdb_after.log`, `duckdb_initial.log` | 13 passed |
| G5 / reality check | `stat_target.log`, `stats_after.log` | 9 passed |
| Tape path resolution | `path_after.log`, `path_regressions.log` | 22 passed, 1 skipped |
| Execution safety | `bracket_tests.log` | 10 passed |
| HEAD baseline behaviour | `HEAD_baseline_behaviour.log` | 4 passed (legacy semantics) |

Every log's SHA-256 is in `MEASURED.json` and `SHA256SUMS`.

## Performance impact

Measured on a 35,040-bar leg with 4,379 funding rows (`performance.log`): funding planning went from a per-row full-leg scan (7.12 s median, measured on the pre-bisect version) to 0.0043 s after bisecting the bar end timestamps and caching them per instrument — roughly a 1,650x reduction, and the check itself is identical. The standalone mark helper still builds its own index (~0.39 ms per cold call); the planner never pays that. No other behaviour changed and no test became slower (fast suite stayed ~6 s).
