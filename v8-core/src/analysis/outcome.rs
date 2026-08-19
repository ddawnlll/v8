//! The reconciliation outcome surface (issue #121): the exact projection of
//! the simulator Outcome that ledger reconciliation compares — the ten
//! RECONCILE fields from `tools/regret.py` (frozen oracle, FT010).

use crate::simulator::Outcome;

/// Ledger reconciliation float tolerance (mirror of `tools/regret.py`
/// `RECONCILE_TOLERANCE`).
pub const RECONCILE_TOLERANCE: f64 = 1e-12;

/// Exact-comparison fields (mirror of `tools/regret.py`
/// `RECONCILE_EXACT_FIELDS`): compared with strict equality.
#[allow(dead_code)] // pinned by `field_set_is_exactly_the_ten`; used by the S6 reconcile port
pub const RECONCILE_EXACT_FIELDS: [&str; 4] =
    ["endpoint", "label_status", "horizon_bars", "ambiguous_bars"];

/// Float-comparison fields (mirror of `tools/regret.py`
/// `RECONCILE_FLOAT_FIELDS`): compared with `|a - b| <= RECONCILE_TOLERANCE`.
#[allow(dead_code)] // pinned by `field_set_is_exactly_the_ten`; used by the S6 reconcile port
pub const RECONCILE_FLOAT_FIELDS: [&str; 6] = [
    "net_r",
    "entry_price",
    "risk_unit_price",
    "mae_r",
    "mfe_r",
    "market_move_r",
];

/// Number of outcome fields ledger reconciliation compares (mirror of
/// `tools/regret.py` RECONCILE_EXACT_FIELDS + RECONCILE_FLOAT_FIELDS).
///
/// Field set (ten):
/// - exact: `endpoint`, `label_status`, `horizon_bars`, `ambiguous_bars`
/// - float (tolerance `RECONCILE_TOLERANCE`): `net_r`, `entry_price`,
///   `risk_unit_price`, `mae_r`, `mfe_r`, `market_move_r`
///
/// `label_available_time` is NOT compared (FT010 excluded field).
#[allow(dead_code)]
pub const RECONCILE_FIELD_COUNT: usize = 10;

/// The reconciliation surface of one replayed action (issue #121): the ten
/// compared fields plus identity. The identity strings (`candidate_id`,
/// `action_id`) are bit-encoded and excluded from value comparison
/// (PARITY_AND_IDENTITY_SPEC §3).
#[allow(dead_code)] // consumed by the S6 reconcile port (issue #122)
#[derive(Debug, Clone)]
pub struct OutcomeSurface {
    pub candidate_id: String,
    pub action_id: String,
    pub endpoint: String,
    pub label_status: String,
    pub horizon_bars: i64,
    pub ambiguous_bars: i64,
    pub net_r: f64,
    pub entry_price: f64,
    pub risk_unit_price: f64,
    pub mae_r: f64,
    pub mfe_r: f64,
    pub market_move_r: f64,
}

#[allow(dead_code)] // consumed by the S6 reconcile port (issue #122)
impl OutcomeSurface {
    /// True iff the ten value fields agree: exact fields strictly equal,
    /// float fields within `RECONCILE_TOLERANCE` (mirror of
    /// `tools/regret.py:reconcile_actual_actions`). Identity fields are
    /// ignored (PARITY_AND_IDENTITY_SPEC §3).
    pub fn values_match(&self, other: &OutcomeSurface) -> bool {
        self.endpoint == other.endpoint
            && self.label_status == other.label_status
            && self.horizon_bars == other.horizon_bars
            && self.ambiguous_bars == other.ambiguous_bars
            && (self.net_r - other.net_r).abs() <= RECONCILE_TOLERANCE
            && (self.entry_price - other.entry_price).abs() <= RECONCILE_TOLERANCE
            && (self.risk_unit_price - other.risk_unit_price).abs() <= RECONCILE_TOLERANCE
            && (self.mae_r - other.mae_r).abs() <= RECONCILE_TOLERANCE
            && (self.mfe_r - other.mfe_r).abs() <= RECONCILE_TOLERANCE
            && (self.market_move_r - other.market_move_r).abs() <= RECONCILE_TOLERANCE
    }
}

#[allow(dead_code)] // consumed by the S6 reconcile port (issue #122)
impl Outcome {
    /// The exact projection of a replay Outcome onto the ten reconciliation
    /// fields (mirror of `tools/regret.py:reconcile_actual_actions`, FT010).
    /// `label_available_time` — the one field `Outcome` carries that
    /// reconciliation does not compare — never enters the surface.
    pub fn reconcile_surface(&self, candidate_id: &str, action_id: &str) -> OutcomeSurface {
        OutcomeSurface {
            candidate_id: candidate_id.to_string(),
            action_id: action_id.to_string(),
            endpoint: self.endpoint.clone(),
            label_status: self.label_status.clone(),
            horizon_bars: self.horizon_bars,
            ambiguous_bars: self.ambiguous_bars,
            net_r: self.net_r,
            entry_price: self.entry_price,
            risk_unit_price: self.risk_unit_price,
            mae_r: self.mae_r,
            mfe_r: self.mfe_r,
            market_move_r: self.market_move_r,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn outcome() -> Outcome {
        Outcome {
            endpoint: "TARGET".into(),
            net_r: 1.2345,
            label_status: "MATURE".into(),
            horizon_bars: 7,
            label_available_time: 1_234_567_890_123_456_789,
            mae_r: 0.5,
            mfe_r: 1.5,
            ambiguous_bars: 1,
            entry_price: 100.0,
            risk_unit_price: 5.0,
            market_move_r: 2.0,
            cost_r: 0.07,
            funding_r: 0.0,
            intervention_manifest: None,
        }
    }

    #[test]
    fn projection_carries_the_ten_fields_and_drops_excluded() {
        let s = outcome().reconcile_surface("cid-a", "act-1");
        assert_eq!(s.candidate_id, "cid-a");
        assert_eq!(s.action_id, "act-1");
        assert_eq!(s.endpoint, "TARGET");
        assert_eq!(s.label_status, "MATURE");
        assert_eq!(s.horizon_bars, 7);
        assert_eq!(s.ambiguous_bars, 1);
        assert_eq!(s.net_r, 1.2345);
        assert_eq!(s.entry_price, 100.0);
        assert_eq!(s.risk_unit_price, 5.0);
        assert_eq!(s.mae_r, 0.5);
        assert_eq!(s.mfe_r, 1.5);
        assert_eq!(s.market_move_r, 2.0);

        // The excluded field (label_available_time) cannot enter the surface:
        // two outcomes differing ONLY in it project to value-equal surfaces.
        let mut other = outcome();
        other.label_available_time += 1;
        assert!(s.values_match(&other.reconcile_surface("cid-a", "act-1")));
    }

    #[test]
    fn field_set_is_exactly_the_ten() {
        // Frozen-oracle parity: tools/regret.py RECONCILE_EXACT_FIELDS +
        // RECONCILE_FLOAT_FIELDS, no more, no less.
        let exact = ["endpoint", "label_status", "horizon_bars", "ambiguous_bars"];
        let float = [
            "net_r",
            "entry_price",
            "risk_unit_price",
            "mae_r",
            "mfe_r",
            "market_move_r",
        ];
        assert_eq!(RECONCILE_EXACT_FIELDS, exact);
        assert_eq!(RECONCILE_FLOAT_FIELDS, float);
        assert_eq!(
            RECONCILE_EXACT_FIELDS.len() + RECONCILE_FLOAT_FIELDS.len(),
            RECONCILE_FIELD_COUNT
        );
        assert_eq!(RECONCILE_FIELD_COUNT, 10);
        assert_eq!(RECONCILE_TOLERANCE, 1e-12);
    }

    #[test]
    fn values_match_iff_all_ten_within_tolerance() {
        let base = outcome();
        let s = base.reconcile_surface("cid", "act");

        // Identity is excluded from value comparison.
        assert!(s.values_match(&base.reconcile_surface("other-cid", "other-act")));

        // Every float within tolerance is equal; every float beyond is not.
        for (field, within, beyond) in [
            ("net_r", 1e-13, 1e-10),
            ("entry_price", 1e-13, 1e-10),
            ("risk_unit_price", 1e-13, 1e-10),
            ("mae_r", 1e-13, 1e-10),
            ("mfe_r", 1e-13, 1e-10),
            ("market_move_r", 1e-13, 1e-10),
        ] {
            let mut in_ok = outcome();
            let mut out_ok = outcome();
            match field {
                "net_r" => {
                    in_ok.net_r += within;
                    out_ok.net_r += beyond;
                }
                "entry_price" => {
                    in_ok.entry_price += within;
                    out_ok.entry_price += beyond;
                }
                "risk_unit_price" => {
                    in_ok.risk_unit_price += within;
                    out_ok.risk_unit_price += beyond;
                }
                "mae_r" => {
                    in_ok.mae_r += within;
                    out_ok.mae_r += beyond;
                }
                "mfe_r" => {
                    in_ok.mfe_r += within;
                    out_ok.mfe_r += beyond;
                }
                _ => {
                    in_ok.market_move_r += within;
                    out_ok.market_move_r += beyond;
                }
            }
            assert!(
                s.values_match(&in_ok.reconcile_surface("cid", "act")),
                "{field}: delta {within} within tolerance must match"
            );
            assert!(
                !s.values_match(&out_ok.reconcile_surface("cid", "act")),
                "{field}: delta {beyond} beyond tolerance must mismatch"
            );
        }

        // Any exact-field difference is a mismatch.
        for (field, value) in [
            ("endpoint", "STOP"),
            ("label_status", "RIGHT_CENSORED"),
            ("horizon_bars", "8"),
            ("ambiguous_bars", "2"),
        ] {
            let mut other = outcome();
            match field {
                "endpoint" => other.endpoint = value.to_string(),
                "label_status" => other.label_status = value.to_string(),
                "horizon_bars" => other.horizon_bars = value.parse().unwrap(),
                _ => other.ambiguous_bars = value.parse().unwrap(),
            }
            assert!(
                !s.values_match(&other.reconcile_surface("cid", "act")),
                "{field}: exact difference must mismatch"
            );
        }
    }
}
