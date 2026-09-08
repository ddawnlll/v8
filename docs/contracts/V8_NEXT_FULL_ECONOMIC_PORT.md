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

## Pattern measuring objectives

Added head_shoulders, double_top (both directions) and triangle observations.
Retest and measuring families now share PatternStructure extraction rather than
copying H&S/double-pivot scans. MeasuringSetup retains validation level, structural
stop, measured target distance and completion clock; the target is a declared
projection, not expected profit. H&S/double use the actual fresh-cross OR within
three bars of the right structure pivot condition. That source rule is not
misdescribed as a general rolling three-bars-since-break rule. Triangle requires
declining confirmed pivot highs and rising confirmed pivot lows in the prior
20-bar range, <=3% width/current-close and a current close beyond the range.

Tests exercise actual patterns, projected distance, stale-cross rejection,
triangle convergence and existing retest/Fibonacci behavior after shared-helper
refactoring. The catalog emits 50 stances from 25 families: 24 of 28 active TABLE
families plus squeeze. Remaining observation families are divergence_12_setups,
funding_crowding_reversal, open_interest_divergence and pandf_breakout. Downstream
economic integration, variants not yet covered elsewhere, calibration and
prospective operation remain completion requirements.

## Causal positioning and funding observations

Added immutable PositioningReading with instrument, metric, event/receipt/known
clocks, explicit validity endpoint and source identity. Unknown/future readings
are unavailable, expired latest observations cannot fall back to older values,
conflicting versions reject, and exact duplicates are idempotent. There is no
invented validity duration. This carrier does not authenticate its source hash;
a future capture adapter must verify physical artifacts before supplying it.

Funding a/b/c/d is reconstructed from the frozen Python economic reference:
a positive-funding reversal, b negative-funding reversal, c either with observed
OI, d contrary trade at a ten-bar price extension. The Rust file currently reads
the variant label but executes only the a price gate for every label; that defect
is not propagated. `funding-settled-causal-v2` explicitly uses settled historical
funding readings, never swaps forecasts/settlements silently. Forecast-based
experiments would require a separately frozen metric and policy definition.

Open-interest a/b/c/d preserves its actual proxy methodology: valid OI presence,
long/short ratio, volume z-score and five-bar price direction. It does NOT estimate
OI change/divergence; the family name is not a claim that it does. Flat price
falls on the source's not-price-up branch. All required auxiliary values must
actually exist; absent OI is not a zero or a synthetic positioning estimate.

Catalog accepts explicitly supplied readings and emits these eight additional
stances. Existing historical callbacks supply none and therefore abstain. Tests
exercise causal absence/revision handling and each price/positioning branch.
Capture/replay ingestion of these auxiliary readings remains OPEN; this is an
observation implementation, not a working live derivatives-data pipeline.
The catalog now covers observations for 26/28 active TABLE families plus squeeze,
58 stances. Divergence12 and P&F remain missing; downstream economic integration
and real prospective qualification remain required.

## Confirmed RSI divergence

Added divergence a (bearish) and b (bullish) observations, preserving the actual
implemented frozen Python pair rather than claiming twelve distinct setups.
The active Rust v1 path implements the bearish case. Strict strength-five pivots
must have range at least the current mean high-low range14; the latest two
confirmed pivots require opposing Wilder RSI14 movement and a strict current
close through the intervening price barrier. RSI uses the shared full-prefix
seed convention, removing the old window/global feature cross-check. Setup
records preserve both pivot clocks, the right-flank confirmation clock, barrier
and extreme. No expected edge or capital authority is assigned.

Actual-price synthetic unit fixtures cover both directions, missing right-flank
confirmation, barrier equality and absent oscillator divergence. Historical
prefix invariance includes both new variants. Checks: 180 tests passed, Ruff
clean, mypy clean on 50 source files. Catalog now emits 60 stances and covers
27/28 active TABLE families plus squeeze. P&F remains absent; opportunity,
calibration, portfolio/campaign integration and prospective qualification remain
open requirements, not implied by observer coverage.

## Point-and-figure economic representation

Added a/b double-top/bottom and c/d triple-top/bottom breakouts. The close-based
transform seeds an X column at the first close, fixes its box to detection-time
mean high-low range14, and reverses at three boxes. This is a small economic
representation with source-specific rules, not a replacement event/execution
engine. Columns retain endpoints and integer step counts instead of allocating
one object per box. Decimal arithmetic replaces floating box-boundary rounding;
this is not a bit-for-bit numerical parity claim. The current column must exceed
all required preceding same-direction extremes strictly. Column origin supplies
the stop; its step count times three boxes supplies the target distance. Both
must leave strictly positive risk/reward distances at the observed close.

The setup records column start separately from observation time, retaining the
source anchor distinction. Four variants share one dependency group and gain no
capital authorization. Tests cover all variants, reversal equality, sub-box
moves, equal prior extremes, insufficient columns, compact huge box counts and
historical prefix invariance. All 28 active TABLE families now have observation
implementations, plus squeeze, yielding 64 catalog stances. This does not assert
all variant/campaign semantics or product operation: broader opportunity grammar,
calibration, portfolio integration and prospective qualification remain open.

## Frozen observer selection reaches native admission

PaperConfig now accepts observer_policy (default squeeze for the existing named
experiment). `families:donchian-breakout` selects all observations from that
family; multiple comma-separated family names must be unique and sorted.
Unknown/empty names reject. Selected stances retain their existing dependency
groups, so variants cannot manufacture independent votes. The native economic
adapter now passes the complete selected tuple to reconciliation/admission and
records it with the policy name. Config and execution policy are frozen before
capture and checked on restart; explicit baseline replay remains independently
named. The historical squeeze observation study is still a separate diagnostic.
Cash trajectory/SPA still compare the explicitly labeled squeeze and baseline,
not arbitrary selected-family performance; session selection is reported apart.

A real native-engine test boundary now exercises Donchian observation through
controller admission and native fill using test-only calibration, alongside
squeeze and baseline. All three reject without calibration and produce no orders
or positions and unchanged cash. This does not supply production calibration.
Checks: 197 tests passed before final report-label additions; registry/selection
and frozen-policy tests included. Opportunity grammar is still the original BTC
breakout scope. Auxiliary capture ingestion, per-variant selection, broader
opportunity/regime semantics, campaign geometry and real calibration remain open.

## Independent G0–G3 grammar policies

Added individually selectable `volatility-extreme-v2`, `trend-continuation-v2`,
`mean-reversion-v2`, `compression-expansion-v2` alongside the old range grammar.
They port the actual predicates from v8-core/src/opportunity/grammar.rs:
G0 current-inclusive population z20 >=1.8 with .3 ambiguity band; G1 SMA8/24
alignment and directional current close beyond fast SMA; G2 mean20 +/-2.2 mean
range14 with a reversal close; G3 current mean range14 in the lower quartile of
49 range observations and absolute one-bar return >.008. These are frozen
hypothesis thresholds, not hardcoded computed metrics. No expert signals or
performance outputs enter grammar generation. BasisDislocation had an enum but
no detector in this Rust source and is not claimed ported.

V2 deliberately removes the source's missing-ATR fallback to 1% of price and
its epsilon-created dispersion. Compression needs all 49 complete range14
observations (62 bars). G0 emits UNKNOWN neutral and AMBIGUOUS near-boundary
records; neither may reach execution even with calibrated inputs. Horizon uses
actual regular bar duration (G0 48/neutral4, G1 24, G2 12, G3 24), not an implicit
one-hour multiplier. Anchor remains market candle close, distinct from receipt
clock. Grammar/version, duration, direction and exposure participate in identity.
These are newly versioned measurement coordinates, not legacy identity parity.

Paper replay reads grammar_policy from frozen config; native integration tests
exercise both old range and new trend grammars with squeeze, baseline and
Donchian observers, with/without test-only calibration. The no-filter baseline
uses the same selected grammar; its legacy identifier remains breakout_baseline,
so reports explicitly carry execution_grammar_policy. Historical observation
rows remain the separate old range/squeeze study, not selected-policy outcomes.
209 tests pass, Ruff and mypy clean. G2 tests demonstrate reversion episodes
without a channel breakout. Full simultaneous modular grammar/book arbitration,
multi-instrument exposure, calibration and portfolio/campaign behavior remain
open; this adds selectable independent economic episode types, not those layers.

## Native campaign protection

PaperCampaign can now retain frozen stop/target prices together or neither.
Malformed, nonfinite, nonpositive or inverted protection rejects before the
engine. Central record serialization preserves Decimal precision through paper
checkpoints, calibration inspection, trajectory and revised-accounting replay.
The existing controller still emits timeout-only campaigns; choosing expert
geometry and binding it to calibrated admission remains a separate open step.

The native adapter submits a Nautilus bracket order list: market entry,
stop-market protection and limit take-profit with deterministic child IDs.
Native contingency handling owns activation, fills and sibling cancellation.
No Python price-touch fill logic exists. Before submission, an executable quote
outside the frozen protection interval invalidates the entry; invalidation is
reported separately from timeout. Price increments must match venue metadata.
Timeout cancels remaining protective orders and requests a native reduce-only
close while preserving both child and timeout exit identities in observations.

Native tests cover LONG/SHORT target and stop fills with sibling cancellation,
timeout cleanup, deterministic replay and pre-entry gap invalidation. These are
synthetic test-only execution checks, not prospective economic evidence. Full
suite passed 215 tests after the adapter change; six additional domain/record
validation tests passed. This qualifies the pinned local engine bracket path,
not actual Binance venue OCO or partial-fill/reconnect behavior. Position-bearing
prospective continuation and expert-specific geometry admission remain open.

## Expert geometry reaches economic admission

Frozen PaperConfig.campaign_policy selects timeout-only-v1 or one of ten source
geometry policies: pandf:a/b/c/d:v2, bollinger:a/b/c:v2 and
measuring:head_shoulders/double_top/triangle:v2. This selection is part of the
existing frozen config/hash and is carried by economic decision/report records.
The source setup must exist with the admitted opportunity's direction. A missing
or opposite-direction setup never silently becomes an unprotected campaign.

CampaignProtection binds geometry to opportunity, instrument, direction and
observation/expiry clocks. Controller rejects missing required, mismatched,
future/expired or price-invalid geometry before creating a campaign. Full
calibration, utility and risk checks still apply. P&F retains structural stop and
column-projection target; measuring retains structural stop and measured distance
from decision close; Bollinger uses frozen range times its declared stop/target R.
Expiry is at most eight actual bars from observed candle close and no later than
the opportunity expiry. Stop rounds toward entry and target toward entry using
venue tick; collapsed geometry rejects instead of widening risk.

These are explicitly v2 execution hypotheses: absolute prices freeze at observed
close and entry uses the next eligible quote/native market order, not the legacy
NEXT_BAR_CLOSE execution convention. No same-tick decision fill or retroactive
geometry update is introduced. Calibration must be obtained for this exact
policy; old policy results are not interchangeable. Existing fixture-only
calibration remains the only positive authority test source.

Native integration verifies P&F setup -> independent grammar -> observer ->
calibrated test admission -> bracket target fill and stop cancellation, and the
same path rejects without calibration. Full suite passed 224 tests; three further
geometry tests verify P&F tick tightening/missing setup, Bollinger 2R mapping and
measured target origin. Ruff and mypy pass. Other expert geometry policies,
portfolio risk allocation, real calibration and prospective operation remain open.

## Donchian, gap and candle campaign geometry

Added twelve further explicit v2 protection policies: donchian:a, gap:a/b/c and
all eight named candlestick patterns. Donchian active v1 preserves the preceding
20-bar low as an unclamped LONG stop with a one-range14 target. Gap preserves its
selected gap-zone stop and one-range14 directional target. Candlestick preserves
its structural reference in the setup, then applies the source's declared
0.8–2.0 range14 stop-distance clamp and one-range14 target. These policies retain
the shared eight-bar bound and tick rounding, and require a complete positive
range14 rather than inventing an ATR. A named pattern without a current matching
setup, wrong direction or absent range cannot create protected admission.

As with prior v2 policies, absolute exit prices are frozen at decision close for
next-quote native entry, not claimed identical to legacy NEXT_BAR_CLOSE fills.
Unit tests exercise all eight candle directions, all six directional gap cases,
clamp/target arithmetic and the unclamped Donchian channel. All 242 tests pass;
Ruff and mypy are clean. There are now 22 explicit protected policy variants
across six expert families. Remaining expert exit semantics, actual data-derived
calibration, portfolio allocation and prospective qualification remain open.

## Real-data native counterfactual experiment path

Added HistoricalTrial and app.trial, an explicit DEVELOPMENT experiment path
using the pinned native OHLC execution model. It applies the frozen grammar,
observer reconciliation, declared geometry and exposure budget to measure rule
outcomes without inventing utility or calibration receipts. This is distinct
from production economic admission; its selection reason is
COUNTERFACTUAL_POLICY_SELECTED_NOT_UTILITY_ADMITTED. No QuoteTick or market
input is synthesized. Prior selections execute no earlier than the next real
bar callback. Gaps beyond frozen protection invalidate entry. Native engine owns
fills, contingent orders, cash and observed funding settlement.

ResearchStore registers policy/source/lock/execution-model and dataset identities
before replay; registered HOLDOUT datasets reject in this development command.
Failed attempts remain in the search-family count. Strategy callback failures
are retained and reject the app result even when the native engine merely logs
the Python exception. Full result includes actual native events, campaigns and
account state; calibration_eligible and promotion_eligible remain false.

Real replay uncovered and fixed stale exit authority: a campaign closed by a
native protective fill must not later cancel/close a successor at its original
timeout. A native filled exit now terminates that campaign's exit authority.
A targeted regression covers this; no inferred custom fill state was introduced.

Development evidence: the existing verified real capture
/tmp/v8-next-capture-20260908-initial/manifest.json supplied 499 bars. Frozen
Donchian/trend-continuation with Donchian exits selected 21 experiment campaigns
and produced 50 native order records. Corrected replay was identical across two
runs; the earlier pre-fix trial is invalidated as economic evidence. Outputs are
development-only temporary artifacts, not release receipts. Historical spread,
slippage, funding completeness and venue margin remain unqualified. Native
netting cache position count is not a count of independent trade outcomes.

Full regression passed 245 tests before the callback-failure addition; both
historical-trial guard tests then passed. Native tests establish actual later-bar
entry and future-suffix decision invariance. Ruff/mypy pass. Real calibration,
qualified outcome sample construction, statistical correction and prospective
paper operation remain open; an offline experiment is not their completion.

## Campaign outcomes survive native netting reuse

PaperCampaignAdapter now snapshots each native PositionClosed event with its
opening/closing order ownership, clocks, entry/exit prices, peak quantity,
realized PnL, commissions and adjustment records. The same netting position ID
can be reused without erasing earlier campaign closures. Conflicting duplicate
closures reject. Callback failures are retained and cause paper, revised
accounting and historical-trial apps to reject incomplete output, rather than
accepting a native-engine log as successful collection.

Observed outcome projection binds closures back to campaign/instrument/direction
and requires entry strictly after decision. It preserves unclosed/unfilled
selections as missing returns, never zero. Native realized PnL already contains
commissions and observed funding: components are exposed but not deducted twice.
Entry-notional returns are descriptive conditional outcomes, not expected edge.
An aggregate conditional mean is omitted unless no native exposure/orders remain
and all closed PnL reconciles exactly to native cash change. Unknown/repeated
closures or currency/clock mismatches reject; discrepancies remain explicit.

On the existing real 499-bar Donchian experiment, 21 selections yielded 15 closed
campaign outcomes and 6 missing outcomes. Closed net PnL reconciled exactly to
native cash change; temporary evidence is /tmp/v8-next-real-outcomes.json. This
still has calibration_eligible=false and NO_ECONOMIC_CLAIM: historical availability,
execution assumptions, funding completeness and statistical selection are not
qualified by cash reconciliation. Native tests prove that two successive closes
sharing one netting ID remain separate and reconcile, that fees/funding are
counted once, and that open/missing/corrupted outcomes cannot produce a complete
sample. All 249 tests pass; Ruff/mypy clean. Real calibration and full benchmark
inference remain open requirements.

## White Reality Check numerical path

Added WHITE_MAX_MEAN_CIRCULAR_BLOCK_V2 on aligned baseline-minus-variant loss
intervals. It preserves reality_check.rs's compound-null centering on each
variant's own observed mean, joint resampling of every column, family maximum
and inclusive >= exceedance fraction. arch.bootstrap.CircularBlockBootstrap owns
the sampler; NumPy owns reductions. The installed arch RealityCheck is a shallow
SPA subclass, so it is not substituted for V8's circular-block/inclusive-tail
contract. V2 uses the library RNG instead of reproducing the legacy MT19937 draw
sequence; deterministic repetition within the pinned environment is tested.
Mean ties use lexicographic variant identity rather than dictionary insertion.

Existing exploratory SPA output now also includes a separately labeled WRC
result using the explicit same seed/block-size/repetition plan; SPA remains
stationary and WRC remains circular fixed-block. Their numerical outputs do not
establish source admissibility, preregistration, independent samples, complete
search-family accounting or any claim authority. DSR and PBO remain absent.
The real campaign-conditional outcome sample is not silently treated as aligned
policy loss intervals, so no p-value is fabricated for the earlier 15 outcomes.

A hand-enumerated draw test checks common resampling, per-column centering and
exact tie inclusion (a strict-tail implementation would fail). Library-backed
checks cover seed repeatability, duplicate-column invariance, missing chronology
and degenerate input rejection. This is methodology retained with a mature
resampler, not a custom bootstrap infrastructure port.

## Explicit CSCV/PBO diagnostic

Source: Bailey, Borwein, Lopez de Prado and Zhu, The Probability of Backtest
Overfitting (2015 author version), sections 2.2 and 3.1:
https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
The Rust multiplicity ledger had no genuine PBO implementation to preserve.
The new diagnostic partitions aligned return intervals into equal contiguous
blocks, evaluates every half/complement combination, selects IS maxima and
computes OOS relative-rank logits. NumPy computes scores; SciPy supplies ranks.

CSCVPlan explicitly selects mean return or nonannualized sample Sharpe,
partition count, exact-work budget and the declared complete candidate list.
Inputs must be negative net periodic-return losses with equal interval duration.
Missing variants/values, irregular intervals, duplicate performance columns,
undefined split Sharpe or excess combinatorial work reject without silently
truncating data, dropping folds or sampling a different estimator. Training
score ties share equal weight; OOS ties use midranks, and zero logit counts as
an overfit outcome. These discrete tie conventions are an explicit V8 versioned
policy, not unspecified behavior attributed to the paper. Exact duplicate
performance is not automatically equated with identical economic strategies.

spa_diagnostic accepts an optional CSCVPlan and returns the separately typed PBO
result; without a plan it remains None. A family of one variant cannot yield
PBO and the existing two-path cash report does not invent a larger search family.
The registry-list parameter verifies declared coverage, not undisclosed research
history. CSCV is not a forward simulation or a substitute for untouched holdout;
no source qualification, calibrated edge or promotion authority is minted.

Tests include analytically known persistent-winner, reversed-regime and six-fold
outcomes, tie weighting, repeatability and invalid family/data/work plans. The
family numerical API integration is also exercised. DSR and qualified real-data
statistical plans remain open.

## Genuine DSR numerical path with declared independence

Source: Bailey and Lopez de Prado, The Deflated Sharpe Ratio (2014), equation 2:
https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
The Rust multiplicity ledger supplied no estimator. DSRPlan now declares the
selected variant, complete comparison IDs, effective independent trial count and
its stated basis. The numerical method uses the family's sample Sharpe variance
to approximate the maximum under a zero-Sharpe null, then computes the selected
strategy's confidence using sample length, skewness and Pearson kurtosis.
SciPy supplies Normal quantiles/CDF and moments; NumPy supplies reductions.

Inputs must be negative net excess returns on aligned equal-duration intervals.
Sharpe is nonannualized with sample SD ddof=1; skew/kurtosis use uncorrected
central moments (bias=True, Pearson rather than excess kurtosis). Independent
trials must equal one or lie between two and the declared family size. N=1 has
no multiplicity threshold; the large-N approximation is not extrapolated through
fractional values between one and two. Unknown/duplicate/omitted variants,
missing observations, undefined Sharpe or unidentified variance reject.

The API returns dsr_confidence, explicitly not a p-value. Optional DSRPlan wires
it into the family diagnostic alongside SPA/WRC and optional PBO. No default
independence estimate, annualization factor or fabricated null distribution is
inserted. A caller-supplied basis is not certified independence; serial dependence,
source provenance, complete search history and power remain unqualified. There
is no promotion or calibration authority in this numerical result.

Tests establish the analytic zero-Sharpe/N=1 half-confidence case, increased
multiplicity lowering confidence, positive return-scale invariance, deterministic
results, invalid input rejection and family API integration. The four numerical
method paths now exist, but their qualified real-data benchmark workflow and
prospective evidence remain completion requirements.

## Native marked equity at common bar boundaries

Historical trials now retain one cash-plus-unrealized equity observation per
source bar, including bars without a selection and bars with open exposure.
Nautilus Position.unrealized_pnl values actual open positions at the source bar
close; native cash already incorporates settled costs. Cross-instrument exposure
without a price rejects instead of being omitted. Source hashes and observation
clocks accompany each mark.

The phase is explicitly PRE_STRATEGY_BAR_CALLBACK, before campaign actions.
It is not terminal equity for every event sharing that timestamp. Terminal
account state remains separate; no fabricated balancing adjustment joins them.
Native tests cover open-position valuation, one mark per bar and unchanged
prefix equity under a changed future suffix. These diagnostic modeled historical
marks still need interval-return alignment, explicit research plans and full
family/OOS integration before qualified benchmark use.

## Complete fixed-capital period losses

Trial output now projects adjacent native equity marks into negative equity
change divided by fixed initial capital. The first actual mark is the starting
valuation; no invented pre-data equity or terminal adjustment is added. All
intervals must have identical duration, currency and callback phase. Missing,
repeated, nonfinite or unreconciled marks reject. Computation time supplies
availability, not modeled historical callback time. These are net periodic
capital contributions, not compounded returns or risk-free-adjusted DSR inputs.

The captured real 499-bar Donchian development replay produced 499 equity marks
and 498 intervals in /tmp/v8-next-equity-intervals.json. This remains diagnostic
and promotion-ineligible. Tests cover unrealized gains/losses, fixed denominator,
actual availability and malformed boundaries. Full suite: 268 tests passed;
Ruff/mypy clean. Complete-family experiment execution, explicit excess-return
specification and qualified OOS plans remain required for benchmark integration.

## Registered family to SPA/WRC connection

family_losses requires every locally registered family trial, including attempts
without results (which block comparison rather than vanish). It verifies frozen
policy/trial hashes against registry metadata, development role, computation
chronology, common source marks/dataset/runtime and cash/fee assumptions. Losses
are recomputed from native marks rather than trusted from cached report fields.
compare_family then invokes SPA/WRC with an explicitly selected member baseline
and explicit bootstrap parameters. Degenerate inputs reject without discarding
candidates. PBO/DSR plans and protected forward OOS are not inferred.

This enforces local registry coverage, not completeness of undisclosed research
history or artifact authenticity. Comparing historical development results does
not establish preregistration, OOS status, calibration or economic authority.
Tests cover incomplete/duplicate families, omitted failed attempts, altered
source/policy, future computation clocks and the numerical integration path.

## Executable development comparison command

app.compare reads recorded trial JSON files, requires an existing research store,
explicit family/baseline/bootstrap inputs and writes an exclusive comparison
artifact only after successful validation/inference. Input byte hashes and paths
are recorded. It does not transform development observations into protected OOS.
A missing family member test proves no report is written on rejection.

Two fresh trials on the existing real 499-bar capture compared the same Donchian
observation/trend grammar with protected versus timeout-only exits. Both used
identical declared fee/capital assumptions and code. The command successfully
compared 498 intervals; temporary files /tmp/v8-family-protected.json,
/tmp/v8-family-timeout.json and /tmp/v8-family-comparison.json contain the inputs
and diagnostic output. The explicit 12-block/999-repetition/42-seed selection
is a development choice, not a certified statistical plan. No edge, OOS or
calibration claim follows from this integration run.

## Explicit family CSCV integration

compare_family and app.compare now accept an optional explicit CSCV plan. CLI
JSON schema checks require partition count, metric, split budget and the complete
non-baseline candidate IDs; plan bytes join the hashed inputs. Existing numerical
checks reject omitted candidates, insufficient families, non-divisible intervals,
duplicate performance and undefined split scores without dropping observations.

A real-data development integration used three fresh trials on the same 499-bar
capture: Donchian observations/trend grammar with timeout, Donchian-protected and
Bollinger-protected campaign policies. Timeout was the explicit baseline. The
remaining two candidates produced SPA/WRC and PBO on all 498 intervals, with six
CSCV blocks, mean-return scoring and all 20 combinations. Temporary artifacts
are /tmp/v8-pbo-{timeout,donchian,bollinger}.json and /tmp/v8-pbo-comparison.json.
These experimental policy combinations/parameters are not preregistered OOS
plans or calibration evidence. DSR excess-return and independence specification,
protected OOS, production calibration and portfolio operation remain open.

## Explicit excess-return connection for family DSR

The family API accepts DSR only with an explicit aligned negative reference-return
series and a stated basis. Candidate loss minus reference loss yields negative
excess return; availability is the later input clock. Missing, future or misaligned
reference values reject, never becoming assumed zeros. Baseline remains excluded
from the candidate family. SPA/WRC/PBO continue to use their original net-return
inputs; only DSR receives reference-subtracted returns.

The report retains the reference series/basis and labels it caller-supplied,
not source-certified. Currency, fixed-capital convention and suitability of the
reference must be established by its supplier. Independent-trial assumptions
remain explicit DSRPlan inputs, not inferred validation. Tests cover subtraction
sign, availability, absent references and the full family-to-DSR path. No genuine
reference dataset was invented to produce a real-data DSR result. A CLI reference
artifact contract and economic source qualification remain open.

## DSR reference artifact and CLI

app.compare accepts --dsr-reference with a validated explicit plan/reference
artifact. Pydantic owns schema validation: unknown fields, missing returns,
nonfinite values, non-USDT currency and missing source/basis metadata reject.
The fixed-capital convention must be declared and its denominator must match
all trials. The existing family path checks alignment, availability and complete
candidate IDs. The exact input hash, metadata and reference series are retained
in the output. No reference source is certified by schema validation, and no
zero-return dataset is generated to force DSR availability. Tests validate the
artifact contract; existing family tests exercise the DSR numerical connection.
Real source qualification, protected OOS and production calibration remain open.

## Dataset role contamination guard

ResearchStore.register_trial now prevents one dataset hash from combining HOLDOUT
with DEVELOPMENT or PROSPECTIVE, across trial names, policy IDs and families.
Previously the app trial precheck only prevented one direction and could race
with another registration. Registry lookup, role validation and insertion now
share BEGIN IMMEDIATE, so concurrent conflicting admissions cannot both commit.
Existing identical registrations remain idempotent, and failed registration rolls
back without contaminating subsequent work. Tests cover both directions, restart,
renaming, independent datasets and concurrent contenders.

This protects known local dataset identities, not overlapping observations in
separately hashed manifests, undisclosed external access or alternative registries.
It does not by itself qualify a protected OOS run. Window/observation lineage and
frozen plan integration remain necessary, along with the rest of the full port.

## Cross-manifest coverage protection

The registry now records immutable half-open dataset coverage per instrument.
Historical trial execution derives its range from verified source candles,
including warmup, and registers it before building/running the native engine.
Coverage insertion checks overlapping HOLDOUT versus observed roles atomically,
across different manifest hashes and families. Failed attempts remain in the
trial registry. Exact adjacent boundaries are allowed; same-instrument overlap
rejects in either role direction. Tests cover overlap, adjacency, distinct
instruments and attempted coverage rewrites.

This is conservative declared source coverage, not embargo/purge methodology or
proof of cross-asset independence. Legacy records without coverage and data
outside this registry remain unqualified. An eventual OOS runner must register
verified holdout coverage and bind the frozen plan before evaluation. No existing
historical dataset has been retroactively declared pristine by this change.

## Future experiment plan freeze

ForwardPlan declares hourly future boundaries, named policy family, baseline,
common capital/fees and explicit SPA/WRC sampling parameters. app.plan records
its full content and runtime source/lock hash atomically, using internal wall
clock registration. Windows already started reject new registrations. Identical
retries preserve the original record; changed policy/code cannot reuse an ID.
The plan is revalidated at registration, including duplicate policies and family
compatibility. This is an experiment specification, not an authority receipt.

Tests cover restart/idempotence, no backdating, changed-runtime rejection and
invalid family/window definitions. No genuine experiment is declared completed
by a frozen plan. Execution/coverage binding, acquisition availability, embargo
and protected OOS evaluation remain open. Local database/clock trust and outside
access cannot be established by these checks.

## Frozen forward-window runner

app.forward binds a registered plan to one complete verified source window after
its end, checks the frozen source/lock hash and executes every declared policy
through the shared native trial path with HOLDOUT registry role. This role cannot
mix with known development datasets/windows. The plan binding is atomic and
survives later failure; another manifest cannot replace it. Same-data retries
remain the same plan/trial identities. All policies feed the declared baseline
SPA/WRC plan, without selective omission. No economic/calibration authority is
created. Runtime/manifest changes between policies reject.

The source window has N hourly bars and N-1 pre-callback equity intervals; the
first bar establishes starting valuation. Bootstrap size validation accounts for
this. No pre-window equity is synthesized. Tests cover incomplete/early windows,
changed code, permanent binding and runner orchestration through real numerical
inference with test-only fixtures. Existing native trial tests cover the shared
execution path. No completed real future window has been claimed as tested.

The runner is PREREGISTERED_FORWARD_WINDOW_MODELED_REPLAY. REST historical
availability remains modeled, so this is not qualified prospective execution.
Continuous acquisition/PIT, warmup and embargo methodology, exact venue behavior,
calibration and the broader portfolio/expert requirements remain incomplete.
