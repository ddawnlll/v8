//! Tail-Preserving Dynamic Trailing Exit Challenger (Issue #214 / EXIT-001).
//! Normative Traceability: D-047, D-123, CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md, VENUE_AND_CAPITAL_SIMULATION_SPEC §9.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExitArm {
    Static1R,
    Static2R,
    Static3R,
    NoTP,
    ChandelierATR,
    EMA4hTrail,
    HybridTrail,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrailingState {
    pub arm: ExitArm,
    pub entry_price: f64,
    pub initial_stop: f64,
    pub current_stop: f64,
    pub direction: String, // "LONG" or "SHORT"
    pub highest_high: f64,
    pub lowest_low: f64,
    pub chandelier_multiplier: f64, // e.g. 3.0 ATR
    pub initial_risk_dist: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExitResult {
    pub exit_bar: usize,
    pub exit_price: f64,
    pub realized_r: f64,
    pub max_favorable_r: f64,
    pub max_adverse_r: f64,
    pub tail_capture_efficiency: f64, // Realized / MFE (clamped [0, 1])
    pub exit_reason: String,
}

pub struct DynamicTrailingEngine;

impl DynamicTrailingEngine {
    pub fn new_state(
        arm: ExitArm,
        direction: &str,
        entry_price: f64,
        initial_stop: f64,
        chandelier_multiplier: f64,
    ) -> TrailingState {
        let initial_risk_dist = (entry_price - initial_stop).abs().max(1e-6);
        TrailingState {
            arm,
            entry_price,
            initial_stop,
            current_stop: initial_stop,
            direction: direction.to_string(),
            highest_high: entry_price,
            lowest_low: entry_price,
            chandelier_multiplier,
            initial_risk_dist,
        }
    }

    /// Step trailing stop update on closed bar and check if exit triggered.
    /// Check is evaluated against working stop level from bar open, then stop is advanced on bar close.
    pub fn step_bar(
        state: &mut TrailingState,
        bar_index: usize,
        high: f64,
        low: f64,
        _close: f64,
        atr: f64,
        ema_trail: Option<f64>,
    ) -> Option<ExitResult> {
        let is_long = state.direction == "LONG";
        state.highest_high = state.highest_high.max(high);
        state.lowest_low = state.lowest_low.min(low);

        let mfe_r = if is_long {
            (state.highest_high - state.entry_price) / state.initial_risk_dist
        } else {
            (state.entry_price - state.lowest_low) / state.initial_risk_dist
        };

        let mae_r = if is_long {
            (state.entry_price - state.lowest_low) / state.initial_risk_dist
        } else {
            (state.highest_high - state.entry_price) / state.initial_risk_dist
        };

        // 1. Check static target arms
        match state.arm {
            ExitArm::Static1R if mfe_r >= 1.0 => {
                let exit_price = if is_long {
                    state.entry_price + state.initial_risk_dist
                } else {
                    state.entry_price - state.initial_risk_dist
                };
                return Some(ExitResult {
                    exit_bar: bar_index,
                    exit_price,
                    realized_r: 1.0,
                    max_favorable_r: mfe_r,
                    max_adverse_r: mae_r,
                    tail_capture_efficiency: (1.0 / mfe_r.max(1.0)).clamp(0.0, 1.0),
                    exit_reason: "STATIC_1R_TARGET".to_string(),
                });
            }
            ExitArm::Static2R if mfe_r >= 2.0 => {
                let exit_price = if is_long {
                    state.entry_price + 2.0 * state.initial_risk_dist
                } else {
                    state.entry_price - 2.0 * state.initial_risk_dist
                };
                return Some(ExitResult {
                    exit_bar: bar_index,
                    exit_price,
                    realized_r: 2.0,
                    max_favorable_r: mfe_r,
                    max_adverse_r: mae_r,
                    tail_capture_efficiency: (2.0 / mfe_r.max(2.0)).clamp(0.0, 1.0),
                    exit_reason: "STATIC_2R_TARGET".to_string(),
                });
            }
            ExitArm::Static3R if mfe_r >= 3.0 => {
                let exit_price = if is_long {
                    state.entry_price + 3.0 * state.initial_risk_dist
                } else {
                    state.entry_price - 3.0 * state.initial_risk_dist
                };
                return Some(ExitResult {
                    exit_bar: bar_index,
                    exit_price,
                    realized_r: 3.0,
                    max_favorable_r: mfe_r,
                    max_adverse_r: mae_r,
                    tail_capture_efficiency: (3.0 / mfe_r.max(3.0)).clamp(0.0, 1.0),
                    exit_reason: "STATIC_3R_TARGET".to_string(),
                });
            }
            _ => {}
        }

        // 2. Check if current working stop is hit during bar
        let stop_hit = if is_long {
            low <= state.current_stop
        } else {
            high >= state.current_stop
        };

        if stop_hit {
            let realized = if is_long {
                (state.current_stop - state.entry_price) / state.initial_risk_dist
            } else {
                (state.entry_price - state.current_stop) / state.initial_risk_dist
            };
            let tce = if mfe_r > 0.0 {
                (realized / mfe_r).clamp(0.0, 1.0)
            } else {
                0.0
            };
            return Some(ExitResult {
                exit_bar: bar_index,
                exit_price: state.current_stop,
                realized_r: realized,
                max_favorable_r: mfe_r,
                max_adverse_r: mae_r,
                tail_capture_efficiency: tce,
                exit_reason: "TRAILING_STOP_HIT".to_string(),
            });
        }

        // 3. If stop not hit, update Dynamic Trailing Stop on bar close for next bar
        match state.arm {
            ExitArm::ChandelierATR => {
                if is_long {
                    let chandelier = state.highest_high - (state.chandelier_multiplier * atr);
                    if chandelier > state.current_stop {
                        state.current_stop = chandelier;
                    }
                } else {
                    let chandelier = state.lowest_low + (state.chandelier_multiplier * atr);
                    if chandelier < state.current_stop || state.current_stop <= 0.0 {
                        state.current_stop = chandelier;
                    }
                }
            }
            ExitArm::EMA4hTrail => {
                if let Some(ema) = ema_trail {
                    let update = if is_long {
                        ema > state.current_stop
                    } else {
                        ema < state.current_stop || state.current_stop <= 0.0
                    };
                    if update {
                        state.current_stop = ema;
                    }
                }
            }
            ExitArm::HybridTrail => {
                if is_long {
                    if mfe_r >= 1.5 && state.current_stop < state.entry_price {
                        state.current_stop = state.entry_price;
                    }
                    let chandelier = state.highest_high - (2.5 * atr);
                    if chandelier > state.current_stop {
                        state.current_stop = chandelier;
                    }
                } else {
                    if mfe_r >= 1.5 && state.current_stop > state.entry_price {
                        state.current_stop = state.entry_price;
                    }
                    let chandelier = state.lowest_low + (2.5 * atr);
                    if (chandelier < state.current_stop || state.current_stop <= 0.0) && chandelier > 0.0 {
                        state.current_stop = chandelier;
                    }
                }
            }
            _ => {}
        }

        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chandelier_trailing_rides_fat_tail() {
        let mut state = DynamicTrailingEngine::new_state(
            ExitArm::ChandelierATR,
            "SHORT",
            73000.0,
            74000.0,
            2.0,
        );

        let bars = [
            (73000.0, 71000.0, 71200.0, 500.0), // Bar 0: price drops, stop updated to 72000
            (71500.0, 68000.0, 68200.0, 500.0), // Bar 1: high 71500 < 72000, stop updated to 69000
            (68500.0, 63000.0, 63200.0, 500.0), // Bar 2: high 68500 < 69000, stop updated to 64000
            (65000.0, 62800.0, 64500.0, 500.0), // Bar 3: high 65000 >= 64000 -> trailing stop triggered!
        ];

        let mut exit = None;
        for (i, &(h, l, c, atr)) in bars.iter().enumerate() {
            if let Some(res) = DynamicTrailingEngine::step_bar(&mut state, i, h, l, c, atr, None) {
                exit = Some(res);
                break;
            }
        }

        assert!(exit.is_some());
        let res = exit.unwrap();
        assert_eq!(res.exit_price, 64000.0);
        assert_eq!(res.realized_r, 9.0); // 73000 - 64000 = 9000 / 1000 = 9.0R
        assert!(res.tail_capture_efficiency >= 0.85);
    }
}
