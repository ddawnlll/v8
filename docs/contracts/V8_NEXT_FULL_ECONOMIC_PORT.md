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

## Paper callback failure propagation

Review of position-bearing continuation confirmed the online account still lacks
late-final-funding reconciliation; the existing readmission block remains necessary.
An independent correctness gap was fixed: quote/campaign and economic callbacks
now retain exceptions in callback_failure, which existing paper/accounting app
checks reject after native replay. Later quote callbacks cannot admit additional
campaigns after failure. This prevents a native engine that logs callback errors
from making an incomplete economic run look successful. Tests inject campaign
and economic failures, verify retained reasons and prevent subsequent admission;
existing native execution tests still pass. This is not a funding-continuation
implementation or an authorization to remove its guard.

## Stop-distance allocation policy

Ported the economic rule from v8-core/src/allocator.rs: equity times explicit
risk fraction divided by directional stop distance determines raw quantity.
The controller now accepts an optional StopBudget and reconciled StopExposure,
including reserved nominal risk/concurrency. Missing, stale, unreconciled or
capacity-exceeding state rejects. The proposed budget must fit the heat limit;
existing notional/exposure caps and venue lot rounding still constrain quantity.
No old leverage defaults, custom margin/account model or order infrastructure
is imported. Directional geometry is validated rather than absolute-distance
acceptance of a stop on the wrong side. Fees/gaps can exceed nominal stop loss;
this is not a maximum-loss guarantee.

Tests verify long/short sizing, pending reservations, heat/concurrency rejection,
exact lot-floor behavior and that verified utility remains required. Native
portfolio-to-StopExposure projection and active app policy configuration remain
to be connected; this controller capability is not full multi-asset allocation.

## Stop budgets connected to active applications

PaperConfig now freezes optional explicit StopBudget settings and rejects them
with timeout-only campaign policy. Both historical trial and economic paper
paths size against observed native equity and frozen stop geometry, then apply
existing notional caps/venue lot floors. The paper empty-exposure gate also
includes unsubmitted pending campaigns, so reservations are not silently zero.
The zero StopExposure supplied in this initial path is conditional on no open
native positions/orders or pending campaign; concurrent positions remain blocked.

Native tests run the same real-engine fixture with/without a small stop budget,
verify reduced campaign quantity and bounded nominal risk. Config tests cover
protection requirements, risk/heat constraints and serialization roundtrip.
This connects an economic sizing policy, not generic portfolio infrastructure.
Open-position stop-risk projection, concurrent allocation, funding reconciliation
and genuine calibration remain incomplete.

## Native protective-stop exposure projection

native_stop_exposure reads native open netting positions and their campaign-owned
active reduce-only stop-market orders. It checks instrument, exit side, trigger
price and sufficient remaining stop quantity. Nominal heat is actual entry-to-stop
absolute distance times current native quantity, preserving the legacy convention.
Unknown ownership/orders, missing protection or unpriced pending campaigns yield
None rather than zero. A covered native state yields StopExposure; this structural
reconciliation does not certify funding or guarantee maximum realized loss.

Trial reports now retain that projection. A native-engine test holds a protected
0.01 BTC position with 100 USDT stop distance and observes 1 USDT nominal risk;
removing the stop from the observed cache view returns absence. Pending campaign
risk likewise stays absent. Native engine/order/account ownership is unchanged.
Concurrent admission, reservation valuation and online funding continuation are
still required before using open-position snapshots to expand product operation.

## Unsubmitted protected-campaign reservation bounds

Stop exposure projection can now receive explicit unsubmitted campaign IDs.
For each protected campaign it reserves quantity times the full stop-to-target
reference-price band and counts one concurrency slot. This is a conservative
nominal pre-submission budget, not a predicted fill or maximum realized loss;
the existing entry check requires the reference price strictly within that band,
while native gaps/slippage remain separate execution risk. Unknown, expired,
unprotected or already-native-submitted entries do not become zero reservations.
Trial terminal reports pass their actual unsubmitted ID set to this projection.

Tests cover combined long/short reservations and native transition from a 2 USDT
pre-submission band budget to a 1 USDT actual-entry stop risk. Missing protection
and a native entry already present reject reservation classification. Concurrent
admission and handling partially filled/native in-flight entry risk remain open;
this change does not relax the current one-active-exposure product gate.

## Active trend-family campaign geometry

Added trend-pullback:a:v2 and trend-depth:a:v2 protected campaign policies, using
the already ported active observation predicates. The source active v1 branches
in experts/trend_pullback.rs and experts/trend_pullback_depth.rs both declare
stop_r=1, target_r=1 and expiry_bars=8. The alternate Rust v2 structural stop
branches are not silently substituted. V8-next freezes one mean-range14 distance
on each side of observed close, with existing tick tightening and native bracket
execution. The v2 suffix denotes the new absolute-price execution convention,
not source v2 expert logic or historical fill parity.

Tests exercise actual EMA pullback and confirmed-swing depth setups, no-setup/
wrong-direction rejection, one-range geometry and eight-bar expiry. This extends
protected execution coverage to eight expert families (24 policies); other
families/variants and the remaining economic operation requirements remain open.

## RSI recovery and volume-confirmed campaign geometry

Added rsi-reversion:a:v2 and volume-breakout:active:v2. Both reuse their active
observer predicates rather than introducing another signal definition. Source
rsi_stoch_reversion.rs variant a and volume_confirmed_breakout.rs active v1
explicitly declare one volatility unit stop/target and eight-bar expiry. Volume
policy retains the existing observed d/c/b/a priority selector; its name does
not falsely imply only variant a. Frozen native absolute geometry and tick
rounding follow the established new-product convention.

Tests cover actual long and short recovery/breakout patterns, exact one-range
geometry, expiry and missing recovery/volume rejection. Protected campaign
coverage is now ten families/26 policies, not complete expert migration. Missing
families, allocation integration, auxiliary market data and prospective operation
requirements remain open.

## Failed-breakout structural campaign protection

failed-breakout:a:v2 uses the latest close-break's frozen prior high as the SHORT
stop, matching failed_breakout.rs Issue #63 semantics. It does not substitute a
one-range or clamped stop. Target remains one mean-range14 below observation
close, with eight-bar expiry and existing tick/native execution rules. The shared
last_close_breakout helper now supplies both the observation and geometry path,
so a newer break supersedes the old reference consistently. Missing volatility
warmup or a break older than five bars yields no protection.

Tests distinguish the 101 structural stop from a 102 one-range stop, verify a
newer reference at 104 and reject stale setups. Protected coverage reaches eleven
families/27 policies; this is not complete expert or operational port coverage.

## Bollinger fade campaign geometry

bollinger-reversion:a:v2 preserves the source active-a geometry: freeze population
sigma20 and mean-range14 at the first bar of the current consecutive fade run,
then clamp sigma to [0.8, 2.0] anchor range units for both stop and target distance.
Polars owns rolling moments; the small economic helper owns anchor selection.
Native absolute-price placement remains relative to current observed close and
uses the established tick and eight-bar rules, not historical entry-fill parity.
Tests cover long/short bands, clamp behavior and frozen anchor volatility even
when a later bar's high/low range changes. Protected scope is twelve families/
28 policies; other family geometry and operational work remain incomplete.

## Momentum, climax and Ichimoku campaign connections

Added obv-adl:active:v2, macd-stoch:active:v2 and volume-climax:active:v2 using
the source active paths' one-range stop/target and eight-bar expiry. Existing
observer variant priority and no-setup behavior remain the signal authority.
Ichimoku:cross:v2 separately retains current Kijun26 distance clamped to 0.8–2
mean-range14 units and a 1.5-unit target, as ichimoku_cloud.rs specifies. It
requires the actual crossing predicate, not persistent trend alignment.

Tests verify momentum/climax setup-dependent geometry, no-volume/no-setup
rejection and long/short mirrored Ichimoku geometry. Native execution stays in
the common bracket adapter. Coverage reaches sixteen families/32 protected
policies, still not full variant, auxiliary-data or operational completion.

## Fibonacci and confluence campaign connections

Added fib-retracement:a:v2, fib-projection:a:v2 and confluence:a/b:v2. Source
active paths all declare one mean-range volatility unit per stop/target and
eight-bar expiry. Retracement's alternate deep structural stop branch is not
substituted for active v1. Existing confirmed-pivot/extension observations and
strict-versus-majority confluence rules supply setup eligibility unchanged.
Tests exercise both Fibonacci directions and ensure majority confluence cannot
silently qualify the strict campaign. Tick rounding preserves nominal distances.
Protected coverage is nineteen families/36 policies; source/variant and complete
operational requirements remain outstanding.

## Session pivot and range-height campaign geometry

Added floor-pivot:a:v2 and range-breakout:a:v2. Pivot protection uses the previous
complete UTC session's pivot stop and R1/S1 target, preserving the already explicit
session-data correction rather than reintroducing the legacy rolling-day bug.
Range breakout uses one prior-20-bar range height on each side of observed close,
matching source stop_r=target_r=range_height/atr (not a literal prior-low stop).
Both retain eight-bar expiry and tighten rounding toward entry. Tests cover
long/short reflection, exact structural pivot prices and range-height semantics.
Protected coverage is twenty-one families/38 policies; other families and full
prospective economic operation remain incomplete.

## Divergence A/B protected geometry

Added divergence:a/b:v2 campaign policies over the existing confirmed RSI/price
setups. Rust active v1 declares 1R:1R:8bar for bearish A; the frozen historical
Python family specification explicitly gives the same default for A/B. The
source's barrier/extremum references belong to still-valid logic, not substitutes
for the declared stop. Tests verify both directions, one-range tick-rounded
geometry, eight-bar expiry and distinction from the structural extremum.

This adds geometry only: ongoing barrier/extremum invalidation remains separate
unfinished campaign management work. Protected coverage reaches twenty-two
families/40 policies, not a full-product completion claim.

## Liquidity reclaim and swing retest geometry

Added liquidity-reclaim:a:v2 with its source structural stop at the swept prior
level, not the wick extreme. Added breakout-retest:a:v2 using the confirmed swing
level plus one volatility-unit buffer, the more conservative current wick, and
source 0.8–2-unit stop clamp. Both target one mean-range unit and expire after
eight bars. Existing observation predicates retain recent-breach and confirmation
requirements; no independent signals were introduced. Tests distinguish level
from wick stops, mirrored reclaim behavior and stale retest rejection. Pattern
retest b/c measured targets remain unfinished. Coverage: 24 families/42 protected
policies; this does not establish complete economic operation.

## Pattern retest B/C measured campaigns

Pattern detection now exposes the selected structure alongside direction, sharing
one predicate between observation and protection. breakout-retest:b/c:v2 retains
one full pattern-height target with the source clamped structural stop. Double
patterns use their outer extreme; H&S uses right shoulder for top and left shoulder
for bottom, matching the actual source asymmetry rather than silently symmetrizing
it. Source 0.8–2-range stop clamp and eight-bar expiry remain. Tests distinguish
25-unit double-pattern and 45-unit H&S targets from the generic one-range target.
Protected policy count is 44 across 24 families; campaign invalidation, remaining
families and the wider operational scope are still incomplete.

## Market-profile campaign geometry

profile:a/b/c/d:v2 uses the existing complete-prior-session TPO implementation.
Reversion variants A/B/D stop at the previous day's extreme and target POC;
initiative C stops at the opposite value-area edge and targets the prior-day
extreme. These match market_profile_value_area.rs's executable stop/target rules,
not its less precise prose about POC holding levels. Tests verify all four
variants in both directions, exact structural prices and opportunity-limited
expiry. Protected coverage reaches 25 families/48 policies; ongoing validity and
full economic operation remain unfinished.

## Failed-move B–G campaign connections

failed-move:b/c/d/e/f/g:v2 now reuse their causal observation predicates with the
source family's declared one-range stop/target and eight-bar expiry. Reference
levels distinguish setup and later validity; source geometry does not make them
structural stops. Unit-geometry paths explicitly require all 14 volatility bars,
so short observation warmups cannot produce a partial-window risk estimate.
Tests exercise actual B–G setups, directional geometry and insufficient-volatility
rejection. Protected coverage reaches 26 families/54 policies. Funding/OI data
connections, ongoing validity and full economic operation remain outstanding.


## Causal positioning selection transport

Selected observer policies now accept typed positioning readings and forward them
to the catalog. EconomicPaperAdapter accepts the same explicit input and passes
it through selection; absent input remains empty, never inferred from candles.
Selection tests cover funding and OI families, unavailable/future/expired and
other-instrument observations. Existing positioning resolution retains conflict
rejection and decision-time filtering. This is transport, not source qualification:
public auxiliary capture, durable replay identity, protected funding/OI campaigns
and historical trial wiring remain outstanding.

## Funding and positioning campaign geometry

funding:a/b/c/d:v2 and open-interest:a/b/c/d:v2 now require their selected
causal auxiliary-data observation before producing protection. Funding A/B/C
uses the preceding five-bar extreme excluding the current bar; D uses the
current-inclusive ten-bar extreme plus one mean-range14 unit. This preserves
funding_crowding_reversal.rs active A and the frozen Python B/C/D definitions.
OI uses the current-inclusive five-bar extreme from open_interest_divergence.rs.
All target one range unit and expire after eight bars, limited by opportunity
expiry. No missing auxiliary data is inferred. EconomicPaperAdapter carries the
same readings into protection as into selection. Tests cover all variants,
mirrored funding D, structural distances and late/missing input rejection.
Coverage is 28 families/62 protected policies, not full lifecycle completion.
Auxiliary capture, durable source/replay binding and ongoing invalidation remain
unfinished; historical trial calls without auxiliary data abstain.

## Verified captured funding as auxiliary observations

load_settled_funding decodes the existing hash-verified funding artifact into
positioning readings. Availability is capture receipt, never historical funding
time. An explicit positive max_age_ns expires each observation from settlement;
it is a caller economic policy, not an inferred venue interval. Old records can
therefore already be expired at receipt. Duplicate identical rows collapse;
conflicting values, wrong symbols, future settlements and non-finite rates fail.
Tests also prove receipt-time gating and reject substituted source bytes. This
adapter does not certify historical PIT or authenticate the venue; CLI policy
binding, repeated-capture reconciliation and OI/ratio acquisition remain open.

## Paper funding policy wiring

PaperConfig now carries optional strict positive funding_max_age_ns. Paper replay
loads verified funding readings from every capture when this policy is explicit,
and supplies them to economic selection/protection. Missing policy means no
funding input. Each reading remains unavailable until its own receipt even when
all capture files are loaded before replay. Repeated unchanged event/value/expiry
records are corroborating receipts, not conflicts; changed values or validity
remain rejected once both are known. Tests exercise late revision gating and
repeat-receipt behavior. Config serialization binds freshness into frozen policy.
No historical trial timing upgrade or OI capture is implied.

## Captured funding native boundary qualification

Native paper integration tests now carry hash-verified test capture funding
through decoding, selected family observation and structural protection. An
otherwise identical capture received one nanosecond after decision produces no
support or protection at that decision. The timely capture supports funding B
and its protection but creates no campaign without verified calibration. Both
cases execute through Nautilus callbacks; these are isolated fixtures, not real
prospective economic observations or a completed operational acceptance.

## Paper CLI economic policy input

The paper command accepts --policy-config PATH for JSON observer_policy,
grammar_policy, campaign_policy, stop_budget and funding_max_age_ns. Financial
CLI assumptions remain separate and cannot be overridden from that file. The
combined configuration is validated before session work and frozen before any
capture; changing freshness or selection requires a new run. Tests verify
roundtrip freeze, changed-policy rejection, strict freshness integers and forbidden
fields. No value is selected on the owner's behalf or economic eligibility minted.

## Optional public OI snapshot capture

Capture supports --include-open-interest, storing the unmodified public response
from /fapi/v1/openInterest with URL, hash and request/receipt times. Official
Binance Open Interest documentation was inspected: the response is present OI,
with openInterest, symbol and millisecond transaction time; it is not an OI
change series. Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest
load_open_interest validates the complete capture and decodes receipt-available
readings with explicit event-based freshness. Older captures without this optional
artifact return no readings. Tests cover actual capture/verification/decoding
boundaries with isolated responses, causal availability and expiry. Paper config
wiring, ratio acquisition and real public qualification remain outstanding.

## OI policy wiring and real public capture

PaperConfig/--policy-config accepts open_interest_max_age_ns as an explicit strict
positive integer. Paper captures request OI only when configured, then decode all
available receipts into the existing causal observer/protection path. The setting
is frozen with the run; changes require a new run. Tests cover strict validation
and restart identity; the complete suite passes (351 tests).

A real unauthenticated capture succeeded at
/tmp/v8-next-public-oi-1788872219674838000/manifest.json. The verified decoder read
BTCUSDT OI 109201.379, event_ns 1788872216074000000, received_ns
1788872223557289000, source SHA256
04a7951b81a2cc94c546236fc5a9a5f47a63be27f0d2e82986cb22757e58fb50.
It was fresh under an explicitly supplied 300-second development policy; this
policy is not an inferred or recommended trading threshold. This demonstrates
public acquisition and decoding, not positioning-strategy profitability, OI change
measurement or full paper execution. Long/short-ratio acquisition remains missing.

## Explicit global account-ratio source

Optional account_ratio_period capture uses the public globalLongShortAccountRatio
endpoint with explicit supported period and limit=1. load_account_ratio checks
source period against policy, validates symbol/finite nonnegative value/clocks,
and makes the measurement available only at receipt. It does not recalculate
longShortRatio from rounded account proportions. This is all-trader account-count
skew, not top-trader or position-notional skew. Official documentation inspected:
https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Long-Short-Ratio
The documentation defines timestamp as period end in milliseconds. Tests qualify
capture, source-period mismatch and receipt gating. Paper configuration/CLI and
real public acquisition remain unfinished for this input.

## Account ratio paper policy and public acquisition

Paper policy now accepts account_ratio_period and account_ratio_max_age_ns only
as a complete pair. The period is a supported literal and freshness a strict
positive integer; both are frozen with the session. Capture requests the chosen
period and paper replay loads the verified observations into existing causal
selection/protection. Missing optional artifacts remain absent. The full suite
passes (356 tests), including incomplete/invalid policy rejection.

Real public capture succeeded at
/tmp/v8-next-public-ratio-1788872382073361000/manifest.json. The 5m global account
ratio was 1.2873 with event_ns 1788872100000000000 and receipt_ns
1788872385753220000; artifact SHA256
921674c6f24ab87ff239e9d7d79c19974f492abc890a71da33e916295d0f8228.
The explicit 600-second development freshness check passed. These are acquisition
observations, not fitted policy choices or profitability evidence. Full economic
calibration, campaign validity, portfolio and continuous operational work remain.

## Decision quote follows auxiliary receipts

Capture now requests its decision quote after optional OI/account-ratio inputs.
Previously those requests followed the quote, so the new inputs were correctly
unavailable at the same capture's decision. Reordering requests makes timely use
possible without changing timestamps. A strictly increasing-clock test proves
both auxiliary receipts precede quote receipt. The full suite passes (357 tests).

A real paper step with funding/OI/account-ratio policies and a replay-only restart
succeeded at /tmp/v8-next-positioning-paper-1788872464386406000; the full returned
state matched on restart. Log: /tmp/v8-positioning-paper-check.log. One public
capture, zero orders. Fee/freshness/limit values were explicit development
assumptions. This is no-trade acquisition/recovery evidence only, not position-
bearing operation or calibrated economic success. Policy remains source-frozen;
subsequent source edits require a new run as designed.

## Initial funding observation window correction

Paper capture previously began funding history at policy freeze, excluding the
last settled rate still valid under a configured freshness window. Requests now
begin at max(0, freeze - funding_max_age_ns), preserving the full session's
liabilities as well as the initial observation window. No historical availability
is inferred: rates are still known only at capture receipt. Boundary tests cover
no policy, a pre-freeze window and epoch clamping.

Real paper acquisition at /tmp/v8-next-funding-window-1788872557488881000 returned
one funding record; receipt-causal lookup at the quote decision returned
0.00008180. Zero orders were generated. Log: /tmp/v8-funding-window-check.log.
The eight-hour freshness and fee/limit inputs were explicit development
assumptions, not optimized economic settings. Long sessions still fail on bounded
funding-history truncation until pagination/settlement continuation is qualified.

## Frozen funding thesis validity reference

Funding protection now retains the source confirmation barrier separately from
its executable stop, and controller admission carries it into the serialized
campaign. This distinction is essential for D: its stop includes one range unit
beyond the barrier, but source still_valid rejects a close at/through the bare
barrier. PaperCampaign.invalidated_by_close returns an explicit unknown when the
reference or a later continuous causal bar is absent; otherwise it evaluates the
source strict long-above/short-below rule. It does not reevaluate the entry signal.
Tests cover both D directions, distinction from stop, later-bar eligibility and
serialization. Native close dispatch and durable invalidation replay are still
unfinished; this commit does not claim operational thesis exits are active.

## Native thesis exit and accounting replay

PaperCampaignAdapter evaluates frozen close-validity barriers at matching native
quote receipt callbacks before advancing campaigns. A later observed invalidating
close prevents pending entry or routes an existing campaign through the native
cancel/reduce-only-close path. Existing filled-exit ownership guards remain.
The invalidation timestamp is recorded separately from entry invalidation and
native fill records. EconomicPaperAdapter supplies its causal frames; revised
accounting rebuilds the same receipt-known frames from verified capture candles,
without rerunning expert selection or calibration. Unknown validity does not
cancel existing native protective orders.

Native tests cover both pending and position-bearing cases, close before timeout,
serialized campaign restoration and identical engine-state replay. Full suite:
364 tests before the added repeat-replay assertions; focused native tests pass
with those assertions. This activates the funding frozen-barrier rule only;
other expert-specific validity and wider operational requirements remain open.

## OI validity and shared historical close handling

OI A–D now freeze the recent price extreme as their close-validity barrier, as
open_interest_divergence.py still_valid specifies: strict close above for long,
below for short. This uses the unrounded source level, not a venue-rounded stop.
All positioning geometry tests now assert the retained source reference.

The common native adapter exposes observe_validity for both quote and historical
bar paths. HistoricalTrial builds its current causal frame and checks existing
campaign theses before advancing native entry/exit, while retaining pre-action
native equity marking. Newly selected campaigns receive the frozen barrier too.
Historical auxiliary data remains absent unless explicitly supplied; this does
not turn REST receipt-time readings into historical PIT data. Full suite passes
(364 tests); economic calibration and remaining family validity are still open.

## Structural family thesis references

Liquidity reclaim now retains its swept level; failed breakout retains the
original failed-breakout barrier; retest A retains its swing level and B/C the
pattern neckline/validation level. These follow the frozen Python still_valid
rules, with strict close on the retained side. Retest validity is distinct from
its buffered/clamped stop. Profile A/B/D retain prior-day extremes; initiative C
retains POC, explicitly distinct from its opposite-value-area stop. No moving
reference is substituted after entry. Existing controller/native/accounting paths
carry and evaluate these barriers. Geometry tests cover their exact references
and mirrored profile/reclaim cases. Full suite passes (364 tests). Other families'
non-level validity rules and broader economic delivery remain incomplete.

## Historical bar thesis-exit qualification

A native HistoricalTrial test now opens a serialized protected campaign, supplies
an invalidating later bar close inside the stop/target band, verifies actual
position closure before expiry, and reconstructs identical native state on a
second run. Three pre-action equity marks remain present. Test bar prices and
volumes use the instrument's required precision; the initial invalid-precision
fixture was rejected by Nautilus and was corrected, not treated as a fill.
This test qualifies the historical integration beyond reference serialization;
it does not supply real calibration or prospective economic evidence.

## Pivot, range and gap close-validity rules

Floor pivot retains the exact unrounded traded pivot for thesis validity; range
breakout retains the broken prior-range high/low rather than its range-height
stop. Gap A/B/C retains bottom for long and top for short per source still_valid.
All feed the existing native/revised replay validity path. Tests cover mirrored
levels, gap variants and the distinction between rounded pivot stop and exact
pivot validity. Donchian is intentionally not assigned a frozen barrier: its
source validity uses a live channel and needs a separate rule. Fifteen relevant
tests passed, with Ruff/mypy clean. Remaining economic scope stays open.

## Donchian live channel validity

Donchian active A campaigns now carry live_channel_bars=20 through protection,
admission, serialization, historical trial and revised-accounting replay. The
close-validity evaluator recomputes the prior twenty-bar low (long) or high
(short), excluding the current bar, matching state.rs fixed-window feature
bounds and the source expert's channel exit. It does not freeze entry-time channel
levels or allow the current adverse wick to move the exit threshold. Incomplete
windows remain unknown; simultaneous frozen/live validity definitions reject.
The live predicate is generic, but active Donchian selection remains long-only.
Tests cover warmup, current-wick exclusion and serialization; full suite passes
(366 tests), Ruff/mypy clean. Other validity and operational scope remain open.

## Candle, measuring and point-and-figure validity

Eight candle variants now retain the source trigger_reference for close validity,
not the clamped protective stop. Measuring H&S/double/triangle retains the frozen
completion line. Point-and-figure A–D retains the breakout column origin (lowest
X/highest O), consistent with the source stop/validity reference. Existing native,
historical and revised-accounting paths evaluate these serialized references.
Tests check all candle/P&F variants and three measured patterns; the full suite
passes (366 tests), Ruff/mypy clean. This does not complete remaining dynamic
indicator validity, calibration, multi-instrument allocation or prospective
position-bearing operations.

## Live Kijun thesis validity

Ichimoku cross campaigns now serialize validity_indicator=kijun26 and use the
current-inclusive 26-bar high/low midpoint for continued validity, matching the
source still_valid method. Long close must remain strictly above, short below;
equality invalidates. This differs from Donchian's prior-only channel. Incomplete
windows remain unknown and ambiguous mixed validity definitions reject. Controller,
historical trial and revised replay carry the indicator rule. Tests cover moving
current-window extrema, both directions, equality, warmup and serialization.
Full suite: 368 passing; Ruff/mypy clean. EMA and other remaining validity rules,
calibration, portfolio and operational qualification remain unfinished.

## EMA trend thesis continuation

Trend pullback now carries ema5-above-ema20 validity; depth combines the same
live alignment with its frozen confirmed impulse swing low. The calculation
reuses Polars-backed trend_emas and its existing seed/warmup convention. An intact
trend can remain valid without a fresh below-EMA entry setup. Fast<=slow invalidates;
missing warmup remains unknown. Tests separate continued trend from new entry,
flat alignment failure, structural-depth failure and serialization. Existing
native/historical/revised replay machinery carries both forms. Full suite passes
(369 tests), Ruff/mypy clean. This is not completion of all remaining methodology,
calibration, portfolio or operational requirements.

## Volume-family frozen validity

OBV/ADL and volume-climax campaigns retain the detection bar's low for long/high
for short. Volume-confirmed breakout retains the broken prior twenty-bar extreme.
These are the source still_valid references, distinct from their active one-range
protective stop. Existing native exit and replay paths consume the serialized
levels; tests assert the references alongside unchanged risk geometry. Full suite
passes (369 tests), Ruff/mypy clean. MACD's live zero-line rule remains separate
and is not approximated by these structural references.

## Shared MACD zero-line validity

MACD/stochastic campaign validity now holds long only above zero and short only
below zero, as source still_valid specifies. A shared macd_line calculation serves
both entry observation and continuation; Polars EMA12/26 use existing first-close
seeding and the source state.rs 34-bar availability gate. Zero invalidates both
directions; incomplete windows remain unknown. The serialized indicator routes
through existing native/historical/revised replay paths without requiring another
stochastic entry run. Full suite passes (371 tests), Ruff/mypy clean. Broader
remaining economic requirements are not completed by this change.

## RSI active reversion continuation

Active RSI reversion A now carries rsi14-reversion validity. Long remains valid
only above RSI30, short below RSI70, matching source still_valid; re-entering the
extreme (including equality) invalidates. It reuses the observer's Polars-backed
Wilder RSI seed/recurrence and neutral flat-series convention, without requiring
a new recovery-price entry trigger. Fifteen bars are required for fourteen price
changes; insufficient data stays unknown. Tests cover directional extremes,
neutrality, warmup, serialization and protection binding. Full suite passes
(373 tests), with the added protection assertion checked in focused tests.
Bollinger and remaining family/economic requirements are still open.

## Frozen Bollinger continuation bands

Breakout A retains the setup-run midpoint; B/C retain the broken two-sigma band.
Active fade A retains its setup-run adverse three-sigma boundary. Fade distance
and validity now derive together from the same anchor calculation, preserving
existing clamped risk distance while preventing later band drift. These exact
references, not tick-rounded stops, feed shared campaign close validity. Tests
cover breakout variants in both directions and mirrored fade outer bands. Full
suite passes (373 tests), Ruff/mypy clean. No additional inactive fade variant
or complete economic-operation claim is introduced.

## Fibonacci continuation references

Active retracement campaigns retain the confirmed impulse's 78.6% retracement
as the invalidation level; projection reversals retain the rejected 161.8%
extension. Both follow source still_valid and use the same confirmed impulse as
observation, distinct from active one-range stops. Controller and native/revised
replay already serialize/evaluate these references. Relevant tests verify exact
levels and directional setups (4 passed); Ruff/mypy clean. Confluence has mixed
strict/non-strict boundary and oscillator conditions and remains separate work.

## Confluence composite continuation

Confluence A/B now freezes the 78.6% impulse level and detection-time adverse
three-sigma band, and combines them with live RSI reversion validity. A strict
cross of the Fibonacci level invalidates (equality allowed); equality at the
outer band invalidates; RSI re-entry also invalidates. Known price failures are
checked even if oscillator warmup is missing. The additional strict breach level
is serialized through native/historical/revised replay. Tests distinguish these
boundaries in both directions and roundtrip the composite campaign. The prior
full suite passed (373 tests); added focused composite assertions also pass.
This preserves source methodology, not a full economic-operation claim.

## Divergence confirmation and extremum validity

Divergence A/B now carries the conjunction of strict barrier and second-extremum
hold conditions. Because both constrain the same close and direction, the exact
predicate reduces to max(barrier, extremum) for long and min for short; no
additional exit infrastructure is needed. The frozen tighter level feeds existing
native/replay validity, distinct from active one-range stops. Tests compare the
reduced predicate against both original inequalities at each boundary and the
observed close, in mirrored setups. Three relevant tests pass; Ruff/mypy clean.
Remaining failed-move and broader economic requirements stay open.

## Failed-move continuation references

Failed-move B–G now preserves each selected setup's reference through campaign
close validity: confirmed swing, inside-bar side, prior gap side, prior Kijun or
prior range as applicable. No shared arbitrary stop is substituted. Existing
variant tests verify reference retention alongside source one-range geometry;
full suite passes (374 tests), Ruff/mypy clean. This completes this pass over
protected expert-family continuation wiring, not full product port acceptance.
The minimal squeeze policy, integrated calibration, multi-instrument allocation,
continuous/reconciled funding operation and prospective position-bearing evidence
still require completion and independent qualification.

## Calibration source runtime identity

Calibration source inspection now requires the current code/dependency identity
to equal the source run's frozen identity before any evaluation or replay. A
matching recomputed output under different code is insufficient policy evidence;
missing identity also rejects. Tests preserve forged-campaign rejection and prove
changed/missing runtime rejection before source recomputation. Three focused tests
pass; mypy clean. This does not introduce a calibration estimator or claim receipt;
real eligible outcome estimation and economic admission remain unfinished.

## Economic effect magnitude alongside WRC

WRC now reports each candidate's observed mean baseline-minus-variant interval
loss and the sample standard deviation of bootstrap means, using the same joint
circular-block draws as its existing family test. No extra resampling, zero-loss
imputation or gross-edge assumption is introduced. Outputs explicitly retain
input-loss units and in-sample baseline-relative scope; standard error is not a
confidence bound, calibrated forecast, multiplicity-adjusted interval or utility
receipt. Existing compare-family output carries these values automatically.
Tests use known draw means for exact arithmetic and native library repeatability;
clone uncertainty compares within floating-point tolerance. Full run passed 375
other tests; the corrected focused WRC tests pass. Calibration admission remains
separate unfinished work.

## Real-data effect output qualification and policy labels

The complete registered donchian-pbo-development-v1 family was recomputed through
compare using existing real-source trial artifacts (498 intervals), explicit
baseline, block=12/reps=999/seed=42. Output:
/tmp/v8-real-family-effect-estimates.json. Both candidate mean baseline-relative
loss improvements were negative (-2.434467222891568e-6 and
-2.1580937188755034e-6 per fixed-initial-capital interval), with bootstrap mean
standard errors 1.4702927152347783e-6 and 1.5427975911227134e-6. These remain
in-sample historical-model comparisons, not prospective calibration or proof of
profitability. No utility admission was opened.

Family reports now include trial_policies keyed by validated trial ID so effect
magnitudes can be interpreted against actual frozen observer/campaign/fee/risk
settings rather than opaque hashes alone. This is a presentation of existing
validated configuration, not another authority mechanism.

## Ordered portfolio allocation planning

Added a pure ordered batch admission boundary using existing campaign/risk
admission. Explicit caller priority determines order; accepted lot-rounded
notional is reserved before evaluating the next proposal. Rejected and duplicate
opportunities consume no additional reservation. Per-exposure snapshots must
agree on global equity, gross exposure, reservations, time and reconciliation.
The existing scalar reservation model conservatively charges reservations to
all exposures; this is not diversified exposure optimization. Caller remains
responsible for atomic application and verified calibration provenance.

Four tests cover aggregate capital exhaustion, rejection/duplicate handling,
inconsistent or missing account snapshots and lot-rounded reservation amounts.
Full suite: 380 passed; Ruff/mypy clean (71 source files). This module is not yet
wired into native multi-instrument execution and does not add portfolio stop-heat
allocation. Those integrations and the remaining full economic requirements
remain open; no production calibration or trading authority was enabled.

## Shared stop-risk allocation

Ordered allocation now accepts the existing explicit StopBudget and reconciled
StopExposure. Each accepted lot-rounded quantity reserves its nominal distance
to stop and one campaign slot before the next admission. Rejections consume
neither; the supplied snapshot remains immutable. Missing, stale or unmatched
budget/exposure inputs retain controller rejection semantics. Nominal stop risk
is not a gap-loss guarantee. Existing policy rejects when a full per-campaign
budget would exceed portfolio heat; no implicit remaining-heat sizing was added.
Five allocation tests pass, including shared heat/concurrency exhaustion and
missing/stale inputs; Ruff/mypy clean. Native batch execution and calibration
qualification are still required before this can authorize product operation.

## Exposure-specific reservation accounting

RiskSnapshot now optionally carries exposure_reserved_notional separately from
global reserved_notional. Missing detail retains the conservative legacy scalar
behavior; supplied detail must be finite, nonnegative and no larger than global
reservations. Ordered allocation reserves new admissions globally and against
only their own exposure. It does not net away opposing campaigns or invent
correlation offsets. A two-instrument test verifies preexisting BTC reservations,
independent ETH capacity and shared global exhaustion. Full suite: 382 passed;
Ruff/mypy clean. Native snapshot production and batch execution remain separate
integration requirements; this does not establish live portfolio qualification.

## Unsubmitted campaign price-band reservations

Batch admission now bounds quantity using the maximum protected band price for
notional and the full stop-to-target distance for nominal stop risk, matching
native_stop_exposure's unsubmitted reservation interpretation. Both the first
admission and later reservations use these bounds; simply reserving a larger
amount after admission would itself permit over-allocation. Lot rounding remains
native instrument constrained. Updated tests cover shared capital, per-exposure
capacity and heat with these conservative pending-entry bounds. Actual market
gaps can exceed the band: this is not a guaranteed execution price or maximum
loss. Native submission/reconciliation integration remains outstanding.
Full suite passes (382 tests); focused allocation tests and Ruff/mypy pass.

## Native portfolio risk projection

A read-only adapter now projects native open-position quantities at explicit
same-clock marks into global and per-exposure notionals, plus unsubmitted
protected-band reservations. Existing native stop coverage validates protection
and supplies portfolio heat/campaign count. Unknown instruments, missing marks,
unreconciled accounting and unsupported in-flight entries return absence.
The caller must supply reconciled same-quote-currency equity and the supported
linear instrument mapping, synchronously on the native event thread. This does
not calculate funding-adjusted equity or claim inverse-contract support.

Tests cover two-instrument pending reservations and actual native open-position
projection through the existing engine fixture. Full suite: 383 passed;
Ruff/mypy clean. The paper app still needs reconciled accounting and multi-asset
feed/admission integration before this projection can enable continuous operation.

## Paper admission uses native portfolio projection

EconomicPaperAdapter now obtains both notional snapshots and optional stop
exposure from native_portfolio_risk instead of constructing local zero-valued
risk snapshots. Existing empty-order/position/history guards justify cash equity
and no unresolved funding in this initial admission branch. Missing projection
records UNRECONCILED_PORTFOLIO_RISK and creates no campaign. The single-exposure
and post-position funding guards remain; this integration does not claim their
resolution or enable multiple native campaigns. Full suite: 383 passed;
Ruff/mypy clean, including existing native economic admission tests.

## Funding query coverage across captures

Position coverage now accepts a contiguous chain of overlapping bounded REST
responses known by the accounting cutoff, retaining hashes of the contributing
sources. It never bridges a gap, crosses instruments or consumes a later receipt.
The check remains conservative about interval endpoints and does not infer a
funding schedule. Six settlement tests pass, including chained coverage and
adversarial gap/future/wrong-instrument cases; Ruff/mypy clean. Coverage still
reports cashflow_finality=UNQUALIFIED and does not lift the online funding guard.

## Funding announcement identity and knowledge cutoff

Observed announcement matching now keys settlement evidence by instrument and
boundary together. A same-time payment for another instrument cannot satisfy
an announcement. Final records must also have boundary <= receipt <= evaluation
cutoff; future or pre-boundary receipts cannot conceal missing settlement.
The existing timestamp summary remains compatible and conservative when any
instrument lacks payment. Six settlement tests pass with wrong-instrument and
receipt-clock adversarial assertions; Ruff/mypy clean. This corrects matching
semantics without certifying funding completeness or changing admission gates.

## Standalone capture account-ratio option

The public capture CLI now exposes --account-ratio-period with the existing
supported period set, forwarding it to the same verified acquisition path used
by paper configuration. Actual CLI acquisition with 5m ratio and open interest
succeeded: /tmp/v8-next-ratio-cli-qualification-1957096/manifest.json. This is
real public snapshot data, not historical PIT evidence or calibrated edge.
Ruff/mypy pass. No new infrastructure or private exchange access was added.

## Protected paper campaigns use allocation admission

Protected EconomicPaperAdapter proposals now pass through allocate_ordered using
the native portfolio snapshot and stop exposure. Timeout-only/missing geometry
keeps the existing controller path. Single-exposure gating remains pending broader
native execution qualification. The integration exposed a real minimum-notional
case: a 1.05 quote-currency request cannot fund a 0.010 quantity across a 113 band
ceiling. Native tests now verify rejection at 1.05 and successful bracket lifecycle
at 1.13, with no calibration bypass. Full suite: 386 passed; implementation
Ruff/mypy clean. Real calibration and post-position accounting remain open.

## Native contract valuation boundary

Portfolio projection now inspects native instrument metadata before using linear
quantity-times-price valuation. Missing metadata, inverse contracts, mismatched
quote/settlement currencies and non-unit multipliers return absence. The explicit
settlement currency defaults to the current USDT scope; no FX conversion is
invented. Tests reject inverse and mismatched settlement instruments, while the
native economic and open-position tests pass with actual engine metadata.
Full suite: 386 passed; Ruff/mypy clean. Broader contract support remains outside
this projection until its valuation is implemented and qualified.

## Real paper/restart qualification after portfolio integration

Ran the production paper step against a new actual public capture with
families:pandf-breakout / volatility-extreme-v2 / pandf:a:v2, 5m account ratio
and open interest. Explicit simulation assumptions: maker=0.0002, taker=0.0005,
initial cash=10000, requested notional=100, exposure fraction=0.1; auxiliary
freshness 600s ratio / 300s OI. Immediate replay-only restart produced an exactly
equal returned result. Artifact directory:
/tmp/v8-next-allocation-real-1978039; native process log:
/tmp/v8-allocation-real-restart.log. One capture, zero orders/positions.
This validates real acquisition and deterministic no-trade restart after the
integration. It does not prove that an eligible opportunity exercised allocation,
position-bearing operation, calibration, funding completeness or profitability.

## Calibration sample censoring visibility

Calibration inspection now lists every unresolved sample gate rather than only
one precedence reason. Mixed open/closed positions explicitly require a censoring
or horizon policy: selecting only completed outcomes can bias calibration.
Funding and statistical-family requirements remain visible simultaneously, and
eligible_for_utility remains false. Four calibration-source tests pass;
Ruff/mypy clean. No estimator, fabricated utility or authority promotion was added.

## Baseline and variant sample readiness in reports

Comparison reports now expose baseline_blockers computed from the baseline's
own revised accounting, separately from variant_blockers. Baseline open outcomes
and incomplete funding cannot be hidden behind the selected policy's first
rejection reason. Missing baseline position records remain explicitly unavailable.
This is diagnostic readiness, not a replacement for aligned paired intervals or
statistical qualification. Five report/calibration tests pass; Ruff/mypy clean.

## Explicit funding capture interval from CLI

Standalone capture exposes --funding-start-ms (inclusive Unix milliseconds),
forwarded to the existing bounded request path. End time is recorded at capture;
saturated responses still reject rather than silently truncate. CLI help and the
two bounded-response tests pass, Ruff clean. This exposes existing acquisition
semantics for operator-selected exposure windows; pagination and cashflow
finality remain unresolved.

## Native in-flight reservation gap

Confirmed the pinned native cache exposes orders_inflight. Stop/portfolio risk
projection now returns absence while any submitted/in-flight order exists,
including the interval before it appears in orders_open. This prevents a flat
position/open-order view from being mistaken for zero outstanding risk. Pricing
and reconciling partial/in-flight reservations remains unfinished; no custom OMS
was introduced. Full suite: 388 passed; Ruff/mypy clean. The test explicitly
exercises an in-flight-only cache without allowing other zero-state reads.

## Instrument-scoped native validity frames

Campaign validity frames are now keyed by instrument plus receipt clock, avoiding
same-time cross-instrument overwrites. Native callbacks validate both identity
components before applying thesis rules. Economic paper and revised accounting
construct the same keyed representation. Native thesis exit/replay tests include
an unrelated ETH frame at the identical BTC clock and retain the BTC outcome.
Full suite: 388 passed; implementation Ruff/mypy clean. This removes a multi-asset
collision without claiming complete multi-asset data or campaign operation.

## Two-instrument native campaign isolation qualification

Added an actual native-engine test with simultaneous BTC and ETH protected
campaigns and identical quote clocks. BTC expires and closes while ETH remains
open with both its protective orders intact; native closure snapshots contain
only BTC. The test uses synthetic fixtures exclusively inside the test harness.
Focused native test passes, Ruff clean. This qualifies cross-instrument timeout
isolation in the existing adapter, not multi-asset economic admission, funding
reconciliation, live operation or prospective economic evidence.

## Allocation-to-native two-instrument qualification

The simultaneous native campaign test now starts with actual AllocationProposal
admission against shared account snapshots. Test-only utility inputs authorize
two protected campaigns whose worst-band reservation totals 2.20. These generated
campaigns execute in Nautilus; BTC timeout still leaves ETH and its protection
intact. Focused integration test and Ruff pass. Calibration is explicitly a
fixture, not a production provider; real feed-driven multi-asset admission and
post-position accounting remain unfinished.

## Mixed open/closed two-instrument replay qualification

The two-instrument native fixture now serializes admitted campaigns and restores
them into a fresh engine without rerunning allocation. Full economic state
comparison covers balances, commissions, order status and both the closed BTC
and still-open ETH position. The fresh engine preserves the same protective
orders and timeout isolation. Focused test and Ruff pass. This is bounded native
replay with test data, not crash-safe live recovery or funding-qualified paper
continuation.

## Multi-instrument native funding and replay

Extended the allocation/native replay fixture with a final funding update for
both instruments after BTC has closed while ETH remains open. Explicit native
mark prices are supplied and each funding event is duplicated. The resulting
balance is exactly 9999.987 from initial 10000: three 0.001 commissions plus a
single 0.01 ETH funding debit. BTC receives no post-close debit. Fresh-engine
replay preserves the complete economic state. All inputs are test fixtures;
this does not establish REST settlement completeness or actual venue cashflow
finality. Full suite: 389 passed; Ruff clean.

## Squeeze baseline protected campaign

Added selectable squeeze:baseline:v2 protection: two source range units to stop,
four to target, expiry capped at 336 bars and the opportunity lifetime. Source:
v8-core/src/experts/squeeze_swing.rs constants and state.rs::atr_series, whose
ATR label actually means trailing 14-bar mean high-low range, not Wilder true
range. Existing squeeze observation is required; no calibrated edge is inferred.
Tick rounding uses existing risk-tightening rules. This is the active baseline
policy, not m1/m2/m3 variant parity, and retains current native quote execution
rather than claiming legacy NEXT_BAR_CLOSE entry parity. Full suite: 390 passed;
Ruff/mypy clean. Real calibration and integrated economic operation remain open.

## Explicit squeeze variant selection

Added selectable squeeze:m1/m2/m3 observers and matching protection policies.
Source rank/lookback/volume thresholds are (0.25,48,1.40), (0.30,72,1.35),
(0.25,72,1.40). Variants require their own prior-bar breakout and complete
lookback in addition to existing feature warmup; the baseline preserves its
existing grammar-bound behavior. Stance variant IDs distinguish experiment
selection without manufacturing independent evidence. New policies use explicit
prior 48/72 bars rather than the legacy slice's 47/71, consistent with the
new product's baseline convention. Tests exercise m1 support/protection and
72-bar variants rejecting insufficient history. Existing full suite passes
(390 tests), focused assertions pass, Ruff/mypy clean. Full variant qualification
and prospective economic admission remain unfinished.

## Squeeze baseline direction/domain qualification

The baseline squeeze observer now checks the same instrument and actual prior
48-bar breakout direction itself, as the new variants already do. Relying only
on the caller's opportunity was unsafe when selecting broader grammars: a long
compression release could otherwise support an unrelated short opportunity.
Mirrored long/short protection tests verify two/four-range geometry, and mismatched
direction/instrument abstains. This deliberately tightens the previous baseline
behavior and therefore changes frozen runtime identity. Full suite: 390 passed;
Ruff/mypy clean. No calibration or execution authority is inferred from support.

## Macro squeeze window qualification

Added positive m2/m3 observation and protection tests with complete 73-bar input
in both directions. Changing only the oldest prior bar's high/low blocks the
72-prior-bar breakout, proving that endpoint is included rather than silently
using 71 bars. Both variants then abstain and withhold protection. Two squeeze
tests pass, Ruff clean. These synthetic behavioral checks do not certify
strategy economics or complete the remaining product requirements.

## Real snapshot squeeze configuration qualification

Validated all four observer/protection selections through PaperConfig and ran
policy_stances over a previously verified real BTC capture, with bars becoming
known only at their recorded receipts. Artifact: /tmp/v8-squeeze-real-2070118.json;
source: /tmp/v8-next-ratio-cli-qualification-1957096/manifest.json. All variants
returned NO_OPPORTUNITY under volatility-extreme-v2; no fabricated opportunity,
metric or order was introduced. Output records source/runtime identity and
receipt-known diagnostic scope. This verifies selectable wiring on real input,
not positive-signal economics. Source review confirmed the 0.18 efficiency
threshold remains common to the variants.

## Historical trial and paper reservation alignment

Protected historical trials now size notional at the maximum protected-band
price and nominal stop risk over the full band, matching unsubmitted paper
allocation assumptions. The existing stop budget reconciliation/heat checks
remain; venue minimum notional is also checked at the observed decision price.
Timeout-only trials retain their previous sizing. This changes frozen trial
runtime identity; old results are not silently relabeled. Historical trials
remain counterfactual policy experiments, not utility-admitted economic orders.
Full suite: 391 passed; Ruff/mypy passed before the final minimum-notional guard,
and the full suite also passed after that guard.

## Native historical reservation boundary assertions

Strengthened the historical native integration test to verify full-band nominal
stop risk, rather than the obsolete decision-close distance. The admitted lot
fits its explicit budget and one additional venue lot would exceed it. The same
maximal-feasible-lot check covers protected notional at the band ceiling. All
39 native integration tests pass; Ruff clean. These assertions qualify the
recent sizing change, not economic profitability or complete operation.

## Multi-instrument historical valuation dependency audit

Inspected HistoricalTrial before widening subscriptions/source keys. Its source
map and prefix are single-instrument, but changing those alone is insufficient:
mark_equity rejects any open position on another instrument and requires strictly
increasing bar boundaries, excluding equal-time cross-instrument callbacks.
Existing paired interval evaluation expects the resulting single chronological
account series. Consequently the next multi-asset historical step must first
supply a coherent portfolio mark at each evaluation boundary, with explicit
known-price freshness and missing-mark behavior, and avoid double-counting two
same-time callbacks as two economic intervals. Native campaign isolation tests
do not prove this valuation contract. No subscription or claim gate was widened
under the false assumption that tuple keys alone establish portfolio backtesting.
This narrows the integration dependency: portfolio valuation/aligned interval
construction precedes multi-instrument HistoricalTrial enablement.

## Shared native equity projection

Added native_equity: cash plus native per-position unrealized PnL using explicit
instrument marks and a caller-declared freshness limit. Missing/future/stale marks
or currency mismatch return absence; no FX or funding correction is fabricated.
HistoricalTrial now uses this projection with its current single-bar exact-clock
mark, preserving its single-instrument scope. Native two-instrument replay tests
value the remaining ETH position at an explicit mark and reject missing/stale
marks. Full suite passed 391 tests before those additional assertions; focused
native test passes afterward, Ruff/mypy clean. Common evaluation-phase alignment
is still required before enabling multi-instrument historical callbacks.

## Portfolio mark event/receipt separation

EquityMark now requires both event and observed timestamps. Valuation requires
0 <= event <= receipt <= valuation clock and measures freshness from event time,
so a newly received stale market price cannot qualify as current. Historical
native bars supply their explicit event/init clocks. Native tests reject stale
events with fresh receipts, future receipts and reversed clocks; all 39 native
tests pass, Ruff/mypy clean. This strengthens mark eligibility before common
multi-asset evaluation-phase alignment is implemented.

## Shared market mark clocks for notional risk

Native portfolio risk now consumes EquityMark with separate event/receipt clocks,
matching native equity eligibility. It rejects future/reversed timestamps and
uses event age against an explicit max_mark_age_ns (default exact boundary).
Paper passes actual quote event/init clocks; current flat admission remains
unchanged. Native position tests use real callback clocks. Full suite: 391
passed; Ruff/mypy clean. This unifies valuation inputs without enabling unsupported
continuous multi-asset accounting or relaxing freshness silently.

## Observed return component decomposition

Closed native outcome rows now separate price PnL from commissions, funding and
other native PnL adjustments, with entry-notional normalized components. The
identity is net = price - commissions + funding + other adjustments; costs are
not subtracted twice. Missing adjustment PnL withholds the derived price component
and marks the decomposition incomplete. This is descriptive native accounting,
not expected gross edge, calibrated utility or measured execution costs.
The native fee/funding test verifies exact reconstruction of net return; all 39
native tests pass, Ruff/mypy clean. Calibration remains ineligible.

## Missing adjustment components remain absent

Observed return decomposition now withholds funding/other-adjustment amounts
and normalized returns when that component contains an unknown native PnL change.
It does not report a partial sum as the full component. The known native net PnL
remains available, while derived price PnL is withheld. Native test variations
cover missing funding and missing non-funding adjustments; focused test passes,
Ruff/mypy clean. This preserves missingness, not calibration eligibility.

## Complete-universe equity boundary

Added aligned_native_equity: every explicitly required instrument must have a
mark for the same market boundary, received by valuation time. It delegates
cash/PnL to native_equity and never forward-fills absent inputs. Even a currently
flat required instrument must supply its boundary mark, preventing changing
sample membership with position state. Native integration tests with BTC/ETH
verify complete valuation and missing/stale boundary rejection. Focused test and
Ruff/mypy pass. Event-phase invocation and one-row-per-boundary integration remain
the next dependency; this helper does not itself implement a scheduler or claim
multi-instrument HistoricalTrial completion.

## Historical portfolio boundary integration

HistoricalTrial now keys source bars by instrument/time and maintains per-symbol
feature prefixes. It subscribes to the source universe and waits for all symbols
at each historical boundary before emitting one native equity mark and processing
symbol callbacks in stable sorted order. The explicit historical model requires
event==init; missing/duplicate boundaries reject, including incomplete terminal
input. Native engine processing remains upstream-owned; this is callback input
alignment, not a replacement scheduler. Existing single-exposure trial admission
still limits simultaneous experimental campaigns and app capture remains narrow.

Tests verify no decision/equity before complete input, one equity observation
per completed boundary, deterministic symbol order and missing-boundary failure.
Full suite: 392 passed; mypy clean. Native multi-source HistoricalTrial end-to-end
qualification and complete portfolio evaluation provenance remain required.

## Portfolio valuation input provenance

Historical equity rows now retain per-instrument valuation_inputs containing
price, event/init clocks and original candle source hash. For multiple instruments,
source_hash is the SHA-256 of the canonical sorted input map and close_price is
absent rather than pretending the last callback price values the portfolio.
Single-instrument source identity/close fields retain their meaning. This makes
existing family source-signature comparison distinguish different portfolio
input sets. Full suite: 392 passed; Ruff/mypy clean. Multi-source native end-to-end
qualification and corresponding artifact verification remain required.

## Native multi-source historical boundary qualification

Actual Nautilus bar tests now feed BTC and ETH at three identical hour boundaries
in both instrument insertion orders. Six callbacks produce six observation
decisions but exactly three portfolio equity marks and two evaluation intervals.
Each mark retains both instrument sources; cash remains the observed native
balance in this warmup/no-trade fixture. Both native cases pass, Ruff clean.
This qualifies callback alignment/provenance through the engine, not simultaneous
historical economic allocations or position-bearing multi-source performance.

## Position-bearing historical portfolio boundaries

Extended actual native multi-source bar tests with two explicitly seeded
execution-only test campaigns. Both BTC and ETH positions open, and the final
single boundary equity row observes both positions using complete marks. The
same assertions pass under reversed instrument insertion order and without
positions. Four focused cases pass; full suite passes 396 tests, Ruff clean.
Prices remain flat in this fixture, so it establishes multi-position coverage
and callback isolation, not nonzero portfolio-return accuracy or economic
admission. The seeded campaigns never enter production evidence.

## Nonzero native multi-position valuation

The aligned historical fixture now moves BTC from 100 to 110 and ETH from 100
to 95 after both 0.010 long entries. The final native unrealized portfolio PnL
is exactly +0.05 and equity 10000.05; the flat-account cases remain at 10000.
Both insertion orders pass with separate source/price inputs and one row per
boundary. Four focused native tests pass, Ruff clean. Values are test arithmetic,
not measured strategy returns or evidence of profitability.

## Evaluation verifies portfolio valuation inputs

Equity-loss construction now checks detailed valuation provenance when present:
complete stable instrument universe, positive finite prices, common boundary,
known receipt clocks and canonical source identity. Mixed detailed/legacy schemas
in one series reject; legacy single-source rows remain readable. Tests reject
changed prices, source membership and invalid clocks, while native multi-source
marks continue through evaluation. Full suite: 397 passed; Ruff/mypy clean.
Hashes bind the supplied records, not external venue authenticity; source replay
and remaining economic qualification still apply.

## Explicit ETH opportunity universe

Opportunity grammars now share an explicit BTC/ETH USD-M exposure mapping.
ETH setup identities bind ETH exposure and instrument rather than BTC constants;
unknown contracts remain outside the universe and native contract metadata
qualification still applies. Tests cover distinct identities under range,
volatility, trend and mean-reversion grammars. Grammar tests pass, Ruff/mypy
clean. Paper capture remains BTC-only and historical global exposure admission
is not widened by this change; portfolio acceptance remains separate work.

## Historical native portfolio admission

HistoricalTrial now rejects occupied exposure per instrument rather than globally,
and builds admission snapshots from complete native portfolio valuation and risk
projection. Other instruments' open/pending protected campaigns consume shared
notional and stop-risk budgets; same-instrument overlap remains prohibited.
Unknown universe mappings, incomplete marks, unprotected/unqualified native
reservations and in-flight orders fail closed. Equity uses current native cash
plus PnL under the explicitly historical accounting model; this does not relax
the separate paper funding reconciliation guard. Full suite: 401 passed;
mypy clean. Generated multi-instrument opportunity-to-fill qualification is still
required beyond the existing seeded multi-position tests.

## Generated multi-instrument campaign qualification and native API correction

A new native test now generates BTC and ETH opportunities from 28 bars through
trend-continuation grammar and Donchian observation/protection. Both campaigns
pass shared risk admission and fill after their decision clocks; no campaign is
seeded. The test exposed an actual pending-reservation API mismatch: pinned
Nautilus Cache has client_order_ids(), not order_ids(). Updated the risk reader
and its fixtures to the inspected native API. Both generated positions remain
open and each respects its protected notional bound. Full suite: 402 passed;
Ruff clean. Test data remains isolated; this establishes historical experimental
integration, not calibrated paper or live operation.

## Generated portfolio shared-capital exhaustion

The generated BTC/ETH native trial now also requests 6000 per opportunity against
10000 shared capital (90% individual exposure cap). The second admitted quantity
is smaller and combined protected-band notional stays within 10000; both campaigns
still fill under the native fixture. The ordinary 100-per-opportunity case also
passes. Two focused integration cases and Ruff pass. This tests budget sharing,
not risk-free loss bounds or real-world margin qualification.

## Real ETH native data qualification

Captured actual ETHUSDT public data, open interest and 5m account ratio at
/tmp/v8-next-eth-portfolio-2181277/manifest.json. Existing native_tape mapping
successfully replayed 499 closed bars and 62 funding events (623 iterations),
zero orders/positions. Log: /tmp/v8-eth-native.log. Explicit simulation assumptions
were maker 0.0002, taker 0.0005, initial cash 10000. The current metadata/generic
1x and modeled historical timing limitations remain in the output. This proves
real ETH instrument/data decoding, not combined BTC/ETH portfolio execution;
common capture-window engine composition is still required.
