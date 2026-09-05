# D-152 Scenario-Centric Evidence Profile & Quad Demotion (Full-Text Specification)

**Status:** PROVISIONAL_DECISION · **Date:** 2026-09-06 · **Rules:** 12, 28–31, 44, 51–56
**Supersession:** extends D-147, D-150, D-151; amends no locked invariant; narrows presentation authority only.
**Artifacts:** `v8-core/src/assurance/evidence_profile.rs`, `v8-core/tests/policy_evidence_profile_adversarial.rs`,
`v8-core/src/usdm_sim.rs` (typed receipt), `v8-core/src/main.rs` (diagnostic rendering).

## 1. Measurement crisis

The canonical 12-month quad (`research/tape/quad-1h-12m/tape.jsonl`) is engineering-diagnostic
but was psychologically promoted to policy quality (`+50.9%` headline, `TOTAL REALIZED RUST CASHFLOW`
label in `main.rs`, `Net Realized Cashflow` label in `usdm_sim.rs`). That promotion violates Rule 12
naming (simulated output rendered with realized vocabulary) and collapses five distinct evidence
domains (retrospective diagnostic, robustness, frozen-OOS replication, prospective shadow, realized
settlement) into one scalar. D-152 demotes the quad to a typed diagnostic court without deleting it.

## 2. Ontology (claim → estimand → source → authority → verdict)

| Claim | Estimand | Evidence source | Authority | Verdict path |
|---|---|---|---|---|
| Diagnostic pathology (fee drag, concentration, funnel) | after-cost accounting on inspected tape | burned quad / development tapes | `DIAGNOSTIC_SIGNAL`, role `BURNED_DIAGNOSTIC`, promotion `NONE` | diagnostic state, never edge |
| Scenario behavior per cell | survival / drawdown / retention under declared archetype or world family | A01–A12 allegories, Foundry families | `DIAGNOSTIC_SIGNAL` (robustness) or scoped defeater | visible per-cell, no averaging |
| Robustness topology | nearest validated plausible defeater, failed families, unknowns | passports + coverage manifest + reverse stress | negative-only, passport-bound | defeater or boundary map |
| Replication | after-cost behavior on untouched chronology | frozen-OOS receipt + preregistered plan | `REPLICATION_ONLY` | bounded replication only |
| Prospective support | forward survival / drift under sequential monitoring | `EvaluationEpoch` succession + e-process | `PROSPECTIVE_ONLY` | support / quarantine / revoke |
| Realization | venue-settled fills, fees, funding, slippage | physical ledger | `REALIZATION_ONLY` | cashflow only |
| Certified edge | multiplicity-controlled predictive edge | WRC + genuine DSR + SPA + ≥3 regimes + reconciliation | `SUPPORTED_EDGE` via Kaizen only | edge or `NO_ECONOMIC_CLAIM` |

`SUPPORTED_EDGE`, `SIMULATED_CASHFLOW`, `REALIZED_CASHFLOW` remain disjoint and non-convertible.

## 3. Scenario court

Historical archetypes reuse the 12 canonical allegories (A01–A12) with negative controls where
defined; no hardcoded expected trades; ex-ante decision-time information only. Synthetic families
reuse the 14 Foundry v2 families. Each `ScenarioCell` records coverage bars, episode count,
net utility, survival, max drawdown, fee retention, failure phenotype, authority, and typed status
(`Verified` / `Falsified` / `Blocked` / `Unresolved`). Missing coverage is `Unresolved`, never zero.
No scalar mean across cells may hide a `Falsified` cell.

## 4. Synthetic asymmetry (audited)

`synthetic_pass_confirms_no_edge()` is identically true: PASS grants nothing. `synthetic_fail_may_challenge(passport, claim)`
is true iff `passport.passport_passed` AND `passport.does_not_confer_economic_edge()` AND claim ∈
{`StructuralRobustness`, `EngineeringIntegrity`, `SemanticIntegrity`, `ResearchIntegrity`}.
A failing passport authorizes nothing. `EconomicReplication`, `ProspectiveEfficacy`,
`RealizedCashflow`, `DeploymentQualified` never accept synthetic evidence (existing
`accepts_synthetic_evidence()` preserved). Falsification hypotheses: garbage-generator veto,
correlated-world inflation, and scenario-tuning are blocked by passport conjunction (10 dims ≥ 0.70),
per-cell visibility, and lineage-relative burn (see §8).

## 5. Gates G0–G9

- **G0 constitutional/causal integrity** (PIT, ChronosGate, determinism, ledger conservation,
  receipt integrity, non-escalation, synthetic isolation, claim typing): hard fail blocks all.
- **G1 measurement identity** (estimand, data role, lineage, search lineage, cost/execution/world
  versions, burn marking): hard fail blocks inference.
- **G2 historical diagnostic court**: exposes gross/net/fee/funding/slippage/drawdown/concentration/
  contribution/turnover/funnel/pathology; outcome is diagnostic state, promotion `NONE`.
- **G3 scenario coverage & behavioral robustness**: declared matrix + negative controls +
  perturbations + cross-asset + friction stress + path topology; hard cells visible; unknown stays unknown.
- **G4 adversarial/synthetic falsification**: provenance + passport + plausibility bounds + coverage
  manifest + minimal-defeater search + reproducibility; PASS mints nothing; FAIL is passport-scoped.
- **G5 selection control**: WRC + genuine DSR + SPA remain the active burden. The in-tree
  `ResearchMultiplicityLedger::summarize()` uses analytic proxy PBO/DSR formulas and therefore
  keeps G5 at `NO_ECONOMIC_CLAIM` (`audit_statistical_triple()`). No weakening without a
  `MethodSubstitutionReceipt` proving equal-or-stronger error control.
- **G6 frozen-OOS replication**: frozen identity, untouched chronology, fixed costs/execution,
  preregistered estimands/plan, dependence-aware uncertainty, full trial lineage. PASS = bounded
  replication only.
- **G7 prospective shadow succession**: `EvaluationEpoch` forward evidence, survival/drift/drawdown,
  e-process state; transitions `ACTIVE → QUARANTINED → REVOKED` enforced by certificate lifecycle.
- **G8 live realization**: venue-settled fills/costs/settlement/deviation/capacity/incidents.
  Historical/synthetic never substitutes.
- **G9 certificate**: non-scalar `ProductionEvidenceCertificate` + profile conclusion; scalar collapse forbidden.

## 6. PolicyEvidenceProfile (canonical output)

`v8-core/src/assurance/evidence_profile.rs::PolicyEvidenceProfile` aggregates policy/code/config
hashes, lineage, case/epoch identity, typed historical diagnostic (`BURNED_DIAGNOSTIC`, promotion
`NONE`), scenario cells, `RobustnessTopology`, `FrozenOOSState`, `ShadowState`, `LiveState`,
`CertificateStatus`, gate verdicts, and `EconomicConclusion` (`UNKNOWN`, `HISTORICALLY_REPLICATED`,
`PROSPECTIVELY_SUPPORTED`, `LIVE_SUPPORTED`, `NOT_PRODUCTION_SUPPORTED`). `derive_conclusion()`
returns `LiveSupported` only with live fills, `ProspectivelySupported` only with active shadow,
otherwise `NotProductionSupported` (frozen-OOS pass alone does not produce production support;
any G0/G1 block forces not-supported). `render_text()` prints the quad number only with its
role and authority. Owner: `assurance/` (extends certificate lifecycle; no second registry).

## 7. Quad demotion (call-graph enforcement)

- `PortfolioReceipt` gains `evidence_role = "BURNED_DIAGNOSTIC"`, `promotion_authority = "NONE"`
  (serde-defaulted, backward compatible).
- `main.rs --quad` header becomes `HISTORICAL DIAGNOSTIC COURT -- QUAD TAPE` with
  `Data role: BURNED_DIAGNOSTIC | Economic promotion authority: NONE | Verdict: NO_ECONOMIC_CLAIM`;
  total line becomes `TOTAL SIMULATED DIAGNOSTIC CASHFLOW (BURNED_DIAGNOSTIC, NO PROMOTION AUTHORITY)`.
- `usdm_sim.rs` detail labels become `Simulated Diagnostic Net` / `Net Simulated Diagnostic Cashflow`.
- Downstream promotion is blocked by type: profile conclusion ignores historical net for support;
  renderer firewall classes unchanged (`SimulatedCashflow` header preserved).

## 8. Lineage-relative burn

The 12-month quad is `BURNED_DIAGNOSTIC` for the current policy lineage (tuned under D-140–D-144).
It retains full diagnostic utility and zero promotion authority. Future lineages declare their own
burn ledger; no tape silently changes role.

## 9. Falsification of this design (what would prove it wrong)

- Scenario matrix tuned to favor the policy (detected via lineage audit + negative-control gaps).
- Generator-aligned reward (detected via passport-behavior decoupling tests).
- Synthetic veto overreach (blocked by §4 conjunction; test `adv_garbage_generator_cannot_veto`).
- Correlated-scenario volume inflation (blocked by per-cell visibility; test `adv_no_scalar_average_hides_failure`).
- Shadow optional stopping (blocked by e-process requirement in G7; monitoring plan id required).
- Certificate decoration (blocked by `derive_conclusion()` enforcement; test `adv_certificate_decorative_without_enforcement`).
- Quad dominance persistence (blocked by §7 labels + receipt typing; test `adv_quad_cannot_mint_edge`).
- Triple-gate redundancy (documented in §5 G5; substitution requires receipt, not prose).

## 10. Verification

`cargo test` 1038 passed / 15 suites including 14-test
`policy_evidence_profile_adversarial.rs` (quad promotion, synthetic escalation, holdout reuse
semantics, cherry-picking, correlated inflation, scalar collapse). `cargo check` and `cargo clippy`
clean. Uncertified economic output remains `NO_ECONOMIC_CLAIM`.
