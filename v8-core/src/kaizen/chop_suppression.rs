//! Cost-Aware No-Trade Region & Churn Suppression (Issue #KZ-018 / CHOP-001 / D-126).
//!
//! Production Invariant:
//! A trade/campaign is admitted IFF:
//! ExpectedMarginalUtility_after_cost > MinimumOpportunityThreshold
//! AND campaign is materially different from recent failed campaigns (cooldown)
//! AND expected incremental edge justifies turnover friction.
//!
//! Deterministic Baseline Arms (No fitted opaque router):
//! - A0: Current unsuppressed baseline behavior.
//! - A1: Cost-only feasibility gate (expected excursion > cost multiple).
//! - A2: Episode re-entry cooldown suppression after recent failure.
//! - A3: Expansion-quality gate (sufficient volatility/entropy compression release).
//! - A4: A1 + A2.
//! - A5: A1 + A2 + A3 (Full Composite No-Trade Region).
//!
//! Academic references:
//! - arXiv:2606.00060 (Cost-aware execution thresholds in BTC hourly trading)
//! - arXiv:2407.13547 (Optimal No-Trade Regions under Transaction Costs)
//! - arXiv:1308.5658 (Optimal Turnover-Friction Trade-off in Trend-Following)
//! - arXiv:1705.00109 (Boyd Multi-Period Portfolio Optimization with Transaction Costs)

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChopSuppressionArm {
    A0Baseline,
    A1CostFeasibility,
    A2EpisodeCooldown,
    A3ExpansionQuality,
    A4CostAndCooldown,
    A5CompositeNoTradeRegion,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChopGateContext {
    pub symbol: String,
    pub bar_index: usize,
    pub timestamp_ns: i64,
    pub direction: String, // "LONG" or "SHORT"
    pub entry_price: f64,
    pub structural_stop: f64,
    pub expected_gross_excursion_r: f64,
    pub venue_roundtrip_friction_bps: f64,
    pub bars_since_last_failed_campaign: usize,
    pub last_failed_campaign_same_direction: bool,
    pub rolling_volatility_compression_ratio: f64, // e.g. ATR_short / ATR_long
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChopVerdict {
    pub is_admitted: bool,
    pub reason_code: String,
    pub arm: ChopSuppressionArm,
    pub expected_friction_r: f64,
    pub net_edge_r: f64,
}

pub struct CostAwareNoTradeGate;

impl CostAwareNoTradeGate {
    /// Evaluates candidate admission against the selected No-Trade Arm.
    pub fn evaluate(ctx: &ChopGateContext, arm: ChopSuppressionArm) -> ChopVerdict {
        let stop_distance = (ctx.entry_price - ctx.structural_stop).abs();
        let stop_distance_pct = if ctx.entry_price > 1e-6 {
            stop_distance / ctx.entry_price
        } else {
            0.01
        };

        // Convert roundtrip friction (bps) to R units: (friction_bps / 10,000) / stop_distance_pct
        let friction_r = if stop_distance_pct > 1e-5 {
            (ctx.venue_roundtrip_friction_bps / 10_000.0) / stop_distance_pct
        } else {
            0.15
        };

        let net_edge_r = ctx.expected_gross_excursion_r - friction_r;

        match arm {
            ChopSuppressionArm::A0Baseline => ChopVerdict {
                is_admitted: true,
                reason_code: "A0_UNCONSTRAINED_ADMITTED".to_string(),
                arm,
                expected_friction_r: friction_r,
                net_edge_r,
            },

            ChopSuppressionArm::A1CostFeasibility => {
                // Gate 1: Gross excursion must exceed authoritative cost threshold (at least 2.5x friction)
                if ctx.expected_gross_excursion_r <= 2.5 * friction_r {
                    ChopVerdict {
                        is_admitted: false,
                        reason_code: "VETO_EXPECTED_EDGE_BELOW_COST_FLOOR".to_string(),
                        arm,
                        expected_friction_r: friction_r,
                        net_edge_r,
                    }
                } else {
                    ChopVerdict {
                        is_admitted: true,
                        reason_code: "PASS_COST_FEASIBLE".to_string(),
                        arm,
                        expected_friction_r: friction_r,
                        net_edge_r,
                    }
                }
            }

            ChopSuppressionArm::A2EpisodeCooldown => {
                // Gate 2: Cooldown period of 8 bars after a failed campaign in the same direction
                if ctx.last_failed_campaign_same_direction && ctx.bars_since_last_failed_campaign < 8 {
                    ChopVerdict {
                        is_admitted: false,
                        reason_code: "VETO_FAILED_CAMPAIGN_COOLDOWN_ACTIVE".to_string(),
                        arm,
                        expected_friction_r: friction_r,
                        net_edge_r,
                    }
                } else {
                    ChopVerdict {
                        is_admitted: true,
                        reason_code: "PASS_COOLDOWN_SATISFIED".to_string(),
                        arm,
                        expected_friction_r: friction_r,
                        net_edge_r,
                    }
                }
            }

            ChopSuppressionArm::A3ExpansionQuality => {
                // Gate 3: Volatility compression release check (avoid entering dead choppy ranges)
                if ctx.rolling_volatility_compression_ratio < 0.65 {
                    ChopVerdict {
                        is_admitted: false,
                        reason_code: "VETO_INSUFFICIENT_EXPANSION_QUALITY".to_string(),
                        arm,
                        expected_friction_r: friction_r,
                        net_edge_r,
                    }
                } else {
                    ChopVerdict {
                        is_admitted: true,
                        reason_code: "PASS_EXPANSION_QUALITY_CONFIRMED".to_string(),
                        arm,
                        expected_friction_r: friction_r,
                        net_edge_r,
                    }
                }
            }

            ChopSuppressionArm::A4CostAndCooldown => {
                let v1 = Self::evaluate(ctx, ChopSuppressionArm::A1CostFeasibility);
                if !v1.is_admitted {
                    return v1;
                }
                let v2 = Self::evaluate(ctx, ChopSuppressionArm::A2EpisodeCooldown);
                if !v2.is_admitted {
                    return v2;
                }
                ChopVerdict {
                    is_admitted: true,
                    reason_code: "PASS_A4_COST_AND_COOLDOWN".to_string(),
                    arm,
                    expected_friction_r: friction_r,
                    net_edge_r,
                }
            }

            ChopSuppressionArm::A5CompositeNoTradeRegion => {
                let v4 = Self::evaluate(ctx, ChopSuppressionArm::A4CostAndCooldown);
                if !v4.is_admitted {
                    return v4;
                }
                let v3 = Self::evaluate(ctx, ChopSuppressionArm::A3ExpansionQuality);
                if !v3.is_admitted {
                    return v3;
                }
                ChopVerdict {
                    is_admitted: true,
                    reason_code: "PASS_A5_COMPOSITE_NO_TRADE_REGION".to_string(),
                    arm,
                    expected_friction_r: friction_r,
                    net_edge_r,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chop_gate_cost_feasibility() {
        let ctx = ChopGateContext {
            symbol: "BTCUSDT".to_string(),
            bar_index: 100,
            timestamp_ns: 1751400000000,
            direction: "LONG".to_string(),
            entry_price: 65000.0,
            structural_stop: 64500.0, // 500 stop = 0.769%
            expected_gross_excursion_r: 0.10, // low excursion below 2.5 * friction
            venue_roundtrip_friction_bps: 9.0, // 0.09% friction -> ~0.117R
            bars_since_last_failed_campaign: 20,
            last_failed_campaign_same_direction: false,
            rolling_volatility_compression_ratio: 1.0,
        };

        let verdict = CostAwareNoTradeGate::evaluate(&ctx, ChopSuppressionArm::A1CostFeasibility);
        assert!(!verdict.is_admitted);
        assert_eq!(verdict.reason_code, "VETO_EXPECTED_EDGE_BELOW_COST_FLOOR");
    }

    #[test]
    fn test_chop_gate_cooldown_veto() {
        let ctx = ChopGateContext {
            symbol: "BTCUSDT".to_string(),
            bar_index: 100,
            timestamp_ns: 1751400000000,
            direction: "LONG".to_string(),
            entry_price: 65000.0,
            structural_stop: 64000.0,
            expected_gross_excursion_r: 2.0,
            venue_roundtrip_friction_bps: 9.0,
            bars_since_last_failed_campaign: 3, // < 8 bars
            last_failed_campaign_same_direction: true,
            rolling_volatility_compression_ratio: 1.0,
        };

        let verdict = CostAwareNoTradeGate::evaluate(&ctx, ChopSuppressionArm::A2EpisodeCooldown);
        assert!(!verdict.is_admitted);
        assert_eq!(verdict.reason_code, "VETO_FAILED_CAMPAIGN_COOLDOWN_ACTIVE");
    }
}
