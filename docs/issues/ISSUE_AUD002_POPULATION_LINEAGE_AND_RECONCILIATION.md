# [IMPL] Issue #AUD-002: Population Lineage DAG & Cross-Section Reconciliation (F02, F03)

**Status:** READY / AMENDED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, `TARGET_ORACLE_SPEC.md` §9, §17, arXiv:2512.22476 (P006), arXiv:2606.08285 (P008), arXiv:2606.27570 (P036).  
**Relationships:** Core root dependency for #177, #179, #180A, #181A, #182A, #183.

---

## 1. Objective
Implement deterministic population lineage tracking as a directed acyclic graph (Population Lineage DAG) with explicit edge cardinality contracts ($1:1, 0:1, 1:N$, partition, join), and establish semantic report-to-artifact cell provenance in pure Rust (`v8-core/src/evaluation/lineage.rs`), ensuring every KPI population carries explicit parent hashes, transformation rules, and zero unclassified funnel residuals ($42,647 = 14,766 + 27,879 + 2$).

---

## 2. Owning Authority
- **Primary Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4 (Artifact reconciliation & provenance).
- **Oracle Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §9 (Cohort Semantics), §17 (Reconciliation).
- **Academic Literature:**
  - `P006` (arXiv:2512.22476): *AutoQuant* (Traceability & population lineage).
  - `P008` (arXiv:2606.08285): *Beyond Agent Architecture* (Artifact release & reproducibility).
  - `P036` (arXiv:2606.27570): *Auditing AI Investment Recommendations* (Executable provenance).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- The evaluation report presents separate populations (42,647 setups, 14,766 dedup suppressions, 1,774 admitted candidates, 1,042 portfolio trades, 2,460 USD-M realized trades) without explicit cardinality contracts.
- A naive linear funnel assumption incorrectly treats $1,774 \to 2,460$ as a conservation bug, whereas discrete execution permits $1:N$ fills and partial executions.
- Funnel conservation contains an unexplained $+2$ residual ($42,647 = 14,766 + 27,879 + 2$) labeled implicitly as `OTHER`.
- HTML report cells are formatted as raw strings rather than carrying verifiable cell provenance references.

---

## 5. Required End State
1. **Population Lineage DAG Architecture:**
   ```text
   SetupPopulation
     │
     ├──► [dedup: partition] ──► DedupSuppressedPopulation (14,766)
     │
     └──► CandidatePopulation (27,881)
            │
            ├──► [counterfactual: 1:1 attribution] ──► CounterfactualOutcomePopulation
            │
            └──► [admission: 0:1 filter] ──► AdmittedCandidatePopulation (1,774)
                   │
                   └──► [order_generation: 1:1 or 1:N] ──► OrderPopulation
                          │
                          └──► [matching: 1:N permitted fills] ──► FillPopulation (2,460)
                                 │
                                 └──► [accounting: 1:1 transition] ──► CashflowPopulation
   ```
2. **Explicit Edge Cardinality Contracts:**
   - Every DAG edge defines its cardinality: `OneToOne`, `ZeroOrOne`, `OneToMany { max_branch: usize }`, `Partition`, `Join`.
   - Node identity carries: `population_id`, `population_hash`, `parent_hashes`, `count`, `transform_rule`, `filter_reason`.
   - Emits `population_lineage.jsonl` and `cohort_manifest.json`.
3. **Residual Elimination:**
   - Disallow ambiguous `OTHER` buckets; all funnel residuals must map to formal typed categories.
4. **Semantic Report Cell Provenance:**
   - Implement `ReportCellProvenance` emitted to `report_cell_provenance.parquet` and `report_reconciliation.json`.
   - Every rendered KPI cell must be regenerable via:
     $$\text{CellValue} = \text{AggFn}(\text{Filter}(\text{Artifact}_{\text{hash}}, \text{Predicate}))$$
   - Emits deterministic `report_hash`.

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
2. DAG validation test: every edge verifies its explicit cardinality contract ($1:1, 0:1, 1:N$, partition).
3. Report cell reconciliation test: every displayed KPI value matches the semantic query over parquet artifacts.
4. Funnel partition equality: $\sum \text{Partitions} \equiv N_{\text{parent}}$ with 0 unclassified residuals.

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
- Does not enforce byte-for-byte HTML rendering invariance (semantic provenance + report_hash only).

---

## 10. Guards
- [ ] Every population transition in the DAG must declare its cardinality contract.
- [ ] No candidate or trade may be dropped without an explicit lineage node and typed filter reason.

---

## 11. Normative Traceability
- **R1 — Population Lineage DAG:** Implements acyclic provenance graph with cardinality contracts.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §2.1; arXiv:2512.22476 §4.
- **R2 — Semantic Cell Provenance:** Every report value maps to an artifact query expression.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §3.2; arXiv:2606.27570 §3.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::evaluation::TradeRow`
- `v8-core::evaluation::schema_cache::SchemaCache`
- `v8-core::hash::Canon`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Partition Invariant:** $\forall \text{PartitionEdge}(P \to \{C_1, \dots, C_k\}), \quad N(P) \equiv \sum_{i=1}^k N(C_i)$.
- **I2 — Semantic Cell Invariance:** $\text{RenderedValue}(c) \equiv \text{AggFn}(\text{Query}(\text{Artifact}, c.\text{predicate}))$.

---

## 14. Canonical Failure Semantics
- Edge cardinality violation $\implies$ `Err(EvaluationError::LineageCardinalityViolation)`.

---

## 15. Dependency Map
```text
Runloop / Execution Engine
            │
            ▼
 [Population Lineage DAG Engine] ──► population_lineage.jsonl / cohort_manifest.json
            │
            ▼
   [Semantic Cell Provenance] ──► report_cell_provenance.parquet / report_reconciliation.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If a report cell cannot be computed from saved parquet files via declarative filters, STOP and open OPEN_PIN.
