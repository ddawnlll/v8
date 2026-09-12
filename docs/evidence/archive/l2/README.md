# Archived L2 evidence

**Status:** DEPRECATED / OUT OF PRIMARY BENCHMARK CONTRACT (2026-09-12)

The primary V8.7 benchmark is an hourly swing-trading benchmark. It does not
require or consume 3.3-second L2/depth snapshots, queue position, or OFI.
Existing L2/depth captures and their reports are retained as historical,
non-authoritative evidence and must not be used to produce a primary
benchmark score.

The active capacity contract is:

- hourly OHLCV-derived ADV and turnover;
- a declared, evidenced real-fill model/records;
- observed participation and implementation shortfall only;
- `DATA_BLOCKED` when real fills or the ADV basis are absent;
- `UNRESOLVED` for participation scales outside observed fills.

No historical artifact is deleted by this deprecation. Any future L2 work is
an explicitly separate microstructure experiment, not an input to the swing
benchmark.
