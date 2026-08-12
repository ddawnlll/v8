//! ReplayKernel (COMPUTE_CORE_SPEC §4; SIMULATION_TRUTH_SPEC).
//!
//! The batch counterfactual path of the canonical simulator (`sim.run`), ported
//! to the compute plane. It reproduces `src/v8/simulator.py` byte-for-byte in
//! value and clock:
//!
//! - R-multiples only; one R = the geometry's declared `risk_unit`
//!   (`atr_ref`, else `entry * risk_frac`); a stop-out is exactly -1R - cost.
//! - FILL_AT_BAR_CLOSE entry at the first bar's close; FILL_AT_LIMIT barrier
//!   entry (fill = the limit exactly, never-filling orders never enter).
//! - The entry bar is inspected for a FILL only, never for exits.
//! - Funding settles BEFORE any order/exit event (`SETTLEMENT_BEFORE_ORDERS`),
//!   scalar path `sign * funding_rate_r` per crossed boundary, schedule path
//!   `sign * entry_price * rate / unit`, missing boundary fails closed.
//! - STOP_FIRST on same-bar ambiguity with `ambiguous_bars` counted; a stop
//!   fill uses the WORSE of the barrier and the bar open; a target fills at
//!   the barrier exactly; THESIS_INVALIDATED / TIME_EXIT / EXPIRY exit at bar
//!   close; `mae_r`/`mfe_r` are recorded BEFORE the exit decision.
//! - `net_r = realized_r + remaining*(sign*(exit-entry)/unit) - cost_r -
//!   funding_paid_r`; cost resolves through one `cost_r(entry, unit)`.
//!
//! The post-entry thesis is a compiled predicate (PREDICATE_IR_SPEC) evaluated
//! at the stepped bar from the feature store — never a Python closure
//! (no-callback invariant, D-078). Fail-open semantics are normative: an
//! unreadable thesis is not a dead thesis.

use serde_json::Value;

use crate::data::SymbolBars;
use crate::experts::predicate::{self, FeatCtx};
use crate::state::FeatureStore;

pub const HOUR_NS: i64 = 3_600_000_000_000;

/// The frozen Candidate geometry the kernel replays.
#[derive(Debug, Clone)]
pub struct Draft {
    pub direction: String,
    #[allow(dead_code)] // placeholder id in sim.run's cf: prefix (oracle parity)
    pub birth_time: i64,
    pub risk_geometry: serde_json::Map<String, Value>,
}

impl Draft {
    pub fn geom_f64(&self, key: &str) -> Option<f64> {
        self.risk_geometry.get(key).and_then(|v| v.as_f64())
    }
    pub fn geom_i64(&self, key: &str) -> Option<i64> {
        self.risk_geometry.get(key).and_then(|v| v.as_i64())
    }
    pub fn has_geom(&self, key: &str) -> bool {
        self.risk_geometry.contains_key(key)
    }
}

/// Price distance of one R (mirror of `simulator.risk_unit`).
pub fn risk_unit(draft: &Draft, entry_price: f64) -> Result<f64, String> {
    if let Some(atr) = draft.geom_f64("atr_ref") {
        if !(atr > 0.0) {
            return Err(format!(
                "risk_unit must be > 0 (got {atr:?}); geometry declares neither a positive atr_ref nor a positive risk_frac"));
        }
        return Ok(atr);
    }
    if draft.has_geom("risk_frac") {
        let frac = draft.geom_f64("risk_frac").ok_or_else(|| {
            format!("risk_frac must be numeric ({:?})", draft.risk_geometry.get("risk_frac"))
        })?;
        let unit = entry_price * frac;
        if !(unit > 0.0) {
            return Err(format!(
                "risk_unit must be > 0 (got {unit:?}); geometry declares neither a positive atr_ref nor a positive risk_frac"));
        }
        return Ok(unit);
    }
    Err(format!(
        "risk_unit: geometry declares neither atr_ref nor risk_frac ({:?})",
        draft.risk_geometry
    ))
}

/// Fail closed on a geometry that cannot produce a meaningful outcome
/// (mirror of `simulator.validate_geometry`).
pub fn validate_geometry(draft: &Draft) -> Result<(), String> {
    if let Some(t) = draft.geom_f64("target_r") {
        if t <= 0.0 {
            return Err(format!("risk_geometry target_r must be > 0 (got {t:?})"));
        }
    }
    if let Some(s) = draft.geom_f64("stop_r") {
        if s <= 0.0 {
            return Err(format!("risk_geometry stop_r must be > 0 (got {s:?})"));
        }
    }
    if let Some(e) = draft.geom_i64("expiry_bars") {
        if e < 1 {
            return Err(format!("risk_geometry expiry_bars must be >= 1 (got {e:?})"));
        }
    }
    Ok(())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FillPolicy {
    BarClose,
    Limit,
}

/// The counterfactual outcome (mirror of `schema.CounterfactualOutcome`, hash
/// fields excluded — identities are V8.2-encoded elsewhere).
#[derive(Debug, Clone)]
pub struct Outcome {
    pub endpoint: String,
    pub net_r: f64,
    pub label_status: String,
    pub horizon_bars: i64,
    pub label_available_time: i64,
    pub mae_r: f64,
    pub mfe_r: f64,
    pub ambiguous_bars: i64,
    pub entry_price: f64,
    pub risk_unit_price: f64,
    pub market_move_r: f64,
    /// The round-trip cost charged (R units) — the S6 phase-1 join carries it
    /// (the oracle's cube rows have cost_r/funding_r; the reconciliation
    /// surface deliberately does not).
    pub cost_r: f64,
    /// Cumulative funding paid (R units).
    pub funding_r: f64,
}

#[derive(Debug, Clone)]
struct Pos {
    entry_price: f64,
    bars_held: i64,
    mae_r: f64,
    mfe_r: f64,
    ambiguous_bars: i64,
    entry_time_ns: Option<i64>,
    settlements: i64,
    funding_paid_r: f64,
    stop_level: Option<f64>,
    stop_rolled: bool,
    scaled_out: bool,
    realized_r: f64,
    remaining: f64,
}

impl Pos {
    fn new(entry_price: f64, entry_time_ns: Option<i64>) -> Pos {
        Pos {
            entry_price,
            bars_held: 0,
            mae_r: 0.0,
            mfe_r: 0.0,
            ambiguous_bars: 0,
            entry_time_ns,
            settlements: 0,
            funding_paid_r: 0.0,
            stop_level: None,
            stop_rolled: false,
            scaled_out: false,
            realized_r: 0.0,
            remaining: 1.0,
        }
    }
}

pub struct ReplayKernel<'a> {
    pub round_trip_cost_r: f64,
    pub funding_rate_r: f64,
    pub funding_hours: i64,
    pub fill_policy: FillPolicy,
    pub funding_schedule: &'a [(i64, f64)],
    pub round_trip_cost_bps: Option<f64>,
    pub bars: &'a SymbolBars,
    pub store: &'a FeatureStore,
}

impl<'a> ReplayKernel<'a> {
    pub fn cost_r(&self, entry_price: f64, unit: f64) -> Result<f64, String> {
        match self.round_trip_cost_bps {
            None => Ok(self.round_trip_cost_r),
            Some(bps) => {
                if !(unit > 0.0) {
                    return Err(format!("cost_r: risk unit must be > 0 (got {unit:?})"));
                }
                Ok((bps / 10_000.0) * entry_price / unit)
            }
        }
    }

    fn boundaries_crossed(&self, entry_ns: i64, t_ns: i64) -> i64 {
        if t_ns <= entry_ns || self.funding_hours <= 0 {
            return 0;
        }
        let a = entry_ns / HOUR_NS;
        let b = t_ns / HOUR_NS;
        b / self.funding_hours - a / self.funding_hours
    }

    fn crossed_boundary_times(&self, entry_ns: i64, t_ns: i64) -> Vec<i64> {
        if t_ns <= entry_ns || self.funding_hours <= 0 {
            return Vec::new();
        }
        let a = entry_ns / HOUR_NS;
        let b = t_ns / HOUR_NS;
        let first = (a / self.funding_hours + 1) * self.funding_hours;
        let last = (b / self.funding_hours) * self.funding_hours;
        let mut out = Vec::new();
        let mut hour = first;
        while hour <= last {
            out.push(hour * HOUR_NS);
            hour += self.funding_hours;
        }
        out
    }

    fn apply_funding(&self, pos: &Pos, draft: &Draft, t_ns: i64,
                     unit: f64) -> Result<(Pos, i64), String> {
        let entry_ns = match pos.entry_time_ns {
            Some(t) => t,
            None => return Ok((pos.clone(), 0)),
        };
        let total = self.boundaries_crossed(entry_ns, t_ns);
        let new = total - pos.settlements;
        if new <= 0 {
            return Ok((pos.clone(), 0));
        }
        let sign = if draft.direction == "LONG" { 1.0 } else { -1.0 };
        let cost = if !self.funding_schedule.is_empty() {
            let crossed = self.crossed_boundary_times(entry_ns, t_ns);
            let mut c = 0.0;
            for boundary in crossed.iter().skip(pos.settlements as usize) {
                let rate = self.funding_schedule.iter().find(|(b, _)| b == boundary)
                    .map(|(_, r)| *r)
                    .ok_or_else(|| format!("funding schedule missing boundary {boundary}"))?;
                c += sign * pos.entry_price * rate / unit;
            }
            c
        } else {
            sign * self.funding_rate_r * new as f64
        };
        Ok((Pos {
            settlements: total,
            funding_paid_r: pos.funding_paid_r + cost,
            ..pos.clone()
        }, new))
    }

    /// Step one bar; returns (closed, endpoint, net_r, label, next_pos).
    #[allow(clippy::too_many_arguments)]
    fn step(&self, pos: &Pos, draft: &Draft, i: usize, thesis_valid: bool,
            bar_time: Option<i64>, unit: f64) -> Result<(bool, Option<String>, Option<f64>,
                                                          Option<String>, Pos, i64, f64), String> {
        let (pos, new_settlements) = match bar_time {
            Some(t) => self.apply_funding(pos, draft, t, unit)?,
            None => (pos.clone(), 0),
        };
        let long = draft.direction == "LONG";
        let sign = if long { 1.0 } else { -1.0 };
        let target_r = draft.geom_f64("target_r").unwrap_or(0.0);
        let stop_r = draft.geom_f64("stop_r").unwrap_or(0.0);
        let expiry = draft.geom_i64("expiry_bars").unwrap_or(0);
        let entry = pos.entry_price;
        let target = entry + sign * target_r * unit;
        let base_stop = match draft.geom_f64("stop_ref") {
            Some(sr) => sr,
            None => entry - sign * stop_r * unit,
        };
        let stop = pos.stop_level.unwrap_or(base_stop);
        let bars_held = pos.bars_held + 1;
        let (high, low) = (self.bars.highs[i], self.bars.lows[i]);

        let (fav, adv) = if long { (high, low) } else { (low, high) };
        let mfe_r = pos.mfe_r.max(sign * (fav - entry) / unit).max(0.0);
        let mae_r = pos.mae_r.max(sign * (entry - adv) / unit).max(0.0);

        let hit_target = if long { high >= target } else { low <= target };
        let hit_stop = if long { low <= stop } else { high >= stop };
        let ambiguous = hit_target && hit_stop;
        let ambiguous_bars = pos.ambiguous_bars + if ambiguous { 1 } else { 0 };

        let endpoint: Option<&str> = if hit_stop {
            Some("STOP")
        } else if hit_target {
            Some("TARGET")
        } else if !thesis_valid {
            Some("THESIS_INVALIDATED")
        } else if draft.has_geom("time_exit_bars")
            && bars_held >= draft.geom_i64("time_exit_bars").unwrap_or(0)
        {
            Some("TIME_EXIT")
        } else if bars_held >= expiry {
            Some("EXPIRY")
        } else {
            None
        };

        let mut next = Pos {
            bars_held,
            mae_r,
            mfe_r,
            ambiguous_bars,
            ..pos.clone()
        };
        if endpoint.is_none() {
            // --- EXEC-1/2/3 position management (bar-close, non-terminal) ---
            if draft.has_geom("pyramid_add_rules") {
                return Err("pyramid_add_rules is declared but pyramiding is P2 and not implemented (EXEC-3); a draft that requests it fails closed".to_string());
            }
            let mut stop_level = pos.stop_level;
            let mut stop_rolled = pos.stop_rolled;
            if draft.has_geom("breakeven_roll_at_mfe_r") && !stop_rolled
                && mfe_r >= draft.geom_f64("breakeven_roll_at_mfe_r").unwrap_or(f64::MAX)
            {
                let margin = draft.geom_f64("breakeven_margin_r")
                    .unwrap_or(self.cost_r(entry, unit).unwrap_or(self.round_trip_cost_r));
                stop_level = Some(entry - sign * margin * unit);
                stop_rolled = true;
            }
            if draft.has_geom("trail_stop_atr") {
                let k = draft.geom_f64("trail_stop_atr").unwrap_or(0.0);
                let trail = entry + sign * (mfe_r - k) * unit;
                stop_level = Some(match stop_level {
                    None => {
                        if long { base_stop.max(trail) } else { base_stop.min(trail) }
                    }
                    Some(sl) => {
                        if long { sl.max(trail) } else { sl.min(trail) }
                    }
                });
            }
            next.stop_level = stop_level;
            next.stop_rolled = stop_rolled;
            if draft.geom_f64("scale_out_ratio").unwrap_or(0.0) > 0.0 && !pos.scaled_out
                && mfe_r >= draft.geom_f64("scale_out_at_mfe_r").unwrap_or(f64::MAX)
            {
                let f = stop_r / (stop_r + target_r);
                let leg_r = sign * (self.bars.closes[i] - entry) / unit;
                next.remaining = pos.remaining * (1.0 - f);
                next.realized_r = pos.realized_r + pos.remaining * f * leg_r;
                next.scaled_out = true;
                return Ok((false, None, None, None, next, new_settlements, f));
            }
            return Ok((false, None, None, None, next, new_settlements, 1.0));
        }

        let exit_price = match endpoint.unwrap() {
            "EXPIRY" | "THESIS_INVALIDATED" | "TIME_EXIT" => self.bars.closes[i],
            "TARGET" => target,
            _ => {
                let open_ = self.bars.opens[i];
                if long { stop.min(open_) } else { stop.max(open_) }
            }
        };
        let cost = self.cost_r(entry, unit)?;
        let net_r = pos.realized_r
            + pos.remaining * (sign * (exit_price - entry) / unit)
            - cost - pos.funding_paid_r;
        let label = if matches!(endpoint.unwrap(), "TARGET" | "STOP" | "THESIS_INVALIDATED") {
            "MATURE"
        } else {
            "RIGHT_CENSORED"
        };
        Ok((true, Some(endpoint.unwrap().to_string()), Some(net_r),
            Some(label.to_string()), next, new_settlements, 1.0))
    }

    /// Batch counterfactual replay of one (candidate, action) cell.
    ///
    /// `start` is the entry bar (absolute); `end` bounds the read window. The
    /// kernel reads no bar outside `[start, min(end, start + expiry + 1)]`
    /// (OUTCOME_CUBE_SPEC §5).
    pub fn run(&self, draft: &Draft, start: usize, end: usize,
               thesis: Option<&Value>) -> Result<Outcome, String> {
        validate_geometry(draft)?;
        if start >= end {
            return Ok(Outcome {
                endpoint: "EXPIRY".into(), net_r: 0.0, label_status: "RIGHT_CENSORED".into(),
                horizon_bars: 0, label_available_time: 0,
                mae_r: 0.0, mfe_r: 0.0, ambiguous_bars: 0,
                entry_price: 0.0, risk_unit_price: 0.0, market_move_r: 0.0,
                cost_r: 0.0, funding_r: 0.0,
            });
        }
        let expiry = draft.geom_i64("expiry_bars").unwrap_or(0) as usize;
        let end = end.min(start + expiry + 1);

        let entry = match self.fill_policy {
            FillPolicy::BarClose => self.bars.closes[start],
            FillPolicy::Limit => {
                let limit = draft.geom_f64("limit_price")
                    .ok_or_else(|| "FILL_AT_LIMIT requires risk_geometry[limit_price]".to_string())?;
                let long = draft.direction == "LONG";
                let mut fill = None;
                for i in start..end {
                    let (hi, lo) = (self.bars.highs[i], self.bars.lows[i]);
                    if (long && lo <= limit) || (!long && hi >= limit) {
                        fill = Some((i, limit));
                        break;
                    }
                }
                match fill {
                    Some((i, p)) => {
                        let entry_time = self.bars.available_times[i];
                        return self.exit_loop(draft, i, i + 1, end, thesis, p, entry_time);
                    }
                    None => {
                        return Ok(Outcome {
                            endpoint: "EXPIRY".into(), net_r: 0.0,
                            label_status: "NOT_EXECUTED".into(), horizon_bars: 0,
                            label_available_time: self.bars.available_times[end - 1],
                            mae_r: 0.0, mfe_r: 0.0, ambiguous_bars: 0,
                            entry_price: 0.0, risk_unit_price: 0.0, market_move_r: 0.0,
                            cost_r: 0.0, funding_r: 0.0,
                        });
                    }
                }
            }
        };
        let _unit = risk_unit(draft, entry)?;
        let entry_time = self.bars.available_times[start];
        self.exit_loop(draft, start, start + 1, end, thesis, entry, entry_time)
    }

    #[allow(clippy::too_many_arguments)]
    fn exit_loop(&self, draft: &Draft, _entry_idx: usize, from: usize, end: usize,
                 thesis: Option<&Value>, entry: f64, entry_time: i64)
                 -> Result<Outcome, String> {
        let unit = risk_unit(draft, entry)?;
        let mut pos = Pos::new(entry, Some(entry_time));
        let mut horizon = 0i64;
        let mut i = from;
        while i < end {
            horizon += 1;
            let tv = match thesis {
                Some(ir) => {
                    let t = i + 1; // bar count at stepped bar i
                    let ctx = FeatCtx {
                        live: &|name| crate::state::live_feature(self.store, t, name),
                        live_window: &|name, n| crate::state::live_window_feature(self.store, t, name, n),
                        history: &|| Some(crate::state::history_window(self.store, t, 32)),
                    };
                    predicate::evaluate(ir, &draft.risk_geometry, &draft.direction, &ctx)
                }
                None => true,
            };
            let bar_time = self.bars.available_times[i];
            let (closed, endpoint, net_r, label, next, _new_settlements, _cf) =
                self.step(&pos, draft, i, tv, Some(bar_time), unit)?;
            if closed && endpoint.is_some() && net_r.is_some() {
                return Ok(Outcome {
                    endpoint: endpoint.unwrap(),
                    net_r: net_r.unwrap(),
                    label_status: label.unwrap_or_else(|| "MATURE".into()),
                    horizon_bars: horizon,
                    label_available_time: bar_time,
                    mae_r: next.mae_r,
                    mfe_r: next.mfe_r,
                    ambiguous_bars: next.ambiguous_bars,
                    entry_price: entry,
                    risk_unit_price: unit,
                    market_move_r: (self.bars.closes[i] - entry) / unit,
                    cost_r: self.cost_r(entry, unit)?,
                    funding_r: next.funding_paid_r,
                });
            }
            pos = next;
            i += 1;
        }
        // Never closed within the window: expire at the last bar's close.
        let last = end - 1;
        let sign = if draft.direction == "LONG" { 1.0 } else { -1.0 };
        let cost = self.cost_r(entry, unit)?;
        let net = pos.realized_r
            + pos.remaining * (sign * (self.bars.closes[last] - entry) / unit)
            - cost - pos.funding_paid_r;
        Ok(Outcome {
            endpoint: "EXPIRY".into(),
            net_r: net,
            label_status: "RIGHT_CENSORED".into(),
            horizon_bars: horizon,
            label_available_time: self.bars.available_times[last],
            mae_r: pos.mae_r,
            mfe_r: pos.mfe_r,
            ambiguous_bars: pos.ambiguous_bars,
            entry_price: entry,
            risk_unit_price: unit,
            market_move_r: (self.bars.closes[last] - entry) / unit,
            cost_r: cost,
            funding_r: pos.funding_paid_r,
        })
    }
}

/// Simulator configuration parsed from the compiled request's manifest.
pub struct SimulatorParams {
    pub round_trip_cost_r: f64,
    pub funding_rate_r: f64,
    pub funding_hours: i64,
    pub fill_policy: FillPolicy,
    pub round_trip_cost_bps: Option<f64>,
}

impl SimulatorParams {
    pub fn from_json(m: &Value) -> SimulatorParams {
        SimulatorParams {
            round_trip_cost_r: m.get("round_trip_cost_r").and_then(|v| v.as_f64()).unwrap_or(0.07),
            funding_rate_r: m.get("funding_rate_r").and_then(|v| v.as_f64()).unwrap_or(0.0),
            funding_hours: m.get("funding_hours").and_then(|v| v.as_i64()).unwrap_or(8),
            fill_policy: match m.get("fill_policy").and_then(|f| f.as_str()) {
                Some("FILL_AT_LIMIT") => FillPolicy::Limit,
                _ => FillPolicy::BarClose,
            },
            round_trip_cost_bps: m.get("round_trip_cost_bps").and_then(|v| v.as_f64()),
        }
    }
}
