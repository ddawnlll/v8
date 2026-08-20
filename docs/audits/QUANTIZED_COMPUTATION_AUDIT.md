# Quantized Computation Applicability Audit

**Status:** `NO_ECONOMIC_CLAIM`  
**Date:** 2026-08-20  
**Scope:** whether V8 currently implements quantized computation, whether
quantization would strengthen its determinism contract, and which adjacent
implementation defects must be resolved before such a design could be
considered.

## 1. Executive verdict

`PROJECT_EVIDENCE_SUPPORTED`: V8 does **not** currently implement quantized
computation. The authoritative Rust runtime uses IEEE-754 `f64`, canonical
bit-encoded identities, fixed reduction order, scalar/SIMD/backend parity
checks, and explicit rejection of fast-math/FMA contraction where those could
change values. This is a deterministic floating-point design, not an integer,
fixed-point, FP8, INT8, or lower-bit quantized design.

`LITERATURE_SUPPORTED`: integer-only inference can reduce compute and storage
cost, but requires an explicit quantization scheme and accuracy-preservation
procedure; it is not obtained merely by storing floating-point values as bits
[1]. Cross-platform integer-only inference can remove a class of floating-point
inconsistency in a declared learned-compression setting [2]. Parallel
floating-point non-associativity remains a documented reproducibility hazard,
which supports V8's existing fixed-order/backend-parity controls without
implying that quantization is required [3].

`OPEN_QUESTION`: no V8 decision currently defines the minimum objects needed
for a quantized runtime: bit width, signedness, scale, zero-point, rounding
mode, clipping/saturation, accumulator width, overflow behavior, calibration
population, out-of-range policy, dequantization boundary, or cross-backend
parity oracle. Quantization therefore remains absent by default.

## 2. Project evidence

The repository-wide source scan found no quantization contract or production
implementation. The closest related controls are different in kind:

- `PARITY_AND_IDENTITY_SPEC` requires value-level bit parity between the Python
  oracle and Rust migration stages.
- `COMPUTE_SCHEDULING_SPEC` requires backend invariance and deterministic
  reduction behavior.
- `hash.rs` encodes existing `f64` values by IEEE-754 bits for identity; it
  does not quantize those values.
- `evidence.rs` stores numeric columns as fixed-width IEEE-754 or two's
  complement bytes; binary storage is not lower-precision computation.

`PROJECT_EVIDENCE_SUPPORTED`: after the D-103 remediation below, the Rust
release handoff suite passed 253/253 tests on 2026-08-20, including scalar/SIMD
parity, thread-count byte identity, f64 hash
encoding, subnormal handling, and deterministic statistics fixtures. The
Python-boundary and forbidden-component audits also passed. These checks
support the current deterministic-f64 claim only.

## 3. Quantization contract that is missing

Any proposal must preregister at least:

1. the exact fields or kernels to quantize;
2. representation (`INT8`, `INT16`, fixed-point Q-format, FP8 variant, or
   another declared format);
3. per-tensor/per-channel/per-field scale and zero-point semantics;
4. rounding, tie, clipping, saturation, accumulator, and overflow rules;
5. a development-only calibration population and its three-clock/PIT rules;
6. frozen-OOS error metrics against the authoritative `f64` baseline;
7. backend-independent golden vectors, including extremes and regime shifts;
8. identity/version discontinuities and artifact-header encoding;
9. an explicit cost decision that quantization could change; and
10. a registry decision before it enters any decision or evidence path.

`LITERATURE_SUPPORTED`: financial time-series post-training quantization can be
materially calibration-sensitive at four bits, with regime-dependent activation
ranges; eight-bit or weight-only alternatives can be more robust when
degradation remains [4]. That result is specific to neural financial forecasting
and does not establish a V8 benefit. It does establish that calibration cannot
be treated as a harmless implementation detail.

## 4. Adjacent repository evaluation boundary

`PROJECT_EVIDENCE_SUPPORTED`: the evaluation evidence system in
`v8-core/src/evaluation/` has been purged of synthetic data and bound to strict
Constitution Rule 12 (`NO_ECONOMIC_CLAIM`). Economic authority and statistical
testing remain exclusively in the registered `statistics/` and `report.rs` path;
`evaluation/` provides orthogonal evidence surfaces (authority taxonomy, lineage
DAG, PIT temporal non-interference, and multiple-testing utilities) and Target
Oracle coverage records without emitting autonomous or uncertified economic claims.

## 5. Decision

`PROVISIONAL_DECISION`: retain the current deterministic `f64` computation
contract. Do not introduce quantization until a challenger proposal supplies
the missing contract, a simpler-baseline comparison, frozen-OOS error evidence,
backend parity, and a registry decision (D-118).

Nothing in this audit supports profitability, validated execution, a promoted
trading system, or a compute-speed claim.

## References

1. Jacob et al., *Quantization and Training of Neural Networks for Efficient
   Integer-Arithmetic-Only Inference*, arXiv:1712.05877,
   https://arxiv.org/abs/1712.05877
2. He et al., *Post-Training Quantization for Cross-Platform Learned Image
   Compression*, arXiv:2202.07513, https://arxiv.org/abs/2202.07513
3. Shanmugavelu et al., *Impacts of floating-point non-associativity on
   reproducibility for HPC and deep learning applications*, arXiv:2408.05148,
   https://arxiv.org/abs/2408.05148
4. Ye and Wanjiku, *Calibration Bets on the Past: Post-Training Quantization
   for Financial Time-Series Forecasting*, arXiv:2608.12259,
   https://arxiv.org/abs/2608.12259
