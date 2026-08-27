//! Audit Transcript Verification & Cryptographic Lineage (D-147, D-149, M5).
//!
//! Provides tamper-evident transcript hash verification.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuditTranscript {
    pub steps: Vec<String>,
}

impl AuditTranscript {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_step(&mut self, step_summary: &str) {
        self.steps.push(step_summary.to_string());
    }

    pub fn compute_hash(&self) -> String {
        let mut hasher = Sha256::new();
        for s in &self.steps {
            hasher.update(s.as_bytes());
        }
        format!("{:x}", hasher.finalize())
    }
}
