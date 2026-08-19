//! V8 Evaluation Evidence System — Path Forensics & Trajectory Classification (v8.eval.v1 §10).
//!
//! Forensics for trade excursion paths (MFE/MAE, markouts, barrier sequences)
//! and automated path classification into 6 diagnostic failure/opportunity taxons.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PathClassification {
    StopTooTight,
    TargetTooTight,
    DeadTrade,
    BadEntry,
    GoodSignalBadExecution,
    BadSignalLuckyExit,
    NormalExecution,
}

impl PathClassification {
    pub fn as_str(&self) -> &'static str {
        match self {
            PathClassification::StopTooTight => "STOP_TOO_TIGHT",
            PathClassification::TargetTooTight => "TARGET_TOO_TIGHT",
            PathClassification::DeadTrade => "DEAD_TRADE",
            PathClassification::BadEntry => "BAD_ENTRY",
            PathClassification::GoodSignalBadExecution => "GOOD_SIGNAL_BAD_EXECUTION",
            PathClassification::BadSignalLuckyExit => "BAD_SIGNAL_LUCKY_EXIT",
            PathClassification::NormalExecution => "NORMAL_EXECUTION",
        }
    }
}

pub fn classify_trade_path(
    exit_reason: &str,
    realized_net_r: f64,
    gross_r: f64,
    mfe_r: f64,
    mae_r: f64,
    time_to_mae: usize,
    duration_bars: usize,
    expiry_bars: usize,
    post_exit_mfe_r: f64,
    markout_24_r: f64,
) -> PathClassification {
    let reason_upper = exit_reason.to_uppercase();

    // 1. Stop too tight
    if reason_upper.contains("STOP") && post_exit_mfe_r >= 1.0 {
        return PathClassification::StopTooTight;
    }

    // 2. Target too tight
    if reason_upper.contains("TARGET") && post_exit_mfe_r >= 2.0 {
        return PathClassification::TargetTooTight;
    }

    // 3. Bad entry
    if time_to_mae <= 1 && mae_r >= 0.5 && mfe_r < 0.05 {
        return PathClassification::BadEntry;
    }

    // 4. Dead trade
    let min_dur = ((expiry_bars.max(1) as f64) * 0.8) as usize;
    if duration_bars >= min_dur && mfe_r.abs() < 0.2 && mae_r.abs() < 0.2 {
        return PathClassification::DeadTrade;
    }

    // 5. Good signal bad execution
    if markout_24_r >= 0.8 && realized_net_r <= 0.0 && gross_r >= realized_net_r {
        return PathClassification::GoodSignalBadExecution;
    }

    // 6. Bad signal lucky exit
    if mae_r >= 0.8 && realized_net_r > 0.0 && mfe_r <= 0.3 {
        return PathClassification::BadSignalLuckyExit;
    }

    PathClassification::NormalExecution
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Markouts {
    pub t_plus_1_r: f64,
    pub t_plus_2_r: f64,
    pub t_plus_3_r: f64,
    pub t_plus_6_r: f64,
    pub t_plus_12_r: f64,
    pub t_plus_24_r: f64,
}

pub fn compute_markouts(
    entry_price: f64,
    is_long: bool,
    future_closes: &[f64],
    unit_risk_p: f64,
) -> Markouts {
    let risk = if unit_risk_p <= 0.0 { entry_price * 0.01 } else { unit_risk_p };
    let sign = if is_long { 1.0 } else { -1.0 };

    let get_r = |delta: usize| -> f64 {
        if future_closes.len() >= delta {
            let p = future_closes[delta - 1];
            sign * (p - entry_price) / risk
        } else if !future_closes.is_empty() {
            let p = *future_closes.last().unwrap();
            sign * (p - entry_price) / risk
        } else {
            0.0
        }
    };

    Markouts {
        t_plus_1_r: get_r(1),
        t_plus_2_r: get_r(2),
        t_plus_3_r: get_r(3),
        t_plus_6_r: get_r(6),
        t_plus_12_r: get_r(12),
        t_plus_24_r: get_r(24),
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct IntrabarAmbiguity {
    pub same_bar_sl_tp_touch: bool,
    pub optimistic_net_r: f64,
    pub pessimistic_net_r: f64,
    pub ambiguity_spread_r: f64,
}

pub fn compute_intrabar_ambiguity(
    high: f64,
    low: f64,
    stop_price: f64,
    target_price: f64,
    is_long: bool,
    nominal_net_r: f64,
) -> IntrabarAmbiguity {
    let (hit_sl, hit_tp) = if is_long {
        (low <= stop_price, high >= target_price)
    } else {
        (high >= stop_price, low <= target_price)
    };

    let same_bar = hit_sl && hit_tp;
    let opt = if same_bar { 1.0 } else { nominal_net_r };
    let pess = if same_bar { -1.0 } else { nominal_net_r };
    let spread = if same_bar { (opt - pess).abs() } else { 0.0 };

    IntrabarAmbiguity {
        same_bar_sl_tp_touch: same_bar,
        optimistic_net_r: opt,
        pessimistic_net_r: pess,
        ambiguity_spread_r: spread,
    }
}
