# V9 Architecture Monograph — Changes v1.0 → v1.1

**Council result:** three blind reviewers: PROMISING BUT REQUIRES REVISION. **Editorial response:** MAJOR REVISION, not an implementation approval.

## Normative/specification changes

- `§4`: MarketBelief is now a bounded PIT immutable view, not a calibrated or mutually exclusive regime probability model. One preregistered decision-use ablation (`M1`) is required.
- `§6`: Opportunity identity, opportunity status, and native trade/order state remain separate; mandatory D4 retest policy remains off.
- `§7`: A canonical action/intent/event/reason vocabulary, legal action matrix, `UNKNOWN` handling, `DecisionPolicyV0` pseudocode, idempotency and 10 example fixtures replace the insufficient symbolic economic argmax. Argmax is research-only.
- `§8`: Parallel intent, venue order, position and protection state machines; partial-fill race conditions; restart and `UNKNOWN_AT_VENUE` reconciliation.
- `§9`: Dynamic Position Management remains an explicit future capability; static bracket preserved; single amendment challenger must pass churn and coverage gates.
- `§10`: Occupancy is factual; simulated alternative portfolios cannot be reported as realized missed profit; capital rotation needs ex-ante estimates.
- `§11`: Execution authority matrix, next-observable caveat, funding settlement versus publication and marked equity identity.
- `§12`: Historical audit findings not extrapolated to current HEAD; independent hand-computed oracle, wrong-but-complete joins, mutations, separate mechanical/accounting/scientific/production verdicts, a predeclared family protocol.
- `§13`: Pi/Kaizen remains optional offline extension and requires a one-task pilot against bounded manual/script baseline.
- `§16`: Engineering plan changed to explicit P0/P1/P2/P3 gates; baseline equivalence and mechanical correctness before economic experimentation.
- `§XXV`: Council-to-revision response matrix and falsification conditions.

## Critical non-claims

This update did **not** run V9 code, verify the current local `v8-next` HEAD, resolve the old 2026-10-30 audit findings, open sealed OOS, validate live fills, or demonstrate economic edge.
