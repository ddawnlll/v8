//! Value-safe SIMD primitives (D-088, #133).
//!
//! The one rule of this module: **an optimization may not change a value**
//! (COMPUTE_SCHEDULING_SPEC §5; D-088). SIMD is used here only where the lane
//! decomposition is bit-identical to the scalar reference:
//!
//! - Lane-wise `f64` arithmetic (`add`/`sub`/`mul`/`div`) is correctly rounded
//!   per lane — the IEEE 754 result of a lane op is the scalar result. The
//!   crate builds with `--fp-contract=off` (`.cargo/config.toml`), so no lane
//!   op fuses into an FMA that the scalar reference would not perform.
//! - Lane-wise `max`/`min` are exact (no rounding) and order-independent, so a
//!   SIMD fold reproduces a scalar scan bit-for-bit on any window whose
//!   elements are strictly ordered or merely share exact equal values. The one
//!   divergence mode is a `+0.0`/`-0.0` tie, and its outcome is even
//!   arch-dependent: NEON `FMAX`/`FMIN` follow IEEE-754 maxNum/minNum
//!   (`max(+0,-0) = +0`, `min(+0,-0) = -0`), SSE `MAXPD`/`MINPD` return the
//!   second source operand on a tie, and a scalar `if x > acc` scan keeps the
//!   first operand. Every outcome is a correct extreme (a zero of the right
//!   magnitude), and OHLC prices are strictly positive reals, so the window
//!   reductions in the K1/K2 feature path are bit-identical to the scalar
//!   reference on every real tape — see [`window_max`]/[`window_min`].
//! - Lane-wise comparisons (`>=`/`<=`) are exact; a SIMD compare is the scalar
//!   compare.
//!
//! What is deliberately NOT here: tree reductions of additions (reassociating
//! a float sum changes its rounding — reductions go through `state::fsum`,
//! the verbatim CPython port, never through SIMD lanes), and any
//! `pow(x, 2.0)` -> `x*x` style folding (the feature path `black_box`es the
//! exponent so libm `powf` survives; D-088).
//!
//! The lane width is two `f64` (`f64x2`): NEON and SSE2 are both native for
//! it, and it is narrow enough that every lane operation is exactly the scalar
//! IEEE operation. Wider vectors would require reassociation to materialize
//! their benefit — which this module refuses by construction.
//!
//! D-032 file-family registration: `simd.rs` — value-safe SIMD primitives
//! (Backend-1, #133). No `target_feature` gates are used; NEON (aarch64) and
//! SSE2 (x86_64) are baseline on their platforms and compile without feature
//! flags, so the crate stays stable-toolchain compatible.

use std::fmt;

/// A two-lane `f64` vector. The lane ops below are exactly the scalar IEEE
/// operations, so any bit pattern produced here is the bit pattern the scalar
/// backend would produce for the same operand order.
#[derive(Clone, Copy)]
pub struct F64x2(V);

/// The per-architecture vector register type.
#[cfg(target_arch = "aarch64")]
type V = std::arch::aarch64::float64x2_t;
#[cfg(target_arch = "x86_64")]
type V = std::arch::x86_64::__m128d;
/// Scalar fallback: a plain pair. Still `f64x2`-shaped so callers never split
/// into per-arch code paths; on exotic targets it degrades to element loops.
#[cfg(not(any(target_arch = "aarch64", target_arch = "x86_64")))]
type V = [f64; 2];

impl fmt::Debug for F64x2 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.to_array().fmt(f)
    }
}

impl F64x2 {
    /// Broadcast `x` to both lanes.
    #[inline(always)]
    pub fn splat(x: f64) -> F64x2 {
        F64x2(unsafe { arch::splat(x) })
    }

    /// Load `series[i]`, `series[i+1]`. Caller guarantees `i + 1 <
    /// series.len()`; the load is unaligned (columnar `Dataset` slices have no
    /// alignment guarantee).
    #[inline(always)]
    pub fn load_unaligned(series: &[f64], i: usize) -> F64x2 {
        F64x2(unsafe { arch::load(series, i) })
    }

    /// Store the two lanes into `out[i]`, `out[i+1]`.
    #[inline(always)]
    pub fn store_unaligned(self, out: &mut [f64], i: usize) {
        unsafe { arch::store(self.0, out, i) };
    }

    /// The two lanes as a plain array.
    #[inline(always)]
    pub fn to_array(self) -> [f64; 2] {
        unsafe { arch::to_array(self.0) }
    }

    /// Lane-wise maximum. Exact and order-independent (no rounding), so a
    /// left-to-right fold reproduces the scalar `if x > acc { x } else { acc }`
    /// scan bit-for-bit on any window without `+0.0`/`-0.0` ties — the whole
    /// OHLC price domain (see the module doc for the tie rule, which differs
    /// by architecture).
    #[inline(always)]
    pub fn max(self, rhs: F64x2) -> F64x2 {
        F64x2(unsafe { arch::max(self.0, rhs.0) })
    }

    /// Lane-wise minimum (the mirror of [`F64x2::max`]).
    #[inline(always)]
    pub fn min(self, rhs: F64x2) -> F64x2 {
        F64x2(unsafe { arch::min(self.0, rhs.0) })
    }

    /// Lane-wise addition (correctly rounded per lane; `fp-contract=off`
    /// guarantees no lane-op fusion).
    #[inline(always)]
    pub fn add(self, rhs: F64x2) -> F64x2 {
        F64x2(unsafe { arch::add(self.0, rhs.0) })
    }

    /// Lane-wise subtraction.
    #[inline(always)]
    pub fn sub(self, rhs: F64x2) -> F64x2 {
        F64x2(unsafe { arch::sub(self.0, rhs.0) })
    }

    /// Lane-wise multiplication.
    #[inline(always)]
    pub fn mul(self, rhs: F64x2) -> F64x2 {
        F64x2(unsafe { arch::mul(self.0, rhs.0) })
    }

    /// Lane-wise division (IEEE, correctly rounded per lane).
    #[inline(always)]
    pub fn div(self, rhs: F64x2) -> F64x2 {
        F64x2(unsafe { arch::div(self.0, rhs.0) })
    }

    /// Lane-wise `>=` (exact; a NaN lane compares false, like the scalar
    /// operator).
    #[inline(always)]
    pub fn ge(self, rhs: F64x2) -> [bool; 2] {
        unsafe { arch::ge(self.0, rhs.0) }
    }

    /// Lane-wise `<=` (exact).
    #[inline(always)]
    pub fn le(self, rhs: F64x2) -> [bool; 2] {
        unsafe { arch::le(self.0, rhs.0) }
    }

    /// Max of the two lanes with the scalar-scan tie rule (first lane wins:
    /// `if b > a { b } else { a }`) — exactly the scalar `if x > acc` scan.
    #[inline(always)]
    pub fn reduce_max(self) -> f64 {
        let [a, b] = self.to_array();
        if b > a { b } else { a }
    }

    /// Min of the two lanes with the scalar-scan tie rule.
    #[inline(always)]
    pub fn reduce_min(self) -> f64 {
        let [a, b] = self.to_array();
        if b < a { b } else { a }
    }

    /// Scalar `max` with the scalar-scan tie rule (`if b > a { b } else { a }`).
    /// Used for the odd trailing lane.
    #[inline(always)]
    pub fn scalar_max(a: f64, b: f64) -> f64 {
        if b > a { b } else { a }
    }

    /// Scalar `min` with the scalar-scan tie rule.
    #[inline(always)]
    pub fn scalar_min(a: f64, b: f64) -> f64 {
        if b < a { b } else { a }
    }
}

/// Fixed-window maximum of `series[from..to]`, bit-identical to a scalar
/// `let mut m = f64::NEG_INFINITY; for x in &series[from..to] { if *x > m { m =
/// *x; } }` scan whenever the window contains no `+0.0`/`-0.0` pair (the whole
/// OHLC price domain): max is exact and order-independent, and the IEEE
/// maxNum tie rule can differ from the scan only in which zero's sign is
/// returned for a `+0.0`/`-0.0` tie. NaN can never enter a valid tape. An
/// empty window returns `f64::NEG_INFINITY`, matching the scalar scan.
pub fn window_max(series: &[f64], from: usize, to: usize) -> f64 {
    debug_assert!(from <= to && to <= series.len());
    let mut acc = F64x2::splat(f64::NEG_INFINITY);
    let mut i = from;
    while i + 1 < to {
        acc = acc.max(F64x2::load_unaligned(series, i));
        i += 2;
    }
    let mut m = acc.reduce_max();
    if i < to {
        m = F64x2::scalar_max(m, series[i]);
    }
    m
}

/// Fixed-window minimum of `series[from..to]`, bit-identical to a scalar
/// `let mut m = f64::INFINITY; for x in &series[from..to] { if *x < m { m =
/// *x; } }` scan on any `+0.0`/`-0.0`-free window (the whole OHLC price
/// domain). An empty window returns `f64::INFINITY`.
pub fn window_min(series: &[f64], from: usize, to: usize) -> f64 {
    debug_assert!(from <= to && to <= series.len());
    let mut acc = F64x2::splat(f64::INFINITY);
    let mut i = from;
    while i + 1 < to {
        acc = acc.min(F64x2::load_unaligned(series, i));
        i += 2;
    }
    let mut m = acc.reduce_min();
    if i < to {
        m = F64x2::scalar_min(m, series[i]);
    }
    m
}

#[cfg(target_arch = "aarch64")]
mod arch {
    //! NEON `f64x2`. All intrinsics used are stable `std::arch::aarch64`
    //! (verified at first landing; NEON is aarch64 baseline, no feature flag).

    use std::arch::aarch64::*;

    #[inline(always)]
    pub unsafe fn splat(x: f64) -> float64x2_t {
        vdupq_n_f64(x)
    }

    #[inline(always)]
    pub unsafe fn load(series: &[f64], i: usize) -> float64x2_t {
        vld1q_f64(series.as_ptr().add(i))
    }

    #[inline(always)]
    pub unsafe fn store(v: float64x2_t, out: &mut [f64], i: usize) {
        vst1q_f64(out.as_mut_ptr().add(i), v);
    }

    #[inline(always)]
    pub unsafe fn to_array(v: float64x2_t) -> [f64; 2] {
        let mut a = [0.0; 2];
        vst1q_f64(a.as_mut_ptr(), v);
        a
    }

    #[inline(always)]
    pub unsafe fn max(a: float64x2_t, b: float64x2_t) -> float64x2_t {
        vmaxq_f64(a, b)
    }

    #[inline(always)]
    pub unsafe fn min(a: float64x2_t, b: float64x2_t) -> float64x2_t {
        vminq_f64(a, b)
    }

    #[inline(always)]
    pub unsafe fn add(a: float64x2_t, b: float64x2_t) -> float64x2_t {
        vaddq_f64(a, b)
    }

    #[inline(always)]
    pub unsafe fn sub(a: float64x2_t, b: float64x2_t) -> float64x2_t {
        vsubq_f64(a, b)
    }

    #[inline(always)]
    pub unsafe fn mul(a: float64x2_t, b: float64x2_t) -> float64x2_t {
        vmulq_f64(a, b)
    }

    #[inline(always)]
    pub unsafe fn div(a: float64x2_t, b: float64x2_t) -> float64x2_t {
        vdivq_f64(a, b)
    }

    #[inline(always)]
    pub unsafe fn ge(a: float64x2_t, b: float64x2_t) -> [bool; 2] {
        let m = vcgeq_f64(a, b);
        [vgetq_lane_u64(m, 0) != 0, vgetq_lane_u64(m, 1) != 0]
    }

    #[inline(always)]
    pub unsafe fn le(a: float64x2_t, b: float64x2_t) -> [bool; 2] {
        let m = vcleq_f64(a, b);
        [vgetq_lane_u64(m, 0) != 0, vgetq_lane_u64(m, 1) != 0]
    }
}

#[cfg(target_arch = "x86_64")]
mod arch {
    //! SSE2 `__m128d`. SSE2 is x86_64 baseline; all intrinsics are stable.

    use std::arch::x86_64::*;

    #[inline(always)]
    pub unsafe fn splat(x: f64) -> __m128d {
        _mm_set1_pd(x)
    }

    #[inline(always)]
    pub unsafe fn load(series: &[f64], i: usize) -> __m128d {
        _mm_loadu_pd(series.as_ptr().add(i))
    }

    #[inline(always)]
    pub unsafe fn store(v: __m128d, out: &mut [f64], i: usize) {
        _mm_storeu_pd(out.as_mut_ptr().add(i), v);
    }

    #[inline(always)]
    pub unsafe fn to_array(v: __m128d) -> [f64; 2] {
        let mut a = [0.0; 2];
        _mm_storeu_pd(a.as_mut_ptr(), v);
        a
    }

    #[inline(always)]
    pub unsafe fn max(a: __m128d, b: __m128d) -> __m128d {
        _mm_max_pd(a, b)
    }

    #[inline(always)]
    pub unsafe fn min(a: __m128d, b: __m128d) -> __m128d {
        _mm_min_pd(a, b)
    }

    #[inline(always)]
    pub unsafe fn add(a: __m128d, b: __m128d) -> __m128d {
        _mm_add_pd(a, b)
    }

    #[inline(always)]
    pub unsafe fn sub(a: __m128d, b: __m128d) -> __m128d {
        _mm_sub_pd(a, b)
    }

    #[inline(always)]
    pub unsafe fn mul(a: __m128d, b: __m128d) -> __m128d {
        _mm_mul_pd(a, b)
    }

    #[inline(always)]
    pub unsafe fn div(a: __m128d, b: __m128d) -> __m128d {
        _mm_div_pd(a, b)
    }

    #[inline(always)]
    pub unsafe fn ge(a: __m128d, b: __m128d) -> [bool; 2] {
        let m = _mm_movemask_pd(_mm_cmpge_pd(a, b));
        [(m & 1) != 0, (m & 2) != 0]
    }

    #[inline(always)]
    pub unsafe fn le(a: __m128d, b: __m128d) -> [bool; 2] {
        let m = _mm_movemask_pd(_mm_cmple_pd(a, b));
        [(m & 1) != 0, (m & 2) != 0]
    }
}

#[cfg(not(any(target_arch = "aarch64", target_arch = "x86_64")))]
mod arch {
    //! Scalar fallback for non-aarch64/x86_64 targets. Same lane semantics
    //! (element-wise), just without vector registers.

    #[inline(always)]
    pub unsafe fn splat(x: f64) -> [f64; 2] {
        [x, x]
    }

    #[inline(always)]
    pub unsafe fn load(series: &[f64], i: usize) -> [f64; 2] {
        [*series.get_unchecked(i), *series.get_unchecked(i + 1)]
    }

    #[inline(always)]
    pub unsafe fn store(v: [f64; 2], out: &mut [f64], i: usize) {
        *out.get_unchecked_mut(i) = v[0];
        *out.get_unchecked_mut(i + 1) = v[1];
    }

    #[inline(always)]
    pub unsafe fn to_array(v: [f64; 2]) -> [f64; 2] {
        v
    }

    #[inline(always)]
    pub unsafe fn max(a: [f64; 2], b: [f64; 2]) -> [f64; 2] {
        [super::F64x2::scalar_max(a[0], b[0]), super::F64x2::scalar_max(a[1], b[1])]
    }

    #[inline(always)]
    pub unsafe fn min(a: [f64; 2], b: [f64; 2]) -> [f64; 2] {
        [super::F64x2::scalar_min(a[0], b[0]), super::F64x2::scalar_min(a[1], b[1])]
    }

    #[inline(always)]
    pub unsafe fn add(a: [f64; 2], b: [f64; 2]) -> [f64; 2] {
        [a[0] + b[0], a[1] + b[1]]
    }

    #[inline(always)]
    pub unsafe fn sub(a: [f64; 2], b: [f64; 2]) -> [f64; 2] {
        [a[0] - b[0], a[1] - b[1]]
    }

    #[inline(always)]
    pub unsafe fn mul(a: [f64; 2], b: [f64; 2]) -> [f64; 2] {
        [a[0] * b[0], a[1] * b[1]]
    }

    #[inline(always)]
    pub unsafe fn div(a: [f64; 2], b: [f64; 2]) -> [f64; 2] {
        [a[0] / b[0], a[1] / b[1]]
    }

    #[inline(always)]
    pub unsafe fn ge(a: [f64; 2], b: [f64; 2]) -> [bool; 2] {
        [a[0] >= b[0], a[1] >= b[1]]
    }

    #[inline(always)]
    pub unsafe fn le(a: [f64; 2], b: [f64; 2]) -> [bool; 2] {
        [a[0] <= b[0], a[1] <= b[1]]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The window reductions must reproduce the scalar scans bit-for-bit on
    /// the declared data domain (OHLC prices: strictly positive reals, so no
    /// `+0.0`/`-0.0` ties), across odd and even windows, empty windows, and
    /// trailing single elements.
    #[test]
    fn window_max_min_bit_identical_to_scalar_scan() {
        let series: Vec<f64> = vec![
            3.0, 1.0, 4.5, 2.0, 5.0, 5.0, 2.5, 7.0, 9.0, 4.0, 8.0, 6.0, 7.5,
        ];
        let n = series.len();
        for from in 0..n {
            for to in from..=n {
                let mut m = f64::NEG_INFINITY;
                for x in &series[from..to] {
                    if *x > m {
                        m = *x;
                    }
                }
                assert_eq!(
                    window_max(&series, from, to).to_bits(),
                    m.to_bits(),
                    "window_max [{from}, {to})"
                );
                let mut m = f64::INFINITY;
                for x in &series[from..to] {
                    if *x < m {
                        m = *x;
                    }
                }
                assert_eq!(
                    window_min(&series, from, to).to_bits(),
                    m.to_bits(),
                    "window_min [{from}, {to})"
                );
            }
        }
        // Empty and single-element windows match the scan exactly.
        assert_eq!(
            window_max(&series, 4, 4).to_bits(),
            f64::NEG_INFINITY.to_bits()
        );
        assert_eq!(
            window_min(&series, 4, 4).to_bits(),
            f64::INFINITY.to_bits()
        );
    }

    /// The `+0.0`/`-0.0` tie is the one declared divergence mode, and it is
    /// arch-dependent: NEON `FMAX`/`FMIN` follow IEEE-754 maxNum/minNum
    /// (`max(+0,-0) = +0`, `min(+0,-0) = -0`), SSE `MAXPD`/`MINPD` return the
    /// SECOND source operand on a tie — so the two architectures can pick
    /// different zero signs. Both are a correct extreme (a zero of the right
    /// magnitude), and the scalar `if x > acc` scan keeps the first operand,
    /// so neither SIMD rule equals the scan's choice on `±0.0`. OHLC prices
    /// are strictly positive reals, so this can never fire on the K1/K2/K4
    /// path — the window reductions and the exit-walk extremes are
    /// bit-identical to the scalar reference on every real tape. This test
    /// pins that contract: a `±0.0` tie must return a zero of the correct
    /// magnitude, whichever sign the architecture picks.
    #[test]
    fn signed_zero_tie_returns_a_correct_zero_on_every_arch() {
        let pz = F64x2::splat(0.0_f64);
        let nz = F64x2::splat(-0.0_f64);
        for v in [
            pz.max(nz).to_array(),
            nz.max(pz).to_array(),
            pz.min(nz).to_array(),
            nz.min(pz).to_array(),
        ]
        .into_iter()
        .flatten()
        {
            assert!(v.to_bits() == 0.0f64.to_bits() || v.to_bits() == (-0.0f64).to_bits());
            assert_eq!(v, 0.0, "a ±0.0 tie must stay a zero");
        }
    }

    /// Lane arithmetic must be the scalar IEEE result per lane (this is the
    /// whole "value-safe" claim for `add`/`sub`/`mul`/`div`).
    #[test]
    fn lane_ops_are_scalar_ieee_per_lane() {
        let a = F64x2::splat(0.1_f64).add(F64x2::splat(0.2_f64));
        let [l0, l1] = a.to_array();
        assert_eq!(l0.to_bits(), (0.1_f64 + 0.2_f64).to_bits());
        assert_eq!(l1.to_bits(), (0.1_f64 + 0.2_f64).to_bits());

        let x = F64x2::load_unaligned(&[1.0e308_f64, 3.14_f64], 0);
        let y = x.mul(x);
        let [m0, m1] = y.to_array();
        assert_eq!(m0.to_bits(), (1.0e308_f64 * 1.0e308_f64).to_bits()); // +inf
        assert_eq!(m1.to_bits(), (3.14_f64 * 3.14_f64).to_bits());

        let z = x.sub(F64x2::splat(1.0_f64)).div(F64x2::splat(2.0_f64));
        let [z0, z1] = z.to_array();
        assert_eq!(z0.to_bits(), ((1.0e308_f64 - 1.0_f64) / 2.0_f64).to_bits());
        assert_eq!(z1.to_bits(), ((3.14_f64 - 1.0_f64) / 2.0_f64).to_bits());
    }

    /// Lane-wise comparisons are exact: a NaN lane compares false and a
    /// `+0.0`/`-0.0` pair compares equal, exactly like the scalar operators.
    #[test]
    fn lane_compares_match_scalar_operators() {
        let a = F64x2::splat(5.0);
        let b = F64x2::load_unaligned(&[5.0, 4.0], 0);
        assert_eq!(a.ge(b), [true, true]);
        assert_eq!(a.le(b), [true, false]);

        let nan = F64x2::splat(f64::NAN);
        assert_eq!(nan.ge(a), [false, false]);
        assert_eq!(nan.le(a), [false, false]);

        let pz = F64x2::splat(0.0);
        let nz = F64x2::splat(-0.0);
        assert_eq!(pz.ge(nz), [true, true]); // -0.0 >= +0.0 is true
        assert_eq!(nz.le(pz), [true, true]);
    }

    /// The scalar fold helpers must reproduce the `if x > acc` / `if x < acc`
    /// scan semantics for the odd trailing lane and the final lane combine —
    /// on the price domain this is what keeps the fold bit-identical.
    #[test]
    fn scalar_fold_helpers_match_scan() {
        assert_eq!(F64x2::scalar_max(2.0, 5.0), 5.0);
        assert_eq!(F64x2::scalar_max(5.0, 2.0), 5.0);
        assert_eq!(F64x2::scalar_min(2.0, 5.0), 2.0);
        assert_eq!(F64x2::scalar_min(5.0, 2.0), 2.0);
        // Equal values keep the first operand (the scan's `>`/`<` tests),
        // matching the vector fold for exact-equal positive values.
        assert_eq!(F64x2::scalar_max(3.0, 3.0), 3.0);
        assert_eq!(F64x2::scalar_min(3.0, 3.0), 3.0);
        // Reduce combines the two lanes left-to-right with the same rule.
        let v = F64x2::load_unaligned(&[4.0, 2.0], 0);
        assert_eq!(v.reduce_max(), 4.0);
        assert_eq!(v.reduce_min(), 2.0);
        let v = F64x2::load_unaligned(&[2.0, 4.0], 0);
        assert_eq!(v.reduce_max(), 4.0);
        assert_eq!(v.reduce_min(), 2.0);
    }
}
