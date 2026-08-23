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
    ChandelierATRWithBE05R,  // Challenger A1: +0.5R BE trigger
    ChandelierATRWithBE075R, // Challenger A2: +0.75R BE trigger
    ChandelierATRWithBE10R,  // Challenger A3: +1.0R BE trigger
    Structural24hTrail,      // D-140 Macro Swing 24h Structural Low/High Trail
    Structural48hTrail,      // H-MACRO-01 Ultra Swing 48h Structural Low/High Trail
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
            ExitArm::ChandelierATRWithBE05R => {
                let be_trigger = 0.5;
                let fee_offset_r = 0.07;
                if is_long {
                    if mfe_r >= be_trigger {
                        let be_level = state.entry_price + (fee_offset_r * state.initial_risk_dist);
                        if be_level > state.current_stop {
                            state.current_stop = be_level;
                        }
                    }
                    let chandelier = state.highest_high - (state.chandelier_multiplier * atr);
                    if chandelier > state.current_stop {
                        state.current_stop = chandelier;
                    }
                } else {
                    if mfe_r >= be_trigger {
                        let be_level = state.entry_price - (fee_offset_r * state.initial_risk_dist);
                        if be_level < state.current_stop || state.current_stop <= 0.0 {
                            state.current_stop = be_level;
                        }
                    }
                    let chandelier = state.lowest_low + (state.chandelier_multiplier * atr);
                    if (chandelier < state.current_stop || state.current_stop <= 0.0) && chandelier > 0.0 {
                        state.current_stop = chandelier;
                    }
                }
            }
            ExitArm::ChandelierATRWithBE075R => {
                let be_trigger = 0.75;
                let fee_offset_r = 0.07;
                if is_long {
                    if mfe_r >= be_trigger {
                        let be_level = state.entry_price + (fee_offset_r * state.initial_risk_dist);
                        if be_level > state.current_stop {
                            state.current_stop = be_level;
                        }
                    }
                    let chandelier = state.highest_high - (state.chandelier_multiplier * atr);
                    if chandelier > state.current_stop {
                        state.current_stop = chandelier;
                    }
                } else {
                    if mfe_r >= be_trigger {
                        let be_level = state.entry_price - (fee_offset_r * state.initial_risk_dist);
                        if be_level < state.current_stop || state.current_stop <= 0.0 {
                            state.current_stop = be_level;
                        }
                    }
                    let chandelier = state.lowest_low + (state.chandelier_multiplier * atr);
                    if (chandelier < state.current_stop || state.current_stop <= 0.0) && chandelier > 0.0 {
                        state.current_stop = chandelier;
                    }
                }
            }
            ExitArm::ChandelierATRWithBE10R => {
                let be_trigger = 1.0;
                let fee_offset_r = 0.07;
                if is_long {
                    if mfe_r >= be_trigger {
                        let be_level = state.entry_price + (fee_offset_r * state.initial_risk_dist);
                        if be_level > state.current_stop {
                            state.current_stop = be_level;
                        }
                    }
                    let chandelier = state.highest_high - (state.chandelier_multiplier * atr);
                    if chandelier > state.current_stop {
                        state.current_stop = chandelier;
                    }
                } else {
                    if mfe_r >= be_trigger {
                        let be_level = state.entry_price - (fee_offset_r * state.initial_risk_dist);
                        if be_level < state.current_stop || state.current_stop <= 0.0 {
                            state.current_stop = be_level;
                        }
                    }
                    let chandelier = state.lowest_low + (state.chandelier_multiplier * atr);
                    if (chandelier < state.current_stop || state.current_stop <= 0.0) && chandelier > 0.0 {
                        state.current_stop = chandelier;
                    }
                }
            }
            ExitArm::Structural24hTrail | ExitArm::Structural48hTrail => {
                if let Some(struct_stop) = ema_trail {
                    if is_long {
                        if struct_stop > state.current_stop {
                            state.current_stop = struct_stop;
                        }
                    } else {
                        if (struct_stop < state.current_stop || state.current_stop <= 0.0) && struct_stop > 0.0 {
                            state.current_stop = struct_stop;
                        }
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

    #[test]
    fn test_breakeven_challenger_saves_loss_on_failed_continuation() {
        // Scenario 1: Long entry at 100, Stop at 90 (risk dist = 10).
        // Bar 0: High 106, Low 99, Close 105, ATR 8.0 (MFE = +0.6R >= 0.5R trigger).
        // A0 Chandelier = 106 - (2.5 * 8.0) = 86.0 < 90.0 (stop stays 90.0).
        // A1 BE05R moves stop to 100.0 + 0.7 = 100.7.
        // Bar 1: Low 95.0. A1 exits at 100.7 (+0.07R). A0 stays in position.
        // Bar 2: Low 88.0. A0 exits at 90.0 (-1.0R).

        let bars = [
            (106.0, 99.0, 105.0, 8.0), // Bar 0: MFE = +0.6R
            (104.0, 95.0, 96.0, 8.0),  // Bar 1: pulls back below entry
            (95.0, 88.0, 89.0, 8.0),   // Bar 2: crashes
        ];

        // Run A0
        let mut state_a0 = DynamicTrailingEngine::new_state(ExitArm::ChandelierATR, "LONG", 100.0, 90.0, 2.5);
        let mut exit_a0 = None;
        for (i, &(h, l, c, atr)) in bars.iter().enumerate() {
            if let Some(res) = DynamicTrailingEngine::step_bar(&mut state_a0, i, h, l, c, atr, None) {
                exit_a0 = Some(res);
                break;
            }
        }

        // Run A1
        let mut state_a1 = DynamicTrailingEngine::new_state(ExitArm::ChandelierATRWithBE05R, "LONG", 100.0, 90.0, 2.5);
        let mut exit_a1 = None;
        for (i, &(h, l, c, atr)) in bars.iter().enumerate() {
            if let Some(res) = DynamicTrailingEngine::step_bar(&mut state_a1, i, h, l, c, atr, None) {
                exit_a1 = Some(res);
                break;
            }
        }

        assert!(exit_a0.is_some());
        assert!(exit_a1.is_some());

        let res_a0 = exit_a0.unwrap();
        let res_a1 = exit_a1.unwrap();

        // A0 exits at bar 2 at initial stop 90.0 (-1.0R)
        assert_eq!(res_a0.exit_bar, 2);
        assert_eq!(res_a0.exit_price, 90.0);
        assert_eq!(res_a0.realized_r, -1.0);

        // A1 exits at bar 1 at BE stop 100.7 (+0.07R)
        assert_eq!(res_a1.exit_bar, 1);
        assert_eq!(res_a1.exit_price, 100.7);
        assert!((res_a1.realized_r - 0.07).abs() < 1e-6);
    }

    #[test]
    fn test_breakeven_challenger_premature_kill_tradeoff() {
        // Scenario 2: Long entry at 100, Stop at 90 (risk dist = 10).
        // Bar 0: High 106, Low 99, Close 105, ATR 3.0 (MFE = +0.6R >= 0.5R trigger).
        // A0 Chandelier = 106 - (2.5 * 3.0) = 98.5 (stop moves to 98.5).
        // A1 BE05R moves stop to 100.7.
        // Bar 1: High 104, Low 100.0, Close 103. A1 stopped out at 100.7 (+0.07R). A0 stays in position (low 100.0 > 98.5).
        // Bar 2: Mega breakout to High 150 (Chandelier moves to 150 - 7.5 = 142.5).
        // Bar 3: High 145, Low 140, Close 141. A0 exits at 142.5 (+4.25R).

        let bars = [
            (106.0, 99.0, 105.0, 3.0),  // Bar 0: MFE = +0.6R
            (104.0, 100.0, 103.0, 3.0), // Bar 1: minor retrace (hits A1 stop 100.7, stays above A0 stop 98.5)
            (150.0, 103.0, 148.0, 3.0), // Bar 2: mega move to 150
            (145.0, 140.0, 141.0, 3.0), // Bar 3: trailing exit
        ];

        // Run A0
        let mut state_a0 = DynamicTrailingEngine::new_state(ExitArm::ChandelierATR, "LONG", 100.0, 90.0, 2.5);
        let mut exit_a0 = None;
        for (i, &(h, l, c, atr)) in bars.iter().enumerate() {
            if let Some(res) = DynamicTrailingEngine::step_bar(&mut state_a0, i, h, l, c, atr, None) {
                exit_a0 = Some(res);
                break;
            }
        }

        // Run A1
        let mut state_a1 = DynamicTrailingEngine::new_state(ExitArm::ChandelierATRWithBE05R, "LONG", 100.0, 90.0, 2.5);
        let mut exit_a1 = None;
        for (i, &(h, l, c, atr)) in bars.iter().enumerate() {
            if let Some(res) = DynamicTrailingEngine::step_bar(&mut state_a1, i, h, l, c, atr, None) {
                exit_a1 = Some(res);
                break;
            }
        }

        let res_a0 = exit_a0.unwrap();
        let res_a1 = exit_a1.unwrap();

        // A1 got prematurely choked at Bar 1
        assert_eq!(res_a1.exit_bar, 1);
        assert!((res_a1.realized_r - 0.07).abs() < 1e-6);

        // A0 rode the trend and captured +4.25R (142.5 exit)
        assert_eq!(res_a0.exit_bar, 3);
        assert_eq!(res_a0.exit_price, 142.5);
        assert!((res_a0.realized_r - 4.25).abs() < 1e-6);
    }
}
