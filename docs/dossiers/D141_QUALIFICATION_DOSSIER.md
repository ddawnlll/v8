# D-141 Qualification Dossier

**Decision:** D-141 Expert Proving Ground & Alpha Refinery
**Scope:** deterministic semantic qualification only
**Economic authority:** `NO_ECONOMIC_CLAIM`

## Test-only boundary

Pilot qualification runs only in Rust test builds. It emits no production CLI
output or persistent synthetic receipt; the scoped verification command is:

```text
cargo test --manifest-path v8-core/Cargo.toml qualification::tests
```

## Pilot result contract

| Expert | Formal manifest | Semantic verdict | Economic verdict |
|---|---|---|---|
| `failed_breakout:v1` | D-141 test manifest | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `fib_projection_reversal:v1` | D-141 test manifest | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `ichimoku_cloud:v2` | D-141 test manifest | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |

The current suite executes 3 pilot witnesses against a 28-witness registry (3/28 = 10.71% manifest coverage). The other registered witnesses are intentionally not counted as passed or failed until they receive their own Behavior Card, scenarios, and manifest. Registry manifest coverage is reported separately from the executed-test pass rate.

## Gate interpretation

- EWQ-01…06 are semantic qualification gates. A failed canonical, metamorphic, or critical mutation control falsifies qualification.
- EWQ-07 (sealed challenge) and EWQ-08 (statistical no-regression) remain `UNRESOLVED` in the pilot run.
- EWQ-09 (real-tape attribution) is `NOT_APPLICABLE` in this synthetic semantic run.
- EWQ-10 (frozen economic OOS) is `BLOCKED`; D-141 rejects absent authority rather than opening substitute data.

## Issue-to-receipt traceability

| Issue | Implementation surface | Verification / receipt |
|---|---|---|
| #285–#287 | manifests, scenarios, runner | manifest/run/scenario hashes |
| #288–#291 | metamorphic, mutation, generator, EAST | relation, kill, coverage, counterexample receipts |
| #292–#294 | statistics, risk, passport | typed non-economic evidence and gate map |
| #295–#297 | attribution, interaction, migration | optional diagnostic fields and unscored legacy strength |
| #298–#300 | EWQ gates, self-qualification, frozen guard | explicit pass/fail/unresolved/blocked state |
| #301 | monographs and this dossier | regenerated EN/TR monographs |

No D-141 receipt is evidence of live profitability, realized cashflow, or promotion eligibility.
