# [IMPL] Issue #AUD-002: Population Lineage DAG & Cross-Source Reconciliation (F02, F03)

**Status:** READY / AUDITED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `rust`, `P0`, `methodology`  
**Owning Authority:** `EVALUATION_EVIDENCE_SYSTEM.md` §1–4, `TARGET_ORACLE_SPEC.md` §9, §17, arXiv:2512.22476 (P006), arXiv:2606.08285 (P008), arXiv:2606.27570 (P036).  
**Relationships:** Core root dependency for #177, #179, #180A, #181A, #182A, #183.

---

## 1. Objective
Build a deterministic Population Lineage DAG that makes distinct evaluation, candidate, admission, execution, fill, position, and economic-cashflow populations explicitly identifiable, hash-bound, and semantically reconcilable in pure Rust (`v8-core/src/evaluation/lineage.rs`), establishing automated detection of cross-source population disagreement (e.g. reconciling the conflicting $14,766 + 27,879 + 2$ vs $14,766 + 26,107 + 1,774 = 42,647$ funnel snapshots) rather than forcing unlike cohorts into a single conservation equation.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/audits/EVALUATION_EVIDENCE_SYSTEM.md`](docs/audits/EVALUATION_EVIDENCE_SYSTEM.md) §1–4 (Artifact reconciliation & provenance).
- **Oracle Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](docs/contracts/TARGET_ORACLE_SPEC.md) §9 (Cohort Semantics), §17 (Reconciliation Protocols).
- **Academic Literature:**
  - `P006` (arXiv:2512.22476): *AutoQuant* (Traceability & population lineage).
  - `P008` (arXiv:2606.08285): *Beyond Agent Architecture* (Artifact release & reproducibility).
  - `P036` (arXiv:2606.27570): *Auditing AI Investment Recommendations* (Executable provenance).

---

## 3. Change Class
`CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`

---

## 4. Current State
- Multiple distinct populations exist across execution, admission, and cashflows with differing cardinalities:
  - Candidates ($27,881$) $\to$ Admitted ($1,774$) $\to$ Fills ($2,460$) $\to$ Cashflow Events ($>5,000$).
- In current report rendering, a historical manifest snapshot ($14,766 + 27,879 + 2 = 42,647$) was juxtaposed against active run KPIs ($14,766 + 26,107 + 1,774 = 42,647$), creating a false $+2$ residual illusion caused by cross-cohort collision.
- The system lacks a typed DAG that binds every population node to a deterministic hash and validates cardinality contracts along edges.

---

## 5. Required End State
1. **Population Lineage DAG Architecture:**
   ```text
   SetupPopulation (42,647)
     │
     ├──► [dedup: Partition] ──► DedupSuppressedPopulation (14,766)
     │
     └──► CandidatePopulation (27,881)
            │
            ├──► [counterfactual: OneToOne] ──► CounterfactualOutcomePopulation (27,881)
            │
            └──► [admission: ZeroOrOne] ──► AdmittedCandidatePopulation (1,774)
                   │
                   └──► [order_gen: ZeroOrMany] ──► OrderPopulation
                          │
                          └──► [matching: ZeroOrMany] ──► FillPopulation (2,460)
                                 │
                                 └──► [position: OneToOne] ──► PositionTransitionPopulation
                                        │
                                        ├──► [commissions: OneOrMany] ──┐
                                        ├──► [funding: ZeroOrMany] ─────┼──► [Join] ──► EconomicCashflowPopulation
                                        ├──► [realized_pnl: ZeroOrOne] ─┤
                                        └──► [gap_loss: ZeroOrOne] ─────┘
   ```
2. **Cardinality & Node Contracts:**
   - Edge Cardinality Types: `OneToOne`, `ZeroOrOne`, `ZeroOrMany`, `OneOrMany`, `Partition`, `Join`.
   - Node Data Model: `population_id`, `population_hash`, `parent_hashes: Vec<String>`, `count: usize`, `transform_rule: String`, `filter_reason: Option<String>`.
   - Emits `population_lineage.jsonl` and `cohort_manifest.json`.
3. **Cross-Source Cohort Disagreement Gate:**
   - Any report or audit comparing numbers across disparate population hashes must fail closed:
     $$\text{Same KPI Label} \land (\text{Hash}_A \ne \text{Hash}_B) \implies \text{RECONCILIATION\_BLOCK}$$
4. **Semantic Report Cell Provenance:**
   - Emits `report_cell_provenance.parquet` and `report_reconciliation.json`.
   - Every rendered KPI cell must evaluate to:
     $$\text{CellValue} \equiv \text{AggFn}(\text{Query}(\text{Artifact}_{\text{hash}}, \text{Predicate}))$$

---

## 6. Expected File / Module Surface
```text
v8-core/src/evaluation/mod.rs
v8-core/src/evaluation/lineage.rs
v8-core/src/report.rs
```

---

## 7. Verification Gates
1. `cargo test --manifest-path v8-core/Cargo.toml` passing.
2. DAG validation: all `Partition` edges verify $N_{\text{parent}} \equiv \sum N_{\text{children}}$.
3. Cardinality validation: non-partition edges ($0:N$, $1:N$, Join) permit valid cardinality expansion without forced equal counts.
4. Cross-source disagreement check: detects the $27,879 / 2$ vs $26,107 / 1,774$ cohort mismatch and blocks inconsistent aggregation.
5. Semantic provenance verification: all report cells regenerate identically from parquet queries.

---

## 8. Required Evidence Artifacts
- `population_lineage.jsonl`
- `cohort_manifest.json`
- `report_cell_provenance.parquet`
- `report_reconciliation.json`

---

## 9. Non-Goals / Forbidden Scope
- Does not modify simulator execution mechanics or matching algorithms.
- Does not invent new error enum types (returns `std::io::Result` or boolean verification receipts).

---

## 10. Guards
- [ ] Partition conservation equality applies ONLY to declared `Partition` edges.
- [ ] Inconsistent population hashes under identical metric labels MUST trigger a reconciliation block.

---

## 11. Normative Traceability
- **R1 — Population Lineage DAG:** Implements acyclic graph with declared edge cardinality contracts.  
  *Authority:* `EVALUATION_EVIDENCE_SYSTEM.md` §2.1; arXiv:2512.22476 §4.
- **R2 — Cross-Cohort Reconciliation:** Reconciles disparate population snapshots with hash binding.  
  *Authority:* `TARGET_ORACLE_SPEC.md` §9.2, §17.1.

---

## 12. Existing Types / Interfaces to Reuse
- `v8-core::evaluation::TradeRow`
- `v8-core::evaluation::schema_cache::SchemaCache`
- `v8-core::cashflow::EconomicCashflow`
- `v8-core::hash::Canon`

---

## 13. Mathematical / Semantic Invariants
- **I1 — Partition Invariant:** $\forall \text{PartitionEdge}(P \to \{C_1, \dots, C_k\}), \quad N(P) \equiv \sum_{i=1}^k N(C_i)$.
- **I2 — Expansion Invariant:** $\forall \text{ManyEdge}(P \to C), \quad N(C) \ge 0$.
- **I3 — Cohort Binding Invariant:** $\text{Hash}(A) \ne \text{Hash}(B) \implies \neg\text{Reconcilable}(\text{Metric}_A, \text{Metric}_B)$.

---

## 14. Canonical Failure Semantics
- Lineage or cohort discrepancy $\implies$ `Err(io::Error::new(io::ErrorKind::InvalidData, "Lineage reconciliation discrepancy"))`.

---

## 15. Dependency Map
```text
Runloop / Cashflow Engine
            │
            ▼
[Population Lineage DAG Engine] ──► population_lineage.jsonl / cohort_manifest.json
            │
            ▼
 [Semantic Cell Provenance] ──► report_cell_provenance.parquet / report_reconciliation.json
```

---

## 16. Ambiguity / OPEN_PIN Triggers
- If two report modules reference conflicting historical manifests without declared cohort IDs, STOP and open OPEN_PIN.
