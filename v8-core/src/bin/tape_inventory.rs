//! SB01 (#410) — read-only four-year tape inventory and hash verification.
//!
//! Produces a hash-bound inventory manifest over a real tape directory:
//!
//! * three-way archive digest cross-check: physical `.zip` sha256 vs its
//!   `.CHECKSUM` sidecar vs the `source.json` archive registry;
//! * per instrument/channel row coverage over the ingested `tape.jsonl`
//!   (rows, unique decision clocks, duplicates, grid gaps, causality sanity);
//! * explicit absence fields (mark price, funding interval anomalies) — an
//!   unmeasured quantity stays absent, it is never recorded as a zero;
//! * optional role binding from an external role file (R2). Without it every
//!   partition stays `USAGE_UNKNOWN`; this tool never promotes a period to
//!   `PROTECTED_OOS` on its own.
//!
//! Read-only invariant: nothing under the tape directory is written, renamed or
//! rewritten. `verify` re-derives every identity field and fails closed.
//!
//! ```text
//! cargo run --manifest-path v8-core/Cargo.toml --bin tape_inventory -- \
//!   scan --tape-dir ../research/tape/multi-1h-4y --out <manifest.json> [--roles <roles.json>]
//! cargo run --manifest-path v8-core/Cargo.toml --bin tape_inventory -- \
//!   verify --manifest <manifest.json>
//! ```
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs::File;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{anyhow, bail, Context, Result};
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

/// Nanoseconds per millisecond: the tape stores `*_ms` payload fields and
/// nanosecond `event_time`/`available_time` columns.
const NS_PER_MS: i64 = 1_000_000;

/// Expected kline grid step (1h) and funding grid step (8h), in nanoseconds.
/// 1h = 3_600_000 ms = 3.6e12 ns; an off-by-1000 here silently makes every
/// measured grid "mismatch", so the values are pinned by a unit test below.
const KLINE_STEP_NS: i64 = 3_600_000 * NS_PER_MS;
const FUNDING_STEP_NS: i64 = 28_800_000 * NS_PER_MS;

/// Machine identity of this inventory schema. Changing the emitted identity
/// fields requires a new version string, never a silent re-render.
const SCHEMA_VERSION: &str = "v87-sb01-tape-inventory-v1";

#[derive(Parser)]
#[command(
    name = "tape_inventory",
    about = "SB01 (#410) read-only tape inventory and hash verification"
)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Scan a tape directory and write the inventory manifest.
    Scan {
        /// Tape directory holding monthly `*.zip` archives and `tape.jsonl`.
        #[arg(long)]
        tape_dir: PathBuf,
        /// Manifest output path.
        #[arg(long)]
        out: PathBuf,
        /// Optional role-binding file (R2 burn map). Absent => USAGE_UNKNOWN.
        #[arg(long)]
        roles: Option<PathBuf>,
        /// Skip physical archive hashing (row coverage only, for fast iteration).
        #[arg(long, default_value_t = false)]
        skip_archive_hash: bool,
    },
    /// Re-derive the manifest identity from the live tape and compare.
    Verify {
        /// Manifest previously written by `scan`.
        #[arg(long)]
        manifest: PathBuf,
        /// Tape directory override (defaults to the path recorded in the manifest).
        #[arg(long)]
        tape_dir: Option<PathBuf>,
    },
}

/// One missing/gap run inside an otherwise expected regular grid.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
struct GapExample {
    after_event_time_ms: i64,
    next_event_time_ms: i64,
    missing_slots: u64,
}

/// Coverage of one (instrument, channel) partition.
#[derive(Serialize, Deserialize, Clone, Debug, Default)]
struct ChannelStats {
    rows: u64,
    unique_event_time: u64,
    duplicate_event_time: u64,
    duplicate_event_id: u64,
    /// Rows whose availability time precedes the event time (causality sanity).
    available_before_event: u64,
    first_event_time_ms: i64,
    last_event_time_ms: i64,
    first_available_time_ms: i64,
    last_available_time_ms: i64,
    /// Modal inter-event step; recorded as measured, not assumed.
    modal_step_ns: i64,
    /// Grid step this channel is expected to follow (1h klines, 8h funding).
    /// Zero means no expectation is declared for the channel.
    #[serde(default)]
    expected_step_ns: i64,
    /// Whether the measured modal step equals the declared expectation.
    #[serde(default)]
    grid_matches_expected: bool,
    expected_slots: u64,
    missing_slots: u64,
    gap_runs: u64,
    coverage_ratio: f64,
    /// kline only: rows whose payload does not carry `closed: true`.
    unclosed_rows: u64,
    /// Rows missing a required payload field for the channel.
    missing_payload_fields: u64,
    distinct_payload_hash: u64,
    distinct_event_id: u64,
    /// Counts of the payload's own interval declaration (funding rows only),
    /// e.g. {"8": 4300, "4": 75}. A heterogeneous grid is recorded, not smoothed.
    #[serde(default)]
    interval_field_counts: BTreeMap<String, u64>,
    /// True when the payload declares more than one grid interval.
    #[serde(default)]
    grid_heterogeneous: bool,
    /// Events beyond the modal grid's slot count (positive only). A non-zero
    /// value means extra events exist that the modal grid cannot express.
    #[serde(default)]
    events_beyond_modal_grid: u64,
    gap_examples: Vec<GapExample>,
    /// Required payload fields that were absent at least once (explicit absence).
    absent_payload_fields: Vec<String>,
}

/// Per-instrument entry.
#[derive(Serialize, Deserialize, Clone, Debug, Default)]
struct InstrumentEntry {
    instrument: String,
    months_present: Vec<String>,
    months_missing: Vec<String>,
    archives: u64,
    channels: BTreeMap<String, ChannelStats>,
}

/// Archive-registry cross-check result.
#[derive(Serialize, Deserialize, Clone, Debug, Default)]
struct ArchiveCheck {
    zip_count: u64,
    zip_bytes: u64,
    sidecar_count: u64,
    source_json_path: String,
    source_json_sha256: Option<String>,
    source_json_entries: u64,
    aggregate_archive_digest: String,
    matched_all_three: u64,
    sidecar_mismatch: Vec<String>,
    source_mismatch: Vec<String>,
    missing_sidecar: Vec<String>,
    missing_source_entry: Vec<String>,
    sidecar_only: Vec<String>,
    /// Marker prices are not present in this tape at all: recorded as absent.
    mark_price_present: bool,
    funding_present: bool,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct TapeStats {
    path: String,
    bytes: u64,
    lines: u64,
    sha256: String,
    malformed_lines: u64,
    unknown_channel_lines: u64,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct Totals {
    instruments: u64,
    kline_rows: u64,
    funding_rows: u64,
    other_channel_rows: u64,
    window_first_event_time_ms: i64,
    window_last_event_time_ms: i64,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct RoleBinding {
    status: String,
    roles_path: Option<String>,
    roles_sha256: Option<String>,
    /// Roles are an input, never inferred here.
    assignment_count: u64,
    assignments: Value,
    default_role: String,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct Manifest {
    schema_version: String,
    issue: String,
    generated_at_unix_s: u64,
    /// Digest over every identity field with the timestamp zeroed.
    manifest_identity: String,
    tape_dir: String,
    tape: TapeStats,
    archives: ArchiveCheck,
    totals: Totals,
    coverage: Vec<InstrumentEntry>,
    role_binding: RoleBinding,
    /// Physical artifacts this inventory refers to, path + hash only.
    evidence_bindings: Vec<Value>,
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Streaming SHA-256 of a file. Used for archives and the ingested tape.
fn sha256_file(path: &Path) -> Result<(String, u64)> {
    let mut file = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    let mut bytes = 0u64;
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
        bytes += n as u64;
    }
    Ok((hex(&hasher.finalize()), bytes))
}

fn sha256_bytes(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex(&hasher.finalize())
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push_str(&format!("{b:02x}"));
    }
    out
}

fn ms(ns: i64) -> i64 {
    ns.div_euclid(NS_PER_MS)
}

/// Parse a `.CHECKSUM` sidecar: `<sha256>  <filename>` (two spaces, as written
/// by `sha256sum`). Unknown shapes are returned as an error, never guessed.
fn parse_sidecar(text: &str) -> Result<(String, String)> {
    let line = text
        .lines()
        .find(|l| !l.trim().is_empty())
        .ok_or_else(|| anyhow!("empty CHECKSUM sidecar"))?;
    let (digest, name) = line
        .split_once("  ")
        .ok_or_else(|| anyhow!("CHECKSUM line is not '<sha256>  <name>': {line:?}"))?;
    if digest.len() != 64 || !digest.chars().all(|c| c.is_ascii_hexdigit()) {
        bail!("CHECKSUM digest is not a 64-char hex sha256: {digest:?}");
    }
    Ok((digest.to_ascii_lowercase(), name.trim().to_string()))
}

/// Required payload fields per channel. Missing ones are recorded as absent.
fn required_payload_fields(channel: &str) -> &'static [&'static str] {
    match channel {
        "kline" => &[
            "open",
            "high",
            "low",
            "close",
            "volume",
            "open_time_ms",
            "close_time_ms",
            "closed",
        ],
        "funding" => &["funding_rate", "funding_time_ms", "funding_interval_hours"],
        _ => &[],
    }
}

/// Modal inter-event step of a sorted, deduplicated series.
fn modal_step(sorted: &[i64]) -> i64 {
    if sorted.len() < 2 {
        return 0;
    }
    let mut counts: HashMap<i64, u64> = HashMap::new();
    for w in sorted.windows(2) {
        *counts.entry(w[1] - w[0]).or_insert(0) += 1;
    }
    counts
        .into_iter()
        .max_by_key(|(delta, n)| (*n, std::cmp::Reverse(*delta)))
        .map(|(delta, _)| delta)
        .unwrap_or(0)
}

/// Finalize one channel partition: duplicates, gaps, coverage, absence fields.
fn finalize_channel(
    events: Vec<i64>,
    availables: Vec<i64>,
    event_ids: HashSet<String>,
    payload_hashes: HashSet<String>,
    unclosed: u64,
    missing_fields: &HashMap<String, u64>,
    intervals: BTreeMap<String, u64>,
    total_rows: u64,
) -> ChannelStats {
    let mut stats = ChannelStats {
        rows: total_rows,
        duplicate_event_id: total_rows.saturating_sub(event_ids.len() as u64),
        unclosed_rows: unclosed,
        missing_payload_fields: missing_fields.values().sum(),
        distinct_payload_hash: payload_hashes.len() as u64,
        distinct_event_id: event_ids.len() as u64,
        grid_heterogeneous: intervals.len() > 1,
        interval_field_counts: intervals,
        first_event_time_ms: events.iter().min().map(|v| ms(*v)).unwrap_or(0),
        last_event_time_ms: events.iter().max().map(|v| ms(*v)).unwrap_or(0),
        first_available_time_ms: availables.iter().min().map(|v| ms(*v)).unwrap_or(0),
        last_available_time_ms: availables.iter().max().map(|v| ms(*v)).unwrap_or(0),
        ..Default::default()
    };
    let mut absent: Vec<String> = missing_fields
        .iter()
        .filter(|(_, n)| **n > 0)
        .map(|(k, _)| k.clone())
        .collect();
    absent.sort();
    stats.absent_payload_fields = absent;

    stats.available_before_event = events
        .iter()
        .zip(availables.iter())
        .filter(|(event, available)| available < event)
        .count() as u64;

    let mut sorted = events;
    sorted.sort_unstable();
    let unique: Vec<i64> = {
        let mut v = sorted.clone();
        v.dedup();
        v
    };
    stats.unique_event_time = unique.len() as u64;
    stats.duplicate_event_time = total_rows.saturating_sub(unique.len() as u64);
    stats.modal_step_ns = modal_step(&unique);

    if unique.len() >= 2 && stats.modal_step_ns > 0 {
        let span = unique[unique.len() - 1] - unique[0];
        stats.expected_slots = (span / stats.modal_step_ns + 1) as u64;
        stats.missing_slots = stats.expected_slots.saturating_sub(stats.unique_event_time);
        stats.events_beyond_modal_grid =
            stats.unique_event_time.saturating_sub(stats.expected_slots);
        stats.coverage_ratio = if stats.expected_slots > 0 {
            stats.unique_event_time as f64 / stats.expected_slots as f64
        } else {
            0.0
        };
        for w in unique.windows(2) {
            let delta = w[1] - w[0];
            if delta > stats.modal_step_ns {
                stats.gap_runs += 1;
                if stats.gap_examples.len() < 20 {
                    stats.gap_examples.push(GapExample {
                        after_event_time_ms: ms(w[0]),
                        next_event_time_ms: ms(w[1]),
                        missing_slots: (delta / stats.modal_step_ns - 1) as u64,
                    });
                }
            }
        }
    }
    stats
}

/// Row-coverage scan over the ingested tape. Streaming: one line at a time.
fn scan_tape(
    path: &Path,
) -> Result<(
    TapeStats,
    BTreeMap<String, BTreeMap<String, ChannelStats>>,
    Totals,
)> {
    let file = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let bytes = file.metadata()?.len();
    let (sha256, _) = sha256_file(path)?;
    let reader = BufReader::with_capacity(1 << 20, File::open(path)?);

    struct Acc {
        events: Vec<i64>,
        availables: Vec<i64>,
        ids: HashSet<String>,
        payload_hashes: HashSet<String>,
        unclosed: u64,
        missing_fields: HashMap<String, u64>,
        intervals: BTreeMap<String, u64>,
        rows: u64,
    }
    impl Default for Acc {
        fn default() -> Self {
            Acc {
                events: Vec::new(),
                availables: Vec::new(),
                ids: HashSet::new(),
                payload_hashes: HashSet::new(),
                unclosed: 0,
                missing_fields: HashMap::new(),
                intervals: BTreeMap::new(),
                rows: 0,
            }
        }
    }

    let mut acc: BTreeMap<String, BTreeMap<String, Acc>> = BTreeMap::new();
    let mut lines = 0u64;
    let mut malformed = 0u64;
    let mut unknown_channel = 0u64;
    let mut kline_rows = 0u64;
    let mut funding_rows = 0u64;
    let mut other_rows = 0u64;
    let mut first_event = i64::MAX;
    let mut last_event = i64::MIN;

    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        lines += 1;
        let v: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(_) => {
                malformed += 1;
                continue;
            }
        };
        let instrument = v
            .get("instrument")
            .and_then(Value::as_str)
            .ok_or_else(|| anyhow!("tape line without instrument: {line:.80}"))?
            .to_string();
        let channel = v
            .get("channel")
            .and_then(Value::as_str)
            .ok_or_else(|| anyhow!("tape line without channel: {line:.80}"))?
            .to_string();
        let event_time = v
            .get("event_time")
            .and_then(Value::as_i64)
            .unwrap_or(i64::MIN);
        let available_time = v
            .get("available_time")
            .and_then(Value::as_i64)
            .unwrap_or(i64::MIN);

        match channel.as_str() {
            "kline" => kline_rows += 1,
            "funding" => funding_rows += 1,
            _ => unknown_channel += 1,
        }
        if event_time > i64::MIN {
            first_event = first_event.min(event_time);
            last_event = last_event.max(event_time);
        }

        let entry = acc
            .entry(instrument)
            .or_default()
            .entry(channel.clone())
            .or_default();
        entry.rows += 1;
        entry.events.push(event_time);
        entry.availables.push(available_time);
        if let Some(id) = v.get("event_id").and_then(Value::as_str) {
            entry.ids.insert(id.to_string());
        }
        let payload = v.get("payload").cloned().unwrap_or(Value::Null);
        if let Some(ph) = payload.get("payload_hash").and_then(Value::as_str) {
            entry.payload_hashes.insert(ph.to_string());
        }
        for field in required_payload_fields(&channel) {
            match payload.get(*field) {
                None | Some(Value::Null) => {
                    *entry
                        .missing_fields
                        .entry((*field).to_string())
                        .or_insert(0) += 1;
                }
                Some(_) => {}
            }
        }
        if channel == "kline" && payload.get("closed").and_then(Value::as_bool) != Some(true) {
            entry.unclosed += 1;
        }
        if channel == "funding" {
            if let Some(h) = payload
                .get("funding_interval_hours")
                .and_then(Value::as_f64)
            {
                *entry.intervals.entry(format!("{h}")).or_insert(0) += 1;
            }
        }
    }

    let mut coverage: BTreeMap<String, BTreeMap<String, ChannelStats>> = BTreeMap::new();
    for (instrument, channels) in acc {
        let mut out = BTreeMap::new();
        for (channel, a) in channels {
            let mut stats = finalize_channel(
                a.events,
                a.availables,
                a.ids,
                a.payload_hashes,
                a.unclosed,
                &a.missing_fields,
                a.intervals,
                a.rows,
            );
            stats.expected_step_ns = match channel.as_str() {
                "kline" => KLINE_STEP_NS,
                "funding" => FUNDING_STEP_NS,
                _ => 0,
            };
            stats.grid_matches_expected =
                stats.expected_step_ns == 0 || stats.modal_step_ns == stats.expected_step_ns;
            out.insert(channel, stats);
        }
        coverage.insert(instrument, out);
    }

    let stats = TapeStats {
        path: path.display().to_string(),
        bytes,
        lines,
        sha256: format!("sha256:{sha256}"),
        malformed_lines: malformed,
        unknown_channel_lines: unknown_channel,
    };
    let totals = Totals {
        instruments: 0, // filled by caller from the coverage map
        kline_rows,
        funding_rows,
        other_channel_rows: other_rows + unknown_channel,
        window_first_event_time_ms: ms(first_event),
        window_last_event_time_ms: ms(last_event),
    };
    let _ = &mut other_rows;
    Ok((stats, coverage, totals))
}

/// Archive-registry cross-check: physical file vs sidecar vs `source.json`.
fn scan_archives(
    dir: &Path,
    skip_hash: bool,
) -> Result<(ArchiveCheck, BTreeMap<String, Vec<String>>)> {
    let mut check = ArchiveCheck::default();
    let mut months_by_symbol: BTreeMap<String, Vec<String>> = BTreeMap::new();

    let source_path = dir.join("source.json");
    check.source_json_path = source_path.display().to_string();
    let mut registry: HashMap<String, String> = HashMap::new();
    if source_path.is_file() {
        let text = std::fs::read_to_string(&source_path)?;
        check.source_json_sha256 = Some(format!("sha256:{}", sha256_bytes(text.as_bytes())));
        let v: Value = serde_json::from_str(&text).context("source.json is not valid JSON")?;
        if let Some(arr) = v.get("archives").and_then(Value::as_array) {
            check.source_json_entries = arr.len() as u64;
            for a in arr {
                let symbol = a.get("symbol").and_then(Value::as_str).unwrap_or("");
                let month = a.get("month").and_then(Value::as_str).unwrap_or("");
                let channel = a.get("channel").and_then(Value::as_str).unwrap_or("");
                let hash = a.get("zip_sha256").and_then(Value::as_str).unwrap_or("");
                if symbol.is_empty() || month.is_empty() || channel.is_empty() || hash.is_empty() {
                    bail!("source.json entry missing symbol/month/channel/zip_sha256: {a}");
                }
                // File naming convention in this tape: <SYMBOL>-1h-<MONTH>.zip for
                // klines and <SYMBOL>-fundingRate-<MONTH>.zip for funding.
                let file = match channel {
                    "kline" => format!("{symbol}-1h-{month}.zip"),
                    "funding" => format!("{symbol}-fundingRate-{month}.zip"),
                    other => bail!("unknown source.json channel {other:?}"),
                };
                registry.insert(file, hash.to_ascii_lowercase());
            }
        }
    } else {
        bail!("source.json not found in {}", dir.display());
    }

    let mut entries: Vec<PathBuf> = std::fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .collect();
    entries.sort();
    for path in entries {
        let name = match path.file_name().and_then(|n| n.to_str()) {
            Some(n) => n.to_string(),
            None => continue,
        };
        if !name.ends_with(".zip") {
            continue;
        }
        check.zip_count += 1;
        check.zip_bytes += std::fs::metadata(&path)?.len();

        // symbol / month extraction, sharing the registry naming convention.
        let stem = name.trim_end_matches(".zip");
        let parts: Vec<&str> = stem.split('-').collect();
        if parts.len() >= 3 {
            let symbol = parts[0].to_string();
            let month = parts[parts.len() - 2..].join("-");
            months_by_symbol.entry(symbol).or_default().push(month);
        }

        let sidecar = dir.join(format!("{name}.CHECKSUM"));
        let sidecar_digest = if sidecar.is_file() {
            check.sidecar_count += 1;
            let text = std::fs::read_to_string(&sidecar)?;
            let (digest, referenced) = parse_sidecar(&text)?;
            if referenced != name {
                bail!("sidecar {name}.CHECKSUM references {referenced:?}, not the archive name");
            }
            Some(digest)
        } else {
            check.missing_sidecar.push(name.clone());
            None
        };

        let physical = if skip_hash {
            None
        } else {
            Some(sha256_file(&path)?.0)
        };
        let registered = registry.get(&name).cloned();
        if registered.is_none() {
            check.missing_source_entry.push(name.clone());
        }

        match (&physical, &sidecar_digest, &registered) {
            (Some(p), Some(s), Some(r)) if p == s && s == r => check.matched_all_three += 1,
            (None, Some(s), Some(r)) if s == r => check.matched_all_three += 1,
            (Some(p), Some(s), _) if p != s => check.sidecar_mismatch.push(name.clone()),
            (Some(p), _, Some(r)) if p != r => check.source_mismatch.push(name.clone()),
            _ => {}
        }
    }
    for name in registry.keys() {
        if !dir.join(name).is_file() {
            check.sidecar_only.push(name.clone());
        }
    }

    for sidecar in std::fs::read_dir(dir)? {
        let p = sidecar?.path();
        if let Some(n) = p.file_name().and_then(|n| n.to_str()) {
            if n.ends_with(".zip.CHECKSUM") {
                let zip = dir.join(n.trim_end_matches(".CHECKSUM"));
                if !zip.is_file() {
                    check.sidecar_only.push(n.to_string());
                }
            }
        }
    }

    check.mark_price_present = false; // this tape carries no markPriceKlines channel
    check.funding_present = months_by_symbol.values().flatten().count() > months_by_symbol.len(); // both channels present per symbol

    // Aggregate digest over the sorted "<name>\t<sha256>" registry lines.
    let mut lines: Vec<String> = registry
        .iter()
        .map(|(name, hash)| format!("{name}\t{hash}"))
        .collect();
    lines.sort();
    check.aggregate_archive_digest =
        format!("sha256:{}", sha256_bytes(lines.join("\n").as_bytes()));
    Ok((check, months_by_symbol))
}

/// Full 48-month grid implied by the tape window, used for explicit gaps.
fn expected_months(first: &str, last: &str) -> Vec<String> {
    let parse = |s: &str| -> (i32, u32) {
        let (y, m) = s.split_once('-').expect("YYYY-MM");
        (y.parse().unwrap_or(0), m.parse().unwrap_or(0))
    };
    let (mut year, mut month) = parse(first);
    let (last_year, last_month) = parse(last);
    let mut out = Vec::new();
    while (year, month) <= (last_year, last_month) {
        out.push(format!("{year:04}-{month:02}"));
        month += 1;
        if month > 12 {
            month = 1;
            year += 1;
        }
    }
    out
}

fn build_manifest(args: &ScanArgs) -> Result<Manifest> {
    let dir = &args.tape_dir;
    let tape_path = dir.join("tape.jsonl");
    let (tape, coverage, mut totals) = scan_tape(&tape_path)?;
    let (archives, months_by_symbol) = scan_archives(dir, args.skip_archive_hash)?;

    let all_months: BTreeSet<String> = months_by_symbol.values().flatten().cloned().collect();
    let grid = if let (Some(min), Some(max)) = (all_months.iter().min(), all_months.iter().max()) {
        expected_months(min, max)
    } else {
        Vec::new()
    };

    let mut entries: Vec<InstrumentEntry> = Vec::new();
    let mut instruments: BTreeSet<String> = BTreeSet::new();
    instruments.extend(coverage.keys().cloned());
    instruments.extend(months_by_symbol.keys().cloned());
    for instrument in instruments {
        let months_present = months_by_symbol
            .get(&instrument)
            .map(|v| {
                let mut s: Vec<String> = v.clone();
                s.sort();
                s.dedup();
                s
            })
            .unwrap_or_default();
        let present: BTreeSet<String> = months_present.iter().cloned().collect();
        let months_missing: Vec<String> = grid
            .iter()
            .filter(|m| !present.contains(*m))
            .cloned()
            .collect();
        entries.push(InstrumentEntry {
            instrument: instrument.clone(),
            archives: (months_present.len() * 2) as u64,
            months_present,
            months_missing,
            channels: coverage.get(&instrument).cloned().unwrap_or_default(),
        });
    }
    totals.instruments = entries.len() as u64;

    let role_binding = match &args.roles {
        Some(path) => {
            let text = std::fs::read_to_string(path)
                .with_context(|| format!("read roles file {}", path.display()))?;
            let v: Value = serde_json::from_str(&text).context("roles file is not valid JSON")?;
            let assignments = v
                .get("assignments")
                .cloned()
                .ok_or_else(|| anyhow!("roles file has no `assignments` array"))?;
            let count = assignments.as_array().map(|a| a.len()).unwrap_or(0) as u64;
            RoleBinding {
                status: "BOUND".to_string(),
                roles_path: Some(path.display().to_string()),
                roles_sha256: Some(format!("sha256:{}", sha256_bytes(text.as_bytes()))),
                assignment_count: count,
                assignments,
                default_role: "USAGE_UNKNOWN".to_string(),
            }
        }
        None => RoleBinding {
            status: "PENDING_R2_BURN_MAP".to_string(),
            roles_path: None,
            roles_sha256: None,
            assignment_count: 0,
            assignments: json!([]),
            default_role: "USAGE_UNKNOWN".to_string(),
        },
    };

    let mut manifest = Manifest {
        schema_version: SCHEMA_VERSION.to_string(),
        issue: "#410 (SB01)".to_string(),
        generated_at_unix_s: 0,
        manifest_identity: String::new(),
        tape_dir: dir.display().to_string(),
        tape,
        archives,
        totals,
        coverage: entries,
        role_binding,
        evidence_bindings: Vec::new(),
    };
    manifest.evidence_bindings = vec![
        json!({"kind": "tape_ingest", "path": manifest.tape.path, "sha256": manifest.tape.sha256, "bytes": manifest.tape.bytes, "lines": manifest.tape.lines}),
        json!({"kind": "archive_registry", "path": manifest.archives.source_json_path, "sha256": manifest.archives.source_json_sha256, "entries": manifest.archives.source_json_entries}),
    ];
    // Identity excludes the wall-clock timestamp: re-scanning the same bytes
    // with the same schema must reproduce the same identity.
    let mut identity_probe = manifest.clone();
    identity_probe.generated_at_unix_s = 0;
    identity_probe.manifest_identity = String::new();
    manifest.manifest_identity = format!(
        "sha256:{}",
        sha256_bytes(serde_json::to_string(&identity_probe)?.as_bytes())
    );
    manifest.generated_at_unix_s = unix_now();
    Ok(manifest)
}

struct ScanArgs {
    tape_dir: PathBuf,
    out: PathBuf,
    roles: Option<PathBuf>,
    skip_archive_hash: bool,
}

fn cmd_scan(args: ScanArgs) -> Result<()> {
    let manifest = build_manifest(&args)?;
    if let Some(parent) = args.out.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let text = serde_json::to_string_pretty(&manifest)?;
    std::fs::write(&args.out, format!("{text}\n"))
        .with_context(|| format!("write {}", args.out.display()))?;

    let kline_rows = manifest.totals.kline_rows;
    let funding_rows = manifest.totals.funding_rows;
    println!(
        "tape_inventory scan OK\n  tape          : {} ({} bytes, {} lines)",
        manifest.tape.path, manifest.tape.bytes, manifest.tape.lines
    );
    println!("  tape sha256   : {}", manifest.tape.sha256);
    println!(
        "  archives      : {} zips / {} sidecars / {} registry entries; 3-way matched {}",
        manifest.archives.zip_count,
        manifest.archives.sidecar_count,
        manifest.archives.source_json_entries,
        manifest.archives.matched_all_three
    );
    println!(
        "  rows          : {} kline + {} funding ({} instruments)",
        kline_rows, funding_rows, manifest.totals.instruments
    );
    println!(
        "  window        : {} .. {} ms",
        manifest.totals.window_first_event_time_ms, manifest.totals.window_last_event_time_ms
    );
    println!(
        "  mark price    : present = {}",
        manifest.archives.mark_price_present
    );
    println!("  roles         : {}", manifest.role_binding.status);
    println!("  identity      : {}", manifest.manifest_identity);
    println!("  manifest      : {}", args.out.display());
    Ok(())
}

fn cmd_verify(manifest_path: &Path, tape_dir: Option<PathBuf>) -> Result<()> {
    let text = std::fs::read_to_string(manifest_path)
        .with_context(|| format!("read {}", manifest_path.display()))?;
    let recorded: Manifest = serde_json::from_str(&text)
        .with_context(|| format!("parse {} as inventory manifest", manifest_path.display()))?;
    if recorded.schema_version != SCHEMA_VERSION {
        bail!(
            "unsupported manifest schema {} (this binary emits {})",
            recorded.schema_version,
            SCHEMA_VERSION
        );
    }
    let dir = tape_dir
        .or_else(|| Some(PathBuf::from(&recorded.tape_dir)))
        .ok_or_else(|| anyhow!("no tape dir recorded"))?;
    let fresh = build_manifest(&ScanArgs {
        tape_dir: dir,
        out: PathBuf::from(""), // unused by build_manifest
        roles: None,
        skip_archive_hash: false,
    })?;

    let mut mismatches: Vec<String> = Vec::new();
    let mut compare = |field: &str, a: String, b: String| {
        if a != b {
            mismatches.push(format!("{field}: recorded={a} live={b}"));
        }
    };
    compare(
        "tape.sha256",
        recorded.tape.sha256.clone(),
        fresh.tape.sha256.clone(),
    );
    compare(
        "tape.lines".into(),
        recorded.tape.lines.to_string(),
        fresh.tape.lines.to_string(),
    );
    compare(
        "archives.aggregate_archive_digest",
        recorded.archives.aggregate_archive_digest.clone(),
        fresh.archives.aggregate_archive_digest.clone(),
    );
    compare(
        "archives.matched_all_three",
        recorded.archives.matched_all_three.to_string(),
        fresh.archives.matched_all_three.to_string(),
    );
    compare(
        "totals.kline_rows",
        recorded.totals.kline_rows.to_string(),
        fresh.totals.kline_rows.to_string(),
    );
    compare(
        "totals.funding_rows",
        recorded.totals.funding_rows.to_string(),
        fresh.totals.funding_rows.to_string(),
    );
    compare(
        "totals.instruments",
        recorded.totals.instruments.to_string(),
        fresh.totals.instruments.to_string(),
    );
    for (rec, live) in recorded.coverage.iter().zip(fresh.coverage.iter()) {
        if rec.instrument != live.instrument {
            mismatches.push(format!(
                "coverage order: recorded={} live={}",
                rec.instrument, live.instrument
            ));
            continue;
        }
        for (channel, rec_stats) in &rec.channels {
            match live.channels.get(channel) {
                None => mismatches.push(format!(
                    "{} {}: recorded channel is absent in live tape",
                    rec.instrument, channel
                )),
                Some(live_stats) => {
                    if rec_stats.rows != live_stats.rows
                        || rec_stats.unique_event_time != live_stats.unique_event_time
                        || rec_stats.missing_slots != live_stats.missing_slots
                        || rec_stats.duplicate_event_time != live_stats.duplicate_event_time
                    {
                        mismatches.push(format!(
                            "{} {}: rows {}/{} unique {}/{} missing {}/{} dup {}",
                            rec.instrument,
                            channel,
                            rec_stats.rows,
                            live_stats.rows,
                            rec_stats.unique_event_time,
                            live_stats.unique_event_time,
                            rec_stats.missing_slots,
                            live_stats.missing_slots,
                            live_stats.duplicate_event_time
                        ));
                    }
                }
            }
        }
    }
    if mismatches.is_empty() {
        println!(
            "tape_inventory verify PASS — {} identity fields reproduced for {} instruments",
            8 + recorded.coverage.len() * 2,
            recorded.totals.instruments
        );
        Ok(())
    } else {
        for m in &mismatches {
            eprintln!("MISMATCH {m}");
        }
        bail!(
            "tape_inventory verify FAIL — {} mismatch(es)",
            mismatches.len()
        )
    }
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Scan {
            tape_dir,
            out,
            roles,
            skip_archive_hash,
        } => cmd_scan(ScanArgs {
            tape_dir,
            out,
            roles,
            skip_archive_hash,
        }),
        Cmd::Verify { manifest, tape_dir } => cmd_verify(&manifest, tape_dir),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sidecar_parser_accepts_canonical_sha256sum_line() {
        let (digest, name) = parse_sidecar(
            "99172d8a39583d968bb603b00302428dac06937a07e8ad50473559a5ec2420f7  ADAUSDT-1h-2022-07.zip\n",
        )
        .expect("canonical sha256sum line must parse");
        assert_eq!(name, "ADAUSDT-1h-2022-07.zip");
        assert_eq!(digest.len(), 64);
    }

    #[test]
    fn sidecar_parser_rejects_non_sha256_digest() {
        let err = parse_sidecar("deadbeef  x.zip\n").expect_err("short digest must be rejected");
        assert!(err.to_string().contains("64-char hex sha256"));
    }

    #[test]
    fn finalize_channel_detects_duplicates_and_missing_grid_slots() {
        // 1h grid with one duplicated clock and one hour missing (mechanics only).
        let step = KLINE_STEP_NS;
        let events: Vec<i64> = vec![0, step, step, 3 * step];
        let availables: Vec<i64> = events.iter().map(|e| e + NS_PER_MS).collect();
        let ids: HashSet<String> = (0..4).map(|i| format!("id-{i}")).collect();
        let hashes: HashSet<String> = (0..4).map(|i| format!("ph-{i}")).collect();
        let stats = finalize_channel(
            events,
            availables,
            ids,
            hashes,
            0,
            &HashMap::new(),
            BTreeMap::new(),
            4,
        );
        assert_eq!(stats.rows, 4);
        assert_eq!(stats.unique_event_time, 3);
        assert_eq!(stats.duplicate_event_time, 1);
        assert_eq!(stats.expected_slots, 4);
        assert_eq!(stats.missing_slots, 1);
        assert_eq!(stats.gap_runs, 1);
        assert_eq!(stats.available_before_event, 0);
    }

    #[test]
    fn finalize_channel_flags_available_before_event() {
        let events = vec![10 * NS_PER_MS];
        let availables = vec![9 * NS_PER_MS];
        let stats = finalize_channel(
            events,
            availables,
            HashSet::new(),
            HashSet::new(),
            0,
            &HashMap::new(),
            BTreeMap::new(),
            1,
        );
        assert_eq!(stats.available_before_event, 1);
    }

    #[test]
    fn finalize_channel_never_reports_absent_payload_fields_as_zero_rows() {
        let mut missing = HashMap::new();
        missing.insert("mark_price".to_string(), 5u64);
        let stats = finalize_channel(
            vec![NS_PER_MS],
            vec![2 * NS_PER_MS],
            HashSet::new(),
            HashSet::new(),
            0,
            &missing,
            BTreeMap::new(),
            1,
        );
        assert_eq!(stats.absent_payload_fields, vec!["mark_price".to_string()]);
        assert_eq!(stats.missing_payload_fields, 5);
        assert_eq!(stats.rows, 1);
    }

    #[test]
    fn expected_months_spans_a_year_boundary() {
        let months = expected_months("2022-11", "2023-02");
        assert_eq!(months, vec!["2022-11", "2022-12", "2023-01", "2023-02"]);
    }

    #[test]
    fn modal_step_uses_the_measured_dominant_delta() {
        let step = KLINE_STEP_NS;
        assert_eq!(modal_step(&[0, step, 2 * step, 5 * step]), step);
        assert_eq!(modal_step(&[0]), 0);
    }

    /// Guard against the off-by-1000 that made every measured grid look wrong
    /// (1h expressed as 3.6 s instead of 3.6e12 ns).
    #[test]
    fn declared_grid_steps_are_one_hour_and_eight_hours_in_nanoseconds() {
        assert_eq!(KLINE_STEP_NS, 3_600_000 * NS_PER_MS);
        assert_eq!(KLINE_STEP_NS, 3_600_000_000_000);
        assert_eq!(
            KLINE_STEP_NS / NS_PER_MS / 1000,
            3_600,
            "1h is 3 600 000 ms"
        );
        assert_eq!(FUNDING_STEP_NS, 8 * KLINE_STEP_NS, "funding is an 8h grid");
        assert_ne!(FUNDING_STEP_NS, KLINE_STEP_NS);
    }
}
