//! 5-Component Economic Cashflow Ledger and Accounting Conservation Equations.
//!
//! Owning Authority: VENUE_AND_CAPITAL_SIMULATION_SPEC.md §7, Decisions D-116.

use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::collections::HashSet;
use std::io::{BufRead, BufWriter, Write};
use std::path::Path;

/// 5-Component Economic Cashflow Event Record (VENUE_AND_CAPITAL_SIMULATION_SPEC §7).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EconomicCashflow {
    pub event_time: i64,
    pub candidate_id: String,
    pub symbol: String,
    pub direction: String,
    pub quantity: f64,
    pub entry_price: f64,
    pub exit_price: f64,
    pub gross_market_pnl_usdt: f64,
    pub commission_usdt: f64,
    pub funding_cashflow_usdt: f64,
    pub slippage_usdt: f64,
    pub gap_through_stop_usdt: f64,
    pub net_pnl_usdt: f64,
    pub wallet_balance_before: f64,
    pub wallet_balance_after: f64,
    pub margin_usage_pct: f64,
}

impl EconomicCashflow {
    /// Constructs and validates a cashflow event enforcing strict accounting conservation.
    pub fn new(
        event_time: i64,
        candidate_id: String,
        symbol: String,
        direction: String,
        quantity: f64,
        entry_price: f64,
        exit_price: f64,
        gross_market_pnl_usdt: f64,
        commission_usdt: f64,
        funding_cashflow_usdt: f64,
        slippage_usdt: f64,
        gap_through_stop_usdt: f64,
        wallet_balance_before: f64,
        margin_usage_pct: f64,
    ) -> Result<Self, String> {
        let net_pnl_usdt = gross_market_pnl_usdt - commission_usdt + funding_cashflow_usdt
            - slippage_usdt
            - gap_through_stop_usdt;
        let wallet_balance_after = wallet_balance_before + net_pnl_usdt;

        let flow = Self {
            event_time,
            candidate_id,
            symbol,
            direction,
            quantity,
            entry_price,
            exit_price,
            gross_market_pnl_usdt,
            commission_usdt,
            funding_cashflow_usdt,
            slippage_usdt,
            gap_through_stop_usdt,
            net_pnl_usdt,
            wallet_balance_before,
            wallet_balance_after,
            margin_usage_pct,
        };

        flow.verify_conservation()?;
        Ok(flow)
    }

    /// Verifies strict cashflow conservation (Invariant 5.1).
    pub fn verify_conservation(&self) -> Result<(), String> {
        let expected_net = self.gross_market_pnl_usdt - self.commission_usdt
            + self.funding_cashflow_usdt
            - self.slippage_usdt
            - self.gap_through_stop_usdt;
        if (self.net_pnl_usdt - expected_net).abs() > 1e-6 {
            return Err(format!(
                "Net PnL conservation violated: recorded {:.6}, calculated {:.6}",
                self.net_pnl_usdt, expected_net
            ));
        }
        let expected_wallet_after = self.wallet_balance_before + self.net_pnl_usdt;
        if (self.wallet_balance_after - expected_wallet_after).abs() > 1e-6 {
            return Err(format!(
                "Wallet balance conservation violated: recorded {:.6}, calculated {:.6}",
                self.wallet_balance_after, expected_wallet_after
            ));
        }
        Ok(())
    }
}

/// Append-only Economic Cashflow Ledger.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct CashflowLedger {
    pub flows: Vec<EconomicCashflow>,
}

impl CashflowLedger {
    pub fn new() -> Self {
        Self { flows: Vec::new() }
    }

    /// Appends and validates a cashflow record.
    pub fn record(&mut self, flow: EconomicCashflow) -> Result<(), String> {
        flow.verify_conservation()?;
        self.flows.push(flow);
        Ok(())
    }

    /// Publishes only cashflow records not already present in the append-only
    /// ledger.  The canonical JSON record is used as the idempotence key because
    /// the legacy cashflow schema predates a dedicated event id.
    pub fn write_jsonl(&self, path: &Path) -> std::io::Result<()> {
        let mut persisted = HashSet::new();
        if path.exists() {
            let file = std::fs::File::open(path)?;
            for line in std::io::BufReader::new(file).lines() {
                let line = line?;
                if line.trim().is_empty() {
                    continue;
                }
                let flow: EconomicCashflow = serde_json::from_str(&line).map_err(|e| {
                    std::io::Error::new(std::io::ErrorKind::InvalidData, e)
                })?;
                flow.verify_conservation().map_err(|e| {
                    std::io::Error::new(std::io::ErrorKind::InvalidData, e)
                })?;
                persisted.insert(serde_json::to_string(&flow).map_err(|e| {
                    std::io::Error::new(std::io::ErrorKind::InvalidData, e)
                })?);
            }
        }

        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)?;
        let mut writer = BufWriter::new(file);
        for f in &self.flows {
            let json = serde_json::to_string(f)?;
            if !persisted.insert(json.clone()) {
                continue;
            }
            writeln!(writer, "{json}")?;
        }
        writer.flush()?;
        writer.get_ref().sync_data()?;
        Ok(())
    }

    #[allow(dead_code)]
    pub fn total_gross_pnl(&self) -> f64 {
        self.flows.iter().map(|f| f.gross_market_pnl_usdt).sum()
    }

    #[allow(dead_code)]
    pub fn total_commission(&self) -> f64 {
        self.flows.iter().map(|f| f.commission_usdt).sum()
    }

    #[allow(dead_code)]
    pub fn total_funding(&self) -> f64 {
        self.flows.iter().map(|f| f.funding_cashflow_usdt).sum()
    }

    #[allow(dead_code)]
    pub fn total_slippage(&self) -> f64 {
        self.flows.iter().map(|f| f.slippage_usdt).sum()
    }

    #[allow(dead_code)]
    pub fn total_net_pnl(&self) -> f64 {
        self.flows.iter().map(|f| f.net_pnl_usdt).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cashflow_accounting_conservation() {
        let flow = EconomicCashflow::new(
            1750000000,
            "c_101".into(),
            "BTCUSDT".into(),
            "LONG".into(),
            0.05,
            60_000.0,
            62_000.0,
            100.0,  // Gross PnL
            3.05,   // Commission
            0.50,   // Funding
            1.00,   // Slippage
            0.0,    // Gap
            1000.0, // Wallet before
            15.0,   // Margin usage %
        )
        .expect("Valid cashflow");

        assert_eq!(flow.net_pnl_usdt, 96.45);
        assert_eq!(flow.wallet_balance_after, 1096.45);
        assert!(flow.verify_conservation().is_ok());
    }
}
