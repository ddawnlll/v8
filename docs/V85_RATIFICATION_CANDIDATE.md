# V8.5 M0 Ratification Candidate

**Status:** `M0 RATIFICATION CANDIDATE` / non-binding / `NO_ECONOMIC_CLAIM`

**Version:** DRAFT-2 (surgical revision of the supplied V8.5 architecture paper)

> [!IMPORTANT]
> **Authoritative Full-Text Specification:**
> The complete 35-section V8.5 architectural blueprint and research monograph is permanently recorded in [`docs/contracts/V85_ARCHITECTURE_SPEC.md`](contracts/V85_ARCHITECTURE_SPEC.md). All implementations, claims, and proofs are anchored to that full specification.

This document is a V8 extension proposal, not an active constitutional amendment. Existing V8 Constitution and registered decisions remain authoritative until a maintainer-ratified D-series supersession. The architecture is preserved; this candidate narrows authority and makes the first implementation gate executable.

## M0 constitutional boundaries

1. `SUPPORTED_EDGE` and `REALIZED_CASHFLOW` are disjoint, non-convertible statutory claims. Frozen OOS/statistical evidence can never mint physical settlement authority.
2. `AuthorityProjection` is a read-only canonical projection over the existing three-dimensional `crate::authority::Authority`. It cannot mint authority, write `ClaimRegistry`, reclassify claims, issue verdicts or create promotion paths. Projection safety is `AdmissibleClaims(output) ⊆ AdmissibleClaims(input)`; unknown or incomparable mappings fail closed.
3. Assurance Fabric is a deterministic composition view over adjudicated D-136 evidence. It emits only `EvidenceAttestation`, arguments, `ClaimRule` evaluations and `DefeaterReceipt`/`AssuranceCaseReceipt`. Normative claim minting remains exclusively on the Kaizen verdict path with independent audit and existing separation of powers.
4. Synthetic full-chain Foundry/System Proving Ground output is restricted to deterministic `#[cfg(test)]` sabotage and integration harnesses at M0. It cannot enter a production EvaluationCase, report, certificate or ClaimRegistry path. A future expansion requires a separate ratified D-series amendment, transitive taint and negative-only synthetic authority.
5. Until explicit ratified supersession, WRC + genuine DSR + Hansen SPA remain the active `SUPPORTED_EDGE` burden. A future assumption-aware `StatisticalPlan` may substitute a method only through a pre-outcome, D-series-authorized `MethodSubstitutionReceipt` proving equal-or-stronger error control.
6. A sealed `EvaluationCase` is immutable and never reopened. New declared shadow/live observations create immutable `EvaluationEpoch` snapshots; policy, code, config, data-role, statistical-plan or authority-rule changes create a new case. Certificates are time-bounded and may be `SUPERSEDED`, `REVOKED`, `NARROWED` or `EXPIRED`.
7. DSR direction/type mismatches, underpowered fallbacks and proxy PBO/DSR outputs are `BLOCKING_IMPLEMENTATION_DEBT`; they remain `NO_ECONOMIC_CLAIM` until genuine, versioned receipts exist.

## Production Growth Contract

The objective remains long-horizon after-cost geometric capital growth. M0 makes the minimum deterministic fields explicit: initial/current equity, realized/unrealized PnL, fees, funding, slippage, open positions, drawdown and geometric-growth formula version. Missing FX, capacity, liability or valuation inputs remain `UNKNOWN`/`INCOMPLETE_ECONOMICS`; no zero/default substitution is allowed. Weekly-equivalent and stretch targets are non-authoritative `PlanningAmbition` metadata and cannot reach policy selection, challenger ranking, stopping, sizing, exits, promotion or readiness.

## M0 implementation order

- **M0:** close authority/claim/statistical/synthetic/lifecycle P0 boundaries; register the governance work item and reuse matrix.
- **M1:** implement the minimal passive Assurance Fabric, immutable case/epoch receipts, hard-defeater propagation and capability tests; promotion remains closed.
- **M2:** run the real-data deployment-equivalent court with deterministic PGC metrics, genuine typed statistics, trial debt and protected OOS.
- **M2b:** run Foundry/SPG only as `#[cfg(test)]` full-chain sabotage harnesses.
- **M3+:** add TEVV, shadow/live epochs, revocation and any future synthetic expansion only after their owning decisions and gates exist.

## Required verification

The ratification candidate requires Rust contract and sabotage tests for authority non-escalation, claim-mint capability, synthetic isolation, DSR typing, proxy-metric quarantine, sealed-case immutability, epoch ordering, holdout burn, deterministic PGC accounting and certificate revocation. All uncertified economic output remains `NO_ECONOMIC_CLAIM`.

See the associated governance work item: `docs/issues/ISSUE_V85_RATIFICATION_CANDIDATE.md`.
