"""Bollinger band-breakout expert tests (`bollinger_breakout`).

Covers, per the book-to-V8 mapper card E-08 (mechanism `volatility_band`,
behavior `band_breakout`): Setup-1 detection on a crafted tape (close beyond
the SMA -> LONG/SHORT), the closing band violation variant, the bandwidth-
squeeze precondition, risk_geometry values pinned to the book's levels
(central-value stop, 2-SD target, expressed as R-multiples), still_valid
thesis invalidation, D-026 episode-key stability + SUPPRESSED_DUPLICATE, and
the no-economic-claim lab invariant (rule 12).
"""
from __future__ import annotations

import pytest

from v8.schema import TapeRow
from v8.marketstate import build_state
from v8.lab import Lab
from v8.synth import HOUR_NS, make_synthetic_tape
from v8.experts.bollinger_breakout import BollingerBreakoutExpert

UNIVERSE = ('SOLUSDT',)


def _tape(closes: list[float]) -> list[TapeRow]:
    """Deterministic 1h tape; OHLC keeps the D-024 bar-range veto quiet
    ((high-low)/close = 0.004 < 0.05) and funding windows out of the way."""
    rows: list[TapeRow] = []
    for i, c in enumerate(closes):
        rows.append(TapeRow(
            source='binance-um', channel='kline', instrument='SOLUSDT',
            event_time=HOUR_NS * i, available_time=HOUR_NS * i,
            ingested_time=HOUR_NS * i, venue_sequence=i + 1,
            event_id=f'SOLUSDT:{i + 1}',
            payload={'open': c, 'high': c * 1.002, 'low': c * 0.998,
                     'close': c, 'volume': 1.0, 'closed': True}))
    return rows


def _state_at(rows, idx):
    as_of = rows[idx].available_time
    return build_state([r for r in rows if r.available_time <= as_of],
                       as_of, UNIVERSE)


def _draft_at(rows, expert, idx):
    ev = expert.evaluate(_state_at(rows, idx))
    assert ev.draft is not None, f'no draft at bar {idx}'
    return ev.draft


# Bars 30..41 sit 5% above the 20-SMA: the SMA20 is ~102.5 and the upper
# 2-SD band ~103-107 across the run, so bar 30 is the first close > bb_mid
# AND the first close > bb_upper (a step of +5 on a sigma ~1 base breaks every
# band level at once). 30 flat bars at 100 pin the anchor context.
UP_TAPE = _tape([100.0] * 30 + [105.0] * 12)
DOWN_TAPE = _tape([100.0] * 30 + [97.0] * 12)


def test_setup_1_detects_long_on_close_above_sma():
    ex = BollingerBreakoutExpert()
    draft = _draft_at(UP_TAPE, ex, 30)
    assert draft.direction == 'LONG'
    assert draft.setup_anchor_event_id == 'SOLUSDT:31'   # run-start bar 30
    st = _state_at(UP_TAPE, 30)
    f = st.features
    mid = float(f['SOLUSDT.bb_mid'].value)
    upper = float(f['SOLUSDT.bb_upper'].value)
    atr = float(f['SOLUSDT.atr'].value)
    sigma = (upper - mid) / 2
    g = draft.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['expiry_bars'] == 8
    # Book levels frozen at the anchor (== detection here): stop under the
    # SMA, target the 2-SD band, each one band-sigma from the 1-SD entry
    # proxy -> stop_r = target_r = sigma/atr (Ch12 p473-474, p480-481).
    assert g['atr_ref'] == pytest.approx(atr)
    assert g['stop_r'] == pytest.approx(sigma / atr)
    assert g['target_r'] == pytest.approx(sigma / atr)
    assert g['mid_ref'] == pytest.approx(mid)
    assert g['upper_1sd_ref'] == pytest.approx(mid + sigma)
    assert g['upper_2sd_ref'] == pytest.approx(upper)


def test_setup_1_detects_short_on_close_below_sma():
    ex = BollingerBreakoutExpert()
    draft = _draft_at(DOWN_TAPE, ex, 30)
    assert draft.direction == 'SHORT'
    assert draft.setup_anchor_event_id == 'SOLUSDT:31'
    st = _state_at(DOWN_TAPE, 30)
    f = st.features
    mid = float(f['SOLUSDT.bb_mid'].value)
    lower = float(f['SOLUSDT.bb_lower'].value)
    atr = float(f['SOLUSDT.atr'].value)
    sigma = (mid - lower) / 2
    g = draft.risk_geometry
    assert g['stop_r'] == pytest.approx(sigma / atr)
    assert g['target_r'] == pytest.approx(sigma / atr)
    assert g['lower_1sd_ref'] == pytest.approx(mid - sigma)
    assert g['lower_2sd_ref'] == pytest.approx(lower)


def test_no_setup_on_flat_tape():
    ex = BollingerBreakoutExpert()
    ev = ex.evaluate(_state_at(_tape([100.0] * 40), 35))
    assert ev.decision == 'NO_SETUP'
    assert ev.draft is None


def test_geometry_frozen_at_anchor_not_detection():
    """The band stack is frozen at the setup ANCHOR (bar 30), not the
    detection bar (bar 35): episode_key hashes the structural geometry, and a
    detection-bar-frozen level would drift across the run and break dedup."""
    ex = BollingerBreakoutExpert()
    draft = _draft_at(UP_TAPE, ex, 35)
    assert draft.setup_anchor_event_id == 'SOLUSDT:31'
    fa = _state_at(UP_TAPE, 30).features
    fd = _state_at(UP_TAPE, 35).features
    mid_a = float(fa['SOLUSDT.bb_mid'].value)
    upper_a = float(fa['SOLUSDT.bb_upper'].value)
    atr_a = float(fa['SOLUSDT.atr'].value)
    g = draft.risk_geometry
    assert g['stop_r'] == pytest.approx((upper_a - mid_a) / 2 / atr_a)
    assert g['mid_ref'] == pytest.approx(mid_a)
    assert g['mid_ref'] != pytest.approx(
        float(fd['SOLUSDT.bb_mid'].value))        # detection-bar value differs


def test_warmup_tape_is_no_habitat():
    # Fewer than 20 closes: no bb_* features are emitted -> NO_HABITAT.
    ev = BollingerBreakoutExpert().evaluate(_state_at(_tape([100.0] * 15), 14))
    assert ev.decision == 'NO_HABITAT'


def test_band_breakout_closing_violation_detects_long():
    ex = BollingerBreakoutExpert(variant_id='b')
    draft = _draft_at(UP_TAPE, ex, 30)
    assert draft.direction == 'LONG'
    st = _state_at(UP_TAPE, 30)
    f = st.features
    mid = float(f['SOLUSDT.bb_mid'].value)
    upper = float(f['SOLUSDT.bb_upper'].value)
    atr = float(f['SOLUSDT.atr'].value)
    sigma = (upper - mid) / 2
    g = draft.risk_geometry
    # The 2-SD band is already violated at entry; the central-value stop is
    # two sigma away and the unstated target falls back to the family 1:1.
    assert g['stop_r'] == pytest.approx(2 * sigma / atr)
    assert g['target_r'] == pytest.approx(2 * sigma / atr)
    assert g['mid_ref'] == pytest.approx(mid)          # book caveat: SMA stop
    assert g['upper_2sd_ref'] == pytest.approx(upper)


def test_band_breakout_short_violation():
    ex = BollingerBreakoutExpert(variant_id='b')
    draft = _draft_at(DOWN_TAPE, ex, 30)
    assert draft.direction == 'SHORT'
    assert draft.risk_geometry['lower_2sd_ref'] == pytest.approx(
        float(_state_at(DOWN_TAPE, 30).features['SOLUSDT.bb_lower'].value))


def test_squeeze_requires_prior_bandwidth_contraction():
    ex = BollingerBreakoutExpert(variant_id='c')
    # 20 alternating 105/95 bars (wide bandwidth), 20 flat 100 bars (each a
    # fresh bandwidth low), then a breakout close beyond the band.
    squeeze = _tape([105.0 if i % 2 == 0 else 95.0 for i in range(20)]
                    + [100.0] * 20 + [105.0])
    draft = _draft_at(squeeze, ex, 40)
    assert draft.direction == 'LONG'
    assert draft.setup_anchor_event_id == 'SOLUSDT:41'
    # Without the contraction (flat -> step: the breakout bar's bandwidth is
    # an EXPANSION, not a continuation of a low) the squeeze gate must refuse.
    assert ex.evaluate(_state_at(UP_TAPE, 30)).decision == 'NO_SETUP'


def test_still_valid_setup_1_dies_when_close_crosses_frozen_sma():
    ex = BollingerBreakoutExpert()
    draft = _draft_at(UP_TAPE, ex, 30)
    assert ex.still_valid(_state_at(UP_TAPE, 30), draft) is True
    drop = _tape([100.0] * 30 + [105.0] * 4 + [98.0])
    late = _state_at(drop, len(drop) - 1)
    assert ex.still_valid(late, draft) is False        # close 98 < mid_ref 100.25


def test_still_valid_band_breakout_tracks_broken_band():
    ex = BollingerBreakoutExpert(variant_id='b')
    draft = _draft_at(UP_TAPE, ex, 30)
    assert ex.still_valid(_state_at(UP_TAPE, 30), draft) is True
    # Close falls back inside the bands (below the frozen 2-SD level).
    back = _tape([100.0] * 30 + [105.0] * 4 + [101.0])
    assert ex.still_valid(_state_at(back, len(back) - 1), draft) is False


def test_still_valid_fails_open_on_unobservable_close():
    ex = BollingerBreakoutExpert()
    draft = _draft_at(UP_TAPE, ex, 30)
    # A tape with no closed kline emits no close feature; an unreadable
    # thesis is not a dead thesis (price still governs).
    empty = build_state([], 0, UNIVERSE)
    assert ex.still_valid(empty, draft) is True


def test_variants_evaluated_and_variant_switch():
    assert BollingerBreakoutExpert.variants_evaluated == ('a', 'b', 'c')
    assert BollingerBreakoutExpert().variant_id == 'a'
    assert BollingerBreakoutExpert('a').variant_id == 'a'
    assert BollingerBreakoutExpert('b').variant_id == 'b'
    assert BollingerBreakoutExpert('c').variant_id == 'c'
    with pytest.raises(ValueError, match='unknown variant'):
        BollingerBreakoutExpert('z')


def test_episode_key_stable_and_suppressed_duplicate(tmp_path):
    """One setup run over consecutive clocks -> one episode; repeats are
    SUPPRESSED_DUPLICATE, never a second candidate (D-026)."""
    lab = Lab(tmp_path)
    lab.ingest(UP_TAPE)
    r = lab.run(_manifest(), [BollingerBreakoutExpert()])
    detected = [rec for rec in lab.candidates.read()
                if rec.get('to_state') == 'DETECTED']
    suppressed = [rec for rec in lab.candidates.read()
                  if rec.get('kind') == 'suppressed_duplicate']
    assert len(detected) == 1
    assert suppressed
    assert r.candidate_count == 1
    assert r.verdict == 'NO_ECONOMIC_CLAIM'


def _manifest(**kw):
    base = dict(experiment_id='exp-bb', code_hash='', data_hash='',
                universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    from v8.schema import ExperimentManifest
    return ExperimentManifest(**base)


def test_lab_run_on_synthetic_tape_no_economic_claim(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r = lab.run(_manifest(), [BollingerBreakoutExpert(),
                              BollingerBreakoutExpert('b'),
                              BollingerBreakoutExpert('c')])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'          # no authority receipt
    assert r.evaluation_distribution                  # expert actually ran
    assert sum(r.terminal_distribution.values()) == r.candidate_count


def test_deterministic_across_fresh_stores(tmp_path):
    m = _manifest()
    lab1 = Lab(tmp_path / 'r1')
    lab1.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r1 = lab1.run(m, [BollingerBreakoutExpert(), BollingerBreakoutExpert('b')])
    lab2 = Lab(tmp_path / 'r2')
    lab2.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r2 = lab2.run(m, [BollingerBreakoutExpert(), BollingerBreakoutExpert('b')])
    assert r1.ledger_hash == r2.ledger_hash
    assert r1.candidate_count == r2.candidate_count
