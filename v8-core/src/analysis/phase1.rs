//! S6 Phase 1 — candidate-local opportunity accounting (issue #118): the
//! frozen join of the reconciled CandidateSnapshots with the cube-reduced
//! accumulators and the per-Candidate regret gap (mirror of
//! `tools/regret_phase1.py`; RECOVERABLE_REGRET_PROTOCOL §4 "Phase 1").
//!
//! Phase 1 is DESCRIPTIVE ONLY. It joins one regret.jsonl gap record per
//! Candidate with its ACTUAL action's cube row, tags the row with the symbol
//! its store was built for, and emits exactly the 19 oracle fields. It does
//! not slice by context/habitat, does not test significance, and does not sum
//! Candidate-local gaps into a claimed portfolio value. Every number is
//! `MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED`.
//!
//! The legal-opportunity set is the regret manifest grid — NO_TRADE + ACTUAL
//! + the declared target_r (1,2,3) x expiry_bars (8,24,48) variants,
//!   de-duplicated by action id (`regret::generate_legal_actions`); when the
//!   ACTUAL geometry is itself on the grid the variant set collapses to 8
//!   cells, the "8-cell + NO_TRADE + ACTUAL" manifest. The per-cell utilities
//!   arrive already cube-reduced (`regret::Cell`/`ReducedRow`); Phase 1's job
//!   is the join, not a second cube reduction.
//!
//! The input is the reconciled CandidateSnapshot projection
//! (`reconcile.rs`, issue #122) plus the reduced tables; the module is
//! implemented against in-memory input structs so it stays independent of
//! the store wiring (the `analysis` subcommand, issue #116).

use std::collections::HashMap;

/// The Phase-1 honesty label (every population-style number in the oracle's
/// output carries it; `tools/regret_phase1.py` `LABEL`).
#[allow(dead_code)]
pub const LABEL: &str = "MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED";

/// One row of the frozen Phase-1 dataset: a regret.jsonl gap record joined
/// with its ACTUAL action's cube row and tagged with the symbol its store
/// was built for. 19 fields, exactly as `tools/regret_phase1.py`
/// `JoinedCandidateRow`.
#[derive(Debug, Clone, PartialEq)]
pub struct JoinedCandidateRow {
    pub symbol: String,
    pub candidate_id: String,
    pub expert_id: String,
    pub direction: String,
    pub birth_time: i64,
    pub gap_status: String,
    pub legal_hindsight_gap: Option<f64>,
    pub actual_utility: Option<f64>,
    pub best_utility: Option<f64>,
    pub tie_cardinality: usize,
    pub endpoint: Option<String>,
    pub label_status: Option<String>,
    pub horizon_bars: Option<i64>,
    pub cost_r: Option<f64>,
    pub funding_r: Option<f64>,
    pub mae_r: Option<f64>,
    pub mfe_r: Option<f64>,
    pub ambiguous_bars: Option<i64>,
    pub epistemic_class: String,
}

impl JoinedCandidateRow {
    /// The oracle's field count (19; pinned by
    /// `JoinedCandidateRow.__dataclass_fields__` in `tools/regret_phase1.py`).
    #[allow(dead_code)]
    pub const FIELD_COUNT: usize = 19;
}

/// The candidate identity a Phase-1 join needs — the projection of the
/// DETECTED transition that the oracle's `_load_store_snapshots` extracts
/// (expert_id, direction, birth_time per candidate_id; birth_time is the
/// DETECTED transition's own knowledge_time, the only decision-time-defined
/// clock a Candidate carries before any action is taken, FT002). In V8.2
/// this is the reconciled CandidateSnapshot projection (reconcile.rs).
#[derive(Debug, Clone, Default, PartialEq)]
pub struct CandidateIdentity {
    pub expert_id: String,
    pub direction: String,
    pub birth_time: i64,
}

/// The per-Candidate regret gap — the fields of the oracle's RegretRecord
/// that the Phase-1 join carries (gap-status vocabulary is `regret.rs`'s).
#[derive(Debug, Clone, PartialEq)]
pub struct GapRecord {
    pub candidate_id: String,
    pub actual_action_id: Option<String>,
    pub actual_utility: Option<f64>,
    pub best_utility: Option<f64>,
    pub tie_cardinality: usize,
    pub legal_hindsight_gap: Option<f64>,
    pub gap_status: String,
}

/// The ACTUAL action's cube-reduced accumulators — the eight OutcomeCubeRow
/// value fields the Phase-1 join carries (endpoint, label_status,
/// horizon_bars, cost_r, funding_r, mae_r, mfe_r, ambiguous_bars), as the
/// CubeReducer persists them per (candidate, action).
#[derive(Debug, Clone, Default, PartialEq)]
pub struct CubeAccumulators {
    pub endpoint: Option<String>,
    pub label_status: Option<String>,
    pub horizon_bars: Option<i64>,
    pub cost_r: Option<f64>,
    pub funding_r: Option<f64>,
    pub mae_r: Option<f64>,
    pub mfe_r: Option<f64>,
    pub ambiguous_bars: Option<i64>,
}

/// One symbol's Phase-0 output, in memory: the candidate identities, the gap
/// records (regret.jsonl) and the cube accumulators (cube.jsonl) keyed by
/// (candidate_id, action_id), as the oracle reads them from a store.
#[derive(Debug, Clone, Default)]
pub struct Phase0Output {
    pub identities: HashMap<String, CandidateIdentity>,
    pub gaps: Vec<GapRecord>,
    pub cubes: HashMap<(String, String), CubeAccumulators>,
}

/// The frozen Phase-1 dataset: one `JoinedCandidateRow` per gap record across
/// every symbol — symbols iterated sorted, rows in gap-record order per
/// symbol. Mirror of `tools/regret_phase1.py:join_dataset`.
pub fn join_dataset(per_symbol: Vec<(String, Phase0Output)>) -> Vec<JoinedCandidateRow> {
    let mut rows = Vec::new();
    let mut symbols = per_symbol;
    symbols.sort_by(|a, b| a.0.cmp(&b.0));
    for (symbol, out) in symbols {
        for g in out.gaps {
            let ident = out
                .identities
                .get(&g.candidate_id)
                .cloned()
                .unwrap_or_default();
            // The actual cube row is looked up by (candidate_id,
            // actual_action_id); a gap record with no actual_action_id — or
            // whose action is absent from the reduced cube table — yields
            // None cube fields (the oracle's `cube_by_key.get` miss).
            let actual = g
                .actual_action_id
                .as_ref()
                .and_then(|aid| out.cubes.get(&(g.candidate_id.clone(), aid.clone())));
            rows.push(JoinedCandidateRow {
                symbol: symbol.clone(),
                candidate_id: g.candidate_id.clone(),
                expert_id: ident.expert_id,
                direction: ident.direction,
                birth_time: ident.birth_time,
                gap_status: g.gap_status.clone(),
                legal_hindsight_gap: g.legal_hindsight_gap,
                actual_utility: g.actual_utility,
                best_utility: g.best_utility,
                tie_cardinality: g.tie_cardinality,
                endpoint: actual.and_then(|c| c.endpoint.clone()),
                label_status: actual.and_then(|c| c.label_status.clone()),
                horizon_bars: actual.and_then(|c| c.horizon_bars),
                cost_r: actual.and_then(|c| c.cost_r),
                funding_r: actual.and_then(|c| c.funding_r),
                mae_r: actual.and_then(|c| c.mae_r),
                mfe_r: actual.and_then(|c| c.mfe_r),
                ambiguous_bars: actual.and_then(|c| c.ambiguous_bars),
                // Python: JoinedCandidateRow.epistemic_class = 'MODEL_DERIVED'
                // (regret_phase1.py:103); LABEL is the DATASET tag, not the
                // per-row value — conflating them broke the S6 pipeline parity
                // (939 divergences in the #117 harness).
                epistemic_class: "MODEL_DERIVED".to_string(),
            });
        }
    }
    rows
}

/// One legal-opportunity cell with its cube-reduced utility.
#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub struct OpportunityCell {
    pub action_id: String,
    pub kind: &'static str,       // NO_TRADE | GEOMETRY_VARIANT
    pub provenance: &'static str, // ACTUAL | DECLARED_VARIANT
    pub utility: Option<f64>,
}

/// The per-Candidate legal-opportunity set with per-cell utilities: the
/// manifest's legal actions in manifest order (NO_TRADE, ACTUAL, then the
/// declared target_r x expiry_bars grid, de-duplicated by action id), each
/// paired with its cube-reduced net utility (None when the cell is absent
/// from the reduced table). A thin projection of `regret.rs` — the manifest
/// IS the oracle's A(C) (FCR FT003), so this never re-derives the set.
#[allow(dead_code)]
pub fn opportunity_set(
    manifest: &crate::regret::Manifest,
    utility_by_action: &HashMap<String, f64>,
) -> Vec<OpportunityCell> {
    manifest
        .actions
        .iter()
        .map(|a| OpportunityCell {
            action_id: a.action_id.clone(),
            kind: a.kind,
            provenance: a.provenance,
            utility: utility_by_action.get(&a.action_id).copied(),
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::regret::{self, Manifest};

    fn identity(expert: &str, direction: &str, birth_time: i64) -> CandidateIdentity {
        CandidateIdentity {
            expert_id: expert.to_string(),
            direction: direction.to_string(),
            birth_time,
        }
    }

    fn gap(
        cid: &str,
        actual_action_id: Option<&str>,
        status: &str,
        gap: Option<f64>,
        actual_u: Option<f64>,
        best_u: Option<f64>,
        tie: usize,
    ) -> GapRecord {
        GapRecord {
            candidate_id: cid.to_string(),
            actual_action_id: actual_action_id.map(|s| s.to_string()),
            actual_utility: actual_u,
            best_utility: best_u,
            tie_cardinality: tie,
            legal_hindsight_gap: gap,
            gap_status: status.to_string(),
        }
    }

    fn cube(
        cid: &str,
        aid: &str,
        endpoint: Option<&str>,
        label: Option<&str>,
        horizon: Option<i64>,
        cost_r: Option<f64>,
        funding_r: Option<f64>,
        mae_r: Option<f64>,
        mfe_r: Option<f64>,
        ambiguous: Option<i64>,
    ) -> ((String, String), CubeAccumulators) {
        (
            (cid.to_string(), aid.to_string()),
            CubeAccumulators {
                endpoint: endpoint.map(|s| s.to_string()),
                label_status: label.map(|s| s.to_string()),
                horizon_bars: horizon,
                cost_r,
                funding_r,
                mae_r,
                mfe_r,
                ambiguous_bars: ambiguous,
            },
        )
    }

    /// The synthetic Phase-1 fixture: 2 symbols x 8 Candidates covering the
    /// oracle's row shapes (COMPUTED with non-trivial floats, tie, censored
    /// abstention, undefined abstention, no-actual-action, missing actual
    /// cube row, missing DETECTED identity). Reference rows are captured from
    /// the frozen oracle by `tools/regret_phase1.py:join_dataset` on the same
    /// synthetic cube-reduced input (see the oracle-capture script in the S6
    /// job notes); every constant below is the oracle's emitted value.
    fn fixture() -> Vec<(String, Phase0Output)> {
        let mut btc_ident = HashMap::new();
        btc_ident.insert(
            "c-btc-0001".to_string(),
            identity("trend_pullback", "LONG", 1_700_000_000),
        );
        btc_ident.insert(
            "c-btc-0002".to_string(),
            identity("failed_breakout", "SHORT", 1_700_000_100),
        );
        btc_ident.insert(
            "c-btc-0003".to_string(),
            identity("liquidity_sweep_reclaim", "LONG", 1_700_000_200),
        );
        btc_ident.insert(
            "c-btc-0004".to_string(),
            identity("trend_pullback", "LONG", 1_700_000_300),
        );
        btc_ident.insert(
            "c-btc-0005".to_string(),
            identity("failed_breakout", "SHORT", 1_700_000_400),
        );
        // c-btc-0006 deliberately has no DETECTED transition.

        let btc_gaps = vec![
            gap(
                "c-btc-0001",
                Some("btc-act-1"),
                "COMPUTED",
                Some(0.6771358024691356),
                Some(-0.38701234567890123),
                Some(0.29012345678901234),
                1,
            ),
            gap(
                "c-btc-0002",
                Some("btc-act-2"),
                "COMPUTED",
                Some(1.142),
                Some(-0.09),
                Some(1.052),
                3,
            ),
            gap(
                "c-btc-0003",
                Some("btc-act-3"),
                "ABSTAINED_CENSORED",
                None,
                Some(-0.2),
                None,
                0,
            ),
            gap(
                "c-btc-0004",
                Some("btc-act-4-missing-cube"),
                "COMPUTED",
                Some(0.001),
                Some(-0.001),
                Some(0.0),
                1,
            ),
            gap(
                "c-btc-0005",
                None,
                "NOT_APPLICABLE_NO_ACTUAL_ACTION",
                None,
                None,
                None,
                0,
            ),
            gap(
                "c-btc-0006",
                Some("btc-act-6"),
                "COMPUTED",
                Some(0.222),
                Some(0.111),
                Some(0.333),
                2,
            ),
        ];

        let mut btc_cubes = HashMap::new();
        btc_cubes.extend([
            cube(
                "c-btc-0001",
                "btc-act-1",
                Some("TARGET"),
                Some("MATURE"),
                Some(47),
                Some(0.053111111111111116),
                Some(0.0),
                Some(-0.8812345678901234),
                Some(0.9234567890123457),
                Some(2),
            ),
            cube(
                "c-btc-0002",
                "btc-act-2",
                Some("TARGET"),
                Some("MATURE"),
                Some(8),
                Some(0.05),
                Some(0.0),
                Some(-0.4),
                Some(1.6),
                Some(0),
            ),
            cube(
                "c-btc-0003",
                "btc-act-3",
                Some("STOP"),
                Some("RIGHT_CENSORED"),
                Some(24),
                Some(0.05),
                None,
                Some(-1.2),
                Some(0.7),
                Some(5),
            ),
            cube(
                "c-btc-0006",
                "btc-act-6",
                Some("TARGET"),
                Some("MATURE"),
                Some(16),
                Some(0.0),
                Some(0.0),
                Some(-0.5),
                Some(0.9),
                Some(0),
            ),
        ]);

        let mut sol_ident = HashMap::new();
        sol_ident.insert(
            "c-sol-0001".to_string(),
            identity("liquidity_sweep_reclaim", "LONG", 1_700_000_500),
        );
        sol_ident.insert(
            "c-sol-0002".to_string(),
            identity("trend_pullback", "SHORT", 1_700_000_600),
        );

        let sol_gaps = vec![
            gap(
                "c-sol-0001",
                Some("sol-act-1"),
                "COMPUTED",
                Some(0.28),
                Some(0.05),
                Some(0.33),
                2,
            ),
            gap(
                "c-sol-0002",
                None,
                "ABSTAINED_UNDEFINED",
                None,
                None,
                None,
                0,
            ),
        ];

        let mut sol_cubes = HashMap::new();
        sol_cubes.extend([cube(
            "c-sol-0001",
            "sol-act-1",
            Some("TARGET"),
            Some("MATURE"),
            Some(48),
            Some(0.07777777777777778),
            Some(0.0),
            Some(-0.6543210987654321),
            Some(1.2345678901234567),
            Some(0),
        )]);

        vec![
            (
                "BTCUSDT".to_string(),
                Phase0Output {
                    identities: btc_ident,
                    gaps: btc_gaps,
                    cubes: btc_cubes,
                },
            ),
            (
                "SOLUSDT".to_string(),
                Phase0Output {
                    identities: sol_ident,
                    gaps: sol_gaps,
                    cubes: sol_cubes,
                },
            ),
        ]
    }

    fn expected_rows() -> Vec<JoinedCandidateRow> {
        vec![
            JoinedCandidateRow {
                symbol: "BTCUSDT".into(),
                candidate_id: "c-btc-0001".into(),
                expert_id: "trend_pullback".into(),
                direction: "LONG".into(),
                birth_time: 1_700_000_000,
                gap_status: "COMPUTED".into(),
                legal_hindsight_gap: Some(0.6771358024691356),
                actual_utility: Some(-0.38701234567890125),
                best_utility: Some(0.29012345678901236),
                tie_cardinality: 1,
                endpoint: Some("TARGET".into()),
                label_status: Some("MATURE".into()),
                horizon_bars: Some(47),
                cost_r: Some(0.053111111111111116),
                funding_r: Some(0.0),
                mae_r: Some(-0.8812345678901234),
                mfe_r: Some(0.9234567890123457),
                ambiguous_bars: Some(2),
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "BTCUSDT".into(),
                candidate_id: "c-btc-0002".into(),
                expert_id: "failed_breakout".into(),
                direction: "SHORT".into(),
                birth_time: 1_700_000_100,
                gap_status: "COMPUTED".into(),
                legal_hindsight_gap: Some(1.142),
                actual_utility: Some(-0.09),
                best_utility: Some(1.052),
                tie_cardinality: 3,
                endpoint: Some("TARGET".into()),
                label_status: Some("MATURE".into()),
                horizon_bars: Some(8),
                cost_r: Some(0.05),
                funding_r: Some(0.0),
                mae_r: Some(-0.4),
                mfe_r: Some(1.6),
                ambiguous_bars: Some(0),
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "BTCUSDT".into(),
                candidate_id: "c-btc-0003".into(),
                expert_id: "liquidity_sweep_reclaim".into(),
                direction: "LONG".into(),
                birth_time: 1_700_000_200,
                gap_status: "ABSTAINED_CENSORED".into(),
                legal_hindsight_gap: None,
                actual_utility: Some(-0.2),
                best_utility: None,
                tie_cardinality: 0,
                endpoint: Some("STOP".into()),
                label_status: Some("RIGHT_CENSORED".into()),
                horizon_bars: Some(24),
                cost_r: Some(0.05),
                funding_r: None,
                mae_r: Some(-1.2),
                mfe_r: Some(0.7),
                ambiguous_bars: Some(5),
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "BTCUSDT".into(),
                candidate_id: "c-btc-0004".into(),
                expert_id: "trend_pullback".into(),
                direction: "LONG".into(),
                birth_time: 1_700_000_300,
                gap_status: "COMPUTED".into(),
                legal_hindsight_gap: Some(0.001),
                actual_utility: Some(-0.001),
                best_utility: Some(0.0),
                tie_cardinality: 1,
                endpoint: None,
                label_status: None,
                horizon_bars: None,
                cost_r: None,
                funding_r: None,
                mae_r: None,
                mfe_r: None,
                ambiguous_bars: None,
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "BTCUSDT".into(),
                candidate_id: "c-btc-0005".into(),
                expert_id: "failed_breakout".into(),
                direction: "SHORT".into(),
                birth_time: 1_700_000_400,
                gap_status: "NOT_APPLICABLE_NO_ACTUAL_ACTION".into(),
                legal_hindsight_gap: None,
                actual_utility: None,
                best_utility: None,
                tie_cardinality: 0,
                endpoint: None,
                label_status: None,
                horizon_bars: None,
                cost_r: None,
                funding_r: None,
                mae_r: None,
                mfe_r: None,
                ambiguous_bars: None,
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "BTCUSDT".into(),
                candidate_id: "c-btc-0006".into(),
                expert_id: "".into(),
                direction: "".into(),
                birth_time: 0,
                gap_status: "COMPUTED".into(),
                legal_hindsight_gap: Some(0.222),
                actual_utility: Some(0.111),
                best_utility: Some(0.333),
                tie_cardinality: 2,
                endpoint: Some("TARGET".into()),
                label_status: Some("MATURE".into()),
                horizon_bars: Some(16),
                cost_r: Some(0.0),
                funding_r: Some(0.0),
                mae_r: Some(-0.5),
                mfe_r: Some(0.9),
                ambiguous_bars: Some(0),
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "SOLUSDT".into(),
                candidate_id: "c-sol-0001".into(),
                expert_id: "liquidity_sweep_reclaim".into(),
                direction: "LONG".into(),
                birth_time: 1_700_000_500,
                gap_status: "COMPUTED".into(),
                legal_hindsight_gap: Some(0.28),
                actual_utility: Some(0.05),
                best_utility: Some(0.33),
                tie_cardinality: 2,
                endpoint: Some("TARGET".into()),
                label_status: Some("MATURE".into()),
                horizon_bars: Some(48),
                cost_r: Some(0.07777777777777778),
                funding_r: Some(0.0),
                mae_r: Some(-0.6543210987654321),
                mfe_r: Some(1.2345678901234567),
                ambiguous_bars: Some(0),
                epistemic_class: "MODEL_DERIVED".into(),
            },
            JoinedCandidateRow {
                symbol: "SOLUSDT".into(),
                candidate_id: "c-sol-0002".into(),
                expert_id: "trend_pullback".into(),
                direction: "SHORT".into(),
                birth_time: 1_700_000_600,
                gap_status: "ABSTAINED_UNDEFINED".into(),
                legal_hindsight_gap: None,
                actual_utility: None,
                best_utility: None,
                tie_cardinality: 0,
                endpoint: None,
                label_status: None,
                horizon_bars: None,
                cost_r: None,
                funding_r: None,
                mae_r: None,
                mfe_r: None,
                ambiguous_bars: None,
                epistemic_class: "MODEL_DERIVED".into(),
            },
        ]
    }

    /// Parity vs the frozen oracle: the 19-field rows produced by
    /// `tools/regret_phase1.py:join_dataset` on the same synthetic
    /// cube-reduced input, embedded as constants and compared value-level
    /// (IEEE bit equality — the join passes floats through untouched).
    #[test]
    fn join_matches_oracle_rows() {
        let rows = join_dataset(fixture());
        assert_eq!(rows.len(), 8);
        assert_eq!(rows, expected_rows());
    }

    /// The oracle's emitted float is the double the join actually carried:
    /// explicit bit-level check on the non-trivial round-trip value.
    #[test]
    fn join_floats_are_bit_identical() {
        let rows = join_dataset(fixture());
        let r0 = &rows[0];
        assert_eq!(
            r0.legal_hindsight_gap.unwrap().to_bits(),
            0x3FE5AB18B3D1C7EA
        );
        assert_eq!(r0.actual_utility.unwrap().to_bits(), 0xBFD8C4CF6DF5B445);
        assert_eq!(r0.cost_r.unwrap().to_bits(), 0x3FAB31612A8D8A21);
        // c-btc-0001 input literal -0.38701234567890123 and the oracle's
        // emitted -0.38701234567890125 are the SAME double: shortest-repr
        // JSON round-trip is bit-preserving.
        assert_eq!(
            (-0.38701234567890123f64).to_bits(),
            r0.actual_utility.unwrap().to_bits()
        );
    }

    /// The manifest row has exactly the 19 oracle fields (no more, no less).
    #[test]
    fn row_has_exactly_nineteen_fields() {
        let r = &expected_rows()[0];
        assert_eq!(JoinedCandidateRow::FIELD_COUNT, 19);
        let _ = (
            &r.symbol,
            &r.candidate_id,
            &r.expert_id,
            &r.direction,
            &r.birth_time,
            &r.gap_status,
            &r.legal_hindsight_gap,
            &r.actual_utility,
            &r.best_utility,
            &r.tie_cardinality,
            &r.endpoint,
            &r.label_status,
            &r.horizon_bars,
            &r.cost_r,
            &r.funding_r,
            &r.mae_r,
            &r.mfe_r,
            &r.ambiguous_bars,
            &r.epistemic_class,
        );
    }

    /// Symbols iterate sorted (BTCUSDT before SOLUSDT); rows keep the
    /// gap-record order per symbol.
    #[test]
    fn symbols_sorted_and_rows_in_gap_order() {
        let rows = join_dataset(fixture());
        let symbols: Vec<&str> = rows.iter().map(|r| r.symbol.as_str()).collect();
        assert_eq!(
            symbols,
            vec![
                "BTCUSDT", "BTCUSDT", "BTCUSDT", "BTCUSDT", "BTCUSDT", "BTCUSDT", "SOLUSDT",
                "SOLUSDT"
            ]
        );
        let btc_cids: Vec<&str> = rows
            .iter()
            .take(6)
            .map(|r| r.candidate_id.as_str())
            .collect();
        assert_eq!(
            btc_cids,
            vec![
                "c-btc-0001",
                "c-btc-0002",
                "c-btc-0003",
                "c-btc-0004",
                "c-btc-0005",
                "c-btc-0006"
            ]
        );
    }

    /// The 8-cell + NO_TRADE + ACTUAL grid: an on-grid ACTUAL geometry
    /// collapses the declared variants to 8 distinct grid cells (the oracle's
    /// manifest cardinality 10, measured on `tools/regret.py`); an off-grid
    /// geometry yields 9 (cardinality 11).
    #[test]
    fn opportunity_set_is_the_manifest_grid() {
        let on_grid = regret::generate_legal_actions(
            &serde_json::json!({
                "target_r": 2.0, "expiry_bars": 24,
            })
            .as_object()
            .unwrap()
            .clone(),
        );
        let utils: HashMap<String, f64> = HashMap::new();
        let set = opportunity_set(&on_grid, &utils);
        assert_eq!(set.len(), 10);
        assert_eq!(set[0].kind, "NO_TRADE");
        assert_eq!(set[0].provenance, "DECLARED_VARIANT");
        assert_eq!(set[1].kind, "GEOMETRY_VARIANT");
        assert_eq!(set[1].provenance, "ACTUAL");
        let declared: Vec<&OpportunityCell> = set
            .iter()
            .filter(|c| c.provenance == "DECLARED_VARIANT" && c.kind == "GEOMETRY_VARIANT")
            .collect();
        assert_eq!(declared.len(), 8);
        assert!(declared.iter().all(|c| c.utility.is_none()));

        let off_grid = regret::generate_legal_actions(
            &serde_json::json!({
                "atr_ref": 123.5, "size": 1.0,
            })
            .as_object()
            .unwrap()
            .clone(),
        );
        assert_eq!(off_grid.actions.len(), 11);
        let set2 = opportunity_set(&off_grid, &utils);
        assert_eq!(set2.len(), 11);
        let declared2: Vec<&OpportunityCell> = set2
            .iter()
            .filter(|c| c.provenance == "DECLARED_VARIANT" && c.kind == "GEOMETRY_VARIANT")
            .collect();
        assert_eq!(declared2.len(), 9);
    }

    /// Per-cell utilities ride along the opportunity set once the reduced
    /// cube table has them (a candidate whose cell is absent reads None).
    #[test]
    fn opportunity_set_carries_per_cell_utilities() {
        let manifest: Manifest = regret::generate_legal_actions(
            &serde_json::json!({
                "target_r": 2.0, "expiry_bars": 24,
            })
            .as_object()
            .unwrap()
            .clone(),
        );
        let mut utils = HashMap::new();
        utils.insert(manifest.actions[0].action_id.clone(), 0.0); // NO_TRADE
        utils.insert(manifest.actions[1].action_id.clone(), -0.38701234567890125); // ACTUAL
        utils.insert(manifest.actions[2].action_id.clone(), 0.6771358024691356);
        let set = opportunity_set(&manifest, &utils);
        assert_eq!(set[0].utility, Some(0.0));
        assert_eq!(set[1].utility, Some(-0.38701234567890125));
        assert_eq!(set[2].utility, Some(0.6771358024691356));
        assert!(set[3..].iter().all(|c| c.utility.is_none()));
    }
}
