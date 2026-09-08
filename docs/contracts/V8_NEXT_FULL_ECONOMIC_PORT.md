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

## Ichimoku crossover and gap sequences

The active `ichimoku_cloud` code implements a fresh Tenkan9/Kijun26 midrange
cross, previous-side equality allowed, with the current close aligned beyond
Kijun. It does not implement a displaced Senkou cloud or Chikou confirmation;
those are not inferred from the family name. Complete current and prior windows
require 27 bars. Its Rust VERSION is v1 but its emitted variant is v2; the new
observation preserves this actual variant label. All values are causal rolling
high/low midranges through Polars. Persistent alignment without a new cross
abstains; tests exercise both directions and next-bar suppression.

Gap a observes reversal after at least three same-direction gaps in the trailing
20 transitions; b observes the first gap beyond the prior 20-bar range with a
continuation close; c observes the second gap with a continuation close. Twenty
transitions require 21 actual candles: the new implementation rejects shorter
partial gap-count histories. Strict opening beyond the prior high/low defines
a price gap. Noncontiguous timestamps instead produce SOURCE_GAP abstention.
GapSetup retains the current gap's top/bottom and directional structural stop.
The source's gap-level inventory tests fills only on subsequent closes: a current
new gap is necessarily its last zone, so no custom zone inventory is needed for
these current-gap observations. This does not qualify future gap-zone persistence
or execution. Tests cover counts, directional mirrors, wrong variants and gaps.

Historical diagnostics now contain 28 stances from fourteen families. Their
presence is not qualification of the remaining campaign, allocation, calibration,
benchmark, portfolio or operational scope.

## Session pivot correction and narrow-range breakout

Added floor-trader pivot drift and range-breakout-1to1 observations. Daily pivot
has an explicit semantic correction/version: `floor-trader-pivot-utc-session-v2`
uses the previous complete UTC day's high, low and LAST close, fixed for the
current session. The Rust state function instead uses the prior rolling 24 bars
and their FIRST close, despite daily-session descriptions. That accidental formula
is not promoted into the new daily product. Exact hourly coverage and day endpoints
are required; missing history abstains. Directional drift needs positive remaining
room to R1/S1; crossing an already-passed target does not qualify. This is a new
versioned hypothesis, not numerical parity with legacy daily-pivot results.

Range breakout retains the actual active volume gate (z>=0.20 over 100 bars),
prior 20-bar channel, width/current-close <=3%, and rejection if the immediately
preceding bar already broke its own prior channel. The stale source header's
"no volume gates" is not followed. Missing dispersion abstains. The breakout
bar cannot enlarge its own prior channel. Tests cover actual volume rejection,
freshness and fixed daily references rather than merely testing helper formulas.

Historical diagnostics now include 30 stances across sixteen families. These
remain observations; full campaign, allocation, calibration and prospective
position-bearing operation are still open requirements.

## CMF/close-count regime and MACD/stochastic

Added `obv_adl_regime` with the actual d/c/b/a priority. Its so-called OBV slope
is the net sign count over ten close changes (threshold +/-3), not a newly
implemented OBV estimator. CMF20 and EMA5/20 use native-backed calculations.
Zero total volume is missing CMF and abstains; the source null-to-zero fallback
is not copied. Flat individual candles contribute zero signed flow under the
source convention. Variant d is intentionally asymmetric: oversold CMF below
-0.15 with close below slow EMA observes LONG; no mirrored d-SHORT is invented.
Tests exercise every branch and its priority/boundaries, plus computed features.

`macd_stoch_trend` uses EMA12-EMA26, stochastic K14/D3 and a confirmed directional
K/D run aligned with MACD's sign. The source permits later bars in that run;
it is not changed to a one-bar crossover. Full stochastic windows and the source
MACD feature's 34-bar availability are required. A run starting before complete
D values cannot claim an observed crossing. Flat ranges use the declared neutral
K=50 convention. Tests cover actual recovery in both directions, flat-price
abstention and warmup. Historical callbacks now run 32 stances across eighteen
families, without changing the admitted squeeze policy or certifying economics.

## Fibonacci continuation and projection

Added active v1 Fibonacci retracement continuation (38.2% touch/reclaim) and
projection reversal (161.8% extension touch/rejection). A shared immutable
FibImpulse records origin/extreme, their source clocks and the later pivot's
confirmation clock. Levels are Decimal formulas derived from that impulse,
including the 78.6% deep invalidation reference. No fitted ratios or edge scores.

Source distinction: Fibonacci uses the latest confirmed strength-10 pivots WITHOUT
the significant-swing range filter used by pullback-depth. Pattern pivot extraction
now accepts an explicit strength and still requires both completed flanks. A pivot
that is simultaneously the latest high and low cannot define temporal impulse
direction and remains absent; the legacy arbitrary downward tie case is not copied.
Tests prove delayed confirmation, frozen origin/extreme levels and both mirrored
reclaim/rejection paths. Existing strength-three pattern tests remain green.

The diagnostic catalog now contains 34 stances from twenty families. Fibonacci
confluence and other remaining expert families, as well as downstream full-product
requirements, are still open; this is not an economic-operation completion claim.

## Fibonacci/RSI/Bollinger confluence

Added both confluence variants: a requires all three directional observations;
b requires two, including the source's behavior when the third contradicts.
This is an internal hypothesis predicate, not evidence reconciliation or a
statistical independence claim. Both variants share a dependency group.
The legs are the two-to-three-sigma Bollinger fade zone, observed Wilder-RSI
recovery run (LONG precedence), and 78.6% confirmed-impulse retracement reclaim.
The RSI leg does not borrow the separate RSI expert's signal-candle extreme
trigger: the source confluence deliberately uses the recovered oscillator run.
A confirmed impulse is required even for the majority variant. Full-prefix RSI
supplies one consistent current value instead of conflicting local/global seeds.

Tests exhaust all 27 directional/missing vote combinations and establish actual
computed three-leg positive behavior from isolated OHLC fixtures. Prefix replay
covers both variants. No confidence or profitability is inferred from agreement.
The historical catalog now emits 36 stances across twenty-one families; remaining
expert and full economic-operation requirements are still open.

## Volume climax and active-registry reconciliation

Added volume_climax_reversal's active VERSION=v2, with e/d/c/b/a precedence:
strict 3-sigma trend fade, 2-sigma reversal bar, low-volume proximity fade, then
2-sigma buying/selling climax. Volume and range percentile ranks count <= ties
on the trailing 100 bars. Reversal uses the actual five-bar close comparison and
candle color. Constant volume provides neither z-score nor min/max proximity
and abstains rather than inventing a neutral statistic. Tests cover every branch,
priority boundaries and an actual computed strict-climax observation.

Registry accounting correction: counts reported above are executable catalog
families, not fractions of the Rust active TABLE. Squeeze is an additional family
outside the current 28-entry TABLE. The current 22 catalog families represent
observations for 21 active TABLE families plus squeeze, with 37 stances total.
Still missing active TABLE observation families are:

- divergence_12_setups
- failed_breakout_2b
- funding_crowding_reversal
- market_profile_value_area
- open_interest_divergence
- pandf_breakout
- pattern_measuring_objective

These counts do not assert completed variants, campaign semantics or economic
integration. The broader requirements at the start of this document remain open.

## Complete-session Market Profile a/b/c/d

Added prior-session TPO profile and all four reaction variants. NumPy difference
arrays/cumulative sums count one TPO per touched price bucket per candle. V8 owns
the source methodology: maximum-count POC, nearest session midpoint then lower
bucket ties; greedy larger-neighbor value-area expansion, left on ties, to ceil
68% of TPOs. A disconnected profile that cannot reach that share abstains instead
of returning the source's underfilled area labeled as value area. A 100000-bucket
resource guard fails explicitly, never silently changes bucket width.

As with daily pivot, the new complete-session version requires all 24 hourly bars
of the previous UTC day, not a possibly truncated 12-bar prior-session suffix.
Bucket width remains detection-time mean high-low range14 under the source's
range convention; Decimal bucket boundaries replace float-floor ambiguity. The
version is `market-profile-complete-session-v2`, not a legacy numeric parity claim.
Variants a/b/d revert inside prior-day extremes toward POC from its center, value
area or half-bucket deviation respectively. Variant c uses >=55% directional TPO
tail pressure and an initiative close beyond value area inside prior-day range.

Tests establish exact TPO totals/POC/coverage, tie handling, disconnected absence,
complete prior-day availability and all four actual feature-to-stance paths.
The catalog has 23 families (22 active TABLE families plus squeeze), 41 stances.
Six active TABLE observation families remain missing; downstream economic scope
remains open regardless of these observer counts.

## Failed-breakout 2B variants b through g

Added six active variants: b significant-swing close reclaim in both directions;
c/d bullish/bearish Hikkake inside-bar false break and reclaim within three bars;
e opening gap reversed through the prior extreme; f SHORT-only failed 26-bar
midrange/cloud proxy; g prior 20-bar range close-through failure in both directions.
The false-move candle is excluded from the cloud/range it broke. Hikkake searches
only the three eligible recent false moves, newest first, equivalent to the
source's full backward scan plus recency rejection. Inside/outside shape is
computed directly from the same immutable candles, removing duplicate feature
cross-check plumbing. FailedMove retains the frozen reference and completion
clock; this does not yet implement every campaign/run-anchor consequence.

Tests cover every variant, mirrored Hikkake, exact 1/2/3-bar eligibility versus
4-bar rejection, significant swing references and false-bar exclusion. Historical
catalog now contains 47 stances from 24 families (23 of 28 active TABLE families
plus squeeze). Remaining active observation families: divergence_12_setups,
funding_crowding_reversal, open_interest_divergence, pandf_breakout and
pattern_measuring_objective. All downstream full-product requirements remain open.
