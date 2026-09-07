# D-159 Research-Validity Audit: Receipt Self-Verification, Policy-Bound Parity, Gate Authority Firewall and Governance Reconciliation (Full-Text Specification)

**Status:** PROVISIONAL_DECISION · **Date:** 2026-09-07 · **Rules:** 5, 12, 28–31, 44, 51–57
**Supersession:** Extends D-153, D-152, D-151, D-150, D-149, D-147, D-138, D-136, D-118, D-116; preserves all locked invariants. Adds no economic authority and relaxes no gate.
**Issues closed:** #327, #328, #329, #330.
**Artifacts:** `v8-core/src/benchmark/gate_authority.rs`, `v8-core/src/benchmark/receipt.rs`, `v8-core/src/benchmark/ledger.rs`, `v8-core/src/benchmark/parity.rs`, `v8-core/src/benchmark/external.rs`, `v8-core/src/benchmark/certificate.rs`, `v8-core/src/benchmark/runner.rs`, `v8-core/src/benchmark/types.rs`, `v8-core/src/main.rs`, `v8-core/tests/d152_gate_vector_authority_firewall.rs`, `v8-core/tests/d153_receipt_ledger_selfverify.rs`, `v8-core/tests/d153_parity_adapters_policy_bound.rs`, `v8-core/tests/d153_benchmark_fabric_sabotage.rs`, `docs/contracts/D153_BENCHMARK_FABRIC_SPEC.md`, `docs/tr/D153_BENCHMARK_FABRIC_SPEC.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.
**Turkish mirror:** `docs/tr/D159_RESEARCH_VALIDITY_AUDIT_SPEC.md` (translation; the English text in this file is normative).
**ID allocation note:** D-154, D-155, D-156, D-157 and D-158 were already allocated to the concurrent performance work-stream (#332–#336, branches `perf/332-cargo-profile-split`, `perf/333-consolidated-test-harness`, `perf/334-bootstrap-scratch-buffer`, `perf/335-zero-copy-hist-bar`, `perf/336-rayon-parallelism`), several of which are not merged to `main`. This audit therefore registers under D-159. No D-15x identifier is reused, redefined or double-allocated by this decision.

---

## 1. Problem Statement

The D-153 Benchmark Fabric shipped with four independent breaks in its trust
chain. Each one made weak evidence *look* certified rather than making it
certifiable:

1. **#327 — the gate vector was not the registered gate vector.**
   `GateVector` carried six positions while D-152 §5 and D-153 §2.4 register
   G0–G9 as nine non-compensable positions, and `GateState` had no way to
   express "this gate was never evaluated". A run that simply did not compute
   G6–G9 read as "nothing failed". Separately, `PolicyCertificate` derived its
   own readiness locally and could print `PRODUCTION_READY` from a scalar
   `CapabilityScore`, minting authority inside a renderer.

2. **#328 — receipts and the ledger trusted the digest they were storing.**
   `BenchmarkReceipt::compute_digest()` hashed a hand-assembled field list, and
   the ledger wrote `digest == entry_hash`. Any field outside that list —
   artifact provenance, method versions, gate provenance — could change under a
   fixed digest. There was no path that recomputed the digest from canonical
   bytes at read time, so tampering was undetectable by construction.

3. **#329 — external parity was fabricated.**
   `external.rs::evaluate_parity(policy_id)` discarded its `policy_id` argument
   as `_policy_id` and compared two hardcoded arrays (`[0.012, -0.005, ...]`
   against `[0.0121, -0.0049, ...]`). `fill_timing_mae_ms` was hardcoded to
   `0.0`, and `maximum_drawdown_discrepancy_bps` was derived by multiplying the
   PnL discrepancy by 1.5 / 1.2 / 1.1 per engine. That is not parity against an
   external engine; it is a fixed vector that always reports a near-miss inside
   a bps tolerance the parity spec forbids. It satisfied D-153 §2.6 in name only.

4. **#330 — governance diverged from the tree.**
   The D-153 spec header claimed `RATIFIED_DECISION` while both decision
   registers said `PROVISIONAL_DECISION`; the registers, the spec header and the
   CHANGELOG all cited `v8-core/tests/benchmark_fabric_adversarial.rs`, a file <!-- AUDIT-DOC-PATHS: NEGATIVE_CITATION `v8-core/tests/benchmark_fabric_adversarial.rs` is cited here precisely because it never existed; the real D-153 suite is `v8-core/tests/d153_benchmark_fabric_sabotage.rs`. -->
   that has never existed; the Turkish full-text mirror of D-153 was missing
   while the Turkish register cited it; `IMPLEMENTATION_LAYOUT.md` still
   described the deleted adapter API; and the CHANGELOG claimed D-153
   "Ratified and fully completed" while D-156's benchmark-evaluator OPEN_PIN was
   (and remains) open.

The common failure mode is the same in all four: **a stored assertion was
treated as its own proof.** D-159 records the replacements and pins the
properties that prevent recurrence.

---

## 2. Normative Requirements

### 2.1 Gate vector and authority firewall (#327)

**R2.1.1** `GateVector` SHALL expose exactly the registered positions G0–G9.
`types::GATE_DESCRIPTORS` is the single source for position → name → owner.

**R2.1.2** `GateState` SHALL be a four-variant lattice: `Pass`, `Fail`,
`Blocked`, and `Missing`. `Missing` is **not** a pass and is not
"not-applicable": it means the gate was never computed. `readiness()` SHALL
degrade on `Missing` and SHALL never promote on it.

**R2.1.3** Every gate failure SHALL carry a `GateFailureClass` so that a
failure is attributable to data absence, semantic divergence, statistical
refutation, or policy violation rather than being an opaque boolean.

**R2.1.4** `ReadinessVerdict` SHALL be produced by
`gate_authority::AuthorityFirewall` and SHALL be a *projection* of inputs.
No renderer, report, or certificate is permitted to compute authority from
scratch.

**R2.1.5** `cap_authority(a_in, a_out)` SHALL enforce monotone
non-escalation: `a_out ≤ a_in` under the `EvidenceAuthority` order. Rendering
steps SHALL be asserted against this at every stage; the property is checked by
test, not assumed.

**R2.1.6** Any claim of `SUPPORTED_EDGE` or production promotion SHALL resolve
through `ClaimRegistry`. `AuthorityDecision::Registered` SHALL be reachable only
via `AuthorityFirewall::route_claim`, which verifies registry membership.
Absent, `N/A`, `UNKNOWN`, `MISSING` or `BLOCKED` required evidence SHALL yield
`NO_ECONOMIC_CLAIM` or `BLOCKED` — never a pass.

**R2.1.7** `PolicyCertificate` SHALL NOT be able to derive a status string
stronger than its gate vector permits. `to_status_string()` is a function of the
projected verdict, and `MISSING`/`Blocked` gates ceiling the certificate.

**R2.1.8 (OPEN_PIN, carried, not resolved).** D-152 §5 names G7 prospective
shadow, G8 live realization, G9 certificate; the D-153 `GateVector` field names
are `g7_generalization`, `g8_prospective_shadow`, `g9_live_realization`. This
decision does not adjudicate the conflict. Mapping is positional, neither
register is rewritten, and the conflict is surfaced as
`OPEN_PIN_GATE_NAMING` plus `AuthorityDecision::OpenPin`. Per-gate narrative
that depends on which position *is* the live-realization gate SHALL NOT be
authored until the register conflict is settled by a governance decision.
Readiness under either reading is identical, so no gate is weakened by deferral.

### 2.2 Cryptographic receipt and ledger self-verification (#328)

**R2.2.1** `BenchmarkReceipt::compute_digest()` SHALL be a canonical digest over
the *whole* receipt, produced through `crate::hash::Canon`, not over an
ad-hoc field list. No authority-relevant field may live outside the digest.

**R2.2.2** The digest algorithm identity SHALL be versioned and recorded on the
receipt: `d153.receipt.v2` is current; `d153.receipt.v1` is a permanently
recognised legacy identity. Verification SHALL dispatch on the recorded version
rather than silently accepting either.

**R2.2.3** `BenchmarkProvenance` and `ArtifactBinding` SHALL bind every consumed
artifact (path, SHA-256, byte length, role) and every method/version string that
can change a result. Referencing an artifact that was not physically produced and
verified on disk is a critical system hallucination under the anti-synthetic
directive, not a documentation slip.

**R2.2.4** A receipt is only evidence once re-verified. `verify()` SHALL
recompute from canonical bytes; `verify_artifacts()` SHALL re-hash the physical
files; `verify_policy_identity()` SHALL reject identity drift. Report rendering
SHALL require a `VerifiedReceipt`, and the JSON and HTML renderers SHALL stamp
the recomputed digest and verification metadata so the reader can see which
digest was checked. HTML SHALL refuse to render an unverified receipt.

**R2.2.5** The ledger SHALL seal each entry with a `d153.ledger.v2` entry seal
that folds the full canonical receipt encoding into the hash chain, so the chain
binds content and not the stored digest. The ledger SHALL expose `audit()` and
`load_with_report()` returning a `LedgerAuditReport` with stable tamper codes and
a `LedgerTamper` classification per row.

**R2.2.6** Digest comparison SHALL be constant-time. Non-finite metric values
SHALL be rejected at construction rather than canonicalised into a digest. A
canonical tree that produces an unexpected null SHALL be an error, not a silent
zero.

**R2.2.7 (Honest legacy boundary).** Rows written before v2 have no recoverable
binding. The system SHALL classify them `legacy_unbound`, SHALL NOT count them as
verified, and SHALL exit `3` with `LEDGER_PARTIALLY_BOUND`. On the audit
repository's real ledger (7 rows, all pre-v2) every row is reported
legacy-unbound. Deleting or rewriting them is not permitted; claiming they verify
is not permitted.

### 2.3 Policy-bound external parity adapters (#329)

**R2.3.1** Parity SHALL be computed from two physical ledger artifacts — a
native side and a reference side — both of which SHALL be declared in the case
evidence manifest before evaluation. There is no in-process reference
implementation and no fixed expected vector.

**R2.3.2** `SemanticMapping` (version `v8.d153.parity.mapping.v1`) SHALL declare
how the two records correspond: pairing key, PnL field, optional fill-time field,
optional sequence field. A parity result is only meaningful relative to a named
mapping; the mapping identity is recorded on the receipt. Parity without a
mapping is undefined, not defaulted.

**R2.3.3** Tolerance-based parity is prohibited by
`docs/contracts/PARITY_AND_IDENTITY_SPEC.md`. PnL comparison SHALL use IEEE-754
bit-pattern equality (`to_bits()`), not `==`, so that `NaN`, signed zero and
last-bit drift are distinguished rather than averaged away. Outcomes are
`ExactMatch`, `Diverged`, `UnsupportedSemantics`, `UnpairedRecords` or
`DataBlocked`; there is no "within tolerance" outcome.

**R2.3.4** Fill-time divergence SHALL count as a mismatch wherever both sides
carry fill times. Where either side lacks fill times, the diagnostic SHALL be
`None` — never `0.0`. Fabricated zero error is prohibited.

**R2.3.5** Drawdown and equity diagnostics SHALL be computed from the equity
curves, ordered by the declared `sequence_field` when present. If the mapping
declares a sequence field but a ledger is only partially sequenced, the drawdown
diagnostic SHALL be `None` rather than a best-effort guess.

**R2.3.6** `EngineVersion` and method versions SHALL be real version or build
identifiers. Placeholders (`"N/A"`, `"unknown"`, `"TBD"`, empty) SHALL block the
evaluation (`DataBlocked`), not pass through.

**R2.3.7** Parity authority SHALL be *derived*, never stored.
`ParityReceipt::authority()` computes from the D-152
`BENCHMARK_DIAGNOSTIC_AUTHORITY` ceiling; the serialised receipt exposes
`authority_class()` only and carries no `authority` field that could be forged by
deserialisation. Parity output is a non-sovereign diagnostic observation.

**R2.3.8** `BenchmarkReceipt::with_parity()` SHALL reject identity mismatch,
policy mismatch, case-hash mismatch and conflicting artifact hashes; SHALL merge
artifact bindings; and SHALL recompute the receipt digest. Parity cannot be
grafted onto an unrelated receipt.

**R2.3.9 (Honest gap, carried).** `reconciliation_gaps()` SHALL state explicitly
that commission, funding and terminal-balance parity are **not** mapped for
D-116 reconciliation, so a `ExactMatch` on PnL and fill timing is not mistaken
for full economic reconciliation.

**R2.3.10** The deleted fabricated API (`CommodityExecutionAdapter`,
`LeanParityAdapter`, `SkfolioParityAdapter`, `VectorBtParityAdapter`,
`ExecutionParityReport`, `evaluate_parity`, `parity_passed`) SHALL NOT return.
Regression tests assert at source level that the fixed literals, the discarded
`_policy_id` parameter and the fabricated drawdown multipliers are absent from
`v8-core/src/benchmark/`.

### 2.4 Governance and documentation reconciliation (#330)

**R2.4.1** Normative status SHALL have exactly one owner per artifact. Where a
spec header and the decision register disagree on status, the register governs
and the header is corrected. D-153 remains `PROVISIONAL_DECISION`.

**R2.4.2** Every path cited by `docs/`, `docs/contracts/`, `docs/tr/` and the
decision registers SHALL resolve to a file present in the tree. Phantom
references are a contract violation, not a typo, because they are the mechanism
by which unproduced artifacts acquire apparent provenance.

**R2.4.3** Rule 44 / D-149 require unabridged full-text specifications, and the
Turkish register cites Turkish full text. Therefore every decision cited by
`docs/tr/DECISION_REGISTER.md` SHALL have an EN source and a TR mirror; a
register row pointing at a non-existent mirror is a Rule 44 anchor failure.

**R2.4.4** `docs/contracts/IMPLEMENTATION_LAYOUT.md` SHALL be reconciled to the
as-built tree: new modules registered (§1.1 tree, §2 file contract), deleted API
surfaces removed, divergences recorded in §4 rather than left as silent drift.

**R2.4.5** `docs/CHANGELOG.md` completion claims SHALL be bounded by observed
verification. "Ratified and fully completed" is not permitted while a
registered OPEN_PIN in the same decision family is open; the entry SHALL state
what is implemented, what is verified with counts, and what remains blocked.

**R2.4.6** Monographs (`site/index.html`, `site/tr.html`) are generated
artifacts. They SHALL be regenerated by `tools/build_monograph.py`, never
hand-edited, so generated HTML cannot drift from its `docs/` source.

**R2.4.7** A guard SHALL exist for R2.4.2. `tools/audit_doc_path_refs.py`
resolves repository paths cited in documentation and fails on unresolved
references. Prose, git object ids and commit shas are excluded so the guard
stays actionable instead of being disabled by noise.

---

## 3. Explicitly Not Granted

D-159 grants no authority beyond what it constrains. In particular:

1. No `SUPPORTED_EDGE`, no deployment authority, no promotion. Every verdict in
   scope remains `NO_ECONOMIC_CLAIM` (Constitution Rule 12).
2. D-153 is **not** ratified by this decision and its status is **not**
   upgraded. `PROVISIONAL_DECISION` stands.
3. The registered benchmark-evaluator OPEN_PIN from D-156 remains **open**: no
   benchmark receipt is emitted without a registered data-backed evaluator.
4. The #327 G7–G9 naming conflict remains an **OPEN_PIN**.
5. Pre-v2 ledger rows remain **unbound**, not verified.
6. D-116 commission / funding / terminal-balance parity remains **unmapped**.
7. No economic metric, p-value, effect size, tolerance or expected improvement
   is introduced anywhere in this work. The fabricated vectors and multipliers
   are removed, not recalibrated.
8. The audit work in this branch is delivered as a **PR for maintainer review**.
   It is not merged, and no direct push to `main` is made.

---

## 4. Verification Contract

| Check | Command / evidence | Required result |
|---|---|---|
| Canonical gate vector + firewall | `cargo test --manifest-path v8-core/Cargo.toml --test d152_gate_vector_authority_firewall` | 15 passed |
| Receipt + ledger self-verification | `cargo test --manifest-path v8-core/Cargo.toml --test d153_receipt_ledger_selfverify` | 40 passed |
| Policy-bound parity adapters | `cargo test --manifest-path v8-core/Cargo.toml --test d153_parity_adapters_policy_bound` | 50 passed |
| BFS sabotage suite | `cargo test --manifest-path v8-core/Cargo.toml --test d153_benchmark_fabric_sabotage` | 24 passed (BFS-001..024) |
| Workspace regression | `cargo test --manifest-path v8-core/Cargo.toml` | 0 failed |
| Lint gate | `cargo clippy --manifest-path v8-core/Cargo.toml --all-targets -- -D warnings` | clean |
| Python boundary frozen | `.venv/bin/python tools/audit_python_boundary.py` | pass |
| Synthetic leakage | `python3 tools/audit_synthetic_leakage.py` | pass |
| Economic claim guard | `python3 tools/audit_economic_claim.py` | pass |
| Doc path references (new, R2.4.2) | `python3 tools/audit_doc_path_refs.py` | pass with scoped baseline |
| Monographs regenerated (R2.4.6) | `uv run --with markdown tools/build_monograph.py --lang en|tr ...` | regenerated, not edited |
| Parity CLI, exact | `v8-core benchmark parity …` on identical ledgers | `PARITY_EXACT_MATCH`, exit `0`, gaps printed |
| Parity CLI, divergent | same on perturbed reference | `PARITY_DIVERGED`, exit `1` |
| Parity CLI, placeholder versions | `--engine-version N/A` | blocked, exit `1` |
| Parity CLI, undeclared artifacts | unlisted ledger path | blocked, exit `1` |
| Legacy ledger audit | `v8-core benchmark ledger audit` on `.audit/benchmark/ledger.jsonl` | 7 rows `legacy_unbound`, exit `3`, `LEDGER_PARTIALLY_BOUND` |

---

## 5. Consequences for Existing Contracts

- **D-153 §2.6** is now implemented as written (typed adapters, recorded
  semantic divergence, parity attribution) rather than as fixed vectors.
  §2.6's normative text is unchanged; only its implementation status moved.
- **D-152 §5/§6** gains an enforcement point: the firewall is the single
  boundary between benchmark evidence and authority, and readiness cannot be
  produced locally by a certificate.
- **D-118 / D-138** identity and hashing are reused, not duplicated: `Canon`
  canonical bytes and the existing content-addressed artifact hash. D-153's
  non-goal of "no new identity mechanism without a registered reason" holds.
- **D-116** parity reconciliation is narrower than the ledger might imply, and
  `reconciliation_gaps()` is the machine-readable statement of that narrowness.
- **D-149 / Rule 44** is satisfied for both D-153 (TR mirror added) and this
  decision (EN full text + TR mirror).
