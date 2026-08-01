# V8 Learning Protocol v0.1

**Status:** PROVISIONAL_DECISION. Learning is offline, registry-gated, and
one-directional. It consolidates the pieces already present in the corpus
(hypothesis lab, shadow/promote pipeline, deferred scorer/RL) into a single
protocol whose central rule is: **outcome data never mutates an active
Expert, Scorer, or Executor.**

## 1. One-directional time flow

```text
Outcome ledger
  -> offline experiment (preregistered, costed, frozen OOS)
  -> challenger version (new immutable artifact)
  -> shadow comparison
  -> registry decision (REJECT | MERGE | QUARANTINE | SHADOW | PROMOTE)
  -> future decisions
```

Never:

```text
Outcome -> active model weight update
```

A system that retrains against the last trades is policy churn, not learning
(`V8_CONSTITUTION` rule 15).

## 2. Inputs and outputs

**Inputs:** immutable decision ledger, mature outcome views, execution ledger,
`ExperimentManifest`.

**Allowed outputs:** `ExpertRevisionProposal`, `ScorerModelArtifact`,
`PathModelArtifact`, `ExecutionPolicyChallenger`, `RegistryDecision`.

**Forbidden:** online mutation of an active Expert; outcome access from the
decision plane; silent parameter updates; auto-promotion; frozen-OOS reuse;
overwriting previous versions.

## 3. Learning ladder — one moving part at a time

| Step | Question | Learning type | First algorithm |
|---|---|---|---|
| A | Does this Expert carry after-cost value? | statistical audit | walk-forward, block bootstrap, family correction |
| B | Is this Candidate worth taking? | supervised | logistic regression -> shallow GBDT |
| C | When does a Candidate trigger/invalidate? | time-to-event | discrete hazard / quantile regression |
| D | How is entry executed better? | sequential control | heuristic -> contextual bandit -> conservative offline RL |
| E | Which Experts run? | routing | none initially; full self-gating is the baseline |

Only one learned component may be active in the decision path at any time
(`V8_CONSTITUTION` rule 14). A learned component enters through the same
`ExpertContract` as a deterministic Expert — the Candidate store must not know
whether an Expert is an if-statement, a LightGBM, or a GRU. Training happens
outside the Expert: `trainer.fit(frozen_dataset) -> model_artifact_v2 ->
Expert v2 challenger`.

## 4. What learning never decides

No learned component may set direction, maximum risk, invalidation, expiry, or
maximum size; those are predeclared by the Expert and are hard constraints.
Risk preferences are hard constraints, not reward penalties — a forbidden
action is masked, not punished.

## 5. Cheap executable tests

1. An attempt to mutate an active Expert's definition from outcome data fails.
2. A challenger without a registry decision cannot affect the decision plane.
3. Outcome-ledger access from an Expert evaluation raises.
4. Retraining reads only materialized views and pinned hashes; raw tape access
   in training fails (`DATASET_SPEC` section 5).
5. A second learned component cannot be admitted while one is already active
   in the decision path.
