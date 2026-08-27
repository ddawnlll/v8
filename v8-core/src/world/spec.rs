//! World Specification, Families and Receipts (D-147, D-149, D-150, Foundry v2).
//!
//! Scoped strictly under test harness. Synthetic worlds are deterministic, content-addressed,
//! and strictly isolated from production economic claim minting.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

/// 14 Categorical families of synthetic market worlds (Foundry v2, D-150).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum WorldFamily {
    /// 1. 9-state Markov regime engine (TrendUp, TrendDown, LowVolRange, HighVolChop, Euphoria, Capitulation, Cascade, Recovery, SlowBleed)
    StructuralRegime,
    /// 2. Fixed-block empirical resampling
    BlockResampled,
    /// 3. Politis-Romano variable-block stationary bootstrap
    StationaryBootstrap,
    /// 4. GARCH(1,1) / Heston-style volatility clustering & vol-of-vol
    StochasticVolatility,
    /// 5. Clustered Hawkes self-exciting jumps & downside cascades
    JumpCascade,
    /// 6. Dynamic copula cross-asset correlation & tail contagion across quad basket
    CrossAssetContagion,
    /// 7. Endogenous funding rate dynamics & basis crowding
    FundingBasisWorld,
    /// 8. Spread widening, slippage amplification & liquidity depth collapse
    LiquidityStressWorld,
    /// 9. Multi-axis surgical intervention on real market tape
    CounterfactualSurgery,
    /// 10. Identical terminal return across distinct path geometries
    PathTopologyWorld,
    /// 11. Learned diffusion / GAN-diffusion stylized facts generator stub
    LearnedGenerativeWorld,
    /// 12. Endogenous participant / order-flow simulation stub
    AgentMarketWorld,
    /// 13. Metamorphic scaling, mirror inversion, time-reversal & permutation relations
    MetamorphicWorld,
    /// 14. Minimal-plausibility-distance adversarial failure trajectory search
    ReverseStressAdversarial,
}

/// Three isolated populations of synthetic worlds (D-150).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum SyntheticPopulation {
    /// Open to agents for hypothesis discovery and parameter calibration
    SyntheticDev,
    /// Sealed cryptographic seeds; agents cannot inspect during development
    SyntheticQualification,
    /// Fresh runtime seeds and perturbations generated upon release qualification
    SyntheticNovelty,
}

/// Exact specification parameters for generating a market world.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorldSpec {
    pub family: WorldFamily,
    pub population: SyntheticPopulation,
    pub symbol: String,
    pub n_bars: usize,
    pub base_price: f64,
    pub volatility_annualized: f64,
    pub jump_frequency: f64,
    pub jump_mean: f64,
    pub jump_std: f64,
    pub seed: u64,
}

impl Default for WorldSpec {
    fn default() -> Self {
        Self {
            family: WorldFamily::StructuralRegime,
            population: SyntheticPopulation::SyntheticDev,
            symbol: "BTCUSDT".to_string(),
            n_bars: 720,
            base_price: 50000.0,
            volatility_annualized: 0.65,
            jump_frequency: 12.0,
            jump_mean: -0.015,
            jump_std: 0.03,
            seed: 42,
        }
    }
}

/// Individual synthetic candle bar with microstructure context.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorldBar {
    pub timestamp_ns: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    #[serde(default)]
    pub funding_rate: f64,
    #[serde(default)]
    pub spread_bps: f64,
}

impl WorldBar {
    pub fn new_simple(timestamp_ns: i64, open: f64, high: f64, low: f64, close: f64, volume: f64) -> Self {
        Self {
            timestamp_ns,
            open,
            high,
            low,
            close,
            volume,
            funding_rate: 0.0001,
            spread_bps: 2.0,
        }
    }

    /// Invariant: High >= max(Open, Close) and Low <= min(Open, Close) and Low > 0.
    pub fn is_valid(&self) -> bool {
        self.open > 0.0
            && self.close > 0.0
            && self.high >= self.open.max(self.close) * (1.0 - 1e-9)
            && self.low <= self.open.min(self.close) * (1.0 + 1e-9)
            && self.low > 0.0
            && self.volume >= 0.0
    }
}

/// Cryptographic receipt for a single-asset generated market world.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorldReceipt {
    pub world_id: String,
    pub spec: WorldSpec,
    pub bars: Vec<WorldBar>,
    pub world_digest: String,
}

impl WorldReceipt {
    pub fn new(spec: WorldSpec, bars: Vec<WorldBar>) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(spec.symbol.as_bytes());
        hasher.update(&spec.seed.to_le_bytes());
        hasher.update(&(bars.len() as u64).to_le_bytes());
        for b in &bars {
            hasher.update(&b.timestamp_ns.to_le_bytes());
            hasher.update(&b.close.to_le_bytes());
        }
        let digest = format!("{:x}", hasher.finalize());
        let world_id = format!("world-{}-{}", &digest[..12], spec.seed);

        Self {
            world_id,
            spec,
            bars,
            world_digest: digest,
        }
    }
}

/// Multi-asset synchronized candle snapshot across quad universe.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MultiAssetBarSnapshot {
    pub timestamp_ns: i64,
    pub asset_bars: BTreeMap<String, WorldBar>,
    pub cross_asset_correlation: f64,
}

/// Cryptographic receipt for a multi-asset synchronized market world.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MultiAssetWorldReceipt {
    pub world_id: String,
    pub spec: WorldSpec,
    pub symbols: Vec<String>,
    pub snapshots: Vec<MultiAssetBarSnapshot>,
    pub world_digest: String,
}

impl MultiAssetWorldReceipt {
    pub fn new(spec: WorldSpec, symbols: Vec<String>, snapshots: Vec<MultiAssetBarSnapshot>) -> Self {
        let mut hasher = Sha256::new();
        for sym in &symbols {
            hasher.update(sym.as_bytes());
        }
        hasher.update(&spec.seed.to_le_bytes());
        hasher.update(&(snapshots.len() as u64).to_le_bytes());
        for s in &snapshots {
            hasher.update(&s.timestamp_ns.to_le_bytes());
            for (sym, b) in &s.asset_bars {
                hasher.update(sym.as_bytes());
                hasher.update(&b.close.to_le_bytes());
            }
        }
        let digest = format!("{:x}", hasher.finalize());
        let world_id = format!("multi-world-{}-{}", &digest[..12], spec.seed);

        Self {
            world_id,
            spec,
            symbols,
            snapshots,
            world_digest: digest,
        }
    }

    pub fn extract_single_asset(&self, symbol: &str) -> Option<Vec<WorldBar>> {
        let mut result = Vec::with_capacity(self.snapshots.len());
        for snap in &self.snapshots {
            if let Some(bar) = snap.asset_bars.get(symbol) {
                result.push(bar.clone());
            } else {
                return None;
            }
        }
        Some(result)
    }
}
