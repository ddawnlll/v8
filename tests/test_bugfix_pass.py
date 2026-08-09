"""Regression tests for the 2026-08-01 session-6 bugfix pass.

Each test pins one silent bug that was confirmed by the adversarial bug hunt and
fixed in this pass: H1 (instrument mixing), H2 (counterfactual thesis), H3
(pre-entry invalidation on the entry bar), H5 (MATURE -> NOT_EXECUTED), M2
(missing-symbol quality), M5 (open klines in the decision loop), M6 (duplicate
decision clocks), M7/M1 (OHLC/NaN/volume invariants in monitoring), M8 (legacy
revision guard), M12 (unsupported interval fails closed).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from v8.experts import FailedBreakoutExpert, TrendPullbackExpert
from v8.lab import Lab
from v8.lifecycle import LEGAL, TERMINAL
from v8.marketstate import build_state
from v8.schema import CandidateDraft, ExperimentManifest, TapeRow
from v8.simulator import CanonicalSimulator
from v8.synth import make_synthetic_tape

HOUR_NS = 3_600_000_000_000


def _manifest(**kw) -> ExperimentManifest:
    d = dict(experiment_id='exp-fix', code_hash='', data_hash='',
             universe=('SOLUSDT',), start_ns=0, end_ns=0)
    d.update(kw)
    return ExperimentManifest(**d)


def _bar(i: int, close: float, low=None, high=None) -> TapeRow:
    low = low if low is not None else close - 0.05
    high = high if high is not None else close + 0.05
    return TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                   event_time=HOUR_NS * i, available_time=HOUR_NS * i,
                   ingested_time=HOUR_NS * i, venue_sequence=i + 1,
                   event_id=f'SOLUSDT:{i + 1}',
                   payload={'open': close, 'high': high, 'low': low,
                            'close': close, 'volume': 1.0, 'closed': True})


def _pullback_tape() -> list[TapeRow]:
    """Flat -> rise -> pullback: detection at bar 57, trigger at 58, entry 59."""
    rows = []
    for i in range(40):
        rows.append(_bar(i, 99.0 + i * 0.01))            # prior_low ~98.95
    for i in range(16):
        rows.append(_bar(40 + i, 99.5 + i * 0.15))
    rows.append(_bar(56, 100.9))
    rows.append(_bar(57, 100.5, low=100.2))              # pullback -> detection
    rows.append(_bar(58, 100.8, low=100.5, high=101.2))  # trigger bar
    rows.append(_bar(59, 101.0, low=100.6, high=101.4))  # entry bar
    for i in range(60, 80):
        rows.append(_bar(i, 101.0 + (i - 59) * 0.05))
    return rows


def test_h3_entry_bar_invalidation_fails_closed():
    """A trigger-condition break ON the entry bar must invalidate, not execute."""
    rows = _pullback_tape()
    p = dict(rows[59].payload)
    p['low'] = 98.0                                       # < prior_low ~98.95
    p['high'] = 102.3                                     # spread 4.3% < 5%
    rows[59] = rows[59].__class__(
        **{**rows[59].__dict__, 'payload': p})
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(rows)
    rep = lab.run(_manifest(), [TrendPullbackExpert()])
    seq = [c for c in lab.candidates.read()
           if c.get('to_state') == 'INVALIDATED']
    assert seq, 'entry-bar break must invalidate the TRIGGERED candidate'
    assert seq[0]['reason_code'] == 'invalidation_observed'
    outs = [o for o in lab.outcomes.read()
            if o['endpoint'] == 'INVALIDATED_BEFORE_TRIGGER']
    assert outs and outs[0]['label_status'] == 'NOT_EXECUTED'
    assert rep.terminal_distribution == {'INVALIDATED': 1}


def test_h2_counterfactual_applies_thesis():
    """sim.run with thesis_valid must exit THESIS_INVALIDATED when the thesis
    dies before price does (the executed path already did; the counterfactual
    population used to be held by price alone)."""
    draft = CandidateDraft(expert_id='t', expert_version='v1',
                           instrument='SOLUSDT', direction='LONG',
                           setup_fingerprint='f',
                           risk_geometry={'target_r': 1.0, 'stop_r': 1.0,
                                          'expiry_bars': 50, 'atr_ref': 1.0},
                           birth_time=0)
    quiet = [{'open': 100, 'high': 100.5, 'low': 99.5, 'close': 100}] * 60
    times = [i * HOUR_NS for i in range(60)]
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    out = sim.run(draft, quiet, times=times,
                  thesis_valid=lambda t, b: t < 4 * HOUR_NS)
    assert out.endpoint == 'THESIS_INVALIDATED'
    assert out.horizon_bars == 4
    assert out.label_status == 'MATURE'


def test_h5_invalidated_before_trigger_is_not_executed():
    """Never-triggered candidates must not be stamped MATURE in the outcome
    ledger (they would pollute the executed population)."""
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    ibt = [o for o in lab.outcomes.read()
           if o['endpoint'] == 'INVALIDATED_BEFORE_TRIGGER']
    assert ibt, 'seed-7 tape should contain a pre-trigger invalidation'
    assert all(o['label_status'] == 'NOT_EXECUTED' for o in ibt)


def test_m2_missing_symbol_degrades_state():
    """A universe symbol with zero bars must degrade the state, never stay
    COMPLETE with the symbol silently absent."""
    rows = make_synthetic_tape(seed=7, n_bars=10, symbol='SOLUSDT')
    as_of = rows[-1].available_time
    state = build_state(rows, as_of, universe=('SOLUSDT', 'BTCUSDT'))
    assert state.quality == 'DEGRADED'


def test_m5_open_kline_excluded_from_decision_loop():
    """lab.run must drive only closed klines; an open (closed:false) kline with
    garbage OHLC must not change any outcome."""
    def run(lab_: Lab, rows) -> dict:
        lab_.ingest(rows)
        lab_.run(_manifest(), [TrendPullbackExpert()])
        return {o['candidate_id']: (o['endpoint'], o['net_r'])
                for o in lab_.outcomes.read()}

    base = _pullback_tape()
    lab_a = Lab(Path(tempfile.mkdtemp()))
    r_a = run(lab_a, base)
    opened = _bar(75, 1.0, low=1.0, high=1.0)
    opened = opened.__class__(**{**opened.__dict__,
                                 'payload': dict(opened.payload, closed=False),
                                 'event_id': 'SOLUSDT:open'})
    lab_b = Lab(Path(tempfile.mkdtemp()))
    r_b = run(lab_b, base + [opened])
    assert r_a == r_b, 'an open kline must not enter the decision loop'


def test_m6_duplicate_decision_clock_fails_closed():
    """Two kline rows sharing an available_time silently truncated the state
    ledger via store dedup; now it fails closed."""
    rows = _pullback_tape()
    dup = _bar(10, 99.2)
    dup = dup.__class__(**{**dup.__dict__, 'event_id': 'SOLUSDT:10dup'})
    rows.insert(11, dup)
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(rows)
    with pytest.raises(ValueError, match='duplicate decision clocks'):
        lab.run(_manifest(), [TrendPullbackExpert()])


def test_h1_multi_instrument_tape_fails_closed():
    """A tape mixing instruments would silently step positions on the wrong
    OHLC; the bar-driven loop fails closed until O-011 passes."""
    rows = _pullback_tape() + [
        _bar(i, 50.0).__class__(source='binance-um', channel='kline',
                                instrument='BTCUSDT', event_time=HOUR_NS * i,
                                available_time=HOUR_NS * i,
                                ingested_time=HOUR_NS * i,
                                venue_sequence=i + 1,
                                event_id=f'BTCUSDT:{i + 1}',
                                payload={'open': 50.0, 'high': 50.1,
                                         'low': 49.9, 'close': 50.0,
                                         'volume': 1.0, 'closed': True})
        for i in range(40)]
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(rows)
    with pytest.raises(ValueError, match='multi-instrument'):
        lab.run(_manifest(universe=('SOLUSDT', 'BTCUSDT')),
                [TrendPullbackExpert()])


def test_m12_unsupported_interval_fails_closed():
    """_INTERVAL_NS must not silently default an unknown interval to 1h."""
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(_pullback_tape())
    with pytest.raises(ValueError, match='unsupported interval'):
        lab.run(_manifest(interval='2h'), [TrendPullbackExpert()])


def test_m9_archived_transition_is_legal():
    """CANDIDATE_LIFECYCLE_SPEC: any terminal -> ARCHIVED must be legal
    (ARCHIVED itself excluded: a self-archival self-loop is not a transition)."""
    for term in TERMINAL - {'ARCHIVED'}:
        assert (term, 'ARCHIVED') in LEGAL, f'{term} -> ARCHIVED missing'


def test_s2_every_legal_transition_forced_and_replayed():
    """State-coverage audit: every (from,to) in LEGAL must be executable,
    its illegal re-application must raise, and a re-instantiated registry
    must project the same current state (replay identity)."""
    from v8.lifecycle import CandidateRegistry
    from v8.store import AppendOnlyLog
    from collections import deque

    # BFS reachability inside LEGAL to reach each 'from' state from None.
    rev = {to: [] for _f, to in LEGAL}
    for (f, t) in LEGAL:
        rev.setdefault(t, []).append(f)
    path: dict[str, list] = {'DETECTED': [(None, 'DETECTED')]}

    def reach(state) -> list | None:
        if state in path:
            return path[state]
        seen = set()
        q = deque([('DETECTED', [(None, 'DETECTED')])])
        while q:
            cur, steps = q.popleft()
            if cur == state:
                path[state] = steps
                return steps
            if cur in seen:
                continue
            seen.add(cur)
            for (f, t) in LEGAL:
                if f == cur:
                    q.append((t, steps + [(f, t)]))
        return None

    for (f, t) in sorted(LEGAL, key=lambda k: (str(k[0]), str(k[1]))):
        steps = reach(f) if f is not None else []
        assert steps is not None, f'{f}->{t} unreachable from None'
        log = AppendOnlyLog(Path(tempfile.mkdtemp()) / 'cand.jsonl')
        reg = CandidateRegistry(log)
        cid = f'force-{f}-{t}'
        for (pf, pt) in steps:
            reg.apply(cid, pf, pt, LEGAL[(pf, pt)], 0)
        reg.apply(cid, f, t, LEGAL[(f, t)], 0)
        # Illegal re-application: already at t, repeating raises.
        with pytest.raises(Exception):
            reg.apply(cid, f, t, LEGAL[(f, t)], 0)
        # Replay identity: re-instantiate from the same log -> same state.
        reg2 = CandidateRegistry(log)
        assert reg2.current(cid) == t


def test_m8_legacy_revision_guard_fails_closed():
    """A legacy single-month source.json must still reject a different zip."""
    from tools.vision_backfill import check_archive_revision
    tmp = Path(tempfile.mkdtemp())
    (tmp / 'source.json').write_text(json.dumps(
        {'symbol': 'BTCUSDT', 'interval': '1h', 'month': '2026-04',
         'zip_sha256': 'aa' * 32, 'row_count': 0, 'tape_hash': 'x'}))
    with pytest.raises(ValueError, match='revised archive'):
        check_archive_revision(tmp, '2026-04', 'bb' * 32)


def test_m4_outcomes_carry_label_available_time():
    """DATASET_SPEC section 4.5: every outcome is knowable at a decision clock;
    the materialized view must expose it so training can refuse overlaps."""
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    outs = lab.outcomes.read()
    assert outs and all('label_available_time' in o for o in outs)
    for o in outs:
        if o['label_status'] in ('MATURE', 'NOT_EXECUTED'):
            assert o['label_available_time'] > 0, \
                f'{o["endpoint"]} outcome has no label clock'


def test_s2_lab_rejects_nan_tape_at_ingest_and_run_boundary():
    """Mutation campaign: a NaN close reaching the lab directly must fail
    closed (the monitoring tools are not in the decision path)."""
    rows = make_synthetic_tape(seed=7, n_bars=40)
    p = dict(rows[5].payload, close=float('nan'))
    rows[5] = rows[5].__class__(**{**rows[5].__dict__, 'payload': p})
    lab = Lab(Path(tempfile.mkdtemp()))
    with pytest.raises(ValueError, match='non-finite'):
        lab.ingest(rows)


def test_s2_expert_order_shuffle_identical():
    """RUNTIME_SCHEDULER_SPEC section 5: shuffling the evaluation order of
    independent experts produces identical stored events (ledger hashes)."""
    from v8.schema import sha1_hex as _sh
    rows = make_synthetic_tape(seed=7, n_bars=160)

    def run_store(exps) -> tuple:
        lab = Lab(Path(tempfile.mkdtemp()))
        lab.ingest(rows)
        lab.run(_manifest(), exps)
        return (lab.candidates.hash, lab.evaluations.hash, lab.outcomes.hash,
                lab.states.hash)

    a = run_store([TrendPullbackExpert(), FailedBreakoutExpert()])
    b = run_store([FailedBreakoutExpert(), TrendPullbackExpert()])
    assert a == b, 'expert-order shuffle must not change the ledger hashes'


def test_s2_build_state_rejects_unsorted_rows():
    """PIT ordering: unsorted rows silently select the wrong 'latest' bar;
    build_state must fail closed."""
    rows = make_synthetic_tape(seed=7, n_bars=30)
    as_of = rows[-1].available_time
    with pytest.raises(ValueError, match='sorted by available_time'):
        build_state(list(reversed(rows)), as_of, ('SOLUSDT',))


def test_s2_sim_hash_binds_module_source():
    """Hash canary 4: the simulator hash must change when the simulator's
    semantics change, not only when the version tag is bumped."""
    from v8.simulator import CanonicalSimulator, _SIMULATOR_SRC_HASH
    from v8.schema import sha1_hex as _sh
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    assert sim.hash() == _sh(('canonical-sim-v8', 'FILL_AT_BAR_CLOSE', 0.07,
                              0.0, 8, 'flat', _SIMULATOR_SRC_HASH))
    assert sim.hash() != _sh(('canonical-sim-v4', 'FILL_AT_BAR_CLOSE', 0.07,
                              0.0, 8, 'flat', 'tampered-source'))


def test_s2_report_carries_zero_trade_provenance():
    """LabReport must distinguish no-setup from invalidated from degenerate
    instead of collapsing every zero-candidate cause into count=0."""
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    rep = lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert rep.evaluation_distribution is not None
    assert 'CANDIDATE' in rep.evaluation_distribution
    assert rep.data_invalid is False


def test_s2_lab_rejects_forged_manifest_hash():
    """Hash canary: a non-empty manifest pin that does not match the live
    code/tape must fail closed at the composition root, never be reported."""
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=40))
    with pytest.raises(ValueError, match='code_hash'):
        lab.run(_manifest(code_hash='deadbeef' * 5), [TrendPullbackExpert()])
    lab2 = Lab(Path(tempfile.mkdtemp()))
    lab2.ingest(make_synthetic_tape(seed=7, n_bars=40))
    with pytest.raises(ValueError, match='data_hash'):
        lab2.run(_manifest(data_hash='cafebabe' * 5), [TrendPullbackExpert()])


def test_s2_failed_breakout_uses_frozen_prior_high_ref():
    """The SHORT thesis reference is frozen at detection: a live max drifts
    with the adverse move and the documented invalidation never fires."""
    from v8.experts import FailedBreakoutExpert
    from v8.marketstate import build_state
    from v8.schema import sha1_hex as _sh

    rows = make_synthetic_tape(seed=7, n_bars=45)
    ex = FailedBreakoutExpert()
    st = build_state([r for r in rows if r.available_time <= rows[40].available_time],
                     rows[40].available_time, ('SOLUSDT',))
    ev = ex.evaluate(st)
    if ev.draft is not None:
        assert 'prior_high_ref' in ev.draft.risk_geometry
        # episode identity must not depend on the market-moving reference
        from v8.lab import _geometry_version
        ref = ev.draft.risk_geometry['prior_high_ref']
        g1 = _geometry_version(ev.draft)
        ev.draft.risk_geometry['prior_high_ref'] = ref * 2
        assert _geometry_version(ev.draft) == g1, \
            'prior_high_ref must not join episode identity'


def test_s2_funding_window_veto_fires_when_window_ge_period():
    """window >= period must VETO (a boundary always books funding on the first
    post-entry step), not silently disable the check (1d bars + fh=8 settled 3x
    on the first step while never being vetoed)."""
    from v8.risk import tradability_mask_veto
    HOUR_NS = 3_600_000_000_000
    bar = {'high': 101.0, 'low': 99.0, 'close': 100.0}
    # 1d interval, funding_hours=8: window = 24h >= period = 8h -> always veto
    vetoed, reason = tradability_mask_veto(bar, 'COMPLETE', 0,
                                           max_bar_range_frac=0.05,
                                           funding_window_bars=1,
                                           funding_hours=8,
                                           interval_ns=24 * HOUR_NS)
    assert vetoed and reason == 'FUNDING_WINDOW'


def test_s2_report_surfaces_rejection_reasons():
    """Zero-trade provenance: rejections must not all collapse into one
    REJECTED bucket — D-024 vs risk vs cost are distinguishable."""
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    rep = lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert rep.rejection_distribution is not None
    assert rep.terminal_distribution.get('REJECTED') == \
        sum(rep.rejection_distribution.values())


def test_b1_never_entered_candidate_not_fabricated_outcome():
    """A TRIGGERED candidate with no entry bar before tape end must be a
    NOT_EXECUTED non-trade, not a fabricated RIGHT_CENSORED 0.0 with a fake
    simulator hash (DATASET_SPEC: absence is never interpreted as zero)."""
    rows = _pullback_tape()[:59]          # trigger at 58, entry 59 beyond tape
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(rows)
    lab.run(_manifest(), [TrendPullbackExpert()])
    outs = lab.outcomes.read()
    assert outs, 'TRIGGERED-no-entry must record an outcome'
    o = outs[0]
    assert o['label_status'] == 'NOT_EXECUTED'
    assert o['endpoint'] == 'INVALIDATED_BEFORE_TRIGGER'
    assert o['net_r'] == 0.0
    assert o['label_available_time'] > 0


def test_b2_config_bound_into_ledger_hash():
    """SIMULATION_TRUTH_SPEC configuration hash: two runs with DIFFERENT
    manifests must not produce byte-identical ledgers, and the manifest must be
    persisted in the store."""
    flat = make_synthetic_tape(seed=7, n_bars=40)

    def run(mk) -> tuple:
        lab = Lab(Path(tempfile.mkdtemp()))
        lab.ingest(flat)
        rep = lab.run(_manifest(**mk), [TrendPullbackExpert()])
        return (rep.ledger_hash, (lab.dir / 'manifest.json').exists())

    a = run(dict(round_trip_cost_r=0.07))
    b = run(dict(round_trip_cost_r=0.50, funding_rate_r=0.05))
    assert a[0] != b[0], 'different configs must differ in the ledger hash'
    assert a[1] and b[1], 'manifest must be persisted in the store'


def test_b3_authority_receipt_bound_into_ledger_hash():
    """Adding an authority receipt later must move the ledger hash — a report
    cannot be silently re-labelled CERTIFIED_AVAILABLE under the same hash."""
    flat = make_synthetic_tape(seed=7, n_bars=40)

    def run(receipt) -> tuple:
        lab = Lab(Path(tempfile.mkdtemp()))
        lab.ingest(flat)
        rep = lab.run(_manifest(authority_receipt=receipt),
                      [TrendPullbackExpert()])
        return (rep.ledger_hash, rep.verdict)

    no = run(None)
    yes = run('some-authority-sha')
    assert no[1] == 'NO_ECONOMIC_CLAIM' and yes[1] == 'CERTIFIED_AVAILABLE'
    assert no[0] != yes[0], 'receipt must be bound into the ledger hash'


def test_b4_replay_rejects_illegal_transition():
    """Mutation campaign: a corrupt candidates log with an illegal transition
    must fail loudly on replay, not silently project an unreachable state."""
    from v8.lifecycle import CandidateRegistry
    from v8.store import AppendOnlyLog
    log = AppendOnlyLog(Path(tempfile.mkdtemp()) / 'c.jsonl')
    log.append({'candidate_id': 'c1', 'sequence': 1,
                'from_state': 'DETECTED', 'to_state': 'EXECUTED',
                'reason_code': 'illegal', 'knowledge_time': 0,
                'event_hash': 'x', 'source': 'lifecycle', 'event_id': 'c1:1'})
    with pytest.raises(Exception, match='not legal'):
        CandidateRegistry(log)


def test_m7_monitor_rejects_bool_nan_and_ohlc_violations():
    """monitor_tape schema must reject boolean OHLC, NaN, and invariant
    violations — not certify them clean."""
    from tools.monitor_tape import validate_schema
    def row(payload):
        return {'source': 'binance-um', 'channel': 'kline',
                'instrument': 'SOLUSDT', 'event_time': 1,
                'available_time': 2, 'ingested_time': 2,
                'venue_sequence': 1, 'event_id': 'S1', 'payload': payload}
    base = {'open': 100, 'high': 101, 'low': 99, 'close': 100,
            'volume': 1.0, 'closed': True}
    assert validate_schema([row(base)]) == []
    assert any('boolean' in p for p in
               validate_schema([row(dict(base, high=True))]))
    assert any('non-finite' in p for p in
               validate_schema([row(dict(base, close=float('nan')))]))
    assert any('invariant' in p for p in
               validate_schema([row(dict(base, high=90, low=110))]))
    assert any('negative' in p for p in
               validate_schema([row(dict(base, volume=-1.0))]))


# --- 2026-08-02 bugfix pass: provenance binding + PIT + null hygiene ---------

def test_pit_tape_consumes_all_admissible_rows(tmp_path):
    """The state accumulator must include EVERY row admissible at the decision
    clock. replay_tape sorts by (event_time, available_time, venue_sequence);
    consuming in that order on a tape whose availability predates its event
    order (heterogeneous latencies) skips an admissible row or feeds build_state
    an unsorted batch. The lab consumes in available_time order (the PIT
    clock)."""
    HOUR_NS = 3_600_000_000_000
    MIN_NS = 60_000_000_000
    SEC_NS = 1_000_000_000

    def bar(event_ns: int, avail_ns: int, close: float, seq: int) -> TapeRow:
        return TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                       event_time=event_ns, available_time=avail_ns,
                       ingested_time=avail_ns, venue_sequence=seq,
                       event_id=f'S{seq}',
                       payload={'open': close, 'high': close + 1,
                                'low': close - 1, 'close': close,
                                'volume': 1.0, 'closed': True})

    # A: event 10:00, available 10:05 (5-min latency) — sorts FIRST in replay
    # order and would block an event-ordered pointer past D=10:01:30.
    a = bar(10 * HOUR_NS, 10 * HOUR_NS + 5 * MIN_NS, 100.0, 1)
    # B: event 10:01, available 10:01:30 (30-sec latency) — admissible at its
    # own decision clock but AFTER A in replay order (event/available diverge).
    b = bar(10 * HOUR_NS + MIN_NS, 10 * HOUR_NS + 90 * SEC_NS, 101.0, 2)
    lab = Lab(tmp_path)
    lab.ingest([a, b])
    lab.run(_manifest(), [TrendPullbackExpert()])
    states = lab.states.read()
    state_at_b = [s for s in states if s['as_of'] == 10 * HOUR_NS + 90 * SEC_NS]
    assert state_at_b, "a state must be recorded at bar B's decision clock"
    close = state_at_b[0]['features']['SOLUSDT.close']['value']
    assert float(close) == 101.0, \
        f'state at bar B must include the admissible bar (close 101.0), got {close}'


def test_risk_gate_config_bound_into_ledger_hash():
    """Risk admission parameters are a run-configuration input, not a code
    constant: two runs with DIFFERENT gates must never share a ledger hash,
    even when no cap is breached on a light tape."""
    from v8.risk import RiskGate
    flat = make_synthetic_tape(seed=3, n_bars=40)

    def run(gate) -> tuple:
        lab = Lab(Path(tempfile.mkdtemp()))
        lab.ingest(flat)
        rep = lab.run(_manifest(), [TrendPullbackExpert()], risk_gate=gate)
        return rep.ledger_hash, rep.risk_gate_hash

    a = run(RiskGate())
    b = run(RiskGate(max_heat=1.0))
    assert a[0] != b[0], 'different risk gates must differ in the ledger hash'
    assert a[1] != b[1], 'the report must surface the gate identity'


def test_tape_end_close_uses_simulator_authority():
    """The tape-end close of an open position is a simulator formula
    (close_out): the net derivation must live in ONE authority so the lab can
    never silently diverge from step()'s EXPIRY economics."""
    from v8.simulator import CanonicalSimulator, OpenPosition
    draft = CandidateDraft(expert_id='t', expert_version='v1',
                           instrument='SOLUSDT', direction='LONG',
                           setup_fingerprint='f',
                           risk_geometry={'target_r': 1.0, 'stop_r': 1.0,
                                          'expiry_bars': 50, 'atr_ref': 1.0},
                           birth_time=0)
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    pos = OpenPosition(candidate_id='c', draft=draft, entry_price=100.0,
                       entry_bar_index=0, entry_time_ns=0)
    assert sim.close_out(pos, 103.0) == (103.0 - 100.0) - 0.07


def test_code_hash_excludes_vendored_simtruth():
    """src/v8/simtruth/ is vendored engineering code, not the decision path:
    its bytes must not move the decision-path code hash (a vendored edit would
    otherwise invalidate every pinned manifest for a byte-identical decision
    path)."""
    from v8.lab import _code_hash
    from v8.schema import sha1_hex as _sh
    base = Path(__file__).resolve().parents[1] / 'src' / 'v8'
    all_py = {str(p.relative_to(base)): p.read_bytes().hex()
              for p in sorted(base.rglob('*.py'))}
    # Mirror _code_hash's path-parts exclusion exactly (a file like
    # simtruth_foo.py at the top level is decision path and must stay bound).
    decision_only = {k: v for k, v in all_py.items() if 'simtruth' not in k.split('/')}
    assert _code_hash() == _sh(decision_only)


def test_excess_cost_never_entered_records_invalidated_before_trigger():
    """A TRIGGERED candidate rejected for excess cost on the FINAL tape bar has
    no entry bar: it must be recorded INVALIDATED_BEFORE_TRIGGER (NOT_EXECUTED),
    never a fabricated empty-tail counterfactual (EXPIRY/0.0) — the same
    never-entered convention the epilogue uses below the cost gate."""
    rows = _pullback_tape()[:59]          # trigger at 58, entry 59 beyond tape
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(rows)
    lab.run(_manifest(round_trip_cost_r=0.11), [TrendPullbackExpert()])
    outs = lab.outcomes.read()
    assert outs, 'excess-cost never-entered must record an outcome'
    o = outs[0]
    assert o['endpoint'] == 'INVALIDATED_BEFORE_TRIGGER'
    assert o['label_status'] == 'NOT_EXECUTED'
    assert o['net_r'] == 0.0


def test_absent_feature_is_degraded_not_complete():
    """A feature with no input (prior_high on the first bar) is absent data,
    not a zero: it must be DEGRADED with an explicit null_reason and a
    calculation clock derived from the rows actually consumed (0), never
    COMPLETE (MARKET_STATE_CONTRACT section 4)."""
    rows = make_synthetic_tape(seed=7, n_bars=3)
    st = build_state([rows[0]], rows[0].available_time, ('SOLUSDT',))
    ph = st.features['SOLUSDT.prior_high']
    assert ph.value is None
    assert ph.quality == 'DEGRADED'
    assert ph.null_reason == 'NOT_YET_AVAILABLE'
    assert ph.max_input_available_time == 0
    assert st.quality == 'DEGRADED'
