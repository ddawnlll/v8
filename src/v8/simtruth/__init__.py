"""simtruth — canonical Level-1 simulation truth (reference engine).

This package is the scalar reference implementation of V8's single source of
economic truth (SIMULATION_TRUTH_SPEC). It is the *truth* any faster or richer
path (vectorized, DuckDB, Nautilus-class engines) must reproduce exactly under
a parity test; it is never the sole path and never bypassed.

Modules:
- sim.py        deterministic scalar simulation core: gap semantics, same-bar
                stop-wins (conservative), fail-closed, costed, tiered returns
                (nominal / execution / net / net_r), funding tape
- market.py     hashable market-tape builder (one row per completed candle;
                canonical SHA-256 over text serialization — parquet is not
                byte-stable)
- events.py     candidate event records
- features.py   candidate features
- indicators.py indicator library

Provenance: vendored from the V7 lab (`/Users/hootie/src/v7/lab/`,
2026-08-01); only module import paths were rewritten (`from lab.*` ->
relative). Content is otherwise unchanged.

Authority status: ENGINEERING-ONLY. V7's simulation authority is recorded as
FAIL/BLOCKED with `economic_verdict: INVALID_NOT_CERTIFIED` (project evidence
audit). Before this package may act as V8's canonical economic authority it
must pass V8's own verification suite (differential oracle, full-vs-window
replay parity, cost-model binding) and the authority record must be renewed
(OPERATIONS_SPEC section 1; ROADMAP Phase 4/6). Until then it is a challenger
implementation, not certified truth.
"""
