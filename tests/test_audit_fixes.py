"""Regression tests for the 2026-08-07 audit-fix pass (issues #61-#72).

Each test pins a behavior that was BROKEN before the fix and is now enforced.
The economic-measurement issues (#61, #71) are recorded in
`.audit/BASELINE.md` / the CHANGELOG rather than hard-asserted here; the
behavioral fixes below are all testable.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from v8.experts.base import Expert
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.lab import Lab
from v8.schema import (CandidateDraft, ExperimentManifest, ExpertEvaluation,
                       TapeRow, record_dict, sha1_hex)
from v8.simulator import CanonicalSimulator, OpenPosition
from v8.synth import FIXED_EPOCH_NS, HOUR_NS, make_synthetic_tape


def _draft(**geom_overrides) -> CandidateDraft:
    g = {'target_r': 2.0, 'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 10.0}
    g.update(geom_overrides)
    return CandidateDraft(expert_id='test_expert', expert_version='v1',
                          instrument='SOLUSDT', direction='LONG',
                          setup_fingerprint='f', risk_geometry=g, birth_time=0)


def _bar(high=105.0, low=95.0, open_=100.0, close=100.0) -> dict:
    return {'high': high, 'low': low, 'open': open_, 'close': close}


# ----------------------------------------------------------------------------
# #70 — risk_geometry invariants are enforced (fail closed in step/run)
# ----------------------------------------------------------------------------

def test_validate_geometry_rejects_nonpositive_target():
    sim = CanonicalSimulator()
    with pytest.raises(ValueError, match='target_r'):
        sim.run(_draft(target_r=-1.0), [_bar()])


def test_validate_geometry_rejects_zero_stop():
    sim = CanonicalSimulator()
    with pytest.raises(ValueError, match='stop_r'):
        sim.run(_draft(stop_r=0.0), [_bar()])


def test_validate_geometry_rejects_zero_expiry():
    sim = CanonicalSimulator()
    with pytest.raises(ValueError, match='expiry_bars'):
        sim.run(_draft(expiry_bars=0), [_bar()])


def test_validate_geometry_fires_on_step_too():
    sim = CanonicalSimulator()
    draft = _draft(target_r=-1.0)
    pos = OpenPosition(candidate_id='c', draft=draft, entry_price=100.0,
                       entry_bar_index=0)
    with pytest.raises(ValueError, match='target_r'):
        sim.step(pos, _bar())


# ----------------------------------------------------------------------------
# #63 — a frozen structural stop (stop_ref) is used, not an ATR multiple
# ----------------------------------------------------------------------------

def test_structural_stop_ref_is_used():
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    draft = _draft(stop_ref=95.0)          # entry 100, atr 10, stop_r 1.0
    pos = OpenPosition(candidate_id='c', draft=draft, entry_price=100.0,
                       entry_bar_index=0)
    # low 93 is below the structural stop (95) but ABOVE the ATR stop (90):
    # only a structural-stop implementation stops out on this bar.
    res = sim.step(pos, _bar(high=105.0, low=93.0))
    assert res.closed and res.endpoint == 'STOP'
    assert res.net_r is not None
    assert abs(res.net_r - (-0.5)) < 1e-9   # (95 - 100) / 10


def test_atr_stop_fallback_when_no_stop_ref():
    sim = CanonicalSimulator(round_trip_cost_r=0.0)
    draft = _draft()                        # no stop_ref -> ATR stop 90
    pos = OpenPosition(candidate_id='c', draft=draft, entry_price=100.0,
                       entry_bar_index=0)
    res = sim.step(pos, _bar(high=105.0, low=93.0))
    assert not res.closed                    # ATR stop 90 not touched


# ----------------------------------------------------------------------------
# #62 — PENDING -> TRIGGERED is gated on the frozen trigger predicate
# ----------------------------------------------------------------------------

class _TriggerGatedExpert(Expert):
    """Emits a LONG draft every bar with a trigger 50% ABOVE the close.

    The synth tape's cumulative walk over 80 bars is ~10% (σ=1.2%/bar), so a
    level 50% away can never be confirmed by a close — under issue #62 the
    candidate must stay PENDING and expire (or invalidate) instead of
    triggering unconditionally and entering.
    """
    version = 'v1'
    mechanism_family_id = 'test_trigger_gate'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')
    expert_id = 'trigger_gated'

    def evaluate(self, state) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        if not self._need(state, [f'{sym}.close', f'{sym}.atr', f'{sym}.history']):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        atr = f[f'{sym}.atr'].value
        hist = f[f'{sym}.history'].value
        if atr is None or not isinstance(hist, (tuple, list)) or not hist:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='LONG',
            setup_fingerprint=f'{self.expert_id}:{close:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr,
                           'trigger_ref': close * 1.5,
                           'trigger_side': 'CLOSE_ABOVE'},
            birth_time=t, setup_anchor_event_id=hist[-1][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)


def _manifest(**kw) -> ExperimentManifest:
    return ExperimentManifest(experiment_id='exp-audit-fix', code_hash='',
                              data_hash='', universe=('SOLUSDT',),
                              start_ns=0, end_ns=0, **kw)


def test_trigger_predicate_keeps_candidate_pending():
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=80))
    r = lab.run(_manifest(), [_TriggerGatedExpert()])
    assert r.candidate_count > 0, 'test would be vacuous'
    # The 10%-away trigger is never confirmed by a close -> nothing executes.
    assert r.n_executed == 0
    # Every candidate ends in a non-entering terminal state.
    assert set(r.terminal_distribution) <= {'EXPIRED', 'INVALIDATED', 'REJECTED'}


# ----------------------------------------------------------------------------
# #66 — the pre-entry invalidation fallback uses a WINDOWED extreme
# ----------------------------------------------------------------------------

def _kline(i: int, o: float, h: float, l: float, c: float) -> TapeRow:
    ev = FIXED_EPOCH_NS + i * HOUR_NS
    return TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                   event_time=ev, available_time=ev + HOUR_NS,
                   ingested_time=ev + HOUR_NS, venue_sequence=i + 1,
                   event_id=f'SO:{i + 1}',
                   payload={'open': o, 'high': h, 'low': l, 'close': c,
                            'volume': 1.0, 'closed': True})


class _ConditionalEmitExpert(Expert):
    """LONG draft only when the close exceeds a threshold (single emission).

    Used to isolate ONE birth bar so the invalidation behavior of that specific
    candidate is observable.
    """
    version = 'v1'
    mechanism_family_id = 'test_windowed_fallback'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')
    expert_id = 'conditional_emit'

    def __init__(self, emit_above: float):
        super().__init__()
        self._emit_above = emit_above

    def evaluate(self, state) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        if not self._need(state, [f'{sym}.close', f'{sym}.atr', f'{sym}.history']):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        if close <= self._emit_above:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_SETUP', t)
        atr = f[f'{sym}.atr'].value
        hist = f[f'{sym}.history'].value
        if atr is None or not isinstance(hist, (tuple, list)) or not hist:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='LONG',
            setup_fingerprint=f'{self.expert_id}:{close:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': atr},
            birth_time=t, setup_anchor_event_id=hist[-1][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)


def test_windowed_fallback_invalidation_not_alltime():
    """A new 32-bar extreme (but not an all-time extreme) invalidates.

    Tape: bars 0-2 print an all-time low (69); bars 3-40 rise to ~118 (so the
    32-bar window before a bar-40 birth has low ~76.5); bar 41 dips to 71 —
    below the window low, above the all-time low. The single candidate born at
    bar 40 must be invalidated before trigger. The pre-fix fallback (unbounded
    all-time low 69) would not fire and the candidate would enter.
    """
    rows = [_kline(i, o=71, h=74, l=69, c=70) for i in range(3)]
    for i in range(3, 41):
        c = 70 + (i - 3) * 1.3
        rows.append(_kline(i, o=c - 0.5, h=c + 1.0, l=c - 1.0, c=c))
    # bar 40 close = 70 + 37*1.3 = 118.1; bar 39 close = 116.8. Threshold 117
    # makes the expert emit ONLY at bar 40.
    rows.append(_kline(41, o=73, h=74, l=71, c=72))

    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(rows)
    r = lab.run(_manifest(), [_ConditionalEmitExpert(emit_above=117.0)])
    assert r.candidate_count == 1, f'expected exactly one candidate, got {r.candidate_count}'
    assert r.n_executed == 0
    outcomes = lab.outcomes.read()
    assert len(outcomes) == 1
    assert outcomes[0]['endpoint'] == 'INVALIDATED_BEFORE_TRIGGER'
    assert outcomes[0]['label_status'] == 'NOT_EXECUTED'


# ----------------------------------------------------------------------------
# #72 — the continuous synth variant does not fabricate bar-to-bar gaps
# ----------------------------------------------------------------------------

# GOLDEN_DATA_HASH of the legacy (non-continuous) tape — the continuous variant
# must not move the pinned golden data.
LEGACY_GOLDEN_DATA_HASH = '1c41077b2cf861f9779bb71e49bbe606015e602f'


def test_continuous_tape_has_no_fabricated_gaps():
    rows = make_synthetic_tape(seed=7, n_bars=500, continuous=True)
    gap = 0
    for prev, cur in zip(rows, rows[1:]):
        pc = prev.payload['close']
        H, L = cur.payload['high'], cur.payload['low']
        if max(H - L, abs(H - pc), abs(L - pc)) > H - L:
            gap += 1
    assert gap / (len(rows) - 1) < 0.10, (
        'continuous tape must not fabricate TR > (H-L) gaps')


def test_legacy_synth_tape_is_unchanged():
    rows = make_synthetic_tape(seed=7, n_bars=160)
    h = sha1_hex([record_dict(r, source=r.source) for r in rows])
    assert h == LEGACY_GOLDEN_DATA_HASH, (
        'the legacy default tape must stay byte-identical (pinned tests)')


def test_continuous_tape_atr_is_unbiased():
    """#72 — the continuous tape's shipped ATR must not be gap-distorted.

    The audit measured mean(shipped/trueATR) = 0.5923 on the legacy tape — a
    ~40% underestimate, because the fabricated bar-to-bar gaps add True Range
    that the mean(H-L) ATR feature never sees. On the continuous tape true
    range collapses to H-L (no fabricated gaps), so the shipped ATR must track
    it: the same measurement on real BTCUSDT 1h is 1.0000 (0.00% deviation).
    """
    def mean_ratio(rows: list[TapeRow], period: int = 14) -> float:
        ps = [r.payload for r in rows]
        ratios = []
        for i in range(period - 1, len(ps)):
            shipped = sum(ps[j]['high'] - ps[j]['low']
                          for j in range(i - period + 1, i + 1)) / period
            true = sum(max(ps[j]['high'] - ps[j]['low'],
                           abs(ps[j]['high'] - ps[j - 1]['close']),
                           abs(ps[j]['low'] - ps[j - 1]['close']))
                       for j in range(i - period + 1, i + 1)) / period
            ratios.append(shipped / true)
        return sum(ratios) / len(ratios)

    legacy = mean_ratio(make_synthetic_tape(seed=7, n_bars=2000))
    continuous = mean_ratio(make_synthetic_tape(seed=7, n_bars=2000,
                                                continuous=True))
    # the legacy default still exhibits the audit's ~40% underestimate —
    # this is what the continuous variant exists to avoid
    assert legacy < 0.95, f'legacy ATR distortion collapsed: {legacy:.4f}'
    assert 0.98 < continuous < 1.02, (
        f'continuous tape ATR is biased: mean(shipped/trueATR) = {continuous:.4f}')


# ----------------------------------------------------------------------------
# #64 / #69 — feasibility notes surface in the report
# ----------------------------------------------------------------------------

def test_feasibility_note_when_breakeven_exceeds_realized():
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    r = lab.run(_manifest(), [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r.economic_note is not None
    assert 'FEASIBILITY: breakeven win rate' in r.economic_note


def test_excess_cost_feasibility_note_and_rejection():
    lab = Lab(Path(tempfile.mkdtemp()))
    lab.ingest(make_synthetic_tape(seed=7, n_bars=160))
    r = lab.run(_manifest(round_trip_cost_r=0.125),
                [TrendPullbackExpert(), FailedBreakoutExpert()])
    assert r.n_executed == 0
    assert r.economic_note is not None
    assert 'excess_cost' in r.economic_note
    assert (r.rejection_distribution or {}).get('excess_cost', 0) > 0
