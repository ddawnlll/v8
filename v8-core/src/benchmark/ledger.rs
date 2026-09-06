//! Append-only Benchmark Ledger (D-153 Section 112).
//!
//! Stores benchmark run records with monotonic sequence indexing and verification.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use crate::benchmark::receipt::BenchmarkReceipt;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkLedgerEntry {
    pub sequence_number: u64,
    pub previous_hash: String,
    pub receipt: BenchmarkReceipt,
    pub entry_hash: String,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkLedger {
    pub entries: Vec<BenchmarkLedgerEntry>,
}

impl BenchmarkLedger {
    pub fn new() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn append(&mut self, receipt: BenchmarkReceipt) -> &BenchmarkLedgerEntry {
        let seq = self.entries.len() as u64;
        let prev_hash = self.entries.last().map(|e| e.entry_hash.clone()).unwrap_or_else(|| "0".repeat(64));
        
        let mut hasher = Sha256::new();
        hasher.update(&seq.to_le_bytes());
        hasher.update(prev_hash.as_bytes());
        hasher.update(receipt.receipt_digest.as_bytes());
        let entry_hash = format!("{:x}", hasher.finalize());

        let entry = BenchmarkLedgerEntry {
            sequence_number: seq,
            previous_hash: prev_hash,
            receipt,
            entry_hash,
        };
        self.entries.push(entry);
        self.entries.last().unwrap()
    }

    pub fn verify_integrity(&self) -> Result<(), String> {
        let mut expected_prev = "0".repeat(64);
        for (i, entry) in self.entries.iter().enumerate() {
            if entry.sequence_number != i as u64 {
                return Err(format!("Invalid sequence at index {}: got {}", i, entry.sequence_number));
            }
            if entry.previous_hash != expected_prev {
                return Err(format!("Hash mismatch at index {}: prev_hash {} != expected {}", i, entry.previous_hash, expected_prev));
            }
            let mut hasher = Sha256::new();
            hasher.update(&entry.sequence_number.to_le_bytes());
            hasher.update(entry.previous_hash.as_bytes());
            hasher.update(entry.receipt.receipt_digest.as_bytes());
            let computed = format!("{:x}", hasher.finalize());
            if entry.entry_hash != computed {
                return Err(format!("Corrupted entry_hash at index {}: {} != {}", i, entry.entry_hash, computed));
            }
            expected_prev = entry.entry_hash.clone();
        }
        Ok(())
    }
}
