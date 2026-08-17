# V8.2 Compute Scheduling Specification

**Status:** PROVISIONAL_DECISION (D-084, implementation update D-098). This contract governs how the compute
core distributes work across cores and, conditionally, across a GPU. Backend
selection is an **internal implementation detail**: no caller chooses it, and by
`PARITY_AND_IDENTITY_SPEC` G5 no backend may change a value. No economic claim
(rule 12).

## 1. Interface

The caller submits one evaluation request and receives artifacts:

```rust
let result = engine.evaluate(request)?;
```

The engine decides what runs where. There is no per-backend API, no
`use_gpu` flag in the experiment manifest, and no scheduling parameter in any
hash. A scheduling decision that could alter a result would make the manifest
incomplete; G5 is what keeps scheduling out of the identity.

## 2. Kernel granularity: modular, never monolithic

Work is expressed as separate kernels with explicit buffers between them:

| Kernel | Shape | Parallel over |
|---|---|---|
| K1 feature series | sequential recurrences (EMA, Wilder, ADX) + fixed windows | symbols, feature families |
| K2 state assembly | column gather + identity | bars |
| K3 expert predicates | branchy, data-dependent | bars x experts |
| K4 candidate replay | short bounded bar walk | (candidate, action) cells |
| K5 cube reduction | per-Candidate accumulators | candidates |
| K6 bootstrap / resampling | independent resamples | resamples |

A single fused kernel spanning features → experts → replay → regret is
**prohibited**. The reasons are structural, not stylistic: it maximizes
divergence and register pressure, it makes a CPU fallback impractical, it makes
one Expert edit recompile everything, and it destroys the ability to attribute
a cost or a defect to a stage. Modularity here is what preserves the
measurability the program depends on.

Buffers between kernels are owned by the engine, not by any kernel.

## 3. Where the work actually is

Measured on V8.0 for a symbol-year at 1h (`PERFORMANCE_AUDIT_V82`):

| Kernel | Character | Measured cost |
|---|---|---|
| K1/K2 | prefix-dependent recurrences; poor SIMD/GPU fit | ~2.8 s for 648,240 feature computations (~4.3 us each) after removing the O(N^2) lineage term |
| K4 | uniform, short, embarrassingly wide | 6.4 us per cell, 246,884 cells |
| K5 | associative accumulation | dominated by K4 |

The two shapes are opposites, and the naive intuition inverts them: the layer
that is expensive (features) is the one least suited to a wide backend, and the
layer that is wide (replay cells) is individually trivial.

## 4. Parallelism order

1. **Task parallelism across independent units first.** Symbols are fully
   independent; so are cells within a Candidate and Candidates within a symbol.
   This requires no vectorization, no backend, and no new numerical risk, and
   it is the largest single multiplier available.
2. **SIMD within a kernel** where the data layout already permits it (columnar
   `Dataset`), for K1 window reductions and K4 barrier comparisons.
3. **GPU only past the trigger in §6.**

Determinism constraint on all three: a parallel decomposition may not change
any value. Reductions with a data-dependent order are therefore performed
either in a fixed sequential order or with a fixed-shape tree whose shape does
not depend on the thread count.

## 5. Determinism per backend

This section is the reason backend selection can be an implementation detail at
all.

**K1/K2 (feature path).** These contain floating-point reductions — window
sums, EMA recurrences, Wilder smoothing. Reassociating a floating-point
reduction changes its result. Therefore: the reduction order for every feature
is **declared and fixed**, identical on every backend and every thread count.
A backend that cannot honour the declared order is not eligible for K1/K2.

**K4 (replay cells).** Each cell is a sequential walk executed by one worker.
There is no cross-worker reduction, no reassociation, and no transcendental
function in the path — only comparisons, additions and multiplications on `f64`.
Bit-identical results across backends are therefore achievable, subject to:

- FMA contraction disabled (a fused multiply-add rounds once where the
  reference rounds twice);
- fast-math / unsafe-math optimizations disabled;
- `f64` throughout — no implicit demotion to `f32` on any backend;
- a declared NaN payload normalization (`PARITY_AND_IDENTITY_SPEC` §4).

**K6 (resampling).** Resample indices come from a declared deterministic
generator seeded from the request, never from a backend-supplied RNG. Results
are combined in index order, not completion order.

An earlier framing in this program treated "GPU breaks determinism" as a
blanket rule. That is accurate for K1/K2 and inaccurate for K4; the distinction
is recorded here because it is exactly the distinction that decides what may
ever be offloaded.

## 6. The GPU trigger and implemented capability gate

The original design trigger remains a workload/economics inference, not a
permission bit. D-098 adds an optional Linux Vulkan backend so the runtime can
measure the question when a compatible device exists; the backend is still
ineligible unless it satisfies the semantic capability contract below.
Arithmetic, from the measured cell cost:

| Substrate | per cell | 10^7 cells | 10^9 cells |
|---|---|---|---|
| Python, index-bounded (measured) | 6.4 us | ~64 s | ~1.8 h |
| Rust CPU, single core (estimate) | ~0.1 us | ~1 s | ~100 s |
| Rust CPU, 10 cores (estimate) | ~0.01 us | ~0.1 s | ~10 s |
| GPU (estimate) | ~0.001 us | transfer-bound | ~1 s |

**Design trigger: a routine request exceeding ~10^9 replay cells.** Below it, the GPU
saves seconds over a multicore CPU backend while adding a second numerical
surface to certify (§5), a second toolchain, and a second failure mode. Above
it, the arithmetic finally amortizes transfer and launch overhead.

The research target as presently scoped — 100 symbols, 15m base, ~10 component
interventions — is ~10^9 cells only in aggregate across all symbols, i.e. ~10^7
per request. It does **not** trigger. The configuration that would is an
Expert-variant sweep (thousands of variants x symbols x cells), which is an
open scope question (`OPEN_DECISIONS`).

`Auto` has no baked-in GPU crossover.  It stays on the CPU until the certified
Linux `SHADER_F64` release runner injects a positive
`V8_GPU_CROSSOVER_STEPS` measured on that adapter; the value is deliberately
not part of request identity.  A request below that measured threshold, an
unavailable adapter, a non-`BarClose` fill policy, or any unsupported cell
falls back to CPU in `Auto`. Explicit `Gpu` returns an error for those cases.
The independent `gpu-release-parity` workflow is the required hardware gate:
it emits and retains the capability/no-FMA probe and CPU-to-GPU bitwise golden
receipt.  A normal hosted CI runner cannot substitute for that receipt.

Writing kernels in a backend-portable form so the decision can be deferred at
near-zero cost is a legitimate design choice, on one condition: the portable
form's CPU output must be competitive with a directly-written CPU kernel. That
is an assumption to be **measured before adoption**, not a premise.

**The f64 contract constrains any GPU path more than the trigger does
(D-096).** K4 runs `f64` throughout with FMA contraction and fast-math off
(D-084), and GPU fp64 is a wall on every portable route: Metal exposes no
fp64 in shaders; Vulkan exposes `SHADER_F64` (native only) but fp64
operations run 16-64x slower than f32 (wgpu feature docs); consumer CUDA/HIP
parts (RTX 40/50, RX 7000) execute fp64 at 1/16-1/32 rate. So even past the
trigger, a K4 f64 backend amortizes transfer only at a 16-64x
per-operation penalty — the economics close before the trigger does. If a
portable layer is ever adopted it is CubeCL over wgpu: CubeCL compiles one
kernel IR to CUDA/HIP/Metal/Vulkan/CPU, matching the K1-K6 kernel structure
and the "backend is not kernel semantics" rule, while wgpu sits at the
buffer/pipeline/dispatch level. On Apple, both paths run through wgpu, so
the fp64 limitation applies regardless. K1/K2 (reduction-order sensitive,
D-084) stay CPU-only; K4 (no cross-worker reduction) is the only GPU
candidate.

## 7. Resource policy

- Concurrency defaults to available parallelism minus a small reserve; it is
  configurable and, by G5, cannot appear in any hash.
- Memory: one `Dataset` allocation per symbol per request; kernels borrow. A
  kernel that allocates per cell is a defect (`COMPUTE_CORE_SPEC` §5).
- Failure: a worker fault fails the whole request. Partial results are never
  emitted, because a partial cube silently changes every per-Candidate maximum
  in §`OUTCOME_CUBE_SPEC` 6.

## 8. Cheap executable tests

1. **Thread invariance:** the same request at 1, 2, and N threads produces
   byte-identical artifacts.
2. **Backend invariance:** where a second backend exists, K4 outputs are
   bit-identical to the CPU backend on the full fixture set.
3. **Contraction check:** a fixture chosen so that FMA and separate
   multiply-add differ detects an accidentally contracted build.
4. **No fusion:** the kernel registry test asserts each of K1-K6 is separately
   dispatchable and separately timeable.
5. **Trigger honesty:** the engine logs the cell count of every request, so the
   §6 threshold is checked against reality rather than assumed.
6. **Partial-failure:** an injected worker fault produces no artifact.

## 9. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** the 6.4 us/cell replay cost, the 246,884-cell
  symbol-year, and the ~4.3 us/feature figure (`PERFORMANCE_AUDIT_V82` §§5-6).
- **DESIGN_INFERENCE:** the kernel decomposition, the parallelism order, the
  per-backend determinism analysis, and the ~10^9 trigger. Every Rust and GPU
  per-cell figure in §6 is an estimate, not a measurement, and is labelled as
  such in the table.
- **REJECTED_OPTION:** a single fused kernel spanning features through
  statistics (§2), and any backend flag exposed in the experiment manifest
  (§1).
- **Not claimed:** that GPU is faster or economically justified. D-098 proves
  the implementation and fail-closed contract; a physical Linux `SHADER_F64`
  device is still needed for the runtime parity receipt and crossover benchmark.
