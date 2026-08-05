# P4 artifact integrity audit

Run the structural gate before treating a checkpoint as complete:

```bash
python3 tools/p4_integrity_audit.py \
  --full-run registry/p4_full_run.json \
  --checkpoint registry/p4_full_run.checkpoint.json
```

The command exits non-zero when the checkpoint disagrees with the detailed
run artifact, when round/book accounting is incomplete, when category totals
do not close, or when the checkpoint's human-readable note disagrees with its
numeric fields. Duplicate `claim_ref` values are reported as warnings and are
never used as dictionary keys; list position remains the record identity.

This is a structural gate, not a semantic extraction-quality verdict. A PASS
does not establish recall, provenance correctness, or market transferability.
