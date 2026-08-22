# [RESEARCH] Execute the one-shot V8.3 frozen OOS succession experiment

## Objective

Preregister and execute one untouched, chronological, costed OOS comparison of
V8.3 against the approved incumbent, then issue a verdict without reopening or
tuning the holdout.

## Owning authority

- `docs/registries/EXPERIMENT_REGISTRY.yaml`.
- `docs/registries/CLAIMS_REGISTRY.yaml`.
- `docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md` §4–§6 and §8.
- `docs/protocols/SWEEP_PROTOCOL.md` §7.
- `docs/protocols/OPERATIONS_SPEC.md` §1 and §4.
- D-044, D-046, D-128, D-131.

## Change class

`EXPERIMENT_PREREGISTRATION`

## Current state / null hypothesis

V8.3 has historical diagnostic evidence and a funnel, but G5 prospective
evidence is absent. The current statistical substrate may correctly return
`INCONCLUSIVE_UNDERPOWERED`; that is a valid result, not a failure to be
patched. The null is that the V8.3 challenger does not improve the declared
after-cost objective over the incumbent under the preregistered comparison.

## Required end state / falsifiable hypothesis

Before opening the OOS, freeze:

- exact code and configuration hashes;
- the physically collected future data window and its authority;
- incumbent and challenger identities;
- cost, fill, risk, exposure, and clock policies;
- primary outcome and uncertainty method;
- multiplicity/search accounting and the promotion threshold;
- minimum support/power condition and all rejection outcomes.

H1: the V8.3 challenger beats the approved simpler/incumbent baseline on the
declared after-cost objective with the registered uncertainty and multiplicity
controls. H1 is rejected or remains inconclusive if any required condition is
not met.

## Expected file / module surface

- `docs/registries/EXPERIMENT_REGISTRY.yaml`
- the relevant preregistration document under `docs/protocols/` or `docs/`
- Rust evaluation/receipt code already owning the statistic
- generated evaluation artifacts under the declared audit output directory
- `docs/CHANGELOG.md` and EN/TR monographs if authorities change

Do not add a new statistical implementation if the existing Rust statistics
module owns the required method.

## Verification gates

```shell
cargo test --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml -- -D warnings
python3 tools/audit_economic_claim.py
python3 tools/audit_synthetic_leakage.py
```

The run must verify, from receipts:

- chronological/PIT integrity;
- no post-freeze tuning or second query;
- baseline/challenger comparability;
- block dependence and declared clustering;
- within-family and cross-family multiplicity accounting;
- null-world / direction-scrambled controls;
- authority and cashflow provenance;
- complete artifact lineage.

## Required evidence artifacts

- Immutable preregistration and experiment manifest.
- Dataset and collection-authority receipt.
- Per-candidate/campaign ledger and reconciliation output.
- Statistical result with computed uncertainty and multiplicity receipt.
- Final verdict receipt: `PROMOTE`, `REJECTED_OPTION`, or
  `INCONCLUSIVE_UNDERPOWERED` / `NO_ECONOMIC_CLAIM`.

## Non-goals / forbidden scope

- No tuning after OOS opening.
- No second look at the same holdout.
- No synthetic future data or fabricated trade excursions.
- No conversion of counterfactual markout into realized PnL.
- No production succession from this issue alone.

## 11. Normative traceability

- **R1 —** Freeze before OOS opening and burn the holdout once. Authority: `HYPOTHESIS_LAB_PROTOCOL` §1, §6; D-128.
- **R2 —** Compare against a declared simpler/incumbent baseline. Authority: `V8_CONSTITUTION` Rule 5; `EXPERIMENT_REGISTRY.yaml`.
- **R3 —** Apply registered dependence and multiplicity controls. Authority: D-044/D-046; `SWEEP_PROTOCOL` §7.
- **R4 —** Keep all uncertified results at `NO_ECONOMIC_CLAIM`. Authority: D-131; `CLAIMS_REGISTRY.yaml`.

## 12. Existing types / interfaces to reuse

- Existing experiment registry schema and `ExperimentManifest`.
- Rust `v8-core/src/evaluation/statistics.rs` and
  `v8-core/src/statistics/` methods.
- Existing evidence/authority/lineage/reconciliation receipts.
- Existing baselines: `NO_TRADE`, `DIRECTION_SCRAMBLED`, and the declared
  deterministic incumbent comparator where authority permits.

## 13. Mathematical / semantic invariants

- The estimand and decision rule are fixed before the holdout is read.
- Search dimensions are counted before verdict and cannot be retroactively
  removed.
- A missing or unsupported observation is explicit absence, never a substitute
  value.
- Statistical significance without valid authority does not imply economic
  support.

## 14. Canonical failure semantics

- PIT violation or post-freeze mutation → `BLOCKED / OPEN_PIN`.
- Insufficient support/power → `INCONCLUSIVE_UNDERPOWERED`.
- Multiplicity or null-control failure → `REJECTED_OPTION`.
- Missing authority/cashflow evidence → `NO_ECONOMIC_CLAIM`.
- Conflicting ledger/artifact lineage → reconciliation failure and no verdict.

## 15. Dependency map

```text
authority decision
  -> preregistration + immutable manifest
  -> future PIT dataset
  -> incumbent/challenger replay
  -> statistical + multiplicity evaluation
  -> independent authority review
  -> succession decision (or incumbent retained)
```

## 16. OPEN_PIN triggers

- The V8.2 incumbent cannot be run or represented by a reproducible artifact.
- The future data window was touched by model selection.
- The declared outcome differs between historical dossier and canonical runner.
- The required multiplicity/e-process method is not valid for the episode stream.
- The experiment needs a new metric, threshold, or claim class not already owned
  by a registered authority.
