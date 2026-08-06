"""Declared per-Expert MarketState serving (D-053).

An Expert declares the groups, intervals and depth it needs; the runtime serves
exactly that from ONE canonical state per decision clock. These tests pin the
three properties that make the arrangement safe rather than merely convenient:
the projection withholds only undeclared features, it does NOT mint a second
state identity, and a declaration the tape cannot serve is refused in words
instead of silently degraded.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from v8.experts.base import Expert
from v8.interval import INTERVAL_NS, bars_per
from v8.lab import Lab
from v8.marketstate import (build_multi_state, build_state, feature_interval,
                            group_closure, project_state)
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape

UNIVERSE = ('SOLUSDT',)
KNOWN = frozenset(INTERVAL_NS)


def _state(n_bars: int = 200):
    rows = [r for r in make_synthetic_tape(seed=7, n_bars=n_bars)
            if r.channel == 'kline' and r.payload.get('closed') is True]
    return rows, build_state(rows, rows[-1].available_time, UNIVERSE)


# --- declaration -----------------------------------------------------------


def test_default_declaration_is_base_interval_only():
    """Every pre-D-053 Expert declared nothing, so it must keep seeing exactly
    the base interval and the historic 32-bar depth."""
    ex = Expert()
    assert ex.intervals == ()
    assert ex.declared_intervals('1h') == ('1h',)
    assert ex.declared_depth('1h') == 32
    assert 'intervals' not in ex.registry_entry()
    assert 'depth' not in ex.registry_entry()


def test_declared_intervals_are_base_first_and_deduplicated():
    class E(Expert):
        intervals = ('4h', '1h', '4h')
    assert E().declared_intervals('1h') == ('1h', '4h')


def test_depth_may_differ_per_interval():
    class E(Expert):
        intervals = ('4h',)
        depth = {'1h': 120, '4h': 60}
    ex = E()
    assert ex.declared_depth('1h') == 120
    assert ex.declared_depth('4h') == 60
    assert ex.registry_entry()['intervals'] == ['4h']
    assert ex.registry_entry()['depth'] == {'1h': 120, '4h': 60}


# --- projection ------------------------------------------------------------


def test_group_closure_reaches_raw():
    """No registered Expert declares `raw`, yet all of them read `close`. The
    closure is what keeps the declaration honest without making every Expert
    restate the base layer."""
    assert 'raw' in group_closure(('history',))
    assert group_closure(('volatility',)) == frozenset({'volatility', 'raw'})
    assert group_closure(()) == frozenset()


def test_projection_withholds_only_undeclared_groups():
    _, st = _state()

    class E(Expert):
        requires = ('trend', 'history')
    allowed = group_closure(E.requires)
    view = project_state(st, groups=E.requires, intervals=('1h',),
                         base_interval='1h', known_intervals=KNOWN)
    assert view.features                       # not empty
    assert len(view.features) < len(st.features)
    assert all(v.group in allowed for v in view.features.values())
    # Everything withheld is genuinely outside the declaration.
    for k in set(st.features) - set(view.features):
        assert st.features[k].group not in allowed


def test_projection_does_not_mint_a_second_state_identity():
    """The projection is a VIEW. If it minted its own state_id the audit anchor
    would fork per Expert and two Experts' decisions at one clock would no
    longer be traceable to the same world."""
    _, st = _state()
    view = project_state(st, groups=('trend',), intervals=('1h',),
                         base_interval='1h', known_intervals=KNOWN)
    assert view.state_id == st.state_id
    assert view.lineage_hash == st.lineage_hash
    assert view.as_of == st.as_of
    assert view.universe == st.universe


def test_undeclared_feature_access_raises_rather_than_reads_stale():
    _, st = _state()
    view = project_state(st, groups=('trend',), intervals=('1h',),
                         base_interval='1h', known_intervals=KNOWN)
    assert 'SOLUSDT.ema_fast' in view.features
    with pytest.raises(KeyError):
        view.features['SOLUSDT.rsi14']         # oscillator was never declared


# --- interval namespacing --------------------------------------------------


def test_base_interval_features_stay_unprefixed():
    """Backward compatibility is the whole reason the base interval keeps bare
    keys: every existing Expert and test reads `{sym}.{feature}`."""
    assert feature_interval('SOLUSDT.atr', '1h', KNOWN) == '1h'
    assert feature_interval('SOLUSDT.4h.atr', '1h', KNOWN) == '4h'
    # A feature whose name merely looks like an interval is not one.
    assert feature_interval('SOLUSDT.close', '1h', KNOWN) == '1h'


def test_multi_state_adds_namespaced_higher_interval_features():
    # 202 bars = 50 complete 4h buckets plus a 2-bar partial, so the newest 4h
    # close is deliberately NOT the newest 1h close.
    rows, base = _state(202)
    multi = build_multi_state(rows, rows[-1].available_time, UNIVERSE,
                              base_interval='1h', intervals=('4h',))
    assert set(base.features) < set(multi.features)          # strict superset
    ns = [k for k in multi.features if k.startswith('SOLUSDT.4h.')]
    assert ns, 'no 4h features emitted'
    # The 4h close comes from the last COMPLETED bucket; the trailing partial
    # bucket is not a bar, so it cannot equal the newest 1h close here.
    assert (multi.features['SOLUSDT.4h.close'].value
            == rows[199].payload['close'])
    assert (multi.features['SOLUSDT.4h.close'].value
            != base.features['SOLUSDT.close'].value)
    assert multi.provenance['intervals'] == ['1h', '4h']


def test_multi_state_is_identical_to_base_when_nothing_is_declared():
    """A run whose Experts declare no extra interval must produce byte-identical
    evidence to the pre-D-053 runtime."""
    rows, base = _state(120)
    multi = build_multi_state(rows, rows[-1].available_time, UNIVERSE,
                              base_interval='1h', intervals=())
    assert multi.state_id == base.state_id
    assert multi.lineage_hash == base.lineage_hash


def test_higher_interval_features_never_precede_their_availability():
    """A 4h bar spanning 08:00-12:00 must not exist in the 09:00 state."""
    rows, _ = _state(200)
    n = bars_per('1h', '4h')
    # Clock sits one bar INTO a fresh bucket: the bucket cannot be readable yet.
    mid = rows[n * 3]                       # first bar of the 4th bucket
    st = build_multi_state([r for r in rows if r.available_time <= mid.available_time],
                           mid.available_time, UNIVERSE,
                           base_interval='1h', intervals=('4h',))
    for k, v in st.features.items():
        if '.4h.' in k:
            assert v.max_input_available_time <= mid.available_time


# --- declared depth --------------------------------------------------------


def test_history_depth_is_a_default_not_a_ceiling():
    """O-020 pinned `history` at 32 bars globally, which is why ichimoku (78
    bars) has 3 of 4 variants unevaluated. Depth is now requested."""
    rows, _ = _state(300)
    deep = build_state(rows, rows[-1].available_time, UNIVERSE, 'v1', 120)
    shallow = build_state(rows, rows[-1].available_time, UNIVERSE, 'v1', 32)
    assert len(deep.features['SOLUSDT.history'].value) == 120
    assert len(shallow.features['SOLUSDT.history'].value) == 32
    # The deep window is a strict extension: its newest bars are the shallow one.
    assert deep.features['SOLUSDT.history'].value[-32:] == \
        shallow.features['SOLUSDT.history'].value


def test_projection_truncates_history_to_the_experts_own_depth():
    """The canonical state holds max(declared) so one deep Expert does not make
    everyone recompute — and each view is cut back so it also cannot WIDEN a
    shallower Expert's window."""
    rows, _ = _state(300)
    canonical = build_state(rows, rows[-1].available_time, UNIVERSE, 'v1', 120)

    class Shallow(Expert):
        requires = ('history',)
        depth = 40
    view = project_state(canonical, groups=Shallow.requires, intervals=('1h',),
                         base_interval='1h', known_intervals=KNOWN,
                         depths={'1h': Shallow().declared_depth('1h')})
    assert len(view.features['SOLUSDT.history'].value) == 40
    assert view.features['SOLUSDT.history'].value == \
        canonical.features['SOLUSDT.history'].value[-40:]


def test_projection_never_pads_a_short_history():
    """Asking for more than the tape holds yields what exists, not a padded
    window — the feasibility gate is what refuses the declaration, and it must
    not be silently satisfied here instead."""
    rows, _ = _state(60)
    canonical = build_state(rows, rows[-1].available_time, UNIVERSE, 'v1', 120)
    view = project_state(canonical, groups=('history',), intervals=('1h',),
                         base_interval='1h', known_intervals=KNOWN,
                         depths={'1h': 500})
    assert len(view.features['SOLUSDT.history'].value) <= 60


# --- feasibility gate ------------------------------------------------------


def test_gate_admits_a_servable_declaration():
    class E(Expert):
        intervals = ('4h',)
        depth = 30
    assert Lab.feasibility(E(), '1h', 8760) == ('EVALUABLE', '')


def test_gate_refuses_a_finer_interval_than_the_tape():
    """Aggregation is up-only: a 1h tape can never serve 15m, and saying so is
    the difference between 'no edge' and 'never measured'."""
    class E(Expert):
        intervals = ('15m',)
    verdict, reason = Lab.feasibility(E(), '1h', 8760)
    assert verdict == 'NOT_EVALUABLE'
    assert 'up-only' in reason and '15m' in reason


def test_gate_refuses_a_depth_the_tape_cannot_cover():
    """1d x 400 bars is 400 days; a 12-month tape cannot serve it, and a
    silently short window is what produced the O-020 proxy families."""
    class E(Expert):
        intervals = ('1d',)
        depth = {'1h': 32, '1d': 400}
    verdict, reason = Lab.feasibility(E(), '1h', 8760)
    assert verdict == 'NOT_EVALUABLE'
    assert '9600 base bars' in reason and '8760' in reason


def test_gate_reason_names_the_interval_and_the_shortfall():
    class E(Expert):
        depth = 99999
    verdict, reason = Lab.feasibility(E(), '1h', 100)
    assert verdict == 'NOT_EVALUABLE'
    assert '1h' in reason and '100' in reason


# --- end to end ------------------------------------------------------------


def test_lab_run_serves_a_declared_higher_interval():
    """The whole path: declaration -> union -> aggregation -> namespaced state
    -> projection. The Expert sees its 4h features and nothing it did not ask
    for, and the run still produces one state per clock."""
    seen: dict[str, object] = {}

    class Probe(Expert):
        expert_id = 'probe_4h'
        requires = ('volatility', 'history')
        intervals = ('4h',)

        def evaluate(self, state):
            from v8.schema import ExpertEvaluation
            # Capture the LATEST view: early in the tape no 4h bucket has
            # completed yet, which is itself the point-in-time rule working.
            seen['keys'] = sorted(state.features)
            seen['state_id'] = state.state_id
            return ExpertEvaluation(
                expert_id=self.expert_id, version=self.version,
                state_id=state.state_id, applicability='APPLICABLE',
                decision='NO_SETUP', knowledge_time=state.as_of)

    lab = Lab(Path(tempfile.mkdtemp()), universe=UNIVERSE)
    lab.ingest(make_synthetic_tape(seed=7, n_bars=200))
    rows = lab.tape_log.read()
    ev = [r['event_time'] for r in rows if r.get('channel') == 'kline']
    lab.run(ExperimentManifest(
        experiment_id='d053', code_hash='', data_hash='', universe=UNIVERSE,
        start_ns=min(ev), end_ns=max(ev), interval='1h',
        authority_receipt=None), [Probe()])

    keys = seen['keys']
    assert any(k.startswith('SOLUSDT.4h.') for k in keys), '4h never served'
    assert 'SOLUSDT.atr' in keys                       # declared volatility
    assert not any('rsi' in k for k in keys)           # oscillator undeclared
    # One canonical state per clock: the Expert's view carries the ledger's id.
    assert seen['state_id'] in {r['event_id'] for r in lab.states.read()}
