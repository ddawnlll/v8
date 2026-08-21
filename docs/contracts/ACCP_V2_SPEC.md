# ACCP v2.0 — YAML-Native Agentic Coding Communication Protocol Spec

**Status:** RATIFIED CONTRACT (D-124)  
**Version:** 2.0.0  
**Format Profile:** ACCP-YAML  
**Owning Authority:** `docs/contracts/ACCP_V2_SPEC.md`, `WORK_ITEM_POLICY.md` §1–4

---

## 1. Executive Summary

ACCP v2.0 establishes a strict, serializable, and schema-validatable protocol for agentic coding communications:
- Source reports are native YAML documents (`.accp.yaml`).
- Markdown is a human-rendered view, never the raw machine source.
- All 27 official report types are registered with staged support levels (`known`, `template_available`, `schema_lite`, `schema_strict`, `gate_blocking`).
- Core principle: *Agent recommends $\to$ Compiler validates $\to$ Runtime decides.*

---

## 2. The 27 Official Report Types

1. **Core (10):** `RIR`, `PIR`, `IPR`, `TVR`, `HIR`, `RAR`, `PRR`, `CAR`, `ASR`, `ECR`
2. **Bugfix (5):** `BSR`, `BRR`, `RCA`, `FPR`, `FVR`
3. **Feature (5):** `FER`, `FDR`, `FCR`, `FIR`, `FGR`
4. **Writing (4):** `WBR`, `WDR`, `WER`, `WQR`
5. **Coordination (2):** `DCR`, `ECR`
6. **Documentation (1):** `ASR`

---

## 3. Strict YAML Source Profile

Every `.accp.yaml` report strictly adheres to required top-level keys:

```yaml
accp_version: "2.0.0"
source_format: "ACCP-YAML"
report:
  id: "P46_BSR_001"
  type: "BSR"
  family: "bugfix"
  kind: "bug_search"
  status: "complete"
meta:
  plan_id: "P46"
  workspace_id: "W01"
  repo_root: "."
agent:
  agent_id: "v8-agent"
  agent_role: "auditor"
capabilities:
  can_read_files: true
  can_run_commands: true
references: []
assumptions: {}
skipped_inspections: {}
final_status: {}
```

---

## 4. Integration with V8 Runtime Gates

- Reports with `schema_strict` and `gate_blocking` support feed directly into runtime completion and promotion gates.
- Command results, diff integrity, and rollback plans are structured and verifiable by continuous integration.
