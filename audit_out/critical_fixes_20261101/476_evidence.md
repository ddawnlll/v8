# #476 evidence — certificate wiring (R2) + orphan audit (R3). R1 NOT closed.

PR [#504](https://github.com/ddawnlll/v8/pull/504) · branch `codex/issue-476-wiring-closure` · commit `671d370`
8 files, +538/−8: new `certification.py` +205, new `tools/audit_wiring.py` +146, `runner.py` +44,
`app/portfolio.py` +37, `evaluation/certificate.py` +15, `evaluation/report.py` +17,
`app/benchmark.py` +4, new `tests/test_issue_476_certificate_wiring.py` +78

## Root cause

`PolicyCertificate.generate(...)` accepted optional `projection` and `minerva` arguments, but no
benchmark path ever constructed either object: `evaluation/runner.py:821` and `app/portfolio.py:1093`
both passed the receipt alone. Every D-153 port therefore rendered as a bare missing factor with no
producer name — the "fail-closed MISSING masks the gap" cause the issue names.

## R2 — delivered

`v8_next/certification.py` is the bridge. Both call sites now receive produced values **or a named
refusal**, never a silent hole:

- `PROJECTION_DIAGNOSTIC_ONLY_NO_ECONOMIC_FACTOR` — the projection stays `NO_ECONOMIC_CLAIM`; it does
  not mint a 0-100 economic factor.
- `MINERVA_UNMEASURED_NAMED_REFUSAL` — the runner has no PBO/SPA/MinTRL/regime inputs, so it says so.
- `MINTRL_INTERVAL_UNIT_DAYS_UNDECLARED` — no interval-to-day conversion is invented.

## R3 — delivered

`tools/audit_wiring.py` is a static check: every capability module under
`{oracle,evaluation,analysis,telemetry,world,system_proving,opportunities}` must have an importer
outside its own package and outside tests. **No allowlist, no suppression file** (verified by
reading the script and grepping for allow/ignore/suppress/skip).

## R1 — NOT delivered

```
$ cd v8-next && uv run python tools/audit_wiring.py ; echo exit=$?
audit_wiring: FAIL (35 of 75 capability modules orphaned)
...
exit=1
```

Orphans by package: `evaluation` 17, `oracle` 11, `telemetry` 3, `system_proving` 2, `analysis` 2.
R1 demanded a consumer edge for each of the four outputs the issue names; only the D-153 delta output
gained one (via R2). R4 was declared out of scope by the issue itself ("enforcement mechanism TBD").

## R1's own alternative was taken

R1 reads: "Each of the four outputs above gains a named consumer edge into the benchmark path, **or**
the CLOSED issue is reopened with the unwired R back in `Remaining`." Since wiring 35 modules is not a
one-PR change, the second branch was executed on GitHub — each issue reopened with a comment naming
its specific orphaned modules and citing the audit tool as evidence:

| issue | reopened | unwired modules named |
|---|---|---|
| #451 | yes (exit 0) | `analysis.reconcile`, `analysis.veto_attribution`, `telemetry.belief/identity/span` |
| #452 | yes (exit 0) | 11 `oracle.*` modules (`artifacts`, `authority`, `coverage`, `episode`, `independence`, `information`, `opportunity`, `recoverability`, `support`, `taxonomy`, `utility`) |
| #453 | yes (exit 0) | `evaluation.proving_battery`, `system_proving.metrics`, `system_proving.receipt` |
| #454 | yes (exit 0) | `evaluation.external`, `kaizen_delta`, `observation`, `population`, `synthetic` |

Log: `reopen_log.jsonl`.

## Regression test, both directions

| against | result |
|---|---|
| clean `main@a921da2` | **collection error** — `ModuleNotFoundError: No module named 'v8_next.certification'` |
| branch | 1 passed |

This is the weakest before/after evidence of the five (a structural import failure rather than an
assertion failure), stated plainly rather than dressed up.

## PR hygiene

The PR body originally said `Closes #476`. I changed it to
`Refs #476 — **do not close on merge**`, because merging would otherwise close an issue whose R1 is
deliberately open and now tracked on #451–#454.

Full suite on the branch: **1008 passed, 9 skipped** (baseline 1007 + 1 new). `ruff` clean.

---

## Round 2 — three defects the second audit found, and their fixes (`8c29089`)

### R3 was not "wired into the local gate loop"

`tools/audit_wiring.py` existed but nothing ran it. `v8-next/tools/preflight.sh` — the repo's local
pre-run gate — now runs it as a **blocking** step, placed before the tape checks so a wiring
regression costs seconds rather than a 30-minute window:

```
$ bash v8-next/tools/preflight.sh
=== preflight bars=385 start=0 ===
--- wiring closure (#476 R3)
audit_wiring: FAIL (35 of 75 capability modules orphaned)
FATAL: capability modules have no consumer outside their own package/tests.
exit=1
```

The gate fails today, which is the correct fail-closed behaviour for a repo with 35 unwired
capability modules; the backlog is tracked on #451–#454. A *new* orphan is now a hard regression.

### R2 had a latent defect

`certification.minerva_for_certificate` re-declared the parameter inside its own body:

```python
def minerva_for_certificate(*, ..., min_trl_days: float | None, ...):
    min_trl_days: float | None = None      # <-- shadows the argument
```

A caller-supplied measurement was silently replaced by `None`, and the certificate then refused for
an input it had been handed. Both call sites pass `None`, so it was masked. Fixed by resolving into a
separate name (`resolved_min_trl_days`), and covered by
`test_caller_supplied_min_trl_days_is_not_discarded`, which fails on the pre-fix file
(`assert result.measured_inputs["min_trl_days"] == 12.5` → `assert None == 12.5`) and passes after.

### R1's alternative was only half-executed

Reopening #451–#454 changed their `state` but left the bodies saying `Remaining R IDs: NONE` and
`state:review … closed 2026-09-12`, so the tracker still read "complete". All four bodies were edited:
`Lifecycle` → `state:reopened` (+ a dated note) and `Remaining R IDs` replaced with that issue's
specific orphaned modules. Verified by reading the live bodies back.

### Post-fix state

Full suite **1009 passed, 9 skipped** (baseline 1007 + 2 new); `ruff check src tests` clean;
`bash -n tools/preflight.sh` clean. Regression test verified both directions again:
branch 2 passed, clean `main` 1 error.
