# W4 verdict record (issue #347) — differential.rs + system_proving/*

Verdict authority: autonomous lane (user delegation 2026-09-07:
"napiyorsan yap kendin karar verirsin"). Verdicts cite receipts R2(a–c)
per the issue; a verdict without receipts would be BLOCKED.

## R2(a): reachability — PASS

`python3 tools/audit_reachability.py` → rc=0,
"PASS: Constitutional Reachability & Authority Integrity 100% verified."
(receipt: `.audit/w4/reachability_after.log`)

Note: the tool FAILED immediately after W1 (it requires
`v8-core/src/kaizen/{controller,verdict}.rs` per D-132/Rule 35) because W1
had moved those files. Constitutional gate outranks W1's zero-caller
heuristic, so `controller.rs` + `verdict.rs` were reverted to the live tree
(W1 amendment commit; self-contained pair, deps only on live
`claims`/`authority`/`hash`/`research_debt`). No other W1/W2/W3 move is in
the tool's required-component list.

## R2(b): differential_* artifact — ABSENT in production

- `reconcile_differential_parity` / `save_differential_artifacts`
  (`v8-core/src/usdm_sim/differential.rs`) are called only by their own
  D-116 tests (lines 272, 295). No production caller.
- The production bundle certificate (`.audit/w2/full-audit.after.stdout`)
  contains NO `differential_economic_ledger.jsonl`. `full-audit`'s artifact
  list is existence-tolerant (`if p.exists()`), so the absent artifact does
  not fail the gate — but nothing produces it either.

## R2(c): system_proving call-map + proving output

- Call-map: `pub mod system_proving` (`lib.rs:51`); internal wiring
  (`receipt.rs`, `run.rs`); sole live consumer is
  `v8-core/tests/system_proving_ground.rs`
  (`test_af_t12_system_proving_ground_exercises_full_pipeline`). No
  production caller.
- Proving output: the integration test exercises the full pipeline and is
  green (verified in the final full-suite run).

## Verdicts

1. **`usdm_sim/differential.rs` (299) → KEEP (dormant).** D-116 REQUIRES an
   independent secondary reference engine; deletion needs a named successor
   and the only candidate (Nautilus differential, W14) does not exist.
   Deleting now would violate D-116. No code move. Revisit in W14.
2. **`system_proving/*` (5 files) → KEEP + QUARANTINE-TAG.** Test-covered
   (integration test green), no production callers. Tagged
   `needs:authority to grow` in `system_proving/mod.rs`, consistent with the
   W2 quarantine trio. No code move.

Neither verdict moves code, so no W4a/b follow-up is required. W14 scoping
(differential successor) remains the open thread.
