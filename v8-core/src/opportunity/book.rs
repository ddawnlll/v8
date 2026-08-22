//! Point-In-Time Causal Opportunity Episode & Canonical Opportunity Book (Issue #231, #233, D-130).
//!
//! Owning Authority: V8 Constitution Rules 4, 18, 19, 23.
//!
//! Epistemic Invariant:
//!   Market creates the Opportunity first; Observers merely witness and attach evidence subsequently.
//!   Opportunity identity is strictly Expert-independent.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::error::V8CoreError;
use crate::hash::Canon;
use super::exposure::EconomicExposureStructure;

/// Status of the opportunity boundary definition.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum IdentityStatus {
    Canonical,
    Ambiguous,
    Unknown,
    Falsified,
}

/// Canonical Opportunity Episode (Primitive 3 of 7).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OpportunityEpisode {
    pub episode_id: String,
    pub exposure: EconomicExposureStructure,
    pub as_of_time: i64,
    pub valid_until: i64,
    pub expected_horizon_bars: usize,
    pub identity_status: IdentityStatus,
    pub market_state_hash: String,
    pub lineage_hash: String,
}

impl OpportunityEpisode {
    /// Constructs and fingerprints an OpportunityEpisode.
    pub fn new(
        exposure: EconomicExposureStructure,
        as_of_time: i64,
        valid_until: i64,
        expected_horizon_bars: usize,
        identity_status: IdentityStatus,
        market_state_hash: impl Into<String>,
        lineage_hash: impl Into<String>,
    ) -> Result<Self, V8CoreError> {
        if valid_until < as_of_time {
            return Err(V8CoreError::OpportunityIdentityError {
                episode_id: "UNINITIALIZED".to_string(),
                reason: format!("valid_until ({valid_until}) cannot precede as_of_time ({as_of_time})"),
            });
        }
        let market_state_hash = market_state_hash.into();
        let lineage_hash = lineage_hash.into();

        let mut episode = Self {
            episode_id: String::new(),
            exposure,
            as_of_time,
            valid_until,
            expected_horizon_bars,
            identity_status,
            market_state_hash,
            lineage_hash,
        };
        episode.episode_id = episode.compute_id();
        Ok(episode)
    }

    /// Computes cryptographic BLAKE3 identity for this opportunity episode.
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("OpportunityEpisode");
        c.push_str(&self.exposure.exposure_id);
        c.push_i64(self.as_of_time);
        c.push_i64(self.valid_until);
        c.push_u64(self.expected_horizon_bars as u64);
        c.push_str(&format!("{:?}", self.identity_status));
        c.push_str(&self.market_state_hash);
        c.push_str(&self.lineage_hash);
        c.finish_blake3_hex()
    }
}

/// Canonical Opportunity Book holding Expert-independent opportunity episodes.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct OpportunityBook {
    episodes: Vec<OpportunityEpisode>,
    by_id: HashMap<String, usize>,
}

impl OpportunityBook {
    pub fn new() -> Self {
        Self::default()
    }

    /// Inserts a new opportunity episode into the book.
    pub fn insert(&mut self, episode: OpportunityEpisode) -> Result<(), V8CoreError> {
        if self.by_id.contains_key(&episode.episode_id) {
            // Already present — idempotently skip or return error
            return Ok(());
        }
        let idx = self.episodes.len();
        self.by_id.insert(episode.episode_id.clone(), idx);
        self.episodes.push(episode);
        Ok(())
    }

    /// Retrieves an episode by its BLAKE3 episode_id.
    pub fn get(&self, episode_id: &str) -> Option<&OpportunityEpisode> {
        let idx = *self.by_id.get(episode_id)?;
        self.episodes.get(idx)
    }

    /// Returns all episodes active at the specified timestamp.
    pub fn active_at(&self, timestamp: i64) -> Vec<&OpportunityEpisode> {
        self.episodes
            .iter()
            .filter(|ep| ep.as_of_time <= timestamp && timestamp <= ep.valid_until)
            .collect()
    }

    /// Returns all episodes.
    pub fn all(&self) -> &[OpportunityEpisode] {
        &self.episodes
    }

    pub fn len(&self) -> usize {
        self.episodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.episodes.is_empty()
    }
}
