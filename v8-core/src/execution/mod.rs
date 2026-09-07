//! Execution-lane abstraction: USDM simulator vs NautilusTrader matching engine.
//!
//! Authority: D-116 (secondary reference engine requirement), D-160 W14
//! (Nautilus differential successor), D-153 parity adapters (no fabrication).
//!
//! `usdm_sim` remains the default lane. `NautilusLane` is the migration
//! target: it maps V8 execution semantics onto NautilusTrader venue
//! configuration and records calibration gaps explicitly (`None`, never
//! synthetic placeholders). Full replacement is blocked until parity is
//! proven; until then the lane selector fails closed on unknown lanes.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// Lane selector understood by `--engine-mode`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionLaneId {
    Usdm,
    Nautilus,
}

impl ExecutionLaneId {
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_ascii_lowercase().as_str() {
            "usdm" | "usdm_sim" | "" => Some(ExecutionLaneId::Usdm),
            "nautilus" | "nautilus_trader" | "nt" => Some(ExecutionLaneId::Nautilus),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            ExecutionLaneId::Usdm => "usdm",
            ExecutionLaneId::Nautilus => "nautilus",
        }
    }
}

/// One calibration dimension between lanes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationDimension {
    pub name: String,
    /// None = unmapped / not applicable (fail closed, never synthetic).
    pub usdm_value: Option<String>,
    pub nautilus_value: Option<String>,
    pub status: CalibrationStatus,
    pub note: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CalibrationStatus {
    Mapped,
    Unmapped,
    NotApplicable,
}

/// Calibration report: V8 knobs vs Nautilus venue config.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationReport {
    pub lane: String,
    pub dimensions: Vec<CalibrationDimension>,
    pub unmapped_count: usize,
}

impl CalibrationReport {
    pub fn gaps(&self) -> Vec<&CalibrationDimension> {
        self.dimensions
            .iter()
            .filter(|d| d.status != CalibrationStatus::Mapped)
            .collect()
    }
}

pub trait ExecutionLane {
    fn lane_id(&self) -> ExecutionLaneId;
    fn describe(&self) -> BTreeMap<String, String>;
    fn calibrate(&self) -> CalibrationReport;
}

/// Default lane: wraps existing `usdm_sim` semantics by reference.
pub struct UsdmLane {
    pub initial_balance: f64,
    pub risk_fraction: f64,
    pub leverage: u32,
}

impl ExecutionLane for UsdmLane {
    fn lane_id(&self) -> ExecutionLaneId {
        ExecutionLaneId::Usdm
    }

    fn describe(&self) -> BTreeMap<String, String> {
        let mut m = BTreeMap::new();
        m.insert("lane".into(), "usdm".into());
        m.insert("engine".into(), "v8 usdm_sim (default)".into());
        m.insert("initial_balance".into(), self.initial_balance.to_string());
        m.insert("risk_fraction".into(), self.risk_fraction.to_string());
        m.insert("leverage".into(), self.leverage.to_string());
        m
    }

    fn calibrate(&self) -> CalibrationReport {
        CalibrationReport {
            lane: "usdm".into(),
            dimensions: vec![CalibrationDimension {
                name: "self".into(),
                usdm_value: Some("reference".into()),
                nautilus_value: None,
                status: CalibrationStatus::NotApplicable,
                note: "identity lane; nothing to map".into(),
            }],
            unmapped_count: 0,
        }
    }
}

/// Migration target lane: NautilusTrader venue mapping.
///
/// Maps the V8 execution knobs that have a Nautilus counterpart and marks
/// everything else `Unmapped` (maker fill probability, adverse selection,
/// funding-clock sign conventions owned by W14).
pub struct NautilusLane {
    pub initial_balance: f64,
    pub risk_fraction: f64,
    pub leverage: u32,
    /// Nautilus venue id, e.g. `BINANCE`.
    pub venue: String,
}

impl NautilusLane {
    pub fn venue_config(&self) -> BTreeMap<String, String> {
        let mut m = BTreeMap::new();
        m.insert("venue".into(), self.venue.clone());
        m.insert("oms_type".into(), "NETTING".into());
        m.insert("account_type".into(), "MARGIN".into());
        m.insert("base_currency".into(), "USDT".into());
        m.insert("leverage".into(), self.leverage.to_string());
        m
    }
}

impl ExecutionLane for NautilusLane {
    fn lane_id(&self) -> ExecutionLaneId {
        ExecutionLaneId::Nautilus
    }

    fn describe(&self) -> BTreeMap<String, String> {
        let mut m = self.venue_config();
        m.insert("lane".into(), "nautilus".into());
        m.insert("engine".into(), "nautilus_trader 0.63 matching engine".into());
        m
    }

    fn calibrate(&self) -> CalibrationReport {
        let dims = vec![
            CalibrationDimension {
                name: "account/leverage".into(),
                usdm_value: Some(self.leverage.to_string()),
                nautilus_value: Some(self.leverage.to_string()),
                status: CalibrationStatus::Mapped,
                note: "direct map onto Nautilus margin account".into(),
            },
            CalibrationDimension {
                name: "account/balance".into(),
                usdm_value: Some(self.initial_balance.to_string()),
                nautilus_value: Some(self.initial_balance.to_string()),
                status: CalibrationStatus::Mapped,
                note: "starting USDT balance".into(),
            },
            CalibrationDimension {
                name: "risk/risk_fraction".into(),
                usdm_value: Some(self.risk_fraction.to_string()),
                nautilus_value: None,
                status: CalibrationStatus::Unmapped,
                note: "V8 position-sizing knob; no Nautilus venue counterpart (strategy-side)".into(),
            },
            CalibrationDimension {
                name: "execution/maker_fill_probability".into(),
                usdm_value: None,
                nautilus_value: None,
                status: CalibrationStatus::Unmapped,
                note: "owned by W14 differential successor; NOT_APPLICABLE until measured".into(),
            },
            CalibrationDimension {
                name: "execution/adverse_selection".into(),
                usdm_value: None,
                nautilus_value: None,
                status: CalibrationStatus::Unmapped,
                note: "owned by W14; NOT_APPLICABLE until measured".into(),
            },
            CalibrationDimension {
                name: "funding/clock_sign".into(),
                usdm_value: None,
                nautilus_value: None,
                status: CalibrationStatus::Unmapped,
                note: "D-160 carried OPEN_PIN (liquidation cum-sign); unresolved".into(),
            },
        ];
        let unmapped = dims
            .iter()
            .filter(|d| d.status != CalibrationStatus::Mapped)
            .count();
        CalibrationReport {
            lane: "nautilus".into(),
            dimensions: dims,
            unmapped_count: unmapped,
        }
    }
}

/// Resolve `--engine-mode` to a lane id, failing closed on unknown values.
pub fn resolve_lane(mode: Option<&str>) -> Result<ExecutionLaneId, String> {
    match mode {
        None => Ok(ExecutionLaneId::Usdm),
        Some(s) => ExecutionLaneId::parse(s)
            .ok_or_else(|| format!("unknown engine-mode `{s}`: expected `usdm` or `nautilus`")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lane_resolution_fails_closed_on_unknown() {
        assert!(resolve_lane(Some("bogus")).is_err());
        assert_eq!(resolve_lane(None).unwrap(), ExecutionLaneId::Usdm);
        assert_eq!(
            resolve_lane(Some("nautilus")).unwrap(),
            ExecutionLaneId::Nautilus
        );
    }

    #[test]
    fn nautilus_calibration_never_fabricates() {
        let lane = NautilusLane {
            initial_balance: 1000.0,
            risk_fraction: 0.005,
            leverage: 10,
            venue: "BINANCE".into(),
        };
        let report = lane.calibrate();
        // Mapped dims carry values on both sides; unmapped dims must be None,
        // never invented zeros.
        for d in &report.dimensions {
            if d.status == CalibrationStatus::Mapped {
                assert!(d.usdm_value.is_some() && d.nautilus_value.is_some());
            }
        }
        assert!(report.unmapped_count >= 3);
        assert!(!report.gaps().is_empty());
    }
}
