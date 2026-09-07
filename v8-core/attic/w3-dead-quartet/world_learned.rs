//! Learned / Neural Challenger Generator Interface (D-147, M2b).
//!
//! Optional challenger generator stub. Disabled by default to preserve strict analytical reproducibility.

pub struct LearnedChallengerGenerator;

impl LearnedChallengerGenerator {
    pub fn is_enabled() -> bool {
        false
    }
}
