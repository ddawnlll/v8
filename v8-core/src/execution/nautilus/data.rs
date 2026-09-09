//! Nautilus data and instrument translation bridge.
//!
//! Transforms V8 FeatureStore series and venue specifications into native
//! Nautilus domain objects (`CryptoPerpetual`, `Bar`, `FundingRateUpdate`).

use crate::state::FeatureStore;
use crate::venue::VenueContract;
use nautilus_core::UnixNanos;
use nautilus_model::{
    data::{Bar, BarSpecification, BarType, Data, FundingRateUpdate, HasTsInit},
    enums::{AggregationSource, BarAggregation, PriceType},
    identifiers::{InstrumentId, Symbol, Venue},
    instruments::CryptoPerpetual,
    types::{Currency, Money, Price, Quantity},
};
use rust_decimal::Decimal;

/// Derives precision (number of decimal places) from a step or tick value.
pub fn precision_from_step(step: f64) -> u8 {
    if step >= 1.0 {
        0
    } else {
        let s = format!("{:.8}", step);
        let s = s.trim_end_matches('0');
        s.split('.').nth(1).map(|d| d.len() as u8).unwrap_or(0)
    }
}

/// Creates a native Nautilus `CryptoPerpetual` instrument for Binance USDⓈ-M.
pub fn create_binance_perpetual_instrument(
    symbol: &str,
    venue_str: &str,
    leverage: u32,
) -> Result<CryptoPerpetual, String> {
    let contract = VenueContract::for_symbol(symbol);
    let venue = Venue::from(venue_str);
    let raw_symbol = Symbol::from(symbol);
    let instrument_id = InstrumentId::new(Symbol::from(format!("{symbol}-PERP")), venue);

    let price_precision = precision_from_step(contract.price_filter.tick_size);
    let size_precision = precision_from_step(contract.lot_size_filter.step_size);

    let base_ccy_str = if symbol.ends_with("USDT") {
        symbol.trim_end_matches("USDT")
    } else if symbol.ends_with("USDC") {
        symbol.trim_end_matches("USDC")
    } else {
        "BTC"
    };

    let base_currency = Currency::from(base_ccy_str);
    let quote_currency = Currency::from("USDT");
    let settlement_currency = Currency::from("USDT");

    let price_increment = Price::new(contract.price_filter.tick_size, price_precision);
    let size_increment = Quantity::new(contract.lot_size_filter.step_size, size_precision);

    let max_qty = Quantity::new(contract.lot_size_filter.max_qty, size_precision);
    let min_qty = Quantity::new(contract.lot_size_filter.min_qty, size_precision);

    let min_notional = Money::new(contract.min_notional, quote_currency);
    let max_price = Price::new(contract.price_filter.max_price, price_precision);
    let min_price = Price::new(contract.price_filter.min_price, price_precision);

    let init_margin_f64 = if leverage > 0 {
        1.0 / (leverage as f64)
    } else {
        1.0
    };
    let margin_init = Decimal::from_f64_retain(init_margin_f64)
        .ok_or_else(|| "invalid margin_init decimal".to_string())?;

    let maint_rate = contract
        .leverage_brackets
        .first()
        .map(|b| b.maint_margin_rate)
        .unwrap_or(0.005);
    let margin_maint = Decimal::from_f64_retain(maint_rate)
        .ok_or_else(|| "invalid margin_maint decimal".to_string())?;

    let maker_fee = Decimal::from_f64_retain(contract.fee_schedule.maker_rate)
        .ok_or_else(|| "invalid maker_fee decimal".to_string())?;
    let taker_fee = Decimal::from_f64_retain(contract.fee_schedule.taker_rate)
        .ok_or_else(|| "invalid taker_fee decimal".to_string())?;

    CryptoPerpetual::builder()
        .instrument_id(instrument_id)
        .raw_symbol(raw_symbol)
        .base_currency(base_currency)
        .quote_currency(quote_currency)
        .settlement_currency(settlement_currency)
        .is_inverse(false)
        .price_precision(price_precision)
        .size_precision(size_precision)
        .price_increment(price_increment)
        .size_increment(size_increment)
        .multiplier(Quantity::from("1"))
        .lot_size(Quantity::from("1"))
        .max_quantity(max_qty)
        .min_quantity(min_qty)
        .min_notional(min_notional)
        .max_price(max_price)
        .min_price(min_price)
        .margin_init(margin_init)
        .margin_maint(margin_maint)
        .maker_fee(maker_fee)
        .taker_fee(taker_fee)
        .ts_event(UnixNanos::default())
        .ts_init(UnixNanos::default())
        .build()
        .map_err(|e| format!("Failed to build CryptoPerpetual instrument: {e}"))
}

/// Converts a V8 `FeatureStore` into a sorted chronological stream of Nautilus `Data` events.
pub fn convert_feature_store_to_nautilus_data(
    store: &FeatureStore,
    instrument_id: InstrumentId,
    price_precision: u8,
    size_precision: u8,
) -> Result<Vec<Data>, String> {
    let spec = BarSpecification::new_checked(1, BarAggregation::Hour, PriceType::Last)
        .map_err(|e| format!("Invalid BarSpecification: {e}"))?;
    let bar_type = BarType::new(instrument_id, spec, AggregationSource::External);

    let n_bars = store.closes.len();
    let mut data: Vec<Data> = Vec::with_capacity(n_bars + store.funding_rate.len());

    // 1. Convert historical price bars
    for i in 0..n_bars {
        let open_val = store.opens[i];
        let mut high_val = store.highs[i];
        let mut low_val = store.lows[i];
        let close_val = store.closes[i];
        let vol_val = store.volumes.get(i).copied().unwrap_or(0.0).max(0.0);

        // Guarantee high >= max(open, close) and low <= min(open, close) against float precision edge cases
        high_val = high_val.max(open_val).max(close_val);
        low_val = low_val.min(open_val).min(close_val);

        let open = Price::new(open_val, price_precision);
        let high = Price::new(high_val, price_precision);
        let low = Price::new(low_val, price_precision);
        let close = Price::new(close_val, price_precision);
        let volume = Quantity::new(vol_val, size_precision);

        let event_time = if i < store.bar_event_times.len() && store.bar_event_times[i] > 0 {
            store.bar_event_times[i] as u64
        } else {
            (i as u64 + 1) * 3_600_000_000_000 // 1 hour in ns
        };
        let ts = UnixNanos::from(event_time);

        let bar = Bar::new_checked(bar_type, open, high, low, close, volume, ts, ts)
            .map_err(|e| format!("Bar validation failed at index {i}: {e}"))?;
        data.push(Data::Bar(bar));
    }

    // 2. Convert funding settlement events
    for (f_idx, &rate) in store.funding_rate.iter().enumerate() {
        let settlement_time = store.funding_event_times.get(f_idx).copied().unwrap_or(0) as u64;
        if settlement_time > 0 {
            let ts_settle = UnixNanos::from(settlement_time);
            // Next funding boundary (e.g. next 8-hour period)
            let next_funding = store
                .funding_event_times
                .get(f_idx + 1)
                .copied()
                .filter(|&t| t > settlement_time as i64)
                .map(|t| UnixNanos::from(t as u64))
                .or_else(|| Some(UnixNanos::from(settlement_time + 8 * 3_600_000_000_000)));

            if let Some(rate_dec) = Decimal::from_f64_retain(rate) {
                let funding_update = FundingRateUpdate::new(
                    instrument_id,
                    rate_dec,
                    Some(480), // 8 hours = 480 minutes
                    next_funding,
                    ts_settle,
                    ts_settle,
                );
                data.push(Data::FundingRate(funding_update));
            }
        }
    }

    // Sort chronologically by initialization timestamp
    data.sort_by_key(|d| d.ts_init());

    Ok(data)
}
