# [IMPL] Build the hash-bound prospective shadow runner

## Objective

Implement the smallest Rust-only runner that records V8.3 beside the approved
incumbent on genuinely prospective data, with immutable manifests, no
allocation consequence, and fail-closed receipts.

## Owning authority

- The governance decision produced by `ISSUE_V83_URGENT_G5_SUCCESSION_AUTHORITY.md`.
- `docs/protocols/OPERATIONS_SPEC.md` §1, §3–§6.
- `docs/protocols/HYPOTHESIS_LAB_PROTOCOL.md` §1, §4, §6.
- `docs/contracts/PERSISTENCE_REPLAY_SPEC.md` §4 and §8.
- `docs/contracts/DATASET_SPEC.md` §3.
- D-079, D-080, D-097, D-120, D-128, and D-131.

## Change class

`CONTRACT_IMPLEMENTATION`

## Current state

The repository has hash-bound manifests, Rust runloops, evidence artifacts, and
authority firewalls, but no single executable path whose primary purpose is:

```text
freeze -> record future tape -> run incumbent + challenger -> compare -> receipt
```

Historical audit HTML and ad-hoc current bundles can therefore be mistaken for
prospective shadow evidence unless their lineage is manually reconstructed.

## Required end state

Add the minimal Rust wiring needed to:

1. Accept a pre-freeze manifest naming code, config, dataset authority, cutoff,
   incumbent comparator, challenger, and risk policy.
2. Refuse any tape row at or before the freeze cutoff when the run is declared
   prospective.
3. Run incumbent and challenger through the same canonical data and execution
   path where the authority contract permits.
4. Produce separate, content-addressed shadow artifacts and a reconciliation
   receipt; never write a promotion decision from the runner.
5. Preserve the incumbent when the challenger is missing, underpowered,
   inconclusive, or economically uncertified.

## Expected file / module surface

First inspect and reuse:

- `v8-core/src/evaluation/manifest.rs`
- `v8-core/src/evaluation/paths.rs`
- `v8-core/src/experiment.rs`
- `v8-core/src/evidence.rs`
- `v8-core/src/authority.rs`
- `v8-core/src/runloop.rs`
- `v8-core/src/opportunity/runloop.rs`
- `v8-core/src/hash.rs`

Any new Rust module requires a D-series registration and an update to
`docs/contracts/IMPLEMENTATION_LAYOUT.md` before implementation is considered
ready.

## Verification gates

```shell
cargo test --manifest-path v8-core/Cargo.toml
cargo check --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml -- -D warnings
python3 tools/audit_python_boundary.py
python3 tools/audit_synthetic_leakage.py
```

Add tests for:

- cutoff boundary inclusion/exclusion;
- changed code/config/data hashes;
- duplicate/replayed shadow runs;
- missing future rows;
- conflicting incumbent/challenger lineage;
- no allocation side effect;
- byte-identical reruns from the same manifest.

## Required evidence artifacts

- Freeze manifest with code/config/dataset/authority hashes.
- Prospective data-ingest receipt with physical collection timestamps.
- Incumbent and challenger shadow reports.
- Reconciliation and no-promotion receipt.
- Test receipt proving no frozen OOS mutation.

## Non-goals / forbidden scope

- No live order placement.
- No automatic promotion or model tuning.
- No synthetic future tape, offset markouts, or hardcoded metrics.
- No Python runtime dependency.
- No replacement of V8.2 before the separate succession gate passes.

## 11. Normative traceability

- **R1 —** Bind every shadow run to an immutable manifest. Authority: `PERSISTENCE_REPLAY_SPEC` §4; D-079/D-120.
- **R2 —** Enforce post-freeze prospective data only. Authority: `DATASET_SPEC` §3; `HYPOTHESIS_LAB_PROTOCOL` §6.
- **R3 —** Keep shadow allocation-neutral and prevent auto-promotion. Authority: `OPERATIONS_SPEC` §1; D-128.
- **R4 —** Emit only hash-bound evidence artifacts. Authority: `PERSISTENCE_REPLAY_SPEC` §8; D-131.

## 12. Existing types / interfaces to reuse

- `ExperimentManifest`, `EvidenceStore`, `AuthorityReceipt`, `ReconciliationReceipt`.
- Canonical `DataSet`/tape ingestion and `hash` identity functions.
- Existing `NO_ECONOMIC_CLAIM`, `DATA_BLOCKED`, and `INCONCLUSIVE_UNDERPOWERED`
  status values.
- Existing Rust scalar/CPU execution backends; do not create a second simulator.

## 13. Mathematical / semantic invariants

- `manifest_hash = H(code_hash, config_hash, dataset_hash, authority_hash,
  freeze_cutoff, comparator_id, challenger_id)`.
- For a prospective run, every consumed observation has
  `knowledge_time > freeze_cutoff`.
- Same manifest + same tape must yield byte-identical receipts.
- Shadow output cannot mutate allocation state or emit `PROMOTE`.

## 14. Canonical failure semantics

- Missing/invalid manifest → existing manifest validation failure.
- Tape row violating cutoff → `BLOCKED / OPEN_PIN`.
- Missing future data → `DATA_BLOCKED`.
- Changed artifact hash → stale/corrupt artifact rejection.
- Missing authority → `NO_ECONOMIC_CLAIM`.

## 15. Dependency map

```text
governance D-series
  -> preregistered ExperimentManifest
  -> canonical dataset ingest
  -> incumbent/challenger same-path run
  -> EvidenceStore + reconciliation
  -> shadow receipt (no promotion)
```

## 16. OPEN_PIN triggers

- No reproducible V8.2 comparator can be identified.
- The incumbent requires a different economic simulator without an authority
  decision.
- The data provider cannot prove collection after freeze.
- A new artifact/status/error type is needed but no owning contract exists.
