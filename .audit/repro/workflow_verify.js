// Phase 3: verify each of the 12 fixes on the CURRENT (fixed) tree and measure
// the delta vs the baseline (.audit/BASELINE.md + .audit/repro/out/N.json).
// One agent per issue; each writes .audit/repro/out/N.fixed.json.
export const meta = {
  name: 'verify-12-fixes',
  description: 'Verify audit fixes #61-#72 on the fixed tree and measure deltas',
  phases: [{ title: 'Verify', detail: 'one agent per issue' }],
}

const COMMON = `You are VERIFYING a fix for GitHub issue #N on the V8 trading-research
codebase at /Users/hootie/src/v8. The fixes for issues #61-#72 have already
been implemented (see docs/CHANGELOG.md entry "2026-08-07 — Audit-fix pass"
and DECISION_REGISTER D-057..D-064). Your job is to (a) re-run the evidence
against the FIXED tree, (b) compare with the pre-fix baseline, and (c) report
the delta — honestly, including where the fix does NOT change an economic
number (the measurement-only issues #61/#65/#71 deliberately do not).

CONTEXT YOU MUST READ FIRST:
- Issue body: /Users/hootie/src/v8/.audit/issues/N.json
- Pre-fix evidence: /Users/hootie/src/v8/.audit/repro/out/N.json (and
  /Users/hootie/src/v8/.audit/BASELINE.md for the headline numbers)
- The fix's code: the files named in the CHANGELOG entry
- Shared harness: /Users/hootie/src/v8/.audit/repro/lab_probe.py
  (load_window / detect_drafts / run_lab / executed_outcomes / offline_resim / stats)

CONTRACT:
1. Re-run the pre-fix repro:  cd /Users/hootie/src/v8 && .venv/bin/python .audit/repro/repro_N.py
   It runs against the CURRENT tree, so it now measures the FIXED behavior.
   Capture its stdout as the "after" evidence and write it to
   /Users/hootie/src/v8/.audit/repro/out/N.fixed.json.
2. If the repro CRASHES because the fix changed behavior the script assumed
   (e.g. issue #70's bad-geometry scenario now fails closed), DO NOT treat the
   crash as "unverifiable" — REWRITE the script's verification logic to assert
   the NEW behavior (for #70: the simulator must raise ValueError on
   target_r<=0 / stop_r<=0 / expiry<1), keep the measurements that still apply,
   and save the adapted script as .audit/repro/repro_N_verify.py. The fixed
   evidence must prove the bug is GONE.
3. Compute the delta vs the pre-fix numbers from out/N.json. Report the
   before -> after change and what it means.

HARD RULES:
- Do NOT modify anything under src/v8/, tests/, tools/, docs/, site/.
  You may write ONLY .audit/repro/repro_N_verify.py and .audit/repro/out/N.fixed.json.
- Deterministic. Report the CURRENT numbers honestly — if a fix did not move a
  number, say so and explain why (measurement-only issues are expected not to).
- For the economic issues, the headline is the executed-subset statistics on
  the 2500-bar dev window (same population definition as the baseline).`;

const SPECS = [
  { issue: 61, title: 'Cost dominates edge — now surfaced as a FEASIBILITY note',
    prompt: `Verify #61. This issue was a MEASUREMENT record (#61 says "düzeltme önermiyor"). The fix that landed is the feasibility surfacing: the lab report now carries a FEASIBILITY note when the cost-degraded breakeven win rate exceeds the realized win rate (#64) and when the excess-cost gate fires (#69), and the cost/edge mismatch is recorded (D-063, O-025). Verify: (1) re-run repro_61.py and report the cost sweep; (2) run the full lab at round_trip_cost_r=0.07 on the 2500-bar window and confirm report.economic_note contains 'FEASIBILITY'; (3) report whether the mean(c) - mean(0) = -c identity still holds exactly. Delta: the cost sweep is expected ~unchanged (the economics were NOT changed on purpose); the NEW behavior is the note.` },
  { issue: 62, title: 'PENDING->TRIGGERED now gated on the frozen trigger predicate',
    prompt: `Verify #62. The fix: lab.py PHASE 2 evaluates risk_geometry['trigger_ref'] (+trigger_side) before PENDING->TRIGGERED; candlestick_reversal declares trigger_side; unconfirmed candidates stay PENDING and re-check each bar. Verify: (1) re-run repro_62.py — the "n_would_not_trigger" candidates should NO LONGER trigger unconditionally: count how many candlestick candidates now trigger with close-beyond-trigger confirmed vs before (pre-fix: 27 triggered, 16 without confirmation). Expect the triggered set to now equal the confirmed set. (2) Run the full lab on the 2500-bar window and compare the executed candlestick_reversal count (pre-fix 4) and its mean net_R vs the pre-fix numbers. Report the funnel: detected -> triggered -> executed for candlestick_reversal.` },
  { issue: 63, title: 'Structural stop: stop_ref now the static stop when declared',
    prompt: `Verify #63. The fix: simulator.step() uses risk_geometry['stop_ref'] as the static stop when declared (fallback stop_r*unit). Verify: (1) re-run repro_63.py — the static "step_computes_atr_based_stop / step_never_reads_stop_ref" flags should now be false/true respectively (the simulator reads stop_ref); the dynamic mean deviation should now be ~0 for candlestick drafts (|stop_used - stop_ref| == 0 when stop_ref declared). (2) On the executed population (full lab, 2500-bar window) report the MAE/MFE means and the fraction with mae_r > 1.0 — pre-fix was 0.864/0.889/37.3%. The structural stop should reduce the MAE>1R fraction (the stop now sits at the pattern extreme, further out than 1 ATR from entry on average). Report the new numbers and the delta.` },
  { issue: 64, title: 'RR/expiry hardcoded — feasibility gate now surfaces the mismatch',
    prompt: `Verify #64. The fix that landed is the RM-11 feasibility note (report-only) plus the record that RR=1.0 target_r is a DESIGN_INFERENCE until a structural target exists (D-062). Verify: (1) re-run repro_64.py — the static grep counts (target_r=1.0, expiry=8) are unchanged (the geometry was NOT swept — optimization is explicitly not the fix); (2) run the full lab on the 2500-bar window and confirm report.economic_note contains 'FEASIBILITY: breakeven win rate' and report w_min vs the realized win rate (pre-fix w_min 0.528 vs realized 0.469 on the fixed tree — report the current pair and the gap). Delta: the note is the new behavior; the gap should have narrowed somewhat because the win rate improved.` },
  { issue: 65, title: 'Literature preconditions — recorded as O-024, setup inflation unchanged',
    prompt: `Verify #65. The fix is a RECORD (O-024 open decision + CHANGELOG): the failed_breakout 2/10 condition audit is registered; adding conditions is a challenger decision (rule 12), NOT this fix. Verify: (1) re-run repro_65.py — the condition table and setup-inflation numbers (failed_breakout drafts, setups-per-bar) are expected essentially UNCHANGED (no filter was added on purpose); (2) confirm docs/decisions/OPEN_DECISIONS.md has O-024. Report the numbers and state plainly that the fix is the registration, not a behavioral change.` },
  { issue: 66, title: 'Windowed pre-entry invalidation fallback now meaningful',
    prompt: `Verify #66. The fix: lab.py's fallback prior_high/prior_low for experts with no frozen ref is now the 32-bar windowed extreme before birth (was the unbounded all-bars state feature). Verify: (1) re-run repro_66.py — expect the invalidation-fires count for the 6 ref-less experts to be MUCH higher than the pre-fix 7 fires across 2,067 drafts (the gate is no longer dead code). Report the new fire counts per expert. (2) Confirm the windowed semantics: the fallback uses bars[max(0,i-32):i] (read lab.py). (3) On the full lab run, report how many candidates end INVALIDATED (pre-fix terminal INVALIDATED was 2346; the delta comes from the 6 experts' now-firing gate).` },
  { issue: 67, title: 'trigger_ref now consumed by PHASE 2 (with #62)',
    prompt: `Verify #67. The fix: trigger_ref is now the entry predicate (consumed in lab.py PHASE 2), resolving "written but never read". Verify: (1) grep -rn "trigger_ref" src/v8/lab.py src/v8/simulator.py — there must now be a CONSUMER in the lab (not just the expert's still_valid); (2) re-run repro_67.py — the "n_entered_violating_trigger_predicate" should now be 0 (no candidate enters without close-beyond-trigger confirmation); (3) confirm the identity note still holds (trigger_ref is part of episode_key — that is unchanged and now justified since it drives behavior). Report the before (2/4 violators) -> after (0 violators) delta.` },
  { issue: 68, title: 'Contention tie-break is the candidate episode_key hash (neutral)',
    prompt: `Verify #68. The fix: PHASE 1a iterates pending in candidate_id (episode_key hash) order instead of expert_id-sorted insertion order, so a same-bar same-direction slot race is no longer decided alphabetically. Verify: (1) re-run repro_68.py — the "contended_slots_same_bar / alphabetical_first_wins / alpha_share_of_contended" numbers should show the alphabetical share is no longer ~97% (the split is now hash-driven, near 50/50); (2) report the new executed-subset statistics (n, mean, win rate) vs the pre-fix executed (n=895, mean -0.1155, win 45.3%) and the adverse-selection ratio vs the all-setups population (pre-fix 1.83x); (3) confirm determinism: two identical runs give identical conflict splits (the fix is deterministic). Report whether the executed subset improved toward the all-setups mean.` },
  { issue: 69, title: 'Excess-cost gate now surfaced as a FEASIBILITY statement',
    prompt: `Verify #69. The fix: when the excess-cost gate fires, the report now carries a FEASIBILITY note; the threshold↔bps mapping is recorded (D-063). Verify: (1) re-run repro_69.py — the ATR/bps math is unchanged; (2) run the full lab at round_trip_cost_r=0.125 on the 2500-bar window and confirm report.economic_note contains 'excess_cost' and n_executed == 0; (3) at 0.07 confirm n_executed > 0 and the note does NOT contain 'excess_cost'. Report the notes. The rejection count at 0.125 is expected ~unchanged (~6209) — the fix is the surfacing, not the gate value.` },
  { issue: 70, title: 'risk_geometry invariants fail closed in the simulator',
    prompt: `Verify #70. The fix: simulator.validate_geometry() rejects target_r<=0, stop_r<=0, expiry_bars<1 at step()/run() entry. The pre-fix repro_70.py CRASHES against the fixed tree (it expected bad geometry to be ACCEPTED) — that crash IS the fix. Rewrite it as repro_70_verify.py that asserts the NEW behavior: (1) CanonicalSimulator().run() and .step() raise ValueError on target_r=-1, stop_r=0, expiry_bars=0 (match on the message); (2) valid geometry still runs; (3) report the bollinger_reversion Setup 3 RR=0.5 record (docstring now carries the 69% breakeven + PROVISIONAL_DECISION note). Save as .audit/repro/repro_70_verify.py and out/70.fixed.json. Delta: pre-fix accepted bad geometry and booked -1.07R as a TARGET win; now it fails loudly.` },
  { issue: 71, title: 'Gap asymmetry — recorded as a conservatism budget',
    prompt: `Verify #71. The fix is a RECORD (SIMULATION_TRUTH_SPEC conservatism-budget section + CHANGELOG); the conservative stop/target policy is deliberately UNCHANGED. Verify: (1) re-run repro_71.py — the asymmetry numbers (adverse -3.07R vs favorable +0.93R, 3.30R) are expected ~UNCHANGED (deliberately); (2) confirm docs/contracts/SIMULATION_TRUTH_SPEC.md now has a "Conservatism budget (issue #71)" section with the 3.30R figure. Report the numbers and state that the fix is the documentation of the measured budget, not a semantics change.` },
  { issue: 72, title: 'Synthetic tape continuous variant; legacy default byte-identical',
    prompt: `Verify #72. The fix: make_synthetic_tape gains continuous=True (open = prior close ± small move); legacy default byte-identical; D-064 records the default-flip decision. Verify: (1) re-run repro_72.py — the legacy default stats are unchanged (gap_frac ~73%); (2) run the continuous variant (n_bars=2500) and report its gap fraction (TR > H-L) — expect ~3-5% vs the legacy ~73% and real tape ~0.6%; (3) confirm the golden test still passes: .venv/bin/python -m pytest tests/test_golden_backtest.py -q. Report the before -> after (legacy vs continuous) gap stats.` },
]

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    issue: { type: 'integer' },
    title: { type: 'string' },
    fixed: { type: 'boolean' },
    before: { type: 'object' },
    after: { type: 'object' },
    delta: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['issue', 'title', 'fixed', 'after', 'delta'],
}

phase('Verify')
const results = await parallel(
  SPECS.map(spec => () =>
    agent(
      `${COMMON}\n\nISSUE #${spec.issue} — ${spec.title}\n\n${spec.prompt}`,
      { label: `verify-${spec.issue}`, phase: 'Verify', schema: VERIFY_SCHEMA }
    )
  )
)

const done = results.filter(Boolean)
log(`verified ${done.filter(r => r.fixed).length}/${done.length} issues fixed`)
return done
