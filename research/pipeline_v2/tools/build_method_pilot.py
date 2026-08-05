#!/usr/bin/env python3
"""
P4 v2.2 canonical_method pilot classifier.

Builds registry/p4_v22_method_pilot.json from registry/p4_b1_partial.json.

Approach (deterministic, auditable, non-hallucinating):
  * For each of the 920 corroborations, decide whether the record describes a
    NAMED method literally present in its exact_text/added_conditions/
    added_parameters, vs a generic mechanism (left untouched).
  * A named method is only created when the source name appears literally and
    the record is genuinely about that method (not an incidental mention).
  * Distinguishing parameters are carried over from the record's
    added_parameters only when they carry page or claim_ref; otherwise omitted.
  * No profitability / edge / validated-performance claims are asserted.
  * Source-native terminology preserved; no crypto/BTC/V8 vocabulary injected.

The user chose MAXIMAL granularity: every individually-named pattern gets its
own canonical_method_id where genuinely present as the subject of >=1 record.
"""
import json, re, os, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Full-run (A3) reads p4_full_run.json -> p4_v23_methods.json; pilot default
# reads p4_b1_partial.json -> p4_v22_method_pilot.json. Overridable via argv.
def _arg(name, default):
    for a in sys.argv[1:]:
        if a.startswith(name + '='):
            return a.split('=', 1)[1]
    return default
INP = os.path.join(BASE, 'registry', _arg('--inp', 'p4_b1_partial.json'))
OUT = os.path.join(BASE, 'registry', _arg('--out', 'p4_v22_method_pilot.json'))

# ---------------------------------------------------------------------------
# Method catalog: canonical_method_id -> descriptor
#   name_in_source : the literal name as it appears in the source
#   parent         : must be one of the 21 canonical_behavior_ids
#   patterns       : list of (regex, label) to locate the name in the blob
#   subject_re     : optional stricter regex; if present, the record must ALSO
#                    match this to be treated as genuinely about the method
# ---------------------------------------------------------------------------
METHODS = {}

def add(mid, name, parent, patterns, subject=None, only_books=None, mclass='other'):
    METHODS[mid] = {
        'name_in_source': name,
        'parent': parent,
        'patterns': patterns,
        'subject': subject,
        'only_books': only_books,
        'mclass': mclass,
    }

# ---- Harmonic (book_0055) ------------------------------------------------
add('harmonic_rsi_bamm', 'RSI BAMM', 'momentum_divergence_reversal',
    [r'\bRSI BAMM\b'])
add('harmonic_bam', 'BAMM', 'momentum_divergence_reversal',
    [r'\bBAMM\b'])
add('harmonic_ab_cd', 'AB=CD', 'trend_continuation_pullback',
    [r'\bAB\s*=\s*CD\b', r'\bab=cd\b'])
add('harmonic_gartley', 'Gartley', 'momentum_divergence_reversal',
    [r'\bGartley\b'])
add('harmonic_butterfly', 'Butterfly', 'momentum_divergence_reversal',
    [r'\bButterfly\b'])
add('harmonic_bat', 'Bat', 'momentum_divergence_reversal',
    [r'\bBat\b', r'\bBats?\b'])
add('harmonic_crab', 'Crab', 'momentum_divergence_reversal',
    [r'\bCrab\b'])
add('harmonic_5_0', '5-0', 'momentum_divergence_reversal',
    [r'\b5-0\b', r'\b5[- ]0 pattern\b'])

# ---- Candlestick single-line (0052, 0016, 0025) --------------------------
CANDLEBOOKS = ['book_0052', 'book_0016', 'book_0025']
add('candlestick_hammer', 'Hammer', 'candlestick_reversal_pattern',
    [r'\bhammer\b'], subject=r'\bhammer\b', only_books=CANDLEBOOKS)
add('candlestick_hanging_man', 'Hanging Man', 'candlestick_reversal_pattern',
    [r'\bhanging man\b'], only_books=CANDLEBOOKS)
add('candlestick_shooting_star', 'Shooting Star', 'candlestick_reversal_pattern',
    [r'\bshooting star\b'], only_books=CANDLEBOOKS)
add('candlestick_inverted_hammer', 'Inverted Hammer', 'candlestick_reversal_pattern',
    [r'\binverted hammer\b'], only_books=CANDLEBOOKS)
add('candlestick_doji', 'Doji', 'candlestick_reversal_pattern',
    [r'\bdoji\b'], subject=r'\bdoji\b', only_books=CANDLEBOOKS)
add('candlestick_long_legged_doji', 'Long-Legged Doji', 'candlestick_reversal_pattern',
    [r'\blong-legged doji\b', r'\blickshaw man\b'], only_books=CANDLEBOOKS)
add('candlestick_dragonfly_doji', 'Dragonfly Doji', 'candlestick_reversal_pattern',
    [r'\bdragonfly doji\b'], only_books=CANDLEBOOKS)
add('candlestick_gravestone_doji', 'Gravestone Doji', 'candlestick_reversal_pattern',
    [r'\bgravestone doji\b'], only_books=CANDLEBOOKS)
add('candlestick_spinning_top', 'Spinning Top', 'candlestick_reversal_pattern',
    [r'\bspinning top\b'], only_books=CANDLEBOOKS)
add('candlestick_star', 'Star', 'candlestick_reversal_pattern',
    [r'(?<!\bshooting\s)(?<!\bmorning\s)(?<!\bevening\s)(?<!\bdoji\s)(?<!\binverted\s)\bstar\b',
     r'\bstar\s+pattern\b'],
    subject=r'(?<!\bshooting\s)(?<!\bmorning\s)(?<!\bevening\s)(?<!\bdoji\s)(?<!\binverted\s)\bstar\b',
    only_books=CANDLEBOOKS)
add('candlestick_doji_star', 'Doji Star', 'candlestick_reversal_pattern',
    [r'\bdoji star\b'], only_books=CANDLEBOOKS)

# ---- Candlestick two-line ------------------------------------------------
add('candlestick_engulfing', 'Engulfing', 'candlestick_reversal_pattern',
    [r'\bengulfing\b'], only_books=CANDLEBOOKS)
add('candlestick_harami', 'Harami', 'candlestick_reversal_pattern',
    [r'\bharami\b'], only_books=CANDLEBOOKS)
add('candlestick_harami_cross', 'Harami Cross', 'candlestick_reversal_pattern',
    [r'\bharami cross\b', r'\bharami yose sen\b'], only_books=CANDLEBOOKS)
add('candlestick_piercing', 'Piercing Line', 'candlestick_reversal_pattern',
    [r'\bpiercing\b', r'\bpiercing line\b'], only_books=CANDLEBOOKS)
add('candlestick_dark_cloud_cover', 'Dark Cloud Cover', 'candlestick_reversal_pattern',
    [r'\bdark cloud cover\b', r'\bdark cloud\b'], only_books=CANDLEBOOKS)
add('candlestick_homing_pigeon', 'Homing Pigeon', 'candlestick_reversal_pattern',
    [r'\bhoming pigeon\b'], only_books=CANDLEBOOKS)
add('candlestick_descending_hawk', 'Descending Hawk', 'candlestick_reversal_pattern',
    [r'\bdescending hawk\b'], only_books=CANDLEBOOKS)
add('candlestick_in_neck_line', 'In Neck Line', 'candlestick_reversal_pattern',
    [r'\bin neck line\b'], only_books=CANDLEBOOKS)
add('candlestick_on_neck_line', 'On Neck Line', 'candlestick_reversal_pattern',
    [r'\bon neck line\b'], only_books=CANDLEBOOKS)
add('candlestick_thrusting', 'Thrusting Line', 'candlestick_reversal_pattern',
    [r'\bthrusting\b'], only_books=CANDLEBOOKS)
add('candlestick_tweezer', 'Tweezer', 'candlestick_reversal_pattern',
    [r'\btweezer\b'], only_books=CANDLEBOOKS)

# ---- Candlestick three-line ---------------------------------------------
add('candlestick_morning_star', 'Morning Star', 'candlestick_reversal_pattern',
    [r'\bmorning star\b'], only_books=CANDLEBOOKS)
add('candlestick_evening_star', 'Evening Star', 'candlestick_reversal_pattern',
    [r'\bevening star\b'], only_books=CANDLEBOOKS)
add('candlestick_three_white_soldiers', 'Three White Soldiers', 'candlestick_reversal_pattern',
    [r'\bthree white soldiers\b', r'\bthree white\b'], only_books=CANDLEBOOKS)
add('candlestick_three_black_crows', 'Three Black Crows', 'candlestick_reversal_pattern',
    [r'\bthree black crows\b', r'\bthree black\b'], only_books=CANDLEBOOKS)
add('candlestick_breakaway', 'Breakaway', 'candlestick_reversal_pattern',
    [r'\bbreakaway\b'], only_books=CANDLEBOOKS)
add('candlestick_rising_three', 'Rising Three Methods', 'candlestick_reversal_pattern',
    [r'\brising three\b'], only_books=CANDLEBOOKS)
add('candlestick_falling_three', 'Falling Three', 'candlestick_reversal_pattern',
    [r'\bfalling three\b'], only_books=CANDLEBOOKS)
add('candlestick_mat_hold', 'Mat Hold', 'candlestick_reversal_pattern',
    [r'\bmat hold\b'], only_books=CANDLEBOOKS)
add('candlestick_deliberation', 'Deliberation', 'candlestick_reversal_pattern',
    [r'\bdeliberation\b'], only_books=CANDLEBOOKS)

# ---- Chart patterns (0121, 0098, 0052) ----------------------------------
add('chart_head_shoulders', 'Head-and-Shoulders', 'support_resistance_bounce',
    [r'\bhead[\s-]*(?:and|&)[\s-]*shoulders?\b', r'\bH&S\b'],
    only_books=['book_0121', 'book_0110', 'book_0098'])
add('chart_double_top', 'Double Top', 'support_resistance_bounce',
    [r'\bdouble top\b'], only_books=['book_0121', 'book_0098', 'book_0052'])
add('chart_double_bottom', 'Double Bottom', 'support_resistance_bounce',
    [r'\bdouble bottom\b'], only_books=['book_0121', 'book_0098', 'book_0052'])
add('chart_triple_top', 'Triple Top', 'support_resistance_bounce',
    [r'\btriple top\b'], only_books=['book_0121', 'book_0098', 'book_0052'])
add('chart_triple_bottom', 'Triple Bottom', 'support_resistance_bounce',
    [r'\btriple bottom\b'], only_books=['book_0121', 'book_0098', 'book_0052'])
add('chart_rectangle', 'Rectangle', 'breakout_retest',
    [r'\brectangle\b'], only_books=['book_0121', 'book_0098'])
add('chart_triangle', 'Triangle', 'volatility_breakout',
    [r'\btriangle\b'], only_books=['book_0121', 'book_0098'])
add('chart_symmetrical_triangle', 'Symmetrical Triangle', 'volatility_breakout',
    [r'\bsymmetrical triangle\b'], only_books=['book_0121', 'book_0098'])
add('chart_ascending_triangle', 'Ascending Triangle', 'volatility_breakout',
    [r'\bascending triangle\b'], only_books=['book_0121', 'book_0098'])
add('chart_descending_triangle', 'Descending Triangle', 'volatility_breakout',
    [r'\bdescending triangle\b'], only_books=['book_0121', 'book_0098'])
add('chart_flag', 'Flag', 'trend_continuation_pullback',
    [r'\bflag\b'], only_books=['book_0098', 'book_0121'])
add('chart_pennant', 'Pennant', 'trend_continuation_pullback',
    [r'\bpennant\b'], only_books=['book_0098', 'book_0121'])
add('chart_wedge', 'Wedge', 'trend_continuation_pullback',
    [r'\bwedge\b'], only_books=['book_0114'])
add('chart_cup_handle', 'Cup-and-Handle', 'breakout_retest',
    [r'\b(?:cup[\s-]*and[\s-]*handle|cup with handle|cup-and-handle)\b'],
    only_books=['book_0032', 'book_0121'])
add('chart_adam_eve', 'Adam and Eve', 'support_resistance_bounce',
    [r'\badam\b', r'\beve\b'], subject=r'\badam[\s-]*and[\s-]*eve\b|adam bottom|eve bottom',
    only_books=['book_0121'])
add('chart_rounded_bottom', 'Rounded Bottom', 'support_resistance_bounce',
    [r'\brounded bottom\b'], only_books=['book_0121', 'book_0052'])

# ---- Indicators / methodologies -----------------------------------------
add('indicator_bollinger_bands', 'Bollinger Band', 'mean_reversion_band',
    [r'\bBollinger\b'])
add('indicator_stochastic', 'Stochastic', 'mean_reversion_band',
    [r'\bstochastic\b'])
add('indicator_adx', 'Average Directional Index (ADX)', 'trend_continuation_pullback',
    [r'\bADX\b', r'\bAverage Directional Index\b'])
add('indicator_macd', 'MACD', 'line_crossover_momentum',
    [r'\bMACD\b'])
add('indicator_force_index', 'Force Index', 'momentum_divergence_reversal',
    [r'\bForce Index\b'])
add('indicator_parabolic_sar', 'Parabolic SAR', 'trend_continuation_pullback',
    [r'\bParabolic SAR\b'])
add('indicator_fibonacci_retracement', 'Fibonacci Retracement', 'support_resistance_bounce',
    [r'\bfibonacci\b', r'\bFib\b'])
add('indicator_pivot_point', 'Pivot Point', 'support_resistance_bounce',
    [r'\bpivot points?\b'])
add('indicator_donchian', 'Donchian', 'trend_continuation_pullback',
    [r'\bDonchian\b'])
add('indicator_elliott_wave', 'Elliott Wave', 'trend_following_channel',
    [r'\bElliott\b', r'\bfive-wave\b', r'\b5-wave\b'])
add('indicator_volume_roc', 'volume ROC', 'capitulation_exhaustion',
    [r'\bvolume ROC\b', r'\bvolume rate of change\b'])

# ---- Price-action setups (0114) -----------------------------------------
add('pa_two_bar_reversal', 'Two-Bar Reversal', 'candlestick_reversal_pattern',
    [r'\btwo-bar reversal\b', r'\b2-bar reversal\b'])
add('pa_high_low_1_2', 'High 1/2 and Low 1/2', 'trend_continuation_pullback',
    [r'\bhigh 1\b', r'\bhigh 2\b', r'\blow 1\b', r'\blow 2\b', r'\bhigh2\b', r'\blow2\b'])
add('pa_wedge_flag', 'Wedge Flag', 'trend_continuation_pullback',
    [r'\bwedge bull flag\b', r'\bwedge bear flag\b', r'\bwedge flag\b'])
add('pa_double_bottom_bull_flag', 'Double Bottom Bull Flag', 'trend_continuation_pullback',
    [r'\bdouble bottom bull flag\b', r'\bdouble top bear flag\b'])
add('pa_breakout_pullback', 'Breakout Pullback', 'trend_continuation_pullback',
    [r'\bbreakout pullback\b'])
add('pa_inside_bar_ii', 'Inside Bar (ii/iii)', 'trend_continuation_pullback',
    [r'\binside bar\b', r'\bii pattern\b', r'\bii setup\b', r'\bii short\b'])
add('pa_three_push', 'Three-Push', 'pattern_breakout_projection',
    [r'\bthree-push\b', r'\bthree push\b'])
add('pa_stairs', 'Stairs', 'trend_exhaustion_reversal',
    [r'\bstairs\b'])
add('pa_final_flag', 'Final Flag', 'trend_exhaustion_reversal',
    [r'\bfinal flag\b'])
add('pa_trend_from_open', 'Trend From Open', 'trend_continuation_pullback',
    [r'\btrend from the open\b', r'\btrend from open\b'])
add('pa_micro_double_bottom', 'Micro Double Bottom', 'candlestick_reversal_pattern',
    [r'\bmicro double bottom\b', r'\bmicro double top\b'])

# ---- Named strategies (0002, 0032, 0020) ---------------------------------
add('strategy_siamese_twins', 'Siamese Twins', 'trend_continuation_pullback',
    [r'\bSiamese twins\b'])
add('strategy_guppy_burst', 'Guppy Burst', 'volatility_breakout',
    [r'\bguppy burst\b'])
add('strategy_fade_the_break', 'Fade the Break', 'failed_breakout_reentry',
    [r'\bfade the break\b'])
add('strategy_trade_the_break', 'Trade the Break', 'volatility_breakout',
    [r'\btrade the break\b', r'\btrade the break\b'])
add('strategy_trend_knockout', 'Trend Knockout', 'trend_continuation_pullback',
    [r'\bTrend Knockout\b'])
add('strategy_double_top_knockout', 'Double Top Knockout', 'volatility_breakout',
    [r'\bDouble Top Knockout\b'])
add('strategy_trend_pivot_false_rally', 'Trend Pivot (False Rally)', 'trend_continuation_pullback',
    [r'\bTrend Pivot\b', r'\bFalse Rally\b'])
add('strategy_cvr_iii', 'CVR III', 'mean_reversion_band',
    [r'\bCVR III\b', r'\bCVR\b'])
add('strategy_3_10_oscillator', '3-10 Oscillator', 'mean_reversion_band',
    [r'\b3-10 Oscillator\b', r'\b3/10 oscillator\b'])

# ---- P4 v2.3 A2 catalog additions (101-book full run) ---------------------
# Each name is source-explicit (verified verbatim in the 101 books' gate-input
# anchor_text). only_books constrains general words. Parents are among the 21
# canonical behaviors. No invented content.
add('indicator_ichimoku', 'Ichimoku', 'trend_following_channel',
    [r'\bichimoku\b'])
add('indicator_ichimoku_tenkan', 'Tenkan', 'trend_following_channel',
    [r'\btenkan\b'])
add('indicator_ichimoku_kijun', 'Kijun', 'trend_following_channel',
    [r'\bkijun\b'])
add('chart_kagi', 'Kagi', 'trend_following_channel',
    [r'\bkagi\b'], only_books=['book_0008'])
add('chart_renko', 'Renko', 'trend_following_channel',
    [r'\brenko\b'], only_books=['book_0008'])
add('indicator_commitments_of_traders', 'COT', 'volume_confirmed_breakout',
    [r'\bCOT\b', r'\bcommitments?\s+of\s+traders\b'])
add('indicator_vwap', 'VWAP', 'mean_reversion_band',
    [r'\bVWAP\b', r'\bvolume[- ]weighted average price\b'], only_books=['book_0057'])
add('indicator_atr', 'ATR', 'volatility_breakout',
    [r'\bATR\b', r'\bAverage True Range\b'])
add('indicator_williams_r', 'Williams %R', 'mean_reversion_band',
    [r'\bWilliams\s*%?\s*R\b'])
add('indicator_cci', 'CCI', 'mean_reversion_band',
    [r'\bCCI\b', r'\bCommodity Channel Index\b'])
add('indicator_keltner_channel', 'Keltner', 'mean_reversion_band',
    [r'\bKeltner\b'])
add('indicator_gann', 'Gann', 'support_resistance_bounce',
    [r'\bGann\b'])
add('indicator_market_profile', 'Market Profile', 'volume_confirmed_breakout',
    [r'\bMarket Profile\b'])
add('indicator_volume_flow', 'Volume Flow Indicator', 'volume_confirmed_breakout',
    [r'\bVolume Flow Indicator\b', r'\bVFI\b'])
add('indicator_on_balance_volume', 'OBV', 'volume_confirmed_breakout',
    [r'\bOBV\b'])
add('indicator_dmi', 'DMI', 'trend_continuation_pullback',
    [r'\bDMI\b', r'\bDirectional Movement\b'])
add('indicator_gann_fan_lines', 'Fan Lines', 'support_resistance_bounce',
    [r'\bfan lines?\b'])
add('chart_half_mast', 'Half-mast', 'trend_continuation_pullback',
    [r'\bHalf[- ]mast\b'])
add('strategy_kiss', 'KISS', 'mean_reversion_band',
    [r'\bKISS\b'])
# Wyckoff spring (support break-and-reclaim). "upthrust" is a distinct
# concept (resistance break-and-fail) and is NOT a Spring; "spring" as a
# season ("spring 2006") or "coiled spring" (a chart spring/coil) is also
# not the Wyckoff spring — constrained to Wyckoff/Nison sources.
add('level_spring', 'Spring', 'support_resistance_bounce',
    [r'\bspring\b'], only_books=['book_0008', 'book_0065', 'book_0006', 'book_0084'])
add('chart_broadening_top', 'Broadening Top', 'volatility_breakout',
    [r'\bBroadening Top\b'])
add('candlestick_one_day_reversal', 'One-Day Reversal', 'candlestick_reversal_pattern',
    [r'\bone[- ]day reversal\b'])
add('pa_busted', 'Busted', 'failed_breakout_reentry',
    [r'\bbusted\b'])
add('indicator_rs_macd', 'RS-MACD', 'momentum_divergence_reversal',
    [r'\bRS-MACD\b'])
add('indicator_comas', 'COMAS', 'mean_reversion_band',
    [r'\bCOMAS\b'])
add('indicator_atm_tsb', 'ATM TSB', 'mean_reversion_band',
    [r'\bATM TSB\b', r'\bTSB\b'])
add('chart_ges', 'GES', 'breakout_retest',
    [r'\bGES\b'])
add('indicator_jdk_rs_ratio', 'JdK RS-Ratio', 'momentum_divergence_reversal',
    [r'\bJdK\b'])
add('indicator_ribbon_study', 'Ribbon Study', 'trend_following_channel',
    [r'\bRibbon Study\b', r'\bribbon\b'])
add('strategy_dual_moving_average', 'Dual Moving Average', 'trend_continuation_pullback',
    [r'\bdual moving average\b'])
add('chart_expanded_flat', 'Expanded Flat', 'trend_continuation_pullback',
    [r'\bExpanded Flat\b'])
add('chart_zigzag', 'Zigzag', 'trend_continuation_pullback',
    [r'\bzigzag\b'])
add('indicator_dma', 'DMA', 'trend_continuation_pullback',
    [r'\bDMA\b'])
add('pa_pinocchio', 'Pinocchio', 'liquidity_sweep_reclaim',
    [r'\bPinocchio\b'])
add('chart_impulse', 'Impulse', 'trend_following_channel',
    [r'\bimpulse\b'])
add('strategy_turtle_soup', 'Turtle Soup', 'failed_breakout_reentry',
    [r'\bturtle soup\b'])

# ---------------------------------------------------------------------------
# method_class roll-up (ADIM 1b KURAL 2) — assigned by method_id prefix
# ---------------------------------------------------------------------------
MCLASS = {}
for _m in list(METHODS):
    if _m.startswith('harmonic_'):
        MCLASS[_m] = 'harmonic_pattern'
    elif _m.startswith('candlestick_'):
        # assign by the pattern structure encoded in the id suffix
        if _m in ('candlestick_morning_star', 'candlestick_evening_star'):
            MCLASS[_m] = 'candlestick_three_line'
        elif any(_m.endswith(s) for s in ('_hammer','_hanging_man','_shooting_star',
            '_inverted_hammer','_doji','_long_legged_doji','_dragonfly_doji',
            '_gravestone_doji','_spinning_top','_star','_doji_star','_tweezer',
            '_one_day_reversal')):
            MCLASS[_m] = 'candlestick_single_line'
        elif any(_m.endswith(s) for s in ('_engulfing','_harami','_harami_cross',
            '_piercing','_dark_cloud_cover','_homing_pigeon','_descending_hawk',
            '_in_neck_line','_on_neck_line','_thrusting')):
            MCLASS[_m] = 'candlestick_two_line'
        else:
            MCLASS[_m] = 'candlestick_three_line'
    elif _m.startswith('chart_'):
        MCLASS[_m] = 'chart_pattern'
    elif _m.startswith('indicator_'):
        MCLASS[_m] = 'indicator_method'
    elif _m.startswith('pa_'):
        MCLASS[_m] = 'other'
    elif _m.startswith('level_'):
        MCLASS[_m] = 'level_method'
    elif _m.startswith('strategy_'):
        MCLASS[_m] = 'other'

# ---------------------------------------------------------------------------
def blob_of(x):
    parts = [x.get('exact_text', '')]
    parts += x.get('added_conditions', []) or []
    parts += [json.dumps(p) for p in (x.get('added_parameters', []) or [])]
    return ' '.join(parts)


def match_methods(x):
    """Return list of (mid, evidence_quote) for EVERY named method present in
    the record. A record may describe multiple named methods (e.g. an RSI BAMM
    Confirmation Point that completes with a Bearish Bat), so all matches are
    collected. Returns [] if the record is generic."""
    blob = blob_of(x)
    desc = ' '.join(x.get('added_conditions', []) or []) + ' ' + \
           json.dumps(x.get('added_parameters', []) or [])
    book = x['claim_ref'].split('::')[0]

    # Pass 1 — candidates: the method name appears anywhere in the record.
    cand = []
    for mid, m in METHODS.items():
        if m['only_books'] and book not in m['only_books']:
            continue
        for pat in m['patterns']:
            rx = re.compile(pat, re.I)
            mm = rx.search(blob)
            if not mm:
                continue
            if m['subject'] and not re.search(m['subject'], blob, re.I):
                continue
            cand.append((mid, m, rx, mm))
            break

    # Pass 2 — D1 (v2.2.3): distinguish DESCRIPTION from ENUMERATION.
    # A record that names many methods at once is a list/comparison, not a
    # corroboration of each (e.g. book_0052_2_034 names 6 candlestick shapes
    # while describing only bullish harami). A record that names one or two is
    # describing them. Binding to the describing content (added_conditions /
    # added_parameters) is the strong signal; when the name sits only in
    # exact_text, accept it only if the record is not an enumeration.
    #
    # This replaces the v2.2.2 desc-only gate, which over-pruned: it dropped
    # named harmonic concepts whose conditions describe the mechanism without
    # repeating the name ("The Failed Wave" / 1.13 extension, PRZ magnet
    # effect), costing 7 T1 records and all of book_0005.
    ENUM_LIMIT = 2
    hits = []
    for mid, m, rx, mm in cand:
        in_desc = bool(rx.search(desc)) and (
            not m['subject'] or bool(re.search(m['subject'], desc, re.I)))
        if in_desc or len(cand) <= ENUM_LIMIT:
            hits.append((mid, mm.group(0)))
    return hits

def main():
    data = json.load(open(INP))
    corr = data['corroborations']

    # index corroborations by list position (claim_ref is NOT unique)
    method_members = {}   # mid -> list of record indices
    assigned_idx = set()  # distinct records assigned to >=1 method
    for i, x in enumerate(corr):
        hits = match_methods(x)
        if hits:
            assigned_idx.add(i)
            for mid, quote in hits:
                method_members.setdefault(mid, []).append((i, x, quote))
    generic_count = len(corr) - len(assigned_idx)

    # build methods registry
    methods = []
    for mid in sorted(method_members):
        m = METHODS[mid]
        members = method_members[mid]
        # v2.2.3: the v2.2.2 post-filter (drop refs failing _t7_matches) was
        # REMOVED. It filtered by exactly T7's own criterion, so T7 passed by
        # construction (measured 562/562 = 100%) and stopped measuring
        # anything. Assignment precision is now decided in match_methods; T7
        # audits that decision on unfiltered output.
        if not members:
            continue
        # distinguishing parameters: union of added_parameters carrying page/claim_ref
        params = []
        seen = set()
        for _i, x, quote in members:
            for p in (x.get('added_parameters', []) or []):
                if not p.get('page') and not p.get('claim_ref'):
                    continue
                key = (p.get('name'), p.get('value'))
                if key in seen:
                    continue
                seen.add(key)
                entry = {'name': p['name'], 'value': p['value']}
                if p.get('page') is not None:
                    entry['page'] = p['page']
                if p.get('claim_ref'):
                    entry['claim_ref'] = p['claim_ref']
                params.append(entry)
        # distinguishing conditions — source conditions only (drop P4 gate/analyst notes)
        conds = []
        seen_c = set()
        _ANALYST = re.compile(r'(verdict\s*:|DIFFERS_FROM_REGISTRY|differs_from_registry|gated diff|gate diff|gate[- ]recorded|DIFF \(gate|\(matches gate|\(gate diff|\(gate-recorded)', re.I)
        for _i, x, quote in members:
            for c in (x.get('added_conditions', []) or []):
                if c in seen_c:
                    continue
                if _ANALYST.search(c):
                    continue
                seen_c.add(c)
                conds.append(c)
        books = sorted({x['claim_ref'].split('::')[0] for _i, x, _q in members})
        # KURAL 3 (ADIM 1b): a name-only mention does not create a
        # canonical_method — the method must carry at least one distinguishing
        # parameter or condition. Without one, the records stay generic and are
        # recorded as observed_name_mentions.
        if not params and not conds:
            assigned_idx.difference_update(i for i, x, _q in members)
            continue
        # parent = dominant behavior_id among the method's corroborations
        beh = Counter(x['behavior_id'] for _i, x, _q in members)
        parent = beh.most_common(1)[0][0]
        methods.append({
            'canonical_method_id': mid,
            'parent_behavior_id': parent,
            'method_class': MCLASS[mid],
            'method_name_in_source': m['name_in_source'],
            'name_provenance': 'SOURCE_EXPLICIT',
            'distinguishing_parameters': params,
            'distinguishing_conditions': conds,
            'supporting_claim_refs': [x['claim_ref'] for _i, x, _q in members],
            'book_ids': books,
            'book_count': len(books),
            'corroboration_count': len(members),
            'evidence_label': 'LITERATURE_SUPPORTED',
        })

    assigned = len(assigned_idx)
    # KURAL 3 pruning above removed name-only methods from assigned_idx;
    # recompute the generic (left-unassigned) count after pruning.
    generic_count = len(corr) - assigned
    # observed_name_mentions (KURAL 3): name mentions in records NOT assigned to any
    # method. These are passing mentions that do not (by themselves) create a method.
    observed = []
    seen_obs = set()
    for i, x in enumerate(corr):
        if i in assigned_idx:
            continue
        for mid, quote in match_methods(x):
            key = (mid, x['claim_ref'])
            if key in seen_obs:
                continue
            seen_obs.add(key)
            observed.append({
                'method_id': mid,
                'name_in_source': METHODS[mid]['name_in_source'],
                'claim_ref': x['claim_ref'],
                'page': x.get('page'),
                'behavior_id': x['behavior_id'],
            })
    observed.sort(key=lambda o: (o['method_id'], o['claim_ref']))
    out = {
        'pipeline_version': 'research_pipeline_v2.2',
        'schema_version': '2.2',
        'stage': 'P4_METHOD_PILOT',
        'input_corroborations': len(corr),
        'methods': methods,
        'observed_name_mentions': observed,
        'unassigned_count': 0,
        'counts': {
            'methods_total': len(methods),
            'corroborations_assigned': assigned,
            'corroborations_left_generic': generic_count,
            'books_covered': len({b for m in methods for b in m['book_ids']}),
        },
    }
    json.dump(out, open(OUT, 'w'), indent=2, ensure_ascii=False)
    print(f"methods_total: {len(methods)}")
    print(f"corroborations_assigned: {assigned}")
    print(f"corroborations_left_generic: {generic_count}")
    print(f"sum: {assigned + generic_count} (input {len(corr)})")
    print(f"books_covered: {out['counts']['books_covered']}")
    print("\n--- method inventory ---")
    for m in methods:
        print(f"  {m['canonical_method_id']:40s} n={m['corroboration_count']:3d} books={m['book_count']}")

if __name__ == '__main__':
    main()
