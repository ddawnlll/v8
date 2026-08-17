# V8 agent rules

## Computation is a budgeted decision

Before a command expected to take more than five seconds, or before repeating
an already-green check, name the decision it can change and the new semantic
risk it covers. Run it only if its expected marginal decision value exceeds
its total cost: runtime, user latency, context/tool overhead, and redundancy.

Mandatory gates still run: a changed correctness semantic, a determinism or
parity boundary, a safety/authority boundary, or an explicit handoff gate.

Use the smallest discriminating check. Never rerun a green suite after only
documentation or formatting changes. Run the full suite at most once per
handoff. Do not spend more than 60 seconds of additional verification without
reporting current evidence, remaining uncertainty, and the exact next check.

If several cheap checks are jointly necessary, treat them as one named,
bounded gate bundle. Do not accumulate “just in case” computation.

Canonical policy: `docs/COMPUTATION_BUDGET_POLICY.md` (D-099).

## Python boundary

`v8-core/` is authoritative. `src/v8/` is a hash-locked historical parity
oracle, not a runtime. Python may run in CI only for the explicitly allowed
documentation and boundary-audit tools; pytest, oracle imports, and Python
evaluation are not Rust runtime gates. Any oracle-tree change requires the
registry decision, changelog entry, and new lock hash described in
`docs/legacy/PYTHON_ORACLE_POLICY.md`.
