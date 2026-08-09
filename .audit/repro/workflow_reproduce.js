// Phase 1: reproduce all 12 audit bugs (#61-#72) on the current working tree.
// One agent per issue; each writes .audit/repro/repro_N.py, runs it with the
// venv python, and saves evidence to .audit/repro/out/N.json.
export const meta = {
  name: 'reproduce-12-bugs',
  description: 'Reproduce audit issues #61-#72 on the current tree',
  phases: [{ title: 'Reproduce', detail: 'one agent per issue' }],
}

const COMMON = `You are reproducing a GitHub issue on the V8 trading-research codebase at
/Users/hootie/src/v8 (the CURRENT working tree). The issue was filed by an
earlier audit session against an OLDER tree; the working tree has since
changed (D-053/D-054/D-055 landed). So exact digits may shift — you must
reproduce the STRUCTURE of the claim (the bug mechanism), not match old
numbers, and you must report the current tree's actual numbers.

SHARED HARNESS: /Users/hootie/src/v8/.audit/repro/lab_probe.py provides:
- load_window(n_bars=2500) -> pit rows of the real BTCUSDT 1h tape (first 2500 closed bars)
- detect_drafts(rows, n_bars=2500) -> (states, drafts), drafts = [(cid, draft, birth_idx), ...] — every unique draft all 27 experts emit, byte-consistent with the lab
- run_lab(rows, **manifest_kwargs) -> (lab, report) — full Lab.run(); kwargs like round_trip_cost_r=..., store_dir=...
- executed_outcomes(lab) — outcomes with label_status != NOT_EXECUTED
- all_outcomes(lab) — every outcome
- offline_resim(rows, drafts, cost_r=..., lag=..., geometry_override=...) -> outcome dicts for the ALL-SETUPS population (no contention)
- stats(net_rs) -> {n, mean_net_r, win_rate, total_r}
- ALL_EXPERT_CLASSES, TAPE_PATH, SYMBOL='BTCUSDT', UNIVERSE, INTERVAL
The harness is already imported/usable: put '.audit/repro' on sys.path.

CONTRACT (non-negotiable):
1. Read the issue body at /Users/hootie/src/v8/.audit/issues/N.json.
2. Write a DETERMINISTIC repro script to /Users/hootie/src/v8/.audit/repro/repro_N.py
   (fixed seeds, no wall clock). It must print a single JSON object (the
   evidence) to stdout.
3. Run it with: cd /Users/hootie/src/v8 && .venv/bin/python .audit/repro/repro_N.py
   (mkdir -p .audit/repro/out first). ALSO write the same JSON to
   .audit/repro/out/N.json.
4. In your final report, return the STRUCTURED OUTPUT (issue, title, claim,
   reproduced: true/false, key_numbers, notes). Read the harness source before
   writing your script; read the source files the issue cites.

HARD RULES:
- Do NOT modify anything under src/v8/, tests/, tools/, docs/, site/,
  research/. You may write ONLY .audit/repro/repro_N.py and .audit/repro/out/N.json.
- If a code path you need is hard to reach through the harness, read the code
  and build a minimal direct test instead (e.g. construct a CandidateDraft and
  call CanonicalSimulator directly — see src/v8/simulator.py).
- Deterministic. If the issue needs a "would-have-triggered" counterfactual,
  compute it directly from the bar payloads (you have birth_idx and can load
  the bar list yourself: bars = [r for r in rows if r.channel=='kline' and
  r.payload.get('closed') is True][:2500]).
- Report the current numbers honestly. If a claim does NOT reproduce (the
  structure is absent on the current tree), set reproduced:false and explain
  what changed.`;

const SPECS = [
  {
    issue: 61,
    title: 'Cost dominates measured edge (round_trip_cost_r=0.07 is ~5.7x the edge)',
    prompt: `Claim: the raw signal edge is small and positive; the shipped round_trip_cost_r=0.07 exceeds it by a large factor, so cost is the dominant cause of the negative economics. The audit measured all-setups (offline, 1R:1R geometry, lag=2) mean net_R = +0.0123 at cost 0.0 and -0.0577 at cost 0.07.

Repro: load_window(2500); detect_drafts; offline_resim with geometry_override={'target_r':1.0,'stop_r':1.0}, lag=2, at cost_r in {0.0, 0.02, 0.04, 0.07}; print a table of mean_net_r / win_rate / total_r per cost. Also compute edge/cost ratio: edge = mean at cost 0.0, the ratio cost/edge. Also run_lab at round_trip_cost_r=0.07 and 0.0 for the executed population.

key_numbers: cost_sweep table, edge_at_cost0, mean_at_shipped_cost, cost_edge_ratio, executed_before/after.`,
  },
  {
    issue: 62,
    title: 'PENDING->TRIGGERED has no trigger predicate',
    prompt: `Claim: src/v8/lab.py PHASE 2 (around lines 635-694) advances PENDING->TRIGGERED unconditionally (only the invalidation check gates it). The experts that DO compute a trigger price (candlestick_reversal writes risk_geometry['trigger_ref']) never have it evaluated as an entry predicate. The book (Ch14.2) requires "entry only on a CLOSE beyond the trigger".

Repro: (1) static: read lab.py PHASE 2 and confirm no trigger_ref predicate is evaluated (quote the relevant lines in notes). (2) dynamic: detect_drafts; filter drafts from candlestick_reversal (they carry trigger_ref); for each, load the bars, look at the bar at birth_idx+1 (the trigger bar), and evaluate the would-be book predicate: LONG -> close > trigger_ref, SHORT -> close < trigger_ref (candlestick_reversal direction from draft.direction). Count how many candlestick_reversal drafts WOULD NOT have triggered under the book predicate yet still entered the unconditional path. Also count how many WOULD. Fraction.

key_numbers: n_candlestick_drafts, n_would_not_trigger, n_would_trigger, fraction_not_triggering.`,
  },
  {
    issue: 63,
    title: 'Stop placed at ATR multiple from entry, not the structural level',
    prompt: `Claim: src/v8/simulator.py step() computes base_stop = entry - sign*stop_r*unit (ATR multiple from entry) even when the expert froze a structural stop price (risk_geometry['stop_ref']). The structural level is ignored as a stop.

Repro: (1) static: confirm step() lines ~287-302 read target_r/stop_r and compute entry +/- stop_r*unit, never reading 'stop_ref'. (2) dynamic: take candlestick_reversal drafts from detect_drafts (they carry stop_ref), pick a few, and for each: entry = the bar at birth_idx+1's close; compute the ATR-based stop (entry - sign*stop_r*unit) vs the frozen stop_ref; measure |atr_stop - stop_ref| and how often they differ. Report a summary over all candlestick drafts (n_drafts, n_where_stop_ref_differs_from_atr_stop, mean absolute deviation in R units where unit = atr_ref). (3) On the executed population (run_lab + executed_outcomes), report MAE/MFE stats: mean/median mae_r and mfe_r, and fraction of executed outcomes with mae_r > 1.0 (the stop distance in R) — evidence that the ATR stop sits inside the noise band.

key_numbers: n_drafts, n_stop_ref_differs, mean_abs_deviation_R, executed MAE/MFE means, frac_mae_gt_1R.`,
  },
  {
    issue: 64,
    title: 'RR 1:1 and expiry_bars=8 hardcoded across the expert slate',
    prompt: `Claim: 17/25 experts ship target_r=1.0 stop_r=1.0 (RR=1.0) and ALL ship expiry_bars=8. At RR=1 with cost 0.07 the breakeven win rate is 53.5%, above the realized ~45%.

Repro: (1) static grep: for each file in src/v8/experts/*.py, extract the target_r and stop_r and expiry_bars values shipped in risk_geometry dicts (regex the literal assignments). Report per-expert target_r/stop_r/expiry_bars and counts: n_experts target_r==1.0, n stop_r==1.0, n expiry==8. (2) dynamic: run_lab (default cost 0.07) and from the report's w_min field + executed_outcomes' win rate, compute the breakeven win rate implied by the shipped geometry (1/(1+R/r') per RM-11) vs realized win rate; report the gap. Read lab.py lines ~914-924 for the RM-11 formula.

key_numbers: count_RR1, count_expiry8, w_min, realized_win_rate, gap_breakeven_vs_realized.`,
  },
  {
    issue: 65,
    title: 'Literature preconditions mostly unimplemented (failed_breakout 2/10)',
    prompt: `Claim: the shipped experts implement few of the literature preconditions their names claim; failed_breakout implements 2/10. The setup count is inflated as a result (many cheap setups per bar).

Repro: (1) read /Users/hootie/src/v8/src/v8/experts/failed_breakout.py FULLY and the issue body's 10-condition table. Audit which of the 10 conditions the code implements (search each condition's mechanism: trend filter, exhaustion, sweep, rejection, close-back-in-range, volume, RR, structural stop, invalidation). Produce the condition->implemented? table. (2) setup inflation: detect_drafts; count failed_breakout drafts and the TOTAL drafts over 2500 bars; report setups-per-bar for failed_breakout and overall.

key_numbers: conditions_applied (int), conditions_total (10), failed_breakout_drafts, total_drafts, setups_per_bar.`,
  },
  {
    issue: 66,
    title: 'prior_high/prior_low unbounded prefix extremes -> invalidation is dead code for 6 experts',
    prompt: `Claim: src/v8/marketstate.py computes prior_high/prior_low as running prefix max/min (all-time extremes), so the lab's pre-entry invalidation gate (low < prior_low / high > prior_high) almost never fires for the 6 experts that do not freeze their own ref.

Repro: (1) static: confirm the running prefix computation (marketstate.py ~756-764) and the lab fallback (lab.py ~738-774) that uses the state feature when no prior_high_ref/prior_low_ref is frozen. (2) identify the 6 experts with no frozen ref: grep which expert files do NOT emit prior_high_ref/prior_low_ref into risk_geometry. (3) dynamic: detect_drafts; for the 6 experts' drafts, at the trigger bar (birth_idx+1), test the invalidation predicate (LONG: low < prior_low_unbounded; SHORT: high > prior_high_unbounded) where the unbounded levels come from the state feature (see detect_drafts' states dict — states[bar_available_time].features). Count how many fires (expect ~0) vs total drafts for those experts. Also report how OLD the pinned extreme is (bar distance from birth to the bar that set the all-time extreme) for a couple of examples, to show it is stale.

key_numbers: experts_without_frozen_ref (list), drafts_total, invalidation_fires (expect 0), example_staleness_bars.`,
  },
  {
    issue: 67,
    title: 'trigger_ref is written to geometry but never read by the runner',
    prompt: `Claim: candlestick_reversal computes trigger_ref and writes it to risk_geometry; the lab runner never consumes it as an entry predicate. The field enters the geometry hash (episode identity) but not the behavior.

Repro: (1) static: grep -rn "trigger_ref" across src/v8/ — confirm the only decision-path reader is candlestick_reversal's still_valid (a POST-ENTRY thesis check), and that lab.py/simulator.py have zero consumers. (2) show the identity impact: read v8.lab._geometry_version — it hashes risk_geometry minus atr_ref/prior_high_ref/prior_low_ref, so trigger_ref IS part of episode_key; demonstrate by computing episode_key with and without trigger_ref in the geometry and showing they differ. (3) dynamic: count candlestick_reversal candidates that trigger and enter, and confirm their entry was unconditional (no trigger price was enforced) — e.g. report how many entered whose entry-bar close did NOT satisfy the book trigger predicate (LONG: close > trigger_ref; SHORT: close < trigger_ref).

key_numbers: consumers (list), episode_key_differs (bool), n_entered, n_entered_violating_trigger_predicate.`,
  },
  {
    issue: 68,
    title: 'ExposureBook adverse selection: executed subset ~2x worse; alphabetical race',
    prompt: `Claim: the executed subset is much worse than the average setup, and which candidate wins a contended (instrument, direction) slot is decided by alphabetical expert_id order (lab.py PHASE 3 sorts experts by expert_id; pending dict preserves insertion order; ExposureBook allows one active exposure per (instrument, direction)).

Repro: (1) run_lab (cost 0.07) -> executed_outcomes stats (n, mean, win rate, total). (2) detect_drafts + offline_resim (own geometry, lag=2, cost 0.07) -> all-setups stats. Compare means (executed vs all-setups) and the ratio. (3) per-expert: for each expert, detected drafts count (from detect_drafts) and executed count (from candidates ledger: lab.candidates.read() records carry expert_id and to_state; executed = candidates that reached CLOSED, or outcomes with label_status != NOT_EXECUTED joined by candidate_id). Report a table sorted by executed count. Show the alphabetical-first two experts' combined share of executions. (4) alternative-explanation test: report signal-per-expert rate (detected/2500 bars) vs execution rate, to see whether bollinger_breakout simply emits more signals or is systematically preferred.

key_numbers: executed_stats, all_setups_stats, adverse_selection_ratio, top2_share, per_expert_rates (top 6 rows).`,
  },
  {
    issue: 69,
    title: 'EXCESS_COST_THRESHOLD_R=0.10 below realistic taker cost',
    prompt: `Claim: lab.py EXCESS_COST_THRESHOLD_R=0.10 corresponds to ~6.39 bps on BTCUSDT 1h (1R ~63.9 bps), below every realistic taker round trip (8-10 bps). So at an honest cost the lab would reject everything; the default 0.07 sits just under the gate to keep it from firing.

Repro: (1) compute ATR(14)/price mean and median over the 2500-bar window (load bars, compute ATR the way marketstate does — or read the shipped feature: use detect_drafts' states to read f['BTCUSDT.atr'] at a late bar and the close) -> 1R in bps, then threshold bps (0.10 * 1R_bps) and default-cost bps (0.07 * 1R_bps). (2) run_lab with round_trip_cost_r=0.125 (realistic taker 8bps) — report terminal_distribution and rejection_distribution (expect excess_cost rejects), and n_executed. (3) run_lab at 0.07 — same fields for contrast.

key_numbers: atr_price_frac, threshold_bps, default_cost_bps, realistic_cost_bps, rejection_dist_at_0_125, n_executed_at_0_125.`,
  },
  {
    issue: 70,
    title: 'risk_geometry invariants not enforced: target_r<0 booked as TARGET win',
    prompt: `Claim: the canonical simulator accepts nonsensical geometry: target_r<0 puts the target on the wrong side and the loss is recorded as endpoint=TARGET (a win in any downstream stat); stop_r=0 is accepted too. No validation exists in step()/run() (only a few experts guard their own geometry).

Repro: (1) static: grep src/v8/simulator.py and src/v8/lab.py for target_r/stop_r validation (raise/validate) — show none. (2) dynamic: construct a CandidateDraft (schema.CandidateDraft) with risk_geometry {'atr_ref': 10.0, 'target_r': -1.0, 'stop_r': 1.0, 'expiry_bars': 8}; run CanonicalSimulator().run(draft, [two bar payloads]) and show endpoint=TARGET, net_r negative (~-1.07). Same for stop_r=0 -> accepted (endpoint=STOP, net_r=-0.07). Report the actual outcomes. (3) read src/v8/experts/bollinger_reversion.py docstring: confirm Setup 3 ships RR = 0.5 (stop_r=2*sigma/atr, target_r=sigma/atr) and report the breakeven win rate that geometry requires at cost 0.07 (win: +1.00-0.07=+0.93R; loss: -2.00-0.07=-2.07R; breakeven = 2.07/3.00 = 69.0%).

key_numbers: negative_target_outcome (endpoint, net_r), zero_stop_outcome, bollinger_setup3_RR, bollinger_breakeven_win_rate.`,
  },
  {
    issue: 71,
    title: 'Gap asymmetry: adverse gap fully paid, favorable gap clipped at barrier',
    prompt: `Claim: simulator step() uses, for STOP fills, the WORSE of barrier and bar open (gap semantics), but for TARGET fills exactly the barrier price. A 20-unit adverse gap and a 20-unit favorable gap produce very different R. (Deliberate conservative design — the issue records the magnitude, it does not demand a change.)

Repro: (1) dynamic, direct simulator: build a LONG CandidateDraft with atr_ref=10, target_r=1.0, stop_r=1.0, expiry_bars=8. OpenPosition entry=100 (stop 90, target 110). Feed a bar with open=70, high=70, low=70, close=70 -> record endpoint and net_r (expect STOP, ~-3.07). Feed a separate run with open=130, high=130, low=130, close=130 -> record (expect TARGET, ~+0.93). Compute the asymmetry (|adverse_gap_R| vs favorable_gap_R). (2) measure the real gap rate on the tape: fraction of bars where TR > (H-L) (i.e. gap exists) and fraction where open == prev_close.

key_numbers: adverse_gap_outcome, favorable_gap_outcome, asymmetry_R, tape_gap_frac, tape_open_eq_prevclose_frac.`,
  },
  {
    issue: 72,
    title: 'synth.py generates unrealistic gaps (open independent of prev close)',
    prompt: `Claim: src/v8/synth.py make_synthetic_tape generates each bar's open independently of the previous close (o = price/(1+uniform)), producing bar-to-bar gaps that real continuously-traded perps do not have. This makes the synthetic tape misleading even for mechanical diagnostics. (Golden hash issue is already resolved on the working tree — verify.)

Repro: (1) static: read src/v8/synth.py and quote the open-generation line. (2) dynamic continuity stats: build make_synthetic_tape(seed=7, n_bars=2500) and load the real tape (load_window(2500)); for each compute: fraction of bars where TR > (H-L) (a gap), fraction where open == prev close, and the mean |open - prev_close|/prev_close. Compare. (3) run the golden regression test: .venv/bin/python -m pytest tests/test_golden_backtest.py -q and report pass/fail.

key_numbers: synth_gap_frac, real_gap_frac, synth_open_eq_prev, real_open_eq_prev, synth_mean_gap_frac, golden_test_passed.`,
  },
]

const REPRO_SCHEMA = {
  type: 'object',
  properties: {
    issue: { type: 'integer' },
    title: { type: 'string' },
    claim: { type: 'string' },
    reproduced: { type: 'boolean' },
    key_numbers: { type: 'object' },
    notes: { type: 'string' },
    script: { type: 'string' },
  },
  required: ['issue', 'title', 'claim', 'reproduced', 'key_numbers'],
}

phase('Reproduce')
const results = await parallel(
  SPECS.map(spec => () =>
    agent(
      `${COMMON}\n\nISSUE #${spec.issue} — ${spec.title}\n\n${spec.prompt}`,
      { label: `repro-${spec.issue}`, phase: 'Reproduce', schema: REPRO_SCHEMA }
    )
  )
)

const done = results.filter(Boolean)
log(`reproduced ${done.filter(r => r.reproduced).length}/${done.length} issues`)
return done
