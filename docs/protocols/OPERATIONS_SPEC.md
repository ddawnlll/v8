# V8 Operations Specification

**Status:** PROVISIONAL_DECISION. This spec governs the operational lifecycle
of research artifacts: how data quality is monitored, how runs are
observable, how reproducibility is enforced, and how the system fails closed.

## 1. Artifact status lifecycle

Every strategy artifact (expert, scorer, dataset, simulator configuration)
carries an explicit status:

`research -> shadow -> paper -> live`

with promotion gates, not prose:

- **research:** preregistered hypothesis + frozen spec + canonical
  simulation; promotion to shadow requires the registry experiment's gate.
- **shadow:** runs on the current tape alongside the baseline, producing
  comparison artifacts; no allocation consequence.
- **paper:** shadow + simulated fills through the canonical execution policy
  with full cost model; a paper promotion review requires the backtest
  config, shadow results, and risk limits as artifacts.
- **live:** unreachable under the current charter. The project evidence audit
  records `simulation_authority_certification_v1.json` as `FAIL` with
  `autopilot_permission: BLOCKED`; live status may not be claimed until that
  authority is independently renewed (`V8_CONSTITUTION` rule 12).

Shadow and paper must run the **same code path** as each other, with only the
fill source differing — a single strategy implementation, not three
codebases. Rollback is a first-class operation: revert to the previous
version, cancel new signals, and record a documented kill-switch path per
artifact.

## 2. Data-quality monitoring

- **Schema contract per ingest:** every ingest validates column set, dtypes,
  nullability, and exchange-sequence continuity against the versioned schema
  (`FEED_INGESTION_SPEC` §2). A schema drift fails the ingest.
- **Staleness and gap detection:** alert on micro-gaps and out-of-sequence
  messages using venue sequence numbers and message counts — not only on full
  outages.
- **Backfill audits:** backfills are idempotent reprocesses
  (`FEED_INGESTION_SPEC` §5); every backfill is followed by an audit
  comparing row counts, payload hashes, and summary stats against the
  baseline.
- **Feed reconciliation:** redundant feeds (live stream vs REST pagination,
  or a second provider) are compared continuously; divergence beyond
  declared tolerance is an incident.

## 3. Observability

- **Structured JSON logs** with `experiment_id` / `run_id` in every line;
  unified structured logging for logs, metrics, and traces is sufficient at
  research scale.
- **Counters and gauges** for pipeline runs, data latency, backtest job
  duration, and per-artifact error rates; alert only on the critical ones
  (Prometheus + Grafana, or a lighter single-node equivalent — do not
  over-invest).
- **Experiment tracking:** every backtest logs full config, metrics, and
  teardown artifacts so runs are comparable side by side (a local MLflow
  server or the flat registry in this corpus suffices).

## 4. Reproducibility and CI

- **Hash-binding:** pin data snapshots, lockfiles, and code commit in
  `ExperimentManifest`; store artifact hashes in the experiment registry so
  any result traces to exact inputs (`PERSISTENCE_REPLAY_SPEC` §4).
- **Point-in-time data:** only PIT, survivorship-free universes enter
  experiments (`DATASET_SPEC` §3); current-constituent universes invert
  results.
- **CI for research code:** lint, typecheck, and tests on every change, plus
  a golden-backtest regression check so refactors cannot silently change
  results.

## 5. Fail-closed behavior and incident handling

- **Fail closed, not open:** if a check cannot evaluate (missing quote,
  unreachable store, unknown availability), the run rejects rather than
  passes. A missing authority receipt blocks an economic verdict
  (`V8_CONSTITUTION` rules 8–9).
- **Kill switches are independent** of the systems they protect, and failure
  paths are tested — a gate never tripped in anger fails when needed.
- **Incident procedure:** predefined owner, rollback decision, and postmortem
  per incident class. Data incidents that could invalidate in-flight research
  are flagged to the affected experiments immediately.

## 6. Cheap executable tests

1. Kill the feed connection; the ingest process must emit a staleness alert
   within the declared budget.
2. Change a schema column; the next ingest must fail with the schema error.
3. Run the same backfill twice; audits must report identical counts and
   hashes.
4. Refactor a feature fold; the golden-backtest regression must detect any
   output change.
5. Make the store unreachable mid-run; the lab run must abort with a
   fail-closed verdict, not a partial economic result.

## 7. Evidence and citations

- **LITERATURE_SUPPORTED:** promotion lifecycle and rollback discipline for
  trading strategies: [Anatomy of an HFT strategy lifecycle (QuantInsider)](https://www.quantinsider.io/blogs/anatomy-of-an-HFT-strategy-lifecycle).
- **LITERATURE_SUPPORTED:** point-in-time, survivorship-free data as the
  primary backtest correctness gate: [QuantConnect research guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide).
- **LITERATURE_SUPPORTED:** idempotent backfills with post-backfill audits:
  [ML4Devs — Backfilling Data](https://www.ml4devs.com/what-is/backfilling-data).
- **LITERATURE_SUPPORTED:** automated trading risk controls, kill switches on
  independent infrastructure, and tested failure paths: [FIA, Automated Trading Risk Controls](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf).
- **DESIGN_INFERENCE:** the status gates, alert set, and fail-closed rules
  are V8 choices; they do not constitute a claim of readiness to trade.
