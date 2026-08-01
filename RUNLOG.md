# V8 Autonomous Build — Runlog

Session artifact, not corpus. Filled by the build agent per `docs/AGENT_RUNBOOK.md`.
Every step gets an entry: status, evidence, fixes, commit. The operator reads
this file and `docs/STATUS_REPORT.md`.

## Format

```markdown
## Step N — <title> — <DONE | BLOCKED | SKIPPED>
- started: <UTC> finished: <UTC>
- files touched: <paths>
- evidence: <command> -> <output tail>
- fixes / deviations: <what broke and how it was fixed>
- commit: <short hash> `v8-step-N: ...`
- gate: pytest=<pass count> monograph=byte-identical?<yes/no> forbidden-scan=clean?
```

## Step 0 — Baseline (written by the agent)

- pytest: _(to fill: `15 passed` expected)_
- monograph probe hash: _(to fill: shasum of /tmp/v8_index_probe.html)_
- baseline commit: _(to fill)_
