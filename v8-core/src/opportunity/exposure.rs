//! Economic exposure identity and structure definitions (Issue #231, #232, D-130).
//!
//! Owning Authority: V8 Constitution Rules 16, 19, 26.
//!
//! Identity Constitution:
//!   Symbol != Instrument != EconomicExposure != Opportunity != Trade

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;

/// Instrument category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum InstrumentType {
    Spot,
    Perpetual,
    DeliveryFuture,
    Option,
    SyntheticSpread,
}

/// Exposure directionality.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ExposureDirection {
    Long,
    Short,
    Neutral,
    Bidirectional,
}

/// Payoff curvature / complexity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum PayoffStructure {
    Linear,
    Convex,
    NonLinear,
    MultiLeg,
}

/// Expected structural duration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum HorizonClass {
    Intraday,
    MultiDay,
    Structural,
}

/// One leg of a multi-leg or single-asset exposure structure.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExposureLeg {
    pub symbol: String,
    pub venue: String,
    pub instrument_type: InstrumentType,
    pub weight: f64,
}

impl ExposureLeg {
    pub fn new(symbol: impl Into<String>, venue: impl Into<String>, instrument_type: InstrumentType, weight: f64) -> Self {
        Self {
            symbol: symbol.into(),
            venue: venue.into(),
            instrument_type,
            weight,
        }
    }
}

/// Canonical Economic Exposure Structure (Primitive 2 of 7).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EconomicExposureStructure {
    pub exposure_id: String,
    pub underlying_factors: Vec<String>,
    pub instrument_type: InstrumentType,
    pub venue: String,
    pub settlement_asset: String,
    pub direction: ExposureDirection,
    pub payoff_structure: PayoffStructure,
    pub legs: Vec<ExposureLeg>,
    pub horizon_class: HorizonClass,
}

impl EconomicExposureStructure {
    /// Builds and computes the cryptographic BLAKE3 identity for an ExposureStructure.
    pub fn new(
        underlying_factors: Vec<String>,
        instrument_type: InstrumentType,
        venue: impl Into<String>,
        settlement_asset: impl Into<String>,
        direction: ExposureDirection,
        payoff_structure: PayoffStructure,
        legs: Vec<ExposureLeg>,
        horizon_class: HorizonClass,
    ) -> Result<Self, V8CoreError> {
        let venue = venue.into();
        let settlement_asset = settlement_asset.into();

        if underlying_factors.is_empty() {
            return Err(V8CoreError::InvalidExposureStructure(
                "underlying_factors cannot be empty".to_string(),
            ));
        }
        if legs.is_empty() {
            return Err(V8CoreError::InvalidExposureStructure(
                "exposure legs cannot be empty".to_string(),
            ));
        }

        let mut exposure = Self {
            exposure_id: String::new(),
            underlying_factors,
            instrument_type,
            venue,
            settlement_asset,
            direction,
            payoff_structure,
            legs,
            horizon_class,
        };
        exposure.exposure_id = exposure.compute_id();
        Ok(exposure)
    }

    /// Single spot asset helper.
    pub fn single_spot(symbol: &str, factor: &str, venue: &str, settlement: &str, dir: ExposureDirection) -> Result<Self, V8CoreError> {
        Self::new(
            vec![factor.to_string()],
            InstrumentType::Spot,
            venue,
            settlement,
            dir,
            PayoffStructure::Linear,
            vec![ExposureLeg::new(symbol, venue, InstrumentType::Spot, 1.0)],
            HorizonClass::Intraday,
        )
    }

    /// Single perpetual contract helper.
    pub fn single_perp(symbol: &str, factor: &str, venue: &str, settlement: &str, dir: ExposureDirection) -> Result<Self, V8CoreError> {
        Self::new(
            vec![factor.to_string()],
            InstrumentType::Perpetual,
            venue,
            settlement,
            dir,
            PayoffStructure::Linear,
            vec![ExposureLeg::new(symbol, venue, InstrumentType::Perpetual, 1.0)],
            HorizonClass::Intraday,
        )
    }

    /// Spot-Perp Cash & Carry / Basis spread helper (Rule 26 False-Collapse Protection).
    pub fn spot_perp_basis(
        factor: &str,
        spot_symbol: &str,
        spot_venue: &str,
        perp_symbol: &str,
        perp_venue: &str,
        settlement: &str,
    ) -> Result<Self, V8CoreError> {
        Self::new(
            vec![factor.to_string(), format!("{factor}_BASIS")],
            InstrumentType::SyntheticSpread,
            perp_venue,
            settlement,
            ExposureDirection::Neutral,
            PayoffStructure::MultiLeg,
            vec![
                ExposureLeg::new(spot_symbol, spot_venue, InstrumentType::Spot, 1.0),
                ExposureLeg::new(perp_symbol, perp_venue, InstrumentType::Perpetual, -1.0),
            ],
            HorizonClass::MultiDay,
        )
    }

    /// Computes deterministic BLAKE3 identity hash for this exposure structure.
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("EconomicExposureStructure");
        
        // Canonical sorted factors
        let mut sorted_factors = self.underlying_factors.clone();
        sorted_factors.sort();
        c.push_list();
        c.push_count(sorted_factors.len());
        for f in &sorted_factors {
            c.push_str(f);
        }

        c.push_str(&format!("{:?}", self.instrument_type));
        c.push_str(&self.venue);
        c.push_str(&self.settlement_asset);
        c.push_str(&format!("{:?}", self.direction));
        c.push_str(&format!("{:?}", self.payoff_structure));
        c.push_str(&format!("{:?}", self.horizon_class));

        c.push_list();
        c.push_count(self.legs.len());
        for leg in &self.legs {
            c.push_str(&leg.symbol);
            c.push_str(&leg.venue);
            c.push_str(&format!("{:?}", leg.instrument_type));
            c.push_f64(leg.weight);
        }

        c.finish_blake3_hex()
    }

    /// Checks if this is a basis or multi-leg structure requiring independent leg tracking.
    pub fn is_basis_or_spread(&self) -> bool {
        self.payoff_structure == PayoffStructure::MultiLeg
            || self.instrument_type == InstrumentType::SyntheticSpread
            || self.legs.len() > 1
    }
}
