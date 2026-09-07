//! Campaign Pyramiding, Midpoint Stops & Position Additions (Issue #220 / SCALE-001).
//! Normative Traceability: D-047, D-123, CANDIDATE_LIFECYCLE_SPEC §4, SIMULATION_TRUTH_SPEC §3.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionLayer {
    pub layer_id: usize,
    pub entry_bar: usize,
    pub entry_price: f64,
    pub quantity: f64,
    pub layer_risk_dist: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PyramidingCampaign {
    pub campaign_id: String,
    pub symbol: String,
    pub direction: String, // "LONG" or "SHORT"
    pub layers: Vec<PositionLayer>,
    pub current_stop_price: f64,
    pub initial_stop_price: f64,
    pub max_layers: usize,
    pub add_threshold_r: f64, // e.g. 1.0R
    pub total_executed_qty: f64,
    pub total_open_risk_usdt: f64,
    pub initial_unit_risk_usdt: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PyramidingDecision {
    pub can_add: bool,
    pub recommended_add_qty: f64,
    pub new_stop_price: f64,
    pub projected_total_risk_usdt: f64,
    pub rejection_reason: Option<String>,
}

pub struct PyramidingEngine;

impl PyramidingEngine {
    pub fn new_campaign(
        campaign_id: &str,
        symbol: &str,
        direction: &str,
        entry_bar: usize,
        entry_price: f64,
        stop_price: f64,
        quantity: f64,
        unit_risk_usdt: f64,
        add_threshold_r: f64,
        max_layers: usize,
    ) -> PyramidingCampaign {
        let risk_dist = (entry_price - stop_price).abs();
        let initial_layer = PositionLayer {
            layer_id: 0,
            entry_bar,
            entry_price,
            quantity,
            layer_risk_dist: risk_dist,
        };

        PyramidingCampaign {
            campaign_id: campaign_id.to_string(),
            symbol: symbol.to_string(),
            direction: direction.to_string(),
            layers: vec![initial_layer],
            current_stop_price: stop_price,
            initial_stop_price: stop_price,
            max_layers,
            add_threshold_r,
            total_executed_qty: quantity,
            total_open_risk_usdt: unit_risk_usdt,
            initial_unit_risk_usdt: unit_risk_usdt,
        }
    }

    /// Evaluate if an addition can be made at current bar price without increasing overall campaign risk.
    pub fn evaluate_addition(
        campaign: &PyramidingCampaign,
        _current_bar: usize,
        current_price: f64,
        step_size: f64,
    ) -> PyramidingDecision {
        if campaign.layers.len() >= campaign.max_layers {
            return PyramidingDecision {
                can_add: false,
                recommended_add_qty: 0.0,
                new_stop_price: campaign.current_stop_price,
                projected_total_risk_usdt: campaign.total_open_risk_usdt,
                rejection_reason: Some("MAX_LAYERS_REACHED".to_string()),
            };
        }

        let is_long = campaign.direction == "LONG";
        let initial_entry = campaign.layers[0].entry_price;
        let initial_dist = campaign.layers[0].layer_risk_dist;

        let mfe_r = if is_long {
            (current_price - initial_entry) / initial_dist
        } else {
            (initial_entry - current_price) / initial_dist
        };

        // Anti-martingale invariant
        if mfe_r < campaign.add_threshold_r {
            return PyramidingDecision {
                can_add: false,
                recommended_add_qty: 0.0,
                new_stop_price: campaign.current_stop_price,
                projected_total_risk_usdt: campaign.total_open_risk_usdt,
                rejection_reason: Some(format!("EXCURSION_BELOW_THRESHOLD: {:.2}R < {:.2}R", mfe_r, campaign.add_threshold_r)),
            };
        }

        let midpoint_stop = if is_long {
            initial_entry + (0.5 * (current_price - initial_entry))
        } else {
            initial_entry - (0.5 * (initial_entry - current_price))
        };

        let new_stop = if is_long {
            midpoint_stop.max(initial_entry)
        } else {
            midpoint_stop.min(initial_entry)
        };

        let mut locked_profit_usdt = 0.0;
        for l in &campaign.layers {
            if is_long {
                locked_profit_usdt += l.quantity * (new_stop - l.entry_price);
            } else {
                locked_profit_usdt += l.quantity * (l.entry_price - new_stop);
            }
        }

        let new_layer_dist = (current_price - new_stop).abs();
        if new_layer_dist <= 0.0 {
            return PyramidingDecision {
                can_add: false,
                recommended_add_qty: 0.0,
                new_stop_price: campaign.current_stop_price,
                projected_total_risk_usdt: campaign.total_open_risk_usdt,
                rejection_reason: Some("INVALID_NEW_STOP_DISTANCE".to_string()),
            };
        }

        let allowable_new_layer_risk = campaign.initial_unit_risk_usdt + locked_profit_usdt;
        let raw_add_qty = (allowable_new_layer_risk / new_layer_dist).min(campaign.layers[0].quantity * 0.75);
        let add_qty = (raw_add_qty / step_size).floor() * step_size;

        if add_qty < step_size {
            return PyramidingDecision {
                can_add: false,
                recommended_add_qty: 0.0,
                new_stop_price: campaign.current_stop_price,
                projected_total_risk_usdt: campaign.total_open_risk_usdt,
                rejection_reason: Some("QUANTIZATION_BELOW_MIN_STEP".to_string()),
            };
        }

        let new_layer_risk = add_qty * new_layer_dist;
        let projected_total_risk = new_layer_risk - locked_profit_usdt;

        PyramidingDecision {
            can_add: true,
            recommended_add_qty: add_qty,
            new_stop_price: new_stop,
            projected_total_risk_usdt: projected_total_risk.max(0.0),
            rejection_reason: None,
        }
    }

    pub fn commit_addition(
        campaign: &mut PyramidingCampaign,
        current_bar: usize,
        current_price: f64,
        decision: &PyramidingDecision,
    ) {
        if !decision.can_add || decision.recommended_add_qty <= 0.0 {
            return;
        }

        let new_layer = PositionLayer {
            layer_id: campaign.layers.len(),
            entry_bar: current_bar,
            entry_price: current_price,
            quantity: decision.recommended_add_qty,
            layer_risk_dist: (current_price - decision.new_stop_price).abs(),
        };

        campaign.layers.push(new_layer);
        campaign.current_stop_price = decision.new_stop_price;
        campaign.total_executed_qty += decision.recommended_add_qty;
        campaign.total_open_risk_usdt = decision.projected_total_risk_usdt;
    }
}
