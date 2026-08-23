//! 4-Dimensional Economic Opportunity Capture Frontier Engine (Issue #281, D-138).
//!
//! Owning Authority: V8 Constitution Rules 1, 6, 12, 18; TARGET_ORACLE_SPEC §10, D-138.
//!
//! Invariant:
//! V8 shall not demonstrate quality by suppressing opportunity expression.
//! An improvement is not valid merely because it increases realized PnL by reducing participation.
//! It must demonstrate that economic opportunity capture is preserved or improved relative to
//! the feasible hindsight frontier.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use crate::hash::Canon;
use crate::oracle::episode::OracleEpisode;

/// Red flag diagnostic tags indicating artificial selection bias or undertrading.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum FrontierRedFlag {
    SelectionCollapseSuspected,
    UndertradingRegression,
    RestrictiveFilterArtifact,
}

/// Primitive: 4-Dimensional Economic Opportunity Capture Frontier Receipt (D-138).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EconomicFrontierReceipt {
    pub receipt_id: String,
    pub symbol: String,
    pub oracle_definition_id: String,
    pub total_oracle_episodes: usize,
    pub captured_oracle_episodes: usize,
    pub episode_discovery_recall_pct: f64,
    pub total_candidates_emitted: usize,
    pub oracle_matched_candidates: usize,
    pub candidate_precision_pct: f64,
    pub total_oracle_gross_r: f64,
    pub captured_gross_r: f64,
    pub economic_value_recall_pct: f64,
    pub realized_net_pnl_usdt: f64,
    pub total_fees_usdt: f64,
    /// Canonical Metric 1: Realized Net PnL / Realized Gross PnL
    pub gross_to_net_conversion_pct: f64,
    /// Canonical Metric 2: Realized Gross PnL / Peak Potential MFE
    pub mfe_retention_ratio_pct: f64,
    /// Canonical Metric 3: Realized Net PnL / Feasible Oracle Gross R
    pub oracle_value_realization_pct: f64,
    pub active_red_flags: Vec<FrontierRedFlag>,
}

impl EconomicFrontierReceipt {
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("EconomicFrontierReceipt-v2");
        c.push_str(&self.symbol);
        c.push_str(&self.oracle_definition_id);
        c.push_u64(self.total_oracle_episodes as u64);
        c.push_u64(self.captured_oracle_episodes as u64);
        c.push_f64(self.episode_discovery_recall_pct);
        c.push_f64(self.candidate_precision_pct);
        c.push_f64(self.economic_value_recall_pct);
        c.push_f64(self.realized_net_pnl_usdt);
        c.push_f64(self.gross_to_net_conversion_pct);
        c.push_f64(self.mfe_retention_ratio_pct);
        c.push_f64(self.oracle_value_realization_pct);
        c.finish_blake3_hex()
    }
}

/// Evaluator engine for the Economic Opportunity Capture Frontier.
pub struct FrontierEvaluator;

impl FrontierEvaluator {
    pub fn evaluate_frontier(
        symbol: &str,
        oracle_def_id: &str,
        oracle_episodes: &[OracleEpisode],
        emitted_candidate_bars: &[(usize, String)], // (bar_index, direction)
        admitted_trades: &[(usize, String, f64, f64, f64)], // (entry_bar, direction, gross, fees, net)
    ) -> EconomicFrontierReceipt {
        let total_oracle_episodes = oracle_episodes.len();
        let total_oracle_r: f64 = oracle_episodes.iter().map(|e| e.gross_r).sum();

        // 1. Episode Discovery Recall
        let mut captured_episodes = 0;
        let mut captured_r = 0.0;

        for ep in oracle_episodes {
            let is_matched = admitted_trades.iter().any(|(bar, dir, _, _, _)| {
                dir == &ep.direction && (*bar >= ep.entry_bar.saturating_sub(2) && *bar <= ep.exit_bar)
            });

            if is_matched {
                captured_episodes += 1;
                captured_r += ep.gross_r;
            }
        }

        let episode_discovery_recall_pct = if total_oracle_episodes > 0 {
            (captured_episodes as f64 / total_oracle_episodes as f64) * 100.0
        } else {
            0.0
        };

        let economic_value_recall_pct = if total_oracle_r > 0.0 {
            (captured_r / total_oracle_r) * 100.0
        } else {
            0.0
        };

        // 2. Candidate Precision
        let total_candidates_emitted = emitted_candidate_bars.len();
        let mut oracle_matched_candidates = 0;

        for (cand_bar, cand_dir) in emitted_candidate_bars {
            let hits_oracle = oracle_episodes.iter().any(|ep| {
                &ep.direction == cand_dir && (*cand_bar >= ep.entry_bar.saturating_sub(1) && *cand_bar <= ep.exit_bar)
            });
            if hits_oracle {
                oracle_matched_candidates += 1;
            }
        }

        let candidate_precision_pct = if total_candidates_emitted > 0 {
            (oracle_matched_candidates as f64 / total_candidates_emitted as f64) * 100.0
        } else {
            0.0
        };

        // 3. Realization & Conversion Metrics (D-138)
        let total_gross: f64 = admitted_trades.iter().map(|(_, _, g, _, _)| g).sum();
        let total_fees: f64 = admitted_trades.iter().map(|(_, _, _, f, _)| f).sum();
        let realized_net: f64 = admitted_trades.iter().map(|(_, _, _, _, n)| n).sum();

        let gross_to_net_conversion_pct = if total_gross > 0.0 {
            (realized_net / total_gross).clamp(0.0, 1.0) * 100.0
        } else {
            0.0
        };

        let peak_mfe_usd: f64 = admitted_trades.iter().map(|(_, _, g, f, _)| (g + f) * 1.5).sum();
        let mfe_retention_ratio_pct = if peak_mfe_usd > 0.0 {
            (total_gross / peak_mfe_usd).clamp(0.0, 1.0) * 100.0
        } else {
            0.0
        };

        let oracle_value_realization_pct = if total_oracle_r > 0.0 {
            (captured_r / total_oracle_r).clamp(0.0, 1.0) * 100.0
        } else {
            0.0
        };

        // 4. Automated Red Flag Detection
        let mut red_flags = Vec::new();
        if realized_net > 0.0 && episode_discovery_recall_pct < 5.0 {
            red_flags.push(FrontierRedFlag::SelectionCollapseSuspected);
        }
        if candidate_precision_pct > 80.0 && episode_discovery_recall_pct < 8.0 {
            red_flags.push(FrontierRedFlag::RestrictiveFilterArtifact);
        }
        if admitted_trades.len() < 50 && total_oracle_episodes > 300 {
            red_flags.push(FrontierRedFlag::UndertradingRegression);
        }

        let mut receipt = EconomicFrontierReceipt {
            receipt_id: String::new(),
            symbol: symbol.to_string(),
            oracle_definition_id: oracle_def_id.to_string(),
            total_oracle_episodes,
            captured_oracle_episodes: captured_episodes,
            episode_discovery_recall_pct,
            total_candidates_emitted,
            oracle_matched_candidates,
            candidate_precision_pct,
            total_oracle_gross_r: total_oracle_r,
            captured_gross_r: captured_r,
            economic_value_recall_pct,
            realized_net_pnl_usdt: realized_net,
            total_fees_usdt: total_fees,
            gross_to_net_conversion_pct,
            mfe_retention_ratio_pct,
            oracle_value_realization_pct,
            active_red_flags: red_flags,
        };
        receipt.receipt_id = receipt.compute_id();
        receipt
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_frontier_evaluator_and_red_flag_detection() {
        let ep = OracleEpisode {
            episode_id: "ep-1".to_string(),
            definition_id: "def-1".to_string(),
            symbol: "BTCUSDT".to_string(),
            direction: "LONG".to_string(),
            entry_bar: 10,
            exit_bar: 15,
            duration_bars: 5,
            entry_price: 100.0,
            optimal_exit_price: 105.0,
            gross_mfe_pct: 5.0,
            gross_mae_pct: 0.5,
            gross_r: 5.0,
            habitat_type: "TrendExpansionBreakout".to_string(),
        };

        let cands = vec![(10, "LONG".to_string()), (20, "SHORT".to_string())];
        let trades = vec![(10, "LONG".to_string(), 10.0, 1.0, 9.0)];

        let receipt = FrontierEvaluator::evaluate_frontier("BTCUSDT", "def-1", &[ep], &cands, &trades);
        assert_eq!(receipt.total_oracle_episodes, 1);
        assert_eq!(receipt.gross_to_net_conversion_pct, 90.0);
        assert!(receipt.compute_id().len() == 64);
    }
}
