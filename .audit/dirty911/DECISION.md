# Dirty-911 disposition (local `main@c2539cd8` uncommitted work)

Decision authority: autonomous lane (user delegation 2026-09-07). Table row
said "al ya da at" (take or drop). Decision: **DROP the raw port, PRESERVE
the ideas as filed V8.6 work items.** The local `main` tree is left untouched.

## What the dirty tree contains (911 ins / 304 del vs stale fork `c2539cd8`)

Fork point with `origin/main`: `5385fcba` (D-150). The dirty work predates
the `usdm_sim` single-file → `usdm_sim/` directory split and D-152/D-156/D-159.

| File | Delta | Content |
|---|---|---|
| `v8-core/src/usdm_sim.rs` | +615/-241 | Funding-settlement rework: ledger-owned funding, `funding_events_settled` cursor, per-event rate lookup (`partition_point`) |
| `v8-core/src/portfolio.rs` | +16/-3 | `OpenPosition.funding_events_settled` field + test init (rest is formatting) |
| `v8-core/src/venue.rs` | +32/-8 | **Liquidation `cum` sign flip** (`-cum` long / `+cum` short) + doc fix (rest is formatting) |
| `v8-core/src/kaizen/exit_trailing.rs` | ±162 | Trailing-stop rework (not line-reviewed; stale base) |
| `CLAUDE.md` | +138 | Agent guidance (human's tree; out of lane) |
| `v8-core/tests/research_validity_diagnostics.rs` | +237 (untracked) | Investigation witnesses vs old single-file `usdm_sim` paths |

## Why not port

1. **Stale base**: the diff applies to the pre-split single-file layout and
   pre-D-152/D-156/D-159 economics. A mechanical port is infeasible; a manual
   port is a redesign.
2. **Behavior change without authority**: funding settlement and liquidation
   math alter simulation economics → the full-audit bundle would drift,
   voiding the W2 byte-identical seal. That requires its own registered
   decision + re-baseline, not smuggling into the attic-cleanup lane
   (anti-shadow rule).
3. **Partially superseded theme**: the validity-investigation theme is merged
   on `origin/main` as D-159 (#327–#330); only the funding/liquidation
   mechanics remain novel.

## Where each idea is preserved (filed V8.6 work items)

- Funding-ledger ownership (`funding_events_settled`, ledger-owned funding)
  → V8.6 §14 venue-conformance work item.
- Liquidation `cum`-sign question → V8.6 §14 work item (must be settled with
  a named oracle/venue spec before any formula change).
- `exit_trailing` rework → V8.6 §15 portfolio/risk work item (unreviewed,
  carried as a claim to verify, not a fact).
- `research_validity_diagnostics.rs` witnesses → referenced from the §14
  work item; NOT ported (imports resolve against the removed single-file
  layout).
