//! Expert surface (COMPUTE_CORE_SPEC §6; EXPERT_PROTOCOL §2-3).
//!
//! The 28-register dispatch table lives here: one behaviour family per module
//! (D-033), each exporting `PORTED` (true once its evaluate() port passes
//! draft parity) and its evaluate() fn. Unported families return NO_HABITAT —
//! a missing port must never fabricate a candidate; the S4 gate fails loudly
//! until the registry is complete.
//!
//! The `registry` subcommand reads `registry_rows()` so the parity harness
//! derives its PORTED set from the binary instead of a hand-maintained list
//! (parallel-safe: ports only ever touch their own module file).

pub mod base;
pub mod predicate;
pub mod bollinger_breakout;
pub mod bollinger_reversion;
pub mod breakout_retest;
pub mod candlestick_reversal;
pub mod divergence_12_setups;
pub mod donchian_breakout;
pub mod failed_breakout;
pub mod failed_breakout_2b;
pub mod fib_projection_reversal;
pub mod fib_retracement_continuation;
pub mod fib_rsi_bb_confluence;
pub mod floor_trader_pivot;
pub mod funding_crowding_reversal;
pub mod gap_exhaustion;
pub mod ichimoku_cloud;
pub mod liquidity_sweep_reclaim;
pub mod macd_stoch_trend;
pub mod market_profile_value_area;
pub mod obv_adl_regime;
pub mod open_interest_divergence;
pub mod pandf_breakout;
pub mod pattern_measuring_objective;
pub mod range_breakout_1to1;
pub mod rsi_stoch_reversion;
pub mod trend_pullback;
pub mod trend_pullback_depth;
pub mod volume_climax_reversal;
pub mod volume_confirmed_breakout;

use base::{ExpertEval, FeatMap};

pub type PortFn = fn(&FeatMap, &str, &str) -> ExpertEval;

/// (expert_id, port fn, declared version, ported flag) — the dispatch table.
pub const TABLE: [(&str, PortFn, &str, bool); 28] = [
    ("bollinger_breakout", bollinger_breakout::bollinger_breakout, bollinger_breakout::VERSION, bollinger_breakout::PORTED),
    ("bollinger_reversion", bollinger_reversion::bollinger_reversion, bollinger_reversion::VERSION, bollinger_reversion::PORTED),
    ("breakout_retest", breakout_retest::breakout_retest, breakout_retest::VERSION, breakout_retest::PORTED),
    ("candlestick_reversal", candlestick_reversal::candlestick_reversal, candlestick_reversal::VERSION, candlestick_reversal::PORTED),
    ("divergence_12_setups", divergence_12_setups::divergence_12_setups, divergence_12_setups::VERSION, divergence_12_setups::PORTED),
    ("donchian_breakout", donchian_breakout::donchian_breakout, donchian_breakout::VERSION, donchian_breakout::PORTED),
    ("failed_breakout", failed_breakout::failed_breakout, failed_breakout::VERSION, failed_breakout::PORTED),
    ("failed_breakout_2b", failed_breakout_2b::failed_breakout_2b, failed_breakout_2b::VERSION, failed_breakout_2b::PORTED),
    ("fib_projection_reversal", fib_projection_reversal::fib_projection_reversal, fib_projection_reversal::VERSION, fib_projection_reversal::PORTED),
    ("fib_retracement_continuation", fib_retracement_continuation::fib_retracement_continuation, fib_retracement_continuation::VERSION, fib_retracement_continuation::PORTED),
    ("fib_rsi_bb_confluence", fib_rsi_bb_confluence::fib_rsi_bb_confluence, fib_rsi_bb_confluence::VERSION, fib_rsi_bb_confluence::PORTED),
    ("floor_trader_pivot", floor_trader_pivot::floor_trader_pivot, floor_trader_pivot::VERSION, floor_trader_pivot::PORTED),
    ("funding_crowding_reversal", funding_crowding_reversal::funding_crowding_reversal, funding_crowding_reversal::VERSION, funding_crowding_reversal::PORTED),
    ("gap_exhaustion", gap_exhaustion::gap_exhaustion, gap_exhaustion::VERSION, gap_exhaustion::PORTED),
    ("ichimoku_cloud", ichimoku_cloud::ichimoku_cloud, ichimoku_cloud::VERSION, ichimoku_cloud::PORTED),
    ("liquidity_sweep_reclaim", liquidity_sweep_reclaim::liquidity_sweep_reclaim, liquidity_sweep_reclaim::VERSION, liquidity_sweep_reclaim::PORTED),
    ("macd_stoch_trend", macd_stoch_trend::macd_stoch_trend, macd_stoch_trend::VERSION, macd_stoch_trend::PORTED),
    ("market_profile_value_area", market_profile_value_area::market_profile_value_area, market_profile_value_area::VERSION, market_profile_value_area::PORTED),
    ("obv_adl_regime", obv_adl_regime::obv_adl_regime, obv_adl_regime::VERSION, obv_adl_regime::PORTED),
    ("open_interest_divergence", open_interest_divergence::open_interest_divergence, open_interest_divergence::VERSION, open_interest_divergence::PORTED),
    ("pandf_breakout", pandf_breakout::pandf_breakout, pandf_breakout::VERSION, pandf_breakout::PORTED),
    ("pattern_measuring_objective", pattern_measuring_objective::pattern_measuring_objective, pattern_measuring_objective::VERSION, pattern_measuring_objective::PORTED),
    ("range_breakout_1to1", range_breakout_1to1::range_breakout_1to1, range_breakout_1to1::VERSION, range_breakout_1to1::PORTED),
    ("rsi_stoch_reversion", rsi_stoch_reversion::rsi_stoch_reversion, rsi_stoch_reversion::VERSION, rsi_stoch_reversion::PORTED),
    ("trend_pullback", trend_pullback::trend_pullback, trend_pullback::VERSION, trend_pullback::PORTED),
    ("trend_pullback_depth", trend_pullback_depth::trend_pullback_depth, trend_pullback_depth::VERSION, trend_pullback_depth::PORTED),
    ("volume_climax_reversal", volume_climax_reversal::volume_climax_reversal, volume_climax_reversal::VERSION, volume_climax_reversal::PORTED),
    ("volume_confirmed_breakout", volume_confirmed_breakout::volume_confirmed_breakout, volume_confirmed_breakout::VERSION, volume_confirmed_breakout::PORTED),
];

/// The registered evaluate() dispatch. Unported experts return NO_HABITAT
/// (never a wrong draft — a missing port must not fabricate a candidate).
pub fn evaluate(expert_id: &str, fm: &FeatMap) -> ExpertEval {
    for (id, f, ver, _) in TABLE {
        if *id == *expert_id {
            return f(fm, expert_id, ver);
        }
    }
    base::no_habitat(expert_id, "v1", fm.as_of)
}

pub fn ported(expert_id: &str) -> bool {
    TABLE.iter()
        .find(|(id, _, _, _)| **id == *expert_id)
        .map(|(_, _, _, p)| *p)
        .unwrap_or(false)
}

/// (expert_id, ported) rows for the `registry` subcommand / parity harness.
pub fn registry_rows() -> Vec<(&'static str, bool)> {
    TABLE.iter().map(|(id, _, _, p)| (*id, *p)).collect()
}

/// (expert_id, requires groups) — the D-053 projection declaration.
pub const REQUIRES_TABLE: [(&str, &[&str]); 28] = [
    ("bollinger_breakout", bollinger_breakout::REQUIRES),
    ("bollinger_reversion", bollinger_reversion::REQUIRES),
    ("breakout_retest", breakout_retest::REQUIRES),
    ("candlestick_reversal", candlestick_reversal::REQUIRES),
    ("divergence_12_setups", divergence_12_setups::REQUIRES),
    ("donchian_breakout", donchian_breakout::REQUIRES),
    ("failed_breakout", failed_breakout::REQUIRES),
    ("failed_breakout_2b", failed_breakout_2b::REQUIRES),
    ("fib_projection_reversal", fib_projection_reversal::REQUIRES),
    ("fib_retracement_continuation", fib_retracement_continuation::REQUIRES),
    ("fib_rsi_bb_confluence", fib_rsi_bb_confluence::REQUIRES),
    ("floor_trader_pivot", floor_trader_pivot::REQUIRES),
    ("funding_crowding_reversal", funding_crowding_reversal::REQUIRES),
    ("gap_exhaustion", gap_exhaustion::REQUIRES),
    ("ichimoku_cloud", ichimoku_cloud::REQUIRES),
    ("liquidity_sweep_reclaim", liquidity_sweep_reclaim::REQUIRES),
    ("macd_stoch_trend", macd_stoch_trend::REQUIRES),
    ("market_profile_value_area", market_profile_value_area::REQUIRES),
    ("obv_adl_regime", obv_adl_regime::REQUIRES),
    ("open_interest_divergence", open_interest_divergence::REQUIRES),
    ("pandf_breakout", pandf_breakout::REQUIRES),
    ("pattern_measuring_objective", pattern_measuring_objective::REQUIRES),
    ("range_breakout_1to1", range_breakout_1to1::REQUIRES),
    ("rsi_stoch_reversion", rsi_stoch_reversion::REQUIRES),
    ("trend_pullback", trend_pullback::REQUIRES),
    ("trend_pullback_depth", trend_pullback_depth::REQUIRES),
    ("volume_climax_reversal", volume_climax_reversal::REQUIRES),
    ("volume_confirmed_breakout", volume_confirmed_breakout::REQUIRES),
];

/// The D-053 requires closure for an expert (empty for unknown ids).
pub fn requires_for(expert_id: &str) -> &'static [&'static str] {
    for (id, reqs) in REQUIRES_TABLE {
        if *id == *expert_id {
            return reqs;
        }
    }
    &[]
}
