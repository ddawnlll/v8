# V8-next full economic port

Owner scope: “hepsini ekle o zaman”. This extends the first-slice acceptance;
that acceptance does not establish completion of the full economic product.
Legacy code is reference only, never a runtime dependency. No real-money
activation is authorized. No feature parity with legacy infrastructure is needed.

## Completion requirements

All active expert families and economically relevant variants require executable
observations, causal feature/data coverage, opportunity binding and meaningful
behavior tests. A registry entry alone is not a port. Preserve opportunity types,
habitat/regime semantics, witness reconciliation, real outcome calibration,
allocation across opportunities, multi-instrument exposure, campaign management,
continuous market input and auxiliary expert data. Qualify fee/funding accounting,
position-bearing continuation, restart/reconnect and operational telemetry.
Preserve benchmark tables/scorecards/gates, WRC/DSR/PBO/SPA methodology,
search-family accounting and protected OOS discipline. Demonstrate prospective
paper observations and qualified execution behavior without fabricated edge or
forced trades. Missing data must remain absent and claims gated.

Nautilus owns execution infrastructure. Scientific libraries own supported
numerical procedures. V8 owns null definitions, causal alignment, economic policy
and authority boundaries. Do not implement another engine, OMS or scheduler.

## Expert migration evidence

Donchian E-10 active Rust VERSION=v1 is long-only, variant a, with a preceding
20-bar high channel. `experts/donchian.py` preserves that observation and maps it
to support/contradiction on a pre-existing opportunity. Complete windows and
continuous inputs are mandatory. ATR and channel stop/target/expiry geometry
belong to a separate economic campaign policy, not observer authority. That
campaign policy is still outstanding; this is not full Donchian capability parity.
The inactive non-v1 Rust branch is not silently made an active variant.

The legacy witness adapter's fixed confidence, uncertainty and expected-edge
fallbacks are not calibrated estimates and must not migrate. Directional evidence
is retained without manufacturing economic strength. The initial paper comparison
remains explicitly frozen to squeeze/breakout until expanded trial identity,
configuration and report wiring is implemented; no silent policy change.

Remaining requirements above are open until implementation and integrated evidence
prove each one. The previous first-slice's no-trade acceptance is insufficient.

## Reversion observations and executable catalog

`experts/reversion.py` implements the active Rust v1/a Bollinger reversion
and RSI/stochastic reversion observations. Bollinger uses the trailing 20-close
population deviation: the two-sigma threshold is inclusive, three-sigma is
exclusive. Variant a does not use EMA direction; those unused legacy operands
are not prerequisites for this observation. Degenerate bands abstain. RSI uses
14 price changes for the initial arithmetic-mean gain/loss seed followed by
Wilder smoothing through Polars. A recovery from <=30 or >=70 requires a later
close through the recovered run's first candle high/low. Merely crossing the RSI
threshold is not a trigger. Flat RSI is 50 under the declared source convention.
No stochastic variant is claimed implemented by this RSI-only active version.

The executable catalog contains four observed families including initial squeeze.
Historical native callbacks include all four as `expert_diagnostics`; the frozen
squeeze admission/comparison remains unchanged. These diagnostics do not become
a new allocation policy or statistical search family without explicit experiment
registration. Current opportunity grammar still limits which episodes can be
observed; richer opportunity generation and campaign geometry remain outstanding.

Tests exercise band boundaries, both observed directions, recovery-bar ordering,
RSI seed/recurrence, warmup, gap/instrument rejection and future-prefix invariance
through native bar callbacks. No claim of full four-family economic parity follows.

## Failed and volume-confirmed breakout observations

The executable catalog now also includes `failed_breakout` and
`volume_confirmed_breakout`, both active Rust v1 semantics. Failed breakout
uses the newest close above the maximum preceding high in the supplied history,
freezes that preceding high, and observes SHORT only on a strict return below
it within five bars. A newer breakout replaces the reference. This window-relative
hypothesis needs a frozen history policy in any future deployment configuration.

Volume-confirmed breakout uses the preceding 20-bar price channel, the current-
inclusive 20-bar volume mean, and optional current-inclusive 100-bar population
z-score/min-max proximity, as defined in Rust state.rs. Priority is d (>=2x mean
and z<2), c (>=1.2x), b (>mean and proximity<0.4), then a (>mean). Missing or
zero-dispersion optional statistics remain absent, never fabricated z/proximity.
The other branches remain available when their own operands suffice. Unselected
variants are explicitly UNRESOLVED. Tests cover both price directions, current-bar
exclusion from the price channel, volume priority/boundaries and actual 100-bar
d/b feature paths. Native historical prefix invariance covers the six-observer
catalog. These observation ports still do not provide campaign geometry,
independent opportunity grammars, calibration or qualified live execution.

## Active trend observations and causal swing features

Added active registry families `trend_pullback` and `trend_pullback_depth` v1/a.
`trend_continuation.rs` exists but is not in the canonical 28-entry TABLE; its
presence alone does not make it an active expert. Pullback is long-only:
EMA5 > EMA20 with close below EMA20. Depth is long-only with aligned EMAs and
close below the significant swing high but within 38.2% of its high/low range.
The inactive v2 reclaim and 50%-depth branches are not silently substituted.

EMA5/20 uses the supplied causal prefix with first-close seed, adjust=False,
and 20-bar availability, delegated to Polars. Freeze the supplied-history origin
in deployment/research configuration; varying the origin changes EMA state.
Significant swing10 is not a ten-bar rolling extreme: it is a strict pivot with
ten completed bars on either side and pivot-bar range at least the current
14-bar mean high-low range. This legacy range convention is preserved explicitly,
not mislabeled as standard gap-aware ATR. Polars calculates neighboring extremes;
only fully confirmed prefix pivots are usable. Missing pivots remain absent.
Tests verify EMA recurrence, long-only behavior, delayed pivot availability, ties,
and older confirmed pivots versus trailing-window extrema. Native diagnostic
callbacks now include eight observations; broader product integration remains open.

## Sweep/reclaim and three retest variants

`liquidity_sweep_reclaim` preserves strict penetration and close reclaim of the
supplied prefix's preceding extrema, with LONG precedence if both sides qualify.
`breakout_retest` now has executable a/b/c observations: significant swing
role reversal; double-top/bottom validation-level retest; and head-and-shoulders
neckline retest. Retests require a prior close beyond the level within six bars,
not merely the current candle's breach. Pattern pivots are strict, strength three,
and require completed right flanks. H&S selects the extremal head and strongest
flanking shoulders, with the legacy flat-neckline rules and first-on-tie selection.
The pattern-derived validation level must have been breached after the right
structure pivot. Unsupported variants reject explicitly.

Default and both pattern variants are included in historical diagnostics: twelve
stances across ten families. All variants in a family retain the same dependency
group; they cannot manufacture independent evidence. The fixed squeeze admission
policy remains separate from these diagnostic stances. Unit tests qualify mirrored
patterns, rejection without level contact, recency endpoints, strict sweep bounds
and variant validation; native prefix tests include all twelve stances. Campaign
stop/target geometry and opportunity grammar coverage still require integration.

## Eight candlestick variants

`candlestick_reversal` now supplies hammer, shooting star, bullish/bearish
engulfing, bullish/bearish harami, three white soldiers and three black crows.
No override uses the source's ordered first-matching variant selection, despite
the stale Rust header describing hammer-only dispatch. Explicit variants are
independent diagnostic stances sharing one dependency group. The historical
catalog now emits 21 stances from eleven families, including automatic selection.

`CandlePattern` preserves the source-defined structural stop, trigger, direction
and completion clock, without quantity or execution authority. Pattern detection
is not trigger crossing; campaign admission must still enforce its separate
policy. Three-candle patterns require their preceding opposite-color context bar
and a close beyond the second candle's extreme. Zero bodies, missing pattern
context and unsupported variants do not become signals. Decimal price arithmetic
expresses the one-third body boundary as 3*body <= range, without float rounding.

Source discrepancy preserved explicitly: bearish harami's executable inequality
is min(previous open,close) < current open and current close < max(previous
open,close). It does not fully enforce the prose's two-sided body nesting. This
port preserves the actual hypothesis; correcting that condition requires a new
version/trial, not a silent semantic change. It is not a profitability endorsement.
Tests cover all eight patterns, mirrored direction, decline context, zero-body
rejection, four-bar soldier context, strict trigger bound and override behavior.

## Bollinger breakout a/b/c and frozen references

Added three Bollinger breakout variants. Variant a requires a directional close
past the middle band and percent-b >=0.75 or <=0.25; b requires a strict two-sigma
band violation. Variant c adds the previous bar's bandwidth strictly below its
preceding ten bandwidth values, requiring 31 bars. All rolling computations use
Polars with complete 20-close population windows. Flat bands abstain instead of
imputing a percent-b. No absolute 1e-9 price-width fallback is copied; the declared
positive-dispersion formula applies across instrument scales.

`BandSetup` preserves the first bar in the current consecutive directional setup
run, its middle/sigma and 14-bar mean high-low range. Declared stop/target R ratios
and eight-bar expiry are retained as hypothesis geometry, never expected edge.
Tests verify unchanged anchor references as the run extends, all three mirrored
variants and rejection of c when the prior bandwidth is merely tied. The native
historical catalog now contains 24 stances from twelve families. Campaign execution
of this geometry and complete economic-capability port remain outstanding.
