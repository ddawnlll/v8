//! Quantization-Aware Risk Budgeting & Micro-Lot Feasibility (Issue #216 / CAP-001).
//! Normative Traceability: D-109, D-110, D-123, VENUE_AND_CAPITAL_SIMULATION_SPEC §3, CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum QuantizationFeasibilityStatus {
    AdmissibleExact,
    AdmissibleMicroLot,
    ExceedsCapitalRiskBudget,
    BelowMinimumNotional,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuantizationBudgetResult {
    pub symbol: String,
    pub status: QuantizationFeasibilityStatus,
    pub allowed_risk_usdt: f64,
    pub minimum_executable_risk_usdt: f64,
    pub step_size: f64,
    pub min_qty: f64,
    pub min_notional: f64,
    pub computed_raw_qty: f64,
    pub allocated_executable_qty: f64,
    pub final_dollar_risk: f64,
    pub avoidable_opportunity_loss: bool,
}

pub struct QuantizationRiskEngine;

impl QuantizationRiskEngine {
    /// Calculate exact executable lot size with quantization awareness.
    /// Eliminates false `QUANTITY_ROUNDS_TO_ZERO` dropouts while preserving maximum risk bounds.
    pub fn compute_executable_lot(
        symbol: &str,
        entry_price: f64,
        stop_price: f64,
        allowed_risk_budget_usdt: f64,
        step_size: f64,
        min_qty: f64,
        min_notional: f64,
        estimated_round_trip_fee_bps: f64, // e.g. 8 bps = 0.0008
    ) -> QuantizationBudgetResult {
        let stop_distance = (entry_price - stop_price).abs();

        if stop_distance <= 0.0 || entry_price <= 0.0 || allowed_risk_budget_usdt <= 0.0 {
            return QuantizationBudgetResult {
                symbol: symbol.to_string(),
                status: QuantizationFeasibilityStatus::ExceedsCapitalRiskBudget,
                allowed_risk_usdt: allowed_risk_budget_usdt,
                minimum_executable_risk_usdt: 0.0,
                step_size,
                min_qty,
                min_notional,
                computed_raw_qty: 0.0,
                allocated_executable_qty: 0.0,
                final_dollar_risk: 0.0,
                avoidable_opportunity_loss: false,
            };
        }

        // Minimum physical legal lot
        let min_executable_lot = min_qty.min(step_size).max(1e-8);
        let min_lot_loss = min_executable_lot * stop_distance;
        let min_lot_friction = min_executable_lot * entry_price * (estimated_round_trip_fee_bps / 10_000.0);
        let minimum_executable_risk = min_lot_loss + min_lot_friction;

        // Raw continuous theoretical qty
        let raw_qty = allowed_risk_budget_usdt / (stop_distance + (entry_price * estimated_round_trip_fee_bps / 10_000.0));

        // Quantize down to nearest step_size
        let steps = (raw_qty / step_size).floor();
        let mut quantized_qty = steps * step_size;

        // Quantization-Aware Micro-Lot Resolution:
        // When raw_qty fits within budget but step_size quantization drops it to 0, admit minimum lot
        let mut avoidable_loss = false;
        if quantized_qty < min_qty {
            if minimum_executable_risk <= allowed_risk_budget_usdt {
                quantized_qty = min_qty;
                avoidable_loss = true;
            } else {
                return QuantizationBudgetResult {
                    symbol: symbol.to_string(),
                    status: QuantizationFeasibilityStatus::ExceedsCapitalRiskBudget,
                    allowed_risk_usdt: allowed_risk_budget_usdt,
                    minimum_executable_risk_usdt: minimum_executable_risk,
                    step_size,
                    min_qty,
                    min_notional,
                    computed_raw_qty: raw_qty,
                    allocated_executable_qty: 0.0,
                    final_dollar_risk: 0.0,
                    avoidable_opportunity_loss: false,
                };
            }
        }

        // Min notional check
        let notional = quantized_qty * entry_price;
        if notional < min_notional {
            return QuantizationBudgetResult {
                symbol: symbol.to_string(),
                status: QuantizationFeasibilityStatus::BelowMinimumNotional,
                allowed_risk_usdt: allowed_risk_budget_usdt,
                minimum_executable_risk_usdt: minimum_executable_risk,
                step_size,
                min_qty,
                min_notional,
                computed_raw_qty: raw_qty,
                allocated_executable_qty: 0.0,
                final_dollar_risk: 0.0,
                avoidable_opportunity_loss: false,
            };
        }

        let final_risk = (quantized_qty * stop_distance) + (notional * estimated_round_trip_fee_bps / 10_000.0);
        let status = if avoidable_loss {
            QuantizationFeasibilityStatus::AdmissibleMicroLot
        } else {
            QuantizationFeasibilityStatus::AdmissibleExact
        };

        QuantizationBudgetResult {
            symbol: symbol.to_string(),
            status,
            allowed_risk_usdt: allowed_risk_budget_usdt,
            minimum_executable_risk_usdt: minimum_executable_risk,
            step_size,
            min_qty,
            min_notional,
            computed_raw_qty: raw_qty,
            allocated_executable_qty: quantized_qty,
            final_dollar_risk: final_risk,
            avoidable_opportunity_loss: avoidable_loss,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_micro_lot_admission_prevents_zero_rounding_dropout() {
        let res = QuantizationRiskEngine::compute_executable_lot(
            "BTCUSDT",
            65000.0,
            64000.0,
            15.0,
            0.001,
            0.001,
            5.0,
            8.0,
        );

        assert_eq!(res.status, QuantizationFeasibilityStatus::AdmissibleExact);
        assert_eq!(res.allocated_executable_qty, 0.014);
        assert!(res.final_dollar_risk <= 15.0);
    }

    #[test]
    fn test_micro_lot_admitted_when_raw_rounds_to_zero_but_one_lot_fits() {
        // Step size = 0.01 BTC, min_qty = 0.001 BTC. Allowed risk = $5.00. (Stop dist = 1000)
        // Raw qty = 5 / 1000 = 0.005 BTC -> steps = floor(0.005 / 0.01) = 0.
        // Quantized would be 0, but min_qty 0.001 costs $1.00 risk <= $5.00 -> admitted as MicroLot!
        let res = QuantizationRiskEngine::compute_executable_lot(
            "BTCUSDT",
            65000.0,
            64000.0,
            5.00,
            0.01,
            0.001,
            5.0,
            0.0,
        );

        assert_eq!(res.status, QuantizationFeasibilityStatus::AdmissibleMicroLot);
        assert_eq!(res.allocated_executable_qty, 0.001);
        assert!(res.avoidable_opportunity_loss);
    }

    #[test]
    fn test_exceeds_budget_fails_closed() {
        let res = QuantizationRiskEngine::compute_executable_lot(
            "BTCUSDT",
            65000.0,
            64000.0,
            0.50,
            0.001,
            0.001,
            5.0,
            0.0,
        );

        assert_eq!(res.status, QuantizationFeasibilityStatus::ExceedsCapitalRiskBudget);
        assert_eq!(res.allocated_executable_qty, 0.0);
    }
}
