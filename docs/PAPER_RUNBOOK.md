# Paper Runbook — fast local replay (Tier A/B note)

Historical note: `docs/AGENT_RUNBOOK.md` §0 declares a spec freeze for the
Phase 0-3 autonomous build. That freeze is scoped to that build contract and
does not veto this Tier A/B operational note per
`docs/GOVERNANCE_RESET_V86_2026-09-07.md` (current objective > historical
decisions). This file changes no runtime behavior and registers no
architecture.

## Why `paper` feels slow

`v8-next/app/paper.py::_step_locked` does, in order:

1. `initialize()` — rehashes all `*.py` + `uv.lock` + 9 package versions.
2. Checkpoint replay — `replay_account(prior_paths)` over **all** manifests.
3. `capture()` — 5 sequential Binance REST calls
   (`exchangeInfo` is the heavy one; `timeout=30` each).
4. Full replay — `replay_account(all manifests)` + `replay_frozen_campaigns`
   + sqlite writes. Cost grows as `O(N²)` with capture count.
5. `print(json.dumps(result))` — full result to stdout every run.

A leading `sleep 200` in the shell command dominates all of the above.
(Real case: `sleep 200` waited ~179s for an `experiment_window` to open.)

## Fast pattern

```bash
# No network, no new capture — read current state fast:
uv run --no-sync --project v8-next python -m v8_next.app.paper /tmp/<run> \
  --maker-fee 0.0002 --taker-fee 0.0005 --initial-balance 10000 \
  --max-notional 100 --max-exposure-fraction 0.1 \
  --policy-config /tmp/<policy>.json --replay-only 2>&1 | tail -n 2
```

Rules of thumb:

- Omit `sleep N`; if waiting for an `experiment_window`, poll the clock
  (`while [ $(date +%s%N) -lt <start_ns> ]; do sleep 10; done`) instead of
  blind-sleeping past the window.
- Use `--no-sync` on repeat runs to skip `uv` re-resolution.
- Use `--replay-only` when you only need state/ledger output (no network).
- Read `paper-state.json` directly instead of relying on the full stdout JSON.
- Start fresh `/tmp` run dirs for new experiments; old dirs replay every
  capture on every step.
- New captures are inherently network-bound (sequential REST) — no local flag
  removes that cost. Code changes under `v8-next/` are out of scope (frozen).
