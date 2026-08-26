# [GOV] V8.5 M0 Ratification Candidate

**Status:** `state:ready` candidate; non-binding until maintainer ratification

**Change class:** `CONTRACT_GOVERNANCE`
**Risk:** `risk:high`

## R# traceability

- **R1 —** Preserve the existing V8 ontology, three Oracle taxonomy, D-136/D-141 ownership and separation of powers. Authority: V8 Constitution, D-132, D-134, D-136, D-141.
- **R2 —** Close the six V8.5 P0 contradictions without silently superseding active rules. Authority: V8.5 DRAFT-2 P0 register; `docs/WORK_ITEM_POLICY.md` §3.
- **R3 —** Keep WRC + genuine DSR + Hansen SPA as the active `SUPPORTED_EDGE` burden until a separately ratified supersession. Authority: root anti-synthetic/economic-claim directive; D-132; `v8-core/src/kaizen/verdict.rs`.
- **R4 —** Make the authority layer a read-only `AuthorityProjection`; no second statutory authority root, claim registry or verdict engine. Authority: D-132 Rule 28–31.
- **R5 —** Keep synthetic full-chain Foundry/SPG output inside deterministic `#[cfg(test)]` harnesses for M0; no synthetic economic authority. Authority: root anti-synthetic directive §5.3; D-141.
- **R6 —** Separate immutable `EvaluationCase` from append-only `EvaluationEpoch` snapshots; policy/code/config/rule changes create a new case. Authority: D-138; D-139; V8.5 DRAFT-2 lifecycle boundary.
- **R7 —** Treat DSR direction/type errors and proxy PBO/DSR outputs as `BLOCKING_IMPLEMENTATION_DEBT`; they cannot carry economic authority. Authority: root anti-hardcoded-metrics directive §5.1; V8.5 DRAFT-2 Statistical Court.

## Existing contracts to reuse

`crate::authority::Authority`, `ClaimValue<T>`, `ClaimRegistry`, `KaizenVerdictEngine`, D-136 `EvidenceGraph`, D-141 qualification receipts, `shadow.rs`, `judiciary/`, `kaizen` trial debt and `tools/build_monograph.py`. No parallel authority, evidence store or claim registry is permitted.

## Mathematical and semantic invariants

- `SUPPORTED_EDGE` and `REALIZED_CASHFLOW` are disjoint and non-convertible.
- `AdmissibleClaims(output) ⊆ AdmissibleClaims(input)` for every authority projection.
- Missing, unknown, incomparable or underpowered values remain `UNKNOWN`, `INSUFFICIENT_EVIDENCE` or `NO_ECONOMIC_CLAIM`; no zero/default coercion.
- A sealed case is immutable. New declared observations create an immutable epoch/snapshot; policy, code, config, plan or rule changes create a new case.
- Synthetic evidence is test-only at M0 and cannot enter production EvaluationCase, report, certificate or ClaimRegistry paths.
- No calendar ambition may reach policy selection, challenger ranking, stopping, sizing, exits, promotion or readiness.

## Canonical failure semantics

`OPEN_PIN` for conflicting authority; `BLOCKED` for hard defeaters; `INCOMPLETE_ECONOMICS` for missing valuation inputs; `BLOCKING_IMPLEMENTATION_DEBT` for proxy statistics; `HOLDOUT_CONTAMINATION` for burned-lineage reuse; `NO_ECONOMIC_CLAIM` for every uncertified economic result.

## Composition topology

`Constitution/Decision Register → Judiciary preregistration → Kaizen verdict → constitution-pinned ExecutionMandate → implementer → passive backend/ledger → D-136 evidence → read-only Assurance Fabric receipt → independent auditor → ClaimRegistry mint only through Kaizen.`

## M0 closure disposition

1. P0-001 becomes a constitutional separation of `SUPPORTED_EDGE` from settlement authority.
2. P0-002 uses read-only `AuthorityProjection` over the existing 3-D `Authority`.
3. P0-003 keeps claim-scoped admissibility but restricts synthetic full-chain output to `#[cfg(test)]`.
4. P0-004 adds explicit `ClaimRule`/hard-defeater composition above D-136 without a second registry.
5. P0-005 preserves the active WRC/DSR/SPA burden; future substitution requires pre-outcome D-series approval and a `MethodSubstitutionReceipt`.
6. P0-006 freezes deterministic ProductionGrowthContract fields; advanced FX/capacity semantics remain later contracts.

## Verification and receipts

Before ratification, implement Rust contract/sabotage tests for authority non-escalation, claim mint capability, synthetic isolation, DSR typing, proxy-metric quarantine, sealed-case immutability, epoch ordering, holdout burn, PGC deterministic accounting and certificate revocation. Regenerate both monographs and attach byte-identity receipts.

## OPEN_PIN triggers

Any attempt to grant synthetic production authority, loosen the active statistical burden without supersession, add a second authority/registry/verdict path, mutate a sealed case, or render proxy statistics as economic claims blocks the work item.
