"""Bring the five critical issues' GitHub state up to date with what was actually delivered.

Comments carry the status (append-only, the original acceptance text stays intact); the two
issues whose bodies say 'state:triage' / 'Evidence: PENDING' also get their body sections
rewritten so a reader is not told the work never happened.
"""
from __future__ import annotations

import json
import subprocess
import sys

REPO = "ddawnlll/v8"
HEAD = "audit_out/critical_fixes_20261101"


def gh(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", input=stdin
    )


COMMENTS: dict[str, str] = {
    "389": """## Status: FIXED — PR #501 (open, unmerged, base `a921da2`)

`chain_ok` was consumed only inside a `print` f-string, so a **BROKEN** chain still rendered a
`PolicyCertificate` and `cmd_status` returned `0`.

- `EXIT_LEDGER_QUARANTINED = 3`; a broken chain renders no certificate; an empty ledger is its own
  named state instead of an early success return.
- Regression test `tests/test_cli_status_ledger_quarantine_389.py`: **3 failed / 4 passed** on clean
  `main@a921da2` (`assert 0 == 3`), **7 passed** on the branch. Branch suite 1014 passed / 9 skipped.
- Evidence: `audit_out/critical_fixes_20261101/389_evidence.md`, `verify_389/`.

R1–R4 are delivered. This PR says `Fixes #389`.""",

    "495": """## Status: FIXED — PR #505 (open, unmerged, base `a921da2`)

R1 — `g3_benchmark_coverage` → `g3_scenario_robustness` in the model. Stored ledger digests still
verify: the digest canon hashes field *values*, so `validation_alias=AliasChoices("g3_scenario_robustness",
"g3_benchmark_coverage")` keeps old receipts valid and no `tests/fixtures/ledger_canon/*.json` byte was
edited (D-164). The name also had to leave the **renderer**: `site/app.html` was still asking for the
pre-rename key and would have shown `UNKNOWN` on a receipt that measured the cell (`494fcbc`, with a
fallback for immutable stored ledgers).

R2 — the canonical producer calls `evaluate_g3_scenario_robustness(regimes)` instead of storing the rule
default, and publishes the result as a DIAGNOSTIC cell.

R3 — `G3ScenarioBasis` (bars / trades / max_drawdown / return_variance per regime) travels beside the
digest canons; `_state_and_basis_travel_together` makes a non-default state without its basis
impossible; `G3_SCENARIO_BASIS_ABSENT` is a named refusal, never an empty mapping.

Gates 2 and 3 were **executed** on a real producer run (4-leg Binance Vision tape, 2025-07-01..07-22):

```
gate keys: ['g3_scenario_robustness'] -> ['BLOCKED']
g3_benchmark_coverage anywhere in the entry: False
g3_scenario_robustness_basis: present, four regimes with bars/trades/max_drawdown/return_variance
```

`BLOCKED` rather than `PASS` because every regime recorded `trades: 0` — fail-closed with its measured
inputs attached, which is what R3 asks for. Evidence: `495_evidence.md`, `E2E_EVIDENCE.md`,
`e2e/495_post/`. This PR says `Closes #495`.""",

    "477": """## Status: PARTIAL — PR #502 (open, unmerged, base `a921da2`)

Delivered: R1 (the swing-capacity contract is imported by the canonical path at
`app/portfolio.py:209`, so an extrapolated bound can no longer publish `MEASURED_*`), R2 (maxima
bit-identical), R3, R5, and **R1/gate 2 for every entry**: `6b619a9` fixed the three
`HYPOTHETICAL_SCENARIO` entries, which had shipped with no `status` at all — 3 of 6 published entries
were failing the issue's own gate.

Gate 2 verified end-to-end on a real producer run. Re-taken receipt (`e2e/477_post/`):

```
PROJECTED_LINEAR_BOUND   UNRESOLVED          OBSERVED_FILLS_AT_OTHER_SCALE          (1%, 5%, 10%)
HYPOTHETICAL_SCENARIO    NO_ECONOMIC_CLAIM   HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED (k=0.1, 0.5, 1.0)
```

against the committed receipt's `MEASURED_LINEAR_BOUND` with **no** `status` key.

**R4 is not fully satisfied.** The committed canonical `quad-1h-12m` 12-month tape is absent here; the
tape used was a real 4-leg rebuild from sha256-verified Binance Vision archives for the same July-2025
window. The producer was genuinely re-run and nothing was hand-edited, but the artifact is not the
committed canonical one, so this is not offered as a re-taken canonical receipt. Evidence:
`477_evidence.md`, `477_rederivation.txt`, `E2E_EVIDENCE.md`.

This PR says `Refs #477 — do not close on merge`.""",

    "491": """## Status: PARTIAL — PR #503 (open, unmerged, base `a921da2`)

Re-derived first, per the objective: **CONFIRMED** at `main@a921da2`
(`491_rederivation.md`, `probe_491.py`) — the builders marked positions at bar close and then dropped
them before the exit leg, so the last segment never entered `equity_mtm` and the graft smeared the gap
over every bar.

Delivered:

- **R1** — the exit leg is booked (`qd * (px - closes[i-1])`) before the position goes flat, in both
  builders. Probe gate 1: `[1000, 1005, 1005]` / drift 2.5 on main → `[1000, 1005, 1010]` / drift 0.0
  on the branch.
- **R3** — re-published statistics with a pre/post delta on the same real window:
  `max_drawdown` -0.00685479 → **-0.0111552** (portfolio_P) and -0.00348082 → **-0.00631568**
  (portfolio_PE); Sharpe and `tail_mean_5pct` move with it; `excess_vs_primary` unchanged to 1e-13.
- **R4** — the graft's assumed meaning is now asserted, not assumed.
- The identity itself is now **published** (`77f6576`): `published_cost_reconciliation()` was dropping
  `exit_leg_identity`, so it appeared nowhere in the receipt, the forensic HTML or the markdown report.

**R2 does not hold, and is not claimed.** R2 requires the graft residual to equal fees + funding.
Measured on two independent real windows:

```
benchmark 500 bars: portfolio_P unexplained  5.8050 USDT, portfolio_PE 22.5040 USDT   (tol 0.05)
smoke     336 bars: portfolio_P unexplained  3.7058 USDT, portfolio_PE 19.2493 USDT   (tol 0.05)
cost_basis = MISMATCH in every run (closed_loop_terms.residual_usdt -0.407 / -0.203)
```

R2 is an identity on `balance_total`; when the engine's own closed loop does not reconcile on the
window, its premise is false and no term bookkeeping rescues it. What is implemented and published is
this issue's §14 rule — a residual not explainable by fees + funding publishes a **named**
non-reconciling state (`UNEXPLAINED_RESIDUAL` + `unexplained_usdt`) instead of a graft presenting it as
cost. The synthetic 3-bar equality still passes exactly; the test now states plainly that the synthetic
equality is not evidence about the real residual.

This PR says `Refs #491 — do not close on merge`.""",

    "476": """## Status: PARTIAL — PR #504 (open, unmerged, base `a921da2`)

**R2 — delivered.** `PolicyCertificate.generate` (`runner.py:821`, `app/portfolio.py:1093`) now receives
produced `projection` / `minerva` / MinTRL values or a named refusal via `v8_next/certification.py`:
`PROJECTION_DIAGNOSTIC_ONLY_NO_ECONOMIC_FACTOR`, `MINERVA_UNMEASURED_NAMED_REFUSAL`,
`MINTRL_INTERVAL_UNIT_DAYS_UNDECLARED`. A latent defect found on the way: `minerva_for_certificate`
shadowed its own `min_trl_days` parameter, so a caller-supplied measurement always became `None` and the
certificate refused an input it had been given — fixed, with a test that fails pre-fix.

**R3 — delivered.** `tools/audit_wiring.py` (no allowlist, no suppression file) is a **blocking** step in
`v8-next/tools/preflight.sh`, fail-closed with no skip flag. It reports `FAIL (35 of 75 capability
modules orphaned)` and preflight exits 1 today, by design.

**R4 — delivered** (`18f8760`). `tools/check_issue_wiring_manifest.py` validates the `W1-W7` manifest,
all seven steps and the Completed/Remaining R-ID sections, with named failures
(`WIRING_MANIFEST_ABSENT`, `WIRING_MANIFEST_INCOMPLETE`, `REMAINING_R_IDS_ABSENT`,
`COMPLETED_R_IDS_ABSENT`), and says in its own output that it checks form only.
`.github/workflows/issue-wiring-manifest.yml` runs it on `issues: [opened, edited, reopened]`, so an
issue created through the API cannot bypass the manifest. Observed: #491's real body → `OK (W1..W7)`;
this issue's own pre-manifest body → `FAIL WIRING_MANIFEST_ABSENT`.

**R1 — open, and this PR does not pretend otherwise.** 35 of 75 capability modules still have no
consumer: `evaluation` 17, `oracle` 11, `telemetry` 3, `system_proving` 2, `analysis` 2. R1's own
alternative was executed instead of wiring them in one branch: **#451–#454 are reopened** with their
bodies edited to `state:reopened` and their orphaned modules listed under `Remaining R IDs` (#451:
`analysis.reconcile`, `analysis.veto_attribution`, `telemetry.belief/identity/span`; #452: the eleven
`oracle.*` modules; #453: `evaluation.proving_battery`, `system_proving.metrics/receipt`; #454:
`evaluation.external/kaizen_delta/observation/population/synthetic`). `projection`, `minerva` and
`mintrl` are wired by this PR, covering part of #454.

This PR says `Refs #476 — do not close on merge`.""",
}

# Body edits: only for the two bodies whose own status lines are actively misleading.
BODY_FIX = {
    "476": [
        ("state:triage", "state:in-progress — R2, R3, R4 delivered on PR #504 (open, unmerged); R1 open on #451–#454"),
        ("PENDING (this issue's R-evidence to be produced per R).",
         "R2/R3/R4 evidenced at `audit_out/critical_fixes_20261101/476_evidence.md` and PR #504 "
         "(branch tip `18f8760`); R1 is NOT delivered — see `## Remaining R IDs`."),
    ],
    "491": [
        ("state:triage", "state:in-progress — R1, R3, R4 delivered on PR #503 (open, unmerged); R2 fails its equality and is published as a named non-reconciling state"),
        ("PENDING — the 3-bar probe output above is reproducible",
         "PARTIAL — the 3-bar probe was independently reproduced (`probe_491.py`, `491_rederivation.md`, "
         "verdict CONFIRMED), R1/R3/R4 are evidenced in `491_evidence.md` with a real pre/post delta, and "
         "R2 is measured and NOT satisfied (`491_identity_states.txt`: 5.8050 / 22.5040 USDT unexplained, "
         "`cost_basis=MISMATCH`). The old note follows — 3-bar probe output above is reproducible"),
    ],
}


def comment(number: str, body: str) -> None:
    r = gh("issue", "comment", number, "--body", body)
    print(f"#{number} comment rc={r.returncode} {r.stderr.strip()[:120]}")


def fix_body(number: str, pairs: list[tuple[str, str]]) -> None:
    body = gh("issue", "view", number, "--json", "body", "-q", ".body").stdout
    for old, new in pairs:
        if old not in body:
            print(f"#{number} body: pattern not found -> {old[:50]!r}")
            continue
        body = body.replace(old, new, 1)
    path = f"{HEAD}/issue_body_{number}.md"
    open(path, "w", encoding="utf-8").write(body)
    r = gh("issue", "edit", number, "--body-file", path)
    print(f"#{number} body edit rc={r.returncode} {r.stderr.strip()[:120]}")


if __name__ == "__main__":
    for number, body in COMMENTS.items():
        comment(number, body)
    for number, pairs in BODY_FIX.items():
        fix_body(number, pairs)
