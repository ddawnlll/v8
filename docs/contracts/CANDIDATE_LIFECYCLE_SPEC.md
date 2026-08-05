# V8 Candidate Episode Lifecycle

**Status:** PROVISIONAL_DECISION. A Candidate records a falsifiable trade
hypothesis; it is not an order, recommendation, or label of future profitability.

## 1. Identity and frozen birth record

`candidate_id` is a UUID. `episode_key` is deterministic and **anchored to the
setup event, never to the decision clock** (D-026):

```text
episode_key = hash(expert_id, expert_version, instrument_id, direction,
                   setup_anchor_event_id, geometry_version)
```

`setup_anchor_event_id` identifies the market event that created the setup (the
swing, the sweep, the liquidation print) — not the bar on which the Expert
happened to notice it. This is the identity primitive for *"is this the same
idea I am already holding?"*, and it is the only definition; `EXPERT_PROTOCOL`
section 2 references it rather than restating it.

Including a birth timestamp in the key is a **defect, not a variant**: the same
setup re-detected on consecutive bars would hash to a different key, so the
suppression window would never find the prior episode and deduplication would
silently never fire. A key must be stable across every decision clock on which
the same setup is observable.

A collision or a repeat inside the Expert's declared deduplication window links
to the existing episode (`SUPPRESSED_DUPLICATE`) rather than silently
disappearing. New materially distinct setup evidence — a new anchor event —
gets a new ID.

At birth, record an immutable `BirthSnapshot`: state/feature lineage, expert
version, setup evidence, proposed trigger, invalidation, expiry, risk geometry,
decision clock, and all input availability maxima. Later state may be attached as
a transition snapshot but cannot rewrite the birth record.

## 2. State machine

```text
DETECTED -> PENDING -> TRIGGERED -> ACCEPTED -> ORDER_SUBMITTED -> EXECUTED -> CLOSED
    |          |            |            |              |              |
    v          v            v            v              v              v
 REJECTED   EXPIRED     INVALIDATED   REJECTED       CANCELLED       (terminal)
    \__________\______________\____________\______________/ 
                       -> ARCHIVED
```

`DETECTED` is an expert observation, not yet a complete trade hypothesis.
`PENDING` has a complete trigger/invalidation/expiry contract. `TRIGGERED` means
the trigger predicate was observed using admissible information—not that a fill
occurred. `ACCEPTED` is a portfolio/risk admission decision. `EXECUTED` requires
at least one fill. `CLOSED` has a completed position lifecycle. `REJECTED`,
`EXPIRED`, `INVALIDATED`, `CANCELLED`, and `ARCHIVED` are terminal.

| From | Event | To | Required decision-time evidence |
|---|---|---|---|
| — | `setup_detected` | DETECTED | expert evaluation + MarketState ref |
| DETECTED | `hypothesis_completed` | PENDING | trigger, invalidation, expiry, risk |
| DETECTED/PENDING/TRIGGERED/ACCEPTED | `reject` | REJECTED | reason code + actor/version |
| PENDING | `trigger_observed` | TRIGGERED | trigger predicate + TriggerSnapshot |
| PENDING | `expiry_reached` | EXPIRED | clock and expiry rule |
| PENDING/TRIGGERED | `invalidation_observed` | INVALIDATED | predicate + snapshot |
| TRIGGERED | `risk_accept` | ACCEPTED | capacity/risk decision evidence |
| ACCEPTED | `submit_order` | ORDER_SUBMITTED | canonical order plan |
| ORDER_SUBMITTED | `fill_observed` | EXECUTED | fill ref; partial fills remain here |
| ORDER_SUBMITTED | `cancel_confirmed` | CANCELLED | venue/order event |
| EXECUTED | `position_flat` | CLOSED | position/fill/outcome refs |
| EXECUTED | `thesis_invalidated` | CLOSED | Expert `still_valid` predicate + snapshot |
| any terminal | `retain` | ARCHIVED | retention/version policy |

All other transitions fail closed. Reactivation is forbidden: after terminal
state create a new episode with `parent_candidate_id` and a stated new setup
fingerprint.

**Post-entry thesis invalidation (D-029).** Pre-entry invalidation ends a
`PENDING`/`TRIGGERED` Candidate. After a fill, the Expert's thesis does not stop
being falsifiable: the setup that justified holding can disappear while price is
still far from the stop. The Expert therefore keeps a deterministic
`still_valid(state, draft)` predicate, evaluated on closed bars exactly like
every pre-entry rule, and a failing predicate closes the position at that bar's
close with `reason_code = thesis_invalidated` and endpoint
`THESIS_INVALIDATED`.

This is a distinct exit cause, never merged into `STOP`: a stop says the market
moved against the position, a dead thesis says the reason to hold it no longer
exists. Merging them would make the competing-risk decomposition in section 4
unable to separate "wrong about direction" from "right to leave early". The
predicate is part of the Expert's frozen specification and adds no learned
component (`V8_CONSTITUTION` rule 14); an Expert that declares none defaults to
`True` and is governed by price alone. Where the predicate's inputs are
unobservable it fails **open** — an unreadable thesis is not a dead thesis, and
the price barriers still govern. An Expert may own many candidates, subject to
its documented concurrency and dedup policies.

## 3. Lifecycle truth and event sourcing

`CandidateTransition` is append-only. Its immutable order is `(knowledge_time,
transition_sequence)`, not ingestion order. It contains `event_time`,
`available_time`, `knowledge_time`, `from_state`, `to_state`, `reason_code`,
`actor_type`, `actor_version`, `snapshot_ref`, `evidence_refs`, and `event_hash`.
Current state is a materialized projection; replay of the transition log must
reproduce it. Corrections append a superseding event, retaining the original.

This is **LITERATURE_SUPPORTED** as an audit/rebuild pattern: event sourcing stores
state changes as events and permits reconstruction/temporal queries
([Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)).
The exact state names and no-reactivation rule are **DESIGN_INFERENCE**.

## 4. Labels, counterfactuals, and censoring

Transition outcome is not candidate quality. Preserve separate fields:

* `observed_execution_outcome`: only orders/fills actually sent.
* `counterfactual_outcome`: deterministic simulator result under a named,
  versioned execution policy; never an observed fill.
* `label_status`: `MATURE`, `RIGHT_CENSORED`, `INVALIDATED`, `EXPIRED`,
  `NOT_EXECUTED`, or `UNAVAILABLE`.

Expiry/invalidations are lifecycle facts, not automatic negative labels. A
candidate is right-censored if its predeclared label horizon has not completed or
the required market data is unavailable. Competing endpoints (target, stop,
expiry, forced exit) must be represented as distinct causes, with same-bar ties
resolved by the predeclared simulator policy—not hindsight. This follows the
standard competing-risk convention that follow-up can end without the endpoint
and event type is distinct ([R survival competing-risk vignette](https://cran.r-project.org/web/packages/survival/vignettes/compete.pdf)).

## 5. Cheap tests

* Replay a shuffled-ingestion log sorted by `(knowledge_time, sequence)` and
  assert identical state/hash.
* Attempt `PENDING -> EXECUTED`, `CLOSED -> PENDING`, and duplicate transition;
  each must fail.
* Trigger and invalidate at the same clock: apply declared precedence and retain
  both source facts; do not choose from later price path.
* Create a second equal `episode_key` within suppression window: ensure an
  explicit suppression record, not a dropped row.
* **Key stability (D-026):** observe one unchanged setup on two consecutive
  decision clocks; both evaluations must produce the *same* `episode_key`, and
  the second must be recorded `SUPPRESSED_DUPLICATE`. A key that varies with
  the decision clock fails this test and disables deduplication entirely.
* Delete post-horizon data: label changes to `RIGHT_CENSORED`, not loss.

## 6. Acceptance, capacity, heat and exposure conflict

`ACCEPTED` is a portfolio/risk admission decision. Research attribution and
portfolio execution are **two separate paths**:

- **Attribution (counterfactual):** every Candidate — including rejected,
  expired, and invalidated ones — is simulated through the canonical policy
  and keeps a `CounterfactualOutcome` (`label_status = NOT_EXECUTED` for
  rejected candidates). This population is the material for selection-bias
  diagnostics (`OPEN_DECISIONS` O-014) and it is not interchangeable with the
  traded population: when the two diverge, or when too few Candidates survive
  admission, the attribution validity gate blocks the economic verdict
  (`HYPOTHESIS_LAB_PROTOCOL`, D-027).
- **Execution (stepped ledger):** only accepted Candidates become positions,
  and a position **lives across decision clocks** — it is advanced one bar at
  a time by the canonical simulator until TARGET/STOP/EXPIRY. The entry bar
  is never inspected for exits. Concurrent positions are therefore a real,
  measurable set at every decision clock; without this, exposure, portfolio
  heat, and post-entry management are not measurable at all.

Baseline admission policy (deterministic; `LEARNING_PROTOCOL` section 4 — risk
preferences are hard constraints, never reward penalties):

1. **One active exposure per (instrument, direction).** A conflicting
   Candidate is rejected with `reason_code = CAPACITY_REJECTED`,
   `sub_reason = EXISTING_EXPOSURE_CONFLICT`, and keeps its counterfactual
   outcome. The purpose is **attribution** — one position, one owning Expert,
   so realized PnL is never split across hypotheses — not a risk ceiling.
   Since rule 14 stopped capping the Expert count (D-043), this rule and the
   heat cap below are what actually bound portfolio scale: adding Experts
   without revisiting them changes which hypotheses are *measured*, not which
   positions are *held*. The contested slot goes to the lexicographically
   first `expert_id` (`RUNTIME_SCHEDULER_SPEC` §5); replacing that with a
   ranking is gated by O-006 / O-012.
2. **Portfolio heat cap (D-023).** Heat is the sum of per-position stop risk
   in R (with fixed 1R geometry this equals the number of open positions).
   Correlated clusters are a **fixed instrument list** — no rolling
   estimation, because estimation error is what kills allocation models
   (DeMiguel et al., 2009). A Candidate that breaches the total or cluster
   cap is rejected (`CAPACITY_REJECTED`,
   `sub_reason = PORTFOLIO_HEAT_EXCEEDED`), **never downsized**: downsizing
   would silently enter the deferred ranker gate
   (`OPEN_DECISIONS` O-006/O-012).
3. **Mechanical tradability mask (D-024).** Deterministic data-integrity
   vetoes — funding settlement windows, entry-bar intrabar range beyond the
   declared `max_bar_range_frac` (detail `BAR_RANGE`; this is `(high-low)/close`
   and never a bid-ask spread, which the depth-free tape cannot express),
   `StateQuality = DEGRADED` — are a data-plane concern
   (`FEED_INGESTION_SPEC`), not a regime filter. They add no degrees of
   freedom and are a deterministic-baseline candidate; learned regime labels
   are a separate, router-gated question (`O-015`).

Conflicts and heat rejections are counted and reported; a ranker is
considered only when they are frequent and economically material
(`OPEN_DECISIONS` O-012).

Cheap tests for this policy:

* Two Candidates with the same `(instrument, direction)` overlap across bars:
  the second is rejected with `EXISTING_EXPOSURE_CONFLICT`; both still have
  counterfactual outcomes.
* A fourth 1R position while three are open: rejected with
  `PORTFOLIO_HEAT_EXCEEDED` (total); a third position inside one correlated
  cluster: rejected with `PORTFOLIO_HEAT_EXCEEDED` (cluster).
* A position opened at bar close is not stepped on its entry bar; replay
  reproduces identical ledger hashes.
