# Acceptance contract

Gate enum: PASS | FAIL | BLOCKED | NOT_APPLICABLE. Never mark unavailable verification PASS. No economic claim without authority. Audit follow-ups #1–#8 and IDs FUND-01–04, MARK-01–03, G5-01–03, RC-01–03, PATH-01–02, DB-01–02, REG-01–04 require concrete evidence. Orphan, unmatched, reconciliation, and hash counts must be explicit or explained where applicable.

Required artifacts: REPORT.md, SPEC_DECISIONS.md, ACCEPTANCE_MATRIX.md, BEFORE_AFTER.json, TEST_RESULTS.md, SHA256SUMS; update AUDIT_FOLLOWUPS_2026-10-31.md after verification. Run directory: v8-next/audit_out/followup_remediation_2026-11-04/. No frozen market-data window or tape is required for baseline mechanics; do not claim real-tape verification if unavailable.

Final delivery language: Turkish. Sections: HEAD and working tree; eight statuses; specification decisions; files changed; before/after; DuckDB and arch; fast suite/lint/mypy; risks; artifacts; COMPLETE/PARTIAL/BLOCKED. Baseline and verification: v8-next/.venv/bin/pytest targeted tests, then fast suite, Ruff and mypy. Preserve immutable evidence and current changes.
