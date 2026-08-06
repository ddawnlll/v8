"""Within-family multiplicity control for variant search (D-044).

Preregistration section 11 spends a family's Bonferroni-corrected alpha
budget on a single configuration when only one variant was evaluated, and
on a block-bootstrap Reality-Check max-statistic test (White 2000 Procedure
RC; `HYPOTHESIS_LAB_PROTOCOL.md` Sources) when more than one variant was
evaluated. All configurations passed to `reality_check_p_value` must fire on
the same setup predicate (same family) so their episode series are aligned
by index — this module does not attempt cross-family pooling (O-021).

No function here reads the wall clock; callers supply `seed` explicitly
(PERSISTENCE_REPLAY_SPEC section 4). Stdlib-only (`IMPLEMENTATION_LAYOUT.md`
section 3: the decision path never crosses the numpy boundary).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class EpisodeExposure:
    """One executed episode's net_R plus the exposure that produced it.

    Mirrors the fields `CounterfactualOutcome` records (D-045). `net_R` alone
    cannot be detrended: the benchmark must be expressed in the SAME R unit
    the simulator used, and that unit depends on the fill whenever a draft
    declares `risk_frac` instead of `atr_ref`.
    """
    net_r: float
    direction: str              # LONG | SHORT
    entry_price: float
    risk_unit_price: float      # price distance of one R at the entry fill
    horizon_bars: int


def mean_log_drift_per_bar(closes: Sequence[float]) -> float:
    """Mean per-bar log price change of the evaluation window.

    Aronson uses logs of price ratios so the benchmark subtracts symmetrically
    for LONG and SHORT (Ch1 p28-29): in simple returns a +10% and a -10% move
    are not mirror images, so a raw-return benchmark would penalise one
    direction more than the other and reintroduce the very position bias it is
    meant to remove.

    This is the sample mean of the SAME window the test is run on — Appendix A
    defines detrending as centering raw returns by their own sample mean. A
    drift imported from another window would be an estimate, not a centering,
    and would leave the null mis-centered by the difference.
    """
    if len(closes) < 2:
        return 0.0
    steps = []
    for prev, cur in zip(closes, closes[1:]):
        if prev <= 0 or cur <= 0:
            raise ValueError(
                f'non-positive close in the drift window ({prev!r} -> {cur!r}): '
                'a log ratio is undefined; fail closed rather than skipping bars')
        steps.append(math.log(cur / prev))
    return sum(steps) / len(steps)


def passive_benchmark_r(exposure: EpisodeExposure, mean_log_drift: float) -> float:
    """The same-exposure placebo benchmark for one episode, in R.

    Aronson Appendix A proves detrending is equivalent to subtracting a
    benchmark with the SAME position bias and no predictive power
    (`Corrected = Σ_long(R_i − E[Raw]) − Σ_short(R_i − E[Raw])`). The V8
    reading of that: an episode that held `direction` for `horizon_bars` with
    zero skill still collects the window's drift over those bars, scaled into
    the episode's own R unit.

    Costs are deliberately NOT subtracted here. The benchmark is what the
    market handed a zero-skill position; the rule's own `net_R` already pays
    cost and funding, so the difference is "skill after cost", which is the
    quantity preregistration section 10 claims to measure.
    """
    if exposure.direction == 'LONG':
        sign = 1.0
    elif exposure.direction == 'SHORT':
        sign = -1.0
    else:
        raise ValueError(
            f'direction must be LONG or SHORT (got {exposure.direction!r}); a '
            'benchmark with an unknown position bias cannot be centered')
    if not exposure.risk_unit_price > 0:
        raise ValueError(
            f'risk_unit_price must be > 0 (got {exposure.risk_unit_price!r}): '
            'an episode with no recorded R unit cannot be detrended — fail '
            'closed rather than passing its raw net_R through uncentered')
    if exposure.horizon_bars <= 0:
        return 0.0
    drift_move = exposure.entry_price * (
        math.exp(mean_log_drift * exposure.horizon_bars) - 1.0)
    return sign * drift_move / exposure.risk_unit_price


def detrend_net_r(exposures: Sequence[EpisodeExposure],
                  mean_log_drift: float) -> list[float]:
    """Episode net_R re-centered on the same-exposure passive benchmark.

    This is the series preregistration section 11's tests run on. The
    undetrended series stays available as a diagnostic, and — critically —
    signal GENERATION never sees this: Aronson is explicit that detrended data
    is used only for return calculation, never to produce the positions
    (Ch1 p27-28). Nothing here touches `MarketState` or an Expert.
    """
    return [e.net_r - passive_benchmark_r(e, mean_log_drift) for e in exposures]


def placebo_exposures(closes: Sequence[float], *, long_share: float,
                      horizon_bars: int, risk_unit_frac: float,
                      n_episodes: int, seed: int) -> list[EpisodeExposure]:
    """A zero-skill placebo family with a declared long/short occupancy.

    The Appendix A empirical check (EV_METHODS G-02): entries are drawn
    uniformly at random and directions by a biased coin, so the family has NO
    predictive power by construction. Its `net_R` is the passive move it
    happened to hold — no barriers, no cost — which is exactly the quantity
    Aronson shows is positive for a long-biased rule on a trending tape
    (90%-long earns 7.31%/yr vs 60%-long 1.78%/yr on 1976-2004 S&P, with zero
    skill in both).

    The R unit is a FRACTION of the entry price, not an absolute price
    distance — the `risk_frac` path `simulator.risk_unit` already supports. An
    absolute unit is only meaningful while the price level is roughly
    constant: over a window that multiplies price several-fold, late episodes
    would carry many times the R of early ones and the placebo mean would be
    dominated by whichever end of the window it happened to sample. A
    proportional unit keeps every episode's net_R on one scale, which is what
    makes the invariant window-length independent.

    Deterministic for a fixed seed; the caller supplies it (never the wall
    clock, PERSISTENCE_REPLAY_SPEC section 4).
    """
    if not 0.0 <= long_share <= 1.0:
        raise ValueError(f'long_share must be in [0, 1] (got {long_share!r})')
    if horizon_bars <= 0:
        raise ValueError(f'horizon_bars must be positive (got {horizon_bars!r})')
    if not risk_unit_frac > 0:
        raise ValueError(
            f'risk_unit_frac must be > 0 (got {risk_unit_frac!r})')
    last_entry = len(closes) - horizon_bars - 1
    if last_entry < 0:
        raise ValueError(
            f'window of {len(closes)} closes is shorter than horizon_bars '
            f'{horizon_bars}: no placebo episode can complete')
    rng = random.Random(seed)
    out: list[EpisodeExposure] = []
    for _ in range(n_episodes):
        i = rng.randrange(last_entry + 1)
        direction = 'LONG' if rng.random() < long_share else 'SHORT'
        sign = 1.0 if direction == 'LONG' else -1.0
        entry = float(closes[i])
        exit_close = float(closes[i + horizon_bars])
        unit = entry * risk_unit_frac
        out.append(EpisodeExposure(
            net_r=sign * (exit_close - entry) / unit,
            direction=direction, entry_price=entry,
            risk_unit_price=unit, horizon_bars=horizon_bars))
    return out


@dataclass(frozen=True)
class InvariantCheck:
    """Result of the Appendix A placebo check on one evaluation window."""
    placebo_mean_raw: float         # zero-skill family's mean net_R, uncentered
    placebo_mean_detrended: float   # ... after subtracting its own benchmark
    long_share: float
    horizon_bars: int
    n_episodes: int
    seed: int
    holds: bool


def appendix_a_invariant(closes: Sequence[float], *, long_share: float,
                         horizon_bars: int, risk_unit_frac: float,
                         n_episodes: int, seed: int) -> InvariantCheck:
    """Run the placebo family and report whether detrending neutralised it.

    `holds` is decided by `invariant_holds` below.
    """
    drift = mean_log_drift_per_bar(closes)
    placebo = placebo_exposures(closes, long_share=long_share,
                                horizon_bars=horizon_bars,
                                risk_unit_frac=risk_unit_frac,
                                n_episodes=n_episodes, seed=seed)
    raw = sum(e.net_r for e in placebo) / len(placebo)
    detrended_series = detrend_net_r(placebo, drift)
    detrended = sum(detrended_series) / len(detrended_series)
    return InvariantCheck(
        placebo_mean_raw=raw, placebo_mean_detrended=detrended,
        long_share=long_share, horizon_bars=horizon_bars,
        n_episodes=n_episodes, seed=seed,
        holds=invariant_holds(raw, detrended))


# METH-1 (EV_METHODS G-02) frozen tolerance for Aronson's Appendix A placebo
# invariant. This is a preregistration choice (prereg §16 freezes it once the
# holdout opens) and is therefore a declared constant here, never fitted:
#   * RELATIVE reading — centering must remove at least 75% of the measured
#     position bias (|detrended| <= 0.25 * |raw|). Scales with how much bias
#     there actually was, which is the honest "did the benchmark absorb the
#     bias" question.
#   * When `raw` is already ~0 (a driftless window), the relative test has no
#     denominator, so the rule falls back to an absolute R floor small enough
#     that a working centering clears it comfortably.
INVARIANT_RELATIVE_FRACTION = 0.25      # |detrended| <= 0.25 * |raw|
INVARIANT_ABSOLUTE_FLOOR_R = 0.02       # fallback when |raw| ~ 0
INVARIANT_RAW_EPSILON_R = 0.01          # |raw| below this is "no bias measured"


def invariant_holds(placebo_mean_raw: float,
                    placebo_mean_detrended: float) -> bool:
    """Does the detrended placebo satisfy Aronson's "expected net_R ≈ 0"?

    Aronson states the invariant qualitatively (Ch1 p23-28, Appendix A p475-476;
    "expected net_R ≈ 0" has no number in the book), so the tolerance is a V8
    preregistration choice and belongs here as one auditable, frozen rule
    rather than an inline constant at the call site.

    FROZEN RULE (METH-1, EV_METHODS G-02, prereg §9/§11/§16): the RELATIVE
    reading — centering removed most of the measured bias:
        holds = |detrended| <= 0.25 * |raw|
    with an absolute fallback when the window measured no bias at all
    (|raw| < 0.01 -> require |detrended| <= 0.02 R). Constants are declared
    above and never fitted.

    Residual bias is expected even when this is working correctly: the
    benchmark uses `exp(μ·h)` while a realised path is `exp(Σ steps)`, and by
    Jensen's inequality the noisy realisation sits slightly above it. So the
    honest target is "small", never "exactly zero" — that is what the 25%
    relative tolerance encodes.
    """
    if abs(placebo_mean_raw) < INVARIANT_RAW_EPSILON_R:
        return abs(placebo_mean_detrended) <= INVARIANT_ABSOLUTE_FLOOR_R
    return abs(placebo_mean_detrended) <= INVARIANT_RELATIVE_FRACTION * abs(
        placebo_mean_raw)


def select_block_size(episode_net_r: Sequence[float], small: int = 24,
                       large: int = 168, threshold: float = 0.10) -> int:
    """Preregistration section 9's mechanical block-size rule: lag-1
    autocorrelation of episode `net_R` picks 24 (one day) or 168 (one week).
    Fixed thresholds, not a free parameter — mirrors the prose rule exactly.
    """
    n = len(episode_net_r)
    if n < 3:
        return small
    mean = sum(episode_net_r) / n
    c0 = sum((x - mean) ** 2 for x in episode_net_r)
    if c0 == 0:
        return small
    c1 = sum((episode_net_r[i] - mean) * (episode_net_r[i + 1] - mean)
              for i in range(n - 1))
    lag1 = c1 / c0
    return large if abs(lag1) > threshold else small


def _block_bootstrap_indices(n: int, block_size: int, rng: random.Random) -> list[int]:
    """One circular fixed-block bootstrap draw of length n over [0, n):
    repeatedly picks a uniform start point and appends a contiguous run of
    `block_size` indices (wrapping past the end), until length n is reached,
    then truncates. Contiguous within a block, independent across blocks —
    the same episode-block dependence unit as preregistration section 9.
    """
    if n <= 0:
        return []
    if block_size <= 0:
        raise ValueError('block_size must be positive')
    out: list[int] = []
    while len(out) < n:
        start = rng.randrange(n)
        out.extend((start + j) % n for j in range(block_size))
    return out[:n]


@dataclass(frozen=True)
class RealityCheckResult:
    """Output of `reality_check_p_value`. `argmax_config` is the only
    configuration that can pass preregistration section 11's within-family
    test on this record; every other evaluated configuration fails by
    construction of the max statistic, regardless of its own mean."""
    observed_max: float
    argmax_config: str
    p_value: float
    n_resamples: int
    block_size: int
    seed: int


def reality_check_p_value(
    episode_net_r: Mapping[str, Sequence[float]],
    block_size: int,
    n_resamples: int,
    seed: int,
) -> RealityCheckResult:
    """White (2000) Procedure RC max-statistic bootstrap p-value, extended
    to N within-family configurations (D-044).

    `episode_net_r` maps each evaluated `variant_id` to its ordered episode
    `net_R` series. All series must share the same length and episode order
    — true within one family because every variant fires on the same setup
    predicate (rule 13), so the episode grid is identical across variants;
    this is what lets a single per-round block draw be applied identically
    to every series, preserving whatever correlation the shared episodes
    carry instead of assuming independence.

    Each bootstrap round recenters every configuration's resampled mean on
    its own observed mean (imposing the null that no configuration beats
    its own realized performance by more than resampling noise would), then
    takes the max recentered statistic across configurations. The p-value is
    the fraction of resampled max statistics that reach or exceed the
    observed max of the raw (non-recentered) means — the compound null this
    tests is "no evaluated configuration's true mean exceeds 0 by more than
    search-induced noise explains," which is what preregistration section 11
    needs in place of "family-level control: variants count as one unit."

    METH-1 (EV_METHODS G-02) centering contract: this function EXPECTS the
    D-045 pre-centered series. Position-bias centering (Aronson Appendix A
    detrending, `detrend_net_r`) is the CALLER's job and is never applied
    inside — the only recentering here is the WRC compound-null recentering,
    which imposes the max-of-family null, not the position-bias null. Passing
    raw net_R straight off a trending tape would leave the test mis-centered
    (G-02), so a caller that has not yet centered must call `detrend_net_r`
    first; this function will not guess.
    """
    configs = list(episode_net_r)
    if not configs:
        raise ValueError('no configurations supplied')
    lengths = {len(v) for v in episode_net_r.values()}
    if len(lengths) != 1:
        raise ValueError(
            'all configuration episode series must share length (aligned by '
            'episode index) — cross-family series are not aligned; see O-021')
    n = lengths.pop()
    if n == 0:
        raise ValueError('empty episode series')
    if n_resamples <= 0:
        raise ValueError('n_resamples must be positive')

    means = {c: sum(episode_net_r[c]) / n for c in configs}
    observed_max = max(means.values())
    argmax_config = max(means, key=means.__getitem__)

    rng = random.Random(seed)
    exceed = 0
    for _ in range(n_resamples):
        idx = _block_bootstrap_indices(n, block_size, rng)
        round_max = max(
            sum(episode_net_r[c][i] for i in idx) / n - means[c]
            for c in configs
        )
        if round_max >= observed_max:
            exceed += 1
    p_value = exceed / n_resamples

    return RealityCheckResult(
        observed_max=observed_max,
        argmax_config=argmax_config,
        p_value=p_value,
        n_resamples=n_resamples,
        block_size=block_size,
        seed=seed,
    )


def block_bootstrap_means(net_rs: Sequence[float], block_size: int,
                          n_resamples: int, seed: int) -> list[float]:
    """The section-9 circular fixed-block bootstrap resample means.

    One rng from `seed` drives every resample; each resample is a length-n
    draw from `_block_bootstrap_indices` (contiguous within a block, wrapping
    past the end — the SAME sampler `reality_check_p_value` uses). This is the
    one block sampler of record (METH-4 / EV_METHODS E-04): the single-config
    percentile test and the WRC must resample identically, and `run_experiment`
    is wired to this function rather than keeping a second, non-circular
    sampler. Bootstrap theorem: resample size = original n (Aronson Ch5
    p234-238).
    """
    n = len(net_rs)
    if n == 0:
        return []
    if n_resamples <= 0:
        raise ValueError('n_resamples must be positive')
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(n_resamples):
        idx = _block_bootstrap_indices(n, block_size, rng)
        means.append(sum(net_rs[i] for i in idx) / n)
    return means


def bootstrap_ci(net_r_series: Sequence[float], block_size: int,
                 n_resamples: int, seed: int,
                 ci: float = 0.90) -> tuple[float, float]:
    """Bootstrap percentile confidence interval on mean episode net_R.

    METH-4 / EV_METHODS E-01, grounded in Aronson Ch5 p245-253 (percentile
    method; "remove top x% and bottom x%"): circular fixed-block bootstrap
    (reuse `block_bootstrap_means`), resample size = n (bootstrap theorem,
    Ch5 p234-238), mean per resample, sort; `tail = int(n_resamples*(1-ci)/2)`;
    `lower = means[tail]`, `upper = means[-tail-1]`. For ci=0.90, B=5000 that
    drops 250 per tail (the book's own numbers).

    V8 grounding: prereg §11 pairs an interval estimate with every hypothesis
    test; the single-config gate already computes the 2.5th-percentile bound —
    this is the same resample loop generalised to both tails. `block_size`
    must respect the E-04 rule (>= max episode hold); callers with an explicit
    dependence length pass it explicitly. An empty series returns (0.0, 0.0).
    """
    if not 0.0 < ci < 1.0:
        raise ValueError(f'ci must be in (0, 1) (got {ci!r})')
    means = block_bootstrap_means(net_r_series, block_size, n_resamples, seed)
    if not means:
        return (0.0, 0.0)
    means.sort()
    tail = int(n_resamples * (1.0 - ci) / 2.0)
    return (means[tail], means[-tail - 1])


def effective_independent_episodes(n_episodes: int,
                                   max_hold_bars: int) -> float:
    """Effective number of independent episodes under overlap.

    METH-4 / EV_METHODS E-04, grounded in Aronson Ch7 n43 p504 ("multiperiod
    horizons reduce the number of independent observations... block length
    must be at least the episode hold"): with overlapping episodes (target /
    stop / expiry lengths vary), the effective sample is `n / block_size`, and
    because the block size must be >= the longest hold (a resampled block must
    never split within-episode dependence), `n / max_hold_bars` is the
    conservative upper bound on independent observations. Report it beside
    every family statistic so a 200-episode family with an 8-bar hold is read
    as at most ~25 independent blocks, not 200.

    V8 grounding: prereg §9 (episode is the dependence unit; block bootstrap).
    """
    if n_episodes < 0:
        raise ValueError(f'n_episodes must be >= 0 (got {n_episodes!r})')
    if max_hold_bars <= 0:
        raise ValueError(f'max_hold_bars must be positive (got {max_hold_bars!r})')
    if n_episodes == 0:
        return 0.0
    return n_episodes / max_hold_bars


@dataclass(frozen=True)
class PermutationRealityCheckResult:
    """Output of `monte_carlo_permutation_p_value` (METH-3 / EV_METHODS E-02).
    `argmax_config` is the only configuration whose observed performance the
    null is judged against, mirroring `RealityCheckResult`."""
    observed_max: float
    argmax_config: str
    p_value: float
    n_permutations: int
    seed: int


def monte_carlo_permutation_p_value(
    episode_moves: Sequence[float],
    episode_directions: Mapping[str, Sequence[int]],
    episode_net_r: Mapping[str, Sequence[float]],
    n_permutations: int,
    seed: int,
) -> PermutationRealityCheckResult:
    """Monte-Carlo permutation Reality-Check p-value (Masters' method).

    METH-3 / EV_METHODS E-02, grounded in Aronson Ch5 p239-240, Ch6 p327-328,
    Ch9 p442: the signal-content null — "the rules' long/short positions are
    randomly paired with the market's one-day-forward price change". The WRC
    tests the return null (all rules have expected return <= 0); this engine
    tests whether the observed best-of-family mean could arise from randomly
    re-pairing each episode's DIRECTION with the market's move. The book runs
    BOTH engines and expects agreement on detrended data (Ch5 p235) — this is
    the cross-check for every family verdict (G-03).

    Mechanics (all stdlib, seed-explicit):
      * `episode_moves` is the SHARED, direction-free per-episode market move
        (`CounterfactualOutcome.market_move_r`, D-045), aligned by episode
        index across every variant.
      * `episode_directions` maps each evaluated variant to its per-episode
        direction (+1 LONG, -1 SHORT).
      * `episode_net_r` maps each variant to its per-episode net_R. The
        OBSERVED statistic is `max_c mean(net_r[c])` — the SAME quantity the
        WRC observes, so the two engines cross-check the same number.
      * Each round draws ONE permutation pi of {0..n-1} without replacement
        (Fisher-Yates, `random.sample`) and applies it to every variant
        (`mean_c = (1/n) sum_e direction_c[pi(e)] * episode_moves[e]`),
        preserving cross-configuration correlation by construction; the round
        statistic is the max over configurations. No recentering — the null is
        "randomly correlated with future market behavior", which is what
        destroys the signal while keeping the correlation structure.
      * `p = #{rounds: round_stat >= observed_max} / n_permutations`.

    Scale note: permuted means are centered on `direction x move`, while the
    observed net_R already pays cost and funding. On a no-edge family the
    permuted null therefore sits slightly ABOVE the observed statistic, so the
    test is conservative (biased toward non-rejection) — a documented
    asymmetry, not a silent permissiveness.

    V8 grounding: prereg §11 (within-family multiplicity control). The
    `market_move_r` field exists precisely so this test does not force a
    second simulator hash bump (D-045).
    """
    configs = list(episode_net_r)
    if not configs:
        raise ValueError('no configurations supplied')
    if set(episode_directions) != set(episode_net_r):
        raise ValueError(
            'episode_directions and episode_net_r must cover the same variants')
    n = len(episode_moves)
    if n == 0:
        raise ValueError('empty episode series')
    lengths = {len(v) for v in episode_net_r.values()}
    lengths.update(len(v) for v in episode_directions.values())
    lengths.add(n)
    if len(lengths) != 1:
        raise ValueError(
            'episode_moves, every direction series and every net_R series must '
            'share length (aligned by episode index — the D-045 grid)')
    for c in configs:
        if any(d not in (1, -1) for d in episode_directions[c]):
            raise ValueError(
                f'{c}: directions must be +1 (LONG) or -1 (SHORT), got '
                f'{sorted(set(episode_directions[c]))}')
    if n_permutations <= 0:
        raise ValueError('n_permutations must be positive')

    means = {c: sum(episode_net_r[c]) / n for c in configs}
    observed_max = max(means.values())
    argmax_config = max(means, key=means.__getitem__)

    rng = random.Random(seed)
    exceed = 0
    for _ in range(n_permutations):
        perm = rng.sample(range(n), n)   # one pi for every variant
        round_max = max(
            sum(episode_directions[c][perm[e]] * episode_moves[e]
                for e in range(n)) / n
            for c in configs
        )
        if round_max >= observed_max:
            exceed += 1
    p_value = exceed / n_permutations

    return PermutationRealityCheckResult(
        observed_max=observed_max,
        argmax_config=argmax_config,
        p_value=p_value,
        n_permutations=n_permutations,
        seed=seed,
    )


@dataclass(frozen=True)
class RegimeSlice:
    """One consecutive window of the episode net_R series (METH-5 / G-06)."""
    start_idx: int          # inclusive
    end_idx: int            # exclusive
    n: int
    mean_net_r: float


def regime_slices(episode_net_r: Sequence[float],
                  slice_bars: int) -> list[RegimeSlice]:
    """Per-slice mean net_R strata over the ordered episode series.

    METH-5 / EV_METHODS G-06, grounded in Aronson Ch3 p123-124 (long/flat
    rules in a rising market show profit with zero predictive power), Ch7
    p352/355 (per-regime evaluation): split the episode series into consecutive
    non-overlapping windows of `slice_bars` episodes and report each window's
    mean. A positive pooled mean concentrated in one window is a regime
    artifact and is indistinguishable from a broad edge by the pooled
    statistic alone — the strata make the concentration visible.

    V8 grounding: prereg §13 (single chronological holdout) — this is the
    report-side decay/regime surface. Report-only; never a gate.
    """
    if slice_bars <= 0:
        raise ValueError(f'slice_bars must be positive (got {slice_bars!r})')
    out: list[RegimeSlice] = []
    for start in range(0, len(episode_net_r), slice_bars):
        chunk = episode_net_r[start:start + slice_bars]
        out.append(RegimeSlice(start_idx=start, end_idx=start + len(chunk),
                               n=len(chunk),
                               mean_net_r=sum(chunk) / len(chunk)))
    return out


@dataclass(frozen=True)
class StreakVsNullResult:
    """Observed best-of-family winning streak vs the no-edge bootstrap null
    (METH-5 / EV_METHODS G-08)."""
    observed_streak: int
    p_value: float
    null_best_streaks: tuple[int, ...]   # longest positive run per resample
    block_size: int
    n_resamples: int
    seed: int


def _longest_positive_run(xs: Sequence[float]) -> int:
    best = cur = 0
    for x in xs:
        if x > 0.0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def streak_vs_null(episode_net_r: Sequence[float], block_size: int,
                   n_resamples: int, seed: int) -> StreakVsNullResult:
    """Observed streak of profitable episodes vs the no-edge bootstrap null.

    METH-5 / EV_METHODS G-08, grounded in Aronson/Taleb (10,000 dart-throwing
    managers: ~312 beat the market 5 years running by chance; the clustering
    illusion misreads random streaks as trends): a reported winning streak
    (consecutive positive episode net_R) is not calibrated unless compared to
    the chance distribution of best-of-family streaks under the no-edge null.

    The no-edge null is imposed by zero-centering the series (E-03: x'_i =
    x_i - mean(x)) before circular block resampling (same §9 block-size rule /
    sampler as the WRC); each resample contributes its longest run of positive
    values, and `p` is the fraction of null streaks at least as long as the
    observed one. Report-only — never a gate (prereg §11).

    V8 grounding: prereg §9 (block bootstrap), §16 (deterministic, seeded).
    """
    if not episode_net_r:
        raise ValueError('empty episode series')
    if n_resamples <= 0:
        raise ValueError('n_resamples must be positive')
    observed = _longest_positive_run(episode_net_r)
    n = len(episode_net_r)
    mu = sum(episode_net_r) / n
    centered = [x - mu for x in episode_net_r]
    rng = random.Random(seed)
    nulls: list[int] = []
    for _ in range(n_resamples):
        idx = _block_bootstrap_indices(n, block_size, rng)
        nulls.append(_longest_positive_run([centered[i] for i in idx]))
    p_value = sum(1 for s in nulls if s >= observed) / n_resamples
    return StreakVsNullResult(observed_streak=observed, p_value=p_value,
                              null_best_streaks=tuple(nulls),
                              block_size=block_size, n_resamples=n_resamples,
                              seed=seed)


def practical_significance(net_r: Sequence[float], min_net_r: float,
                           min_trades: int) -> tuple[bool, str]:
    """Statistical significance is not practical significance.

    METH-5 / EV_METHODS G-12, grounded in Aronson Ch8 p394 (with 6,000+ days
    statistical significance is trivially achievable; a rule can be
    significant yet practically negligible) and Ch9 p443: the composite
    verdict must gate on an ECONOMIC magnitude on top of p < alpha. This
    helper applies the economic-magnitude gate `mean(net_R) >= min_net_r` AND
    the coverage gate `n >= min_trades`, and returns `(meets, note)` where the
    note states both observed values so the verdict is auditable.

    V8 grounding: prereg §11 (family gate is statistical), §12 (minimum
    coverage). Report-only — a note for the authority-receipt verdict path,
    never a hard fail.
    """
    if not min_net_r > 0:
        raise ValueError(f'min_net_r must be > 0 (got {min_net_r!r})')
    if min_trades <= 0:
        raise ValueError(f'min_trades must be positive (got {min_trades!r})')
    n = len(net_r)
    mean = (sum(net_r) / n) if n else 0.0
    meets = n >= min_trades and mean >= min_net_r
    note = (
        f'mean net_R {mean:.4f} vs economic floor {min_net_r} '
        f'({"meets" if mean >= min_net_r else "below"}); '
        f'episodes {n} vs minimum coverage {min_trades} '
        f'({"meets" if n >= min_trades else "below"})'
    )
    return meets, note


def expected_false_positives(n_rules: int, alpha: float) -> float:
    """Expected false positives under the null: N rules at alpha -> N*alpha.

    METH-6 / EV_METHODS E-05, grounded in Aronson Ch9 p443: of 6,402 rules at
    0.05, ~320 significant by chance — exactly 6,402 * 0.05 = 320.1. A count
    near expectation is evidence of NO edge. Report it beside the observed
    count of significant variants per family and as a program-level sum (G-11).

    V8 grounding: prereg §11 (family-corrected alpha_f = 0.025; the case-study
    calibration is the prior: the best rule's naive p = 0.0005 collapsed to
    WRC/MCP p ~ 0.82 after adjustment — zero rules survived).
    """
    if n_rules < 0:
        raise ValueError(f'n_rules must be >= 0 (got {n_rules!r})')
    if not 0.0 < alpha < 1.0:
        raise ValueError(f'alpha must be in (0, 1) (got {alpha!r})')
    return n_rules * alpha


def effective_search_size(variants_evaluated: int,
                          search_universe_size: int) -> int:
    """The honest family size for multiplicity-sensitive report lines (D-046).

    METH-2 / EV_METHODS G-01, grounded in Aronson Ch6 p255-330 and Ch8 p390-391
    (data-mining bias is a function of the TOTAL search extent — every
    parameter grid, indicator variant, and loser tried en route, not just the
    retained variants). How D-046 `search_universe_size` enters V8's
    multiplicity correction, documented:

      * Bonferroni across families uses the FAMILY COUNT (F = 2 -> alpha_f =
        0.025) — the only cross-family error-rate procedure (prereg §11).
      * Within-family Reality-Check max-stat uses `len(variants_evaluated)`
        (D-044) — the configurations whose aligned series are actually tested.
      * `search_universe_size` is the TOTAL configurations the search consumed
        (D-046, registry-enforced >= variants_evaluated). It is RECORDED and
        REPORTED alongside the p-value (never silently folded into the RC
        count, which would be a different test).

    `effective_search_size` returns `max(variants_evaluated,
    search_universe_size)` so the reported size can never understate the
    declared search; when the two differ the within-family control saw only
    part of the search and the p-value is optimistic by that margin — the
    caller surfaces `multiplicity_undercounted` so the optimism is visible.
    """
    if not isinstance(variants_evaluated, int) or isinstance(variants_evaluated, bool) \
            or variants_evaluated < 0:
        raise ValueError(
            f'variants_evaluated must be a non-negative int (got '
            f'{variants_evaluated!r})')
    if not isinstance(search_universe_size, int) or isinstance(search_universe_size, bool) \
            or search_universe_size < 0:
        raise ValueError(
            f'search_universe_size must be a non-negative int (got '
            f'{search_universe_size!r})')
    if search_universe_size < variants_evaluated:
        raise ValueError(
            f'search_universe_size {search_universe_size} < variants_evaluated '
            f'{variants_evaluated}: the declared search cannot be smaller than '
            'what it retained (D-046)')
    return max(variants_evaluated, search_universe_size)
