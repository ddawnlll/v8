# V8.2 Parity and Identity Specification

**Status:** PROVISIONAL_DECISION (D-079). This contract defines what it means
for the V8.2 compute core to "agree with" V8.0, and what a hash identifies once
two implementations exist. It is the acceptance instrument for every migration
stage in `COMPUTE_CORE_SPEC` §8. It adds no economic claim (rule 12).

## 1. Two implementations, one semantics

V8.2 does not replace V8.0 by assertion. It replaces it by **demonstrated
agreement on the same inputs**, one layer at a time. Until a layer's parity
gate passes, the Python implementation is normative and the Rust one is a
candidate.

This is the shape the evaluator protocol already requires of itself — a slow,
transparent reference alongside a fast implementation, with semantic parity as
the acceptance condition (`RECOVERABLE_REGRET_PROTOCOL` §7). V8.2 applies the
same discipline to the runtime.

## 2. The oracle

`src/v8/` at the V8.2 branch point is the **reference implementation**. It is:

- **Frozen for behaviour.** No optimization, no representation change, no
  refactor lands in it during the migration. A change that alters any emitted
  value invalidates every parity result recorded against it.
- **Permitted to be slow.** An oracle must be *correct*, not fast. The costs in
  `PERFORMANCE_AUDIT_V82` are not defects of the oracle role.
- **Repaired only for correctness.** A genuine wrong-value bug is fixed in the
  oracle first, the fix is registered, and every affected parity result is
  re-run. Fixing it only in Rust would silently make the oracle wrong.
- **Retired, not deleted**, when V8.2 is certified: it becomes an archived
  reference under its pinned code hash, reachable by checkout for forensics.

## 3. Parity is value-level, not hash-level

> **Two implementations are in parity for a stage when every emitted value is
> bit-identical, field by field, on the same inputs.**

- Floating point: equality of the IEEE-754 bit pattern, not `==`. This makes
  `-0.0` distinct from `0.0` and makes any NaN payload difference a failure.
  Tolerance-based comparison is **not** permitted anywhere in the parity path.
- Integers, enums, strings, and clocks: exact equality.
- Absence: a field that is absent in one implementation and present-but-null in
  the other is a failure, not a match (`MARKET_STATE_CONTRACT` §4 — null is
  data absence, not zero).
- Ordering: sequences compare element-wise in order. Set-like fields are
  compared after the canonical sort each implementation already applies.

**Hashes are excluded from the parity comparison** for the reason in §4. A
parity run compares the values a hash would cover, which is strictly stronger:
equal values with different hash encodings pass; different values with
colliding hashes cannot pass.

## 4. Identity in V8.2: hash the bits, not the decimals

V8.0 defines every identity as
`sha1_hex(json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str))`.
The decimal rendering of each float is therefore part of `state_id`,
`lineage_hash`, `simulator_hash`, and every ledger hash downstream.

That rendering is runtime-specific. Measured on eight representative values,
**seven of eight differ** between CPython's `json` encoder and Rust's default
`f64` formatting (`PERFORMANCE_AUDIT_V82` §8) — both shortest-roundtrip
correct, differing only in exponent-notation thresholds. A second
implementation that reproduces every value exactly would still produce
different hashes.

**Decision.** The V8.2 canonical hash is computed over a byte encoding that is
representation-independent:

- `f64` contributes its 8 IEEE-754 bytes, little-endian. `-0.0` and `0.0` are
  distinct. A NaN is normalized to a single declared payload before hashing so
  that identity is total.
- Integers contribute fixed-width two's-complement bytes; clocks are `i64`
  nanoseconds.
- Strings contribute UTF-8 bytes prefixed by their byte length.
- Composites contribute a declared tag, an element count, and their elements in
  canonical order.

The digest function stays SHA-1 for continuity of tooling; it is not a security
boundary, and changing it is a separate decision.

### 4.1 The V8.0 ↔ V8.2 hash discontinuity is declared

V8.2 hashes will not equal V8.0 hashes for identical values. This is
**intended**. A version boundary is precisely where identities are permitted to
change (`PERSISTENCE_REPLAY_SPEC` §4: a code change that alters the event
stream requires a version bump). The alternative — reimplementing CPython's
`float_repr` and encoder thresholds in Rust to preserve hash continuity — buys
comparability of hash strings across a boundary where the values are already
compared directly, and costs a compatibility layer with no research value.

Consequences that must be honoured rather than discovered:

1. Evidence artifacts produced under V8.0 keep their V8.0 hashes. They are not
   re-hashed and not migrated.
2. A V8.2 artifact never claims a V8.0 hash and vice versa; the hash encoding
   version is recorded in every artifact header
   (`LEDGER_FORMAT_SPEC` §3).
3. Cross-version comparison of runs is done on **values**, via the parity
   harness, never by comparing identity strings.

## 5. The acceptance gate

A migration stage (`COMPUTE_CORE_SPEC` §8) passes when all of the following
hold on the declared fixture set:

| # | Condition |
|---|---|
| G1 | Value-level bit parity (§3) on every emitted record of that stage |
| G2 | Parity holds on **every** bar / candidate / cell, not a sample — no aggregate-only comparison |
| G3 | Parity holds on at least one synthetic fixture **and** one real verified tape |
| G4 | Determinism: two Rust runs of the same request are byte-identical |
| G5 | Backend invariance: values are identical across thread count and, where a GPU backend exists, across backends (`COMPUTE_SCHEDULING_SPEC` §5) |
| G6 | Failure modes agree: an input that fails closed in V8.0 (future row, unsorted batch, degenerate geometry) fails closed in V8.2 with the same classification |

G6 is not optional. An implementation that silently accepts what the reference
refuses has not reproduced the reference's semantics; fail-closed behaviour is
part of the contract, not an implementation detail.

### 5.1 Fixture set

- The synthetic tape (`synth.make_synthetic_tape`), several seeds and lengths,
  including the degenerate short-tape cases that exercise warmup absence.
- At least one verified real multi-symbol tape from the certified dev dataset.
- The randomized-path generator already used for the independent reference walk
  (`RECOVERABLE_REGRET_PROTOCOL` §7), reused rather than rewritten.

### 5.2 Harness placement

The harness is **Python-driven** and lives with the tests: it runs the V8.0
implementation in-process, invokes the V8.2 binary, and compares. The V8.0 test
suite is not ported to Rust — it encodes the semantics and is more valuable
pointed at both implementations than duplicated in one.

## 6. What re-versions

| Change | Re-versions |
|---|---|
| Hash byte-encoding (§4) | every V8.2 identity; declared once at the version boundary |
| A feature formula | that feature's `feature_version`, its state identity, everything downstream |
| A predicate IR compilation rule | the compiled predicate's version and every cell that consulted it |
| Ledger tiering policy | the artifact header version only, never a value |
| Backend selection (CPU/GPU), thread count | **nothing** — by G5 these cannot change a value |

The last row is the load-bearing one: scheduling is an implementation detail
precisely because backend invariance is gated, and it stops being one the
moment G5 is relaxed.

## 7. Cheap executable tests

1. A float fixture covering the eight values in `PERFORMANCE_AUDIT_V82` §8 plus
   subnormals, both zeros, and NaN: the V8.2 encoder produces identical bytes
   on both platforms it is built for.
2. Mutating one OHLC digit anywhere in a fixture tape changes the V8.2
   `state_id` for every state that consumed it, and no other.
3. A deliberately-injected off-by-one in a ported feature is caught by G2 (this
   is a test of the harness, run against a mutant build).
4. A run whose values are identical but whose float rendering differs produces
   the **same** V8.2 hash — the property §4 exists to obtain.
5. The oracle-freeze check: the V8.0 tree hash recorded in a parity result
   matches the V8.0 tree hash at the time the result is cited.

## 8. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** the float-rendering divergence (7 of 8 values)
  and the resulting hash non-portability, measured with CPython 3.14.0 and
  rustc 1.96.0-nightly (`PERFORMANCE_AUDIT_V82` §8).
- **PROJECT_EVIDENCE_SUPPORTED:** the dual-implementation parity pattern is
  already exercised in V8.0 — the cached and uncached MarketState paths are
  held to full state equality on every bar (`tests/test_state_cache_identity.py`),
  and an independently-derived reference walk agrees with the canonical
  simulator on randomized paths (D-071).
- **DESIGN_INFERENCE:** the bit-pattern encoding, the gate list, and the
  decision to accept hash discontinuity at the version boundary.
- **Not claimed:** that value parity implies the V8.2 engine is correct in any
  sense beyond "agrees with V8.0". If the reference is wrong, parity reproduces
  the error. Parity is a migration instrument, not a validity argument.
