//! Production RNG abstraction (V8.6 M11, ANA-A5).
//!
//! Provides versioned, deterministic random stream primitives backed by
//! the standard `rand` crate (ChaCha8/StdRng) for active simulation/testing,
//! while isolating CPython MT19937 parity to historical verification shims.

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

/// Production RNG wrapper using a versioned deterministic standard engine.
pub struct ProductionRng {
    rng: StdRng,
    seed: u64,
}

impl ProductionRng {
    /// Create a new ProductionRng from a 64-bit seed.
    pub fn from_seed(seed: u64) -> Self {
        Self {
            rng: StdRng::seed_from_u64(seed),
            seed,
        }
    }

    /// Return the seed used to construct this stream.
    pub fn seed(&self) -> u64 {
        self.seed
    }

    /// Draw a uniform f64 in [0.0, 1.0).
    pub fn gen_f64(&mut self) -> f64 {
        self.rng.gen_range(0.0..1.0)
    }

    /// Draw a uniform usize in [0, n).
    pub fn gen_index(&mut self, n: usize) -> usize {
        assert!(n > 0, "n must be positive");
        self.rng.gen_range(0..n)
    }

    /// Draw a standard normal random variable using Box-Muller.
    pub fn gen_standard_normal(&mut self) -> f64 {
        let u1 = self.gen_f64().max(1e-15);
        let u2 = self.gen_f64();
        (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
    }
}
