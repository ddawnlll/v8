# V8 Governance Reset — 2026-09-07 (owner-authorized)

Trunk-based, tiered-governance reset. Replaces the PR-first / mandatory-issue /
global-OPEN_PIN regime for ordinary development. Safety and evidence rules
(Rule 12 anti-fabrication, Rust-only oracle boundary, release claim gates)
are unchanged.

## 1. Authority hierarchy (new order)

1. current explicit project objective
2. minimal safety/evidence constitution (§5 RUST ONLY, §5 anti-synthetic/Rule 12,
   data-destruction/security/real-money paths fail-closed)
3. physical evidence + executable correctness checks
4. active technical specification
5. historical D-xxx / ADR
6. old audit/research notes

5 and 6 NEVER veto normal implementation. A historical ADR warns; it does not
veto. Supersession is recorded inline (see §4), no tribunal required.

## 2. Risk tiers

| Tier | Example | Required |
|---|---|---|
| **A — Dev** | refactor, module, CLI, implementation | fast gate: fmt (touched lines) + clippy/build + relevant tests |
| **B — Architecture** | USDM → Nautilus lane migration | short goal note + acceptance tests |
| **C — Evidence** | benchmark evaluator, execution parity | physical evidence + reproducibility |
| **D — Release claim** | monograph, readiness, economic results | full receipt/certificate/audit machinery |

Full constitutional machinery (D-series registration, monograph sync,
CHANGELOG entries, traceability matrices) applies to Tier D only. Tier A/B
needs none of: issue, work item, PR, OPEN_PIN, D-xxx, receipt.

## 3. Workflow (trunk-based)

```text
edit → relevant checks → commit to main → continue
```

- `main` = latest coherent development state (NOT a certified release).
- Release tags (`v8.6-dev.N`, `v8.6-rcN`) mark validated states; certified
  releases additionally pass Tier D evidence.
- Branch use is exceptional: short-lived scratch workspaces only when `main`
  cannot stay compilable during an atomic migration. No mandatory PR.
- Issue filing is optional for Tier A/B; required only for Tier C/D claims.

## 4. Partial supersessions (V8.6 scope)

- **D-116** (independent cashflow-ledger validator): REMAINS a release/economic-
  claim invariant. CEASES to be an implementation veto. USDM keeps no veto over
  production execution architecture; it may live on as reference adapter/fixture.
- **D-160 W4** (Nautilus differential successor): migration-blocking readings are
  superseded for V8.6. Independent parity verification stays mandatory BEFORE
  any release/economic claim, never before architecture/implementation work.
- Kept as release invariants: secondary/reference parity, real-evidence
  requirement, pre-claim execution parity, fabricated-parity/evidence ban.

## 5. OPEN_PIN scoping

Every PIN carries `blocks` / `does_not_block` / `unlock_condition`. A PIN
without scope is ADVISORY and vetoes nothing. Current carried PINs:

| PIN | blocks | does_not_block | unlock_condition |
|---|---|---|---|
| registered benchmark evaluator (D-156) | official readiness certificate, public economic claim | execution refactor, Nautilus migration, tests, dev benchmark diagnostics | evaluator registered with data-backed authority receipt |
| G7–G9 naming conflict (D-152 vs D-153) | Tier D naming certification | implementation, tests | register reconciliation entry |
| pre-v2 ledger rows unbound (#328) | Tier D ledger certification | new development, diagnostics | v2 re-seal of historic rows (if ever needed) |
| D-116 commission/funding/terminal-balance parity gaps | release economic claim | architecture/implementation | measured parity receipts |
| liquidation `cum`-sign question | release economic claim | architecture/implementation | sign-convention measurement |

No new PIN is created for uncertainty alone; uncertainty is recorded in code
(`None` / `UNRESOLVED` / `NOT_APPLICABLE`) or not at all.

## 6. `.audit` rule

Ephemeral process outputs (`*.log`, `*.norm`, `*.stdout`, `*.stderr`,
`*.sha256` under `.audit/`) are local/CI artifacts, git-ignored. Tracked:
canonical release evidence manifests, receipts, seals, and release-persistent
evidence only.
