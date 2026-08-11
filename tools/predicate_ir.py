"""Declarative `still_valid` -> predicate IR compiler (PREDICATE_IR_SPEC).

The control plane compiles each Expert's post-entry thesis into an IR tree
before the compute plane runs, so the kernel evaluates data instead of
re-entering Python (no-callback invariant, D-078). The IR is emitted as
canonical JSON (sorted keys); the predicate's identity (`predicate_version`)
is the V8.2 bit-encoding of those bytes (PARITY_AND_IDENTITY_SPEC §4), so it
is runtime-independent.

Semantics are normative because they reproduce V8.0 exactly:
- fail-open on absence: a missing geometry key, an absent feature value, or a
  `None` reference yields `true` (thesis still valid — price governs);
- `FLIP_ON_SHORT` applies the comparison as written for LONG and with the
  operator reversed for SHORT;
- `Dispatch` is ordered, first match wins (mirrors `if 'x' in geom ...`);
- violation-form comparisons in the sources (`>=`/`<=` returning False) are
  lowered to their valid-form equivalents (`<`/`>`) — equivalent semantics;
- the IR vocabulary is closed (E5): the live features are the eleven declared
  names plus the parameterized window_high_/window_low_ channels.
"""
from __future__ import annotations

import json

# --- IR builders -------------------------------------------------------------

def _live(name: str) -> dict:
    return {"type": "live", "name": name}

def _ref(key: str) -> dict:
    return {"type": "ref", "key": key}

def _ref_dir(long_key: str, short_key: str) -> dict:
    return {"type": "ref_dir", "long_key": long_key, "short_key": short_key}

def _const(v: float) -> dict:
    return {"type": "const", "v": v}

def _live_window_dir(long_name: str, short_name: str, n_default: int,
                     n_ref: str | None = None) -> dict:
    out = {"type": "live_window_dir", "long": long_name, "short": short_name,
           "n_default": n_default}
    if n_ref is not None:
        out["n_ref"] = n_ref
    return out

def _window_agg(feature: str, n: int, agg: str, end: str = "INCLUSIVE") -> dict:
    return {"type": "window_agg", "feature": feature, "n": n, "agg": agg,
            "end": end}

def _window_agg_dir(long_feat: str, long_agg: str, short_feat: str,
                    short_agg: str, n: int, end: str = "EXCLUSIVE") -> dict:
    return {"type": "window_agg_dir",
            "long": {"feature": long_feat, "agg": long_agg},
            "short": {"feature": short_feat, "agg": short_agg},
            "n": n, "end": end}

def _mean_of2(a: dict, b: dict) -> dict:
    return {"type": "mean_of2", "a": a, "b": b}

def _compare(lhs, op: str, rhs, orient: str = "AS_WRITTEN") -> dict:
    return {"type": "compare", "lhs": lhs, "op": op, "rhs": rhs, "orient": orient}

def _asym(lhs, long_op: str, long_v: float, short_op: str, short_v: float) -> dict:
    return {"type": "asym_compare", "lhs": lhs,
            "long": {"op": long_op, "rhs": {"type": "const", "v": long_v}},
            "short": {"op": short_op, "rhs": {"type": "const", "v": short_v}}}

def _all(*rules) -> dict:
    return {"type": "all_of", "rules": list(rules)}

def _guard(operands, rule) -> dict:
    """Whole-condition fail-open: if ANY declared operand is absent, the rule
    yields true (the source returns True before the AND)."""
    return {"type": "guard", "operands": list(operands), "rule": rule}

def _dispatch(cases, default) -> dict:
    return {"type": "dispatch", "cases": cases, "default": default}

def _case(key: str, rule: dict, equals: str | None = None) -> dict:
    out = {"key": key, "rule": rule}
    if equals is not None:
        out["equals"] = equals
    return out


# --- expert rules (transcribed verbatim from src/v8/experts/*.py) ------------

# The dominant shape: close vs a frozen reference, LONG gt / SHORT lt.
def _close_vs_ref_dir(long_key: str, short_key: str) -> dict:
    return _compare(_live("close"), "GT", _ref_dir(long_key, short_key),
                    "FLIP_ON_SHORT")

def _close_vs_ref(key: str) -> dict:
    return _compare(_live("close"), "GT", _ref(key), "FLIP_ON_SHORT")


RULES = {
    "trend_pullback": _compare(_live("ema_fast"), "GT", _live("ema_slow")),
    "trend_pullback_depth": _guard(
        [_live("ema_fast"), _live("ema_slow"), _live("close"), _ref("prior_low_ref")],
        _all(
            _compare(_live("ema_fast"), "GT", _live("ema_slow")),
            _compare(_live("close"), "GT", _ref("prior_low_ref")),
        ),
    ),
    # SHORT-only family: close stays below the frozen (else live) prior high.
    "failed_breakout": _dispatch(
        [_case("prior_high_ref", _compare(_live("close"), "LT",
                                          _ref("prior_high_ref")))],
        default=_compare(_live("close"), "LT", _live("prior_high")),
    ),
    "failed_breakout_2b": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "breakout_retest": _close_vs_ref("level_ref"),
    "candlestick_reversal": _close_vs_ref("trigger_ref"),
    "liquidity_sweep_reclaim": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "fib_retracement_continuation": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "fib_projection_reversal": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "floor_trader_pivot": _close_vs_ref("level_ref"),
    "pattern_measuring_objective": _close_vs_ref("level_ref"),
    "range_breakout_1to1": _close_vs_ref("breakout_ref"),
    "volume_confirmed_breakout": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "volume_climax_reversal": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "obv_adl_regime": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "open_interest_divergence": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "funding_crowding_reversal": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "market_profile_value_area": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    "pandf_breakout": _close_vs_ref_dir("prior_low_ref", "prior_high_ref"),
    # The source returns True if EITHER gap ref is absent, independent of
    # direction — so both keys are guarded, not just the direction's.
    "gap_exhaustion": _guard(
        [_live("close"), _ref("gap_top_ref"), _ref("gap_bottom_ref")],
        _close_vs_ref_dir("gap_bottom_ref", "gap_top_ref"),
    ),
    "divergence_12_setups": _all(
        # Valid-form: LONG c > barrier (violation c <= barrier); SHORT flips.
        _compare(_live("close"), "GT", _ref("barrier_ref"), "FLIP_ON_SHORT"),
        _compare(_live("close"), "GT", _ref("extremum_ref"), "FLIP_ON_SHORT"),
    ),
    "macd_stoch_trend": _asym(_live("macd"), "GT", 0.0, "LT", 0.0),
    "rsi_stoch_reversion": _dispatch(
        [_case("variant", _asym(_live("rsi14"), "GT", 30.0, "LT", 70.0), equals="a"),
         _case("variant", _guard(
             [_live("rsi14"), _live("stoch_k")],
             _all(
                 _asym(_live("rsi14"), "GT", 30.0, "LT", 70.0),
                 _asym(_live("stoch_k"), "GT", 20.0, "LT", 80.0),
             ),
         ), equals="b")],
        default=_asym(_live("cci20"), "GT", -100.0, "LT", 100.0),
    ),
    "bollinger_breakout": _dispatch(
        # Setup 1 (1sd band present): premise is the frozen SMA (mid_ref).
        [_case("upper_1sd_ref", _close_vs_ref("mid_ref")),
         _case("lower_1sd_ref", _close_vs_ref("mid_ref"))],
        # Band-violation variants: LONG breaks above upper_2sd, SHORT below
        # lower_2sd; the thesis holds while close stays beyond the band.
        default=_compare(_live("close"), "GT",
                         _ref_dir("upper_2sd_ref", "lower_2sd_ref"),
                         "FLIP_ON_SHORT"),
    ),
    "bollinger_reversion": _guard(
        # The source checks close FIRST (fail open if absent) before the
        # variant dispatch — variant b reads ema_fast/ema_slow, not close, so
        # a close-absent input must still yield true.
        [_live("close")],
        _dispatch(
            [_case("variant", _compare(_live("ema_fast"), "GT", _live("ema_slow"),
                                       "FLIP_ON_SHORT"), equals="b")],
            # Setup 2 reversion: LONG holds while c > lower_3sd_ref, SHORT
            # while c < upper_3sd_ref (a close beyond the band is a trend, not
            # a reversion).
            default=_close_vs_ref_dir("lower_3sd_ref", "upper_3sd_ref"),
        ),
    ),
    # Violation forms differ per rule: the fib ref dies on c < ref (LONG), so
    # the valid form is c >= ref (GTE — the equality boundary holds); the 3sd
    # band dies on c <= ref3, so the valid form is c > ref3 (GT); the RSI dies
    # on re-entering the extreme zone (v <= 30 / v >= 70).
    "fib_rsi_bb_confluence": _all(
        _compare(_live("close"), "GTE",
                 _ref_dir("prior_low_ref", "prior_high_ref"), "FLIP_ON_SHORT"),
        _compare(_live("close"), "GT",
                 _ref_dir("lower_3sd_ref", "upper_3sd_ref"), "FLIP_ON_SHORT"),
        _asym(_live("rsi14"), "GT", 30.0, "LT", 70.0),
    ),
    "ichimoku_cloud": _compare(
        _live("close"), "GT",
        _mean_of2(_window_agg("high", 26, "MAX"),
                  _window_agg("low", 26, "MIN")),
        "FLIP_ON_SHORT"),
}


# donchian: exit_kind-dependent live channel / responsive band.
# channel exit: LONG c > window_low_{n}, SHORT c < window_high_{n}.
_DONCHIAN_CHANNEL = _compare(
    _live("close"), "GT",
    _live_window_dir("window_low", "window_high", n_default=20, n_ref="channel_n"),
    "FLIP_ON_SHORT")
# responsive (m=5) / significant-extreme (m=3): band over hist[-(m+1):-1].
_DONCHIAN_RESPONSIVE = _compare(
    _live("close"), "GT",
    _window_agg_dir("low", "MIN", "high", "MAX", n=6),
    "FLIP_ON_SHORT")
_DONCHIAN_SIGNIFICANT = _compare(
    _live("close"), "GT",
    _window_agg_dir("low", "MIN", "high", "MAX", n=4),
    "FLIP_ON_SHORT")

DONCHIAN_EXIT_KIND = {
    "channel": _DONCHIAN_CHANNEL,
    "responsive": _DONCHIAN_RESPONSIVE,
    "significant_extreme": _DONCHIAN_SIGNIFICANT,
}


def predicate_for(expert, geometry: dict | None = None) -> dict:
    """Compile one Expert's `still_valid` into the predicate IR.

    `geometry` is the candidate's frozen risk_geometry (used only to resolve
    expert-local mode dispatch; the IR itself is data, evaluated against the
    geometry at runtime). Raises for an Expert whose thesis cannot be
    compiled — fail CLOSED at compilation time, never silently fail-open
    (PREDICATE_IR_SPEC §5).
    """
    eid = expert.expert_id
    if eid == "donchian_breakout":
        kind = getattr(expert, "exit_kind", "channel")
        try:
            return DONCHIAN_EXIT_KIND[kind]
        except KeyError:
            raise ValueError(f"cannot compile {eid}: unknown exit_kind {kind!r}")
    try:
        return RULES[eid]
    except KeyError:
        raise ValueError(f"cannot compile {eid}: no still_valid IR registered")


def emit(ir: dict) -> str:
    """Canonical JSON (sorted keys) — the byte carrier whose V8.2 hash is the
    predicate identity."""
    return json.dumps(ir, sort_keys=True, separators=(",", ":"))
