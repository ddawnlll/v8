"""Bollinger band-reversion expert tests (`bollinger_reversion`).

Covers, per the book-to-V8 mapper card E-09 (mechanism `volatility_band`,
behavior `band_reversion`): Setup-2 fade-zone detection (close between the
2-SD and 3-SD bands -> fade toward 1-SD), Setup-3 trend-aligned reversion,
risk_geometry values pinned to the book's levels, still_valid thesis
invalidation (3-SD breakout for Setup 2; trend flip for Setup 3), D-026
episode-key stability + SUPPRESSED_DUPLICATE, and the no-economic-claim lab
invariant (rule 12).
"""
from __future__ import annotations

import pytest

from v8.schema import TapeRow
from v8.marketstate import build_state
from v8.lab import Lab
from v8.synth import HOUR_NS, make_synthetic_tape
from v8.experts.bollinger_reversion import BollingerReversionExpert

UNIVERSE = ('SOLUSDT',)


def _tape(closes: list[float]) -> list[TapeRow]:
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


def _manifest(**kw):
    base = dict(experiment_id='exp-br', code_hash='', data_hash='',
                universe=UNIVERSE, start_ns=0, end_ns=0)
    base.update(kw)
    from v8.schema import ExperimentManifest
    return ExperimentManifest(**base)


# A 20-bar alternating 102/98 base (wide bandwidth, sigma ~1.4) then 10 flat
# bars, then a gentle drift that keeps the close inside the upper fade zone
# (between 2-SD and 3-SD) for bars 30..33 -> a multi-bar Setup-2 SHORT run.
FADE_BASE = [102.0 if i % 2 == 0 else 98.0 for i in range(20)] + [100.0] * 10
SHORT_FADE = _tape(FADE_BASE + [103.5, 104.0, 104.5, 105.0, 105.0, 105.0])
LONG_FADE = _tape(FADE_BASE + [96.5, 96.0, 95.5, 95.0, 95.0, 95.0])
UP_TREND = _tape([100.0] * 20 + [100.0 + i for i in range(1, 13)])
DOWN_TREND = _tape([120.0] * 20 + [120.0 - i for i in range(1, 21)])


def test_setup_2_detects_short_fade_at_upper_band():
    ex = BollingerReversionExpert()
    draft = _draft_at(SHORT_FADE, ex, 30)
    assert draft.direction == 'SHORT'
    assert draft.setup_anchor_event_id == 'SOLUSDT:31'
    st = _state_at(SHORT_FADE, 30)
    f = st.features
    mid = float(f['SOLUSDT.bb_mid'].value)
    upper = float(f['SOLUSDT.bb_upper'].value)
    atr = float(f['SOLUSDT.atr'].value)
    sigma = (upper - mid) / 2
    g = draft.risk_geometry
    assert g['entry'] == 'NEXT_BAR_CLOSE'
    assert g['expiry_bars'] == 8
    # Setup 2 (Ch12 p481-482): the 3-SD stop and the 1-SD target are each one
    # band-sigma from the 2-SD entry proxy -> stop_r = target_r = sigma/atr.
    assert g['atr_ref'] == pytest.approx(atr)
    assert g['stop_r'] == pytest.approx(sigma / atr)
    assert g['target_r'] == pytest.approx(sigma / atr)
    assert g['upper_2sd_ref'] == pytest.approx(upper)
    assert g['upper_1sd_ref'] == pytest.approx(mid + sigma)
    assert g['upper_3sd_ref'] == pytest.approx(mid + 3 * sigma)


def test_setup_2_detects_long_fade_at_lower_band():
    ex = BollingerReversionExpert()
    draft = _draft_at(LONG_FADE, ex, 30)
    assert draft.direction == 'LONG'
    st = _state_at(LONG_FADE, 30)
    f = st.features
    mid = float(f['SOLUSDT.bb_mid'].value)
    lower = float(f['SOLUSDT.bb_lower'].value)
    atr = float(f['SOLUSDT.atr'].value)
    sigma = (mid - lower) / 2
    g = draft.risk_geometry
    assert g['stop_r'] == pytest.approx(sigma / atr)
    assert g['target_r'] == pytest.approx(sigma / atr)
    assert g['lower_2sd_ref'] == pytest.approx(lower)
    assert g['lower_3sd_ref'] == pytest.approx(mid - 3 * sigma)


def test_no_setup_outside_fade_zone():
    """A close beyond 3-SD is a breakout, not a reversion (Ch12 p471-474): the
    fade gate refuses it, as it refuses a degenerate flat tape."""
    ex = BollingerReversionExpert()
    assert ex.evaluate(_state_at(_tape([100.0] * 30 + [105.0] * 12),
                                 30)).decision == 'NO_SETUP'
    assert ex.evaluate(_state_at(_tape([100.0] * 30 + [95.0] * 12),
                                 30)).decision == 'NO_SETUP'
    assert ex.evaluate(_state_at(_tape([100.0] * 40), 35)).decision == 'NO_SETUP'


def test_setup_3_detects_trend_aligned_long():
    ex = BollingerReversionExpert(variant_id='b')
    draft = _draft_at(UP_TREND, ex, 25)
    assert draft.direction == 'LONG'
    assert draft.setup_anchor_event_id == 'SOLUSDT:21'   # run started bar 20
    # Geometry is frozen at the ANCHOR bar (20), not the detection bar (25).
    fa = _state_at(UP_TREND, 20).features
    mid = float(fa['SOLUSDT.bb_mid'].value)
    upper = float(fa['SOLUSDT.bb_upper'].value)
    atr = float(fa['SOLUSDT.atr'].value)
    sigma = (upper - mid) / 2
    g = draft.risk_geometry
    # Setup 3 (Ch12 p482): stop under the SMA (two sigma from the 2-SD entry
    # proxy), profit exit at the 1-SD band (one sigma).
    assert g['stop_r'] == pytest.approx(2 * sigma / atr)
    assert g['target_r'] == pytest.approx(sigma / atr)
    assert g['target_r'] == pytest.approx(g['stop_r'] / 2)
    assert g['mid_ref'] == pytest.approx(mid)
    assert g['upper_1sd_ref'] == pytest.approx(mid + sigma)
    assert g['upper_2sd_ref'] == pytest.approx(upper)


def test_setup_3_detects_trend_aligned_short():
    ex = BollingerReversionExpert(variant_id='b')
    draft = _draft_at(DOWN_TREND, ex, 25)
    assert draft.direction == 'SHORT'
    assert draft.risk_geometry['target_r'] == pytest.approx(
        draft.risk_geometry['stop_r'] / 2)


def test_geometry_frozen_at_anchor_not_detection():
    """The band stack is frozen at the setup ANCHOR (bar 30), not the
    detection bar (bar 33): episode_key hashes the structural geometry, and a
    detection-bar-frozen level would drift across the run and break dedup."""
    ex = BollingerReversionExpert()
    draft = _draft_at(SHORT_FADE, ex, 33)
    assert draft.setup_anchor_event_id == 'SOLUSDT:31'
    fa = _state_at(SHORT_FADE, 30).features
    fd = _state_at(SHORT_FADE, 33).features
    mid_a = float(fa['SOLUSDT.bb_mid'].value)
    upper_a = float(fa['SOLUSDT.bb_upper'].value)
    atr_a = float(fa['SOLUSDT.atr'].value)
    g = draft.risk_geometry
    assert g['stop_r'] == pytest.approx((upper_a - mid_a) / 2 / atr_a)
    assert g['upper_2sd_ref'] == pytest.approx(upper_a)
    assert g['upper_2sd_ref'] != pytest.approx(
        float(fd['SOLUSDT.bb_upper'].value))   # detection-bar value differs


def test_still_valid_setup_2_dies_when_close_passes_frozen_3sd():
    ex = BollingerReversionExpert()
    draft = _draft_at(SHORT_FADE, ex, 30)
    assert ex.still_valid(_state_at(SHORT_FADE, 30), draft) is True
    ref = draft.risk_geometry['upper_3sd_ref']
    over = _tape(FADE_BASE + [103.5, 104.0, 104.5, 105.0, ref + 1.0])
    assert ex.still_valid(_state_at(over, len(over) - 1), draft) is False


def test_still_valid_setup_3_dies_when_trend_flips():
    ex = BollingerReversionExpert(variant_id='b')
    rows = _tape([100.0] * 20 + [100.0 + i for i in range(1, 21)]
                 + [110.0, 100.0, 95.0, 92.0])
    draft = _draft_at(rows, ex, 20)
    assert draft.direction == 'LONG'
    assert ex.still_valid(_state_at(rows, 25), draft) is True
    # The sharp drop flips ema_fast below ema_slow at bar 41.
    assert ex.still_valid(_state_at(rows, 41), draft) is False


def test_still_valid_fails_open_on_unobservable_close():
    ex = BollingerReversionExpert()
    draft = _draft_at(SHORT_FADE, ex, 30)
    empty = build_state([], 0, UNIVERSE)
    assert ex.still_valid(empty, draft) is True


def test_variants_evaluated_and_variant_switch():
    assert BollingerReversionExpert.variants_evaluated == ('a', 'b')
    assert BollingerReversionExpert().variant_id == 'a'
    assert BollingerReversionExpert('b').variant_id == 'b'
    with pytest.raises(ValueError, match='unknown variant'):
        BollingerReversionExpert('z')


def test_episode_key_stable_and_suppressed_duplicate(tmp_path):
    """Multi-bar fade run -> one episode; repeats are SUPPRESSED_DUPLICATE
    (D-026), both for Setup 2 and the persistent Setup-3 trend run."""
    for rows, ex in [(SHORT_FADE, BollingerReversionExpert()),
                     (UP_TREND, BollingerReversionExpert(variant_id='b'))]:
        lab = Lab(tmp_path / ex.variant_id)
        lab.ingest(rows)
        r = lab.run(_manifest(), [ex])
        detected = [rec for rec in lab.candidates.read()
                    if rec.get('to_state') == 'DETECTED']
        suppressed = [rec for rec in lab.candidates.read()
                      if rec.get('kind') == 'suppressed_duplicate']
        assert len(detected) == 1, f'variant {ex.variant_id}: key drift'
        assert suppressed, f'variant {ex.variant_id}: no suppressed repeat'
        assert r.candidate_count == 1
        assert r.verdict == 'NO_ECONOMIC_CLAIM'


def test_lab_run_on_synthetic_tape_no_economic_claim(tmp_path):
    lab = Lab(tmp_path)
    lab.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r = lab.run(_manifest(), [BollingerReversionExpert(),
                              BollingerReversionExpert(variant_id='b')])
    assert r.verdict == 'NO_ECONOMIC_CLAIM'          # no authority receipt
    assert r.evaluation_distribution                  # expert actually ran
    assert sum(r.terminal_distribution.values()) == r.candidate_count


def test_deterministic_across_fresh_stores(tmp_path):
    m = _manifest()
    lab1 = Lab(tmp_path / 'r1')
    lab1.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r1 = lab1.run(m, [BollingerReversionExpert()])
    lab2 = Lab(tmp_path / 'r2')
    lab2.ingest(make_synthetic_tape(seed=11, n_bars=160))
    r2 = lab2.run(m, [BollingerReversionExpert()])
    assert r1.ledger_hash == r2.ledger_hash
    assert r1.candidate_count == r2.candidate_count
