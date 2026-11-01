## Observed contradiction

Chain issues #451–#454 are CLOSED with "Completed R IDs: all, Remaining: NONE", but their outputs are not consumed by any executable path that ends at the authoritative final surface (`v8-next benchmark` → `BenchmarkRunner` → `BenchmarkReceipt` → `PolicyCertificate` → forensic HTML / `readiness` / `regression`). Per `docs/contracts/WIRING_COMPLETION_CONTRACT.md` §4, code + unit tests is `IMPLEMENTED`, and an issue "MUST NOT claim `completed` for a requirement that is only `IMPLEMENTED`". These four do exactly that.

## Owning authority
- `docs/contracts/WIRING_COMPLETION_CONTRACT.md` §§3–4, §6 anti-pattern #1
- `docs/WORK_ITEM_POLICY.md` §§3–4 (W1–W7 mandatory; PR wiring closure)
- `docs/contracts/V87_READINESS_BENCHMARK_SPEC.md` §9 (central CLI surface)

## Measured evidence (2026-09-12, `e971daf8`)

Unwired outputs — producer exists, no consumer in `src` outside tests:

- #452 oracle substrate: 9 modules (`episode`, `utility`, `coverage`, `support`, `recoverability`, `information`, `independence`, `opportunity`, `artifacts`) have **zero** importers in `v8-next/src` outside `v8_next/oracle/` itself and tests. Only the pre-existing `Identifiability` enum is consumed (4 files).
- #454 D-153 delta: 7 modules (`observation`, `population`, `projection`, `synthetic`, `minerva`, `kaizen_delta`, `external`) are imported only by `tests/test_benchmark_fabric.py` (MECHANICS ONLY). `runner.py:821` calls `PolicyCertificate.generate(receipt)` with no `projection`/`minerva` argument, so the report renders MISSING for both factors on every run.
- #451 attribution: `analysis/` + `telemetry/` consumed only by `app/analysis.py` (side CLI module); nothing flows into the P2 report columns.
- #453 proving ground: `proving_battery.py` referenced only as a `cli.py` passthrough string (`"proving": "v8_next.evaluation.proving_battery"`); `BenchmarkRunner` never invokes the world foundry.
- W1–W7 manifest count across #450–#456 bodies: **0**.

## Contributing causes (not excuses, fix targets)

1. R-requirements written as module-existence, not wired slices; verification gates are `ruff + mypy + module pytest` only — i.e. wiring contract anti-pattern #1 as the success criterion.
2. `WORK_ITEM_POLICY.md` §9 admits form validation does not enforce API submissions — the mandatory `wiring_manifest` field was bypassed on all 7 issues.
3. The no-foreign-touch convention forbids touching the consumer (`runner.py`, `certificate.py`, `report.py`, `readiness.py`), which wiring by definition requires.
4. Fail-closed MISSING rendering masks the gap: no red signal, so closure looked safe.

## Required end state (wired slices, not modules)

- R1 — Each of the four outputs above gains a named consumer edge into the benchmark path, or the CLOSED issue is reopened with the unwired R back in Remaining.
- R2 — `PolicyCertificate.generate` in `runner.py` and `app/portfolio.py` receives produced `projection`/`minerva` values (or a named refusal when unmeasured); forensic HTML stops rendering MISSING for factors that have producers.
- R3 — A `tools/audit_wiring.py` static check exists: every `v8-next/src/v8_next/{oracle,eoanalysis,evaluation,world,system_proving}/*.py` module must have at least one importer outside its own package and tests, else FAIL. Wired into the local gate loop.
- R4 — API-created issues cannot bypass the wiring manifest (process fix; enforcement mechanism TBD in this issue).

## Non-goals
- No new ontology, no score semantics change, no economic claim.
- No re-litigation of the ported code itself; only the missing consumer edges.

## Owner
ddawnlll

## Lifecycle
state:in-progress — R2, R3, R4 delivered on PR #504 (open, unmerged); R1 open on #451–#454

## Base SHA
e971daf8a2f5e73f0a390a57a2e375a92e38cae8

## Completed R IDs
NONE

## Remaining R IDs
R1, R2, R3, R4

## Dependencies
Reopens the closure question on #451, #452, #453, #454. Blocked by owner prioritization of slice order.

## Evidence
R2/R3/R4 evidenced at `audit_out/critical_fixes_20261101/476_evidence.md` and PR #504 (branch tip `18f8760`); R1 is NOT delivered — see `## Remaining R IDs`.

