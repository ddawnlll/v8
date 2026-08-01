# V8 Dataset Specification

**Status:** PROVISIONAL_DECISION. The canonical store is an append-only evidence
log plus reproducible materializations. Timestamp rows alone are insufficient for
candidate decisions; candidate rows alone conceal the decision path.

## 1. Storage layers and joins

1. **Raw evidence:** vendor/venue payloads, immutable content hashes and source
   metadata. No destructive correction.
2. **Decision ledger:** MarketState, ExpertEvaluation and CandidateTransition;
   only information admissible at each `knowledge_time`.
3. **Execution ledger:** Order, Fill, PositionLifecycle; actual external events.
4. **Outcome ledger:** CounterfactualOutcome and mature labels, access-separated
   from decision features.
5. **Research materializations:** versioned candidate, transition, and timestamp
   tables generated from a pinned `ExperimentManifest`.

All tables use UUID primary keys, UTC timestamps, `schema_version`, `producer`,
`code_version`, `experiment_id` where applicable, and `recorded_at`. Time values
are never overloaded: each source fact supplies `event_time`, `available_time`,
and `ingested_time`; each decision supplies `knowledge_time`.

| Entity (PK) | Required payload / references | Ownership and leakage rule |
|---|---|---|
| `MarketState(state_id)` | as_of, universe/version, raw manifest hash, feature graph/version, quality, lineage hash | State builder; every feature carries max input availability `<= as_of`. |
| `ExpertEvaluation(evaluation_id)` | expert/version, state_id, applicability, evidence, decision, knowledge_time | Expert; cannot refer to outcome ledger. |
| `CandidateEpisode(candidate_id)` | episode key, expert/version, parent id, birth snapshot, current projection | Lifecycle service; immutable birth fields. |
| `CandidateTransition(transition_id)` | candidate id, sequence, from/to, reason, clocks, snapshot/evidence refs | Lifecycle service; append-only, legal transition only. |
| `TriggerSnapshot(snapshot_id)` | predicate version, observed inputs, state id, decision clock | Expert; input availability audited. |
| `CounterfactualOutcome(outcome_id)` | candidate id, horizon, simulator/config/hash, endpoint/censoring, result | Simulator; outcome-only access. |
| `Order(order_id)` | candidate id nullable, canonical plan/version, sent/ack times, venue | Execution service; no retrospective price edits. |
| `Fill(fill_id)` | order id, venue execution id, event/available time, price/qty/fees | Execution ingestion; dedupe venue event ID. |
| `PositionLifecycle(position_event_id)` | position id, event type, fills, state, clocks | Execution projection; reconstructed from fills/orders. |
| `ExperimentManifest(experiment_id)` | git/code hash, data snapshot hashes, universe, splits, features, labels, simulator, seeds | Experiment runner; immutable after run begins. |

Nullable values require `null_reason`; absence is never interpreted as zero or
negative outcome. A non-null foreign key must resolve to an entity/version inside
the same or explicitly named immutable data snapshot.

## 2. Dataset units

Publish three distinct model-ready units; never mix their targets implicitly.

* **Timestamp-state row:** one `(instrument, decision_clock, state_version)`;
  useful for descriptive coverage or router research, not a replacement for
  candidate-quality samples.
* **Candidate row:** one candidate at a declared observation cut (`birth`,
  `trigger`, or `accept`) with only then-admissible features and a separately
  matured outcome/censoring status. This is the default scorer unit.
* **Transition row:** one legal state change; useful for trigger/expiry and
  operations models. Its label horizon begins at that transition, not birth.

Candidate sets must be fixed before score comparison. Near misses and suppressed
duplicates are retained as `ExpertEvaluation`/transition facts, but do not become
synthetic negatives unless a protocol defines their sampling population and
weights. Do not label untraded candidates using realized fills; use a declared
counterfactual execution policy if a counterfactual target is required.

## 3. Split, label and population policy

* Construct a PIT universe including delisted/inactive instruments valid at each
  decision time. Instrument identity mappings and corporate-action adjustments
  are versioned.
* Split on time intervals, then purge/embargo any train candidate whose feature
  or label interval overlaps validation/test. Group correlated/repeated episodes
  (`episode_key`, instrument, event cluster) as prescribed by the experiment.
* Outcomes become trainable only after `label_available_time`: max(label horizon
  end, required data availability, simulator completion). A decision cannot use a
  label or calibration statistic before then.
* Weight/report overlap and dependence: candidate duration, concurrency,
  instrument/event cluster, and any uniqueness weight. Do not present IID metrics
  for overlapping episodes without qualification.
* Censored rows are excluded only with a recorded rule; survival/competing-risk
  methods may use them. `EXPIRED` and `INVALIDATED` are causes, not universally
  failures.

The PIT, revision, and survivorship requirements are **LITERATURE_SUPPORTED** by
[ML for Trading: Financial Data Universe](https://ml4trading.io/third-edition/chapters/02_financial_data_universe) and
[Fundamental and Alternative Data](https://ml4trading.io/third-edition/chapters/04_fundamental_alternative_data).
The chosen tables and physical decision/outcome separation are **DESIGN_INFERENCE**.

## 4. Cheap acceptance tests

1. Query any research row with `as_of=D`; assert every feature raw version and
   feature maximum availability is `<= D`.
2. Revise a source after D; reproduce its original state/candidate materialization
   from the old manifest hash.
3. Run a fold twice after changing test outcomes; training rows, scalers,
   thresholds and predictions must be byte-identical.
4. Insert a delisted instrument into historical universe; it must appear before
   its end time and not after it.
5. Assert every candidate target has explicit `MATURE`/censoring status and
   `label_available_time`; fail a scorer export with unlabeled outcome columns in
   its feature projection.
6. Replay raw/transition events and assert primary-key uniqueness, foreign-key
   resolution, monotonic candidate sequence, and matching materialized state.

## 5. Tape compilation and materialization

The tape is compiled once into versioned, hash-bound materialized views:

```text
market_states.parquet
candidate_birth.parquet
candidate_trigger.parquet
candidate_outcomes.parquet
execution_trajectories.parquet
```

Training and analysis read materialized views only, never the raw tape.
Recompilation happens only when the feature graph, an Expert definition, the
simulator, or the outcome definition changes — never per training run. This
separates simulation from training, keeps replay deterministic
(`PERSISTENCE_REPLAY_SPEC` section 4), and prevents the same defect from being
charged twice (`V8_CONSTITUTION` rule 17).
