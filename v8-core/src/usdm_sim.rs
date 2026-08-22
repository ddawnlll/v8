//! Finite-Capital Binance USDⓈ-M Discrete-Event Portfolio Simulator.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §§1–11, Decisions D-109..D-116, D-126.
//!
//! Integrates:
//! - KZ-018: Cost-Aware No-Trade Region & Churn Suppression.
//! - KZ-008: Persistent Multi-Bar Campaign Clustering across 7 Mechanism Families.
//! - KZ-009: Quantization-Aware Micro-Lot Safety.
//! - KZ-007: Tail-Preserving Chandelier Trailing Exits (replacing fixed TP).

pub mod capital_viability;
pub mod differential;
pub mod maker_model;
pub mod scenario_ruin;

use crate::account::{AccountState, MarginMode};
use crate::cashflow::{CashflowLedger, EconomicCashflow};
use crate::data::Dataset;
use crate::features;
use crate::kaizen::campaign::{CampaignDirection, PersistentCampaignRegistry, SensorVote};
use crate::kaizen::chop_suppression::{ChopGateContext, ChopSuppressionArm, CostAwareNoTradeGate};
use crate::kaizen::quantization::QuantizationRiskEngine;
use crate::kaizen::exit_trailing::{DynamicTrailingEngine, ExitArm, TrailingState};
use crate::portfolio::{OpenPosition, PortfolioState};
use crate::state;
use crate::venue::{LiquidationModel, VenueContract};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::path::PathBuf;

/// Request parameters for USD-M Capital Simulation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsdmSimParams {
    pub tape_path: PathBuf,
    pub out_dir: PathBuf,
    #[serde(default = "default_initial_balance")]
    pub initial_balance: f64,
    #[serde(default = "default_risk_fraction")]
    pub risk_fraction: f64,
    #[serde(default = "default_leverage")]
    pub leverage: u32,
    #[serde(default = "default_max_concurrency")]
    pub max_concurrency: usize,
    #[serde(default = "default_max_heat")]
    pub max_heat: f64,
    #[serde(default)]
    pub enabled_experts: Option<Vec<String>>,
    #[serde(default)]
    pub engine_mode: Option<String>,
}

fn default_initial_balance() -> f64 {
    1000.0
}
fn default_risk_fraction() -> f64 {
    0.005
} // 0.5% risk
fn default_leverage() -> u32 {
    10
}
fn default_max_concurrency() -> usize {
    3
}
fn default_max_heat() -> f64 {
    0.05
}

/// Structured execution receipt emitted to `.audit/rust_audit_current/portfolio_receipt.json`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioReceipt {
    pub receipt_id: String,
    pub initial_balance_usdt: f64,
    pub terminal_equity_usdt: f64,
    pub net_profit_usdt: f64,
    pub total_return_pct: f64,
    pub max_drawdown_pct: f64,
    pub max_margin_utilization_pct: f64,
    pub total_fee_drag_usdt: f64,
    pub total_funding_usdt: f64,
    pub n_trades_admitted: usize,
    pub win_rate_pct: f64,
    pub profit_factor: f64,
    pub rejections_by_reason: BTreeMap<String, usize>,
    pub cashflow_ledger_path: String,
    pub venue_contract_hash: String,
}

/// Runs the USD-M finite-capital simulation engine with Kaizen architecture.
pub fn run_simulation(params: &UsdmSimParams) -> Result<PortfolioReceipt, String> {
    let _ = std::fs::create_dir_all(&params.out_dir);
    let rows = crate::read_tape(&params.tape_path)?;
    let ds = Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = crate::state::build_stores(&ds);

    let store = stores
        .iter()
        .find(|s| s.symbol == "BTCUSDT")
        .or_else(|| stores.first())
        .ok_or_else(|| "No symbol series found in tape".to_string())?;

    let n_bars = store.closes.len();
    if n_bars == 0 {
        return Err("Tape is empty".to_string());
    }

    let contract = VenueContract::binance_btcusdt_perpetual();
    let mut account = AccountState::new(params.initial_balance);
    account.margin_mode = MarginMode::Isolated;

    let mut portfolio = PortfolioState::new(params.max_concurrency, params.max_heat);
    let mut ledger = CashflowLedger::new();
    let mut rejections: BTreeMap<String, usize> = BTreeMap::new();
    let mut peak_equity = account.equity_usdt();
    let mut max_drawdown_pct = 0.0;
    let mut max_margin_utilization = 0.0;

    let mut campaign_reg = PersistentCampaignRegistry::new();
    let mut trailing_states: HashMap<String, TrailingState> = HashMap::new();
    let mut last_failed_bar: Option<usize> = None;
    let mut last_failed_dir: Option<String> = None;

    let is_v83_engine = params.engine_mode.as_deref() == Some("v8.3") || params.engine_mode.as_deref() == Some("opportunity");
    let v83_engine = crate::opportunity::runloop::V83Runloop::default();
    let mut v83_book = crate::opportunity::book::OpportunityBook::new();

    let empty_variants = HashMap::new();
    let registry_rows = crate::experts::registry_rows();
    let projections: Vec<(&str, std::collections::HashSet<String>, bool)> = registry_rows
        .iter()
        .filter(|(eid, ported)| {
            if !*ported {
                return false;
            }
            if let Some(enabled) = &params.enabled_experts {
                enabled.contains(&eid.to_string())
            } else {
                true
            }
        })
        .map(|(eid, _)| {
            let closure = features::group_closure(crate::experts::requires_for(eid));
            let allows_hist = features::history_allowed(&closure);
            (*eid, closure, allows_hist)
        })
        .collect();

    let mut bar_votes: Vec<SensorVote> = Vec::with_capacity(32);

    for i in 0..n_bars {
        let current_close = store.closes[i];
        let current_open = store.opens[i];
        let current_high = store.highs[i];
        let current_low = store.lows[i];
        let current_atr = store.atr.get(i).copied().unwrap_or(current_close * 0.01);
        let as_of = store.avail[i];
        let current_funding_rate = if i < store.funding_rate.len() {
            store.funding_rate[i]
        } else {
            0.0
        };

        // 1. Settle 8-hour funding cashflows if applicable
        if (as_of % (8 * 3600 * 1_000_000_000)) == 0 && !portfolio.positions.is_empty() {
            for pos in &mut portfolio.positions {
                let notional = pos.quantity * current_open;
                let funding_cf = if pos.direction == "LONG" {
                    -notional * current_funding_rate
                } else {
                    notional * current_funding_rate
                };
                account.apply_funding(funding_cf);
                pos.cum_funding_usdt += funding_cf;
            }
        }

        // 2. Evaluate active open positions against bar price action (Dynamic Chandelier Trailing)
        let mut surviving_positions = Vec::new();
        for pos in portfolio.positions.drain(..) {
            let bracket = contract.bracket_for_notional(pos.quantity * pos.entry_price);
            let liq_price = LiquidationModel::calculate_isolated_liquidation_price(
                &pos.direction,
                pos.entry_price,
                pos.quantity,
                pos.isolated_margin_usdt,
                bracket,
            );

            // A. Check Liquidation
            if LiquidationModel::is_liquidated(&pos.direction, liq_price, current_high, current_low) {
                let exit_price = liq_price;
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let taker_fee = exit_price * pos.quantity * account.effective_fee_rate(false);

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(taker_fee);

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    gross_pnl,
                    taker_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    account.wallet_balance_usdt - (gross_pnl - taker_fee),
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                trailing_states.remove(&pos.position_id);
                last_failed_bar = Some(i);
                last_failed_dir = Some(pos.direction);
                continue;
            }

            // B. Check Dynamic Trailing Stop (KZ-007)
            let mut stop_exit = false;
            let mut exit_price = pos.stop_loss_price;

            if let Some(tstate) = trailing_states.get_mut(&pos.position_id) {
                if let Some(res) = DynamicTrailingEngine::step_bar(tstate, i, current_high, current_low, current_close, current_atr, None) {
                    stop_exit = true;
                    exit_price = res.exit_price;
                }
            } else {
                let stop_hit = if pos.direction == "LONG" {
                    current_low <= pos.stop_loss_price
                } else {
                    current_high >= pos.stop_loss_price
                };
                if stop_hit {
                    stop_exit = true;
                    exit_price = pos.stop_loss_price;
                }
            }

            if stop_exit {
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let taker_fee = exit_price * pos.quantity * account.effective_fee_rate(false);

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(taker_fee);

                if gross_pnl < 0.0 {
                    last_failed_bar = Some(i);
                    last_failed_dir = Some(pos.direction.clone());
                }

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    gross_pnl,
                    taker_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    account.wallet_balance_usdt - (gross_pnl - taker_fee),
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                trailing_states.remove(&pos.position_id);
                continue;
            }

            // C. Check Maximum Expiry (72 hours = 72 bars for campaigns)
            if (i + 1) >= (pos.entry_time as usize + 72) {
                let exit_price = current_close;
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let taker_fee = exit_price * pos.quantity * account.effective_fee_rate(false);

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(taker_fee);

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    gross_pnl,
                    taker_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    account.wallet_balance_usdt - (gross_pnl - taker_fee),
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                trailing_states.remove(&pos.position_id);
                continue;
            }

            surviving_positions.push(pos);
        }
        portfolio.positions = surviving_positions;

        // 3. Update floating metrics and drawdown
        account.unrealized_pnl_usdt = portfolio.total_unrealized_pnl(current_close);
        let equity = account.equity_usdt();
        if equity > peak_equity {
            peak_equity = equity;
        }
        let dd_pct = if peak_equity > 0.0 {
            ((peak_equity - equity) / peak_equity) * 100.0
        } else {
            0.0
        };
        if dd_pct > max_drawdown_pct {
            max_drawdown_pct = dd_pct;
        }
        let margin_util = account.margin_utilization_pct();
        if margin_util > max_margin_utilization {
            max_margin_utilization = margin_util;
        }
        portfolio.update_portfolio_heat(equity);

        // 4. Evaluate Opportunities (V8.3) or Expert hypotheses (V8.2)
        let t = i + 1;
        if t >= 32 && portfolio.positions.len() < params.max_concurrency {
            if is_v83_engine {
                let current_heat = portfolio.portfolio_heat_r;
                if let Ok(cycle) = v83_engine.step_bar(&store.symbol, "binance-um", store, i, &mut v83_book, current_heat) {
                    for campaign in cycle.campaigns_launched {
                        let dir_str = match campaign.exposure.direction {
                            crate::opportunity::exposure::ExposureDirection::Long => "LONG",
                            crate::opportunity::exposure::ExposureDirection::Short => "SHORT",
                            _ => continue,
                        };

                        let allowed_risk_usdt = equity * params.risk_fraction;
                        let stop_dist = current_atr * 1.5;
                        let stop_price = if dir_str == "LONG" {
                            current_close - stop_dist
                        } else {
                            current_close + stop_dist
                        };

                        let quant_res = QuantizationRiskEngine::compute_executable_lot(
                            &store.symbol,
                            current_close,
                            stop_price,
                            allowed_risk_usdt,
                            contract.lot_size_filter.step_size,
                            contract.lot_size_filter.min_qty,
                            contract.min_notional,
                            account.effective_fee_rate(false) * 20_000.0,
                        );

                        if quant_res.allocated_executable_qty > 0.0 {
                            let entry_price = current_close;
                            let qty = quant_res.allocated_executable_qty;
                            let notional = qty * entry_price;
                            let initial_margin = notional / params.leverage as f64;

                            if account.available_balance_usdt() >= initial_margin {
                                if let Ok(()) = account.lock_margin(initial_margin) {
                                    let entry_fee = notional * account.effective_fee_rate(false);
                                    account.deduct_fee(entry_fee);

                                    let bracket = contract.bracket_for_notional(notional);
                                    let liq = LiquidationModel::calculate_isolated_liquidation_price(
                                        dir_str,
                                        entry_price,
                                        qty,
                                        initial_margin,
                                        bracket,
                                    );

                                    let pos_id = format!("pos-{}", campaign.campaign_id);
                                    let tstate = DynamicTrailingEngine::new_state(
                                        ExitArm::ChandelierATR,
                                        dir_str,
                                        entry_price,
                                        stop_price,
                                        2.5,
                                    );
                                    trailing_states.insert(pos_id.clone(), tstate);

                                    portfolio.positions.push(OpenPosition {
                                        position_id: pos_id,
                                        candidate_id: campaign.opportunity_id.clone(),
                                        symbol: store.symbol.clone(),
                                        direction: dir_str.to_string(),
                                        entry_price,
                                        quantity: qty,
                                        initial_margin_usdt: initial_margin,
                                        isolated_margin_usdt: initial_margin,
                                        leverage: params.leverage,
                                        entry_time: i as i64,
                                        stop_loss_price: stop_price,
                                        take_profit_price: None,
                                        liquidation_price: liq,
                                        cum_funding_usdt: 0.0,
                                    });
                                    break;
                                }
                            } else {
                                *rejections.entry("INSUFFICIENT_AVAILABLE_BALANCE".to_string()).or_default() += 1;
                            }
                        } else {
                            *rejections.entry("MIN_EXECUTABLE_RISK_EXCEEDS_BUDGET".to_string()).or_default() += 1;
                        }
                    }
                }
            } else {
                let feats = state::state_features(store, t, as_of, 32);
                let hist = state::history_bars(store, t, 32);
                bar_votes.clear();

                for (eid, closure, allows_hist) in &projections {
                    let expert_hist = if *allows_hist { hist.clone() } else { Vec::new() };
                    let fm = crate::experts::base::FeatMap {
                        features: crate::experts::base::ProjectedFeatures::new(&feats, closure),
                        history: expert_hist,
                        as_of,
                        symbol: &store.symbol,
                        variant_overrides: &empty_variants,
                    };
                    let ev = crate::experts::evaluate(eid, &fm);
                    if ev.decision == "CANDIDATE" {
                        if let Some(draft) = &ev.draft {
                            let entry_price = current_close;
                            let stop_r = draft.geom_f64("stop_r").unwrap_or(1.0);
                            let stop_dist = stop_r * current_atr;
                            let stop_price = if draft.direction == "LONG" {
                                entry_price - stop_dist
                            } else {
                                entry_price + stop_dist
                            };

                            bar_votes.push(SensorVote {
                                sensor_id: eid.to_string(),
                                symbol: store.symbol.clone(),
                                direction: draft.direction.clone(),
                                entry_price,
                                stop_price,
                                timestamp_ns: as_of,
                                bar_index: i,
                            });
                        }
                    }
                }

                // Cluster votes into Multi-Family Campaigns (KZ-008)
                for vote in bar_votes.drain(..) {
                    let (cluster, is_new) = campaign_reg.ingest_vote(vote, current_close);

                    // Only admit if this is a newly formed campaign with diverse family confirmation
                    if is_new && cluster.direction != CampaignDirection::ConflictNeutral {
                        let dir_str = if cluster.direction == CampaignDirection::Long { "LONG" } else { "SHORT" };

                        // KZ-018: Cost-Aware No-Trade Region Check
                        let bars_since_fail = match last_failed_bar {
                            Some(fb) => i.saturating_sub(fb),
                            None => 999,
                        };
                        let is_same_fail_dir = match &last_failed_dir {
                            Some(d) => d == dir_str,
                            None => false,
                        };

                        let chop_ctx = ChopGateContext {
                            symbol: store.symbol.clone(),
                            bar_index: i,
                            timestamp_ns: as_of,
                            direction: dir_str.to_string(),
                            entry_price: cluster.consensus_entry,
                            structural_stop: cluster.structural_invalidation_price,
                            expected_gross_excursion_r: 2.5,
                            venue_roundtrip_friction_bps: 10.0,
                            bars_since_last_failed_campaign: bars_since_fail,
                            last_failed_campaign_same_direction: is_same_fail_dir,
                            rolling_volatility_compression_ratio: 0.85,
                        };

                        let chop_verdict = CostAwareNoTradeGate::evaluate(&chop_ctx, ChopSuppressionArm::A4CostAndCooldown);
                        if !chop_verdict.is_admitted {
                            *rejections.entry("CHOP_NO_TRADE_REGION_SUPPRESSED".to_string()).or_default() += 1;
                            continue;
                        }

                        // KZ-009: Quantization-Safe Risk Budgeting
                        let allowed_risk_usdt = equity * params.risk_fraction;
                        let quant_res = QuantizationRiskEngine::compute_executable_lot(
                            &store.symbol,
                            cluster.consensus_entry,
                            cluster.structural_invalidation_price,
                            allowed_risk_usdt,
                            contract.lot_size_filter.step_size,
                            contract.lot_size_filter.min_qty,
                            contract.min_notional,
                            account.effective_fee_rate(false) * 20_000.0,
                        );

                        if quant_res.allocated_executable_qty > 0.0 {
                            let entry_price = cluster.consensus_entry;
                            let qty = quant_res.allocated_executable_qty;
                            let notional = qty * entry_price;
                            let initial_margin = notional / params.leverage as f64;

                            if account.available_balance_usdt() >= initial_margin {
                                if let Ok(()) = account.lock_margin(initial_margin) {
                                    let entry_fee = notional * account.effective_fee_rate(false);
                                    account.deduct_fee(entry_fee);

                                    let bracket = contract.bracket_for_notional(notional);
                                    let liq = LiquidationModel::calculate_isolated_liquidation_price(
                                        dir_str,
                                        entry_price,
                                        qty,
                                        initial_margin,
                                        bracket,
                                    );

                                    let pos_id = format!("pos-{}", cluster.campaign_id);
                                    let tstate = DynamicTrailingEngine::new_state(
                                        ExitArm::ChandelierATR,
                                        dir_str,
                                        entry_price,
                                        cluster.structural_invalidation_price,
                                        2.5,
                                    );
                                    trailing_states.insert(pos_id.clone(), tstate);

                                    portfolio.positions.push(OpenPosition {
                                        position_id: pos_id,
                                        candidate_id: cluster.campaign_id.clone(),
                                        symbol: store.symbol.clone(),
                                        direction: dir_str.to_string(),
                                        entry_price,
                                        quantity: qty,
                                        initial_margin_usdt: initial_margin,
                                        isolated_margin_usdt: initial_margin,
                                        leverage: params.leverage,
                                        entry_time: i as i64,
                                        stop_loss_price: cluster.structural_invalidation_price,
                                        take_profit_price: None, // Chandelier trailing exit
                                        liquidation_price: liq,
                                        cum_funding_usdt: 0.0,
                                    });
                                    break; // Admitted 1 campaign for this bar
                                }
                            } else {
                                *rejections.entry("INSUFFICIENT_AVAILABLE_BALANCE".to_string()).or_default() += 1;
                            }
                        } else {
                            *rejections.entry("MIN_EXECUTABLE_RISK_EXCEEDS_BUDGET".to_string()).or_default() += 1;
                        }
                    }
                }
            }
        }
    }

    // Close remaining positions at terminal price
    let last_close = store.closes[n_bars - 1];
    let last_as_of = store.avail[n_bars - 1];
    for pos in portfolio.positions.drain(..) {
        let gross_pnl = if pos.direction == "LONG" {
            (last_close - pos.entry_price) * pos.quantity
        } else {
            (pos.entry_price - last_close) * pos.quantity
        };
        let taker_fee = last_close * pos.quantity * account.effective_fee_rate(false);
        account.release_margin(pos.initial_margin_usdt);
        account.apply_realized_pnl(gross_pnl);
        account.deduct_fee(taker_fee);

        let flow = EconomicCashflow::new(
            last_as_of,
            pos.candidate_id,
            pos.symbol,
            pos.direction,
            pos.quantity,
            pos.entry_price,
            last_close,
            gross_pnl,
            taker_fee,
            pos.cum_funding_usdt,
            0.0,
            0.0,
            account.wallet_balance_usdt - (gross_pnl - taker_fee),
            account.margin_utilization_pct(),
        )?;
        ledger.record(flow)?;
    }

    let terminal_equity = account.equity_usdt();
    let net_profit = terminal_equity - params.initial_balance;
    let total_return_pct = (net_profit / params.initial_balance) * 100.0;

    let n_admitted = ledger.flows.len();
    let n_wins = ledger.flows.iter().filter(|r| r.net_pnl_usdt > 0.0).count();
    let win_rate_pct = if n_admitted > 0 {
        (n_wins as f64 / n_admitted as f64) * 100.0
    } else {
        0.0
    };

    let gross_profit: f64 = ledger
        .flows
        .iter()
        .filter(|r| r.net_pnl_usdt > 0.0)
        .map(|r| r.net_pnl_usdt)
        .sum();
    let gross_loss: f64 = ledger
        .flows
        .iter()
        .filter(|r| r.net_pnl_usdt < 0.0)
        .map(|r| r.net_pnl_usdt.abs())
        .sum();
    let profit_factor = if gross_loss > 0.0 {
        gross_profit / gross_loss
    } else if gross_profit > 0.0 {
        99.0
    } else {
        0.0
    };

    let total_fee_drag_usdt: f64 = ledger.flows.iter().map(|r| r.commission_usdt).sum();
    let total_funding_usdt: f64 = ledger.flows.iter().map(|r| r.funding_cashflow_usdt).sum();

    // Persist cashflow ledger
    let cf_path = params.out_dir.join("economic-cashflow.jsonl");
    ledger.write_jsonl(&cf_path).map_err(|e| e.to_string())?;

    let receipt = PortfolioReceipt {
        receipt_id: format!("receipt-usdm-{}", last_as_of),
        initial_balance_usdt: params.initial_balance,
        terminal_equity_usdt: terminal_equity,
        net_profit_usdt: net_profit,
        total_return_pct,
        max_drawdown_pct,
        max_margin_utilization_pct: max_margin_utilization,
        total_fee_drag_usdt,
        total_funding_usdt,
        n_trades_admitted: n_admitted,
        win_rate_pct,
        profit_factor,
        rejections_by_reason: rejections,
        cashflow_ledger_path: "economic-cashflow.jsonl".to_string(),
        venue_contract_hash: contract.contract_hash(),
    };

    let receipt_json = serde_json::to_string_pretty(&receipt).map_err(|e| e.to_string())?;
    std::fs::write(params.out_dir.join("portfolio_receipt.json"), receipt_json).map_err(|e| e.to_string())?;

    Ok(receipt)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_usdm_sim_execution_on_certified_tape() {
        let tape_path = PathBuf::from("../research/tape/btcusdt-1h-12m/tape.jsonl");
        if !tape_path.exists() {
            return;
        }
        let out_dir = std::env::temp_dir().join("usdm_sim_test");
        std::fs::create_dir_all(&out_dir).ok();

        let params = UsdmSimParams {
            tape_path,
            out_dir: out_dir.clone(),
            initial_balance: 1000.0,
            risk_fraction: 0.005,
            leverage: 10,
            max_concurrency: 3,
            max_heat: 0.05,
            enabled_experts: None,
            engine_mode: None,
        };

        let res = run_simulation(&params);
        assert!(res.is_ok());
        let receipt = res.unwrap();
        assert!(receipt.n_trades_admitted > 0);
    }
}
