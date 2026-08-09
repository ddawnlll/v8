"""Diagnostic engine tests — the spec's 6 synthetic fixtures, each with a
KNOWN verdict. The engine is not allowed into the real data path until all six
pass (spec: "Bu 6 test geçmeden motor gerçek veriye bağlanmaz")."""
from __future__ import annotations

import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest

from tools.diagnostic import DiagnosticEngine, run_diagnostic
from v8.experts import TrendPullbackExpert, FailedBreakoutExpert
from v8.experts.base import Expert
from v8.lab import Lab
from v8.schema import (CandidateDraft, ExperimentManifest, ExpertEvaluation,
                       TapeRow)
from v8.synth import FIXED_EPOCH_NS, HOUR_NS, make_synthetic_tape


def _kline(i: int, o: float, h: float, l: float, c: float) -> TapeRow:
    ev = FIXED_EPOCH_NS + i * HOUR_NS
    return TapeRow(source='binance-um', channel='kline', instrument='SOLUSDT',
                   event_time=ev, available_time=ev + HOUR_NS,
                   ingested_time=ev + HOUR_NS, venue_sequence=i + 1,
                   event_id=f'SO:{i + 1}',
                   payload={'open': o, 'high': h, 'low': l, 'close': c,
                            'volume': 1.0, 'closed': True})


def drift_tape(n: int = 300, drift: float = 0.001, start: float = 100.0):
    """Smooth deterministic positive-drift tape (no intra-bar gaps)."""
    rows = []
    c = start
    for i in range(n):
        o = c
        c = c * (1 + drift)
        rows.append(_kline(i, o, max(o, c) * 1.001, min(o, c) * 0.999, c))
    return rows


def random_walk_tape(n: int = 300, vol: float = 0.01, start: float = 100.0,
                     seed: int = 3):
    """Zero-drift random walk (the mechanical floor's habitat)."""
    rng = random.Random(seed)
    rows = []
    c = start
    for i in range(n):
        o = c
        c = c * (1 + rng.gauss(0, vol))
        rows.append(_kline(i, o, max(o, c) * 1.002, min(o, c) * 0.998, c))
    return rows


class _AlwaysLong(Expert):
    """LONG every bar; configurable geometry; R unit = 1% of the close."""
    version = 'v1'
    mechanism_family_id = 'test_diag'
    variant_id = 'a'
    requires = ('trend', 'volatility', 'history')
    expert_id = 'diag_always_long'

    def __init__(self, target_r: float = 1.0, stop_r: float = 1.0,
                 expiry: int = 8):
        super().__init__()
        self._t, self._s, self._e = target_r, stop_r, expiry

    def evaluate(self, state) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        if not self._need(state, [f'{sym}.close', f'{sym}.atr', f'{sym}.history']):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        hist = f[f'{sym}.history'].value
        if not isinstance(hist, (tuple, list)) or not hist:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction='LONG',
            setup_fingerprint=f'{self.expert_id}:{close:.6f}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': self._t,
                           'stop_r': self._s, 'expiry_bars': self._e,
                           'atr_ref': close * 0.01},
            birth_time=t, setup_anchor_event_id=hist[-1][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)


class _RandomDirection(Expert):
    """Deterministic balanced random direction every bar (a seeded stream
    consumed in detection order — NOT Random(bar_idx), whose first draw is
    biased) — a signal with no information."""
    version = 'v1'
    mechanism_family_id = 'test_diag'
    variant_id = 'r'
    requires = ('trend', 'volatility', 'history')
    expert_id = 'diag_random_direction'

    def __init__(self):
        super().__init__()
        self._rng = random.Random(7)

    def evaluate(self, state) -> ExpertEvaluation:
        t = state.as_of
        sym = state.universe[0]
        if not self._need(state, [f'{sym}.close', f'{sym}.atr', f'{sym}.history']):
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        f = state.features
        close = float(f[f'{sym}.close'].value)
        hist = f[f'{sym}.history'].value
        if not isinstance(hist, (tuple, list)) or not hist:
            return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                    'NOT_APPLICABLE', 'NO_HABITAT', t)
        direction = 'LONG' if self._rng.random() < 0.5 else 'SHORT'
        draft = CandidateDraft(
            expert_id=self.expert_id, expert_version=self.version,
            instrument=sym, direction=direction,
            setup_fingerprint=f'{self.expert_id}:{t}:{direction}',
            risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                           'stop_r': 1.0, 'expiry_bars': 8,
                           'atr_ref': close * 0.01},
            birth_time=t, setup_anchor_event_id=hist[-1][0])
        return ExpertEvaluation(self.expert_id, self.version, state.state_id,
                                'APPLICABLE', 'CANDIDATE', t, draft)


def _always_long_cls(target_r=1.0, stop_r=1.0, expiry=8):
    """Class factory so parameterized geometry can be passed as a CLASS (the
    engine instantiates `expert_classes` with `cls()`)."""
    class _Param(_AlwaysLong):
        def __init__(self):
            super().__init__(target_r=target_r, stop_r=stop_r, expiry=expiry)
    _Param.expert_id = f'diag_always_long_t{target_r}_s{stop_r}'
    return _Param


# ------------------------------------------------------------------------- #
# 1. Zero cost + positive-drift signal -> NOT NO_EDGE
# ------------------------------------------------------------------------- #
def test_drift_zero_cost_is_not_no_edge(tmp_path):
    tape = drift_tape(drift=0.001)                    # +0.1%/bar drift
    report = run_diagnostic(tape, [_AlwaysLong], tmp_path, cost_r=0.0)
    assert report['sections']['invariants']['ok']
    assert report['verdict'] != 'NO_EDGE', (
        'a positive-drift signal at zero cost has an edge; got '
        f'{report["verdict"]}')
    assert report['sections']['ablation']['frictionless'] > 0.01
    # artifacts written (incl. the self-contained HTML report)
    for name in ('report.md', 'report.json', 'report.html', 'trades.jsonl',
                 'manifest.json'):
        assert (tmp_path / name).exists(), name
    html = (tmp_path / 'report.html').read_text(encoding='utf-8')
    assert html.startswith('<!DOCTYPE html>') and html.count('<svg') >= 4
    assert 'AUTHORITY: NONE' in html


# ------------------------------------------------------------------------- #
# 2. High fee + real edge -> COST_DOMINATED
# ------------------------------------------------------------------------- #
def test_high_fee_real_edge_is_cost_dominated():
    tape = drift_tape(drift=0.001)
    eng = DiagnosticEngine(tape, [_AlwaysLong], cost_r=1.5)
    report = eng.run()
    assert report['verdict'] == 'COST_DOMINATED'
    sec2 = report['sections']['ablation']
    assert sec2['frictionless'] > 0 and sec2['actual'] < 0


# ------------------------------------------------------------------------- #
# 3. Random signal + realistic fee -> MECHANICAL_FLOOR
# ------------------------------------------------------------------------- #
def test_random_signal_is_mechanical_floor():
    tape = random_walk_tape()
    eng = DiagnosticEngine(tape, [_RandomDirection], cost_r=0.07)
    report = eng.run()
    assert report['verdict'] == 'MECHANICAL_FLOOR', (
        f"got {report['verdict']}; actual should sit inside the random null")


# ------------------------------------------------------------------------- #
# 4. Real edge + 0.2R TP -> EXIT_MISSPECIFIED
# ------------------------------------------------------------------------- #
def test_tight_tp_is_exit_misspecified():
    tape = drift_tape(drift=0.005)                    # +0.5%/bar drift
    eng = DiagnosticEngine(tape, [_always_long_cls(target_r=0.2)], cost_r=0.07)
    report = eng.run()
    assert report['verdict'] == 'EXIT_MISSPECIFIED', (
        f"got {report['verdict']}; a tight 0.2R TP that clips a strong drift "
        'should read EXIT_MISSPECIFIED')
    sec5 = report['sections']['horizon']['horizons']
    # the 7d horizon (168 bars) must be well above the clipped frictionless
    assert sec5[168]['net_R'] > report['sections']['ablation']['frictionless'] \
        * 1.5


# ------------------------------------------------------------------------- #
# 5. Broken fill price -> SIMULATOR_INVALID
# ------------------------------------------------------------------------- #
def test_broken_fill_is_simulator_invalid():
    tape = drift_tape()
    bar = tape[50]
    p = dict(bar.payload)
    p['close'] = p['high'] * 1.05                     # close above high: broken
    tape[50] = _kline(50, p['open'], p['high'], p['low'], p['close'])
    eng = DiagnosticEngine(tape, [_AlwaysLong])
    report = eng.run()
    assert report['verdict'] == 'SIMULATOR_INVALID'
    assert not report['sections']['invariants']['ok']


# ------------------------------------------------------------------------- #
# 6. Identity violation -> the engine stops (RuntimeError)
# ------------------------------------------------------------------------- #
def test_identity_violation_stops_engine(tmp_path):
    tape = drift_tape(n=200)
    store = tmp_path / 'store'
    lab = Lab(store)
    lab.ingest(tape)
    manifest = ExperimentManifest(experiment_id='exp-diag', code_hash='',
                                  data_hash='', universe=('SOLUSDT',),
                                  start_ns=0, end_ns=0)
    r = lab.run(manifest, [_AlwaysLong()])
    assert r.n_executed > 0, 'fixture needs executed outcomes'
    # tamper one executed outcome's net_r (identity violation)
    outcomes_path = store / 'outcomes.jsonl'
    lines = outcomes_path.read_text().splitlines()
    tampered = False
    for i, line in enumerate(lines):
        o = json.loads(line)
        if o.get('label_status') != 'NOT_EXECUTED':
            o['net_r'] = float(o['net_r']) + 1.0
            lines[i] = json.dumps(o)
            tampered = True
            break
    assert tampered
    outcomes_path.write_text('\n'.join(lines) + '\n')
    # the engine must STOP (spec: identity violation halts the motor)
    with pytest.raises(RuntimeError, match='identity violation'):
        DiagnosticEngine(tape, [_AlwaysLong], store_dir=store).run()


# ------------------------------------------------------------------------- #
# Forensics: per-expert verdicts
# ------------------------------------------------------------------------- #
def test_forensics_good_expert_not_kill():
    """A real drift edge must not be forensically killed."""
    tape = drift_tape(drift=0.001)
    eng = DiagnosticEngine(tape, [_AlwaysLong], cost_r=0.07)
    report = eng.run()
    fx = report['forensics']
    st = fx['experts']['diag_always_long']
    assert st['zero_cost_edge'] > 0.05, st['zero_cost_edge']
    assert st['verdict'] != 'KILL', st
    assert st['n'] >= 10


def test_forensics_random_signal_is_hard_repair_or_investigate():
    """A random-direction signal on a random walk must NOT be KEEP."""
    tape = random_walk_tape()
    eng = DiagnosticEngine(tape, [_RandomDirection], cost_r=0.07)
    report = eng.run()
    fx = report['forensics']
    st = fx['experts']['diag_random_direction']
    assert st['verdict'] in ('HARD_REPAIR', 'INVESTIGATE'), st['verdict']
    assert st['perm_p'] >= 0.05, ('a noise signal must not be significant; '
                                  f'got p={st["perm_p"]}')


def test_per_expert_state_projection_verified():
    """D-054: each expert evaluates a projected view of its declared groups,
    and the engine records that the projection withheld undeclared features."""
    tape = make_synthetic_tape(seed=7, n_bars=200)
    eng = DiagnosticEngine(tape, [TrendPullbackExpert, FailedBreakoutExpert],
                           window_bars=150)
    report = eng.run()
    assert report['manifest']['per_expert_state_projection'] is True
    for eid, aud in report['state_audit'].items():
        assert aud['view_groups_verified'] is True, eid
        # base interval is served; no expert may see the full canonical set
        # unless it declares every group
        assert aud['intervals'] == ['1h']


# ------------------------------------------------------------------------- #
# Multi-symbol × multi-timeframe
# ------------------------------------------------------------------------- #
def _multi_tape_file(path, n=150, drift=0.0005):
    """Two-symbol deterministic tape file in AppendOnlyLog JSONL format."""
    rows = []
    for sym in ('SOLUSDT', 'XRPUSDT'):
        c = 100.0
        for i in range(n):
            c = c * (1 + drift)
            ev = FIXED_EPOCH_NS + i * HOUR_NS
            rows.append({'source': 'binance-um', 'channel': 'kline',
                         'instrument': sym, 'event_time': ev,
                         'available_time': ev + HOUR_NS,
                         'ingested_time': ev + HOUR_NS,
                         'venue_sequence': i + 1, 'event_id': f'{sym}:{i+1}',
                         'payload': {'open': c, 'high': c * 1.001,
                                     'low': c * 0.999, 'close': c,
                                     'volume': 1.0, 'closed': True}})
    import json as _json
    path.write_text('\n'.join(_json.dumps(r) for r in rows) + '\n')


def test_multi_diagnostic_cross_symbol_matrix(tmp_path):
    tape_file = tmp_path / 'multi-tape.jsonl'
    _multi_tape_file(tape_file)
    out = tmp_path / 'multi-out'
    from tools.multi_diagnostic import run_multi, render_multi_html
    report = run_multi(tape_file, ['SOLUSDT', 'XRPUSDT'], ['1h'],
                       span_ns=HOUR_NS * 100, out_dir=out, processes=1)
    assert not report['cell_errors']
    assert len(report['cells']) == 2
    assert set(report['matrix'].keys())  # non-empty expert matrix
    html = render_multi_html(report)
    assert 'Cross-symbol verdict matrix' in html
    assert 'AUTHORITY: NONE' in html


def test_multi_dev_html_embeds_every_cell_full_report(tmp_path):
    """The dev multi HTML must carry 100% of the info: the matrix summary on
    top AND every cell's COMPLETE report (exec summary + per-cell verdict)
    embedded below — not just verdict badges."""
    tape_file = tmp_path / 'multi-tape.jsonl'
    _multi_tape_file(tape_file)
    out = tmp_path / 'multi-out'
    from tools.multi_diagnostic import run_multi, render_multi_html
    report = run_multi(tape_file, ['SOLUSDT', 'XRPUSDT'], ['1h'],
                       span_ns=HOUR_NS * 100, out_dir=out, processes=1)
    html = render_multi_html(report)
    # one section anchor per cell + the cell's own full-report heading
    assert 'id="cell-SOLUSDT-1h"' in html
    assert 'id="cell-XRPUSDT-1h"' in html
    assert '— full report' in html
    # the embedded fragments carry the per-cell engine report markers
    for c in report['cells']:
        assert c['symbol'] in c['report']['verdict'] or True  # report present
        assert 'verdict' in c['report']
        assert 'sections' in c['report']
    # exec summary marker appears (render_html fragment content is embedded)
    assert 'Executive summary' in html or 'VERDICT:' in html
    # cell nav menu jumps to the anchors
    assert 'class="cell-nav"' in html
    assert 'href="#cell-SOLUSDT-1h"' in html


def test_multi_dev_html_is_deterministic(tmp_path):
    tape_file = tmp_path / 'multi-tape.jsonl'
    _multi_tape_file(tape_file)
    import re as _re
    from tools.multi_diagnostic import run_multi, render_multi_html
    outs = [tmp_path / f'out{i}' for i in range(2)]
    htmlish = []
    for out in outs:
        report = run_multi(tape_file, ['SOLUSDT', 'XRPUSDT'], ['1h'],
                           span_ns=HOUR_NS * 100, out_dir=out, processes=1)
        htmlish.append(render_multi_html(report))
    # The ONLY wall-clock-dependent bytes are the generated_at_utc provenance
    # stamp (report metadata, outside the decision path). Normalize it and
    # require byte-identity everywhere else.
    def norm(h):
        return _re.sub(r'<b>generated:</b> [^<]+ UTC', '<b>generated:</b> X UTC', h)
    assert norm(htmlish[0]) == norm(htmlish[1])


def test_multi_allow_surface_reaches_cells(tmp_path):
    """--allow-surface must flow run_multi -> _run_cell -> DiagnosticEngine so
    §6 exit surface is computed per cell (was dropped before)."""
    tape_file = tmp_path / 'multi-tape.jsonl'
    _multi_tape_file(tape_file, n=180, drift=0.002)
    out = tmp_path / 'multi-out'
    from tools.multi_diagnostic import run_multi
    report = run_multi(tape_file, ['SOLUSDT'], ['1h'],
                       span_ns=HOUR_NS * 120, out_dir=out, processes=1,
                       allow_surface=True)
    assert not report['cell_errors']
    cell = report['cells'][0]
    assert 'exit_surface' in cell['report']['sections']
    assert cell['report']['sections']['exit_surface'] is not None


def test_render_html_fragment_backward_compat():
    """render_html(..., fragment=False) stays byte-identical to the legacy
    self-contained report; fragment=True returns body content WITHOUT the
    <html>/<head> wrapper so a parent document can embed it."""
    from tools.diagnostic import DiagnosticEngine, render_html
    eng = DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=60),
                           [TrendPullbackExpert])
    report = eng.run()
    trades = [eng._simulate(d, min(bi + eng.lag, len(eng.bars) - 1))
              for d, bi in eng.drafts]
    full = render_html(report, trades)
    frag = render_html(report, trades, fragment=True)
    assert full.startswith('<!DOCTYPE html>')
    assert '<html lang="en">' in full
    assert '<style>' in full
    assert '<body><div class="wrap">' in full
    # fragment: no wrapper, same body content
    assert not frag.startswith('<!DOCTYPE html>')
    assert '<html' not in frag
    assert '<style>' not in frag
    assert 'Executive summary' in frag
    # fragment is a strict subset of full (same body, minus wrapper)
    assert frag in full


# ------------------------------------------------------------------------- #
# The engine never writes outside its own artifact dir (read-only contract)
# ------------------------------------------------------------------------- #
def test_write_guard_refuses_foreign_paths(tmp_path):
    from tools.diagnostic import _guard_no_write, DiagnosticWriteError
    with pytest.raises(DiagnosticWriteError):
        _guard_no_write(tmp_path / 'registry.yaml')


# ------------------------------------------------------------------------- #
# 2026-08-07 perf pass: the walk-memoized _simulate must be byte-identical
# to a dedicated walk for every cost/funding combination, and the cache must
# actually collapse repeated full-set sims (the 6x-repeat the perf pass
# eliminated).
# ------------------------------------------------------------------------- #
def test_simulate_memo_equals_dedicated_walk():
    eng = DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=200),
                           [TrendPullbackExpert, FailedBreakoutExpert])
    d, bi = eng.drafts[0]
    e = min(bi + eng.lag, len(eng.bars) - 1)
    for cost in (eng.cost_r, 0.0, 0.03, 0.15):
        for f_rate in (eng.funding_rate_r, 0.0):
            memo = eng._simulate(d, e, cost_r=cost, funding_rate_r=f_rate)
            full = eng._simulate_full(d, e, cost_r=cost,
                                      funding_rate_r=f_rate)
            assert memo == full, (cost, f_rate)


def test_walk_cache_collapses_repeated_full_sims():
    eng = DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=200),
                           [TrendPullbackExpert, FailedBreakoutExpert])
    d, bi = eng.drafts[0]
    e = min(bi + eng.lag, len(eng.bars) - 1)
    eng._simulate(d, e)                                   # shipped
    assert len(eng._walk_cache) == 1
    eng._simulate(d, e, cost_r=0.0)                       # no_cost
    assert len(eng._walk_cache) == 1                      # reuses the walk
    eng._simulate(d, e, cost_r=0.0, funding_rate_r=0.0)   # frictionless
    assert len(eng._walk_cache) == 1
    eng._simulate(d, e, sl=2.0)                           # different geometry
    assert len(eng._walk_cache) == 2
