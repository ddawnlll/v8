> This is a preserved triage snapshot, not a current inventory. Since the snapshot, PRs [#501](https://github.com/ddawnlll/v8/pull/501) and [#502](https://github.com/ddawnlll/v8/pull/502) merged on main. Recheck their issue acceptance criteria and all live states before closure. The entries below preserve unresolved requirements regardless of later merge or issue status.

# V9 BACKLOG — preserved requirements

**Historical triage snapshot (not current GitHub state):** `2026-11-02T21:56Z` · **main:** `033cab6fd291` · **open issues:** 28 · **open PRs:** 4
**Intended destination:** `v8-next/docs/V9_BACKLOG.md` — root `AGENTS.md` and the owner's explicit directive make
`v8-next/` the active codebase; the path is authorised. Issue #409 is preserved below as a *documentation-consistency*
follow-up, **not** as evidence that the path is unauthorised.
**Author:** Agent C (triage/preservation). Model `opencode-go/deepseek-v4.1-flash`.
**No economic claim.** `NO_ECONOMIC_CLAIM` applies to every item below.

> ## ⚠️ Baseline qualification
> Main is advancing during this report (`a921da2 → 84b2404d → 12e0dc28 → a00debdb → 033cab6f`). Every statement
> marked **[HISTORICAL]** was measured on the pre-merge branch `integration/v9-minimal-baseline @ 4b226741` and is
> retained only as provenance for triage reasoning. Every statement marked **[CURRENT]** was re-verified against
> `main @ 033cab6f` (or the ref named) at the snapshot time. Re-verify before acting: no claim here is durable
> against a later main.

---

## 1. Merge state at snapshot

| PR | State | Merged (UTC) | Effect |
|---|---|---|---|
| #506 | **MERGED** | 21:50:56 | V9 baseline selection (#487, #498, run-identity guard, #490, #493, #480) **plus** an in-place rewrite of historical evidence (see §4) |
| #505 | **MERGED** | 21:51:55 | #495 G3 cell renamed to the measurement it takes |
| #504 | **MERGED** | 21:54:34 | #476 R2/R3/R4 wiring surfaces (`certification.py`, `audit_wiring.py`) |
| #503 | **MERGED** | 21:55:14 | #491 exit-leg booking |
| #502 | **OPEN** (ready) | — | #477 capacity routing |
| #501 | **OPEN** (ready) | — | #389 ledger quarantine |
| #497 | **OPEN (draft)** | — | #483 bracket replay — *blocked: canonical tape absent* |
| #496 | **OPEN (draft)** | — | #492 opex disclosure |

Issue #495 **CLOSED** 21:51:56 and independently verified landed (§3).

---

## 2. Per-PR remaining unique requirements (open PRs)

### #501 — `codex/issue-389-ledger-quarantine` → #389 · OPEN
Verified **[CURRENT]** fail-open still present on main: with no ledger, `cli status` prints
`benchmark: no ledger at artifacts/benchmarks/benchmark_ledger.jsonl` and **exits 0**.
- R1 verify first entry against canonical contents · R2 verify every predecessor/current digest relation ·
  R3 broken chain authoritative **and** fail closed (new exit code; empty-ledger a *named* state) · R4 keep `NO_ECONOMIC_CLAIM`.
- Tests required: valid genesis replay · tampered first entry · broken predecessor digest · stale receipt · clean quarantine.
- Non-goals: no weakening digest verification · no history deletion to green the chain · no synthetic receipts.

### #502 — `codex/issue-477-capacity-routing` → #477 · OPEN
- R1 canonical path routed through the swing contract · R2 maxima bit-identical · R3 no loosened bound ·
  **R4 re-taken canonical receipt** · R5 every published entry carries a contract status.
- Gate 2 evidence [HISTORICAL]: 6/6 entries published `PROJECTED_LINEAR_BOUND/UNRESOLVED` (×3) and
  `HYPOTHETICAL_SCENARIO/NO_ECONOMIC_CLAIM` (×3).
- **R4 blocker:** canonical `quad-1h-12m` 12-month tape absent; a 4-leg sha256-verified Binance Vision rebuild was
  substituted. Substitution must be declared, not silently accepted.

### #497 — `codex/issue-483` → #483 · **DRAFT, blocked**
- Reading A preserved byte-identical · Reading B decision-based bracket replay · bracket divergence counted ·
  real-window gate **must actually run** on the canonical tape.
- PR body's own blocker: *"the canonical four-year tape is absent"*; the real-window gate was added but **skipped**.
  Land only when the gate can run and pass; otherwise keep draft.

### #496 — `codex/issue-492-opex-disclosure` → #492 · **DRAFT**
- Publish `opex_usdt`, `opex_basis`, `business_net_return`; retain `net_return` as *trading* net; disclose the
  distinction in report, limitations and coverage. **[HISTORICAL]** `grep opex_usdt|business_net` in
  `economic_benchmark.py` returned 0 matches pre-merge — the disclosure is not on main.

### Merged but NOT closable yet (residual criteria)

| PR | Issue | Remaining after merge |
|---|---|---|
| #503 | [#491](https://github.com/ddawnlll/v8/issues/491) | Fix **is** on main (`exit_step += qd * (px - closes[i-1])` then `qty = 0.0`, `equity.append(... + exit_step)`). **R2 still fails by the author's own measure**: `UNEXPLAINED_RESIDUAL` portfolio_P 5.8050 / portfolio_PE 22.5040 USDT (500 bars), 3.7058 / 19.2493 (336 bars), `cost_basis = MISMATCH`. Requires R3 re-published statistics with pre/post delta and a named, non-reconciling residual — not a passed reconciliation. |
| #504 | [#476](https://github.com/ddawnlll/v8/issues/476) | R2/R3/R4 landed (`v8-next/src/v8_next/certification.py` 8,127 B; `v8-next/tools/audit_wiring.py` 5,284 B — **[CURRENT]** present on main). **R1 open**: each orphaned module needs a named consumer on `BenchmarkRunner → BenchmarkReceipt → PolicyCertificate` or an explicit retirement. Re-run `tools/audit_wiring.py` on main and publish the orphan list before closing. |
| #505 | [#495](https://github.com/ddawnlll/v8/issues/495) | **Landed and verified [CURRENT]**: `benchmark_receipt.py:450 vector_field="g3_scenario_robustness"`, `:581 validation_alias=AliasChoices("g3_scenario_robustness","g3_benchmark_coverage")` (old receipts stay valid, fixture bytes unedited, D-164 respected). Executed producer result was `BLOCKED` because all four regimes recorded `trades: 0` — correct fail-closed behaviour, recorded as evidence. |

---

## 3. Historical evidence integrity — **[CURRENT], independently verified**

| Item | Value |
|---|---|
| Artifact | `docs/evidence/v87-r3/PAPER_4Y/paper_trade_4y.json` |
| **Original** (pre-rewrite) | 2,647,782 B · sha256 **`4684885a634d944e41e09a8cca3f3bb019249ffaf402e12451fdb3bb1af99b0a`** · blob `e82f64de` |
| **Current on main** | 2,648,754 B · sha256 **`a66f4a8d6b1a1d1be5532162c75a3f649969a9d5043fc5478864e9276b97276a`** · blob `6173ce45` |
| Pin | `docs/evidence/v87-port-chain/454/sweep/sweep_manifest.json:41-43` still records `bytes 2647782`, `sha256 4684885a…`, `status "PRESENT"` |
| Consequence | **The manifest pin no longer matches its own artifact.** The evidence chain fails its own integrity check while still asserting `PRESENT`. |
| Method of verification | `shasum -a 256` on the worktree file; `git cat-file -p e82f64de \| shasum -a 256` for the original; GitHub contents API on `main` for the manifest bytes and the current blob. |
| Introduced by | `34b58953` ("fix: publish absent reconciliation verdict in canonical artifact"), inherited into `main`; identical blob present on PR #506's branch, so reverting #506 alone would not restore the original. |
| Content changed | `double_entry_reconciled: true → null` (+`_reason`) · `cashflow_discrepancy_usdt: 0.0 → null` · `status: MEASURED → UNMEASURED` · basis prose rewritten · new `cashflow_discrepancy_usdt: UNMEASURED` entry |

**Assessment.** The *semantic* direction is right: `0.0` was an unsupported measured zero, contrary to
monograph §3.4/§12.4 and [#383](https://github.com/ddawnlll/v8/issues/383) R2 ("missing is not zero").
The *method* is prohibited: D-164 / §12.1-2 forbid correcting artifact history in place.

**Required remedy (acceptance criteria)**
1. **BLOCKED: evidence-repair authority required.** Preserve both versions and the existing manifest; do not rewrite
   historical evidence. Independently determine an authorized, append-only repair that makes the original bytes
   (sha256 `4684885a…`, recoverable from blob `e82f64de` / the pre-rewrite commit) verifiable against the pin.
2. A **separately generated superseding correction record** — not an edit of the artifact — stating: which field,
   the original published value, why it was unsupported, the replacement status (`UNMEASURED`), the authorising
   decision id, and the tool/command that generated it. Append-only, content-addressed, D-166/`DECLARED_CORRECTIONS`
   pattern.
3. The correction must be independently reproducible by a second party from the recorded command, not asserted.
4. **No false claims**: the superseded artifact must never be described as having always read `null`, and no report
   may cite the rewritten artifact as if it were the original measurement.
5. Any ledger/receipt already bound to the rewritten bytes must be re-derived, with the supersession recorded.

---

## 4. Disposition of all 28 open issues

Legend: `FIX-LANDED-VERIFY` = code on main, acceptance evidence pending · `PU` = open PR · `DRAFT-BLOCKED` ·
`NW` = no work started · `MUT` = defect changed shape · `GOV` = governance follow-up · `ANN` = announcement ·
`CLOSED-NOT-DURABLE` = closed but fix unmerged.

| # | Issue | Disp. | Verified state | Unresolved requirements / acceptance | Blocked by |
|---|---|---|---|---|---|
| [389](https://github.com/ddawnlll/v8/issues/389) | ledger self-verification fails at entry 0 | `PU` | **[CURRENT]** absent ledger ⇒ exit **0** (fail-open), fix only in #501 | R1 genesis verification · R2 digest relations · R3 quarantine + fail-closed exit code · R4 keep `NO_ECONOMIC_CLAIM`; 5 named tests | PR #501 |
| [390](https://github.com/ddawnlll/v8/issues/390) | DuckDB missing from locked env | `NW` | `duckdb>=1.0` in **`research`** extra; `importorskip` at `test_store_models_and_duckdb.py:340` ⇒ `1 skipped, 7 passed` — a silent skip, which the issue forbids | R1 explicit dependency contract (move to `dev` **or** document `--extra research` with a contract-defined skip) · R2 clean locked env reproduces · R3 documented outcome for the full documented command | — |
| [391](https://github.com/ddawnlll/v8/issues/391) | Ruff I001 import ordering | `FIX-LANDED-VERIFY` | import block is canonical isort order; **no ruff binary** in `v8-next/.venv` ⇒ unverified | R1 fix import block · R2 test behaviour preserved · R3 keep the gate strict (no rule suppression) | needs a logged green `ruff check` |
| [392](https://github.com/ddawnlll/v8/issues/392) | UNKNOWN/MISSING gate states | `NW` | dashboard: `G0-G2 PASS`, `G3-G7 UNKNOWN`, `G8-G9 MISSING`, aggregate `NO_ECONOMIC_CLAIM` | R1 explicit gate-state taxonomy · R2 each non-PASS exposes its blocking evidence · R3 aggregate remains `NO_ECONOMIC_CLAIM` · R4 reports reproducible and source-bound | #377,#380,#383,#385 |
| [393](https://github.com/ddawnlll/v8/issues/393) | close economic gate w/o weakening the claim | `NW` | — | preregistered gate→evidence matrix · real provenance-bound samples before any statistic · OOS/funding/parity/prospective tracked without double use · underpowered ⇒ explicit block · no fabricated p-value/Sharpe/PBO/DSR | #377,#379,#380,#383,#385 |
| [409](https://github.com/ddawnlll/v8/issues/409) | boundary text rewritten w/o authority record | `GOV` | Root `AGENTS.md` + the owner's explicit directive make `v8-next/` active; `CLAUDE.md` still says Rust-only, and `v8-next/AGENTS.md` retains stacked freeze text above the 2026-09-11 correction | **Not a blocker for `v8-next/docs/`.** Follow-up: reconcile the three documents and record the boundary direction in `DECISION_REGISTER` (newest entry D-166 does not cover it) so future agents cannot cite the stale text as current authority | owner decision |
| [434](https://github.com/ddawnlll/v8/issues/434) | autonomous merge authority (D-163) | `ANN` | `docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md` present; directive in force | Announcement only. Preserve: direct push to `main` still forbidden; a merge does not create a receipt, certificate or target-completion authority | close with D-163 pointer |
| [451](https://github.com/ddawnlll/v8/issues/451) | chain 2/7 attribution | `PU` | reopened under #476 R1 | R1 veto reporting · R3 decision trail. Orphans: `analysis.reconcile`, `analysis.veto_attribution`, `telemetry.belief/identity/span` | #504 landed ⇒ R1 now actionable |
| [452](https://github.com/ddawnlll/v8/issues/452) | chain 3/7 oracle substrate | `PU` | reopened under #476 R1 | R1–R3. Orphans: `oracle.{artifacts,authority,coverage,episode,independence,information,opportunity,recoverability,support,taxonomy,utility}` | after #451 |
| [453](https://github.com/ddawnlll/v8/issues/453) | chain 4/7 proving ground | `PU` | reopened under #476 R1 | R1–R3. Orphans: `evaluation.proving_battery`, `system_proving.metrics`, `system_proving.receipt` | after #452 |
| [454](https://github.com/ddawnlll/v8/issues/454) | chain 5/7 benchmark pipeline | `PU` | reopened under #476 R1; `certification.py` now on main | R2/R3. Orphans: `evaluation.{external,kaizen_delta,observation,population,synthetic}` | after #453 |
| [455](https://github.com/ddawnlll/v8/issues/455) | chain 6/7 scoring closure | `NW` `state:blocked` | R1–R4 completed | R5: gates green incl. `audit_synthetic_leakage.py` + doc-path-refs | after #454 |
| [456](https://github.com/ddawnlll/v8/issues/456) | chain 7/7 expert lifecycle | `NW` | `qualification/` absent | R1 EEO + expert-delta mapping published **before** code · R2 expert delta without perf regression · R3 falsification surface yields **no** economic verdict · R4 kaizen feed + explicit no-autonomy guard · R5 assurance/EEO/governance remainder · R6 gates green | after #455 |
| [476](https://github.com/ddawnlll/v8/issues/476) | 451–454 unwired | `FIX-LANDED-VERIFY` | **[CURRENT]** `audit_wiring.py` + `certification.py` on main | R1: consumer edge or explicit retirement per orphan; publish the current orphan count. R2/R3/R4 landed; residual note stands: manifest enforcement is form-only if an issue is created via API | re-run the wiring audit |
| [477](https://github.com/ddawnlll/v8/issues/477) | capacity bound bypasses swing contract | `PU` | fix only in #502 | R1–R3, R5 · **R4 re-taken canonical receipt** | canonical tape absent |
| [478](https://github.com/ddawnlll/v8/issues/478) | ledger keeps superseded cost verdict | `NW` | no ledger/receipts in checkout | Declare the governing verdict for the identical window identity (`seq 21` `cost_basis=MISMATCH`/`EXECUTION_UNPROVEN` vs `seq 23` `VERIFIED_ENGINE_FUNDING`/`SIM_ONLY`); implement via `DECLARED_CORRECTIONS` + D-166; D-164 forbids byte edits | no local ledger |
| [491](https://github.com/ddawnlll/v8/issues/491) | exit P&L dropped from equity | `FIX-LANDED-VERIFY` | **[CURRENT]** exit leg booked before flat (`exit_step += qd*(px-closes[i-1])`, then `qty = 0.0`, `equity.append(... + exit_step)`). Residual is **named but undecomposed**: published fields are `unexplained_usdt`, `engine_series_residual_usdt`, `recomputed_residual_usdt`, `exit_leg_identity`, `cross_identity`, `named_reason` — there is **no fee/funding component split**, so the identity is asserted, not proven | R3 re-published statistics with pre/post delta; R2 needs the residual decomposed into fees + funding + rounding and compared to the measured `unexplained_usdt` (5.8050/22.5040 USDT on 500 bars; 3.7058/19.2493 on 336 bars; `cost_basis = MISMATCH`). Until then publish `UNEXPLAINED_RESIDUAL` as an explicit **non**-reconciliation. Do **not** close on R1 alone | R2 does not hold: identity incomplete |
| [494](https://github.com/ddawnlll/v8/issues/494) | DSR subject chosen by alphabetical sort | `MUT` | **[CURRENT]** `:3774 dsr_names = sorted(...)`, `:3777 selected_variant = max(dsr_names, key=excess_by_name)`, `:3794` publishes it | Alphabetical luck was replaced by **selection on realised excess** — the bias DSR exists to deflate. Requires a `selected_variant` field on the pinned plan, a champion declared from the family registry, and the receipt naming the subject it describes | — |
| [495](https://github.com/ddawnlll/v8/issues/495) | G3 cell mis-measured | **CLOSED/VERIFIED** | **[CURRENT]** landed as in §2 | Executed result `BLOCKED` (all regimes `trades: 0`) is the correct outcome and must remain attached as coverage evidence | — |
| [500](https://github.com/ddawnlll/v8/issues/500) | P+E verdict ignores its own mix | `NW` | cited receipt absent locally | Verdict and `portfolio_mix` must describe the same object on the same basis, else `incremental_net_basis = UNNORMALIZED_NOT_RISK_MATCHED`; root cause is the call site passing a stripped mix, making the #489 exemption unreachable on the canonical path | no local receipt |
| [377](https://github.com/ddawnlll/v8/issues/377) | protected OOS + search family | `NW` | Completed NONE | R1 freeze OOS plan pre-window · R2 atomic burn incl. failed attempts · R3 reject re-access/relabel/reuse · R4 every family member with roles+hashes · R5 `NO_ECONOMIC_CLAIM`; tests: pre-window registration, atomic burn, failed-after-burn, duplicate/relabel, missing-family, two-process replay | no local data |
| [378](https://github.com/ddawnlll/v8/issues/378) | MinTRL estimator | `NW` | Completed NONE | R1 explicit target/null/alpha/power/variance/dependence · R2 horizon evidence ≠ strategy pass · R3 missing assumptions fail closed; no universal threshold, no hardcoded p-values | — |
| [379](https://github.com/ddawnlll/v8/issues/379) | venue fills/latency/shortfall | `NW` | Completed NONE | R1 ingest physical venue artifacts with source+receipt clocks · R2 model-vs-real fill, latency drag, adverse selection, fees, missed-fill · R3 reconcile cash/position/funding/commission without double count · R4 stay `SIM_ONLY`/`EXECUTION_UNPROVEN` | no venue captures |
| [380](https://github.com/ddawnlll/v8/issues/380) | funding finality + coverage | `NW` | Completed NONE | R1 bind row→venue event/receipt/mark/position interval/instrument · R2 each settlement applied once, sign+boundary correct · R3 no-exposure vs unavailable vs incomplete vs verified zero · R4 reconcile across strategy/benchmark/portfolio/venue | no funding data |
| [381](https://github.com/ddawnlll/v8/issues/381) | joint P+E execution | `NW` | Completed NONE | R1 same capital/allocation/concurrency/margin/heat/fees · R2 net opposing orders, count rejects/unfilled · R3 one joint account for return/risk/turnover/drawdown/cost · R4 prove the comparison isolates the declared change | — |
| [382](https://github.com/ddawnlll/v8/issues/382) | capacity/market impact from L2 | `NW` | Completed NONE | H0 ⇒ `DATA_BLOCKED` · R1 capacity is venue/data dependent · R2 impact and participation need identifiable microstructure · R3 model output ≠ venue validation | no L2/tick data |
| [383](https://github.com/ddawnlll/v8/issues/383) | two-ledger external parity | `NW` | Completed NONE | R1 native+reference ledgers from a manifest · R2 versioned mapping, exact bit patterns · R3 missing/unpaired/unsupported ≠ zero · R4 bind receipt to policy/case/mapping/engine/artifact/method hashes · R5 parity is diagnostic, non-sovereign | no physical ledgers |
| [384](https://github.com/ddawnlll/v8/issues/384) | candidate lifecycle → economic eval | `NW` | Completed NONE | R1 immutable identity per episode+transition · R2 all terminal reasons in input · R3 reconcile candidate→campaign→order→fill→position→cashflow without dropping terminal non-fills · R4 reasoned coverage before any metric | no lifecycle ledger |
| [385](https://github.com/ddawnlll/v8/issues/385) | operating net + venue-cost calibration | `NW` | Completed NONE | R1 separate transaction P&L / funding-carry / fees / strategy net / operating net · R2 calibrate from physical receipts, never double-count spread/slippage · R3 bind OPEX period/currency/allocation/source · R4 business-net uncertainty, fail closed | no cost artifacts |

---

## 5. Closed issues whose fix is unmerged (durability hazard)

| # | State | Fix location | Preserved requirements |
|---|---|---|---|
| [#483](https://github.com/ddawnlll/v8/issues/483) | CLOSED | draft PR #497 | Reading A byte-identical · Reading B decision-based · bracket divergence counted · **real-window gate must run on the canonical tape** (currently skipped) |
| [#492](https://github.com/ddawnlll/v8/issues/492) | CLOSED | draft PR #496 | `opex_usdt`/`opex_basis`/`business_net_return` published · `net_return` stays the trading net · distinction disclosed in report/limitations/coverage |

Recommendation: reopen, or record as `DEFERRED_UNMERGED` here with the PR link so closure is not read as resolution.

---

## 6. Standing rules for landing this backlog

1. No closure of any issue whose acceptance evidence is absent from a reproducible local run.
2. `NO_ECONOMIC_CLAIM` remains attached to every artifact cited above; no item here authorises promotion.
3. Historical evidence bytes are preserved; corrections are separate, content-addressed, independently
   reproducible records (§3).
4. Merged ≠ verified: #503/#504/#506 close only when their residual criteria in §2 are met.
5. Monograph prohibitions stand: no second engine/repo, no live LLM market controller, no second
   `OpportunityBook`/ledger/auditor registry, no expert-reset, no retest without evidence, no agent main-push,
   no daemon swarm, no knowledge graph/vector DB without measured need.

*Snapshot 2026-11-02T21:56Z · main 033cab6f · 28 open issues · 4 open PRs · no closure executed · no checkout mutation.*
