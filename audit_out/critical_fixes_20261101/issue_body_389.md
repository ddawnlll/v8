## Objective

Restore a self-verifying V8-next status ledger, or explicitly quarantine stale/corrupt ledger state so the dashboard never presents it as a valid evidence chain.

## Owning authority

- V8-next receipt and evidence-chain contracts
- Constitution Rule 5: verifiable physical artifacts
- Existing receipt/ledger integrity behavior in v8-next evaluation and storage modules

## Change class

CORRECTNESS_SEMANTICS

## Current state / Observed defect

At commit 1563d8955c6e9c47e3909037cdcdeb5961ffc800, running:

    uv run --project v8-next --extra dev python -m v8_next.app.cli status

reports:

    ledger: 13 entries  chain: BROKEN
    ENTRY_RECEIPT_INVALID at 0
    DIGEST_TAMPERED
    expected b2b5636042769a1f5442405c21e63293ca3819ca003608cc36017d606cc732e9
    stored   5e12587f5ee921e72879f465af7a33010ea79244f03c64de2b20622a91e24ea3

The dashboard still renders a latest benchmark certificate while the ledger chain is broken.

## Required end state

- A clean ledger verifies every entry from the genesis/first entry onward.
- Corrupt or stale ledger state is rejected/quarantined and cannot be summarized as valid evidence.
- The dashboard clearly separates latest report metadata from a valid evidence-chain status.
- No repair path rewrites history or fabricates a replacement receipt.

## Expected file / module surface

- v8-next/src/v8_next/app/cli.py
- v8-next/src/v8_next/evaluation/store.py
- v8-next/src/v8_next/evaluation/benchmark_receipt.py
- Relevant ledger/receipt tests

## Verification gates

    uv run --project v8-next --extra dev pytest -q v8-next/tests/test_cli.py v8-next/tests/test_store_models_and_duckdb.py
    uv run --project v8-next --extra dev python -m v8_next.app.cli status

Add tests for valid genesis replay, tampered first entry, broken predecessor digest, stale receipt, and clean quarantine behavior.

## Required evidence artifacts

- Revision-bound status output with a clean chain or explicit quarantine result
- Ledger replay/integrity test log
- No fabricated receipt or replacement digest

## Non-goals / forbidden scope

- Do not weaken digest verification.
- Do not delete history to make the chain green.
- Do not promote an economic claim.
- Do not use synthetic receipts in production/evaluation artifacts.

## Requirements

- R1: Verify the first ledger entry against its canonical contents.
- R2: Verify every subsequent predecessor/current digest relation.
- R3: Make broken-chain status authoritative and fail closed.
- R4: Preserve NO_ECONOMIC_CLAIM regardless of ledger repair outcome.

## Failure semantics

Corrupt or unverifiable ledger -> BROKEN / BLOCKED, never PASS.

## Base SHA

1563d8955c6e9c47e3909037cdcdeb5961ffc800

## Evidence

FIXED on PR #501 (open, unmerged, base `a921da2`).

- `EXIT_LEDGER_QUARANTINED = 3`; a BROKEN chain renders no `PolicyCertificate`; an empty ledger is its own named state instead of an early `return 0`.
- `tests/test_cli_status_ledger_quarantine_389.py`: 3 failed / 4 passed on clean `main@a921da2` (`assert 0 == 3`), 7 passed on the branch. Branch suite 1014 passed / 9 skipped.
- Full detail: `audit_out/critical_fixes_20261101/389_evidence.md`, `verify_389/`.
