"""V8.2 parity harness (PARITY_AND_IDENTITY_SPEC §5).

Python-driven: runs the V8.0 oracle in-process, invokes the V8.2 compute-plane
binary, and compares every emitted value bit-for-bit. Lives with the tests so
the V8.0 suite keeps pointing at both implementations rather than being ported
(PARITY_AND_IDENTITY_SPEC §5.2).
"""
