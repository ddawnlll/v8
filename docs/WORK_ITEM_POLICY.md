# V8 Work Item & Pull Request Policy

## Core rule
Every repository change must be traceable from an actionable Issue to a bounded branch/PR, to explicit verification evidence, to a reviewed merge on protected `main`.

## Issue classes
1. DEFECT — observed contradiction with an existing contract or invariant.
2. IMPLEMENTATION — implement/wire a pinned decision without inventing new semantics.
3. RESEARCH — falsifiable hypothesis/experiment with baseline, search family, uncertainty, and authority.
4. PERFORMANCE — measured compute defect/optimization with semantic-identity constraints.
5. GOVERNANCE — ambiguous contract, open decision, authority question, or registry change.

## Prohibited shortcuts
- Do not use a code patch as the first place where a semantic decision is made.
- Do not weaken an existing test to make a patch pass.
- Do not silently reinterpret a frozen contract; escalate it as a governance issue / OPEN_PIN.
- Do not open frozen OOS for ordinary debugging or implementation.
- Do not treat CI PASS as proof of correctness.
- Do not force-push review history for normal V8 work.
- Do not combine independent semantic changes in one PR unless the issue demonstrates they are inseparable.

## PR merge rule
Merge only when the linked issue's acceptance criteria, required semantic gates, CI checks, review, registry/changelog obligations, and branch-protection rules all pass.

## Context-completeness rule
Before an IMPLEMENTATION/DEFECT/PERFORMANCE issue is marked READY, and before code-bearing RESEARCH/GOVERNANCE follow-up work begins, the issue must include:
1. R1/R2/... requirement-to-authority mapping.
2. Existing types/interfaces/contracts to reuse.
3. Mathematical/semantic invariants needed to disambiguate implementation.
4. Canonical failure/refusal/status semantics.
5. A dependency/composition map.
6. Explicit OPEN_PIN triggers.

A broad citation such as `SPEC §1–§8` is not sufficient when individual requirements are owned by narrower clauses or decisions. Missing authority is a governance state, not developer discretion.

## Anti-invention rule
- Do not create a parallel type, enum, error code, manifest, identity scheme, or semantic interface for an already-owned concept.
- If the existing owner cannot be located or authorities conflict, STOP and open/escalate an OPEN_PIN.
- Taxonomic roles are not automatically separate runtime engines. Implementation must follow the Required End State, not infer architecture from names.

## Authority / procedure precedence
- Constitution / LOCKED_INVARIANT and owning D-/O-/spec authority control semantics.
- This policy controls the collaborative Issue/PR/review/merge workflow after adoption.
- An Issue R# mini-spec indexes and narrows its owning authority; it does not override it.
- A named session/runbook procedure applies when explicitly invoked. Procedural conflicts are resolved by the narrower invoked procedure; semantic conflicts STOP as OPEN_PIN.
