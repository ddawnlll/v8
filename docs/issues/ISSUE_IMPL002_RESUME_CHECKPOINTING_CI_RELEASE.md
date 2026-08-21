# [IMPL] Issue: Simulation Checkpoint / Resume Mechanism and Automated CI Release Packaging

**Status:** RESOLVED & RATIFIED (D-122)
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `CONTRACT_IMPLEMENTATION` / `NEW_FILE_FAMILY_OR_MODULE`  
**Labels:** `type:implementation`, `triage`, `risk:medium`  
**Owning Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md`

---

## 1. Objective
Implement an atomic checkpointing and `--resume` recovery mechanism in `v8-core/src/runloop.rs` to allow long-running multi-day simulations to survive crashes/interruptions, and establish an automated GitHub Actions release workflow for building and packaging production binaries.

---

## 2. Owning Authority
- **Authority:** V8 Constitution Rule 1, `docs/WORK_ITEM_POLICY.md` §6.
- **Decisions:** `D-099` (Fault tolerance and compute efficiency).

---

## 3. Current State
- `v8-core/src/runloop.rs:150-200` treats entire simulation runs as monolithic atomics. Any process termination requires restarting the simulation from bar 0.
- `.github/workflows/` contains CI verification workflows (`ci.yml`, `gpu-release-parity.yml`) but lacks automated release artifact packaging for version tags.

---

## 4. Required End State
1. **Checkpoint / Resume Engine:**
   - Add periodic state snapshots (e.g. every $N$ bars or on `SIGINT`/interval) serialized to an atomic `.checkpoint` file.
   - Introduce `--resume <path>` CLI flag in `v8-core` to seamlessly restore simulation state and continuation.
2. **Automated Release Pipeline:**
   - Create `.github/workflows/release.yml` triggered on version tag pushes (`v*`), compiling release binaries for target architectures (Linux x86_64, macOS aarch64/x86_64) and attaching them to GitHub Releases.

---

## 5. Expected File / Module Surface
- `v8-core/src/runloop.rs` [MODIFY]
- `v8-core/src/checkpoint.rs` [NEW]
- `v8-core/src/main.rs` [MODIFY]
- `.github/workflows/release.yml` [NEW]

---

## 6. Verification Gates
```shell
cargo check --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml --test checkpoint_resume_test
```

---

## 7. Required Evidence Artifacts
- Unit/integration test demonstrating saving at bar $K$, terminating, and resuming to completion with 100% bitwise parity against an un-interrupted run.

---

## 8. Non-Goals / Forbidden Scope
- Altering the simulation outcome or state transition semantics during resumption.

---

## Context-Completeness Contract

### 11. Normative Traceability
- **R1 — Atomic Checkpointing:** Simulation state snapshot must be atomically written and crash-resilient.
  * *Authority:* `D-099`.
- **R2 — Resumption Bitwise Parity:** Resumed simulation from checkpoint must produce identical state to non-interrupted execution.
  * *Authority:* V8 Constitution Rule 1.
- **R3 — Release Packaging:** Automated binary artifact generation on version tags.
  * *Authority:* `docs/WORK_ITEM_POLICY.md` §6.

### 12. Existing Types / Interfaces to Reuse
- Reuse `DecisionState`, `MarketState`, `AccountState`, and CLI argument structures.

### 13. Mathematical / Semantic Invariants
- **I1:** $\text{State}(\text{Run}_{0 \to N}) \equiv \text{State}(\text{Resume}(\text{Checkpoint}_K) \to N)$.

### 14. Canonical Failure Semantics
- Corrupted checkpoint files return `V8CoreError::InvalidCheckpointError` and fail closed.

### 15. Dependency Map
```text
Runloop -> CheckpointWriter -> Atomic Disk Snapshot
CLI --resume -> CheckpointReader -> Runloop State Restoration
GitHub Tag Push -> release.yml -> Build Artifacts -> GitHub Release
```

### 16. Ambiguity / OPEN_PIN Triggers
- If schema evolution breaks older checkpoint files, add explicit version header in checkpoint file format.
