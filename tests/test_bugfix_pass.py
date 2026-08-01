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
    """CANDIDATE_LIFECYCLE_SPEC: any terminal -> ARCHIVED must be legal."""
    for term in TERMINAL:
        assert (term, 'ARCHIVED') in LEGAL, f'{term} -> ARCHIVED missing'


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
