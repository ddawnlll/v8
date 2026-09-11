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
    #[serde(default = "default_decision_stride_bars")]
    pub decision_stride_bars: usize,
    #[serde(default)]
    pub enabled_experts: Option<Vec<String>>,
    #[serde(default)]
    pub variant_overrides: HashMap<String, String>,
    #[serde(default)]
    pub engine_mode: Option<String>,
    #[serde(default)]
    pub exit_arm: Option<ExitArm>,
    #[serde(default)]
    pub symbol: Option<String>,
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
fn default_decision_stride_bars() -> usize {
    1
}
fn default_evidence_role() -> String {
    "BURNED_DIAGNOSTIC".to_string()
}
fn default_promotion_authority() -> String {
    "NONE".to_string()
}

/// Structured execution receipt emitted to `.audit/rust_audit_current/portfolio_receipt.json`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioReceipt {
    pub receipt_id: String,
    pub initial_balance_usdt: f64,
    pub terminal_equity_usdt: f64,
    pub net_profit_usdt: f64,
    pub gross_market_pnl_usdt: f64,
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
    /// D-152: quad/tape output is typed diagnostic evidence, never a promotion.
    #[serde(default = "default_evidence_role")]
    pub evidence_role: String,
    #[serde(default = "default_promotion_authority")]
    pub promotion_authority: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub frontier_receipt: Option<crate::opportunity::frontier::EconomicFrontierReceipt>,
}

/// Runs the USD-M finite-capital simulation engine with Kaizen architecture.
pub fn run_simulation(params: &UsdmSimParams) -> Result<PortfolioReceipt, String> {
    crate::experts::validate_variant_overrides(&params.variant_overrides)?;
    let _ = std::fs::create_dir_all(&params.out_dir);
    let rows = crate::read_tape(&params.tape_path)?;
    let ds = Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = crate::state::build_stores(&ds);
    run_simulation_with_stores(params, &stores)
}

/// Runs the USD-M finite-capital simulation engine with pre-built feature stores.
pub fn run_simulation_with_stores(
    params: &UsdmSimParams,
    stores: &[crate::state::FeatureStore],
) -> Result<PortfolioReceipt, String> {
    crate::experts::validate_variant_overrides(&params.variant_overrides)?;
    let _ = std::fs::create_dir_all(&params.out_dir);

    let store = match &params.symbol {
        Some(sym) => stores.iter().find(|s| s.symbol == *sym),
        None => stores.iter().find(|s| s.symbol == "BTCUSDT"),
    }
    .or_else(|| stores.first())
    .ok_or_else(|| "No symbol series found in tape".to_string())?;

    let n_bars = store.closes.len();
    if n_bars == 0 {
        return Err("Tape is empty".to_string());
    }

    let contract = VenueContract::for_symbol(&store.symbol);
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
    let mut last_exit_bar: Option<usize> = None;
    let mut last_failed_bar: Option<usize> = None;
    let mut last_failed_dir: Option<String> = None;

    let is_v83_engine = params.engine_mode.as_deref() == Some("v8.3") || params.engine_mode.as_deref() == Some("opportunity");
    let v83_engine = crate::opportunity::runloop::V83Runloop::default();
    let mut v83_book = crate::opportunity::book::OpportunityBook::new();

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

    let mut all_emitted_candidates: Vec<(usize, String)> = Vec::new();
    let mut bar_votes: Vec<SensorVote> = Vec::with_capacity(32);
    let mut next_funding = 0;

    for i in 0..n_bars {
        let frame = store.causal_frame(i);
        let current_close = frame.close;
        let current_open = frame.open;
        let current_high = frame.high;
        let current_low = frame.low;
        let current_atr = frame.atr.unwrap_or(current_close * 0.01);
        let as_of = frame.decision_time.0;
        // Consume observed settlement events once, at availability. Decision
        // clocks need not fall exactly on a funding boundary. The existing
        // bar model values notional at this bar's open, not a venue mark price.
        while next_funding < store.funding_avail.len()
            && store.funding_avail[next_funding] <= as_of
        {
            let settlement_time = store.funding_event_times[next_funding];
            let current_funding_rate = store.funding_rate[next_funding];
            apply_funding_event(
                &mut account,
                &mut portfolio.positions,
                settlement_time,
                current_funding_rate,
                current_open,
            )?;
            next_funding += 1;
        }

        // 2. Evaluate active open positions against bar price action (Dynamic Chandelier Trailing)
        let mut surviving_positions = Vec::new();
        for mut pos in portfolio.positions.drain(..) {
            // Update MFE/MAE in R units
            let r_value = pos.nominal_risk_usdt();
            if r_value > 0.0 {
                let unrealized_r = pos.unrealized_pnl(current_close) / r_value;
                pos.mfe_r = pos.mfe_r.max(unrealized_r);
                pos.mae_r = pos.mae_r.min(unrealized_r);
            }

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
                let exit_price = if pos.direction == "LONG" {
                    liq_price.clamp(current_low, current_high)
                } else {
                    liq_price.clamp(current_low, current_high)
                };
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let taker_fee = exit_price * pos.quantity * account.effective_fee_rate(false);
                let entry_fee = pos.entry_price * pos.quantity * account.effective_fee_rate(false);
                let total_fee = entry_fee + taker_fee;

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(taker_fee);

                let balance_before = account.wallet_balance_usdt - (gross_pnl - taker_fee) + entry_fee - pos.cum_funding_usdt;

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id.clone(),
                    pos.expert_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    "LIQUIDATED".to_string(),
                    gross_pnl,
                    total_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    balance_before,
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                trailing_states.remove(&pos.position_id);
                last_exit_bar = Some(i);
                last_failed_bar = Some(i);
                last_failed_dir = Some(pos.direction);
                continue;
            }

            // B. Check Dynamic Trailing Stop (KZ-007)
            let mut stop_exit = false;
            let mut exit_price = pos.stop_loss_price;

            if let Some(tstate) = trailing_states.get_mut(&pos.position_id) {
                let engine_str = params.engine_mode.as_deref().unwrap_or("squeeze-swing");
                let trail_window: usize = match engine_str {
                    "macro-m2" | "macro-m3" | "macro-swing" => 48,
                    _ => 24,
                };
                let s_trail = i.saturating_sub(trail_window.saturating_sub(1));
                let struct_stop = if pos.direction == "LONG" {
                    store.lows[s_trail..=i].iter().cloned().fold(f64::INFINITY, f64::min)
                } else {
                    store.highs[s_trail..=i].iter().cloned().fold(f64::NEG_INFINITY, f64::max)
                };
                if let Some(res) = DynamicTrailingEngine::step_bar(tstate, i, current_high, current_low, current_close, current_atr, Some(struct_stop)) {
                    stop_exit = true;
                    exit_price = res.exit_price.clamp(current_low, current_high);
                }
            } else {
                let stop_hit = if pos.direction == "LONG" {
                    current_low <= pos.stop_loss_price
                } else {
                    current_high >= pos.stop_loss_price
                };
                if stop_hit {
                    stop_exit = true;
                    exit_price = pos.stop_loss_price.clamp(current_low, current_high);
                }
            }

            if stop_exit {
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let taker_fee = exit_price * pos.quantity * account.effective_fee_rate(false);
                let entry_fee = pos.entry_price * pos.quantity * account.effective_fee_rate(false);
                let total_fee = entry_fee + taker_fee;

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(taker_fee);

                last_exit_bar = Some(i);
                if gross_pnl < 0.0 {
                    last_exit_bar = Some(i);
                last_failed_bar = Some(i);
                    last_failed_dir = Some(pos.direction.clone());
                }

                let balance_before = account.wallet_balance_usdt - (gross_pnl - taker_fee) + entry_fee - pos.cum_funding_usdt;

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id.clone(),
                    pos.expert_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    "TRAILING_STOP".to_string(),
                    gross_pnl,
                    total_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    balance_before,
                    account.margin_utilization_pct(),
                )?;
                ledger.record(flow)?;
                trailing_states.remove(&pos.position_id);
                continue;
            }

            // C. Check Maximum Expiry (336 hours = 14 days for macro swing, 72 hours for standard campaigns)
            let max_bars = if pos.candidate_id.contains("squeeze_swing") { 336 } else { 72 };
            if (i + 1) >= (pos.entry_time as usize + max_bars) {
                let exit_price = current_close;
                let gross_pnl = if pos.direction == "LONG" {
                    (exit_price - pos.entry_price) * pos.quantity
                } else {
                    (pos.entry_price - exit_price) * pos.quantity
                };
                let taker_fee = exit_price * pos.quantity * account.effective_fee_rate(false);
                let entry_fee = pos.entry_price * pos.quantity * account.effective_fee_rate(false);
                let total_fee = entry_fee + taker_fee;

                account.release_margin(pos.initial_margin_usdt);
                account.apply_realized_pnl(gross_pnl);
                account.deduct_fee(taker_fee);

                let balance_before = account.wallet_balance_usdt - (gross_pnl - taker_fee) + entry_fee - pos.cum_funding_usdt;

                let flow = EconomicCashflow::new(
                    as_of,
                    pos.candidate_id.clone(),
                    pos.expert_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    exit_price,
                    "MAX_EXPIRY".to_string(),
                    gross_pnl,
                    total_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    balance_before,
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
        let decision_stride_bars = params.decision_stride_bars.max(1);
        if t >= 32
            && portfolio.positions.len() < params.max_concurrency
            && i % decision_stride_bars == 0
        {
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
                                    let chosen_arm = params.exit_arm.clone().unwrap_or(ExitArm::ChandelierATR);
                                    let tstate = DynamicTrailingEngine::new_state(
                                        chosen_arm,
                                        dir_str,
                                        entry_price,
                                        stop_price,
                                        2.5,
                                    );
                                    trailing_states.insert(pos_id.clone(), tstate);

                                portfolio.positions.push(OpenPosition {
                                    position_id: pos_id,
                                    candidate_id: campaign.opportunity_id.clone(),
                                    expert_id: campaign.exposure.exposure_id.clone(),
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
                                     mfe_r: 0.0,
                                     mae_r: 0.0,
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
                let engine_str = params.engine_mode.as_deref().unwrap_or("squeeze-swing");
                let _is_squeeze_mode = matches!(engine_str, "squeeze-swing" | "swing" | "macro-m1" | "macro-m2" | "macro-m3" | "macro-swing");
                let feats = state::state_features(store, t, as_of, 32);
                let hist = state::history_bars(store, t, 128);
                bar_votes.clear();

                // Compute PIT 20-bar Kaufman Trend Efficiency Ratio (ER)
                let close_change = if hist.len() >= 20 { (current_close - hist[hist.len() - 20].close).abs() } else { 0.0 };
                let mut total_path = 0.0;
                if hist.len() >= 20 {
                    for k in (hist.len() - 19)..hist.len() {
                        total_path += (hist[k].close - hist[k - 1].close).abs();
                    }
                }
                let kaufman_er = if total_path > 1e-6 { close_change / total_path } else { 0.0 };

                // Compute PIT Dynamic Volume Expansion & Volatility Compression on bar i
                let vol_cur = store.volumes.get(i).copied().unwrap_or(1.0);
                let s20 = i.saturating_sub(19);
                let vol_sum: f64 = store.volumes[s20..=i].iter().copied().sum();
                let vol_avg20 = vol_sum / (i - s20 + 1) as f64;
                let vol_ratio = if vol_avg20 > 0.0 { vol_cur / vol_avg20 } else { 1.0 };

                let s50 = i.saturating_sub(49);
                let atr50 = if i >= 14 {
                    let tr_sum: f64 = (s50..=i).map(|k| {
                        let h = store.highs[k];
                        let l = store.lows[k];
                        let pc = if k > 0 { store.closes[k-1] } else { store.opens[k] };
                        (h - l).max((h - pc).abs()).max((l - pc).abs())
                    }).sum();
                    tr_sum / (i - s50 + 1) as f64
                } else {
                    current_atr
                };
                let compression_ratio = if atr50 > 1e-6 { current_atr / atr50 } else { 1.0 };

                for (eid, closure, allows_hist) in &projections {
                    // Focus on Certified Net Alpha Producing Strategy Families, or requested experts
                    let is_alpha_expert = if params.enabled_experts.as_ref().unwrap_or(&Vec::new()).is_empty() {
                        matches!(
                            *eid,
                            "floor_trader_pivot"
                                | "failed_breakout"
                                | "fib_projection_reversal"
                                | "liquidity_sweep_reclaim"
                                | "range_breakout_1to1"
                                | "ichimoku_cloud"
                        )
                    } else {
                        params.enabled_experts.as_ref().unwrap().contains(&eid.to_string())
                    };
                    if !is_alpha_expert {
                        continue;
                    }

                    let expert_hist = if *allows_hist { hist.as_slice() } else { &[] };
                    let fm = crate::experts::base::FeatMap {
                        features: crate::experts::base::ProjectedFeatures::new(&feats, closure),
                        history: expert_hist,
                        as_of,
                        symbol: &store.symbol,
                        variant_overrides: &params.variant_overrides,
                    };
                    let ev = crate::experts::evaluate(eid, &fm);
                    if ev.decision == "CANDIDATE" {
                        if let Some(draft) = &ev.draft {
                            all_emitted_candidates.push((i, draft.direction.clone()));
                            let entry_price = current_close;
                            let stop_r = draft.geom_f64("stop_r").unwrap_or(1.0);
                            let stop_dist = stop_r * current_atr;
                            let stop_price = if draft.direction == "LONG" {
                                entry_price - stop_dist
                            } else {
                                entry_price + stop_dist
                            };

                            // D-141/D-144 Regime Gate: Require minimum trend efficiency (ER >= 0.18 or volume surge >= 1.20)
                            if kaufman_er >= 0.18 || vol_ratio >= 1.20 {
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
                }

                // Evaluate TrendContinuationExpert (D-138)
                let eval_tc = params.enabled_experts.as_ref().unwrap_or(&Vec::new()).is_empty() || params.enabled_experts.as_ref().unwrap_or(&Vec::new()).contains(&"trend_continuation".to_string());
                if eval_tc {
                let tc_closure = features::group_closure(&["trend", "volatility", "history"]);
                let fm_tc = crate::experts::base::FeatMap {
                    features: crate::experts::base::ProjectedFeatures::new(&feats, &tc_closure),
                    history: &hist,
                    as_of,
                    symbol: &store.symbol,
                    variant_overrides: &params.variant_overrides,
                };
                let ev_tc = crate::experts::trend_continuation::trend_continuation(&fm_tc, "trend_continuation", "v1");
                if ev_tc.decision == "CANDIDATE" {
                    if let Some(draft) = &ev_tc.draft {
                        all_emitted_candidates.push((i, draft.direction.clone()));
                        let close_change = if hist.len() >= 20 { (current_close - hist[hist.len() - 20].close).abs() } else { 0.0 };
                        let mut total_path = 0.0;
                        if hist.len() >= 20 {
                            for k in (hist.len() - 19)..hist.len() {
                                total_path += (hist[k].close - hist[k-1].close).abs();
                            }
                        }
                        let er = if total_path > 1e-6 { close_change / total_path } else { 0.0 };
                        if compression_ratio >= 0.80 && er >= 0.18 {
                            let entry_price = current_close;
                            let stop_r = draft.geom_f64("stop_r").unwrap_or(1.0);
                            let stop_dist = stop_r * current_atr;
                            let stop_price = if draft.direction == "LONG" {
                                entry_price - stop_dist
                            } else {
                                entry_price + stop_dist
                            };
                            bar_votes.push(SensorVote {
                                sensor_id: "trend_continuation".to_string(),
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

                } // end eval_tc
                // Evaluate SqueezeReleaseSwingExpert (D-140 / H-MACRO-01)
                let eval_ss = params.enabled_experts.as_ref().unwrap_or(&Vec::new()).is_empty() || params.enabled_experts.as_ref().unwrap_or(&Vec::new()).contains(&"squeeze_swing".to_string());
                if eval_ss {
                let engine_str = params
                    .variant_overrides
                    .get("squeeze_swing")
                    .map(|variant| match variant.as_str() {
                        "m1" => "macro-m1",
                        "m2" => "macro-m2",
                        "m3" => "macro-m3",
                        _ => "squeeze-swing",
                    })
                    .or(params.engine_mode.as_deref())
                    .unwrap_or("squeeze-swing");
                let (max_bw, lookback, vol_min, cooldown_bars, struct_trail_bars) = match engine_str {
                    "macro-m1" => (0.25, 48, 1.40, 48, 24),
                    "macro-m2" => (0.30, 72, 1.35, 48, 48),
                    "macro-m3" | "macro-swing" => (0.25, 72, 1.40, 48, 48),
                    _ => (0.35, 48, 1.30, 24, 24),
                };

                let ss_closure = features::group_closure(&["trend", "volatility", "participation", "history"]);
                let fm_ss = crate::experts::base::FeatMap {
                    features: crate::experts::base::ProjectedFeatures::new(&feats, &ss_closure),
                    history: &hist,
                    as_of,
                    symbol: &store.symbol,
                    variant_overrides: &params.variant_overrides,
                };
                let ev_ss = crate::experts::squeeze_swing::squeeze_swing_custom(&fm_ss, "squeeze_swing", "v1", max_bw, lookback, vol_min);
                if ev_ss.decision == "CANDIDATE" {
                    if let Some(draft) = &ev_ss.draft {
                        all_emitted_candidates.push((i, draft.direction.clone()));
                        let bars_since_last_exit = match last_exit_bar {
                            Some(eb) => i.saturating_sub(eb),
                            None => 999,
                        };
                        // Enforce mandatory post-exit cooldown per asset (win or loss)
                        if bars_since_last_exit >= cooldown_bars {
                            let entry_price = current_close;
                            let s_init = hist.len().saturating_sub(struct_trail_bars);
                            let struct_stop = if draft.direction == "LONG" {
                                hist[s_init..].iter().map(|b| b.low).fold(f64::INFINITY, f64::min).min(entry_price - 1.5 * current_atr)
                            } else {
                                hist[s_init..].iter().map(|b| b.high).fold(f64::NEG_INFINITY, f64::max).max(entry_price + 1.5 * current_atr)
                            };
                            bar_votes.push(SensorVote {
                                sensor_id: "squeeze_swing".to_string(),
                                symbol: store.symbol.clone(),
                                direction: draft.direction.clone(),
                                entry_price,
                                stop_price: struct_stop,
                                timestamp_ns: as_of,
                                bar_index: i,
                            });
                        }
                    }
                }
                } // end eval_ss

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
                            expected_gross_excursion_r: if vol_ratio >= 1.2 { 3.0 } else { 2.5 },
                            venue_roundtrip_friction_bps: 10.0,
                            bars_since_last_failed_campaign: bars_since_fail,
                            last_failed_campaign_same_direction: is_same_fail_dir,
                            rolling_volatility_compression_ratio: compression_ratio,
                        };

                        let chop_verdict = CostAwareNoTradeGate::evaluate(&chop_ctx, ChopSuppressionArm::A4CostAndCooldown);
                        if !chop_verdict.is_admitted {
                            *rejections.entry(chop_verdict.reason_code).or_default() += 1;
                            continue;
                        }

                        // ETS Economic Margin Gate: Ensure structural target/stop distance >= ATR-scaled friction floor
                        let stop_dist_pct = (cluster.consensus_entry - cluster.structural_invalidation_price).abs() / cluster.consensus_entry;
                        let min_stop_dist_pct = (0.50 * current_atr / cluster.consensus_entry).max(0.007);
                        if stop_dist_pct < min_stop_dist_pct {
                            *rejections.entry("ECONOMIC_MARGIN_BELOW_FRICTION_FLOOR".to_string()).or_default() += 1;
                            continue;
                        }

                        // ETS Filter: Suppress low-volume unconfirmed micro-noise churn (require volume surge >= 1.15x or high compression release)
                        if vol_ratio < 1.15 && (vol_ratio < 1.00 || compression_ratio < 0.80) {
                            *rejections.entry("SUB_EXPANSION_MICRO_NOISE_SUPPRESSED".to_string()).or_default() += 1;
                            continue;
                        }

                        // KZ-009 + ETS: Cost-Aware & Conviction-Weighted Capital Budgeting
                        let conviction_scale = if vol_ratio >= 1.40 {
                            1.35
                        } else if vol_ratio >= 1.20 {
                            1.10
                        } else {
                            0.80
                        };
                        let allowed_risk_usdt = equity * params.risk_fraction * conviction_scale;
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
                                    let chosen_arm = if let Some(arm) = &params.exit_arm {
                                        arm.clone()
                                    } else if cluster.participating_sensors.contains(&"squeeze_swing".to_string()) {
                                        let engine_str = params.engine_mode.as_deref().unwrap_or("squeeze-swing");
                                        match engine_str {
                                            "macro-m2" | "macro-m3" | "macro-swing" => ExitArm::HybridTrail,
                                            _ => ExitArm::Structural24hTrail,
                                        }
                                    } else {
                                        ExitArm::HybridTrail
                                    };
                                    let tstate = DynamicTrailingEngine::new_state(
                                        chosen_arm,
                                        dir_str,
                                        entry_price,
                                        cluster.structural_invalidation_price,
                                        3.0,
                                    );
                                    trailing_states.insert(pos_id.clone(), tstate);

                                    portfolio.positions.push(OpenPosition {
                                        position_id: pos_id,
                                        candidate_id: cluster.campaign_id.clone(),
                                        expert_id: cluster.participating_sensors.first().cloned().unwrap_or_default(),
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
                                         mfe_r: 0.0,
                                         mae_r: 0.0,
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
        let entry_fee = pos.entry_price * pos.quantity * account.effective_fee_rate(false);
        account.release_margin(pos.initial_margin_usdt);
        account.apply_realized_pnl(gross_pnl);
        account.deduct_fee(taker_fee);

                let flow = EconomicCashflow::new(
                    last_as_of,
                    pos.candidate_id.clone(),
                    pos.expert_id.clone(),
                    pos.symbol.clone(),
                    pos.direction.clone(),
                    pos.quantity,
                    pos.entry_price,
                    last_close,
                    "TERMINAL_CLOSE".to_string(),
                    gross_pnl,
                    entry_fee + taker_fee,
                    pos.cum_funding_usdt,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    account.wallet_balance_usdt - (gross_pnl - taker_fee) + entry_fee - pos.cum_funding_usdt,
                    account.margin_utilization_pct(),
                )?;
        ledger.record(flow)?;
    }

    // All positions are closed; do not count the last floating PnL twice.
    account.unrealized_pnl_usdt = 0.0;
    let terminal_equity = account.equity_usdt();
    let reconciled_equity =
        params.initial_balance + ledger.flows.iter().map(|f| f.net_pnl_usdt).sum::<f64>();
    if !terminal_equity.is_finite()
        || !reconciled_equity.is_finite()
        || (terminal_equity - reconciled_equity).abs() > 1e-6
    {
        return Err(format!(
            "terminal equity does not reconcile: account={terminal_equity}, ledger={reconciled_equity}"
        ));
    }
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

    // Construct Oracle Ground Truth Episodes (O1) and Evaluate Economic Opportunity Capture Frontier (D-138)
    let oracle_def = crate::oracle::episode::OracleDefinition::new(
        &store.symbol,
        24,
        0.015,
        0.008,
        2.0,
        10.0,
        true,
    );
    let atrs: Vec<f64> = (0..n_bars).map(|k: usize| {
        let s = k.saturating_sub(13);
        let tr_sum: f64 = (s..=k).map(|idx| {
            let h = store.highs[idx];
            let l = store.lows[idx];
            let pc = if idx > 0 { store.closes[idx-1] } else { store.opens[idx] };
            (h - l).max((h - pc).abs()).max((l - pc).abs())
        }).sum();
        tr_sum / (k - s + 1).max(1) as f64
    }).collect();
    let oracle_episodes = crate::oracle::episode::OracleEpisodeExtractor::extract_episodes(
        &oracle_def,
        &store.highs,
        &store.lows,
        &store.closes,
        &store.volumes,
        &atrs,
    );

    let executed_trades_for_frontier: Vec<(usize, String, f64, f64, f64)> = ledger
        .flows
        .iter()
        .map(|f| {
            let t_bar = store.avail.iter().position(|&t| t >= f.event_time).unwrap_or(0);
            (t_bar, f.direction.clone(), f.gross_market_pnl_usdt, f.commission_usdt, f.net_pnl_usdt)
        })
        .collect();

    let frontier_receipt = crate::opportunity::frontier::FrontierEvaluator::evaluate_frontier(
        &store.symbol,
        &oracle_def.definition_id,
        &oracle_episodes,
        &all_emitted_candidates,
        &executed_trades_for_frontier,
    );

    let total_fee_drag_usdt: f64 = ledger.flows.iter().map(|r| r.commission_usdt).sum();
    let total_funding_usdt: f64 = ledger.flows.iter().map(|r| r.funding_cashflow_usdt).sum();
    let gross_market_pnl_usdt = ledger.total_gross_pnl();

    // Persist cashflow ledger
    let cf_path = params.out_dir.join("economic-cashflow.jsonl");
    ledger.write_jsonl(&cf_path).map_err(|e| e.to_string())?;

    let receipt = PortfolioReceipt {
        receipt_id: format!("receipt-usdm-{}", last_as_of),
        initial_balance_usdt: params.initial_balance,
        terminal_equity_usdt: terminal_equity,
        net_profit_usdt: net_profit,
        gross_market_pnl_usdt,
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
        evidence_role: default_evidence_role(),
        promotion_authority: default_promotion_authority(),
        frontier_receipt: Some(frontier_receipt),
    };

    let receipt_json = serde_json::to_string_pretty(&receipt).map_err(|e| e.to_string())?;
    std::fs::write(params.out_dir.join("portfolio_receipt.json"), receipt_json).map_err(|e| e.to_string())?;

    Ok(receipt)
}

/// Applies an observed event only to exposure already open at settlement.
fn apply_funding_event(
    account: &mut AccountState,
    positions: &mut [OpenPosition],
    settlement_time: i64,
    rate: f64,
    price: f64,
) -> Result<(), String> {
    if !rate.is_finite() || !price.is_finite() || price <= 0.0 {
        return Err("invalid funding observation".into());
    }
    for pos in positions {
        if pos.entry_time >= settlement_time {
            continue;
        }
        let sign = match pos.direction.as_str() {
            "LONG" => -1.0,
            "SHORT" => 1.0,
            _ => return Err("invalid funding position direction".into()),
        };
        let cashflow = sign * pos.quantity * price * rate;
        account.apply_funding(cashflow);
        pos.cum_funding_usdt += cashflow;
    }
    Ok(())
}
