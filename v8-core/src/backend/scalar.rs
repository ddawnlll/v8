//! Backend-0: the deterministic scalar reference (D-096).
//!
//! This is the single-path scalar replay kernel moved out of
//! `simulator::ReplayKernel` (SIMULATION_TRUTH_SPEC; COMPUTE_CORE_SPEC §4),
//! byte-for-byte — Backend-0 is the in-core reference. The frozen Python
//! `src/v8/` remains the parity oracle (D-087). No parallelism exists here:
//! task parallelism and SIMD are Backend-1, a separate card.
//!
//! The replay semantics are unchanged (the doc from the source module is
//! preserved verbatim):
//!
//! - R-multiples only; one R = the geometry's declared `risk_unit`
//!   (`atr_ref`, else `entry * risk_frac`); a stop-out is exactly -1R - cost.
//! - FILL_AT_BAR_CLOSE entry at the first bar's close; FILL_AT_LIMIT barrier
//!   entry (fill = the limit exactly, never-filling orders never enter).
//! - The entry bar is inspected for a FILL only, never for exits.
//! - Funding settles BEFORE any order/exit event (`SETTLEMENT_BEFORE_ORDERS`),
//!   scalar path `sign * funding_rate_r` per crossed boundary, schedule path
//!   `sign * entry_price * rate / unit`, missing boundary fails closed.
//! - STOP_FIRST on same-bar ambiguity with `ambiguous_bars` counted; gap-through
//!   exits fill at the opening price (SIMULATION_TRUTH_SPEC §6): a stop uses the
//!   WORSE of the barrier and the bar open, a target the BETTER of the barrier
//!   and the bar open — gaps are symmetric at the declared barrier (issue #71);
//!   THESIS_INVALIDATED / TIME_EXIT / EXPIRY exit at bar close; `mae_r`/`mfe_r`
//!   are recorded BEFORE the exit decision.
//! - `net_r = realized_r + remaining*(sign*(exit-entry)/unit) - cost_r -
//!   funding_paid_r`; cost resolves through one `cost_r(entry, unit)`.
//!
//! The post-entry thesis is a compiled predicate (PREDICATE_IR_SPEC) evaluated
//! at the stepped bar from the feature store — never a Python closure
//! (no-callback invariant, D-078). Fail-open semantics are normative: an
//! unreadable thesis is not a dead thesis.

use serde_json::Value;

use crate::backend::{ReplayCell, ReplayKernel};
use crate::data::{Dataset, SymbolBars};
use crate::experts::predicate::{self, FeatCtx};
use crate::simulator::{risk_unit, validate_geometry, Draft, FillPolicy, Outcome, HOUR_NS};
use crate::state::FeatureStore;

/// The per-symbol scalar kernel: the moved `simulator::ReplayKernel` struct,
/// unchanged. One `run` per (candidate, action) cell.
pub struct ScalarKernel<'a> {
    pub round_trip_cost_r: f64,
    pub funding_rate_r: f64,
    pub funding_hours: i64,
    pub fill_policy: FillPolicy,
    pub funding_schedule: &'a [(i64, f64)],
    pub round_trip_cost_bps: Option<f64>,
    pub bars: &'a SymbolBars,
    pub store: &'a FeatureStore,
}

impl<'a> ScalarKernel<'a> {
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

    fn apply_funding(
        &self,
        pos: &Pos,
        draft: &Draft,
        t_ns: i64,
        unit: f64,
    ) -> Result<(Pos, i64), String> {
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
                let rate = self
                    .funding_schedule
                    .iter()
                    .find(|(b, _)| b == boundary)
                    .map(|(_, r)| *r)
                    .ok_or_else(|| format!("funding schedule missing boundary {boundary}"))?;
                c += sign * pos.entry_price * rate / unit;
            }
            c
        } else {
            sign * self.funding_rate_r * new as f64
        };
        Ok((
            Pos {
                settlements: total,
                funding_paid_r: pos.funding_paid_r + cost,
                ..pos.clone()
            },
            new,
        ))
    }

    /// Step one bar; returns (closed, endpoint, net_r, label, next_pos).
    #[allow(clippy::too_many_arguments)]
    fn step(
        &self,
        pos: &Pos,
        draft: &Draft,
        i: usize,
        thesis_valid: bool,
        bar_time: Option<i64>,
        unit: f64,
    ) -> Result<
        (
            bool,
            Option<String>,
            Option<f64>,
            Option<String>,
            Pos,
            i64,
            f64,
        ),
        String,
    > {
        // Defense in depth, not a replacement (issue #70): `run` validates at
        // admission, but the oracle validates the same draft at step() entry
        // too — a draft that reaches a per-bar step must be geometrically
        // sane, never silently book a target_r<0 loss as a TARGET endpoint.
        validate_geometry(draft)?;
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
            if draft.has_geom("breakeven_roll_at_mfe_r")
                && !stop_rolled
                && mfe_r
                    >= draft
                        .geom_f64("breakeven_roll_at_mfe_r")
                        .unwrap_or(f64::MAX)
            {
                let margin = draft
                    .geom_f64("breakeven_margin_r")
                    .unwrap_or(self.cost_r(entry, unit).unwrap_or(self.round_trip_cost_r));
                stop_level = Some(entry - sign * margin * unit);
                stop_rolled = true;
            }
            if draft.has_geom("trail_stop_atr") {
                let k = draft.geom_f64("trail_stop_atr").unwrap_or(0.0);
                let trail = entry + sign * (mfe_r - k) * unit;
                stop_level = Some(match stop_level {
                    None => {
                        if long {
                            base_stop.max(trail)
                        } else {
                            base_stop.min(trail)
                        }
                    }
                    Some(sl) => {
                        if long {
                            sl.max(trail)
                        } else {
                            sl.min(trail)
                        }
                    }
                });
            }
            next.stop_level = stop_level;
            next.stop_rolled = stop_rolled;
            if draft.geom_f64("scale_out_ratio").unwrap_or(0.0) > 0.0
                && !pos.scaled_out
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

        // Gap-through exits fill at the opening price (SIMULATION_TRUTH_SPEC
        // §6) — symmetric at the declared barrier (issue #71): a stop books
        // the WORSE of barrier and open (adverse gap paid in full); a target
        // books the BETTER of barrier and open (favorable gap credited in
        // full). Before #71 the target clipped at the barrier, so an equal
        // favorable gap booked far less R than the adverse gap it mirrored.
        let exit_price = match endpoint.unwrap() {
            "EXPIRY" | "THESIS_INVALIDATED" | "TIME_EXIT" => self.bars.closes[i],
            "TARGET" => {
                let open_ = self.bars.opens[i];
                if long {
                    target.max(open_)
                } else {
                    target.min(open_)
                }
            }
            _ => {
                let open_ = self.bars.opens[i];
                if long {
                    stop.min(open_)
                } else {
                    stop.max(open_)
                }
            }
        };
        let cost = self.cost_r(entry, unit)?;
        let net_r = pos.realized_r + pos.remaining * (sign * (exit_price - entry) / unit)
            - cost
            - pos.funding_paid_r;
        let label = if matches!(endpoint.unwrap(), "TARGET" | "STOP" | "THESIS_INVALIDATED") {
            "MATURE"
        } else {
            "RIGHT_CENSORED"
        };
        Ok((
            true,
            Some(endpoint.unwrap().to_string()),
            Some(net_r),
            Some(label.to_string()),
            next,
            new_settlements,
            1.0,
        ))
    }

    /// The never-entered convention (oracle ledger: a candidate that never
    /// fires its entry trigger is a non-trade — `NOT_EXECUTED`, endpoint
    /// INVALIDATED_BEFORE_TRIGGER when invalidated while waiting / EXPIRY when
    /// the tape ends with the trigger unfired, net_r 0.0).
    fn never_entered(&self, endpoint: &str, wait_end: usize) -> Outcome {
        Outcome {
            endpoint: endpoint.to_string(),
            net_r: 0.0,
            label_status: "NOT_EXECUTED".into(),
            horizon_bars: 0,
            label_available_time: self.bars.available_times[wait_end - 1],
            mae_r: 0.0,
            mfe_r: 0.0,
            ambiguous_bars: 0,
            entry_price: 0.0,
            risk_unit_price: 0.0,
            market_move_r: 0.0,
            cost_r: 0.0,
            funding_r: 0.0,
        }
    }

    /// The D-057 trigger wait over `[start, end)`: the first bar whose close
    /// confirms the declared `trigger_ref` — entry is then the NEXT bar's
    /// close (the oracle triggers on bar j and enters at j+1). A bar whose
    /// range breaches a declared pre-entry invalidation ref (`prior_low_ref`
    /// LONG / `prior_high_ref` SHORT) ends the wait as invalidated (fail-open
    /// when no invalidation ref is declared); the would-be entry bar is
    /// re-checked for the same breach. `Expired` when the window ends with the
    /// trigger unfired.
    fn trigger_entry(
        &self,
        draft: &Draft,
        start: usize,
        end: usize,
    ) -> Result<TriggerWait, String> {
        let long = draft.direction == "LONG";
        let low_ref = draft.geom_f64("prior_low_ref");
        let high_ref = draft.geom_f64("prior_high_ref");
        let breached = |i: usize| -> bool {
            (long && low_ref.map(|r| self.bars.lows[i] < r).unwrap_or(false))
                || (!long && high_ref.map(|r| self.bars.highs[i] > r).unwrap_or(false))
        };
        for j in start..end {
            if breached(j) {
                return Ok(TriggerWait::Invalidated);
            }
            if trigger_confirmed(draft, self.bars.closes[j])? {
                let entry_idx = j + 1;
                if entry_idx >= end {
                    // Confirmed on the final bar: no entry bar before the
                    // window ends — the candidate never enters (the oracle's
                    // INVALIDATED_BEFORE_TRIGGER never-entered convention).
                    return Ok(TriggerWait::Invalidated);
                }
                if breached(entry_idx) {
                    return Ok(TriggerWait::Invalidated);
                }
                return Ok(TriggerWait::Confirmed(
                    entry_idx,
                    self.bars.closes[entry_idx],
                ));
            }
        }
        Ok(TriggerWait::Expired)
    }

    /// Batch counterfactual replay of one (candidate, action) cell.
    ///
    /// `start` is the entry bar (absolute); `end` bounds the read window. The
    /// kernel reads no bar outside `[start, min(end, start + expiry + 1)]`
    /// (OUTCOME_CUBE_SPEC §5) — except the D-057 trigger wait, which runs to
    /// the CALLER's `end` (a PENDING candidate is re-checked each bar until it
    /// confirms, invalidates, or the tape ends, exactly like the oracle's
    /// epilogue).
    pub fn run(
        &self,
        draft: &Draft,
        start: usize,
        end: usize,
        thesis: Option<&Value>,
    ) -> Result<Outcome, String> {
        validate_geometry(draft)?;
        if start >= end {
            return Ok(Outcome {
                endpoint: "EXPIRY".into(),
                net_r: 0.0,
                label_status: "RIGHT_CENSORED".into(),
                horizon_bars: 0,
                label_available_time: 0,
                mae_r: 0.0,
                mfe_r: 0.0,
                ambiguous_bars: 0,
                entry_price: 0.0,
                risk_unit_price: 0.0,
                market_move_r: 0.0,
                cost_r: 0.0,
                funding_r: 0.0,
            });
        }
        let expiry = draft.geom_i64("expiry_bars").unwrap_or(0) as usize;
        // The trigger wait (D-057) runs to the caller's window end; the expiry
        // horizon below bounds only the post-entry exit loop.
        let wait_end = end;
        let end = end.min(start + expiry + 1);

        let entry = match self.fill_policy {
            FillPolicy::BarClose => {
                // D-057 entry-trigger gate (issue #67): a draft declaring
                // `trigger_ref` enters only on the book's close-confirmation.
                // The candidate stays PENDING until a close clears the trigger,
                // a declared pre-entry invalidation ref is breached, or the
                // window ends — fail-open on absent ref (D-082) keeps the
                // unconditional next-bar-close entry for experts without a
                // trigger.
                if draft.has_geom("trigger_ref") {
                    match self.trigger_entry(draft, start, wait_end)? {
                        TriggerWait::Confirmed(entry_idx, price) => {
                            let entry_time = self.bars.available_times[entry_idx];
                            let horizon = wait_end.min(entry_idx + 1 + expiry + 1);
                            return self.exit_loop(
                                draft,
                                entry_idx,
                                entry_idx + 1,
                                horizon,
                                thesis,
                                price,
                                entry_time,
                            );
                        }
                        TriggerWait::Invalidated => {
                            return Ok(self.never_entered("INVALIDATED_BEFORE_TRIGGER", wait_end));
                        }
                        TriggerWait::Expired => {
                            return Ok(self.never_entered("EXPIRY", wait_end));
                        }
                    }
                }
                self.bars.closes[start]
            }
            FillPolicy::Limit => {
                let limit = draft.geom_f64("limit_price").ok_or_else(|| {
                    "FILL_AT_LIMIT requires risk_geometry[limit_price]".to_string()
                })?;
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
                            endpoint: "EXPIRY".into(),
                            net_r: 0.0,
                            label_status: "NOT_EXECUTED".into(),
                            horizon_bars: 0,
                            label_available_time: self.bars.available_times[end - 1],
                            mae_r: 0.0,
                            mfe_r: 0.0,
                            ambiguous_bars: 0,
                            entry_price: 0.0,
                            risk_unit_price: 0.0,
                            market_move_r: 0.0,
                            cost_r: 0.0,
                            funding_r: 0.0,
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
    fn exit_loop(
        &self,
        draft: &Draft,
        _entry_idx: usize,
        from: usize,
        end: usize,
        thesis: Option<&Value>,
        entry: f64,
        entry_time: i64,
    ) -> Result<Outcome, String> {
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
                        live_window: &|name, n| {
                            crate::state::live_window_feature(self.store, t, name, n)
                        },
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
        let net = pos.realized_r + pos.remaining * (sign * (self.bars.closes[last] - entry) / unit)
            - cost
            - pos.funding_paid_r;
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

/// The entry-trigger contract (D-057): a draft declaring
/// `risk_geometry['trigger_ref']` (an absolute price, frozen at detection)
/// enters only on the book's close-confirmation — `trigger_side`
/// CLOSE_ABOVE / CLOSE_BELOW (Ch14.2 "entry only on a CLOSE beyond the
/// trigger"), the side derived from direction when the side key is absent.
/// Fail-open on absent ref (D-082): no `trigger_ref` -> the gate is open and
/// entry is unconditional. An unsupported `trigger_side` value fails CLOSED
/// (the oracle raises `ValueError` for the same input).
fn trigger_confirmed(draft: &Draft, close: f64) -> Result<bool, String> {
    let ref_price = match draft.geom_f64("trigger_ref") {
        Some(p) => p,
        None => return Ok(true),
    };
    let above = match draft
        .risk_geometry
        .get("trigger_side")
        .and_then(|v| v.as_str())
    {
        None => draft.direction != "SHORT",
        Some("CLOSE_ABOVE") => true,
        Some("CLOSE_BELOW") => false,
        Some(s) => {
            return Err(format!(
                "unsupported trigger_side {s:?} — must be CLOSE_ABOVE or CLOSE_BELOW (D-057)"
            ))
        }
    };
    Ok(if above {
        close > ref_price
    } else {
        close < ref_price
    })
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

/// The outcome of a D-057 entry-trigger wait.
enum TriggerWait {
    /// (entry bar index, entry price at the entry bar's close) — the trigger
    /// confirmed on the prior bar.
    Confirmed(usize, f64),
    /// A declared pre-entry invalidation ref was breached while waiting, or
    /// the confirmed trigger had no entry bar left in the window.
    Invalidated,
    /// The window ended with the trigger unfired.
    Expired,
}

/// Backend-0 batch backend: evaluates a cell batch against a `Dataset` with
/// the scalar reference kernel, sequentially, in cell order. The `stores` are
/// the K2 per-symbol feature stores built once per request (never per cell —
/// COMPUTE_CORE_SPEC §5).
pub struct ScalarBackend<'a> {
    pub round_trip_cost_r: f64,
    pub funding_rate_r: f64,
    pub funding_hours: i64,
    pub fill_policy: FillPolicy,
    pub funding_schedule: &'a [(i64, f64)],
    pub round_trip_cost_bps: Option<f64>,
    pub stores: &'a [FeatureStore],
}

impl<'a> ReplayKernel for ScalarBackend<'a> {
    fn evaluate(
        &self,
        dataset: &Dataset,
        cells: &[ReplayCell],
        output: &mut [Outcome],
    ) -> Result<(), String> {
        if cells.len() != output.len() {
            return Err(format!(
                "scalar evaluate: cell batch size {} does not match output size {}",
                cells.len(),
                output.len()
            ));
        }
        for (cell, slot) in cells.iter().zip(output.iter_mut()) {
            let bars = dataset
                .bars
                .iter()
                .find(|b| b.symbol == cell.symbol)
                .ok_or_else(|| format!("scalar evaluate: no bars for symbol {}", cell.symbol))?;
            let store = self
                .stores
                .iter()
                .find(|s| s.symbol == cell.symbol)
                .ok_or_else(|| format!("scalar evaluate: no store for symbol {}", cell.symbol))?;
            let kernel = ScalarKernel {
                round_trip_cost_r: self.round_trip_cost_r,
                funding_rate_r: self.funding_rate_r,
                funding_hours: self.funding_hours,
                fill_policy: self.fill_policy,
                funding_schedule: self.funding_schedule,
                round_trip_cost_bps: self.round_trip_cost_bps,
                bars,
                store,
            };
            *slot = kernel.run(&cell.draft, cell.start, cell.end, cell.thesis.as_ref())?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A minimal columnar fixture: the entry bar followed by one gap bar.
    fn bars_fixture(
        symbol: &str,
        opens: Vec<f64>,
        highs: Vec<f64>,
        lows: Vec<f64>,
        closes: Vec<f64>,
    ) -> SymbolBars {
        let n = closes.len();
        let base = 1_750_000_000_000_000_000i64;
        SymbolBars {
            symbol: symbol.to_string(),
            opens,
            highs,
            lows,
            closes,
            volumes: vec![1.0; n],
            event_times: (0..n).map(|i| base + (i as i64) * HOUR_NS).collect(),
            available_times: (0..n)
                .map(|i| base + (i as i64) * HOUR_NS + 1_000_000_000)
                .collect(),
            ingested_times: vec![0; n],
            venue_sequences: (0..n).map(|i| i as i64 + 1).collect(),
            event_ids: (0..n).map(|i| format!("{symbol}:{}", i + 1)).collect(),
            row_indices: (0..n).collect(),
        }
    }

    /// 1R geometry at atr_ref=10 with a 2-bar horizon.
    fn gap_draft(direction: &str) -> Draft {
        let mut g = serde_json::Map::new();
        g.insert("atr_ref".to_string(), serde_json::json!(10.0));
        g.insert("target_r".to_string(), serde_json::json!(1.0));
        g.insert("stop_r".to_string(), serde_json::json!(1.0));
        g.insert("expiry_bars".to_string(), serde_json::json!(2));
        Draft {
            direction: direction.to_string(),
            birth_time: 0,
            risk_geometry: g,
        }
    }

    fn kernel<'a>(bars: &'a SymbolBars, store: &'a FeatureStore) -> ScalarKernel<'a> {
        ScalarKernel {
            round_trip_cost_r: 0.07,
            funding_rate_r: 0.0,
            funding_hours: 0,
            fill_policy: FillPolicy::BarClose,
            funding_schedule: &[],
            round_trip_cost_bps: None,
            bars,
            store,
        }
    }

    #[test]
    fn favorable_gap_target_fills_at_open_not_barrier() {
        // LONG, entry 100, atr=10, stop_r=target_r=1.0 -> stop 90, target 110.
        // Bar 0 is the entry bar (close 100); bar 1 gaps +30 straight through
        // the 110 target (open 130). Gap-through exits fill at the opening
        // price (SIMULATION_TRUTH_SPEC §6): the target books the BETTER of
        // barrier and open — net_r = (130-100)/10 - 0.07 = +2.93R. Pre-fix the
        // fill was clipped at the barrier (110) for +0.93R, the favorable leg
        // of the issue #71 asymmetry.
        let bars = bars_fixture(
            "SOLUSDT",
            vec![100.0, 130.0],
            vec![100.0, 130.0],
            vec![100.0, 130.0],
            vec![100.0, 130.0],
        );
        let store = FeatureStore::build(&bars, &[]);
        let out = kernel(&bars, &store)
            .run(&gap_draft("LONG"), 0, bars.closes.len(), None)
            .unwrap();
        assert_eq!(out.endpoint, "TARGET");
        assert_eq!(out.entry_price, 100.0);
        assert!(
            (out.net_r - 2.93).abs() < 1e-9,
            "favorable gap must fill at the open 130, not clip at the target: net_r = {}",
            out.net_r
        );
    }

    #[test]
    fn adverse_gap_stop_fills_at_open_in_full() {
        // The adverse mirror: open 70 gaps 20 below the 90 stop — the stop
        // books the WORSE of barrier and open, net_r = (70-100)/10 - 0.07 =
        // -3.07R, unchanged by the fix (the adverse leg was never clipped).
        let bars = bars_fixture(
            "SOLUSDT",
            vec![100.0, 70.0],
            vec![100.0, 70.0],
            vec![100.0, 70.0],
            vec![100.0, 70.0],
        );
        let store = FeatureStore::build(&bars, &[]);
        let out = kernel(&bars, &store)
            .run(&gap_draft("LONG"), 0, bars.closes.len(), None)
            .unwrap();
        assert_eq!(out.endpoint, "STOP");
        assert!(
            (out.net_r + 3.07).abs() < 1e-9,
            "adverse gap must still book -3.07R at the open: net_r = {}",
            out.net_r
        );
    }

    #[test]
    fn equal_opposite_gaps_book_equal_opposite_r() {
        // The issue's core claim: equal-magnitude opposite gaps must book
        // equal-magnitude results. A +/-30 unit gap around a 1R barrier is
        // symmetric only when both directions fill at the open: |net_r| = 3R
        // +/- cost in either direction. Pre-fix the favorable gap was clipped
        // at the barrier — a 3.30R asymmetry on the issue's numbers.
        let fav = bars_fixture(
            "SOLUSDT",
            vec![100.0, 130.0],
            vec![100.0, 130.0],
            vec![100.0, 130.0],
            vec![100.0, 130.0],
        );
        let fav_store = FeatureStore::build(&fav, &[]);
        let out_fav = kernel(&fav, &fav_store)
            .run(&gap_draft("LONG"), 0, fav.closes.len(), None)
            .unwrap();

        let adv = bars_fixture(
            "SOLUSDT",
            vec![100.0, 70.0],
            vec![100.0, 70.0],
            vec![100.0, 70.0],
            vec![100.0, 70.0],
        );
        let adv_store = FeatureStore::build(&adv, &[]);
        let out_adv = kernel(&adv, &adv_store)
            .run(&gap_draft("LONG"), 0, adv.closes.len(), None)
            .unwrap();

        // Both fills happen at the open, so the pair differs from the clean
        // +/-3R only by one round-trip cost each: fav + adv == -2*cost (-0.14).
        // Pre-fix the favorable leg was clipped at the barrier, so the pair
        // summed to 0.93 + (-3.07) = -2.14R — the issue's measured asymmetry.
        assert!(
            (out_fav.net_r + out_adv.net_r + 2.0 * 0.07).abs() < 1e-9,
            "equal opposite gaps must differ from +/-3R by one cost each: fav {} adv {}",
            out_fav.net_r,
            out_adv.net_r
        );
    }

    #[test]
    fn short_gaps_symmetric_at_declared_barrier() {
        // SHORT, entry 100, stop 110, target 90. Adverse gap open 130 -> exit
        // at open (max(stop, open) = 130) = -3.07R; favorable gap open 70 ->
        // exit at open (min(target, open) = 70) = +2.93R. Equal magnitudes.
        let adv = bars_fixture(
            "SOLUSDT",
            vec![100.0, 130.0],
            vec![100.0, 130.0],
            vec![100.0, 130.0],
            vec![100.0, 130.0],
        );
        let adv_store = FeatureStore::build(&adv, &[]);
        let out_adv = kernel(&adv, &adv_store)
            .run(&gap_draft("SHORT"), 0, adv.closes.len(), None)
            .unwrap();
        assert_eq!(out_adv.endpoint, "STOP");
        assert!(
            (out_adv.net_r + 3.07).abs() < 1e-9,
            "short adverse gap must book -3.07R: net_r = {}",
            out_adv.net_r
        );

        let fav = bars_fixture(
            "SOLUSDT",
            vec![100.0, 70.0],
            vec![100.0, 70.0],
            vec![100.0, 70.0],
            vec![100.0, 70.0],
        );
        let fav_store = FeatureStore::build(&fav, &[]);
        let out_fav = kernel(&fav, &fav_store)
            .run(&gap_draft("SHORT"), 0, fav.closes.len(), None)
            .unwrap();
        assert_eq!(out_fav.endpoint, "TARGET");
        assert!(
            (out_fav.net_r - 2.93).abs() < 1e-9,
            "short favorable gap must book +2.93R: net_r = {}",
            out_fav.net_r
        );
    }
}
