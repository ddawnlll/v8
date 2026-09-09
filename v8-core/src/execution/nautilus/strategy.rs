//! Nautilus strategy adapter for V8 experts.
//!
//! Bridges V8 feature stores, causal frames, and expert hypothesis generation
//! with NautilusTrader's event-driven `Strategy` lifecycle.

use crate::experts;
use crate::features;
use crate::state::{self, FeatureStore};
use nautilus_common::actor::DataActor;
use nautilus_model::{
    data::{Bar, BarType},
    enums::OrderSide,
    events::{OrderFilled, PositionClosed, PositionOpened},
    identifiers::{InstrumentId, StrategyId},
    types::Quantity,
};
use nautilus_trading::{
    nautilus_strategy,
    strategy::{Strategy, StrategyConfig, StrategyCore},
};
use rust_decimal::prelude::ToPrimitive;
use rust_decimal::Decimal;
use std::collections::HashMap;
use std::fmt::Debug;
use std::rc::Rc;

/// Strategy state tracking an active trade lifecycle.
#[derive(Debug, Clone)]
pub struct ActiveTrade {
    pub side: OrderSide,
    pub qty: Quantity,
    pub entry_price: f64,
    pub stop_price: f64,
    pub target_price: Option<f64>,
    pub entry_bar: usize,
}

/// Nautilus strategy driven by a V8 expert (e.g. `squeeze_swing`).
pub struct V8ExpertStrategy {
    pub(super) core: StrategyCore,
    pub instrument_id: InstrumentId,
    pub bar_type: BarType,
    pub store: Rc<FeatureStore>,
    pub expert_id: String,
    pub initial_balance: f64,
    pub risk_fraction: f64,
    pub leverage: u32,
    pub max_concurrency: usize,
    pub variant_overrides: HashMap<String, String>,
    pub step_size: f64,
    pub min_qty: f64,
    pub size_precision: u8,
    pub bar_idx: usize,
    pub active_trade: Option<ActiveTrade>,
    pub total_trades_admitted: usize,
}

impl V8ExpertStrategy {
    #[must_use]
    pub fn new(
        instrument_id: InstrumentId,
        bar_type: BarType,
        store: Rc<FeatureStore>,
        expert_id: String,
        initial_balance: f64,
        risk_fraction: f64,
        leverage: u32,
        max_concurrency: usize,
        variant_overrides: HashMap<String, String>,
        step_size: f64,
        min_qty: f64,
        size_precision: u8,
    ) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from(format!(
                "V8-EXPERT-{}",
                expert_id.to_uppercase()
            ))),
            order_id_tag: Some("V8".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            bar_type,
            store,
            expert_id,
            initial_balance,
            risk_fraction,
            leverage,
            max_concurrency,
            variant_overrides,
            step_size,
            min_qty,
            size_precision,
            bar_idx: 0,
            active_trade: None,
            total_trades_admitted: 0,
        }
    }

    /// Discretizes intended quantity to venue lot size step.
    fn discretize_qty(&self, qty: f64) -> f64 {
        if self.step_size <= 0.0 {
            return qty;
        }
        let steps = (qty / self.step_size).floor();
        let rounded = steps * self.step_size;
        let p = self.size_precision as usize;
        let factor = 10f64.powi(p as i32);
        (rounded * factor).round() / factor
    }
}

nautilus_strategy!(V8ExpertStrategy, {
    fn on_order_filled(&mut self, event: &OrderFilled) {
        tracing::info!(
            "V8Strategy fill: {:?} {} @ {} (commission: {:?})",
            event.order_side,
            event.last_qty,
            event.last_px,
            event.commission
        );
    }

    fn on_position_opened(&mut self, event: PositionOpened) {
        tracing::info!("V8Strategy position opened: id={}", event.position_id);
    }

    fn on_position_closed(&mut self, event: PositionClosed) {
        tracing::info!("V8Strategy position closed: id={}", event.position_id);
        self.active_trade = None;
    }
});

impl Debug for V8ExpertStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("V8ExpertStrategy")
            .field("expert_id", &self.expert_id)
            .field("instrument_id", &self.instrument_id)
            .field("bar_idx", &self.bar_idx)
            .field("total_trades_admitted", &self.total_trades_admitted)
            .finish()
    }
}

impl DataActor for V8ExpertStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_bars(self.bar_type, None, None);
        Ok(())
    }

    fn on_bar(&mut self, bar: &Bar) -> anyhow::Result<()> {
        let i = self.bar_idx;
        self.bar_idx += 1;

        let current_close = bar.close.as_f64();
        let current_high = bar.high.as_f64();
        let current_low = bar.low.as_f64();

        // 1. Manage Active Trade Exits (Dynamic Stop / Target / Expiry)
        if let Some(trade) = self.active_trade.clone() {
            let mut should_exit = false;

            if trade.side == OrderSide::Buy {
                // Long: Stop loss hit or Take profit hit
                if current_low <= trade.stop_price {
                    should_exit = true;
                } else if let Some(target) = trade.target_price {
                    if current_high >= target {
                        should_exit = true;
                    }
                }
            } else {
                // Short: Stop loss hit or Take profit hit
                if current_high >= trade.stop_price {
                    should_exit = true;
                } else if let Some(target) = trade.target_price {
                    if current_low <= target {
                        should_exit = true;
                    }
                }
            }

            // Time-based max expiry (336 bars = 14 days for macro swing)
            let max_bars = if self.expert_id.contains("squeeze_swing") {
                336
            } else {
                72
            };
            if i >= trade.entry_bar + max_bars {
                should_exit = true;
            }

            if should_exit {
                let closing_side = if trade.side == OrderSide::Buy {
                    OrderSide::Sell
                } else {
                    OrderSide::Buy
                };
                let exit_order = self.order().market(
                    self.instrument_id,
                    closing_side,
                    trade.qty,
                    None,
                    Some(true), // reduce_only = true
                    None,
                    None,
                    None,
                    None,
                    None,
                );
                self.submit_order(exit_order, None, None, None)?;
                self.active_trade = None;
                return Ok(());
            }
        }

        // 2. Evaluate V8 Expert for New Entry
        let net_pos = self.portfolio().net_position(&self.instrument_id);
        let is_flat = net_pos.is_zero();

        if is_flat && self.active_trade.is_none() && i >= 32 && i < self.store.closes.len() {
            let t = i + 1;
            let as_of = if i < self.store.bar_event_times.len() {
                self.store.bar_event_times[i]
            } else {
                (i as i64 + 1) * 3_600_000_000_000
            };

            let feats = state::state_features(&self.store, t, as_of, 32);
            let hist = state::history_bars(&self.store, t, 128);
            let ev = if self.expert_id.contains("squeeze_swing") {
                let ss_closure =
                    features::group_closure(&["trend", "volatility", "participation", "history"]);
                let fm_ss = experts::base::FeatMap {
                    features: experts::base::ProjectedFeatures::new(&feats, &ss_closure),
                    history: &hist,
                    as_of,
                    symbol: &self.store.symbol,
                    variant_overrides: &self.variant_overrides,
                };
                crate::experts::squeeze_swing::squeeze_swing(&fm_ss, "squeeze_swing", "v1")
            } else {
                let closure = features::group_closure(experts::requires_for(&self.expert_id));
                let allows_hist = features::history_allowed(&closure);
                let expert_hist = if allows_hist { hist.as_slice() } else { &[] };

                let fm = experts::base::FeatMap {
                    features: experts::base::ProjectedFeatures::new(&feats, &closure),
                    history: expert_hist,
                    as_of,
                    symbol: &self.store.symbol,
                    variant_overrides: &self.variant_overrides,
                };
                experts::evaluate(&self.expert_id, &fm)
            };

            if ev.decision == "CANDIDATE" {
                if let Some(draft) = ev.draft {
                    let side = if draft.direction == "LONG" {
                        OrderSide::Buy
                    } else {
                        OrderSide::Sell
                    };

                    let atr = feats
                        .iter()
                        .find(|f| f.name == "atr")
                        .and_then(|f| f.value.as_f64())
                        .unwrap_or(current_close * 0.01);
                    let stop_r = draft.geom_f64("stop_r").unwrap_or(2.0);
                    let target_r = draft.geom_f64("target_r").unwrap_or(4.0);
                    let stop_dist = stop_r * atr;
                    let target_dist = target_r * atr;

                    let stop_price = if side == OrderSide::Buy {
                        current_close - stop_dist
                    } else {
                        current_close + stop_dist
                    };
                    let target_price = if side == OrderSide::Buy {
                        Some(current_close + target_dist)
                    } else {
                        Some(current_close - target_dist)
                    };

                    // Position Sizing: Notional = Capital * RiskFraction * Leverage
                    let notional =
                        (self.initial_balance * self.risk_fraction * (self.leverage as f64))
                            .max(50.0);
                    let raw_qty = notional / current_close;
                    let executable_qty = self.discretize_qty(raw_qty);

                    if executable_qty >= self.min_qty {
                        let qty = Quantity::new(executable_qty, self.size_precision);
                        let order = self.order().market(
                            self.instrument_id,
                            side,
                            qty,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                        );

                        self.submit_order(order, None, None, None)?;
                        self.total_trades_admitted += 1;
                        self.active_trade = Some(ActiveTrade {
                            side,
                            qty,
                            entry_price: current_close,
                            stop_price,
                            target_price,
                            entry_bar: i,
                        });
                    }
                }
            }
        }

        Ok(())
    }
}
