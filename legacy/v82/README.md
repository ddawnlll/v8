# [NON_CANONICAL / FORENSIC_ONLY] V8.2 Legacy Quarantine

**Status:** FROZEN FORENSIC ARCHIVE — NON-CANONICAL  
**Owning Authority:** V8 Constitution Rule 35 & Decision D-136  
**Security Level:** QUARANTINED FORENSIC DATA  

---

## 🚨 MANDATORY GOVERNANCE WARNING

All code, diagnostic tools, and generated audit artifacts in this directory tree are **historical fossils** from the frozen V8.0–V8.2 platform.

1. **NO RUNTIME ACCESS:** No module in `v8-core/` (Rust authoritative runtime) or active V8.3 tooling may import or execute anything in `legacy/v82/`.
2. **NO CURRENT EVIDENCE:** The numbers, diagnostics, p-values, or trade attributions produced by legacy tools (such as `tools/diagnostics.py` or `.audit/diagnostic/`) reflect the deprecated Python simulation and MUST NOT be cited or used as current V8.3 evidence or policy claims.
3. **ISOLATION POLICY:** Discovery tools and autonomous agents must ignore this directory unless explicit `--include-forensic-legacy` is specified for historical replication audits.
