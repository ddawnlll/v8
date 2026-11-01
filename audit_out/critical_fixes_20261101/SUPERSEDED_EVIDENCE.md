# SUPERSEDED — do not read

This file was the first-pass evidence summary. The independent audit found two problems with it:

1. Its #495 section still read "Verdict: PENDING — blocked on the G5 regression", contradicting
   `FINAL_REPORT.md`. The G5 failure was a false alarm caused by running pytest inside a live agent
   worktree during `uv sync`; it was retracted to the agent and never reproduced.
2. It used a single file where `ACCEPTANCE.md` required per-issue `<n>_evidence.md` artifacts.

Superseded by:

- `FINAL_REPORT.md` — authoritative outcome table, gates, per-issue evidence
- `389_evidence.md`, `476_evidence.md`, `477_evidence.md`, `491_evidence.md`, `495_evidence.md`
- `AUDITOR_RESPONSE.md` — point-by-point response to the rejection
