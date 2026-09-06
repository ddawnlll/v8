//! Append-only Benchmark Ledger (D-153 §112; self-verification per #328).
//!
//! Stores benchmark run records with monotonic sequence indexing, disk
//! persistence, and cryptographic chain verification. Enforces BFS-020
//! (append-only invariance).
//!
//! # What the chain actually binds
//!
//! Before #328 each row was sealed as
//! `sha256(seq ‖ prev_hash ‖ receipt.receipt_digest)`. That commits to a string
//! the receipt itself chose, and to nothing else. Combined with the pre-#328
//! receipt digest (which omitted the whole gate vector), a persisted ledger row
//! could be rewritten to flip `g1_causal_pit` from `Defeated` to `Pass`, its
//! `receipt_digest` field updated to the digest of the tampered contents, and
//! the chain still "verified" — because the chain never looked at the contents.
//!
//! [`BenchmarkLedger::entry_seal`] now folds the receipt's **full canonical
//! encoding** into the row seal, so a chain check pins every byte of every
//! recorded receipt, and [`BenchmarkLedger::audit`] recomputes each receipt's own
//! digest from those contents instead of trusting the stored value (issue R2).
//!
//! # Legacy rows
//!
//! Seven rows in `.audit/benchmark/ledger.jsonl` predate this binding. They are
//! *not* rewritten: rewriting history is precisely what BFS-020 forbids, and it
//! would destroy the only record of what the old code claimed. They are verified
//! under the generation that sealed them ([`BenchmarkLedger::legacy_entry_seal`])
//! and reported separately as **unbound**, which is a weaker statement than
//! "verified" and is never upgraded into authority. See the `OPEN_PIN` on
//! [`LedgerAuditReport::legacy_bound_entries`].
//!
//! # What this does NOT protect against
//!
//! A self-consistent **whole-file rewrite** cannot be detected by any purely
//! in-file check, and this one does not pretend otherwise: an attacker holding
//! the file can rewrite a suffix of rows into the legacy generation and recompute
//! a chain that audits clean. [`LedgerTamper::GenerationRegression`] raises the
//! cost (a downgrade is only survivable in a suffix that no v2 row precedes) but
//! it is not a proof.
//!
//! A narrower consequence, measured rather than reasoned about: editing a
//! *legacy* row's gate vector while leaving its `receipt_digest` string untouched
//! is NOT reported as tampering, because the legacy seal binds only that string
//! and the legacy digest never included the gate vector. That is the pre-#328
//! defect, visible in historical data and not retroactively fixable without
//! rewriting history. The mitigation is deniability rather than detection: such a
//! row yields `verified_entries == 0` and `is_fully_bound() == false`, so it can
//! grant nothing. Asserted in
//! `tests/d153_receipt_ledger_selfverify.rs::legacy_row_content_edit_is_unbound_
//! not_detected`, so the boundary is a tested contract and not a hope.
//!
//! What closes the gap is not more hashing inside the file: it is refusing to let
//! a not-fully-bound ledger carry authority. [`LedgerAuditReport::is_fully_bound`]
//! is the gate every authority-carrying consumer must consult, so the worst
//! outcome of a downgrade rewrite is *zero* authority rather than *forged*
//! authority. Anchoring a signed ledger head outside the file is the follow-up
//! that would make even that rewrite detectable; it is recorded as an `OPEN_PIN`
//! rather than invented here (D-153 non-goal: no new identity mechanism without a
//! decision).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

use crate::benchmark::receipt::{BenchmarkReceipt, ReceiptVerificationError};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkLedgerEntry {
    pub sequence_number: u64,
    pub previous_hash: String,
    pub receipt: BenchmarkReceipt,
    pub entry_hash: String,
}

/// A single classification of ledger corruption. Codes are stable because the
/// CLI and any findings ledger report them verbatim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LedgerTamper {
    /// `sequence_number` is not the row index.
    SequenceDiscontinuity { index: usize, got: u64 },
    /// `previous_hash` does not chain to the preceding row's seal.
    ChainBreak { index: usize },
    /// `entry_hash` does not equal the recomputed seal for this row.
    SealMismatch { index: usize, expected: String },
    /// The embedded receipt is not self-consistent.
    Receipt { index: usize, error: ReceiptVerificationError },
    /// A legacy-sealed row appears at or after a v2 row. The only ways that
    /// happens are an out-of-order append or a downgrade edit of the tail, and a
    /// downgraded row escapes the seal that binds full contents. So this is a
    /// hard finding, not a formatting curiosity.
    GenerationRegression { index: usize },
}

impl LedgerTamper {
    /// Stable machine-readable code, e.g. `LEDGER_SEAL_MISMATCH`.
    pub fn code(&self) -> &'static str {
        match self {
            Self::SequenceDiscontinuity { .. } => "LEDGER_SEQUENCE_DISCONTINUITY",
            Self::ChainBreak { .. } => "LEDGER_CHAIN_BREAK",
            Self::SealMismatch { .. } => "LEDGER_SEAL_MISMATCH",
            Self::Receipt { .. } => "LEDGER_RECEIPT_UNVERIFIED",
            Self::GenerationRegression { .. } => "LEDGER_GENERATION_REGRESSION",
        }
    }

    pub fn index(&self) -> usize {
        match self {
            Self::SequenceDiscontinuity { index, .. }
            | Self::ChainBreak { index }
            | Self::SealMismatch { index, .. }
            | Self::Receipt { index, .. }
            | Self::GenerationRegression { index } => *index,
        }
    }
}

impl std::fmt::Display for LedgerTamper {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::SequenceDiscontinuity { index, got } => write!(
                f,
                "{} at index {index}: sequence_number is {got}, expected {index}",
                self.code()
            ),
            Self::ChainBreak { index } => write!(f, "{} at index {index}", self.code()),
            Self::SealMismatch { index, expected } => write!(
                f,
                "{} at index {index}: entry_hash is not the recomputed seal (expected {expected})",
                self.code()
            ),
            Self::Receipt { index, error } => {
                write!(f, "{} at index {index}: {error}", self.code())
            }
            Self::GenerationRegression { index } => write!(
                f,
                "{} at index {index}: a legacy row follows a fully-bound row; history is \
                 append-only and cannot regress to a weaker seal (BFS-020)",
                self.code()
            ),
        }
    }
}

impl std::error::Error for LedgerTamper {}

/// The outcome of auditing a ledger.
///
/// Separates two things that must never be conflated: rows the chain can vouch
/// for, and old-format rows that predate the binding and are therefore
/// *unbound* rather than *innocent*.
///
/// Not `Serialize`: [`LedgerTamper`] carries error enums owned by two other
/// modules, and inventing JSON shapes for them is not part of any contract.
/// Consumers print [`LedgerAuditReport::findings`] or read the counters.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LedgerAuditReport {
    /// Total rows in the ledger.
    pub total_entries: usize,
    /// Rows whose seal, chain link and receipt digest all recompute, at the
    /// current digest generation.
    pub verified_entries: usize,
    /// Rows sealed under the pre-#328 generation.
    ///
    /// OPEN_PIN (#328 §16 "backward compatibility conflicts with tamper
    /// detection"): these rows' digests cannot be recomputed by the current
    /// encoder, and re-sealing them in place would be a BFS-020 history
    /// overwrite. They are therefore counted, reported, and refused by every
    /// authority-carrying consumer, but they are not deleted and not flagged as
    /// tampering. Whether the historical rows must be re-derived from an
    /// archived authority or formally deprecated is a governance decision for
    /// the ledger spec owner, not something this fix should silently make.
    pub legacy_bound_entries: usize,
    /// Rows whose receipt declares at least one artifact binding.
    pub receipts_with_artifacts: usize,
    /// Every classification found. Non-empty means the ledger failed the audit.
    pub tamper: Vec<LedgerTamper>,
}

impl LedgerAuditReport {
    pub fn is_clean(&self) -> bool {
        self.tamper.is_empty()
    }

    /// True when every row is fully bound at the current generation and clean.
    /// Authority-carrying consumers must use this, not [`Self::is_clean`].
    pub fn is_fully_bound(&self) -> bool {
        self.is_clean() && self.legacy_bound_entries == 0
    }

    /// One line per finding, for CLI and report output.
    pub fn findings(&self) -> Vec<String> {
        self.tamper.iter().map(|t| t.to_string()).collect()
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkLedger {
    pub entries: Vec<BenchmarkLedgerEntry>,
}

/// Genesis value for the chain's first `previous_hash`.
const GENESIS: &str = "0";

/// Domain separator for the v2 row seal, so a v1 and v2 seal over the same row
/// can never coincide.
const ENTRY_SEAL_VERSION: &[u8] = b"v8.d153.ledger.entry.v2";

impl BenchmarkLedger {
    pub fn new() -> Self {
        Self { entries: Vec::new() }
    }

    /// The pre-#328 row seal: `sha256(seq ‖ prev ‖ receipt_digest_string)`.
    ///
    /// Retained for **verification only**, so the rows already persisted under
    /// this formula stay auditable. Reproduced independently against all seven
    /// rows of `.audit/benchmark/ledger.jsonl` before being kept. Never used to
    /// seal a new row, and a row sealed this way can never carry authority.
    pub fn legacy_entry_seal(
        sequence_number: u64,
        previous_hash: &str,
        receipt: &BenchmarkReceipt,
    ) -> String {
        let mut hasher = Sha256::new();
        hasher.update(&sequence_number.to_le_bytes());
        hasher.update(previous_hash.as_bytes());
        hasher.update(receipt.receipt_digest.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    /// The v2 row seal.
    ///
    /// Binds the sequence number, the previous seal, and the **complete canonical
    /// encoding** of the receipt — which itself covers the receipt's recomputed
    /// digest, its full gate vector, every observation and domain result, all
    /// provenance, and every artifact binding. No field can be edited without
    /// breaking the chain.
    pub fn entry_seal(
        sequence_number: u64,
        previous_hash: &str,
        receipt: &BenchmarkReceipt,
    ) -> String {
        let mut hasher = Sha256::new();
        hasher.update(ENTRY_SEAL_VERSION);
        hasher.update(&sequence_number.to_le_bytes());
        hasher.update(previous_hash.as_bytes());
        match receipt.canonical_encoding() {
            Ok(bytes) => hasher.update(&bytes),
            // A receipt that cannot be canonically encoded is still sealable,
            // but the seal commits to *that fact* rather than to nothing.
            Err(error) => hasher.update(format!("UNENCODABLE:{error}").as_bytes()),
        }
        format!("{:x}", hasher.finalize())
    }

    /// The seal appropriate to a row's generation. Legacy receipts keep the
    /// legacy seal so persisted history remains checkable.
    fn seal_for_row(sequence_number: u64, previous_hash: &str, receipt: &BenchmarkReceipt) -> String {
        if receipt.is_legacy_bound() {
            Self::legacy_entry_seal(sequence_number, previous_hash, receipt)
        } else {
            Self::entry_seal(sequence_number, previous_hash, receipt)
        }
    }

    /// Append a receipt, sealing it under the generation its digest declares.
    ///
    /// The row is sealed with [`Self::entry_seal`] unless the receipt is legacy,
    /// in which case [`Self::legacy_entry_seal`] keeps the row checkable. A
    /// receipt constructed by [`BenchmarkReceipt::generate_with_context`] always
    /// declares the current generation, so a legacy row can only ever enter
    /// through deserialization of pre-#328 data.
    pub fn append(&mut self, receipt: BenchmarkReceipt) -> &BenchmarkLedgerEntry {
        let seq = self.entries.len() as u64;
        let prev_hash = self
            .entries
            .last()
            .map(|e| e.entry_hash.clone())
            .unwrap_or_else(|| GENESIS.repeat(64));
        let entry_hash = Self::seal_for_row(seq, &prev_hash, &receipt);

        let entry = BenchmarkLedgerEntry {
            sequence_number: seq,
            previous_hash: prev_hash,
            receipt,
            entry_hash,
        };
        self.entries.push(entry);
        self.entries.last().unwrap()
    }

    /// Verify the whole chain, collecting every classification found.
    ///
    /// Per row: monotonic sequence, chaining to the previous seal, `entry_hash`
    /// equals the recomputed seal, and the embedded receipt is self-consistent.
    /// Legacy rows are checked against the legacy seal and reported through
    /// [`LedgerAuditReport::legacy_bound_entries`] rather than being trusted or
    /// condemned.
    pub fn audit(&self) -> LedgerAuditReport {
        let mut report = LedgerAuditReport {
            total_entries: self.entries.len(),
            ..Default::default()
        };
        let mut expected_prev = GENESIS.repeat(64);
        let mut saw_current_generation = false;

        for (i, entry) in self.entries.iter().enumerate() {
            if entry.sequence_number != i as u64 {
                report.tamper.push(LedgerTamper::SequenceDiscontinuity {
                    index: i,
                    got: entry.sequence_number,
                });
                // With a broken sequence the expected chaining value from here
                // is unknowable, so continue from what is on disk: one bad row
                // must not mask every downstream problem.
                expected_prev = entry.entry_hash.clone();
                continue;
            }
            if entry.previous_hash != expected_prev {
                report.tamper.push(LedgerTamper::ChainBreak { index: i });
            }

            let legacy = entry.receipt.is_legacy_bound();
            if legacy && saw_current_generation {
                report.tamper.push(LedgerTamper::GenerationRegression { index: i });
            }
            saw_current_generation |= !legacy;

            let computed =
                Self::seal_for_row(entry.sequence_number, &entry.previous_hash, &entry.receipt);
            if entry.entry_hash != computed {
                report.tamper.push(LedgerTamper::SealMismatch {
                    index: i,
                    expected: computed,
                });
            }

            if legacy {
                report.legacy_bound_entries += 1;
            } else {
                match entry.receipt.verify() {
                    Ok(()) => report.verified_entries += 1,
                    Err(error) => report.tamper.push(LedgerTamper::Receipt { index: i, error }),
                }

                // Physical artifact check (Rule 5). A bound file that exists and
                // disagrees is a hard finding; a bound file merely absent from
                // this machine is an environment condition — the digest still
                // carries the claim, so only a warning is emitted.
                match entry.receipt.verify_artifacts() {
                    Ok(()) => {}
                    Err(ReceiptVerificationError::Artifact(e)) if e.is_missing_file() => {
                        tracing::warn!(
                            target: "benchmark::ledger",
                            "ledger row {i}: bound artifact absent, cannot verify against disk ({e})"
                        );
                    }
                    Err(error) => report.tamper.push(LedgerTamper::Receipt { index: i, error }),
                }
                if !entry.receipt.artifacts.is_empty() {
                    report.receipts_with_artifacts += 1;
                }
            }

            expected_prev = entry.entry_hash.clone();
        }

        report
    }

    /// Back-compatible integrity gate: `Ok(())` only when the audit found no
    /// tamper. Legacy rows do not fail this gate (they predate the binding and
    /// are still sealed correctly for their generation) but they never satisfy
    /// [`LedgerAuditReport::is_fully_bound`].
    pub fn verify_integrity(&self) -> Result<(), String> {
        match self.audit().tamper.first() {
            Some(t) => Err(format!("{t} (BFS-020)")),
            None => Ok(()),
        }
    }

    /// Append an entry and persist it to an append-only JSONL file.
    ///
    /// Sealing and writing are one critical section and the write is flushed, so
    /// a row cannot exist on disk that the in-memory chain does not account for.
    pub fn append_and_persist(
        &mut self,
        path: &Path,
        receipt: BenchmarkReceipt,
    ) -> Result<&BenchmarkLedgerEntry, String> {
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        let entry = self.append(receipt).clone();
        let line = serde_json::to_string(&entry)
            .map_err(|e| format!("Serialization failed: {e}"))?;

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|e| format!("Failed to open benchmark ledger file {path:?}: {e}"))?;

        writeln!(file, "{line}").map_err(|e| format!("Failed to write ledger entry: {e}"))?;
        file.flush()
            .map_err(|e| format!("Failed to flush ledger entry: {e}"))?;

        Ok(self.entries.last().unwrap())
    }

    /// Load a ledger from disk and verify it, failing closed on any finding.
    pub fn load_from_disk(path: &Path) -> Result<Self, String> {
        let (ledger, report) = Self::load_with_report(path)?;
        match report.tamper.first() {
            Some(t) => Err(format!("{t} (BFS-020)")),
            None => Ok(ledger),
        }
    }

    /// Load a ledger and return both it and the audit report.
    ///
    /// `Err` only for I/O and parse failures; content problems surface through
    /// [`LedgerAuditReport`] so a caller can print every finding rather than only
    /// the first.
    pub fn load_with_report(path: &Path) -> Result<(Self, LedgerAuditReport), String> {
        if !path.exists() {
            return Ok((Self::new(), LedgerAuditReport::default()));
        }

        let file =
            File::open(path).map_err(|e| format!("Failed to open ledger at {path:?}: {e}"))?;
        let reader = BufReader::new(file);
        let mut ledger = Self::new();

        for (line_num, line_res) in reader.lines().enumerate() {
            let line = line_res.map_err(|e| format!("Read error at line {line_num}: {e}"))?;
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            let entry: BenchmarkLedgerEntry = serde_json::from_str(trimmed).map_err(|e| {
                format!("JSON parse error at line {line_num}: {e} (BFS-020: ledger is append-only)")
            })?;
            ledger.entries.push(entry);
        }

        let report = ledger.audit();
        Ok((ledger, report))
    }
}
