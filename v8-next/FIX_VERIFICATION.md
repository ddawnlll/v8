# Six issue fixes — verification

Priority reflects potential damage to evidence and stored data, then input integrity and reporting; it is not a claim of exhaustive repository coverage.

1. **Destructive DuckDB export:** exporting onto the source or failing after deleting an existing destination could destroy data. `test_export_never_overwrites_source_or_existing_destination_on_failure` checks both; `test_export_fallback_after_partial_copy` injects a partial scanner failure and verifies a real DuckDB export.
2. **Stale tape SHA:** same-size, same-mtime rewrites returned a cached digest. `test_hash_recomputed_after_metadata_preserving_rewrite` checks the new content hash.
3. **Malformed funding:** invalid decimals or interval strings could abort loading instead of being counted as dropped. `test_malformed_funding_is_counted_not_crashed` exercises both cases.
4. **Nonfinite funding rates:** NaN and infinities could enter the funding feed. `test_nonfinite_funding_rate_is_dropped` checks all three.
5. **Invalid funding intervals:** zero, negative and nonfinite intervals could be accepted as measured. `test_invalid_funding_interval_is_dropped` checks all four cases.
6. **Wrong intersection drop counts:** missing-from-union was reported as rows removed by intersection. `test_loader_reports_intersection_drops_instead_of_trimming_silently` checks the corrected per-leg attribution.

Verification on this checkout:
- `uv run --locked --extra dev --extra research pytest -q tests/test_data_integrity_regressions.py tests/test_store_models_and_duckdb.py --disable-warnings`: 20 passed.
- `uv run --locked --extra dev pytest -q -m slow tests/test_tape_identity_nx01.py::test_loader_reports_intersection_drops_instead_of_trimming_silently`: 1 passed.
- `uv run --locked --extra dev pytest -q --disable-warnings --maxfail=3`: 1019 passed, 9 skipped, 496 deselected; research extras were also present in the environment.
- `uv run --locked --extra dev ruff check src tests`: passed.
- `uv run --locked --extra dev mypy src/v8_next/evaluation/multitape.py src/v8_next/evaluation/store.py`: passed.
- `uv run --locked --extra dev mypy src`: failed with three errors in the pre-existing uncommitted `adapters/expert_strategy.py` and an unused-ignore error in `world/foundry.py` while research extras were installed. These files were not changed in this fix pass. Full-project type checking remains unresolved.
