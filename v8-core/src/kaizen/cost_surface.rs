//! Authoritative Venue Cost, Slippage & Excess Cost Feasibility (Issue #219 / COST-001).
//! Normative Traceability: D-109, D-110, D-123, VENUE_AND_CAPITAL_SIMULATION_SPEC §3,4,8.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum VipTier {
    Regular,
    VIP1,
    VIP2,
    VIP3,
    VIP9,
    UncertifiedFallback,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VenueCostProfile {
    pub tier: VipTier,
    pub maker_fee_bps: f64,
    pub taker_fee_bps: f64,
    pub base_slippage_bps: f64,
    pub adverse_markout_bps: f64,
}

impl Default for VenueCostProfile {
    fn default() -> Self {
        VenueCostProfile {
            tier: VipTier::Regular,
            maker_fee_bps: 2.0, // 0.02%
            taker_fee_bps: 5.0, // 0.05%
            base_slippage_bps: 1.5,
            adverse_markout_bps: 1.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostFeasibilityCheck {
    pub is_feasible: bool,
    pub expected_gross_r: f64,
    pub total_round_trip_cost_r: f64,
    pub net_expected_r: f64,
    pub cost_to_target_ratio: f64,
    pub rejection_reason: Option<String>,
}

pub struct VenueCostEngine;

impl VenueCostEngine {
    pub fn get_profile(tier: VipTier) -> VenueCostProfile {
        match tier {
            VipTier::Regular => VenueCostProfile {
                tier,
                maker_fee_bps: 2.0,
                taker_fee_bps: 5.0,
                base_slippage_bps: 1.5,
                adverse_markout_bps: 1.0,
            },
            VipTier::VIP1 => VenueCostProfile {
                tier,
                maker_fee_bps: 1.6,
                taker_fee_bps: 4.0,
                base_slippage_bps: 1.2,
                adverse_markout_bps: 0.8,
            },
            VipTier::VIP9 => VenueCostProfile {
                tier,
                maker_fee_bps: 0.0,
                taker_fee_bps: 1.5,
                base_slippage_bps: 0.5,
                adverse_markout_bps: 0.3,
            },
            _ => VenueCostProfile {
                tier: VipTier::UncertifiedFallback,
                maker_fee_bps: 10.0,
                taker_fee_bps: 15.0,
                base_slippage_bps: 5.0,
                adverse_markout_bps: 3.0,
            },
        }
    }

    /// Check if trade setup has positive net expectancy after all venue frictions.
    pub fn evaluate_feasibility(
        profile: &VenueCostProfile,
        entry_price: f64,
        stop_price: f64,
        target_r: f64,
        is_maker_entry: bool,
    ) -> CostFeasibilityCheck {
        let stop_dist = (entry_price - stop_price).abs();
        if stop_dist <= 0.0 || entry_price <= 0.0 {
            return CostFeasibilityCheck {
                is_feasible: false,
                expected_gross_r: 0.0,
                total_round_trip_cost_r: f64::INFINITY,
                net_expected_r: f64::NEG_INFINITY,
                cost_to_target_ratio: f64::INFINITY,
                rejection_reason: Some("ZERO_RISK_DISTANCE".to_string()),
            };
        }

        let entry_fee_bps = if is_maker_entry { profile.maker_fee_bps } else { profile.taker_fee_bps };
        let exit_fee_bps = profile.taker_fee_bps;
        let total_bps = entry_fee_bps + exit_fee_bps + profile.base_slippage_bps + profile.adverse_markout_bps;

        let total_cost_usd_per_unit = entry_price * (total_bps / 10_000.0);
        let total_cost_r = total_cost_usd_per_unit / stop_dist;

        let net_expected_r = target_r - total_cost_r;
        let cost_ratio = total_cost_r / target_r.max(1e-6);

        if cost_ratio > 0.35 || net_expected_r <= 0.20 {
            return CostFeasibilityCheck {
                is_feasible: false,
                expected_gross_r: target_r,
                total_round_trip_cost_r: total_cost_r,
                net_expected_r,
                cost_to_target_ratio: cost_ratio,
                rejection_reason: Some("EXCESS_COST_DOMINATED".to_string()),
            };
        }

        CostFeasibilityCheck {
            is_feasible: true,
            expected_gross_r: target_r,
            total_round_trip_cost_r: total_cost_r,
            net_expected_r,
            cost_to_target_ratio: cost_ratio,
            rejection_reason: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wide_stop_trade_is_cost_feasible() {
        let profile = VenueCostEngine::get_profile(VipTier::Regular);
        let check = VenueCostEngine::evaluate_feasibility(&profile, 65000.0, 64000.0, 2.0, false);
        assert!(check.is_feasible);
        assert!(check.total_round_trip_cost_r < 0.15);
    }

    #[test]
    fn test_micro_scalp_rejected_as_cost_dominated() {
        let profile = VenueCostEngine::get_profile(VipTier::Regular);
        let check = VenueCostEngine::evaluate_feasibility(&profile, 65000.0, 64980.0, 1.0, false);
        assert!(!check.is_feasible);
        assert_eq!(check.rejection_reason.unwrap(), "EXCESS_COST_DOMINATED");
    }
}
