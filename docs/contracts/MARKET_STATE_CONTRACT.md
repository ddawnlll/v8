# V8 MarketState Contract

**Status:** PROVISIONAL_DECISION.  This is a causality contract, not evidence that
state-based routing or any proposed feature has predictive value.

## 1. Terms and clocks

For a datum `d`, retain four distinct times (UTC, nanosecond precision where the
source supports it):

| Field | Meaning | May it gate a decision at `D`? |
|---|---|---|
| `event_time` | When the underlying market/economic event occurred. | No, by itself. |
| `source_time` | Timestamp asserted by the venue/publisher. | No, by itself. |
| `available_time` | Earliest time V8's configured live feed could have delivered this exact version. | Yes, iff `<= D`. |
| `ingested_time` | When this run stored it. | Never a proxy for availability. |

`knowledge_time` is the decision clock `D`: the largest time at which every input
used by a decision was available. It is stored on every decision artifact.

**LOCKED_INVARIANT — admissibility:**

```text
d is admissible at D iff d.available_time <= D
  AND d.version was the version available at D
  AND d is in the point-in-time instrument universe at D.
```

`available_time` includes configured feed latency and any deliberate processing
latency. When it is unknown, the datum is **not admissible** for production-like
research; a conservative, documented bound may only be used for an explicitly
`RESEARCH_ONLY` run. Receipt/ETL time cannot repair an unknown historical
availability time.

## 2. MarketState value

At decision clock `D`, `MarketState` is an immutable, versioned value:

```text
S(D, U, C) = {
  state_id, as_of=D, universe_id=U, clock_policy_id=C,
  observations: [ObservationRef],
  features: [FeatureValue], quality: StateQuality,
  provenance: {raw_manifest_hash, feature_graph_version, code_version},
  lineage_hash
}
```

`U` is the point-in-time tradable universe; `C` defines session, venue, latency,
bar-close, and finality policy. A state is a snapshot for a **single decision
clock**, not a mutable cache or a synonym for “regime.” Regime labels are optional
features with their own availability and model version.

Every `FeatureValue` has:

```text
feature_name, value, dtype, feature_version, input_lineage_hash,
calculation_time, max_input_available_time, quality_flag, null_reason
```

The builder must assert `max_input_available_time <= as_of`. Derived values must
be computed only from admissible raw versions.  A feature cannot silently replace
an unavailable input with a later revised value.

## 3. Observation and bar semantics

* Raw market events use the venue sequence/order when available; otherwise retain
  provider sequence and mark ordering quality. Equal timestamps have deterministic
  tie-break `(venue, channel, sequence, received_sequence)`.
* A bar `[start, end)` becomes usable only at its `bar_available_time`, normally
  `end + feed_latency + aggregation_latency`; its close/high/low/volume are not
  visible within the bar. `current_bar` features are forbidden unless the feature
  is explicitly event-time incremental and records its own cutoff.
* Cross-asset joins are as-of joins: for each asset select the latest admissible
  observation, retain its `age_ns`, and apply an explicit maximum-age policy.
  Missing/stale context is represented, never forward-filled from the future.
* Calendars, symbol mappings, contracts, corporate actions, funding/basis and
  external releases are versioned inputs. Revisions/late corrections create new
  versions; they never overwrite the version visible at earlier `D`.
* Normalizers/scalers are fitted only on training observations whose labels and
  raw inputs satisfy their split embargo; serialize `fit_window`, `fit_as_of`, and
  parameter hash. Cross-sectional statistics use only active PIT constituents.

## 4. State quality and nulls

`StateQuality ∈ {COMPLETE, DEGRADED, INVALID}`. `DEGRADED` is allowed only where
the consuming Expert declares that missing/stale field policy; `INVALID` cannot
produce an evaluation. Null is not zero: `null_reason ∈ {NOT_PUBLISHED,
NOT_YET_AVAILABLE, NOT_APPLICABLE, SOURCE_GAP, STALE, REJECTED}`.

## 5. Leakage prevention gates

1. Build states with an as-of query parameter; prohibit “latest” reads.
2. Validate all raw and derived `max_input_available_time` values against `D`.
3. Lock source version, adjustment policy, universe membership, and feature graph
   in an `ExperimentManifest` before evaluation.
4. Split chronologically by decision/candidate interval; purge or embargo any
   train sample whose label horizon overlaps validation/test information.
5. Fit transforms, imputation, selection thresholds and labels inside each train
   fold only.  No global standardization, target encoding, or future-derived
   universe.
6. Separate decision-time facts from outcome-only columns physically and through
   access controls (`decision_*` vs `outcome_*` schemas).

## 6. Cheap executable tests

* **Future rejection:** insert a feature input with `available_time=D+1ns`; state
  construction must fail.
* **Bar-close test:** at `D < bar_available_time`, requesting the bar close/high
  must return `NOT_YET_AVAILABLE`.
* **Revision replay:** revise a filing/release after `D`; an as-of rebuild at `D`
  must produce the prior state hash, while a later rebuild may differ.
* **Join test:** a cross-asset quote after `D` cannot join; a stale quote must
  expose its age/quality flag.
* **Fold test:** mutate a validation row and confirm fitted training scaler and
  all training feature values are unchanged.

## 7. Evidence and citations

* **LITERATURE_SUPPORTED:** financial datasets embed timestamp, adjustment,
  identifier and revision definitions; point-in-time violations and survivorship
  are material research risks: [ML for Trading, Financial Data Universe](https://ml4trading.io/third-edition/chapters/02_financial_data_universe).
* **LITERATURE_SUPPORTED:** a restated financial figure must not be backfilled to
  the original reporting date; bitemporal/as-of storage is the appropriate
  protection: [ML for Trading, Fundamental and Alternative Data](https://ml4trading.io/third-edition/chapters/04_fundamental_alternative_data).
* **DESIGN_INFERENCE:** the named clocks, strict unknown-availability handling,
  and quality enum are V8 choices that make those requirements testable.
