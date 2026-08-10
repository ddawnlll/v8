# V8.2 Ledger Format Specification

**Status:** PROVISIONAL_DECISION (D-080). This contract defines what the
evidence store persists, in what form, and what it deliberately does not
persist. It supersedes the JSONL-at-slice-scale mapping in
`ARCHITECTURE_SPEC` §3 for the V8.2 compute plane; `PERSISTENCE_REPLAY_SPEC`
remains normative for replay semantics. No economic claim (rule 12).

## 1. The measured problem

One 8,760-bar, single-symbol, three-expert run writes **271.8 MB** of
`states.jsonl` from a **3.5 MB** input tape — a 78x audit-to-evidence ratio. A
single state record is 31,091 bytes for 74 features, composed as
(`PERFORMANCE_AUDIT_V82` §7):

| Component | Share |
|---|---|
| JSON key names, repeated per feature per bar | 33% |
| `history` feature (32 bars of OHLC already in the tape) | 15% |
| `input_lineage_hash` (40 hex per feature) | 10% |
| feature names (map key and `name` field, stored twice) | 9% |
| two timestamps per feature | 9% |
| `dtype` / `feature_version` / `quality` / `group` | 6% |
| **the 74 float values** | **2%** |

The `FeatureValue` record is correctly designed *in memory* — each value
carries its own provenance, which is what makes per-feature auditing possible.
The defect is using the in-memory shape directly as the on-disk shape: the
schema is constant across all 8,760 bars and is nonetheless written 8,760
times.

## 2. Classification: information, schema, derivable

Every field in a persisted record falls into exactly one class.

| Class | Definition | Persisted |
|---|---|---|
| **Identity** | the hash-bound anchor of the record | always |
| **Information** | a value not derivable from other persisted data | always |
| **Schema** | constant for all records of a kind within a run | once, in the header |
| **Run-constant** | constant for all records within a run | once, in the header |
| **Derivable** | a pure function of (tape, code_version, index) | on demand, never stored |

The rule follows from the classification: **persist identity and information,
hoist schema and run-constants into the header, recompute derivables.**

Applied to a state record:

| Field | Class | Fate |
|---|---|---|
| `state_id`, `lineage_hash`, `as_of`, `provenance` | identity | stored |
| the 74 feature values | information | stored, columnar |
| `name`, `dtype`, `group`, `feature_version` | schema | header, once |
| `calculation_time`, `max_input_available_time` | derivable | recomputed from window bounds |
| `input_lineage_hash` | derivable | recomputed from `(tape_hash, lo, hi)` |
| `history` | derivable | a view over the stored tape; only its depth is recorded |
| `quality`, `null_reason` | information | stored (they are decision-relevant; D-024) |

Feature windows are declared constants (`VOLUME_STAT_N`, `CMF_N`, `SWING_NS`,
…), so a window's `(lo, hi)` is a function of the feature name and the bar
index. That is what makes the lineage hash derivable rather than informational.

## 3. Artifact header

Every artifact begins with a header that binds it to its producer. The header
is small, human-readable, and hashed into the artifact identity.

```text
artifact_kind        states | candidates | evaluations | outcomes | cube | regret
hash_encoding        v8.2-ieee-le            (PARITY_AND_IDENTITY_SPEC §4)
schema               ordered field list with dtype/group/version per column
run_constants        data_hash, code_hash, config_hash, simulator_hash,
                     risk_gate_hash, evaluator_version, platform, utility_unit,
                     cost_form, slippage, action_manifest_id
tier                 IDENTITY_ONLY | VALUES | FULL      (§5)
row_count, column_count, ordering key
```

`hash_encoding` is mandatory: without it a V8.2 artifact could be mistaken for
a V8.0 one, whose identities are computed differently and are not comparable.

## 4. Columnar layout

Records are stored column-major, one buffer per field, in a self-describing
container.

- Numeric columns: fixed-width IEEE-754 / two's complement, no decimal text.
  This also removes the float-rendering hazard of §`PARITY_AND_IDENTITY_SPEC` 4
  from the storage path entirely.
- Low-cardinality string columns (`endpoint`, `label_status`, `cell_status`,
  `expert_id`, `direction`): dictionary-encoded to small integer ids, with the
  dictionary in the header.
- Absent values carry an explicit validity bit; absence is never encoded as a
  sentinel number (`MARKET_STATE_CONTRACT` §4).
- Ordering is declared and stable so that two runs of the same request produce
  byte-identical artifacts (`PARITY_AND_IDENTITY_SPEC` G4).

Column-major is not chosen for compression alone: the analysis plane reads a
handful of columns out of dozens, and the evaluator's context partitioning
touches a small declared subset of features. Reading three columns must not
require parsing all seventy-four.

## 5. Tiering

Not every run needs the same evidence depth.

| Tier | Contents | Used for |
|---|---|---|
| `IDENTITY_ONLY` | header + per-record identity and quality | sweeps, cache-warming, exploratory passes |
| `VALUES` | identity + information columns | **default** for research runs |
| `FULL` | `VALUES` + materialized derivables (lineage hashes, per-feature clocks, expanded history) | certification and promotion boundaries |

The tier is recorded in the header and is part of the artifact identity, so a
`VALUES` artifact can never be mistaken for a `FULL` one. Promotion from
`VALUES` to `FULL` is a pure recomputation from the stored tape and pinned
code hash; it never requires re-deciding anything.

This mirrors the program's existing treatment of full replay: exhaustive
materialization belongs at the certification boundary, not on every research
iteration.

## 6. The reproducibility argument, and its cost

Everything dropped in the `VALUES` tier is a pure function of
`(tape, code_version, bar_index)`. The tape is archived (3.5 MB for a
symbol-year), the code version is pinned in git and bound into `provenance`,
and the identity of every dropped derivation is still stored. A recomputed
value is therefore **verifiable against the stored identity** rather than
merely asserted.

Storing a derived value is in one respect weaker: a stored value can drift
silently from the code that claims to produce it, whereas a stored hash cannot.

**The real cost, stated plainly.** Forensics on an old research run no longer
works by reading a file. It requires checking out the pinned code version and
replaying the archived tape. For a `VALUES`-tier run whose code version has
since been garbage-collected or whose tape has been lost, the dropped fields
are unrecoverable and the run is reduced to its identities. Two obligations
follow:

1. A tape referenced by any retained artifact is itself retained. Tape
   retention is not optional storage hygiene; it is what makes the tier legal.
2. Any run that will carry a claim is written at `FULL` tier, before the claim
   is made — not retro-fitted afterwards.

## 7. Storage arithmetic

Per-bar state record, at the research target (15m base, five intervals,
~370 features):

| | Bytes/bar | Per symbol-year | 100 symbols |
|---|---|---|---|
| V8.0 JSONL (measured shape, scaled) | ~150 KB | ~5.3 GB | ~530 GB |
| V8.2 `VALUES` tier (design target) | ~350 B | ~12 MB | ~1.2 GB |

Cube rows, at ~9.9M cells/symbol:

| | Per row | Per symbol | 100 symbols |
|---|---|---|---|
| `OutcomeCubeRow` as JSONL, 35 fields | ~600 B | ~6 GB | ~600 GB |
| Columnar + run-constants hoisted (~11 of 35 fields) + dictionary-encoded | ~40 B | ~400 MB | ~40 GB |
| Streaming reduction, cube not materialized (`OUTCOME_CUBE_SPEC` §4) | — | reduced tables only | ~GB scale |

The V8.0 row is measured; the V8.2 figures are design targets computed from
field widths, not observations, and must be re-measured once the writer exists
(`PERFORMANCE_AUDIT_V82` §9).

## 8. Cheap executable tests

1. **Round-trip:** a `VALUES` artifact plus its tape and pinned code
   regenerates every dropped field, and each regenerated field's hash equals
   the stored identity.
2. **Header completeness:** removing any run-constant from the header and
   re-deriving a row fails closed rather than producing a row with a missing
   field.
3. **Byte-stability:** two runs of the same request produce byte-identical
   artifacts including header ordering.
4. **Tier honesty:** an `IDENTITY_ONLY` artifact cannot satisfy a reader that
   requires values; the failure is explicit, not an empty column.
5. **No decimal floats:** a scan of any numeric column finds no text encoding
   of a float anywhere in the artifact.
6. **Retention:** an artifact whose referenced tape hash is not present in the
   store is reported by the audit tool, not silently accepted.

## 9. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** the 31,091-byte record composition, the
  271.8 MB / 3.5 MB ratio, and the 0.29 ms per-state serialization cost
  (`PERFORMANCE_AUDIT_V82` §7). The key-name share (33%) is computed from key
  lengths, +/-3%.
- **PROJECT_EVIDENCE_SUPPORTED:** `OutcomeCubeRow` carries 35 fields, of which
  ~11 are run-constant, read from `tools/regret.py`.
- **DESIGN_INFERENCE:** the classification scheme, the tiering, the header
  contents, and every V8.2 size figure in §7.
- **Not claimed:** that the `VALUES` tier is sufficient for any particular
  audit. That judgement belongs to whoever defines the certification boundary;
  this contract only guarantees that promotion to `FULL` is a recomputation and
  never a re-decision.
