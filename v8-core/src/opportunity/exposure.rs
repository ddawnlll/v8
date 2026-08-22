//! Economic exposure identity, alias resolution and False-Collapse Protection (Issue #231, #232, D-130).
//!
//! Owning Authority: V8 Constitution Rules 16, 19, 26.
//!
//! Identity Constitution:
//!   Symbol != Instrument != EconomicExposure != Opportunity != Trade
//!
//! Seat 4 Mandate / Rule 26:
//!   Spot-Perp basis, calendar spreads, and cross-venue dislocations must preserve
//!   distinct leg identities and never collapse into a naive zero-directional scalar.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
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

    /// Gross absolute factor notional multiplier (sum of absolute leg weights).
    pub fn gross_leg_weight(&self) -> f64 {
        self.legs.iter().map(|l| l.weight.abs()).sum()
    }
}

/// Metadata mapping for a known symbol/ticker on a venue.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SymbolDescriptor {
    pub symbol: String,
    pub venue: String,
    pub underlying_factor: String,
    pub instrument_type: InstrumentType,
    pub settlement_asset: String,
}

/// Exposure Resolver mapping venue tickers to canonical economic factor exposures (Issue #232).
#[derive(Debug, Clone, Default)]
pub struct ExposureResolver {
    descriptors: HashMap<(String, String), SymbolDescriptor>,
}

impl ExposureResolver {
    pub fn new() -> Self {
        let mut resolver = Self::default();
        resolver.register_standard_crypto_universe();
        resolver
    }

    /// Pre-registers standard crypto assets and aliases for test & production environments.
    pub fn register_standard_crypto_universe(&mut self) {
        let std_symbols = [
            ("BTCUSDT", "binance-um", "BTC", InstrumentType::Perpetual, "USDT"),
            ("BTCUSDT", "binance-spot", "BTC", InstrumentType::Spot, "USDT"),
            ("BTC_ALIAS1", "binance-um", "BTC", InstrumentType::Perpetual, "USDT"),
            ("BTC_ALIAS2", "binance-um", "BTC", InstrumentType::Perpetual, "USDT"),
            ("BTC_ALIAS3", "binance-um", "BTC", InstrumentType::Perpetual, "USDT"),
            ("ETHUSDT", "binance-um", "ETH", InstrumentType::Perpetual, "USDT"),
            ("ETHUSDT", "binance-spot", "ETH", InstrumentType::Spot, "USDT"),
            ("SOLUSDT", "binance-um", "SOL", InstrumentType::Perpetual, "USDT"),
            ("SOLUSDT", "binance-spot", "SOL", InstrumentType::Spot, "USDT"),
            ("BNBUSDT", "binance-um", "BNB", InstrumentType::Perpetual, "USDT"),
            ("XRPUSDT", "binance-um", "XRP", InstrumentType::Perpetual, "USDT"),
            ("DOGEUSDT", "binance-um", "DOGE", InstrumentType::Perpetual, "USDT"),
            ("AVAXUSDT", "binance-um", "AVAX", InstrumentType::Perpetual, "USDT"),
        ];

        for (sym, ven, fac, itype, sett) in std_symbols {
            self.register(SymbolDescriptor {
                symbol: sym.to_string(),
                venue: ven.to_string(),
                underlying_factor: fac.to_string(),
                instrument_type: itype,
                settlement_asset: sett.to_string(),
            });
        }
    }

    pub fn register(&mut self, descriptor: SymbolDescriptor) {
        self.descriptors.insert(
            (descriptor.symbol.clone(), descriptor.venue.clone()),
            descriptor,
        );
    }

    /// Resolves a single ticker symbol on a venue to its canonical EconomicExposureStructure.
    pub fn resolve_ticker(
        &self,
        symbol: &str,
        venue: &str,
        direction: ExposureDirection,
    ) -> Result<EconomicExposureStructure, V8CoreError> {
        let desc = self
            .descriptors
            .get(&(symbol.to_string(), venue.to_string()))
            .ok_or_else(|| V8CoreError::UnresolvedExposure {
                symbol: symbol.to_string(),
                venue: venue.to_string(),
                reason: "Symbol descriptor not registered in ExposureResolver".to_string(),
            })?;

        match desc.instrument_type {
            InstrumentType::Spot => EconomicExposureStructure::single_spot(
                &desc.symbol,
                &desc.underlying_factor,
                &desc.venue,
                &desc.settlement_asset,
                direction,
            ),
            InstrumentType::Perpetual => EconomicExposureStructure::single_perp(
                &desc.symbol,
                &desc.underlying_factor,
                &desc.venue,
                &desc.settlement_asset,
                direction,
            ),
            _ => EconomicExposureStructure::new(
                vec![desc.underlying_factor.clone()],
                desc.instrument_type,
                &desc.venue,
                &desc.settlement_asset,
                direction,
                PayoffStructure::Linear,
                vec![ExposureLeg::new(&desc.symbol, &desc.venue, desc.instrument_type, 1.0)],
                HorizonClass::Intraday,
            ),
        }
    }

    /// Resolves a spot-perp basis spread between two venues or symbols.
    pub fn resolve_basis_spread(
        &self,
        spot_symbol: &str,
        spot_venue: &str,
        perp_symbol: &str,
        perp_venue: &str,
    ) -> Result<EconomicExposureStructure, V8CoreError> {
        let spot_desc = self
            .descriptors
            .get(&(spot_symbol.to_string(), spot_venue.to_string()))
            .ok_or_else(|| V8CoreError::UnresolvedExposure {
                symbol: spot_symbol.to_string(),
                venue: spot_venue.to_string(),
                reason: "Spot leg descriptor missing".to_string(),
            })?;

        let perp_desc = self
            .descriptors
            .get(&(perp_symbol.to_string(), perp_venue.to_string()))
            .ok_or_else(|| V8CoreError::UnresolvedExposure {
                symbol: perp_symbol.to_string(),
                venue: perp_venue.to_string(),
                reason: "Perp leg descriptor missing".to_string(),
            })?;

        if spot_desc.underlying_factor != perp_desc.underlying_factor {
            return Err(V8CoreError::InvalidExposureStructure(format!(
                "Cannot build basis spread on mismatched factors: {} vs {}",
                spot_desc.underlying_factor, perp_desc.underlying_factor
            )));
        }

        EconomicExposureStructure::spot_perp_basis(
            &spot_desc.underlying_factor,
            &spot_desc.symbol,
            &spot_desc.venue,
            &perp_desc.symbol,
            &perp_desc.venue,
            &perp_desc.settlement_asset,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_exact_alias_collapse_into_single_factor() {
        let resolver = ExposureResolver::new();
        
        let exp_primary = resolver.resolve_ticker("BTCUSDT", "binance-um", ExposureDirection::Long).unwrap();
        let exp_alias1 = resolver.resolve_ticker("BTC_ALIAS1", "binance-um", ExposureDirection::Long).unwrap();
        let exp_alias2 = resolver.resolve_ticker("BTC_ALIAS2", "binance-um", ExposureDirection::Long).unwrap();

        // All aliases must resolve to the identical underlying factor dimension
        assert_eq!(exp_primary.underlying_factors, vec!["BTC".to_string()]);
        assert_eq!(exp_alias1.underlying_factors, vec!["BTC".to_string()]);
        assert_eq!(exp_alias2.underlying_factors, vec!["BTC".to_string()]);
        assert_eq!(exp_primary.exposure_id.len(), 64);
    }

    #[test]
    fn test_anti_false_collapse_basis_preservation() {
        let resolver = ExposureResolver::new();
        let basis = resolver
            .resolve_basis_spread("BTCUSDT", "binance-spot", "BTCUSDT", "binance-um")
            .unwrap();

        // Invariant: Must not be collapsed to zero-direction or single scalar
        assert!(basis.is_basis_or_spread());
        assert_eq!(basis.direction, ExposureDirection::Neutral);
        assert_eq!(basis.legs.len(), 2);
        assert_eq!(basis.gross_leg_weight(), 2.0); // 1.0 spot + 1.0 perp = 2.0 gross notional exposure
        assert_eq!(basis.underlying_factors, vec!["BTC".to_string(), "BTC_BASIS".to_string()]);
    }

    #[test]
    fn test_unresolved_exposure_fails_closed() {
        let resolver = ExposureResolver::new();
        let err = resolver.resolve_ticker("NONEXISTENT_COIN", "unknown-venue", ExposureDirection::Long);
        match err {
            Err(V8CoreError::UnresolvedExposure { symbol, venue, .. }) => {
                assert_eq!(symbol, "NONEXISTENT_COIN");
                assert_eq!(venue, "unknown-venue");
            }
            other => panic!("Expected UnresolvedExposure, got: {:?}", other),
        }
    }
}
