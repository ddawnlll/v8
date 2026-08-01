"""V8 research runtime — Phase 2 deterministic baseline (vertical slice).

This package is the runnable vertical-slice gate demanded by the project
audit: a tiny but real path from tape -> MarketState -> Experts -> candidate
log -> acceptance -> canonical simulator -> lab report, all deterministic and
hash-bound. It contains no order-sending, no credentials, and no live path
(V8_CONSTITUTION rule 12; OPERATIONS_SPEC section 1).
"""

__version__ = '0.1.0'
