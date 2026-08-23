# D-141 Qualification Dossier

**Decision:** D-141 Expert Proving Ground & Alpha Refinery
**Scope:** deterministic semantic qualification only
**Economic authority:** `NO_ECONOMIC_CLAIM`

## Receipt

The executable receipt is `.audit/d141/current/PILOT_QUALIFICATION_REPORT.json`, produced by:

```text
cargo run --manifest-path v8-core/Cargo.toml -- qualify-experts --out .audit/d141/current/PILOT_QUALIFICATION_REPORT.json
```

The report is only valid when that physical file exists and its manifest/run hashes match the executed code. It contains no profit, return, or promotion assertion.

## Pilot result contract

| Expert | Formal manifest | Semantic verdict | Economic verdict |
|---|---|---|---|
| `failed_breakout:v1` | D-141 manifest hash in receipt | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `fib_projection_reversal:v1` | D-141 manifest hash in receipt | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |

The other registered witnesses are intentionally not counted as passed or failed until they receive their own Behavior Card and manifest. Registry manifest coverage is reported separately from the executed-test pass rate.

## Gate interpretation

- EWQ-01…06 are semantic qualification gates. A failed canonical, metamorphic, or critical mutation control falsifies qualification.
- EWQ-07 (sealed challenge) and EWQ-08 (statistical no-regression) remain `UNRESOLVED` in the pilot receipt.
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
