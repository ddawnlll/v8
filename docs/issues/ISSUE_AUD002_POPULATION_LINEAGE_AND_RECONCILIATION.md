# [IMPL] Issue #AUD-002: Population Lineage Ledger & Cross-Section Funnel Reconciliation (F02, F03)

**Status:** READY / PROPOSED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, `TARGET_ORACLE_SPEC.md` §9, §17, arXiv:2512.22476 (P006), arXiv:2606.08285 (P008), arXiv:2606.27570 (P036).

---

## 1. Objective
Implement deterministic population lineage tracking and report-to-artifact reconciliation in pure Rust (`v8-core/src/evaluation/lineage.rs`), ensuring every KPI population carries explicit parent hashes, transformation semantics, and that every report cell is 100% regenerable from frozen machine-readable parquet/jsonl artifacts without unexplained residuals ($42,647 = 14,766 + 27,879 + 2$).

---

## 2. Owning Authority
- **Primary Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4 (Artifact reconciliation & provenance).
- **Oracle Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §9, §17.
- **Academic Literature:**
  - `P006` (arXiv:2512.22476): *AutoQuant* (Traceability & population lineage).
  - `P008` (arXiv:2606.08285): *Beyond Agent Architecture* (Artifact release & reproducibility).
  - `P036` (arXiv:2606.27570): *Auditing AI Investment Recommendations* (Executable provenance).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The evaluation report displays multiple distinct populations (e.g. 42,647 setups, 14,766 dedup suppressions, 1,774 admitted candidates, 1,042 portfolio trades, 2,460 USD-M realized trades) without an explicit machine-readable transition ledger connecting them.
- Funnel conservation contains an unexplained $+2$ residual ($42,647 = 14,766 + 27,879 + 2$) labeled implicitly as `OTHER`.
- HTML report cells are rendered via string formatting rather than verifiable cell provenance expressions.

---

## 5. Required End State
1. **Population Lineage Ledger:**
   - Implement `PopulationLineageEntry` recorded into `population_lineage.jsonl`.
   - Every population carries `population_id`, `population_hash`, `parent_hash`, `count`, `transform_rule`, `filter_reason`.
   - Explicit funnel path: $\text{Setup} \to \text{Dedup} \to \text{Candidate} \to \text{Admitted} \to \text{PortfolioTrade} \to \text{VenueTrade}$.
2. **Residual Elimination:**
   - Disallow ambiguous `OTHER` buckets; all funnel residuals must map to formal typed categories.
3. **Report Cell Provenance:**
   - Implement `ReportCellProvenance` emitted to `report_cell_provenance.parquet` and `report_reconciliation.json`.
   - Every displayed statistic must carry `(artifact_hash, column_name, filter_predicate, aggregation_fn)`.

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/mod.rs
v8-core/src/evaluation/lineage.rs
v8-core/src/evaluation/html_report.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. Unit tests verifying strict population conservation: $\sum \text{partitions} == N_{\text{parent}}$.
3. Automated check: HTML report regeneration from parquet matches byte-for-byte.
4. Zero unclassified residual entries in funnel ledger.

---

## 8. Required Evidence Artifacts
- `population_lineage.jsonl`
- `cohort_manifest.json`
- `report_cell_provenance.parquet`
- `report_reconciliation.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not change simulator execution mechanics.
- Does not alter trade selection thresholds.

---

## 10. Guards
- [ ] Every KPI number rendered in the UI or report must have a direct provenance pointer in `report_cell_provenance.parquet`.
- [ ] No silent dropping of trades or candidates allowed without a typed lineage transition.

---

## 11. Normative Traceability
- **R1 — Population Lineage Integrity:** Every cohort must be immutable and hash-chained.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §2.1; arXiv:2512.22476 §4.
- **R2 — Zero-Residual Accounting:** Strict funnel equality without unmapped `OTHER` buckets.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §9.3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::evaluation::TradeRow`
- `v8-core::evaluation::schema_cache::SchemaCache`
- `v8-core::hash::Canon`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Conservation Law:** $N_{\text{Setup}} = N_{\text{DedupSuppressed}} + N_{\text{UniqueCandidates}}$.
- **I2 — Provenance Invariant:** $\forall \text{cell} \in \text{Report}, \text{CellVal} = \text{AggFn}(\text{Filter}(\text{Artifact}))$.

---

## 14. Canonical Failure Semantics
- Unmapped population drop $\implies$ `Err(EvaluationError::LineageConservationViolation)`.

---

## 15. Dependency Map
```text
Runloop / Simulation Traces
            │
            ▼
   [Population Lineage] ──► population_lineage.jsonl
            │
            ▼
   [Report Provenance] ──► report_cell_provenance.parquet
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If a report cell cannot be computed from saved parquet files without raw memory re-execution, STOP and escalate OPEN_PIN.
