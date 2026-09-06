//! Append-only Benchmark Ledger (D-153 §112).
//!
//! Stores benchmark run records with monotonic sequence indexing, disk persistence,
//! and cryptographic hash chain verification. Enforces BFS-020 (append-only invariance).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;
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

    /// Verifies cryptographic integrity of the ledger chain
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
                return Err(format!("Corrupted entry_hash at index {}: {} != {} (BFS-020)", i, entry.entry_hash, computed));
            }
            expected_prev = entry.entry_hash.clone();
        }
        Ok(())
    }

    /// Appends entry and persists to an append-only JSONL file on disk
    pub fn append_and_persist(&mut self, path: &Path, receipt: BenchmarkReceipt) -> Result<&BenchmarkLedgerEntry, String> {
        let entry = self.append(receipt).clone();

        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|e| format!("Failed to open benchmark ledger file {:?}: {e}", path))?;

        let line = serde_json::to_string(&entry)
            .map_err(|e| format!("Serialization failed: {e}"))?;

        writeln!(file, "{line}")
            .map_err(|e| format!("Failed to write ledger entry: {e}"))?;

        Ok(self.entries.last().unwrap())
    }

    /// Loads existing ledger from disk and verifies integrity
    pub fn load_from_disk(path: &Path) -> Result<Self, String> {
        if !path.exists() {
            return Ok(Self::new());
        }

        let file = File::open(path)
            .map_err(|e| format!("Failed to open ledger at {:?}: {e}", path))?;
        let reader = BufReader::new(file);
        let mut ledger = Self::new();

        for (line_num, line_res) in reader.lines().enumerate() {
            let line = line_res.map_err(|e| format!("Read error at line {line_num}: {e}"))?;
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            let entry: BenchmarkLedgerEntry = serde_json::from_str(trimmed)
                .map_err(|e| format!("JSON parse error at line {line_num}: {e}"))?;
            ledger.entries.push(entry);
        }

        ledger.verify_integrity()?;
        Ok(ledger)
    }
}
