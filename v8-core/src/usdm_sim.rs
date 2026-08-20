//! Finite-Capital Binance USDⓈ-M Discrete-Event Portfolio Simulator.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §§1–11, Decisions D-109..D-116.

pub mod capital_viability;
pub mod differential;
pub mod maker_model;
pub mod scenario_ruin;

use crate::account::{AccountState, MarginMode};
use crate::allocator::RiskBudgetAllocator;
use crate::cashflow::{CashflowLedger, EconomicCashflow};
use crate::data::Dataset;
use crate::features;
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

/// Runs the USD-M finite-capital simulation engine.
pub fn run_simulation(params: &UsdmSimParams) -> Result<PortfolioReceipt, String> {
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
    let allocator = RiskBudgetAllocator::new(
        params.risk_fraction,
        params.leverage,
        params.max_concurrency,
        params.max_heat,
    );

    let mut ledger = CashflowLedger::new();
    let mut rejections: BTreeMap<String, usize> = BTreeMap::new();
    let mut peak_equity = account.equity_usdt();
    let mut max_drawdown_pct = 0.0;
    let mut max_margin_utilization = 0.0;

    let empty_variants = HashMap::new();
    let registry_rows = crate::experts::registry_rows();
    let projections: Vec<(&str, std::collections::HashSet<String>, bool)> = registry_rows
        .iter()
        .filter(|(eid, ported)| {
            if !*ported {
                return false;
            }
            if let Some(enabled) = &params.enabled_experts {
                enabled.iter().any(|name| name == *eid)
            } else {
                true
            }
        })
        .map(|(eid, _)| {
            let reqs = crate::experts::requires_for(eid);
            let closure = features::group_closure(reqs);
            let allows_hist = features::history_allowed(&closure);
            (*eid, closure, allows_hist)
        })
        .collect();

    // Bar-by-bar simulation loop
    for i in 0..n_bars {
        let current_open = store.opens[i];
        let current_high = store.highs[i];
        let current_low = store.lows[i];
        let current_close = store.closes[i];
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

        // 2. Evaluate active open positions against bar price action
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
                // Liquidated: full loss of isolated margin
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
                    pos.candidate_id,
                    pos.symbol,
                    pos.direction,
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
                continue;
            }

            // B. Check Stop Loss
            let stop_hit = if pos.direction == "LONG" {
                current_low <= pos.stop_loss_price
            } else {
                current_high >= pos.stop_loss_price
            };

            if stop_hit {
                // Fill at stop or open if gapped
                let exit_price = if pos.direction == "LONG" {
                    if current_open < pos.stop_loss_price {
                        current_open
                    } else {
                        pos.stop_loss_price
                    }
                } else {
                    if current_open > pos.stop_loss_price {
                        current_open
                    } else {
                        pos.stop_loss_price
                    }
                };
                let gap_penalty = (exit_price - pos.stop_loss_price).abs() * pos.quantity;
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
                    pos.candidate_id,
                    pos.symbol,
                    pos.direction,
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    gross_pnl,
                    taker_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    gap_penalty,
                    account.wallet_balance_usdt - (gross_pnl - taker_fee - gap_penalty),
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                continue;
            }

            // C. Check Take Profit
            let mut tp_hit = false;
            if let Some(tp) = pos.take_profit_price {
                if (pos.direction == "LONG" && current_high >= tp)
                    || (pos.direction == "SHORT" && current_low <= tp)
                {
                    tp_hit = true;
                }
            }

            if tp_hit {
                let exit_price = pos.take_profit_price.unwrap();
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let maker_fee = exit_price * pos.quantity * account.effective_fee_rate(true);

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(maker_fee);

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id,
                    pos.symbol,
                    pos.direction,
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    gross_pnl,
                    maker_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    account.wallet_balance_usdt - (gross_pnl - maker_fee),
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                continue;
            }

            // D. Check Expiry (24 hours = 24 bars)
            if (i + 1) >= (pos.entry_time as usize + 24) {
                // Expiry exit at bar close
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
                    pos.candidate_id,
                    pos.symbol,
                    pos.direction,
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

        // 4. Evaluate Expert hypotheses at bar close to form new candidate drafts
        let t = i + 1;
        if t >= 32 {
            let feats = state::state_features(store, t, as_of, 32);
            let mut map: HashMap<String, state::Feature> = HashMap::new();
            for f in &feats {
                map.insert(f.name.clone(), f.clone());
            }

            for (eid, closure, allows_hist) in &projections {
                let hist = if *allows_hist {
                    state::history_bars(store, t, 32)
                } else {
                    Vec::new()
                };
                let fm = crate::experts::base::FeatMap {
                    features: crate::experts::base::ProjectedFeatures::new(&map, closure),
                    history: hist,
                    as_of,
                    symbol: &store.symbol,
                    variant_overrides: &empty_variants,
                };
                let ev = crate::experts::evaluate(eid, &fm);
                if ev.decision == "CANDIDATE" {
                    if let Some(draft) = &ev.draft {
                        let entry_price = current_close;
                        let target_r = draft.geom_f64("target_r").unwrap_or(2.0);
                        let stop_r = draft.geom_f64("stop_r").unwrap_or(1.0);
                        let risk_unit = store.atr.get(i).copied().unwrap_or(entry_price * 0.01);
                        let stop_dist = stop_r * risk_unit;
                        let target_dist = target_r * risk_unit;

                        let (stop_price, target_price) = if draft.direction == "LONG" {
                            (entry_price - stop_dist, Some(entry_price + target_dist))
                        } else {
                            (entry_price + stop_dist, Some(entry_price - target_dist))
                        };

                        let cid = format!("cand-{}-{}-{}", eid, store.symbol, as_of);

                        match allocator.allocate(
                            &cid,
                            &store.symbol,
                            &draft.direction,
                            entry_price,
                            stop_price,
                            target_price,
                            24,
                            &contract,
                            &account,
                            &portfolio,
                        ) {
                            Ok(order) => {
                                if let Ok(()) = account.lock_margin(order.initial_margin_usdt) {
                                    // Deduct entry fee
                                    let entry_fee = order.entry_price * order.quantity * account.effective_fee_rate(false);
                                    account.deduct_fee(entry_fee);

                                    let bracket = contract.bracket_for_notional(order.quantity * order.entry_price);
                                    let liq = LiquidationModel::calculate_isolated_liquidation_price(
                                        &order.direction,
                                        order.entry_price,
                                        order.quantity,
                                        order.isolated_margin_usdt,
                                        bracket,
                                    );

                                    portfolio.positions.push(OpenPosition {
                                        position_id: format!("pos-{}", cid),
                                        candidate_id: cid,
                                        symbol: store.symbol.clone(),
                                        direction: order.direction,
                                        entry_price: order.entry_price,
                                        quantity: order.quantity,
                                        initial_margin_usdt: order.initial_margin_usdt,
                                        isolated_margin_usdt: order.isolated_margin_usdt,
                                        leverage: order.leverage,
                                        entry_time: i as i64,
                                        stop_loss_price: order.stop_loss_price,
                                        take_profit_price: order.take_profit_price,
                                        liquidation_price: liq,
                                        cum_funding_usdt: 0.0,
                                    });
                                }
                            }
                            Err(reason) => {
                                *rejections.entry(reason.as_str().to_string()).or_default() += 1;
                            }
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
            0.0,
        )?;
        ledger.record(flow)?;
    }

    // Write cashflow ledger
    std::fs::create_dir_all(&params.out_dir).map_err(|e| e.to_string())?;
    let cashflow_path = params.out_dir.join("economic-cashflow.jsonl");
    ledger.write_jsonl(&cashflow_path).map_err(|e| e.to_string())?;

    let n_trades = ledger.flows.len();
    let wins: Vec<f64> = ledger.flows.iter().map(|f| f.net_pnl_usdt).filter(|p| *p > 0.0).collect();
    let losses: Vec<f64> = ledger.flows.iter().map(|f| f.net_pnl_usdt).filter(|p| *p < 0.0).collect();
    let win_rate_pct = if n_trades > 0 { (wins.len() as f64 / n_trades as f64) * 100.0 } else { 0.0 };
    let gross_win: f64 = wins.iter().sum();
    let gross_loss: f64 = losses.iter().map(|l| l.abs()).sum();
    let pf = if gross_loss > 0.0 { gross_win / gross_loss } else { 99.0 };

    let terminal_equity = account.wallet_balance_usdt;
    let net_profit = terminal_equity - params.initial_balance;
    let total_return_pct = (net_profit / params.initial_balance) * 100.0;

    let receipt = PortfolioReceipt {
        receipt_id: format!("receipt-usdm-{}", last_as_of),
        initial_balance_usdt: params.initial_balance,
        terminal_equity_usdt: terminal_equity,
        net_profit_usdt: net_profit,
        total_return_pct,
        max_drawdown_pct,
        max_margin_utilization_pct: max_margin_utilization,
        total_fee_drag_usdt: ledger.total_commission(),
        total_funding_usdt: ledger.total_funding(),
        n_trades_admitted: n_trades,
        win_rate_pct,
        profit_factor: pf,
        rejections_by_reason: rejections,
        cashflow_ledger_path: "economic-cashflow.jsonl".to_string(),
        venue_contract_hash: contract.contract_hash(),
    };

    let receipt_path = params.out_dir.join("portfolio_receipt.json");
    let json = serde_json::to_string_pretty(&receipt).map_err(|e| e.to_string())?;
    std::fs::write(&receipt_path, json).map_err(|e| e.to_string())?;

    // D-116 Independent Engine Differential Reconciliation (Issue #AUD-003)
    let diff_trades: Vec<_> = ledger
        .flows
        .iter()
        .map(|c| {
            (
                c.candidate_id.clone(),
                c.event_time,
                c.symbol.clone(),
                c.direction.clone(),
                c.quantity,
                c.entry_price,
                c.exit_price,
                c.commission_usdt,
                c.funding_cashflow_usdt,
                c.wallet_balance_after,
            )
        })
        .collect();

    let (risk_report, diff_entries) = differential::reconcile_differential_parity(params.initial_balance, &diff_trades);
    differential::save_differential_artifacts(&params.out_dir, &risk_report, &diff_entries)
        .map_err(|e| e.to_string())?;

    Ok(receipt)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_usdm_sim_execution_on_certified_tape() {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
        let tape_path = root.join("research/tape/btcusdt-1h-12m/tape.jsonl");
        if !tape_path.exists() {
            return;
        }

        let out_dir = root.join(".audit/rust_audit_current_test_tmp");
        let params = UsdmSimParams {
            tape_path,
            out_dir: out_dir.clone(),
            initial_balance: 1000.0,
            risk_fraction: 0.005,
            leverage: 10,
            max_concurrency: 3,
            max_heat: 0.05,
            enabled_experts: None,
        };

        let receipt = run_simulation(&params).expect("Simulation should run successfully");
        assert_eq!(receipt.initial_balance_usdt, 1000.0);
        assert!(receipt.n_trades_admitted > 0);
        assert!(out_dir.join("economic-cashflow.jsonl").exists());
        assert!(out_dir.join("portfolio_receipt.json").exists());

        let _ = std::fs::remove_dir_all(out_dir);
    }
}

