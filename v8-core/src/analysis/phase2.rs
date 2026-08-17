//! S6 Phase 2 — systematicity discovery (issue #119; D-072;
//! RECOVERABLE_REGRET_PROTOCOL §4).
//!
//! Port of `tools/regret_phase2.py` (frozen oracle, FCR-V8RR-007). The oracle
//! reuses `src/v8/statistics.py` in full — zero new estimator code — and this
//! port mirrors that constraint: the six statistics helpers below
//! (`select_block_size`, `bootstrap_ci`, `effective_independent_episodes`,
//! `practical_significance`, `expected_false_positives`,
//! `effective_search_size`) are value-level ports of the frozen Python
//! functions, not re-derivations.
//!
//! Declared family: 72 slices (3 Experts x 6 symbols x 2 directions x 2
//! estimands), scored on a chronological discovery half. Any
//! `CANDIDATE_SYSTEMATIC` slice is queried against the untouched confirmation
//! half **exactly once** — `ConfirmationLedger` refuses a second query of the
//! same slice (FCR-V8RR-007 AP002; protocol §8.4 makes it a hard error, not a
//! warning).
//!
//! Parity: the bootstrap RNG is `crate::mt19937` (bit-exact CPython
//! `random.Random`), every `sum(...)` is `crate::state::fsum` (CPython
//! `sum()` is `math.fsum`), `x ** 2` / `n ** (1/3)` are libm `pow` (`.powf`,
//! D-053 locked finding), and `round()` is Python banker's rounding. The
//! per-slice seed is `int(sha1_hex(slice_key)[:8], 16)` where `sha1_hex` hashes
//! the JSON-encoded key (surrounding quotes included).

use std::collections::HashSet;

use sha1::{Digest, Sha1};

use crate::mt19937::MT19937;
use crate::state::fsum;

// --- FCR-V8RR-007 frozen constants (verbatim mirror of regret_phase2.py) ----

pub const EXPERTS: [&str; 3] = [
    "trend_pullback",
    "failed_breakout",
    "liquidity_sweep_reclaim",
]; // FT003
pub const SYMBOLS: [&str; 6] = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
]; // FT003
pub const DIRECTIONS: [&str; 2] = ["LONG", "SHORT"]; // FT003
pub const ESTIMANDS: [&str; 2] = ["mean_legal_hindsight_gap", "mean_actual_vs_no_trade"]; // FT001

pub const MIN_N_COMPUTED: usize = 30; // FT003 minimum support
pub const MIN_EFFECTIVE_EPISODES: f64 = 8.0; // FT003 minimum support
pub const N_RESAMPLES: usize = 2000; // FT004
pub const CI: f64 = 0.90; // FT004
pub const ALPHA_FAMILY: f64 = 0.05; // FT005 (pre-correction)
pub const MIN_NET_R: f64 = 0.05; // FT007 materiality floor
pub const MIN_TRADES_MATERIALITY: usize = 30; // FT007 — same bar as MIN_N_COMPUTED

pub const DISCOVERY_VERDICTS: [&str; 5] = [
    "CANDIDATE_SYSTEMATIC",
    "INSUFFICIENT_SUPPORT",
    "EXCLUDED_EMPTY",
    "NOT_MATERIAL",
    "NOT_SIGNIFICANT",
];
#[allow(dead_code)]
pub const CONFIRMATION_VERDICTS: [&str; 2] = ["SYSTEMATIC_FINDING", "FAILED_CONFIRMATION"];

/// One Phase-1 dataset row projected onto the fields Phase 2 reads. The
/// oracle consumes `tools.regret_phase1`'s frozen join output; the field set
/// is exactly what `regret_phase2.py` indexes (`expert_id`, `symbol`,
/// `direction`, `gap_status`, the two estimand series, `horizon_bars`).
#[derive(Debug, Clone)]
pub struct SliceRow {
    pub expert_id: String,
    pub symbol: String,
    pub direction: String,
    pub gap_status: String, // "COMPUTED" | "REJECTED" | ...
    pub legal_hindsight_gap: Option<f64>,
    pub actual_utility: Option<f64>,
    pub horizon_bars: Option<i64>,
}

/// Mirror of the oracle's frozen `SliceResult` dataclass — every field, in
/// order, with the same None-vs-Some meaning (discovery scoring leaves the
/// confirmation fields `None`).
#[derive(Debug, Clone)]
pub struct SliceResult {
    pub slice_key: String,
    pub expert_id: String,
    pub symbol: String,
    pub direction: String,
    pub estimand: String,
    pub n_total_in_slice: usize,
    pub n_computed: usize,
    pub effective_independent_episodes: f64,
    pub mean: Option<f64>,
    pub ci_lower: Option<f64>,
    pub ci_upper: Option<f64>,
    pub block_size: Option<usize>,
    pub alpha_slate: f64,
    pub practically_significant: Option<bool>,
    pub materiality_note: String,
    pub discovery_verdict: String,
    pub confirmation_verdict: Option<String>,
}

/// The confirmation-half answer for one candidate slice (FT006).
#[derive(Debug, Clone)]
pub struct ConfirmationResult {
    pub slice_key: String,
    pub confirmation_verdict: String,
    pub confirmation_mean: Option<f64>,
    pub confirmation_ci_lower: Option<f64>,
    pub confirmation_ci_upper: Option<f64>,
    pub confirmation_n_computed: usize,
}

/// The discovery summary the oracle writes to `discovery_summary.json`.
#[derive(Debug, Clone)]
pub struct DiscoverySummary {
    pub n_slices_declared: usize,
    pub discovery_verdict_distribution: Vec<(String, usize)>,
    pub n_candidate_systematic: usize,
    pub expected_false_positives_at_family_alpha: f64,
    pub alpha_slate_bonferroni: f64,
    pub candidate_systematic_slices: Vec<String>,
}

// --- statistics.py ports (zero new estimator code, D-072) -------------------

/// Python `round()` — banker's rounding (half to even). `n ** (1/3)` is
/// positive here, so negatives are not part of the contract.
fn round_half_even(x: f64) -> f64 {
    debug_assert!(x >= 0.0);
    let fl = x.floor();
    let frac = x - fl;
    if frac < 0.5 {
        fl
    } else if frac > 0.5 {
        fl + 1.0
    } else if fl % 2.0 == 0.0 {
        fl
    } else {
        fl + 1.0
    }
}

/// `select_block_size` — two tiers selected by the lag-1 autocorrelation of
/// episode net_R; base `round(n**(1/3))`, doubled when `|lag1| > threshold`,
/// capped at `n // 2` (the cap that keeps the circular sampler non-degenerate).
fn select_block_size(episode_net_r: &[f64], threshold: f64) -> usize {
    let n = episode_net_r.len();
    if n < 4 {
        return 1;
    }
    let mean = fsum(episode_net_r) / n as f64;
    let sq: Vec<f64> = episode_net_r.iter().map(|x| (x - mean).powf(2.0)).collect();
    let c0 = fsum(&sq);
    let base = (round_half_even((n as f64).powf(1.0 / 3.0)) as usize).max(1);
    if c0 == 0.0 {
        return base.min(n / 2).max(1);
    }
    let c1 = fsum(
        &(0..n - 1)
            .map(|i| (episode_net_r[i] - mean) * (episode_net_r[i + 1] - mean))
            .collect::<Vec<_>>(),
    );
    let lag1 = c1 / c0;
    let block = if lag1.abs() > threshold {
        2 * base
    } else {
        base
    };
    block.min(n / 2).max(1)
}

/// One circular fixed-block bootstrap draw of length n over [0, n): repeatedly
/// picks a uniform start and appends a contiguous run of `block_size` indices
/// (wrapping past the end) until length n, then truncates. Fail-closed on the
/// degenerate `block_size >= n` draw (D-052) exactly as the oracle raises.
fn block_bootstrap_indices(n: usize, block_size: usize, rng: &mut MT19937) -> Vec<usize> {
    assert!(n > 0, "block bootstrap on an empty series");
    assert!(block_size > 0, "block_size must be positive");
    assert!(
        !(n >= 2 && block_size >= n),
        "block_size {block_size} >= n {n}: degenerate block bootstrap (every \
         resample is a rotation of the whole series)"
    );
    let mut out = Vec::with_capacity(n);
    while out.len() < n {
        let start = rng.randrange(n as u64) as usize;
        for j in 0..block_size {
            out.push((start + j) % n);
        }
    }
    out.truncate(n);
    out
}

/// `block_bootstrap_means` — one rng from `seed` drives every resample; each
/// mean is `sum(selected)/n` with `sum()` = `fsum`.
fn block_bootstrap_means(
    net_rs: &[f64],
    block_size: usize,
    n_resamples: usize,
    seed: u64,
) -> Vec<f64> {
    let n = net_rs.len();
    if n == 0 {
        return Vec::new();
    }
    let mut rng = MT19937::new(seed);
    let mut means = Vec::with_capacity(n_resamples);
    let mut selected = Vec::with_capacity(n);
    for _ in 0..n_resamples {
        let idx = block_bootstrap_indices(n, block_size, &mut rng);
        selected.clear();
        for &i in &idx {
            selected.push(net_rs[i]);
        }
        means.push(fsum(&selected) / n as f64);
    }
    means
}

/// `bootstrap_ci` — percentile CI on mean episode net_R. `tail` is
/// `int(n_resamples * (1-ci) / 2)` computed in f64 and truncated, so with
/// `N_RESAMPLES=2000, CI=0.90` it is 99, not 100 (2000*(1-0.90) rounds to
/// 199.999... / 2 = 99.999... -> 99). Sort is stable like CPython's, using
/// IEEE `==` semantics where `-0.0` and `0.0` compare equal.
fn bootstrap_ci(
    net_r_series: &[f64],
    block_size: usize,
    n_resamples: usize,
    seed: u64,
    ci: f64,
) -> (f64, f64) {
    assert!((0.0..1.0).contains(&ci), "ci must be in (0, 1)");
    let mut means = block_bootstrap_means(net_r_series, block_size, n_resamples, seed);
    if means.is_empty() {
        return (0.0, 0.0);
    }
    means.sort_by(|a, b| a.partial_cmp(b).expect("bootstrap mean must be finite"));
    let tail = (n_resamples as f64 * (1.0 - ci) / 2.0) as usize;
    (means[tail], means[means.len() - tail - 1])
}

/// `effective_independent_episodes` — `n / max_hold_bars`, the conservative
/// upper bound on independent observations under overlapping holds.
fn effective_independent_episodes(n_episodes: usize, max_hold_bars: usize) -> f64 {
    if n_episodes == 0 {
        return 0.0;
    }
    debug_assert!(max_hold_bars > 0);
    n_episodes as f64 / max_hold_bars as f64
}

/// `practical_significance` — economic-magnitude gate `mean >= min_net_r`
/// AND coverage gate `n >= min_trades`, with the auditable note string.
fn practical_significance(net_r: &[f64], min_net_r: f64, min_trades: usize) -> (bool, String) {
    let n = net_r.len();
    let mean = if n > 0 { fsum(net_r) / n as f64 } else { 0.0 };
    let meets = n >= min_trades && mean >= min_net_r;
    let note = format!(
        "mean net_R {mean:.4} vs economic floor {min_net_r} ({}); \
         episodes {n} vs minimum coverage {min_trades} ({})",
        if mean >= min_net_r { "meets" } else { "below" },
        if n >= min_trades { "meets" } else { "below" },
    );
    (meets, note)
}

/// `expected_false_positives` — N rules at alpha -> N*alpha.
fn expected_false_positives(n_rules: usize, alpha: f64) -> f64 {
    n_rules as f64 * alpha
}

/// `effective_search_size` — `max(variants_evaluated, search_universe_size)`,
/// so the reported family size can never understate the declared search.
fn effective_search_size(variants_evaluated: usize, search_universe_size: usize) -> usize {
    assert!(
        search_universe_size >= variants_evaluated,
        "the declared search cannot be smaller than what it retained (D-046)"
    );
    variants_evaluated.max(search_universe_size)
}

// --- identity and slice building (regret_phase2.py) -------------------------

/// `sha1_hex` of a str: the oracle hashes `json.dumps(obj, ...)`, so the
/// JSON-encoded key (surrounding double quotes) is what enters the digest.
fn sha1_json_str(s: &str) -> String {
    let encoded = serde_json::to_string(s).expect("JSON encoding of a str cannot fail");
    let mut h = Sha1::new();
    h.update(encoded.as_bytes());
    let out = h.finalize();
    out.iter().map(|b| format!("{b:02x}")).collect()
}

/// `_seed_for(slice_key)` — `int(sha1_hex(slice_key)[:8], 16)`. Deterministic
/// per-slice seed (FT004), never wall-clock, never run-order dependent.
fn seed_for(slice_key: &str) -> u64 {
    u64::from_str_radix(&sha1_json_str(slice_key)[..8], 16)
        .expect("sha1 hex prefix is 8 hex digits")
}

/// `_estimand_series` — restrict to `gap_status == COMPUTED` before touching
/// any estimator (AS002); a non-COMPUTED row is never coerced into a float.
fn estimand_series<'a>(rows: &[&'a SliceRow], estimand: &str) -> (Vec<f64>, Vec<&'a SliceRow>) {
    let computed: Vec<&SliceRow> = rows
        .iter()
        .filter(|r| r.gap_status == "COMPUTED")
        .copied()
        .collect();
    let series = match estimand {
        "mean_legal_hindsight_gap" => computed
            .iter()
            .filter_map(|r| r.legal_hindsight_gap)
            .collect(),
        "mean_actual_vs_no_trade" => computed.iter().filter_map(|r| r.actual_utility).collect(),
        other => panic!("unknown estimand {other:?}"),
    };
    (series, computed)
}

/// `_max_hold_bars` — max truthy `horizon_bars` (a 0 is falsy and excluded),
/// falling back to 1 when no hold is recorded.
fn max_hold_bars(rows: &[&SliceRow]) -> usize {
    rows.iter()
        .filter_map(|r| r.horizon_bars)
        .filter(|&h| h > 0)
        .max()
        .map(|h| h as usize)
        .unwrap_or(1)
}

// --- Phase 2: systematicity discovery ---------------------------------------

/// FT003: the full 72-slice discovery family, declared BEFORE any data is
/// touched. The slice table is a verbatim mirror of `regret_phase2.py`
/// `declare_slices` — 3 Experts x 6 symbols x 2 directions x 2 estimands,
/// in that nesting order. Each tuple is `(slice_key, expert_id, symbol,
/// direction, estimand)`.
pub fn declare_slices() -> Vec<[String; 5]> {
    let mut out = Vec::with_capacity(72);
    for &expert in &EXPERTS {
        for &symbol in &SYMBOLS {
            for &direction in &DIRECTIONS {
                for &estimand in &ESTIMANDS {
                    let key = format!("{expert}|{symbol}|{direction}|{estimand}");
                    out.push([
                        key,
                        expert.to_string(),
                        symbol.to_string(),
                        direction.to_string(),
                        estimand.to_string(),
                    ]);
                }
            }
        }
    }
    out
}

/// One slice's systematicity gate (mirror of `regret_phase2.py:score_slice`).
///
/// Verdict chain per RECOVERABLE_REGRET_PROTOCOL §4 Phase 2:
/// `EXCLUDED_EMPTY` (no rows) -> `INSUFFICIENT_SUPPORT` (`n_computed < 30` or
/// `eff_n < 8`) -> `NOT_MATERIAL` (below the 0.05R economic floor or 30-trade
/// coverage) -> `NOT_SIGNIFICANT` (`ci_lower <= 0` — the CI must exclude the
/// null in the claimed direction) -> `CANDIDATE_SYSTEMATIC`. The candidate
/// gate is the systematicity claim Phase 2 makes; it is not yet a finding —
/// only a replicated `SYSTEMATIC_FINDING` on the confirmation half is.
pub fn score_slice(
    key: &str,
    expert_id: &str,
    symbol: &str,
    direction: &str,
    estimand: &str,
    dataset_rows: &[SliceRow],
) -> SliceResult {
    let family_size = effective_search_size(declare_slices().len(), declare_slices().len());
    let alpha_slate = ALPHA_FAMILY / family_size as f64;

    let slice_rows: Vec<&SliceRow> = dataset_rows
        .iter()
        .filter(|r| r.expert_id == expert_id && r.symbol == symbol && r.direction == direction)
        .collect();

    if slice_rows.is_empty() {
        return SliceResult {
            slice_key: key.into(),
            expert_id: expert_id.into(),
            symbol: symbol.into(),
            direction: direction.into(),
            estimand: estimand.into(),
            n_total_in_slice: 0,
            n_computed: 0,
            effective_independent_episodes: 0.0,
            mean: None,
            ci_lower: None,
            ci_upper: None,
            block_size: None,
            alpha_slate,
            practically_significant: None,
            materiality_note: "no candidates in this slice".into(),
            discovery_verdict: "EXCLUDED_EMPTY".into(),
            confirmation_verdict: None,
        };
    }

    let (series, computed_rows) = estimand_series(&slice_rows, estimand);
    let n_computed = series.len();
    let eff_n = if n_computed > 0 {
        effective_independent_episodes(n_computed, max_hold_bars(&computed_rows))
    } else {
        0.0
    };

    if n_computed < MIN_N_COMPUTED || eff_n < MIN_EFFECTIVE_EPISODES {
        return SliceResult {
            slice_key: key.into(),
            expert_id: expert_id.into(),
            symbol: symbol.into(),
            direction: direction.into(),
            estimand: estimand.into(),
            n_total_in_slice: slice_rows.len(),
            n_computed,
            effective_independent_episodes: eff_n,
            mean: None,
            ci_lower: None,
            ci_upper: None,
            block_size: None,
            alpha_slate,
            practically_significant: None,
            materiality_note: format!(
                "n_computed={n_computed} (need >={MIN_N_COMPUTED}) or \
                 effective_independent_episodes={eff_n:.2} (need >={MIN_EFFECTIVE_EPISODES})"
            ),
            discovery_verdict: "INSUFFICIENT_SUPPORT".into(),
            confirmation_verdict: None,
        };
    }

    let block = select_block_size(&series, 0.10);
    let seed = seed_for(key);
    let (ci_lower, ci_upper) = bootstrap_ci(&series, block, N_RESAMPLES, seed, CI);
    let (meets, note) = practical_significance(&series, MIN_NET_R, MIN_TRADES_MATERIALITY);
    let mean = fsum(&series) / series.len() as f64;

    let verdict = if !meets {
        "NOT_MATERIAL"
    } else if ci_lower <= 0.0 {
        // FT005/FT007: the CI must exclude the null in the direction claimed.
        "NOT_SIGNIFICANT"
    } else {
        "CANDIDATE_SYSTEMATIC"
    };

    SliceResult {
        slice_key: key.into(),
        expert_id: expert_id.into(),
        symbol: symbol.into(),
        direction: direction.into(),
        estimand: estimand.into(),
        n_total_in_slice: slice_rows.len(),
        n_computed,
        effective_independent_episodes: eff_n,
        mean: Some(mean),
        ci_lower: Some(ci_lower),
        ci_upper: Some(ci_upper),
        block_size: Some(block),
        alpha_slate,
        practically_significant: Some(meets),
        materiality_note: note,
        discovery_verdict: verdict.into(),
        confirmation_verdict: None,
    }
}

/// Discovery summary (mirror of `run_discovery`'s `discovery_summary.json`).
pub fn discovery_summary(results: &[SliceResult]) -> DiscoverySummary {
    let n_candidate = results
        .iter()
        .filter(|r| r.discovery_verdict == "CANDIDATE_SYSTEMATIC")
        .count();
    let distribution = DISCOVERY_VERDICTS
        .iter()
        .map(|v| {
            let c = results.iter().filter(|r| r.discovery_verdict == *v).count();
            ((*v).to_string(), c)
        })
        .collect();
    DiscoverySummary {
        n_slices_declared: declare_slices().len(),
        discovery_verdict_distribution: distribution,
        n_candidate_systematic: n_candidate,
        expected_false_positives_at_family_alpha: expected_false_positives(
            declare_slices().len(),
            ALPHA_FAMILY,
        ),
        alpha_slate_bonferroni: ALPHA_FAMILY / declare_slices().len() as f64,
        candidate_systematic_slices: results
            .iter()
            .filter(|r| r.discovery_verdict == "CANDIDATE_SYSTEMATIC")
            .map(|r| r.slice_key.clone())
            .collect(),
    }
}

/// FT006 ledger: the confirmation half is queried EXACTLY ONCE per declared
/// slice. A failure is recorded permanently and never re-tested
/// (FCR-V8RR-007 AP002); a second query of the same slice is a hard error,
/// not a warning (RECOVERABLE_REGRET_PROTOCOL §8.4).
#[derive(Debug, Default)]
pub struct ConfirmationLedger {
    queried: HashSet<String>,
}

impl ConfirmationLedger {
    pub fn new() -> Self {
        Self::default()
    }

    /// Query one candidate slice against the untouched confirmation half.
    /// Returns `Err` if this slice's confirmation half was already queried.
    pub fn query(
        &mut self,
        candidate: &SliceResult,
        confirmation_rows: &[SliceRow],
    ) -> Result<ConfirmationResult, String> {
        if !self.queried.insert(candidate.slice_key.clone()) {
            return Err(format!(
                "confirmation half for slice '{}' already queried: a slice's \
                 confirmation half is queried exactly once (FCR-V8RR-007 AP002)",
                candidate.slice_key
            ));
        }
        let slice_rows: Vec<&SliceRow> = confirmation_rows
            .iter()
            .filter(|r| {
                r.expert_id == candidate.expert_id
                    && r.symbol == candidate.symbol
                    && r.direction == candidate.direction
            })
            .collect();
        let (series, computed_rows) = if slice_rows.is_empty() {
            (Vec::new(), Vec::new())
        } else {
            estimand_series(&slice_rows, &candidate.estimand)
        };
        let n_computed = series.len();
        let eff_n = if n_computed > 0 {
            effective_independent_episodes(n_computed, max_hold_bars(&computed_rows))
        } else {
            0.0
        };

        if n_computed < MIN_N_COMPUTED || eff_n < MIN_EFFECTIVE_EPISODES {
            return Ok(ConfirmationResult {
                slice_key: candidate.slice_key.clone(),
                confirmation_verdict: "FAILED_CONFIRMATION".into(),
                confirmation_mean: None,
                confirmation_ci_lower: None,
                confirmation_ci_upper: None,
                confirmation_n_computed: n_computed,
            });
        }

        let block = select_block_size(&series, 0.10);
        let seed = seed_for(&format!("{}|confirmation", candidate.slice_key));
        let (lo, hi) = bootstrap_ci(&series, block, N_RESAMPLES, seed, CI);
        let mean = fsum(&series) / series.len() as f64;
        let (meets, _) = practical_significance(&series, MIN_NET_R, MIN_TRADES_MATERIALITY);
        let verdict = if meets && lo > 0.0 {
            "SYSTEMATIC_FINDING"
        } else {
            "FAILED_CONFIRMATION"
        };
        Ok(ConfirmationResult {
            slice_key: candidate.slice_key.clone(),
            confirmation_verdict: verdict.into(),
            confirmation_mean: Some(mean),
            confirmation_ci_lower: Some(lo),
            confirmation_ci_upper: Some(hi),
            confirmation_n_computed: n_computed,
        })
    }
}

// --- parity tests vs the frozen oracle (tools/regret_phase2.py) -------------

#[cfg(test)]
mod tests {
    use super::*;

    // Captured from the oracle interpreter (`.venv/bin/python`, 3.14.0) on
    // the synthetic fixtures below, via `tools.regret_phase2`. Every numeric
    // constant is the exact IEEE value the oracle produced (asserted with
    // f64 `==`, i.e. bit equality modulo -0.0).

    const KEY: &str = "trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap";
    const KEY_SEED: u64 = 3_159_536_366;
    const KEY_CONF_SEED: u64 = 2_126_530_160;
    const KEY2: &str = "trend_pullback|BTCUSDT|LONG|mean_actual_vs_no_trade";
    const KEY2_SEED: u64 = 3_687_838_827;

    fn row(
        expert: &str,
        symbol: &str,
        direction: &str,
        gap_status: &str,
        gap: Option<f64>,
        util: Option<f64>,
        horizon: Option<i64>,
    ) -> SliceRow {
        SliceRow {
            expert_id: expert.into(),
            symbol: symbol.into(),
            direction: direction.into(),
            gap_status: gap_status.into(),
            legal_hindsight_gap: gap,
            actual_utility: util,
            horizon_bars: horizon,
        }
    }

    /// Discovery half: 40 COMPUTED rows (horizon 2 on i%11==0) + 5 REJECTED
    /// rows in the slice + 3 rows in other slices that the slice-builder must
    /// filter out.
    fn discovery_rows() -> Vec<SliceRow> {
        let mut rows = Vec::new();
        for i in 0..40usize {
            let v = 0.10 + 0.013 * (i % 9) as f64;
            let h = if i % 11 == 0 { 2 } else { 1 };
            rows.push(row(
                "trend_pullback",
                "BTCUSDT",
                "LONG",
                "COMPUTED",
                Some(v),
                None,
                Some(h),
            ));
        }
        for _ in 0..5 {
            rows.push(row(
                "trend_pullback",
                "BTCUSDT",
                "LONG",
                "REJECTED",
                None,
                None,
                Some(3),
            ));
        }
        rows.push(row(
            "failed_breakout",
            "BTCUSDT",
            "LONG",
            "COMPUTED",
            Some(9.9),
            None,
            Some(1),
        ));
        rows.push(row(
            "trend_pullback",
            "ETHUSDT",
            "LONG",
            "COMPUTED",
            Some(8.8),
            None,
            Some(1),
        ));
        rows.push(row(
            "trend_pullback",
            "BTCUSDT",
            "SHORT",
            "COMPUTED",
            Some(7.7),
            None,
            Some(1),
        ));
        rows
    }

    fn actual_vs_no_trade_rows() -> Vec<SliceRow> {
        (0..38)
            .map(|i| {
                let v = 0.04 + 0.021 * (i % 6) as f64;
                row(
                    "trend_pullback",
                    "BTCUSDT",
                    "LONG",
                    "COMPUTED",
                    None,
                    Some(v),
                    Some(1),
                )
            })
            .collect()
    }

    fn short_support_rows() -> Vec<SliceRow> {
        (0..12)
            .map(|i| {
                let v = 0.05 + 0.01 * i as f64;
                row(
                    "trend_pullback",
                    "ETHUSDT",
                    "SHORT",
                    "COMPUTED",
                    Some(v),
                    None,
                    Some(1),
                )
            })
            .collect()
    }

    /// Confirmation half A: 36 COMPUTED (horizon 2 on i%13==0) + 4 CENSORED.
    fn confirmation_rows_a() -> Vec<SliceRow> {
        let mut rows = Vec::new();
        for i in 0..36usize {
            let v = 0.09 + 0.017 * (i % 7) as f64;
            let h = if i % 13 == 0 { 2 } else { 1 };
            rows.push(row(
                "trend_pullback",
                "BTCUSDT",
                "LONG",
                "COMPUTED",
                Some(v),
                None,
                Some(h),
            ));
        }
        for _ in 0..4 {
            rows.push(row(
                "trend_pullback",
                "BTCUSDT",
                "LONG",
                "CENSORED",
                None,
                None,
                Some(2),
            ));
        }
        rows
    }

    /// Confirmation half B: 34 COMPUTED rows (different data -> different CI).
    fn confirmation_rows_b() -> Vec<SliceRow> {
        (0..34)
            .map(|i| {
                let v = 0.06 + 0.019 * (i % 5) as f64;
                row(
                    "trend_pullback",
                    "BTCUSDT",
                    "LONG",
                    "COMPUTED",
                    Some(v),
                    None,
                    Some(1),
                )
            })
            .collect()
    }

    #[test]
    fn slice_family_is_the_declared_72_verbatim() {
        let slices = declare_slices();
        assert_eq!(slices.len(), 72);
        assert_eq!(
            slices[0][0],
            "trend_pullback|BTCUSDT|LONG|mean_legal_hindsight_gap"
        );
        assert_eq!(
            slices[1][0],
            "trend_pullback|BTCUSDT|LONG|mean_actual_vs_no_trade"
        );
        assert_eq!(
            slices[2][0],
            "trend_pullback|BTCUSDT|SHORT|mean_legal_hindsight_gap"
        );
        // Oracle `declare_slices()[-3:]`: LONG|mean_actual_vs_no_trade,
        // SHORT|mean_legal_hindsight_gap, SHORT|mean_actual_vs_no_trade.
        assert_eq!(
            slices[69][0],
            "liquidity_sweep_reclaim|DOGEUSDT|LONG|mean_actual_vs_no_trade"
        );
        assert_eq!(
            slices[70][0],
            "liquidity_sweep_reclaim|DOGEUSDT|SHORT|mean_legal_hindsight_gap"
        );
        assert_eq!(
            slices[71][0],
            "liquidity_sweep_reclaim|DOGEUSDT|SHORT|mean_actual_vs_no_trade"
        );
        // 24 slices per expert; every expert/symbol/direction/estimand crossed.
        for &expert in &EXPERTS {
            assert_eq!(
                slices.iter().filter(|s| s[1] == expert).count(),
                24,
                "{expert}"
            );
        }
        let mut keys: Vec<&str> = slices.iter().map(|s| s[0].as_str()).collect();
        keys.sort();
        keys.dedup();
        assert_eq!(keys.len(), 72, "slice keys are unique");
    }

    #[test]
    fn seed_for_matches_oracle() {
        assert_eq!(seed_for(KEY), KEY_SEED);
        assert_eq!(seed_for(&format!("{KEY}|confirmation")), KEY_CONF_SEED);
        assert_eq!(seed_for(KEY2), KEY2_SEED);
    }

    #[test]
    fn discovery_slice_matches_oracle_bit_for_bit() {
        let r = score_slice(
            KEY,
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            "mean_legal_hindsight_gap",
            &discovery_rows(),
        );
        assert_eq!(r.slice_key, KEY);
        assert_eq!(
            r.n_total_in_slice, 45,
            "REJECTED rows count in the slice total"
        );
        assert_eq!(r.n_computed, 40, "only COMPUTED rows enter the series");
        assert_eq!(r.effective_independent_episodes, 20.0);
        assert_eq!(r.mean, Some(0.14875));
        assert_eq!(r.ci_lower, Some(0.139325));
        assert_eq!(r.ci_upper, Some(0.158175));
        assert_eq!(r.block_size, Some(6));
        assert_eq!(r.alpha_slate, 0.0006944444444444445);
        assert_eq!(r.practically_significant, Some(true));
        assert_eq!(
            r.materiality_note,
            "mean net_R 0.1487 vs economic floor 0.05 (meets); \
             episodes 40 vs minimum coverage 30 (meets)"
        );
        assert_eq!(r.discovery_verdict, "CANDIDATE_SYSTEMATIC");
        assert_eq!(r.confirmation_verdict, None);
    }

    #[test]
    fn actual_vs_no_trade_slice_matches_oracle_bit_for_bit() {
        let r = score_slice(
            KEY2,
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            "mean_actual_vs_no_trade",
            &actual_vs_no_trade_rows(),
        );
        assert_eq!(r.n_total_in_slice, 38);
        assert_eq!(r.n_computed, 38);
        assert_eq!(r.effective_independent_episodes, 38.0);
        assert_eq!(r.mean, Some(0.09028947368421053));
        assert_eq!(r.ci_lower, Some(0.08476315789473685));
        assert_eq!(r.ci_upper, Some(0.09471052631578948));
        assert_eq!(r.block_size, Some(6));
        assert_eq!(r.discovery_verdict, "CANDIDATE_SYSTEMATIC");
    }

    #[test]
    fn insufficient_support_matches_oracle() {
        let r = score_slice(
            "trend_pullback|ETHUSDT|SHORT|mean_legal_hindsight_gap",
            "trend_pullback",
            "ETHUSDT",
            "SHORT",
            "mean_legal_hindsight_gap",
            &short_support_rows(),
        );
        assert_eq!(r.n_computed, 12);
        assert_eq!(r.effective_independent_episodes, 12.0);
        assert_eq!(r.mean, None);
        assert_eq!(r.block_size, None);
        assert_eq!(
            r.materiality_note,
            "n_computed=12 (need >=30) or effective_independent_episodes=12.00 (need >=8)"
        );
        assert_eq!(r.discovery_verdict, "INSUFFICIENT_SUPPORT");
    }

    #[test]
    fn excluded_empty_matches_oracle() {
        // No row matches this expert/symbol/direction in the dataset.
        let rows = vec![row(
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            "COMPUTED",
            Some(0.5),
            None,
            Some(1),
        )];
        let r = score_slice(
            "liquidity_sweep_reclaim|DOGEUSDT|LONG|mean_actual_vs_no_trade",
            "liquidity_sweep_reclaim",
            "DOGEUSDT",
            "LONG",
            "mean_actual_vs_no_trade",
            &rows,
        );
        assert_eq!(r.n_total_in_slice, 0);
        assert_eq!(r.n_computed, 0);
        assert_eq!(r.effective_independent_episodes, 0.0);
        assert_eq!(r.mean, None);
        assert_eq!(r.materiality_note, "no candidates in this slice");
        assert_eq!(r.discovery_verdict, "EXCLUDED_EMPTY");
    }

    #[test]
    fn confirmation_matches_oracle_and_second_query_is_refused() {
        let candidate = score_slice(
            KEY,
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            "mean_legal_hindsight_gap",
            &discovery_rows(),
        );
        assert_eq!(candidate.discovery_verdict, "CANDIDATE_SYSTEMATIC");

        let mut ledger = ConfirmationLedger::new();
        let cr = ledger
            .query(&candidate, &confirmation_rows_a())
            .expect("first query of this confirmation half must succeed");
        assert_eq!(cr.slice_key, KEY);
        assert_eq!(cr.confirmation_verdict, "SYSTEMATIC_FINDING");
        assert_eq!(cr.confirmation_mean, Some(0.13958333333333334));
        assert_eq!(cr.confirmation_ci_lower, Some(0.1343888888888889));
        assert_eq!(cr.confirmation_ci_upper, Some(0.14430555555555558));
        assert_eq!(cr.confirmation_n_computed, 36);

        // FCR-V8RR-007 AP002 / protocol §8.4: a second query of the SAME
        // slice's confirmation half is a hard error.
        match ledger.query(&candidate, &confirmation_rows_a()) {
            Err(msg) => assert!(msg.contains(KEY), "error must name the slice: {msg}"),
            Ok(_) => panic!("second query of the same confirmation half must be refused"),
        }
    }

    #[test]
    fn confirmation_different_half_matches_oracle() {
        let candidate = score_slice(
            KEY,
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            "mean_legal_hindsight_gap",
            &discovery_rows(),
        );
        let mut ledger = ConfirmationLedger::new();
        let cr = ledger
            .query(&candidate, &confirmation_rows_b())
            .expect("first query must succeed");
        assert_eq!(cr.confirmation_verdict, "SYSTEMATIC_FINDING");
        assert_eq!(cr.confirmation_mean, Some(0.09688235294117648));
        assert_eq!(cr.confirmation_ci_lower, Some(0.09073529411764705));
        assert_eq!(cr.confirmation_ci_upper, Some(0.10302941176470588));
        assert_eq!(cr.confirmation_n_computed, 34);
    }

    #[test]
    fn bootstrap_ci_tail_is_99_not_100() {
        // int(2000 * (1.0 - 0.90) / 2.0) = int(99.99999999999998) = 99 in the
        // oracle; a naive 2000*0.10/2 = 100 would pick different percentiles.
        assert_eq!((N_RESAMPLES as f64 * (1.0 - CI) / 2.0) as usize, 99);
    }

    #[test]
    fn family_alpha_stats_match_oracle() {
        let slices = declare_slices();
        let efp = expected_false_positives(slices.len(), ALPHA_FAMILY);
        assert_eq!(efp, 3.6);
        assert_eq!(efp, 72.0 * 0.05);
        assert_eq!(ALPHA_FAMILY / slices.len() as f64, 0.0006944444444444445);
        // every slice carries the Bonferroni-corrected slate
        for s in &slices {
            let key = s[0].as_str();
            assert_eq!(key.split('|').count(), 4);
            assert_eq!(key, &format!("{}|{}|{}|{}", s[1], s[2], s[3], s[4]));
        }
    }

    #[test]
    fn discovery_summary_counts_are_exact() {
        let rows = discovery_rows();
        let candidate = score_slice(
            KEY,
            "trend_pullback",
            "BTCUSDT",
            "LONG",
            "mean_legal_hindsight_gap",
            &rows,
        );
        let empty = score_slice(
            "liquidity_sweep_reclaim|DOGEUSDT|LONG|mean_legal_hindsight_gap",
            "liquidity_sweep_reclaim",
            "DOGEUSDT",
            "LONG",
            "mean_legal_hindsight_gap",
            &rows,
        );
        let insuff = score_slice(
            "trend_pullback|ETHUSDT|SHORT|mean_legal_hindsight_gap",
            "trend_pullback",
            "ETHUSDT",
            "SHORT",
            "mean_legal_hindsight_gap",
            &short_support_rows(),
        );
        let summary = discovery_summary(&[candidate, empty, insuff]);
        assert_eq!(summary.n_slices_declared, 72);
        assert_eq!(summary.n_candidate_systematic, 1);
        assert_eq!(summary.expected_false_positives_at_family_alpha, 3.6);
        assert_eq!(summary.alpha_slate_bonferroni, 0.0006944444444444445);
        assert_eq!(summary.candidate_systematic_slices, vec![KEY.to_string()]);
        let dist: Vec<(&str, usize)> = summary
            .discovery_verdict_distribution
            .iter()
            .map(|(v, c)| (v.as_str(), *c))
            .collect();
        assert_eq!(dist.len(), 5);
        for (v, c) in dist {
            let expected = usize::from(matches!(
                v,
                "CANDIDATE_SYSTEMATIC" | "INSUFFICIENT_SUPPORT" | "EXCLUDED_EMPTY"
            ));
            assert_eq!(c, expected, "verdict {v}");
        }
    }
}
