//! Boyd Dynamic Liquidity Floor & Elastic Capital Router (Issue #217 / ALLOC-001).
//! Normative Traceability: D-110, D-123, CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md; arXiv:1603.06183, arXiv:1705.00109.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiquidityFloorBreakdown {
    pub venue_floor: f64,
    pub margin_stress: f64,
    pub next_trade_floor: f64,
    pub fee_funding_buffer: f64,
    pub effective_cash_floor: f64,
    pub wallet_equity: f64,
    pub deployable_equity: f64,
    pub utilization_ratio: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DynamicAllocationBudget {
    pub deployable_capital_usdt: f64,
    pub max_campaign_risk_usdt: f64,
    pub max_portfolio_heat_r: f64,
    pub is_frozen: bool,
    pub freeze_reason: Option<String>,
}

pub struct DynamicLiquidityFloorEngine;

impl DynamicLiquidityFloorEngine {
    /// Compute dynamic cash floor and deployable equity based on Point-in-Time portfolio state.
    /// Replaces static 80% cash lockup with emergent risk-constrained optimization.
    pub fn compute_liquidity_floor(
        wallet_equity: f64,
        maintenance_margin_required: f64,
        open_notional: f64,
        estimated_3sigma_adverse_move: f64, // e.g. 0.15 (15% adverse gap)
        expected_next_trade_margin: f64,
        accumulated_funding_risk_24h: f64,
    ) -> LiquidityFloorBreakdown {
        // 1. Venue physical floor (maintenance margin + 10% safety cushion)
        let venue_floor = maintenance_margin_required * 1.10;

        // 2. Margin stress cushion: capital required to survive a 3-sigma gap move on all open positions
        let margin_stress = open_notional * estimated_3sigma_adverse_move;

        // 3. Next trade floor: minimum margin needed to execute next high-conviction campaign
        let next_trade_floor = expected_next_trade_margin;

        // 4. Funding & fee reserve buffer for next 24h
        let fee_funding_buffer = accumulated_funding_risk_24h.max(wallet_equity * 0.01);

        // Effective Cash Floor: max of all competing structural requirements
        let effective_cash_floor = venue_floor
            .max(margin_stress)
            .max(next_trade_floor)
            .max(fee_funding_buffer)
            .min(wallet_equity);

        let deployable_equity = (wallet_equity - effective_cash_floor).max(0.0);
        let utilization_ratio = if wallet_equity > 0.0 {
            effective_cash_floor / wallet_equity
        } else {
            1.0
        };

        LiquidityFloorBreakdown {
            venue_floor,
            margin_stress,
            next_trade_floor,
            fee_funding_buffer,
            effective_cash_floor,
            wallet_equity,
            deployable_equity,
            utilization_ratio,
        }
    }

    /// Allocate risk budget for a new candidate campaign from deployable equity.
    pub fn allocate_campaign_budget(
        breakdown: &LiquidityFloorBreakdown,
        evidence_strength: f64, // S_camp >= 1.0
        current_portfolio_heat_r: f64,
        max_portfolio_heat_r: f64, // D-023: 3.0R
        base_risk_fraction: f64,   // e.g. 0.015 (1.5%)
    ) -> DynamicAllocationBudget {
        // Freeze if wallet equity below maintenance margin
        if breakdown.wallet_equity <= breakdown.venue_floor {
            return DynamicAllocationBudget {
                deployable_capital_usdt: 0.0,
                max_campaign_risk_usdt: 0.0,
                max_portfolio_heat_r,
                is_frozen: true,
                freeze_reason: Some("EQUITY_BELOW_MAINTENANCE_MARGIN".to_string()),
            };
        }

        // Freeze if portfolio heat limit reached
        if current_portfolio_heat_r >= max_portfolio_heat_r {
            return DynamicAllocationBudget {
                deployable_capital_usdt: breakdown.deployable_equity,
                max_campaign_risk_usdt: 0.0,
                max_portfolio_heat_r,
                is_frozen: true,
                freeze_reason: Some("MAX_PORTFOLIO_HEAT_REACHED".to_string()),
            };
        }

        // Modulate risk fraction by evidence strength: S_camp in [1.0, 2.0]
        let modulated_risk_fraction = (base_risk_fraction * evidence_strength.clamp(1.0, 2.0)).min(0.03);
        let campaign_risk_usdt = breakdown.deployable_equity * modulated_risk_fraction;

        DynamicAllocationBudget {
            deployable_capital_usdt: breakdown.deployable_equity,
            max_campaign_risk_usdt: campaign_risk_usdt,
            max_portfolio_heat_r,
            is_frozen: false,
            freeze_reason: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dynamic_liquidity_unlocks_deployable_capital_on_clean_account() {
        // $10,000 equity, no open positions
        let floor = DynamicLiquidityFloorEngine::compute_liquidity_floor(
            10_000.0,
            0.0,
            0.0,
            0.15,
            100.0,
            50.0,
        );

        // Floor should only be $100 (next trade + buffer), NOT $8,000 static lockup!
        assert!(floor.effective_cash_floor <= 200.0);
        assert!(floor.deployable_equity >= 9800.0);

        let budget = DynamicLiquidityFloorEngine::allocate_campaign_budget(&floor, 1.25, 0.0, 3.0, 0.015);
        assert!(!budget.is_frozen);
        assert!(budget.max_campaign_risk_usdt >= 140.0);
    }

    #[test]
    fn test_dynamic_liquidity_protects_against_margin_stress_when_positions_open() {
        // $10,000 equity, $30,000 open notional exposure
        let floor = DynamicLiquidityFloorEngine::compute_liquidity_floor(
            10_000.0,
            1_500.0,
            30_000.0,
            0.15, // 15% stress = $4,500
            100.0,
            50.0,
        );

        assert_eq!(floor.margin_stress, 4500.0);
        assert_eq!(floor.effective_cash_floor, 4500.0);
        assert_eq!(floor.deployable_equity, 5500.0);
    }
}
