# [GOV] V8.3 G5 prospective OOS, shadow, and succession authority

## Objective

Pin the exact authority contract that separates the V8.2 production incumbent
from the V8.3 challenger, defines a genuinely prospective out-of-sample (OOS)
shadow run, and specifies the only conditions under which production authority
may transfer.

## Owning authority

- `docs/charter/V8_CONSTITUTION.md` Rules 5, 10, 12, 13, 15, 16, 20, and 24.
- `docs/decisions/DECISION_REGISTER.md` D-128 and D-131.
- `docs/protocols/OPERATIONS_SPEC.md` §1 and §4–§6.
- `docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md` §1, §4, and §6.
- `docs/protocols/KAIZEN_COMPILER_SPEC.md` §5 (DEV → WFA → OOS → SHADOW).
- `docs/dossiers/V83_G5_PROSPECTIVE_CONFIRMATION.md`.

## Change class

`DECISION_RECORD_D_SERIES`

## Current state / contradiction

V8.3 is correctly recorded as `EVIDENCE_NOT_ESTABLISHED` for G5 and retains no
production authority. V8.2 remains incumbent by D-128, but the repository does
not yet expose one short, executable authority statement answering all of these
questions:

1. What exact artifact is the incumbent comparator?
2. What event freezes the V8.3 code, configuration, and data manifest?
3. What data qualifies as genuinely forward prospective data?
4. Which authority receipt is required for succession?
5. What happens when the challenger is underpowered, inconclusive, or fails?

The historical V8.3 result and current audit bundles are not interchangeable
without an exact manifest, commit, tape, and authority binding.

## Required end state

Register the next available D-series decision and update the English/Turkish
decision registers so that the following state machine is normative:

```text
RESEARCH -> FROZEN_PROSPECTIVE_SHADOW -> PAPER -> PROMOTED
                         \-> REJECTED / INCONCLUSIVE / DATA_BLOCKED
```

The decision must state that:

- V8.2 remains incumbent until a separate V8.3 succession receipt exists.
- Prospective OOS begins only after the immutable freeze event.
- Frozen data is opened once, consumed once, and never used for tuning.
- Shadow produces no allocation consequence.
- Any missing, conflicting, stale, or unverifiable authority resolves to
  `BLOCKED / OPEN_PIN` or `NO_ECONOMIC_CLAIM`, never promotion.
- A positive-looking result without certified simulation/venue authority cannot
  produce `SUPPORTED_EDGE` or a production transfer.

## Expected file surface

- `docs/decisions/DECISION_REGISTER.md`
- `docs/tr/DECISION_REGISTER.md`
- `docs/decisions/OPEN_DECISIONS.md`
- `docs/protocols/OPERATIONS_SPEC.md`
- `docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md`
- `docs/CHANGELOG.md`
- regenerated `site/index.html` and `site/tr.html`

No Rust/runtime change belongs in this governance issue.

## Verification gates

```shell
uv run --with markdown tools/build_monograph.py --lang en --docs docs --out site/index.html
uv run --with markdown tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html
python3 tools/audit_economic_claim.py
python3 tools/audit_synthetic_leakage.py
git diff --check
```

## Required evidence artifacts

- New D-series entry with exact status and succession preconditions.
- Updated OPEN_DECISIONS row for any unresolved incumbent-comparator question.
- Byte-identical EN/TR monographs and audit outputs.

## Non-goals / forbidden scope

- No production promotion.
- No frozen OOS opening.
- No threshold, geometry, cost, or expert tuning.
- No economic claim based on historical or counterfactual markout output.

## 11. Normative traceability

- **R1 —** Define the incumbent/challenger authority boundary. Authority: D-128; `V8_CONSTITUTION` Rules 10, 12, 15, 16.
- **R2 —** Define prospective freeze and one-shot OOS semantics. Authority: `HYPOTHESIS_LAB_PROTOCOL` §1, §4, §6; `KAIZEN_COMPILER_SPEC` §5.
- **R3 —** Define shadow and promotion states. Authority: `OPERATIONS_SPEC` §1; `V8_CONSTITUTION` Rule 10.
- **R4 —** Define fail-closed outcomes for missing or conflicting evidence. Authority: `OPERATIONS_SPEC` §5; D-131; `WORK_ITEM_POLICY.md` §7.

## 12. Existing types / interfaces to reuse

- `ExperimentManifest` and existing registry experiment identities.
- Existing authority/status vocabulary: `NO_ECONOMIC_CLAIM`, `BLOCKED / OPEN_PIN`, `DATA_BLOCKED`, `INCONCLUSIVE_UNDERPOWERED`.
- Existing D-series decision and OPEN_DECISIONS table formats.
- Existing `CLAIMS_REGISTRY.yaml` and `EXPERIMENT_REGISTRY.yaml` entries.

## 13. Mathematical / semantic invariants

- Promotion is monotone only after all declared gates and receipts exist.
- A challenger result is bound to `(code_hash, config_hash, dataset_hash,
  authority_hash, freeze_timestamp)`.
- The frozen OOS is not an editable training population.
- `SUPPORTED_EDGE` is unreachable unless the authority tensor, multiplicity
  control, and realized/certified evidence conditions all pass.

## 14. Canonical failure semantics

- Missing freeze or dataset binding → `BLOCKED / OPEN_PIN`.
- Missing authority receipt → `NO_ECONOMIC_CLAIM`.
- Insufficient statistical power → `INCONCLUSIVE_UNDERPOWERED`.
- Conflicting artifact lineage → `BLOCKED / OPEN_PIN`.
- Failed challenger gate → `REJECTED_OPTION`; V8.2 remains incumbent.

## 15. Dependency map

```text
Constitution / D-128 / D-131
        -> this D-series authority
        -> experiment registry + preregistration
        -> prospective shadow runner
        -> frozen OOS verdict
        -> succession receipt or retained V8.2 incumbent
```

## 16. OPEN_PIN triggers

- If V8.2 cannot be represented by a hash-bound, reproducible comparator.
- If “prospective” data is not physically recorded after freeze.
- If the same data can be inspected and then used to tune the challenger.
- If an authority receipt is generated by the implementation under audit.
- If EN and TR authorities diverge.

## References

- `docs/dossiers/V83_G5_PROSPECTIVE_CONFIRMATION.md`
- `docs/dossiers/V83_ANATOMY_TARGET_PREDICTION_AUDIT.md`
- `docs/WORK_ITEM_POLICY.md`
