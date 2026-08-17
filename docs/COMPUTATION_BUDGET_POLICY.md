# Computation Budget Policy (D-099)

**Status:** PROVISIONAL_DECISION. This policy governs agent and operator
verification work. It is about deciding whether to spend compute; it neither
weakens scientific validity gates nor makes an economic claim.

## Rule

Before running a computation expected to take more than five seconds, or
re-running an already-green check, state:

1. the decision its result can change; and
2. the new semantic risk or uncertainty it resolves.

Run it only when its expected marginal decision value exceeds its full cost:

```text
expected value ≈ P(result changes a decision) × impact × novelty
                 + reuse value
                 − runtime − user latency − context/tool overhead − redundancy
```

This is a decision aid, not a fake-precision calculation. If the answer is not
plainly positive, do not run the computation.

## Non-negotiable exceptions

The rule does not permit skipping a mandatory semantic-boundary gate. Run the
smallest applicable gate when a change affects any of the following:

- correctness semantics or a known defect;
- determinism, scalar/SIMD/backend parity, identity, or serialization;
- safety, authority, data-integrity, or fail-closed behavior; or
- an explicitly required handoff/release gate.

For a change that cannot affect one of those boundaries, a previously-green
test is evidence, not a ritual to repeat. In particular, documentation-only
or formatting-only edits do not justify re-running a code suite.

## Operating limits

1. Prefer the smallest check that distinguishes the live decision. A targeted
   test beats a full matrix when the matrix adds no new semantic coverage.
2. Run a full handoff suite at most once per handoff, after substantive code
   changes are complete. Do not repeat it merely because generated documents,
   formatting, or prose changed afterwards.
3. Additional verification after a green result has a 60-second budget. Past
   that point, stop and report: completed evidence, remaining uncertainty,
   and the exact next check that would resolve it.
4. Some boundaries are complementary: e.g. a CPU/GPU parity fixture plus a
   capability probe. These may run as one named, bounded gate bundle, provided
   the shared decision is stated first.
5. Report an unverified environment-dependent receipt honestly instead of
   manufacturing confidence with unrelated local computation.

## Practical examples

| Situation | Decision | Appropriate computation |
|---|---|---|
| A Rust arithmetic branch changed | Can output semantics drift? | Run its focused unit/parity gate. |
| GPU backend is added | Can an eligible adapter preserve f64 bits? | Run one capability probe + one golden CPU/GPU parity fixture on that adapter. |
| Only Markdown or `cargo fmt` output changed | Did code semantics change? | No code suite rerun; regenerate/check the affected artifact only. |
| A full suite is already green | Is there a new boundary to cover? | Do not repeat it; record the existing evidence. |
| No Linux `SHADER_F64` adapter is available | Is production GPU parity proven? | Report the missing receipt; do not substitute repeated macOS CPU tests. |

This policy is informed by value-of-computation work, adaptive-compute
research, and test-case-prioritization evidence: select the maximum expected
net benefit under a budget, recognize mandatory gates, and prioritize fast
decision-changing failures over redundant execution.
