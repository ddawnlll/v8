//! Nautilus simulation execution runner.
//!
//! Executes backtest runs using native NautilusTrader `BacktestEngine`, replacing
//! `usdm_sim` for all execution, matching, fill, and accounting responsibilities.

use super::data::{
    convert_feature_store_to_nautilus_data, create_binance_perpetual_instrument,
    precision_from_step,
};
use super::strategy::V8ExpertStrategy;
use crate::data::Dataset;
use crate::experts;
use crate::usdm_sim::{PortfolioReceipt, UsdmSimParams};
use crate::venue::VenueContract;
use nautilus_backtest::{
    config::{BacktestEngineConfig, SimulatedVenueConfig},
    engine::BacktestEngine,
};
use nautilus_model::{
    accounts::Account,
    data::{BarSpecification, BarType},
    enums::{AccountType, AggregationSource, BarAggregation, BookType, OmsType, PriceType},
    identifiers::{InstrumentId, Venue},
    instruments::InstrumentAny,
    types::{Currency, Money},
};
use std::collections::BTreeMap;
use std::rc::Rc;

/// Runs finite-capital simulation directly through NautilusTrader matching and accounting engine.
pub fn run_nautilus_simulation(params: &UsdmSimParams) -> Result<PortfolioReceipt, String> {
    experts::validate_variant_overrides(&params.variant_overrides)?;
    let _ = std::fs::create_dir_all(&params.out_dir);

    // 1. Ingest historical tape
    let rows = crate::read_tape(&params.tape_path)?;
    let ds = Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = crate::state::build_stores(&ds);

    let store = match &params.symbol {
        Some(sym) => stores.iter().find(|s| s.symbol == *sym),
        None => stores.iter().find(|s| s.symbol == "BTCUSDT"),
    }
    .or_else(|| stores.first())
    .ok_or_else(|| "No symbol series found in tape".to_string())?;

    if store.closes.is_empty() {
        return Err("Tape is empty".to_string());
    }

    let contract = VenueContract::for_symbol(&store.symbol);
    let venue_str = "BINANCE";
    let venue = Venue::from(venue_str);
    let usdt_currency = Currency::from("USDT");

    // 2. Build native Nautilus Perpetual instrument
    let instrument =
        create_binance_perpetual_instrument(&store.symbol, venue_str, params.leverage)?;
    let instrument_id = instrument.id;
    let price_precision = precision_from_step(contract.price_filter.tick_size);
    let size_precision = precision_from_step(contract.lot_size_filter.step_size);
    let inst_any = InstrumentAny::CryptoPerpetual(instrument);

    // 3. Convert tape into Nautilus Data events
    let data = convert_feature_store_to_nautilus_data(
        store,
        instrument_id,
        price_precision,
        size_precision,
    )?;

    // 4. Configure and instantiate Nautilus BacktestEngine
    let mut engine = BacktestEngine::new(BacktestEngineConfig::default())
        .map_err(|e| format!("Failed to create BacktestEngine: {e}"))?;

    let starting_money = Money::new(params.initial_balance, usdt_currency);
    let venue_config = SimulatedVenueConfig::builder()
        .venue(venue)
        .oms_type(OmsType::Netting)
        .account_type(AccountType::Margin)
        .book_type(BookType::L1_MBP)
        .starting_balances(vec![starting_money])
        .build()
        .map_err(|e| format!("Failed to build SimulatedVenueConfig: {e}"))?;

    engine
        .add_venue(venue_config)
        .map_err(|e| format!("Failed to add venue: {e}"))?;

    engine
        .add_instrument(&inst_any)
        .map_err(|e| format!("Failed to add instrument: {e}"))?;

    // 5. Add V8 Expert Strategy
    let expert_name = params
        .enabled_experts
        .as_ref()
        .and_then(|e| e.first().cloned())
        .unwrap_or_else(|| "squeeze_swing".to_string());

    let spec = BarSpecification::new_checked(1, BarAggregation::Hour, PriceType::Last)
        .map_err(|e| format!("Invalid BarSpecification: {e}"))?;
    let bar_type = BarType::new(instrument_id, spec, AggregationSource::External);

    let strategy = V8ExpertStrategy::new(
        instrument_id,
        bar_type,
        Rc::new(store.clone()),
        expert_name,
        params.initial_balance,
        params.risk_fraction,
        params.leverage,
        params.max_concurrency,
        params.variant_overrides.clone(),
        contract.lot_size_filter.step_size,
        contract.lot_size_filter.min_qty,
        size_precision,
    );

    engine
        .add_strategy(strategy)
        .map_err(|e| format!("Failed to add strategy: {e}"))?;

    // 6. Ingest chronological market and funding data
    engine
        .add_data(data, None, true, true)
        .map_err(|e| format!("Failed to add data to engine: {e}"))?;

    // 7. Run simulation
    engine
        .run(None, None, None, false)
        .map_err(|e| format!("Nautilus simulation run failed: {e}"))?;

    // 8. Extract real accounting & execution metrics from Nautilus
    let result = engine.get_result();
    let cache = engine.kernel().cache.borrow();
    let account_opt = cache.account_for_venue(&venue);

    let terminal_equity = account_opt.as_ref().map_or(params.initial_balance, |acc| {
        acc.balance(Some(usdt_currency))
            .map_or(params.initial_balance, |b| b.total.as_f64())
    });

    let total_fees = account_opt.as_ref().map_or(0.0, |acc| match acc.as_ref() {
        nautilus_model::accounts::AccountAny::Margin(m) => {
            m.commission(&usdt_currency).map_or(0.0, |c| c.as_f64())
        }
        _ => 0.0,
    });

    let net_profit = terminal_equity - params.initial_balance;
    let gross_pnl = net_profit + total_fees;
    let total_return_pct = if params.initial_balance > 0.0 {
        (net_profit / params.initial_balance) * 100.0
    } else {
        0.0
    };

    let pnl_stats = result.stats_pnls.get("USDT");
    let n_positions = result.total_positions;

    let win_rate_pct = pnl_stats
        .and_then(|m| m.get("Win Rate"))
        .map(|&wr| wr * 100.0)
        .unwrap_or(0.0);

    let profit_factor = result
        .stats_returns
        .get("Profit Factor")
        .or_else(|| pnl_stats.and_then(|m| m.get("Profit Factor")))
        .copied()
        .unwrap_or(0.0);

    let max_drawdown_pct = result
        .stats_returns
        .get("Max Drawdown [%]")
        .or_else(|| result.stats_returns.get("max_drawdown"))
        .copied()
        .unwrap_or(0.0);

    let receipt_id = format!("nautilus-receipt-{}-{}", store.symbol, result.instance_id);
    let receipt = PortfolioReceipt {
        receipt_id,
        initial_balance_usdt: params.initial_balance,
        terminal_equity_usdt: terminal_equity,
        net_profit_usdt: net_profit,
        gross_market_pnl_usdt: gross_pnl,
        total_return_pct,
        max_drawdown_pct,
        max_margin_utilization_pct: 0.0,
        total_fee_drag_usdt: total_fees,
        total_funding_usdt: 0.0,
        n_trades_admitted: n_positions,
        win_rate_pct,
        profit_factor,
        rejections_by_reason: BTreeMap::new(),
        cashflow_ledger_path: String::new(),
        venue_contract_hash: contract.contract_hash(),
        evidence_role: "BURNED_DIAGNOSTIC".to_string(),
        promotion_authority: "NONE".to_string(),
        frontier_receipt: None,
    };

    // Serialize receipt to output directory
    let receipt_path = params.out_dir.join("portfolio_receipt.json");
    if let Ok(bytes) = serde_json::to_vec_pretty(&receipt) {
        let _ = std::fs::write(&receipt_path, bytes);
    }

    Ok(receipt)
}
