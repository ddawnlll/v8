# D-150: Continuous Epistemic Succession & Living Policy Constitution

**Research monograph, constitutional amendment candidate, and implementation specification.**

`DRAFT FOR RATIFICATION` • `NO_ECONOMIC_CLAIM` • `V8.5` • `2026-08-27`

This paper extends the supplied *V8 Final Research Monograph* without replacing its existing constitutional, Kaizen, Oracle, evidence, shadow, holdout, or claim-authority rules.

---

## 1. Document status and reading rule

**DRAFT FOR RATIFICATION / NO_ECONOMIC_CLAIM.** This document proposes `D-150 — Continuous Epistemic Succession & Living Policy Constitution`. It is a research-backed constitutional and implementation specification. It does not promote a trading policy, authorize capital deployment, create a new Oracle, supersede Kaizen, or convert synthetic evidence into economic truth.

This paper inherits the project vocabulary `LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`, `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`, `OPEN_QUESTION`, and `REJECTED_OPTION`. It also inherits the existing V8 constraints that synthetic tests do not prove economics; claim authority must not exceed evidence authority; economic claims require receipt-bound provenance; and sealed evaluation objects are immutable.

> **Core thesis.** D-150 is not a new trading-intelligence subsystem. It adds the missing temporal law to V8's evidence constitution:
> $$\text{PolicyIdentity} \neq \text{EvidenceState}$$
> A policy can remain byte-identical while the evidence supporting its use improves, weakens, becomes contested, or is revoked.

---

## 2. Abstract

V8 already contains two strong but incomplete ideas: policy evolution through Kaizen and evidence sovereignty through immutable, authority-bound receipts. What is missing is a constitutional definition of how the validity of an unchanged policy evolves as new evidence arrives. Static certification implicitly treats a past `PASS` as if it were timeless. That assumption is incompatible with non-stationary financial markets, expanding synthetic/adversarial test spaces, prospective shadow evidence, new execution observations, and newly discovered failure mechanisms. Continual-evaluation research explicitly motivates repeated assessment as conditions and known limitations evolve [R1, R2, R3, R7].

D-150 introduces **continuous epistemic succession**. Every sealed evaluation remains immutable. New evidence creates a successor `EvaluationEpoch`; it never rewrites an old case. Each epoch produces a revocable, non-scalar evidence certificate bound to policy, code, configuration, evidence ancestry, world coverage, authority, and time. The certificate may remain active, become superseded, enter quarantine, or be revoked. A material defeat is transferred to the existing Kaizen lifecycle for diagnosis, challenger construction, development testing, protected evaluation, and possible succession. Thus D-150 adds an evidence-time axis without creating a second Kaizen or a second authority root.

The design further specifies how real, shadow, synthetic, adversarial, D-136, D-141, and Oracle evidence can enter the succession process without authority escalation. Synthetic or causal world generators may discover robustness defeaters but cannot establish realized economic edge. Recent work on causal market simulation, realistic multivariate synthetic series, controllable market wind tunnels, reverse stress, and adversarial co-evolution supports the value of expanding test worlds while also showing why generated worlds must remain typed and conditional [R8, R9, R10, R11, R13].

---

## 3. Source basis and relationship to the existing V8 monograph

**PROJECT_EVIDENCE_SUPPORTED.** The supplied V8 monograph already contains the foundations D-150 reuses: a falsification-first constitution; point-in-time MarketState; immutable economic objects; the three-dimensional Authority tensor; six statutory claim classes; D-136 EvidenceGraph; D-141 Expert qualification; D-138 prospective shadow receipts; Kaizen as sole normative research/verdict path; and the V8.5 M0 ratification candidate with read-only `AuthorityProjection`, disjoint `SUPPORTED_EDGE`/`REALIZED_CASHFLOW`, synthetic M0 restrictions, preserved statistical burdens, and immutable `EvaluationCase` epochs.

D-150 therefore does *not* restart V8.5 architecture. It closes one missing contract: the lifecycle of evidence validity after a case has been sealed.

---

## 4. The problem: static certification in a non-stationary world

### 4.1 Static PASS is an accidental eternity claim

```
policy
  ↓
evaluation
  ↓
PASS
  ↓
certificate
  ↓
???
```

The missing arrow is the problem. A static certificate does not say what happens when the market distribution changes, when a new failure family is discovered, when execution quality deteriorates, or when a stronger evaluator is introduced. Concept drift and distribution shift are ordinary properties of deployed time-series systems, not exceptional events [R2, R3, R4].

### 4.2 Reopening the old case is epistemically destructive

If new observations are appended into the same sealed object, then `case_hash`, evidence set, burden of proof, and verdict ancestry become time-dependent mutable state. It becomes impossible to reconstruct exactly what was known when a historical decision was issued. D-150 instead treats evaluation as an append-only succession of immutable snapshots.

> **Rejected model:** `certificate.json` is a mutable dashboard row whose values are overwritten as new tests arrive. That model destroys historical auditability.

---

## 5. Research objective

D-150 answers one question:

$$\text{Given an unchanged policy } P, \text{ how should V8 update the epistemic status of } P \text{ when new admissible evidence arrives at time } t, \text{ without rewriting history, escalating authority, or bypassing Kaizen?}$$

The target system is a **living policy**: not a self-modifying live strategy, but a policy whose right to remain active is continuously conditional on current evidence.

$$\text{CurrentSupport} = f(\text{PolicyIdentity}, \text{EvidenceEpoch}, \text{Authority}, \text{BurdenOfProof}, \text{Time})$$

The research objective is therefore not "more tests". It is a governed mechanism for **continuous falsifiability**.

---

## 6. Non-goals and constitutional boundary

| D-150 does | D-150 explicitly does not |
|---|---|
| Version evidence validity over time. | Create a fourth Oracle. |
| Create immutable successor evaluation epochs. | Create a second Kaizen. |
| Allow new evidence to supersede, quarantine, or revoke current assurance. | Automatically mutate the incumbent policy. |
| Route material defeaters into Kaizen. | Automatically promote challengers. |
| Bind certificates to world/evidence coverage and authority. | Convert synthetic robustness into `SUPPORTED_EDGE`. |
| Preserve historical decisions exactly. | Rewrite or "correct" old receipts in place. |
| Permit continuous monitoring under declared statistical plans. | Make repeated peeking statistically free. |

---

## 7. Research synthesis

### 7.1 Continual evaluation
Robustness Gym explicitly frames evaluation as a continual practitioner process because a static test artifact cannot anticipate evolving conditions and limitations [R1]. Dynamic benchmarks such as AndroidWorld generate parameterized task variations rather than relying on one immutable test set [R6]; MACEval similarly targets longitudinal evaluation to reduce closed-ended benchmark overfitting [R7]. V8's analogue is not benchmark churn for its own sake, but fresh evidence epochs bound to the exact incumbent.

### 7.2 Streaming distribution-shift diagnosis
Sequential shift-detection work emphasizes detecting changes early enough to prevent accumulated deployment cost [R3]. Diagnostic Runtime Monitoring with Martingales demonstrates that multiple streaming monitors can help distinguish causes of shift and link them to appropriate interventions [R4]. This supports D-150's choice to preserve typed `DefeaterReceipt`s rather than collapsing monitoring into one health score.

### 7.3 Sequential statistics
Repeated monitoring is not equivalent to one fixed-sample hypothesis test. Sequential model confidence sets use e-processes/confidence sequences to provide time-uniform monitoring guarantees [R5]; robust confidence-sequence work shows how anytime-valid intervals can be constructed under explicit contamination assumptions [R14]. D-150 therefore permits sequential statistical evidence only through a manifest-bound monitoring plan whose assumptions and stopping rule are explicit.

### 7.4 Generated and causal market worlds
Causal market simulators aim to produce counterfactual financial trajectories that preserve declared causal structure [R8]. Financial Wind Tunnel develops controllable synthetic scenarios for stress testing [R9], while the GAN-Diffusion framework emphasizes that stylized facts and inter-asset dependence remain nontrivial generation problems [R10]. D-150's conclusion is conservative: generated worlds can expand robustness evidence, but generated success does not become real economic evidence.

### 7.5 Adversarial co-evolution and evaluator succession
COvolve explicitly co-evolves environment and policy designers so new environments reveal policy weaknesses [R11]. FAMOU's work argues that fixed evaluators can become stale as strategies improve and therefore introduces evaluator co-evolution and weakness pressure [R12]. D-150 uses the same high-level insight without importing their game assumptions: the test distribution may evolve, so certificate validity must be tied to a particular evidence epoch, not to policy identity alone.

### 7.6 Reverse stress
Recent reverse-stress work constructs coherent multivariate scenarios conditional on shocks while preserving empirical dependence structure [R13]. This supports a future Foundry in which new minimal plausible defeaters can invalidate a robustness claim without ever acquiring economic claim authority.

---

## 8. Core model: Policy × Evidence × Time

```
                    POLICY LINEAGE
            P17 ───────────────────────► P18
             │                           ▲
             │                           │
             │ E0  ACTIVE                │
             │ E1  ACTIVE                │
             │ E2  CONTESTED             │
             │ E3  REVOKED ──Defeater────┘
             │
             ▼
        EVIDENCE LINEAGE
```

Kaizen already versions the horizontal axis: **policy succession**. D-150 adds the vertical axis: **evidence succession for an unchanged policy**.

$$\text{PolicyIdentity}(P_{17}, E_0) = \text{PolicyIdentity}(P_{17}, E_3)$$
$$\text{EvidenceState}(P_{17}, E_0) \neq \text{EvidenceState}(P_{17}, E_3)$$

This is the conceptual addition. D-150 is therefore an amendment to Kaizen's environment, not a competitor to Kaizen.

---

## 9. Canonical architecture

```
 REAL MARKET ──────────────┐
 SHADOW / PROSPECTIVE ─────┤
 SYNTHETIC WORLDS ─────────┤
 ADVERSARIAL WORLDS ───────┤
 D-136 / D-141 ────────────┤
 3 ORACLES ────────────────┘
             │
             ▼
       EVIDENCE INTAKE
             │
     admissibility + authority
             │
             ▼
       EVALUATION EPOCH
      immutable / hash-bound
             │
             ▼
       ASSURANCE FABRIC
             │
      ┌──────┴──────┐
      ▼             ▼
   SUPPORTED      DEFEATER
      │             │
      ▼             ▼
 certificate       KAIZEN
 succession      diagnosis
      │             │
      │          challenger
      │             │
      └──────┬──────┘
             ▼
        NEXT EPOCH / POLICY
```

**Ownership rule.** D-150 owns temporal evidence state. Assurance owns evidence composition. Kaizen owns policy improvement and normative succession. ClaimRegistry remains on the existing normative path.

---

## 10. Canonical objects

### 10.1 EvaluationCaseManifest
```
EvaluationCaseManifest {
  case_id, policy_hash, code_hash, config_hash,
  production_growth_contract_id, information_contract_id,
  utility_contract_id, cost_model_id, capacity_model_id,
  universe_id, authority_projection_id, created_at, sealed_hash
}
```
The manifest identifies what is being judged. Once sealed, it is immutable.

### 10.2 EvaluationEpoch
```
EvaluationEpoch {
  epoch_id, case_id, parent_epoch_id?,
  evidence_delta_hash, cumulative_evidence_root,
  world_coverage_root, monitoring_plan_id?,
  assurance_receipt_id, certificate_id, opened_at, sealed_at
}
```
An epoch is not a mutable time bucket. It is an immutable successor snapshot produced when a declared evidence-trigger requires re-adjudication.

### 10.3 ProductionEvidenceCertificate
```
ProductionEvidenceCertificate {
  certificate_id, policy_hash, epoch_id, claim_vector,
  hard_defeaters, authority_bounds, world_coverage,
  statistical_plan_ids, status, issued_by_verdict_receipt,
  supersedes?, revokes?
}
```

---

## 11. Certificate state machine

```
               ┌──────────────┐
               │    ACTIVE    │
               └──────┬───────┘
                      │ new epoch
          ┌───────────┼────────────┐
          │           │            │
          ▼           ▼            ▼
     SUPERSEDED   QUARANTINED    REVOKED
          │           │            │
          │           │            └──► Kaizen diagnosis
          │           └──► additional evidence required
          └──► successor certificate is current
```

| State | Meaning | Capital semantics |
|---|---|---|
| `ACTIVE` | Current evidence epoch satisfies its declared assurance claims. | No new economic authority beyond existing authorized policy. |
| `SUPERSEDED` | A newer certificate exists for the same policy/case lineage. | Historical only; not current authority. |
| `QUARANTINED` | Evidence is contested, stale, incomplete, or a non-terminal concern requires resolution. | Deployment policy follows pre-existing operations/risk rules; D-150 itself does not invent a fallback. |
| `REVOKED` | A hard defeater invalidates a required claim or prerequisite. | Current assurance is withdrawn; material failure is handed to Kaizen and existing governance. |

---

## 12. The append-only epoch law

1. A sealed `EvaluationCaseManifest` may never be changed.
2. A sealed `EvaluationEpoch` may never be changed.
3. New evidence never edits an old receipt; it creates a successor epoch.
4. The successor epoch cryptographically binds its parent, evidence delta, cumulative evidence root, and current adjudication.
5. Historical certificates remain valid descriptions of what was supported under their historical evidence set; they may cease to be current authority.
6. Any correction to an erroneous historical artifact is represented as a new invalidation/supersession artifact, never an overwrite.

$$\text{NewEvidence}(t+1) \implies \text{NewEpoch}(t+1), \quad \text{never } \text{Mutate}(\text{Epoch}_t)$$

---

## 13. What creates a new epoch?

| Trigger | Example | Required action |
|---|---|---|
| Prospective market evidence | New shadow week/month completes. | Create epoch if the monitoring manifest declares the observation boundary. |
| Distribution shift | Declared drift monitor crosses threshold. | Seal diagnostic receipt; re-adjudicate relevant claims. |
| New synthetic/adversarial family | Foundry adds cross-asset contagion worlds. | New robustness epoch; economic claims remain untouched unless independent real evidence changes. |
| Minimal plausible defeater | Reverse stress finds a nearby failure surface. | Challenge/revoke affected robustness or survival claim. |
| Evaluator defect | D136 provider or D141 oracle is invalidated. | Transitively invalidate dependent evidence and produce a successor epoch. |
| Execution-model change | Fee/slippage/capacity assumption changes. | New case or case-family version; do not pretend comparability is unchanged. |
| Policy/code/config change | Incumbent logic changes. | New policy lineage/case, not merely new evidence epoch. |

---

## 14. Evidence admissibility under D-150

D-150 does not redefine evidence authority. It consumes the V8.5 admissibility rules.

| Evidence source | May affect | May not establish by itself |
|---|---|---|
| Real protected OOS | Economic replication, statistical evidence, failure diagnosis within declared authority. | Physical realized cashflow unless it is actual venue-settled evidence. |
| Prospective shadow | Prospective behavior, drift, operational validity, depending on shadow contract. | Automatic promotion or settlement authority. |
| Synthetic worlds | Robustness, semantic consistency, safety, counterexample discovery. | `SUPPORTED_EDGE`, expected real return, `REALIZED_CASHFLOW`. |
| Adversarial/reverse stress | Negative evidence, hard defeaters, vulnerability topology. | Positive economic edge. |
| D141 | Expert semantic qualification and bounded behavioral claims. | Profitability. |
| Hindsight/Target Oracle | Bounds, recoverability, regret, decision-domain analysis under declared authority. | Realized cashflow or ex-ante selectability without supporting evidence. |

---

## 15. Market World Foundry as a temporal evidence source

D-150 does not create the Foundry. It defines what happens to current assurance when the Foundry improves. This is important because synthetic-market research is itself evolving: causal simulators target counterfactual validity [R8]; quality-aware GAN/diffusion work targets stylized facts and multivariate dependence [R10]; and controllable simulators expose policies to conditions outside a single historical tape [R9].

```
Foundry v1
  ├─ structural
  ├─ block resample
  └─ surgery
       │
       ▼
P17 / Epoch 4 → ROBUSTNESS_SUPPORTED

Foundry v2
  ├─ cross-asset contagion
  ├─ branching counterfactuals
  └─ reverse stress
       │
       ▼
P17 / Epoch 7 → NEW_DEFEATER → QUARANTINE / REVOKE
```

**Constitutional consequence:** a previous robustness PASS remains a truthful historical claim about its declared world coverage, but it is not automatically sufficient after the test universe expands.

---

## 16. Co-evolution without evaluator capture

Adversarial co-evolution is attractive because a fixed evaluator can become stale as the policy adapts [R11, R12]. V8 must nevertheless prevent an agent from co-evolving the evaluator into a favorable grader.

| Allowed | Forbidden |
|---|---|
| World population evolves to expose new failure surfaces. | Policy agent edits its own sealed qualification worlds after seeing outcomes. |
| New evaluator families become new versioned evidence sources. | New evaluator silently supersedes historical evidence semantics. |
| Harder worlds generate new negative/robustness evidence. | Synthetic success is promoted to economic evidence. |
| Policy and world populations may co-evolve in development. | Protected economic OOS participates in world/policy co-evolution. |
| Fresh novelty-vault worlds are generated after policy freeze. | Qualification seeds are exposed to the policy-generation agent. |

D-150 binds every evaluator/world family version into the epoch identity, so evaluator evolution becomes auditable rather than invisible.

---

## 17. Prospective shadow and living evidence

D-138 already provides prospective, hash-bound shadow receipts with no automatic economic claim. D-150 gives those receipts a place in time. A shadow observation window does not mutate the original promotion case; it contributes an evidence delta to a successor epoch.

```
P17 / E0  policy frozen
   │
   ├── shadow window S1 ──► E1
   ├── shadow window S2 ──► E2
   └── drift / failure  ──► E3 → QUARANTINE / REVOKE
```

This makes prospective monitoring auditable without turning a continuously viewed stream into a repeatedly reopened OOS test.

---

## 18. Sequential monitoring and optional-stopping firewall

Continuous evaluation creates a statistical trap: repeated inspection of ordinary fixed-horizon p-values can inflate false-alarm risk. D-150 therefore distinguishes **operational monitoring evidence** from one-shot economic promotion evidence. Where continuous statistical inference is required, the `MonitoringPlan` must specify a time-valid method such as an appropriate e-process or confidence sequence, together with assumptions, estimand, update frequency, and stopping semantics [R5, R14].

```
MonitoringPlan {
  estimand, data_stream, update_rule, method_id, assumptions,
  alert_boundary, minimum_information, action_on_alert
}
```

**Rule:** D-150 does not waive the project's existing WRC + genuine DSR + Hansen SPA burden for `SUPPORTED_EDGE`. Sequential monitoring is a separate evidence channel unless an explicit ratified method substitution changes the economic burden.

---

## 19. Hard defeaters and transitive revocation

D-150 must propagate defeat through dependency relationships, not average it away.

| Defeater | Immediate effect |
|---|---|
| PIT / future-read violation | Revoke every claim that depends on the contaminated trajectory. |
| Ledger/cashflow conservation failure | Block economic claims dependent on that ledger. |
| Authority escalation | Invalidate the derived claim and projection path. |
| Evaluator tampering/self-certification | Invalidate evaluator-derived evidence and trigger independent audit. |
| Holdout reuse | Burn the affected OOS authority for that lineage. |
| New catastrophic plausible world | Challenge the corresponding robustness/survival claim; does not erase unrelated real evidence. |
| Execution authority mismatch | Downgrade/unknown claims requiring stronger fill/impact semantics. |

$$\text{HardDefeater}(\text{required\_subclaim}) \implies \text{ParentClaim cannot remain PASS}$$

---

## 20. Kaizen handoff: evidence evolution → policy evolution

D-150 ends where Kaizen begins.

```
New evidence
    ↓
EvaluationEpoch
    ↓
Assurance adjudication
    ↓
DefeaterReceipt
    ↓
certificate QUARANTINED / REVOKED
    ↓
KAIZEN
    ↓
diagnosis
    ↓
hypothesis
    ↓
immutable challenger
    ↓
DEV / WFA / protected evaluation
    ↓
new policy lineage
```

D-150 may request re-evaluation or produce a defeater, but it may not choose parameters, generate an economic challenger, or mint a normative promotion. This preserves the existing Kaizen sovereignty rather than duplicating it.

---

## 21. Data-role and holdout semantics

Evidence succession must be lineage-relative. A dataset is not intrinsically "OOS forever"; its role is defined relative to a policy/research lineage and a declared use.

```
DataRoleLedger / Lineage L17
  2022-2024  DEVELOPMENT
  2025-H1    GENERATOR_CALIBRATION
  2025-H2    GENERATOR_VALIDATION
  2026-H1    POLICY_FROZEN_OOS
  2026-H2    PROSPECTIVE_SHADOW
```

Opening protected OOS for L17 creates a `HoldoutBurnReceipt`. A successor policy may use the revealed outcomes as development information, but the same tape cannot regain untouched-OOS authority for the successor lineage.

---

## 22. World coverage is part of certificate identity

A robustness certificate without a world-space declaration is meaningless. D-150 therefore binds a `WorldCoverageManifest` to every robustness-related epoch.

```
WorldCoverageManifest {
  generator_families, generator_versions, parameter_domains,
  seed_roots, scenario_count, behavioral_cells, cross_asset_cells,
  tail_stress_cells, execution_stress_cells, novelty_vault_id?,
  generator_passport_ids
}
```

World count alone is not a coverage metric. Ten thousand near-duplicate paths may provide less information than one carefully constructed minimal plausible defeater. The certificate must therefore retain family and behavior-space coverage, not merely `N_worlds`.

---

## 23. Failure phenotypes as Kaizen input

D-150 does not require a specific failure-genome implementation, but it standardizes the loss-decomposition receipt that makes continual evidence actionable.

```
FailureAttribution {
  detection_loss, representation_loss, selection_loss,
  allocation_loss, execution_loss, exit_capture_loss, friction_loss,
  interactions, unidentified_residual
}
```

This prevents the continual loop from degenerating into "PnL fell, add another filter." A new epoch should identify which claim or mechanism deteriorated, and Kaizen should target that mechanism rather than blindly optimize proxy metrics.

---

## 24. Reference algorithms

### 24.1 Algorithm A — ingest new evidence
```rust
fn ingest_evidence(case, current_epoch, evidence) {
    verify(case.sealed_hash);
    verify(current_epoch.sealed_hash);
    verify(evidence.provenance);
    admissibility = classify_for_claims(evidence);
    authority = project_authority_read_only(evidence);

    if evidence_changes_policy_code_config_or_contract(evidence) {
        return NEW_CASE_REQUIRED;
    }

    delta = EvidenceDelta(evidence, admissibility, authority);
    next_epoch = seal_successor_epoch(current_epoch, delta);
    return adjudicate(next_epoch);
}
```

### 24.2 Algorithm B — adjudicate successor epoch
```rust
fn adjudicate(epoch) {
    graph = reconstruct_cumulative_assurance_graph(epoch);
    propagate_invalidations(graph);
    verdict_vector = evaluate_claim_rules(graph);

    if hard_required_claim_fails(verdict_vector) {
        certificate = REVOKED_or_QUARANTINED;
        emit DefeaterReceipt;
        handoff_to_kaizen();
    } else {
        certificate = ACTIVE;
    }

    supersede_previous_current_certificate();
    seal_all_outputs();
    return certificate;
}
```

---

## 25. Proposed constitutional invariants

1. **D150-I01 — Temporal Conditionality:** no policy certificate is timeless.
2. **D150-I02 — Immutable History:** sealed cases, epochs, and receipts are append-only.
3. **D150-I03 — New Evidence/New Epoch:** admissible new evidence that changes adjudication state creates a successor epoch.
4. **D150-I04 — Policy/Evidence Separation:** policy identity and evidence status are independent axes.
5. **D150-I05 — No Authority Escalation:** succession cannot strengthen evidence authority beyond its sources.
6. **D150-I06 — Claim-Scoped Admissibility:** evidence may be admissible for one claim and forbidden for another.
7. **D150-I07 — Synthetic Non-Economic Law:** synthetic positive results cannot establish economic edge or realized cashflow.
8. **D150-I08 — Negative Synthetic Force:** synthetic/adversarial evidence may falsify or challenge robustness claims within declared plausibility/authority.
9. **D150-I09 — Hard Defeater Dominance:** required hard failures cannot be averaged away by unrelated passes.
10. **D150-I10 — Evaluator Version Binding:** evaluator/world-family versions are part of epoch identity.
11. **D150-I11 — Sequential Peeking Firewall:** continuous statistical monitoring requires time-valid methods or remains diagnostic-only.
12. **D150-I12 — Kaizen Sovereignty:** D-150 cannot generate or promote a policy challenger autonomously.
13. **D150-I13 — Normative Minting Continuity:** ClaimRegistry mint authority remains on the existing Kaizen/verdict/audit path.
14. **D150-I14 — Holdout Burn:** revealed protected OOS cannot regain untouched authority for the affected lineage.
15. **D150-I15 — Revocation Is First-Class:** revocation is an ordinary lifecycle state, not an exceptional corruption of history.
16. **D150-I16 — Unknown Is Legal:** insufficient or incomparable evidence produces `UNKNOWN`/`QUARANTINED`, not fabricated confidence.
17. **D150-I17 — Coverage-Bound Robustness:** robustness claims must name world/evaluator coverage.
18. **D150-I18 — No Automatic Promotion:** accumulating PASS epochs never bypasses the economic promotion burden.

---

## 26. Mandatory D-150 sabotage suite

| ID | Sabotage | Expected result |
|---|---|---|
| `D150-T01` | Mutate sealed EvaluationCase. | Panic/block: immutable case violation. |
| `D150-T02` | Mutate sealed epoch after certificate. | Panic/block: integrity failure. |
| `D150-T03` | Append shadow evidence by editing E0. | Reject; require E1. |
| `D150-T04` | Synthetic PASS attempts to mint SUPPORTED_EDGE. | Inadmissible. |
| `D150-T05` | Synthetic FAIL attacks robustness prerequisite. | Defeater propagated to parent claim. |
| `D150-T06` | PIT violation appears in new evidence. | Dependent current assurance revoked. |
| `D150-T07` | Old certificate remains marked current after successor. | Fail; old must be SUPERSEDED. |
| `D150-T08` | Policy hash changes but code tries to create evidence-only epoch. | Fail; new case/policy lineage required. |
| `D150-T09` | Evaluator version changes without epoch binding. | Fail. |
| `D150-T10` | Repeated fixed-p p-value monitoring. | Diagnostic-only / blocked as time-valid evidence. |
| `D150-T11` | Holdout-burned data reintroduced as untouched OOS. | Fail closed. |
| `D150-T12` | Assurance Fabric directly writes ClaimRegistry. | Compile/capability failure. |
| `D150-T13` | D-150 directly creates challenger parameters. | Capability failure. |
| `D150-T14` | Hard defeater averaged with many PASS metrics. | FAIL remains (defeater dominance). |
| `D150-T15` | Unidentified evidence coerced to zero. | Fail; UNKNOWN preserved. |
| `D150-T16` | New Foundry family breaks incumbent. | New epoch + challenge/revocation only for affected claims. |
| `D150-T17` | Historical certificate deleted after revocation. | Fail; history must remain reconstructable. |
| `D150-T18` | Parent epoch hash mismatch. | Fail lineage verification. |
| `D150-T19` | Certificate lacks evidence/world coverage root. | Fail issuance. |
| `D150-T20` | All monitoring PASS attempts automatic promotion. | Fail; promotion authority unchanged. |

---

## 27. Minimal implementation layout

D-150 should be implemented as a narrow extension of the existing V8.5 assurance/Kaizen surfaces, not as a parallel bureaucracy.

```
v8-core/src/assurance/
  continuous.rs      # EvaluationEpoch successor logic
  certificate.rs     # certificate lifecycle/state machine
  case.rs            # sealed EvaluationCase identity
  defeater.rs        # hard-defeater receipts
  receipt.rs         # epoch/certificate cryptographic bindings

v8-core/src/kaizen/
  ...                # existing diagnosis/challenger/experiment/verdict path

v8-core/src/shadow.rs
  ...                # unchanged provenance boundary; receipts feed successor epochs

v8-core/src/world/
  ...                # world evidence source; D-150 does not grant economic authority
```

**Implementation bias.** No new subsystem should be added when an existing module can own the behavior. The smallest correct implementation is preferred.

---

## 28. Compatibility with D-147 / D-148 / D-149 and existing law

| Existing decision | D-150 treatment |
|---|---|
| D-132 Kaizen/Claim sovereignty | Preserved. D-150 does not create a second verdict or mint path. |
| D-136 EvidenceGraph | Reused as evidence/adjudication substrate. |
| D-138 Shadow | Reused as prospective receipt source; D-150 versions its effect over time. |
| D-141 Expert Proving Ground | Qualification receipts can trigger successor epochs; authority remains bounded. |
| D-147 V8.5 M0 candidate | Preserves read-only authority projection, immutable cases, synthetic restrictions, and statistical debt. |
| D-148 fast audit engine | Can execute reproduction/evaluation efficiently; no change in epistemic meaning. |
| D-149 full-text anchor invariant | This paper is intended to satisfy the full-text/anchor requirement if ratified and committed under the canonical docs path. |

---

## 29. Ratification gates

D-150 should pass only if all of the following are proven in code and governance:

1. EvaluationCase and EvaluationEpoch immutability tests pass.
2. Certificate succession is reconstructable from parent hashes and evidence deltas.
3. No path from D-150/Assurance directly mints statutory economic claims.
4. Synthetic evidence remains claim-scoped and non-economic-positive.
5. Hard defeaters propagate deterministically.
6. Policy hash change forces a new case/policy lineage.
7. Holdout-burn semantics remain intact.
8. Sequential monitoring cannot silently reuse fixed-horizon statistical thresholds as anytime-valid evidence.
9. Historical certificates remain reconstructable after supersession/revocation.
10. D150-T01–T20 pass with independent audit.

> **Ratification target:** D-150 may be ratified as an evidence-lifecycle amendment without waiting for a richer Foundry. The Foundry can evolve later; D-150's job is to ensure any future evidence source enters history safely.

---

## 30. Open pins

| Pin | Question | Default until resolved |
|---|---|---|
| `D150-P01` | Which operational estimands require anytime-valid sequential statistics? | Diagnostic-only unless a valid MonitoringPlan exists. |
| `D150-P02` | What freshness/expiry policy should each certificate claim use? | No universal expiry; claim-specific trigger rules only. |
| `D150-P03` | When does a contract/environment change create a new case instead of a new epoch? | If policy, code, config, utility, cost, capacity, information, or authority semantics change materially: new case. |
| `D150-P04` | How should world-space coverage be summarized without scalar readiness? | Typed coverage vector + manifests; no scalar score. |
| `D150-P05` | Can future synthetic qualification be admitted beyond test-only M0? | No until separate D-series amendment. |

---

## 31. Proposed D-150 decree text

> **D-150 — Continuous Epistemic Succession & Living Policy Constitution.**
>
> V8 hereby recognizes that policy identity and evidence validity are distinct, versioned dimensions. No sealed evaluation, evidence epoch, or certificate may be reopened or rewritten. Any new real, prospective, synthetic, adversarial, Oracle, D-136, D-141, execution, or audit evidence that is admissible to a current assurance claim shall enter through a new cryptographically linked `EvaluationEpoch`. Each successor epoch shall preserve exact ancestry, authority bounds, evidence provenance, evaluator/world coverage, statistical-plan identity, and hard-defeater state.
>
> A successor epoch may preserve, supersede, contest, quarantine, or revoke the current `ProductionEvidenceCertificate`. Revocation shall not erase historical certification; it shall terminate its current authority. Material defeat shall be emitted as a typed `DefeaterReceipt` and transferred to the existing Kaizen lifecycle for diagnosis and challenger research. D-150 possesses zero independent policy-mutation, promotion, ClaimRegistry-minting, or economic-authority rights.
>
> Synthetic and adversarial evidence may challenge or falsify bounded robustness, semantic, safety, or integrity claims, but successful synthetic performance shall never by itself establish `SUPPORTED_EDGE`, `REALIZED_CASHFLOW`, expected real return, or physical settlement. Continuous statistical monitoring shall receive inferential authority only under a preregistered, assumption-bound, time-valid monitoring method; otherwise it is diagnostic evidence. All existing constitutional authority, holdout, audit, statistical, and claim-separation laws remain in force unless explicitly superseded by a separately ratified decision.

---

## 32. Conclusion

D-150 closes a specific gap rather than expanding V8 for expansion's sake. Kaizen already supplies policy evolution. D-136 supplies evidence observability. D-138 supplies prospective receipts. D-141 supplies expert qualification. V8.5 Assurance supplies claim composition. The missing element is the law that says what happens when all of those systems produce *new evidence tomorrow*.

The answer is continuous epistemic succession: preserve every historical decision, never reopen sealed evidence, version the current evidence state, let new real/synthetic/adversarial observations challenge present assurance, and send material defeat to Kaizen. The resulting system is not a permanently "certified bot"; it is a policy whose permission to remain trusted is conditional on the strongest current admissible evidence.

$$\text{Policy } P \text{ was supported at epoch } E_0 \quad \neq \quad \text{Policy } P \text{ is supported now.}$$
$$\text{Living V8} = \text{Policy Lineage} \times \text{Evidence Lineage} \times \text{Time}$$

---

## 33. References and source map

1. **[R1] Robustness Gym: Unifying the NLP Evaluation Landscape**. Goel et al. (2021). [https://arxiv.org/abs/2101.04840](https://arxiv.org/abs/2101.04840)<br>
   *Frames evaluation as a continual process rather than a one-shot static artifact.*
2. **[R2] Handling Concept Drift in Global Time Series Forecasting**. Liu, Godahewa, Bandara, Bergmeir (2023). [https://arxiv.org/abs/2304.01512](https://arxiv.org/abs/2304.01512)<br>
   *Shows why non-stationary time-series distributions can degrade forecasting models and motivate adaptation and monitoring.*
3. **[R3] Towards Practicable Sequential Shift Detectors**. Cobb & Van Looveren (2023). [https://arxiv.org/abs/2307.14758](https://arxiv.org/abs/2307.14758)<br>
   *Identifies practical requirements for sequential distribution-shift detection.*
4. **[R4] Diagnostic Runtime Monitoring with Martingales**. Hindy et al. (2024). [https://arxiv.org/abs/2407.21748](https://arxiv.org/abs/2407.21748)<br>
   *Uses streaming martingale monitors to diagnose distribution shifts and connect them to lifecycle interventions.*
5. **[R5] Sequential Model Confidence Sets**. Arnold et al. (2024). [https://arxiv.org/abs/2404.18678](https://arxiv.org/abs/2404.18678)<br>
   *Extends model confidence sets to sequential settings using e-processes and confidence sequences.*
6. **[R6] ANDROIDWORLD: A Dynamic Benchmarking Environment for Autonomous Agents**. Rawles et al. (2024). [https://arxiv.org/abs/2405.14573](https://arxiv.org/abs/2405.14573)<br>
   *Demonstrates dynamic parameterized evaluation tasks beyond a fixed test set.*
7. **[R7] MACEval: A Multi-Agent Continual Evaluation Network for Large Models**. Chen et al. (2025). [https://arxiv.org/abs/2511.09139](https://arxiv.org/abs/2511.09139)<br>
   *Proposes dynamic continual evaluation to reduce closed-ended benchmark overfitting.*
8. **[R8] Towards Causal Market Simulators**. Thumm & Ontaneda Mijares (2025). [https://arxiv.org/abs/2511.04469](https://arxiv.org/abs/2511.04469)<br>
   *Combines generative time-series modeling with structural causal models for counterfactual financial trajectories.*
9. **[R9] Financial Wind Tunnel: A Retrieval-Augmented Market Simulator**. Cao et al. (2025). [https://arxiv.org/abs/2503.17909](https://arxiv.org/abs/2503.17909)<br>
   *Presents controllable synthetic market dynamics for stress testing and model evaluation.*
10. **[R10] High-Quality Synthetic Financial Time-Series using a GAN-Diffusion Framework**. Masi, Coletta & Bartolini (2026). [https://arxiv.org/abs/2605.27113](https://arxiv.org/abs/2605.27113)<br>
    *Highlights the difficulty of preserving stylized facts and inter-asset correlation structure.*
11. **[R11] COvolve: Adversarial Co-Evolution of LLM-Generated Policies and Environments**. Sygkounas et al. (2026). [https://arxiv.org/abs/2603.28386](https://arxiv.org/abs/2603.28386)<br>
    *Models policies and environments as adversarial co-evolving populations.*
12. **[R12] Beyond Static Evaluation: Co-Evolutionary Mechanisms for LLM-Driven Strategy Evolution in Adversarial Games**. Li et al. (2026). [https://arxiv.org/abs/2606.10389](https://arxiv.org/abs/2606.10389)<br>
    *Shows how fixed evaluators can become stale as strategies improve and motivates evaluator co-evolution.*
13. **[R13] Reverse Stress Testing for Multivariate Scenarios: A Conditional Framework for Stressed Time Series**. Sparviero & Viola (2026). [https://arxiv.org/abs/2606.09274](https://arxiv.org/abs/2606.09274)<br>
    *Constructs coherent multivariate stressed scenarios conditional on shocks while preserving dependence structure.*
14. **[R14] Huber-Robust Confidence Sequences**. Wang & Ramdas (2023). [https://arxiv.org/abs/2301.09573](https://arxiv.org/abs/2301.09573)<br>
    *Provides anytime-valid confidence sequences under explicit contamination assumptions.*
