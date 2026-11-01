# #389 evidence — a broken ledger no longer mints a certificate

PR [#501](https://github.com/ddawnlll/v8/pull/501) · branch `codex/issue-389-ledger-quarantine` · commit `c7383b4`
`app/cli.py` +51/−3 · new `tests/test_cli_status_ledger_quarantine_389.py` +153

## Root cause (confirmed on `main`)

`chain_ok` was consumed only inside a `print` f-string. The chain verdict never gated anything, so a
`BROKEN` chain still fell through to `PolicyCertificate.generate(...).render_ascii()` and `return 0`.
An empty ledger returned `0` early without any verdict at all.

## Regression test, both directions

| against | result |
|---|---|
| clean `main@a921da2` (test file copied into the baseline checkout) | **3 failed / 4 passed** — all three are `assert 0 == 3` |
| branch | **7 passed** in 1.37s |

The three failures are exactly the cases that matter: tampered first entry, broken predecessor digest,
and an empty ledger. The four that pass on both are the positive controls (a valid genesis replay
still verifies).

## Behaviour after the fix

- `EXIT_LEDGER_QUARANTINED = 3`; a broken chain prints a named quarantine result (entry index +
  `verify_chain` message) and returns 3.
- `PolicyCertificate` is not rendered on a quarantined chain.
- `EMPTY_LEDGER` is its own named state, no longer a silent success.
- No repair path rewrites history or re-seals an entry.

Full suite on the branch: **1014 passed, 9 skipped** (baseline 1007 + 7 new). `ruff` clean.
