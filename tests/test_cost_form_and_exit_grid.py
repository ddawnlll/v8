"""Tests for the 2026-08-09 diagnostic-integrity pass.

Four defects, four contracts:

C1  COST FORM. `round_trip_cost_r` is denominated in R, so it is invariant to
    the R unit and an R-widening experiment cannot move it. The bps form must
    scale inversely with the R unit, and the flat form must stay byte-identical
    so every pre-existing ledger reproduces.

C2  EXIT GRID. The per-expert grid must be a target x horizon CROSS. A 4R
    target at the shipped 8-bar expiry is an incoherent cell (the horizon
    section shows ~4R needs ~48 bars), so a 1-D sweep makes "the exit is not
    the problem" unfalsifiable.

C3  EVIDENCE GATE. A subgroup too small to resolve the effect it claims must
    be marked UNSUPPORTED and must never label a decision-table row. Section 8
    already refuses to score such cells; the decision table contradicted it.

C4  COVERAGE. Zero-setup experts and defined-but-unregistered variants must be
    reported. Both were silently absent.
"""
from __future__ import annotations

import pytest

from v8.simulator import CanonicalSimulator

import tools.diagnostics as D


# --------------------------------------------------------------------------- #
# C1 — cost form
# --------------------------------------------------------------------------- #
def test_flat_cost_is_unchanged_by_the_bps_option():
    """The default path must return the flat constant verbatim — this is what
    keeps every existing ledger and golden reproducible."""
    sim = CanonicalSimulator(round_trip_cost_r=0.07)
    assert sim.round_trip_cost_bps is None
    for entry, unit in ((100.0, 1.0), (65000.0, 400.0), (0.5, 0.01)):
        assert sim.cost_r(entry, unit) == 0.07


def test_bps_cost_scales_inversely_with_the_r_unit():
    """The whole point of the bps form: widening R must lower cost per R.

    Under the flat form this ratio is 1.0 for every unit, which is why
    "widen the R unit to dilute the cost" is a no-op in the flat model.
    """
    sim = CanonicalSimulator(round_trip_cost_bps=5.0)
    entry = 60_000.0
    narrow = sim.cost_r(entry, unit=300.0)     # 0.5% R unit
    wide = sim.cost_r(entry, unit=600.0)       # 1.0% R unit
    assert narrow == pytest.approx(5.0 / 10_000 * 60_000 / 300)
    assert wide == pytest.approx(narrow / 2.0)
    # and the flat form does NOT do this
    flat = CanonicalSimulator(round_trip_cost_r=0.07)
    assert flat.cost_r(entry, 300.0) == flat.cost_r(entry, 600.0)


def test_bps_cost_is_entry_price_proportional():
    sim = CanonicalSimulator(round_trip_cost_bps=10.0)
    # Same R unit as a FRACTION of price -> same cost in R, whatever the price.
    assert sim.cost_r(100.0, 1.0) == pytest.approx(sim.cost_r(50_000.0, 500.0))


def test_bps_cost_rejects_a_non_positive_r_unit():
    sim = CanonicalSimulator(round_trip_cost_bps=5.0)
    with pytest.raises(ValueError, match='risk unit must be > 0'):
        sim.cost_r(100.0, 0.0)


def test_negative_bps_fails_closed():
    with pytest.raises(ValueError, match='must be >= 0'):
        CanonicalSimulator(round_trip_cost_bps=-1.0)


def test_cost_form_binds_into_the_simulator_hash():
    """A flat run and a bps run are different POLICIES; their ledgers must
    never compare equal even when a given episode prices the same."""
    flat = CanonicalSimulator(round_trip_cost_r=0.07).hash()
    bps = CanonicalSimulator(round_trip_cost_bps=5.0).hash()
    bps2 = CanonicalSimulator(round_trip_cost_bps=7.0).hash()
    assert flat != bps
    assert bps != bps2


def test_cost_r_is_the_single_resolution_point():
    """No net_r site may read `round_trip_cost_r` directly — a second copy of
    the resolution rule is exactly how the two forms drift apart."""
    import inspect
    from v8 import simulator as S
    src = inspect.getsource(S)
    body = src.split('class CanonicalSimulator', 1)[1]
    # The only permitted direct reads are the assignment, the flat-form return
    # inside cost_r itself, and the hash tuple.
    assert body.count('self.round_trip_cost_r') == 3, (
        'a net_r site is reading the flat scalar directly instead of going '
        'through cost_r(entry, unit)')


# --------------------------------------------------------------------------- #
# C2 — exit grid
# --------------------------------------------------------------------------- #
def test_exit_grid_is_a_target_by_horizon_cross():
    names = [n for n, _ in D.EXIT_VARIANTS]
    assert len(names) == len(set(names)), 'duplicate exit variant name'
    expected = len(D.EXIT_TP_GRID) * len(D.EXIT_EXPIRY_GRID)
    assert len(D.EXIT_CROSS_NAMES) == expected
    # every (tp, expiry) combination is present
    for tp in D.EXIT_TP_GRID:
        tag = 'notp' if tp is None else f'tp{tp:g}r'
        for ex in D.EXIT_EXPIRY_GRID:
            assert f'{tag}_x{ex}' in names


def test_a_4r_target_is_paired_with_a_horizon_that_can_reach_it():
    """The specific defect: `tp_4r` used to be pinned to the shipped 8-bar
    expiry, so the cell measured "target converted to expiry", not a 1:4
    geometry. At least one 4R cell must have a horizon >= 48 bars."""
    overrides = dict(D.EXIT_VARIANTS)
    four_r = {n: o for n, o in overrides.items() if n.startswith('tp4r_')}
    assert four_r, 'no 4R cells in the grid'
    assert max(o['expiry'] for o in four_r.values()) >= 48


def test_structural_probes_are_excluded_from_the_searched_cross():
    """no_sl / trail change the KIND of exit; counting them in the
    multiplicity correction would misstate the search size."""
    assert 'no_sl' not in D.EXIT_CROSS_NAMES
    assert 'trail_1atr' not in D.EXIT_CROSS_NAMES
    assert 'no_sl' in dict(D.EXIT_VARIANTS)
    assert 'trail_1atr' in dict(D.EXIT_VARIANTS)


# --------------------------------------------------------------------------- #
# C3 — evidence gate
# --------------------------------------------------------------------------- #
def test_min_n_grows_as_the_claimed_effect_shrinks():
    nets = [0.5, -0.5] * 30
    assert D._min_n_for(nets, 0.01) > D._min_n_for(nets, 0.10)
    assert D._min_n_for(nets, 0.0) == float('inf')
    assert D._min_n_for([], 0.1) == float('inf')


def _st(**over):
    """Minimal forensics dict for the observation gate."""
    base = {
        'n': 100, 'net_mean': -0.05, 'zero_cost_edge': 0.02, 'perm_p': 0.01,
        'long': {'net_mean': 0.0, 'nets': [0.0] * 50},
        'short': {'net_mean': 0.0, 'nets': [0.0] * 50},
        'exit_improvement': 0.0, 'best_exit': None, 'exit_cross': {},
        'regime_concentration': 0.0, 'regime': {},
    }
    base.update(over)
    return base


def test_underpowered_regime_claim_is_reported_but_unsupported():
    """The rsi_stoch case: a regime cell of n=19 with a huge spread cannot
    support "add a regime filter", and section 8 would refuse to score it."""
    noisy = [1.0, -1.0] * 9 + [1.0]          # n=19, sd ~ 1.0
    st = _st(regime_concentration=0.9,
             regime={'mid': {'n': 19, 'net_mean': -0.44, 'nets': noisy},
                     'low': {'n': 64, 'net_mean': 0.23, 'nets': [0.23] * 64}})
    obs = D._observations(st)
    regime = [o for o in obs if o[0] == 'Regime']
    assert regime, 'the regime observation should still be PRINTED'
    assert regime[0][2] is False, 'n=19 must not count as support'
    assert 'needs' in regime[0][1]


def test_a_well_powered_side_claim_is_supported():
    tight = [0.1] * 4000          # sd 0 -> any gap resolvable
    st = _st(long={'net_mean': -0.30, 'nets': tight},
             short={'net_mean': 0.10, 'nets': tight})
    obs = D._observations(st)
    side = [o for o in obs if o[0] == 'Long side']
    assert side and side[0][2] is True


def test_an_underpowered_side_claim_is_not_supported():
    noisy = [2.0, -2.0] * 10       # n=20, sd ~2.0
    st = _st(long={'net_mean': -0.30, 'nets': noisy},
             short={'net_mean': 0.10, 'nets': noisy})
    side = [o for o in D._observations(st) if o[0] == 'Long side']
    assert side and side[0][2] is False


def test_unsupported_observations_cannot_label_a_verdict_row():
    """The contract that matters: a row's `problem` column may only name a
    SUPPORTED observation."""
    noisy = [1.0, -1.0] * 9 + [1.0]
    st = _st(zero_cost_edge=0.03, net_mean=-0.05, regime_concentration=0.9,
             regime={'mid': {'n': 19, 'net_mean': -0.44, 'nets': noisy}})
    verdict, problem, observation = D._decide(st)
    assert verdict == 'REPAIR'
    assert problem != 'Regime', (
        'an n=19 regime cell must not become the row label')
    assert isinstance(observation, str) and observation


def test_keep_requires_enough_sample_to_resolve_its_own_edge():
    """Found on the 2026-08-09 BTCUSDT-4h run: `candlestick_reversal` reached
    KEEP on n=10 with a 100th-percentile random-null result, while its own
    observation column read "not distinguishable from sign noise". A row must
    not contradict its evidence column; under-powered goes to INVESTIGATE,
    which says "not enough yet", not "broken"."""
    st = _st(n=10, zero_cost_edge=0.38, net_mean=0.31, perm_p=0.07,
             min_n_for_edge=250.0,
             random_null={'real_edge': True, 'actual_percentile': 100.0})
    verdict, problem, obs = D._decide(st)
    assert verdict == 'INVESTIGATE'
    assert problem == 'Under-powered'
    assert 'n=10' in obs and '250' in obs

    # ...and the same expert WITH the sample does reach KEEP
    st_ok = dict(st, n=400)
    assert D._decide(st_ok)[0] == 'KEEP'


def test_structural_problem_ignores_unsupported_observations():
    noisy = [2.0, -2.0] * 10
    st = _st(long={'net_mean': -0.30, 'nets': noisy},
             short={'net_mean': 0.10, 'nets': noisy})
    assert D._structural_problem(st) is None


def test_exit_observation_requires_a_multiplicity_corrected_p():
    """Selecting the max of a 20-cell grid and quoting its naive p is not a
    p-value; the observation is only supported when Bonferroni survives."""
    st_bad = _st(exit_improvement=0.20, best_exit='tp4r_x48',
                 exit_cross={'best_cell': 'tp4r_x48', 'n_cells_searched': 20,
                             'naive_p_value': 0.04,
                             'bonferroni_p_value': 0.8})
    ex = [o for o in D._observations(st_bad) if o[0] == 'Exit']
    assert ex and ex[0][2] is False

    st_ok = dict(st_bad)
    st_ok['exit_cross'] = dict(st_bad['exit_cross'],
                               bonferroni_p_value=0.01)
    ex = [o for o in D._observations(st_ok) if o[0] == 'Exit']
    assert ex and ex[0][2] is True


def test_decision_table_column_is_an_observation_not_an_action():
    """Regression guard for the prescriptive strings the report used to emit.
    Naming the best corner of a searched space IS the selection."""
    import inspect
    src = inspect.getsource(D)
    for banned in ('Disable long', 'Disable short', 'Add regime filter',
                   'Rebuild the expert', 'Rework TP/SL',
                   'Optimize execution / widen R unit'):
        assert banned not in src, f'prescriptive action string back: {banned}'


# --------------------------------------------------------------------------- #
# C4 — coverage
# --------------------------------------------------------------------------- #
def test_coverage_reports_unregistered_variants():
    """48 Expert subclasses are defined; only the registered ones run. A row
    labelled with a family name is a statement about ONE variant."""
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=120),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    cov = eng._coverage()
    assert cov['defined_variant_classes'] > cov['registered_experts']
    assert cov['unregistered_variants'], (
        'variants defined but never run must be reported, not silently absent')
    fams = {u['module'] for u in cov['unregistered_variants']}
    assert 'donchian_breakout' in fams
    for u in cov['unregistered_variants']:
        assert u['class'] and u['variant_id'] is not None


def test_coverage_reports_zero_setup_experts():
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=120),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    eng.run()
    cov = eng._coverage()
    assert cov['evaluated_experts'] + len(cov['zero_draft_experts']) \
        == cov['registered_experts']
    # a short synthetic tape necessarily leaves some expert silent
    assert cov['zero_draft_experts'], 'zero-setup experts should be listed'


def test_coverage_is_in_the_report_and_the_html():
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=120),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    report = eng.run()
    assert 'coverage' in report
    html = D._render_coverage(report)
    assert 'Coverage' in html and 'unregistered' in html.lower()


# --------------------------------------------------------------------------- #
# determinism of the multi-cell runner
# --------------------------------------------------------------------------- #
def test_multi_cell_plan_is_deterministic_and_position_seeded():
    """`--processes 1` and `--processes 8` must agree. The old code seeded
    `seed + i` in the parallel branch and a bare `seed` in the sequential one,
    so every cell after the first disagreed between the two paths. The plan is
    now built once, before any fork, and both branches consume it."""
    kw = dict(span_ns=1, out_dir='/tmp/x', seed=7, allow_surface=False,
              cost_r=0.07, cost_bps=None)
    jobs = D.plan_cells('t.jsonl', ['BTCUSDT', 'ETHUSDT'], ['1h', '4h'], **kw)
    assert len(jobs) == 4
    # cell identity is (symbol, tf) in a fixed order
    assert [(j[0], j[1]) for j in jobs] == [
        ('BTCUSDT', '1h'), ('BTCUSDT', '4h'),
        ('ETHUSDT', '1h'), ('ETHUSDT', '4h')]
    # each cell gets its own seed, derived from position
    assert [j[4] for j in jobs] == [7, 8, 9, 10]
    # and the plan is a pure function of its arguments
    assert jobs == D.plan_cells('t.jsonl', ['BTCUSDT', 'ETHUSDT'],
                                ['1h', '4h'], **kw)


def test_multi_cell_plan_propagates_the_cost_form():
    jobs = D.plan_cells('t.jsonl', ['BTCUSDT'], ['1h'], span_ns=1,
                        out_dir='/tmp/x', seed=7, allow_surface=False,
                        cost_r=0.07, cost_bps=5.0)
    assert jobs[0][-2:] == (0.07, 5.0)
