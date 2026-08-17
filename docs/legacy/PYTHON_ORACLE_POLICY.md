# Python oracle boundary

**Status:** LOCKED_INVARIANT candidate (D-100).

`src/v8/` is no longer the runtime implementation. `v8-core/` owns the
authoritative request and verification path. The Python tree remains only as a
frozen historical parity oracle and as an explicit dependency of legacy
research tooling whose outputs are not runtime authority.

The lock is recorded in `PYTHON_ORACLE_LOCK.json`. A change to `src/v8/`
requires a new registry decision, a changelog entry, and a new tree hash. A
silent edit is a boundary failure.

Allowed Python execution is intentionally narrow:

- `tools/build_monograph.py` and its Markdown compiler dependencies;
- `tools/forbidden_names.py` and `tools/audit_python_boundary.py`;
- explicit, operator-invoked legacy data/diagnostic scripts that import the
  oracle and never enter `v8-core` or a live path.

The Python pytest/parity suites are not general CI gates. The one explicit
exception is `tests/parity/test_parity_fill_limit.py`: it builds the release
Rust binary, uses the frozen oracle only as an external differential witness,
and bit-compares every outcome field for the `FILL_AT_LIMIT` fixture. The
boundary audit permits that exact command and rejects every other pytest or
Python-`v8` CI invocation. Removing or rewriting the
oracle is deferred until every remaining legacy consumer has an owned Rust or
tooling replacement; deleting it prematurely would destroy the independent
historical reference used to interpret the S0–S7 parity record.
