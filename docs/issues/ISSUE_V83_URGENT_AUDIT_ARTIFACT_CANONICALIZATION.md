# [DEFECT] Canonicalize current audit artifacts and block stale-run summaries

## Objective

Eliminate ambiguity between historical V8.3 dossiers, tracked audit outputs,
and untracked `.audit/rust_audit_current` runs so every summary has one
verifiable manifest and contradictory runs fail closed.

## Owning authority

- `docs/protocols/OPERATIONS_SPEC.md` §3–§5.
- `docs/contracts/PERSISTENCE_REPLAY_SPEC.md` §4 and §8.
- `docs/contracts/LEDGER_FORMAT_SPEC.md` §8.
- `docs/WORK_ITEM_POLICY.md` §1 and §7.
- D-079, D-120, D-131.

## Change class

`DEFECT_FIX`

## Current state / observed defect

The working tree contains many untracked current-audit outputs, including
multiple portfolio receipts and funnel/report variants. The committed historical
dossier reports V8.3 Phase I at +3.46% net with production succession denied,
while one untracked current receipt reports a different run outcome. The files
may represent distinct campaigns, but their relationship is not machine-clear.

This makes it too easy to quote a result without proving which code, data,
configuration, authority, and run produced it.

## Required end state

Implement an artifact canonicalization check that:

1. Identifies exactly one declared current run by manifest hash.
2. Requires every report, receipt, funnel, and ledger to point to that manifest.
3. Rejects mixed-run aggregation and stale artifact reuse.
4. Records whether an artifact is tracked historical evidence, current
   diagnostic evidence, or prospective authority evidence.
5. Prevents generated reports from implying a verdict when lineage is missing.

## Expected file / module surface

- Existing audit/report renderer and artifact path code.
- `v8-core/src/evidence.rs`, `v8-core/src/evaluation/manifest.rs`,
  `v8-core/src/evaluation/lineage.rs`, and `v8-core/src/report.rs`.
- Existing `snapshot_meta`, `request_*`, reconciliation, and authority receipt
  schemas.
- A new Rust module or schema is permitted only after a D-series decision and
  `docs/contracts/IMPLEMENTATION_LAYOUT.md` registration.

## Verification gates

```shell
cargo test --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml -- -D warnings
python3 tools/audit_economic_claim.py
python3 tools/audit_synthetic_leakage.py
git diff --check
```

Add tests for two reports from different manifests, stale receipts, missing
artifact files, duplicate current-run declarations, and a clean single-run
bundle.

## Required evidence artifacts

- Canonical current-run manifest.
- Artifact lineage/reconciliation receipt.
- Negative tests proving mixed-run summaries fail closed.
- Clean report generated from one manifest.

## Non-goals / forbidden scope

- No deletion of historical evidence.
- No rewriting of economic results to make runs agree.
- No live trading or promotion.
- No new statistical metrics.
- No conversion of untracked output into certified evidence without provenance.

## 11. Normative traceability

- **R1 —** Bind artifacts to one manifest. Authority: `PERSISTENCE_REPLAY_SPEC` §4, §8.
- **R2 —** Reject mixed or stale lineage. Authority: `LEDGER_FORMAT_SPEC` §8; `OPERATIONS_SPEC` §4–§5.
- **R3 —** Keep historical/current/prospective statuses distinct. Authority: `OPERATIONS_SPEC` §1; D-131.
- **R4 —** Fail closed when evidence is incomplete. Authority: `WORK_ITEM_POLICY.md` §7; D-131.

## 12. Existing types / interfaces to reuse

- Existing manifest, hash, evidence-store, lineage, and reconciliation types.
- Existing artifact status and authority taxonomy.
- Existing report renderer and audit output directories.

## 13. Mathematical / semantic invariants

- Every artifact in a report resolves to exactly one manifest hash.
- A report is valid only if all referenced files exist and their hashes match.
- Historical and current artifacts may be compared only through an explicit
  comparison manifest.
- Missing or ambiguous lineage cannot be silently dropped.

## 14. Canonical failure semantics

- Mixed manifest hashes → reconciliation failure / `BLOCKED / OPEN_PIN`.
- Missing referenced artifact → `BLOCKED / OPEN_PIN`.
- Untracked but otherwise valid diagnostic output → `MODEL_DERIVED` only, never
  certified economic evidence.
- Incomplete authority → `NO_ECONOMIC_CLAIM`.

## 15. Dependency map

```text
run manifest
  -> artifact writer
  -> hash/lineage validator
  -> report renderer
  -> canonical current-run receipt
```

## 16. OPEN_PIN triggers

- Two runs claim the same manifest hash with different bytes.
- A report references a path that is not physically present.
- Historical dossiers and current runs cannot be separated by authority/status.
- The canonical current-run location or retention policy is not specified.
