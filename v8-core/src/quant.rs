//! Quantitative Analysis, Market Regime Classification, Brownian Bridge,
//! Transaction Cost Attribution, and Portfolio Analytics Engine (D-107).

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// 4-Dimensional Point-in-Time Market Regime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TrendRegime {
    BullTrend,
    BearTrend,
    ChopRange,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum VolRegime {
    HighVol,
    NormalVol,
    LowVolSqueeze,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum VolumeRegime {
    VolumeExpansion,
    NormalVolume,
    VolumeDrought,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FundingRegime {
    CrowdedLong,
    CrowdedShort,
    NeutralFunding,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct MarketRegimeTag {
    pub trend: TrendRegime,
    pub volatility: VolRegime,
    pub volume: VolumeRegime,
    pub funding: FundingRegime,
}

impl MarketRegimeTag {
    pub fn to_string_code(&self) -> String {
        format!(
            "{:?}_{:?}_{:?}_{:?}",
            self.trend, self.volatility, self.volume, self.funding
        )
    }
}

/// Point-in-time regime classifier from feature store metrics.
pub fn classify_bar_regime(
    close: f64,
    _open: f64,
    _high: f64,
    _low: f64,
    volume: f64,
    avg_volume: f64,
    ema_fast: f64,
    ema_slow: f64,
    adx: f64,
    atr: f64,
    atr_rolling_median: f64,
    funding_rate: f64,
) -> MarketRegimeTag {
    // 1. Trend Regime (ADX + EMA alignment + price location)
    let trend = if adx > 20.0 && ema_fast > ema_slow && close > ema_fast {
        TrendRegime::BullTrend
    } else if adx > 20.0 && ema_fast < ema_slow && close < ema_fast {
        TrendRegime::BearTrend
    } else {
        TrendRegime::ChopRange
    };

    // 2. Volatility Regime (ATR vs rolling median ATR)
    let volatility = if atr_rolling_median > 0.0 {
        let vol_ratio = atr / atr_rolling_median;
        if vol_ratio >= 1.35 {
            VolRegime::HighVol
        } else if vol_ratio <= 0.75 {
            VolRegime::LowVolSqueeze
        } else {
            VolRegime::NormalVol
        }
    } else {
        VolRegime::NormalVol
    };

    // 3. Volume Regime (RVOL = volume / 20-bar avg volume)
    let volume_regime = if avg_volume > 0.0 {
        let rvol = volume / avg_volume;
        if rvol >= 1.30 {
            VolumeRegime::VolumeExpansion
        } else if rvol <= 0.70 {
            VolumeRegime::VolumeDrought
        } else {
            VolumeRegime::NormalVolume
        }
    } else {
        VolumeRegime::NormalVolume
    };

    // 4. Funding Regime (8-hour funding rate crowding)
    let funding = if funding_rate >= 0.00015 {
        FundingRegime::CrowdedLong
    } else if funding_rate <= -0.00015 {
        FundingRegime::CrowdedShort
    } else {
        FundingRegime::NeutralFunding
    };

    MarketRegimeTag {
        trend,
        volatility,
        volume: volume_regime,
        funding,
    }
}

/// Driftless Brownian Bridge first-passage probabilities for intrabar ambiguity.
pub struct BrownianBridge;

impl BrownianBridge {
    /// Computes P(Low hit before High) and P(High hit before Low) given OHLC of the bar.
    /// P(Low before High) = (High - Open) / (High - Low)
    pub fn first_passage_prob(open: f64, high: f64, low: f64) -> (f64, f64) {
        let range = high - low;
        if range <= 1e-12 {
            return (0.5, 0.5);
        }
        let p_low_first = ((high - open) / range).clamp(0.0, 1.0);
        let p_high_first = 1.0 - p_low_first;
        (p_low_first, p_high_first)
    }

    /// Evaluates probabilistic expectation of Net R when both stop and target are touched.
    pub fn expected_net_r_ambiguous(
        direction: &str,
        target_r: f64,
        stop_r: f64,
        cost_r: f64,
        p_low_first: f64,
    ) -> f64 {
        if direction == "LONG" {
            let win_net_r = target_r - cost_r;
            let loss_net_r = -stop_r - cost_r;
            let p_stop = p_low_first;
            let p_target = 1.0 - p_stop;
            p_target * win_net_r + p_stop * loss_net_r
        } else {
            let win_net_r = target_r - cost_r;
            let loss_net_r = -stop_r - cost_r;
            let p_stop = 1.0 - p_low_first; // for short, high hit first is stop
            let p_target = p_low_first;
            p_target * win_net_r + p_stop * loss_net_r
        }
    }
}

/// 5-Component Transaction Cost Attribution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TcaAttribution {
    pub gross_market_r: f64,
    pub fee_cost_r: f64,
    pub slippage_cost_r: f64,
    pub funding_paid_r: f64,
    pub net_r: f64,
}

impl TcaAttribution {
    pub fn new(gross_market_r: f64, fee_cost_r: f64, slippage_cost_r: f64, funding_paid_r: f64) -> Self {
        let net_r = gross_market_r - fee_cost_r - slippage_cost_r - funding_paid_r;
        Self {
            gross_market_r,
            fee_cost_r,
            slippage_cost_r,
            funding_paid_r,
            net_r,
        }
    }
}

/// Institutional Portfolio Performance and Risk Analytics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioMetrics {
    pub n_trades: usize,
    pub win_rate_pct: f64,
    pub profit_factor: f64,
    pub avg_net_r: f64,
    pub total_net_r: f64,
    pub max_drawdown_r: f64,
    pub max_consecutive_losses: usize,
    pub sharpe_ratio: f64,
    pub sortino_ratio: f64,
    pub calmar_ratio: f64,
    pub kelly_full: f64,
    pub kelly_half: f64,
    pub kelly_quarter: f64,
}

pub fn calculate_portfolio_metrics(returns: &[f64]) -> PortfolioMetrics {
    let n = returns.len();
    if n == 0 {
        return PortfolioMetrics {
            n_trades: 0,
            win_rate_pct: 0.0,
            profit_factor: 0.0,
            avg_net_r: 0.0,
            total_net_r: 0.0,
            max_drawdown_r: 0.0,
            max_consecutive_losses: 0,
            sharpe_ratio: 0.0,
            sortino_ratio: 0.0,
            calmar_ratio: 0.0,
            kelly_full: 0.0,
            kelly_half: 0.0,
            kelly_quarter: 0.0,
        };
    }

    let wins: Vec<f64> = returns.iter().copied().filter(|r| *r > 0.0).collect();
    let losses: Vec<f64> = returns.iter().copied().filter(|r| *r < 0.0).collect();

    let n_wins = wins.len();
    let win_rate = (n_wins as f64 / n as f64) * 100.0;
    let p_win = n_wins as f64 / n as f64;
    let p_loss = 1.0 - p_win;

    let gross_gains: f64 = wins.iter().sum();
    let gross_losses: f64 = losses.iter().map(|r| r.abs()).sum();
    let pf = if gross_losses > 0.0 { gross_gains / gross_losses } else { 99.0 };

    let total_r: f64 = returns.iter().sum();
    let avg_r = total_r / n as f64;

    // Equity curve & Drawdown
    let mut cum_r = 0.0;
    let mut peak = 0.0;
    let mut max_dd = 0.0;
    let mut cur_loss_streak = 0;
    let mut max_loss_streak = 0;

    for r in returns {
        cum_r += *r;
        if cum_r > peak {
            peak = cum_r;
        }
        let dd = peak - cum_r;
        if dd > max_dd {
            max_dd = dd;
        }

        if *r < 0.0 {
            cur_loss_streak += 1;
            if cur_loss_streak > max_loss_streak {
                max_loss_streak = cur_loss_streak;
            }
        } else {
            cur_loss_streak = 0;
        }
    }

    // Standard deviation and Downside deviation for Sharpe & Sortino
    let variance: f64 = returns.iter().map(|r| (r - avg_r).powi(2)).sum::<f64>() / n as f64;
    let std_dev = variance.sqrt();
    let downside_variance: f64 = returns
        .iter()
        .map(|r| if *r < 0.0 { r.powi(2) } else { 0.0 })
        .sum::<f64>()
        / n as f64;
    let downside_dev = downside_variance.sqrt();

    // Annualized roughly assuming trade frequency
    let sharpe = if std_dev > 1e-9 {
        (avg_r / std_dev) * (n as f64).sqrt()
    } else {
        0.0
    };

    let sortino = if downside_dev > 1e-9 {
        (avg_r / downside_dev) * (n as f64).sqrt()
    } else {
        0.0
    };

    let calmar = if max_dd > 1e-9 {
        total_r / max_dd
    } else {
        0.0
    };

    // Kelly Criterion: f* = p - (q / b), where b = avg_win / avg_loss
    let avg_win = if !wins.is_empty() { gross_gains / wins.len() as f64 } else { 0.0 };
    let avg_loss = if !losses.is_empty() { gross_losses / losses.len() as f64 } else { 1.0 };
    let b_ratio = if avg_loss > 1e-9 { avg_win / avg_loss } else { 1.0 };

    let kelly_full = if b_ratio > 1e-9 {
        ((p_win * b_ratio - p_loss) / b_ratio).clamp(-1.0, 1.0)
    } else {
        0.0
    };

    PortfolioMetrics {
        n_trades: n,
        win_rate_pct: win_rate,
        profit_factor: pf,
        avg_net_r: avg_r,
        total_net_r: total_r,
        max_drawdown_r: max_dd,
        max_consecutive_losses: max_loss_streak,
        sharpe_ratio: sharpe,
        sortino_ratio: sortino,
        calmar_ratio: calmar,
        kelly_full,
        kelly_half: kelly_full * 0.5,
        kelly_quarter: kelly_full * 0.25,
    }
}

/// Regime performance partition bucket.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegimeBucketStats {
    pub regime_name: String,
    pub n_trades: usize,
    pub win_rate_pct: f64,
    pub avg_net_r: f64,
    pub total_net_r: f64,
    pub profit_factor: f64,
}

pub fn partition_by_regime(
    episodes: &[(&MarketRegimeTag, f64)],
) -> BTreeMap<String, RegimeBucketStats> {
    let mut buckets: BTreeMap<String, Vec<f64>> = BTreeMap::new();

    for (tag, r) in episodes {
        let code = tag.to_string_code();
        buckets.entry(code).or_default().push(*r);

        // Also aggregate by top-level dimensions
        let trend_key = format!("Trend_{:?}", tag.trend);
        buckets.entry(trend_key).or_default().push(*r);

        let vol_key = format!("Vol_{:?}", tag.volatility);
        buckets.entry(vol_key).or_default().push(*r);

        let funding_key = format!("Funding_{:?}", tag.funding);
        buckets.entry(funding_key).or_default().push(*r);
    }

    let mut out = BTreeMap::new();
    for (name, rs) in buckets {
        let m = calculate_portfolio_metrics(&rs);
        out.insert(
            name.clone(),
            RegimeBucketStats {
                regime_name: name,
                n_trades: m.n_trades,
                win_rate_pct: m.win_rate_pct,
                avg_net_r: m.avg_net_r,
                total_net_r: m.total_net_r,
                profit_factor: m.profit_factor,
            },
        );
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_brownian_bridge_probability_bounds() {
        let (p_low, p_high) = BrownianBridge::first_passage_prob(100.0, 110.0, 90.0);
        assert!((p_low - 0.5).abs() < 1e-6);
        assert!((p_high - 0.5).abs() < 1e-6);

        let (p_low_near_top, _) = BrownianBridge::first_passage_prob(109.0, 110.0, 90.0);
        assert!((p_low_near_top - 0.05).abs() < 1e-6);

        let (p_low_near_bot, _) = BrownianBridge::first_passage_prob(91.0, 110.0, 90.0);
        assert!((p_low_near_bot - 0.95).abs() < 1e-6);
    }

    #[test]
    fn test_tca_pnl_attribution_conservation() {
        let tca = TcaAttribution::new(1.5, 0.04, 0.03, 0.01);
        assert!((tca.net_r - 1.42).abs() < 1e-9);
    }

    #[test]
    fn test_portfolio_metrics_edge_cases() {
        let returns = vec![1.0, -0.5, 1.5, -1.0, 2.0];
        let m = calculate_portfolio_metrics(&returns);
        assert_eq!(m.n_trades, 5);
        assert_eq!(m.win_rate_pct, 60.0);
        assert!((m.total_net_r - 3.0).abs() < 1e-9);
        assert!(m.sharpe_ratio > 0.0);
    }
}
