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
# every outcome. Candidate counts and terminal distribution are unchanged; the
# outcome-label and label-availability fields moved the ledger hash. Do not
# update silently.
GOLDEN_LEDGER_HASH = '2b15e735bdc177e1e5bcfafd8373195bb9a9cf42'
GOLDEN_DATA_HASH = '1c41077b2cf861f9779bb71e49bbe606015e602f'
GOLDEN_STATES_HASH = '6cc0e25c70dcacc34e80e649f2384b0cb4ebf680'
GOLDEN_CANDIDATE_COUNT = 24
GOLDEN_TERMINAL_DISTRIBUTION = {'CLOSED': 13, 'INVALIDATED': 1, 'REJECTED': 10}


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
