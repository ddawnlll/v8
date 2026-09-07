//! Extreme Move Detection, Lead-Time & Sensor Recall Benchmark (Issue #213 / MEGA-001).
//! Normative Traceability: D-123, D-124, CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.md, TARGET_ORACLE_SPEC §12.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum MegaCapabilityStatus {
    MegaCapabilitySupported,
    MegaCapabilityFalsified,
    InsufficientEpisodes,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtremeEpisode {
    pub episode_id: String,
    pub symbol: String,
    pub start_bar: usize,
    pub end_bar: usize,
    pub peak_bar: usize,
    pub move_pct: f64,
    pub z_score: f64,
    pub direction: String, // "CRASH" (DOWN) or "EXPANSION" (UP)
    pub start_timestamp_ns: i64,
    pub end_timestamp_ns: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorLeadTimeAudit {
    pub sensor_id: String,
    pub lead_window_hours: usize, // 1, 2, 4, 8, 12
    pub total_episodes_evaluated: usize,
    pub episodes_triggered: usize,
    pub correct_direction_triggers: usize,
    pub recall_rate: f64,          // correct_direction_triggers / total_episodes
    pub directional_accuracy: f64, // correct_direction_triggers / episodes_triggered
    pub false_alarm_count: usize,
    pub false_alarm_rate: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MegaBenchmarkReport {
    pub symbol: String,
    pub total_extreme_episodes: usize,
    pub status: MegaCapabilityStatus,
    pub top_lead_sensors: Vec<String>,
    pub mean_lead_hours: f64,
    pub aggregate_recall_rate: f64,
    pub economic_claim: String, // Rule 12: strictly "NO_ECONOMIC_CLAIM"
}

pub struct ExtremeMoveDetector;

impl ExtremeMoveDetector {
    /// Detect all 24h market episodes where |Z_24h| >= 3.0 sigma.
    pub fn label_extreme_episodes(
        symbol: &str,
        closes: &[f64],
        timestamps: &[i64],
        lookback_bars: usize, // e.g. 24 for 24h
        z_threshold: f64,     // 3.0
    ) -> Vec<ExtremeEpisode> {
        let n = closes.len();
        if n < lookback_bars + 24 || timestamps.len() != n {
            return Vec::new();
        }

        // Calculate 24h rolling log returns & std dev
        let mut returns_24h = vec![0.0; n];
        for i in lookback_bars..n {
            if closes[i - lookback_bars] > 0.0 {
                returns_24h[i] = (closes[i] / closes[i - lookback_bars]).ln();
            }
        }

        // Estimate rolling volatility over a 30-day window (720 bars)
        let vol_window = 720.min(n / 2).max(48);
        let mut episodes = Vec::new();
        let mut last_episode_end = 0;

        for i in vol_window..n {
            if i < last_episode_end + 12 {
                continue; // avoid overlapping double-counting within 12 bars
            }

            let slice = &returns_24h[i - vol_window..i];
            let mean = slice.iter().sum::<f64>() / slice.len() as f64;
            let variance = slice.iter().map(|&r| (r - mean).powi(2)).sum::<f64>() / (slice.len() - 1) as f64;
            let std = variance.sqrt();

            if std <= 1e-8 {
                continue;
            }

            let current_ret = returns_24h[i];
            let z = (current_ret - mean) / std;

            if z.abs() >= z_threshold {
                let start_bar = i.saturating_sub(lookback_bars);
                let end_bar = i;
                let move_pct = (closes[end_bar] - closes[start_bar]) / closes[start_bar];
                let direction = if move_pct < 0.0 { "CRASH" } else { "EXPANSION" };

                episodes.push(ExtremeEpisode {
                    episode_id: format!("MEGA_{}_{}_{}", symbol, start_bar, end_bar),
                    symbol: symbol.to_string(),
                    start_bar,
                    end_bar,
                    peak_bar: end_bar,
                    move_pct,
                    z_score: z,
                    direction: direction.to_string(),
                    start_timestamp_ns: timestamps[start_bar],
                    end_timestamp_ns: timestamps[end_bar],
                });

                last_episode_end = end_bar;
            }
        }

        episodes
    }

    /// Audit sensor triggers across lead-time windows (T-12h, T-8h, T-4h, T-2h, T-1h).
    pub fn audit_sensor_recall(
        sensor_id: &str,
        episodes: &[ExtremeEpisode],
        sensor_triggers: &[(usize, &str)], // (bar_index, direction: "LONG" / "SHORT")
        lead_windows_hours: &[usize],      // [1, 2, 4, 8, 12]
        total_tape_bars: usize,
    ) -> Vec<SensorLeadTimeAudit> {
        let mut audits = Vec::new();

        for &lead_h in lead_windows_hours {
            let mut triggered = 0;
            let mut correct = 0;

            for ep in episodes {
                let lead_start = ep.start_bar.saturating_sub(lead_h);
                let lead_end = ep.start_bar;

                // Look for triggers in [lead_start, lead_end]
                let mut found_trigger = false;
                let mut found_correct = false;

                for &(bar, dir) in sensor_triggers {
                    if bar >= lead_start && bar <= lead_end {
                        found_trigger = true;
                        let expected_dir = if ep.direction == "CRASH" { "SHORT" } else { "LONG" };
                        if dir == expected_dir {
                            found_correct = true;
                            break;
                        }
                    }
                }

                if found_trigger {
                    triggered += 1;
                }
                if found_correct {
                    correct += 1;
                }
            }

            let total_ep = episodes.len();
            let recall = if total_ep > 0 { correct as f64 / total_ep as f64 } else { 0.0 };
            let acc = if triggered > 0 { correct as f64 / triggered as f64 } else { 0.0 };

            // Count false alarms (triggers outside any lead window)
            let mut false_alarms = 0;
            for &(bar, _) in sensor_triggers {
                let inside_lead = episodes.iter().any(|ep| {
                    let ls = ep.start_bar.saturating_sub(lead_h);
                    let le = ep.end_bar;
                    bar >= ls && bar <= le
                });
                if !inside_lead {
                    false_alarms += 1;
                }
            }

            let false_alarm_rate = if total_tape_bars > 0 {
                false_alarms as f64 / total_tape_bars as f64
            } else {
                0.0
            };

            audits.push(SensorLeadTimeAudit {
                sensor_id: sensor_id.to_string(),
                lead_window_hours: lead_h,
                total_episodes_evaluated: total_ep,
                episodes_triggered: triggered,
                correct_direction_triggers: correct,
                recall_rate: recall,
                directional_accuracy: acc,
                false_alarm_count: false_alarms,
                false_alarm_rate,
            });
        }

        audits
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_label_extreme_episodes_detects_crash() {
        let mut closes = vec![100.0; 1000];
        let timestamps: Vec<i64> = (0..1000).map(|i| i * 3_600_000_000_000).collect();

        // Inject 15% crash at bar 800
        for i in 800..824 {
            closes[i] = 100.0 - ((i - 799) as f64 * 0.7);
        }
        for i in 824..1000 {
            closes[i] = closes[823];
        }

        let episodes = ExtremeMoveDetector::label_extreme_episodes("BTCUSDT", &closes, &timestamps, 24, 3.0);
        assert!(!episodes.is_empty());
        assert_eq!(episodes[0].direction, "CRASH");
    }

    #[test]
    fn test_sensor_lead_time_recall_audit() {
        let ep = ExtremeEpisode {
            episode_id: "EP_01".to_string(),
            symbol: "BTCUSDT".to_string(),
            start_bar: 100,
            end_bar: 124,
            peak_bar: 124,
            move_pct: -0.15,
            z_score: -3.5,
            direction: "CRASH".to_string(),
            start_timestamp_ns: 100,
            end_timestamp_ns: 124,
        };

        // Sensor triggered SHORT at bar 96 (4h before start)
        let triggers = vec![(96, "SHORT"), (200, "LONG")];
        let audits = ExtremeMoveDetector::audit_sensor_recall("sensor_breakout", &[ep], &triggers, &[1, 4, 8], 500);

        assert_eq!(audits.len(), 3);
        // At lead_window 1h (bar 99..100): trigger at 96 not caught
        assert_eq!(audits[0].recall_rate, 0.0);
        // At lead_window 4h (bar 96..100): trigger at 96 caught correctly
        assert_eq!(audits[1].recall_rate, 1.0);
        assert_eq!(audits[1].directional_accuracy, 1.0);
    }
}
