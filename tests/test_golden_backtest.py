"""Golden-backtest regression (OPERATIONS_SPEC section 4).

A pinned, deterministic lab run on a fixed synthetic tape. Any refactor that
changes the decision path's output — state/ledger hashes, candidate counts,
terminal distribution — fails this test: the signal that a manifest/version
bump is required rather than a silent recomputation (PERSISTENCE_REPLAY_SPEC
section 4). Updating the goldens is a deliberate, reviewed act.
"""
from __future__ import annotations

from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

UNIVERSE = ('SOLUSDT',)

# Pinned from the code as of 2026-08-01 (bugfix pass): D-026 anchored keys,
# funding settlement v4, D-024 mask defaults, decision-ledger states, birth
# snapshots, the Phase-1a counterfactual entry fix, and DEGRADED state quality
# for incomplete states. Re-pinned after the 2026-08-01 session-6 bugfix pass:
# pre-entry invalidation re-checked on the entry bar, INVALIDATED_BEFORE_TRIGGER
# relabelled NOT_EXECUTED, counterfactual thesis (still_valid) applied in
# sim.run, funding-window veto on absolute-hour boundaries, closed-only bars in
# the decision loop, and the DATASET_SPEC section 4.5 label_available_time on
# every outcome. Re-pinned after the session-6 second-level pass: failed_breakout
# uses a windowed prior-high reference for gate AND anchor (fewer spurious
# detections from old spikes -> candidate_count 24->21), terminal_distribution is
# candidate-counted, and Lab.run fails closed on a non-empty manifest pin that
# does not match the live code/tape. Re-pinned after the session-6 provenance
# fixes: the ledger hash now binds the run configuration (config_hash = sha1 of
# the manifest incl. the authority receipt), the never-entered TRIGGERED-no-entry
# epilogue records NOT_EXECUTED/INVALIDATED_BEFORE_TRIGGER instead of a
# fabricated RIGHT_CENSORED 0.0, and the state build is O(N) incremental.
# Re-pinned after the 2026-08-02 bugfix pass (provenance + null hygiene):
# the ledger hash now binds the effective RiskGate configuration
# (max_heat/max_cluster_heat/clusters — previously an unpinned run-config
# input, invisible in every hash when no cap was breached), the tape-end close
# goes through the simulator's canonical close_out(), and build_state marks
# absent (None) features DEGRADED with a null_reason instead of COMPLETE and
# derives their calculation clock from the rows actually consumed. candidate_count
# (21) and terminal_distribution are UNCHANGED — only the hash bindings moved.
# Re-pinned 2026-08-04 (D-043 follow-up, PURE RENAME): the D-024 manifest
# constant max_spread_frac became max_bar_range_frac and its veto reason
# 'SPREAD' became 'BAR_RANGE', because (high-low)/close is the entry bar's
# intrabar range and never a bid-ask spread (the tape carries no depth). The
# ledger hash moved only because config_hash = sha1(asdict(manifest)) keys on
# FIELD NAMES; no threshold, predicate, or decision changed. data_hash,
# states_hash, candidate_count (21) and terminal_distribution are all UNCHANGED
# — that invariance is the proof this was a rename and not a behavior change.
# Re-pinned 2026-08-06 (D-045, RECORD SHAPE ONLY): CounterfactualOutcome gained
# entry_price / risk_unit_price / market_move_r so the detrended null (METH-1)
# can re-center on a same-exposure passive benchmark without re-deriving the R
# denominator outside the simulator, and sim.hash() moved to canonical-sim-v6.
# Measured against the pre-change code on this exact fixture: all 21 outcomes'
# net_r are element-wise identical, and endpoint, label_status, data_hash,
# states_hash, candidate_count (21) and terminal_distribution are UNCHANGED.
# Only ledger_hash moved, because the outcome RECORD gained fields — that
# invariance is the proof this added evidence rather than changing a decision.
# Re-pinned 2026-08-06 (FEATURE-GRAPH EXTENSION FG-1..FG-7, G-01..G-43): the
# feature-group ontology gained candle_shape/oscillator/session/positioning,
# activated participation, and extended volatility/location (73 new features;
# FEATURE_GRAPH_VERSION re-computes). Every MarketState lineage_hash now binds
# the new features, so states_hash and ledger_hash moved by construction.
# Measured against the pre-change code on this exact fixture: candidate_count
# (21), terminal_distribution, and data_hash are UNCHANGED — no expert, setup,
# trigger, or price decision changed; only the state identity widened. That
# invariance is the proof this added feature evidence rather than changing a
# decision. Re-pinned 2026-08-06 (RISK-1..6, RECORD/SIZE SHAPE + MANIFEST
# FIELDS): CandidateDraft gained `size` (RM-01), OpenPosition gained `size`
# (CRIT-3: sim.hash() re-versions to canonical-sim-v7 REGARDLESS of output
# byte-identity), ExperimentManifest gained risk_per_trade/min_trades, and the
# lab wires the O-016 drawdown ladder (equity.RiskState) into the risk-gate
# hash. Measured against the pre-change code on this exact fixture: every one
# of the 21 outcomes' net_r is element-wise identical (size is
# size-independent in R; heat size*stop_r is invariant; the tape never enters
# a drawdown band), and data_hash, states_hash, candidate_count (21) and
# terminal_distribution are UNCHANGED. Only ledger_hash moved (evaluations
# records carry draft.size, outcomes carry the re-versioned simulator_hash,
# config_hash keys on the new manifest fields, risk_config binds the equity
# ladder) — the invariance is the proof this added sizing evidence rather than
# changing a decision. Re-pinned once more the same day: the sim.hash()
# version-tag docstring was extended to record the v6/v7 provenance, which
# moved _SIMULATOR_SRC_HASH (module source is bound) and every outcome's
# simulator_hash; candidate_count/terminal_distribution/data_hash/states_hash
# stayed unchanged again.
# Re-pinned 2026-08-06 (EXEC-1..6, O-013 POSITION MANAGEMENT): OpenPosition
# gained stop_level/stop_rolled/scaled_out/realized_r/remaining; step() gained
# the breakeven roll, chandelier trail, scale-out partial exit and the
# TIME_EXIT endpoint; SUPPORTED_FILL_POLICIES gained FILL_AT_LIMIT;
# sim.hash() -> canonical-sim-v8. The pilots' frozen geometry declares none of
# the management keys, so measured against the pre-change code on this exact
# fixture every executed outcome's net_r/endpoint/label is byte-identical
# (verified by diffing the two runs), and data_hash, states_hash,
# candidate_count (21) and terminal_distribution are UNCHANGED. Only
# ledger_hash moved, because every outcome record carries the re-versioned
# simulator_hash — the invariance is the proof this added management
# mechanics without changing default-geometry decisions. Re-pinned once more
# the same day: a precision edit to the scale-out realized_r accumulation
# (scaled by `remaining` — value-identical at the one-shot scale-out, but the
# module source moved, so _SIMULATOR_SRC_HASH and every outcome's
# simulator_hash moved again); data/states/candidate/terminal unchanged. Do
# not update silently.
# Re-pinned 2026-08-06 (FAILED_BREAKOUT TWO-STEP GATE, BUG-FIX): the family
# now requires the breakout leg — a prior bar must first CLOSE above its own
# prior high (Ch7.3 p228) before a close back below that level is a "failed
# breakout". The old gate fired on any close below the windowed prior high
# (a plain downtrend, never a failure). Measured against the pre-change code
# on this exact fixture: data_hash and states_hash are UNCHANGED (the tape and
# the state identity are identical — the fix moved no feature), while
# candidate_count dropped 21 -> 15 and terminal_distribution moved from
# {CLOSED:12, INVALIDATED:3, REJECTED:6} to {CLOSED:12, INVALIDATED:1,
# REJECTED:2}; the six lost candidates were spurious SHORT detections with no
# breakout premise. ledger_hash moved by construction. Re-pinned once more the
# same day (FIB_EXTENSIONS ORIGIN BASE, BUG-FIX): marketstate._fib_levels now
# projects extensions from the impulse ORIGIN per the book (Ch10.5.1/10.5.2)
# instead of the END extreme — every extension level moved one impulse-range,
# so the fib_levels feature VALUE changed and every MarketState lineage_hash
# recomputes. Measured against the pre-change code on this exact fixture:
# data_hash, candidate_count (15) and terminal_distribution are UNCHANGED
# (the golden experts TrendPullback/FailedBreakout consume no fib feature —
# no decision changed), only states_hash and ledger_hash moved. Do not update
# silently. Re-pinned for D-053 (declared multi-interval MarketState): the
# marketstate module gained `build_multi_state`, `project_state` and the group
# closure helper, which moves `_BUILDER_SRC_HASH` — a whole-FILE hash, so it
# re-versions every state's provenance `code_version` even though no formula
# and no emitted value changed. Measured against the pre-change code on this
# exact fixture: data_hash, candidate_count (15) and terminal_distribution are
# UNCHANGED, and running the same two Experts with the per-Expert projection
# disabled reproduces this run's candidates/evaluations/outcomes/states hashes
# byte-for-byte — the projection withholds only features these Experts never
# read. states_hash and ledger_hash moved by provenance alone. Re-pinned once
# more the same session (D-053 declared depth): the 32-bar `history` pin became
# HISTORY_DEPTH_DEFAULT, a default rather than a ceiling, and `build_state`
# takes the depth as a parameter. Both golden Experts declare the default 32,
# so the emitted history window is byte-identical; only `_BUILDER_SRC_HASH`
# moved again. Measured on this exact fixture: data_hash, candidate_count (15)
# and terminal_distribution UNCHANGED.
# Re-pinned for the state-builder fast path (O(N²) -> O(N x window)):
# `build_state` gained an optional `series` cache (precomputed per-symbol
# arrays) and the lab passes it; `_BUILDER_SRC_HASH` is a whole-FILE hash so
# it moves `code_version` even though every emitted value is byte-identical.
# tests/test_state_cache_identity.py proves cached == uncached on every bar;
# diffing this exact fixture against the pre-change code: candidates,
# evaluations and outcomes are byte-identical (0 differing fields), states
# differ ONLY in the provenance `code_version` field, and data_hash,
# candidate_count (15) and terminal_distribution are UNCHANGED. Re-pinned
# again in the same step when the cache gained a raw-manifest alias (kline ==
# closed on vision tapes reuses the closed-list digest) and when a review pass
# wired the funding/OI channel to the series (the FG-7 scan is no longer
# re-run per state), fixed the running-digest repeat-call idempotency, and
# made the vwap session exact for non-monotonic event_time tapes (PIT tapes
# with heterogeneous latencies fall back to the full-filter `_vwap`; monotonic
# tapes keep the O(1) precompute): every change was value-equivalent (the
# identity test pins cached == uncached), `code_version` moved each time.
# Re-pinned for the 2026-08-07 audit-fix pass (issues #62-#70): the simulator
# gained `validate_geometry` and the structural `stop_ref` stop (#63/#70), and
# the lab gained the entry trigger predicate (#62), the windowed pre-entry
# invalidation fallback (#66), the candidate-hash contention tie-break (#68)
# and the RM-11/excess-cost feasibility notes (#64/#69). data_hash,
# candidate_count (15) and terminal_distribution are UNCHANGED; only
# ledger_hash moved (simulator source hash + the lab's trigger/invalidation
# semantics on this fixture).
# Re-pinned 2026-08-09 (BPS COST FORM): the simulator gained an optional
# `round_trip_cost_bps` and every net_r site now resolves its charge through
# the single `CanonicalSimulator.cost_r(entry, unit)` method instead of reading
# the flat scalar. With `round_trip_cost_bps=None` — the default and this
# fixture's setting — cost_r returns `round_trip_cost_r` unchanged, so the
# ECONOMICS are byte-for-byte identical: verified by dumping every outcome's
# (candidate_id, horizon, endpoint, net_r, entry_price, risk_unit_price) plus
# the whole LabReport minus hashes, before and after the change, and diffing —
# the two dumps are identical. Only ledger_hash moved, because sim.hash() now
# binds the cost FORM ('flat' vs 'bps:X') and the module source moved.
# Re-pinned 2026-08-10 (MERGE RESOLUTION — PROVENANCE-ONLY DRIFT): both
# pre-merge pins were stale against the merged tree. Origin's pin (fae2a5de)
# was measured without `_evolve` (D-075) and the confluence `_geometry_version`
# band-ref exclusion (D-076); HEAD's pin (70b83058) was measured before the
# regret program's lab.py changes. Only whole-file source hashes moved (state
# provenance + simulator source); measured against this exact fixture after
# the merge: data_hash, candidate_count (15), terminal_distribution
# ({CLOSED:12, INVALIDATED:1, REJECTED:2}) and verdict NO_ECONOMIC_CLAIM are
# UNCHANGED. Do not update silently.
# Re-pinned 2026-08-14 (ISSUE #63 STRUCTURAL STOPS): failed_breakout now
# declares `stop_ref` (the frozen breakout level) with stop_r derived from it
# instead of a fixed 1.0 ATR multiple, so the fixture's executed geometry is
# wider (structural distance) and the honest heat (size*stop_r) admits fewer
# concurrent positions: REJECTED 2->8, CLOSED 12->6 on the same 15 candidates.
# data_hash, states_hash, candidate_count and the verdict are unchanged; the
# _geometry_version exclusion of stop_ref/stop_r (D-026, data-dependent) keeps
# dedup byte-identical — this is an exit-geometry change, not an episode change.
GOLDEN_LEDGER_HASH = 'cca35ceece166d7a39665a316ca3042422698700'
GOLDEN_DATA_HASH = '1c41077b2cf861f9779bb71e49bbe606015e602f'
GOLDEN_STATES_HASH = '786378b5bfa50a3c9e422ddaaa1b4b91dc1a2dae'
# 2026-08-07 perf pass (100x total-pipeline program): re-pinned after the
# decision-path fast paths landed. Every change was VALUE-EQUIVALENT —
# tests/test_state_cache_identity.py pins cached == uncached on every bar,
# and a full record diff of this fixture showed ONLY `code_version`
# (marketstate.py `_BUILDER_SRC_HASH`) and `code_hash` moved — so
# candidate_count (15), terminal_distribution, data_hash and the economic
# verdict are unchanged; only ledger_hash/states_hash re-version (the
# documented "code_version moved each time" convention above).
GOLDEN_CANDIDATE_COUNT = 15
GOLDEN_TERMINAL_DISTRIBUTION = {'REJECTED': 8, 'CLOSED': 6, 'INVALIDATED': 1}


def _manifest() -> ExperimentManifest:
    return ExperimentManifest(experiment_id='exp-golden', code_hash='',
                              data_hash='', universe=UNIVERSE, start_ns=0,
                              end_ns=0)


def test_golden_backtest_regression(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    r = lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r.ledger_hash == GOLDEN_LEDGER_HASH
    assert r.data_hash == GOLDEN_DATA_HASH
    assert lab.states.hash == GOLDEN_STATES_HASH
    assert r.candidate_count == GOLDEN_CANDIDATE_COUNT
    assert r.terminal_distribution == GOLDEN_TERMINAL_DISTRIBUTION
    assert r.verdict == 'NO_ECONOMIC_CLAIM'
    # The whole golden run is deterministic: an identical fresh run reproduces
    # every pinned hash (replay idempotency, PERSISTENCE_REPLAY_SPEC section 4).
    lab2 = Lab(tmp_path / 'run2')
    lab2.ingest(make_synthetic_tape(seed=7, n_bars=160))
    r2 = lab2.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r2.ledger_hash == GOLDEN_LEDGER_HASH
    assert r2.data_hash == GOLDEN_DATA_HASH
