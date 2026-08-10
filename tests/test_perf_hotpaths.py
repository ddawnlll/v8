"""Hot-path contracts for the 2026-08-09 performance pass.

The diagnostic was taking minutes per cell and pinning every core. Profiling a
540-bar BTCUSDT cell (cProfile, 72.6s total) found three defects. None of them
is a tuning knob — each is redundant work or a latent correctness hazard:

P1  `_median_atr` is a pure function of the frozen draft set, and was
    recomputed — scanning and SORTING every draft — once per null draft:
    202,000 times, 54.3s of 72.6s (75%), 287M dict lookups.

P2  `_walk_cache` was keyed on `id(draft)`. `id()` is unique only among LIVE
    objects, and a null draft is freed immediately after its walk, so CPython
    hands the same address to the next one. A (recycled id, same entry_idx,
    same geometry) key would then return a walk taken in the OTHER DIRECTION.
    The cache also grew without bound: 97,263 entries against 1,387 drafts.

P3  `dataclasses.replace` in `step()` re-derived the field list and getattr'd
    ~20 fields per call, up to three times per bar: 3.9M calls, 20.4s.

The tests below pin the CONTRACTS, not the timings — a wall-clock assertion
would be flaky on shared CI. The measured numbers live in the CHANGELOG.
"""
from __future__ import annotations

import dataclasses

import pytest

from v8.schema import CandidateDraft
from v8.simulator import OpenPosition, _evolve

import tools.diagnostics as D


def _draft(direction='LONG', expert_id='e1'):
    return CandidateDraft(
        expert_id=expert_id, expert_version='v1', instrument='BTCUSDT',
        direction=direction, setup_fingerprint='fp',
        risk_geometry={'entry': 'NEXT_BAR_CLOSE', 'target_r': 1.0,
                       'stop_r': 1.0, 'expiry_bars': 8, 'atr_ref': 100.0},
        birth_time=0, setup_anchor_event_id='a1')


def _pos(**over):
    base = dict(candidate_id='c1', draft=_draft(), entry_price=100.0,
                entry_bar_index=0, bars_held=3, mae_r=0.4, mfe_r=1.2,
                ambiguous_bars=1, entry_time_ns=123, settlements=2,
                funding_paid_r=0.01, size=2.0, stop_level=99.0,
                stop_rolled=True, scaled_out=False, realized_r=0.5,
                remaining=0.75)
    base.update(over)
    return OpenPosition(**base)


# --------------------------------------------------------------------------- #
# P3 — _evolve must be indistinguishable from dataclasses.replace
# --------------------------------------------------------------------------- #
def test_open_position_still_satisfies_the_evolve_preconditions():
    """_evolve bypasses __init__. That is only safe while OpenPosition has no
    validation and no __slots__ — assert it, so adding either fails loudly
    here rather than silently skipping the new behaviour in the hot path."""
    assert not hasattr(OpenPosition, '__post_init__')
    assert not hasattr(OpenPosition, '__slots__')
    assert dataclasses.is_dataclass(OpenPosition)


@pytest.mark.parametrize('changes', [
    {'bars_held': 9},
    {'mae_r': 1.5, 'mfe_r': 2.5, 'ambiguous_bars': 4},
    {'stop_level': 101.5, 'stop_rolled': False},
    {'remaining': 0.25, 'realized_r': 1.75, 'scaled_out': True},
    {'settlements': 7, 'funding_paid_r': 0.033},
    {},
])
def test_evolve_matches_dataclasses_replace(changes):
    pos = _pos()
    fast = _evolve(pos, **changes)
    slow = dataclasses.replace(pos, **changes)
    assert type(fast) is type(slow)
    for f in dataclasses.fields(OpenPosition):
        assert getattr(fast, f.name) == getattr(slow, f.name), f.name
    assert fast == slow


def test_evolve_does_not_mutate_the_source_position():
    pos = _pos()
    snapshot = {f.name: getattr(pos, f.name)
                for f in dataclasses.fields(OpenPosition)}
    _evolve(pos, bars_held=99, remaining=0.1)
    for k, v in snapshot.items():
        assert getattr(pos, k) == v, k


def test_evolve_result_is_still_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _evolve(_pos(), bars_held=1).bars_held = 5


# --------------------------------------------------------------------------- #
# P1 — the median R unit is computed once
# --------------------------------------------------------------------------- #
def test_median_atr_is_memoised():
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=90),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    eng.drafts = [(_draft(), 0), (_draft(), 1)]
    eng._median_atr_cache = None
    first = eng._median_atr()
    # a later call must NOT rescan: prove it by moving the underlying data
    eng.drafts = [(_draft(), 0)]
    eng.drafts[0][0].risk_geometry['atr_ref'] = 999.0
    assert eng._median_atr() == first


def test_median_atr_value_is_unchanged_by_the_memo():
    eng = object.__new__(D.DiagnosticEngine)
    eng._median_atr_cache = None
    eng.drafts = [(_draft(), 0), (_draft(), 1), (_draft(), 2)]
    for i, (d, _) in enumerate(eng.drafts):
        d.risk_geometry['atr_ref'] = float(10 * (i + 1))
    assert eng._median_atr() == 20.0


# --------------------------------------------------------------------------- #
# P2 — the walk cache cannot serve a foreign walk, and cannot grow on nulls
# --------------------------------------------------------------------------- #
def test_walk_cache_entries_pin_their_owning_draft():
    """The entry holds the draft, so the id in the key cannot be recycled
    while the entry lives, and a hit is verified by identity before use."""
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=120),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    eng.run()
    assert eng._walk_cache, 'real drafts should populate the cache'
    for key, entry in eng._walk_cache.items():
        assert isinstance(entry, tuple) and len(entry) == 2
        owner, _result = entry
        assert isinstance(owner, CandidateDraft)
        assert key[0] == id(owner), 'key id must match the pinned owner'


def test_null_drafts_never_enter_the_walk_cache():
    """202k null walks used to be cached and never re-read. The prefix check
    is the bypass; if a null draft ever lands in the cache the growth (and the
    id-recycling hazard) is back."""
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=120),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    eng.run()
    for owner, _ in eng._walk_cache.values():
        assert not owner.expert_id.startswith(D.NULL_DRAFT_PREFIX)


def test_null_draft_tags_actually_carry_the_bypass_prefix():
    """The bypass is keyed on the tag, so the tags and the constant must not
    drift apart."""
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=90),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    for tag in ('null_random', 'null_long', 'null_short'):
        assert tag.startswith(D.NULL_DRAFT_PREFIX)
        d = eng._null_draft(0, 'LONG', tag)
        assert d.expert_id.startswith(D.NULL_DRAFT_PREFIX)


def test_opposite_direction_null_walks_are_not_confused():
    """The concrete failure P2 allowed: two null drafts at the SAME bar with
    the same geometry but opposite directions must produce opposite walks."""
    from v8.synth import make_synthetic_tape
    eng = D.DiagnosticEngine(make_synthetic_tape(seed=7, n_bars=200),
                             D.ALL_EXPERT_CLASSES, do_forensics=False)
    eng.run()
    k = 40
    long_d = eng._null_draft(k, 'LONG', 'null_long')
    short_d = eng._null_draft(k, 'SHORT', 'null_short')
    a = eng._simulate(long_d, k, sl=1.0, tp=1.0, expiry=8)
    b = eng._simulate(short_d, k, sl=1.0, tp=1.0, expiry=8)
    assert a.direction == 'LONG' and b.direction == 'SHORT'
    # and re-simulating in the other order returns the same values
    b2 = eng._simulate(eng._null_draft(k, 'SHORT', 'null_short'), k,
                       sl=1.0, tp=1.0, expiry=8)
    a2 = eng._simulate(eng._null_draft(k, 'LONG', 'null_long'), k,
                       sl=1.0, tp=1.0, expiry=8)
    assert (a2.net_r, a2.endpoint) == (a.net_r, a.endpoint)
    assert (b2.net_r, b2.endpoint) == (b.net_r, b.endpoint)
