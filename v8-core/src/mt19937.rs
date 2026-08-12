//! S7 bit-exact MT19937 RNG parity (issue #127).
//!
//! CPython's stdlib `random` is Mersenne Twister 19937; the frozen oracle
//! `statistics.py` uses `random.Random(seed)` for bootstrap/permutation draws.
//! For bit-exact parity this module reproduces CPython 3.14 exactly:
//!
//! - seeding: `random.Random(int)` -> `_randommodule.c` `random_seed` ->
//!   `init_by_array` over the seed's 32-bit words (least significant first).
//!   The `version=2` parameter does not engage for int seeds.
//! - the draw: `random()` calls genrand_res53 (the 53-bit double from two
//!   tempered words), NOT getrandbits(53)/2**53 (empirically different bits
//!   on CPython 3.14).
//! - `randrange(n)` / `getrandbits(k)` / `sample(range(n), n)` follow CPython
//!   3.14 `random.py`: `_randbelow_with_getrandbits`, top-k-bits `getrandbits`,
//!   pool-branch Fisher-Yates (no `k == n` short-circuit in 3.14 — it draws).
//!
//! Unit tests assert bit-for-bit equality against sequences captured from the
//! frozen oracle's interpreter (`.venv/bin/python`, Python 3.14.0).
#![allow(dead_code)]

const N: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908_b0df;
const UPPER_MASK: u32 = 0x8000_0000;
const LOWER_MASK: u32 = 0x7fff_ffff;

/// Bit-exact port of CPython 3.14 `random.Random` (Mersenne Twister 19937).
pub struct MT19937 {
    mt: [u32; N],
    mti: usize,
}

impl MT19937 {
    /// `random.Random(seed)`: `init_by_array` over the seed's 32-bit words.
    ///
    /// `_randommodule.c` `random_seed` for an int arg: `n = abs(seed)`, split
    /// into little-endian 32-bit words, `keyused = bits==0 ? 1 : (bits-1)/32+1`,
    /// then `init_by_array`. Seeds are already non-negative `u64`, so `abs`
    /// is the identity.
    pub fn new(seed: u64) -> Self {
        let bits = 64 - seed.leading_zeros(); // 0 when seed == 0
        let keyused = if bits == 0 { 1 } else { (bits as usize - 1) / 32 + 1 };
        let mut key = [0u32; 2]; // covers u64 seeds (keyused <= 2)
        for i in 0..keyused {
            key[i] = (seed >> (32 * i)) as u32;
        }

        let mut rng = Self::init_genrand(19650218);
        let mut i = 1usize;
        let mut j = 0usize;
        let mut k = if N > keyused { N } else { keyused };
        while k > 0 {
            let x = rng.mt[i] ^ (rng.mt[i - 1] ^ (rng.mt[i - 1] >> 30)).wrapping_mul(1664525);
            rng.mt[i] = x.wrapping_add(key[j]).wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                rng.mt[0] = rng.mt[N - 1];
                i = 1;
            }
            if j >= keyused {
                j = 0;
            }
            k -= 1;
        }
        for _ in 0..N - 1 {
            rng.mt[i] = rng.mt[i]
                ^ (rng.mt[i - 1] ^ (rng.mt[i - 1] >> 30)).wrapping_mul(1566083941);
            rng.mt[i] = rng.mt[i].wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                rng.mt[0] = rng.mt[N - 1];
                i = 1;
            }
        }
        rng.mt[0] = 0x8000_0000; // MSB set: non-zero initial array (as in C)
        rng
    }

    /// Raw `init_genrand(seed)` — the reference MT19937 initialization used by
    /// `init_by_array` internally. Exposed for the canonical mt19937ar vector
    /// test; CPython never seeds this way directly.
    pub fn from_genrand(seed: u32) -> Self {
        Self::init_genrand(seed)
    }

    fn init_genrand(seed: u32) -> Self {
        let mut mt = [0u32; N];
        mt[0] = seed;
        for mti in 1..N {
            mt[mti] = 1812433253u32
                .wrapping_mul(mt[mti - 1] ^ (mt[mti - 1] >> 30))
                .wrapping_add(mti as u32);
        }
        Self { mt, mti: N }
    }

    /// `genrand_uint32` — one tempered draw on [0, 2^32).
    pub fn next_u32(&mut self) -> u32 {
        if self.mti >= N {
            let mt = &mut self.mt;
            for kk in 0..N - M {
                let y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
                mt[kk] = mt[kk + M] ^ (y >> 1) ^ (if y & 1 != 0 { MATRIX_A } else { 0 });
            }
            for kk in N - M..N - 1 {
                let y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
                mt[kk] = mt[kk + M - N] ^ (y >> 1) ^ (if y & 1 != 0 { MATRIX_A } else { 0 });
            }
            let y = (mt[N - 1] & UPPER_MASK) | (mt[0] & LOWER_MASK);
            mt[N - 1] = mt[M - 1] ^ (y >> 1) ^ (if y & 1 != 0 { MATRIX_A } else { 0 });
            self.mti = 0;
        }
        let mut y = self.mt[self.mti];
        self.mti += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^= y >> 18;
        y
    }

    /// `random()` — genrand_res53: `(a*67108864.0 + b) * (1.0/2**53)` with
    /// `a = u32>>5`, `b = u32>>6`. Two tempered words per draw.
    pub fn random(&mut self) -> f64 {
        let a = self.next_u32() >> 5;
        let b = self.next_u32() >> 6;
        (a as f64 * 67108864.0 + b as f64) * (1.0 / 9007199254740992.0)
    }

    /// `getrandbits(k)` — k <= 32: top k bits of one tempered word;
    /// k in (32, 64]: two words, little-endian, partial top word shifted
    /// (`_randommodule.c` `_random_Random_getrandbits_impl`).
    pub fn getrandbits(&mut self, k: u64) -> u64 {
        assert!(k <= 64, "getrandbits: k must be <= 64");
        if k == 0 {
            return 0;
        }
        if k <= 32 {
            return (self.next_u32() >> (32 - k as u32)) as u64;
        }
        let lo = self.next_u32();
        let hi = self.next_u32() >> (32 - (k - 32) as u32);
        ((hi as u64) << 32) | lo as u64
    }

    /// `_randbelow_with_getrandbits(n)`: `k = n.bit_length()`, draw
    /// `getrandbits(k)`, reject `r >= n`. `n` must be positive.
    pub fn randbelow(&mut self, n: u64) -> u64 {
        assert!(n > 0, "randbelow: n must be positive");
        let k = 64 - n.leading_zeros(); // n.bit_length()
        loop {
            let r = self.getrandbits(k as u64);
            if r < n {
                return r;
            }
        }
    }

    /// `randrange(n)` — the single-argument form statistics.py uses
    /// (`randrange(last_entry + 1)`, `_block_bootstrap_indices`): returns
    /// `_randbelow(n)`.
    pub fn randrange(&mut self, n: u64) -> u64 {
        self.randbelow(n)
    }

    /// `sample(range(n), n)` — CPython 3.14 `random.sample` on a range with
    /// k == n. There is NO `k == n` short-circuit in 3.14: the pool branch
    /// (n <= setsize) runs a Fisher-Yates shuffle drawing `randbelow(n-i)`,
    /// the set branch (n > setsize) draws `randbelow(n)` with rejection.
    /// Episodes are small, so the pool branch is the one the oracle hits.
    pub fn sample(&mut self, n: u64) -> Vec<u64> {
        let n = n as usize;
        let k = n;
        let setsize = {
            let mut s = 21usize;
            if k > 5 {
                let exp = ((k as f64 * 3.0).log(4.0)).ceil() as u32;
                s += 4usize.pow(exp);
            }
            s
        };
        let mut result = vec![0u64; k];
        if n <= setsize {
            let mut pool: Vec<u64> = (0..n as u64).collect();
            for i in 0..k {
                let j = self.randbelow((n - i) as u64) as usize;
                result[i] = pool[j];
                pool[j] = pool[n - i - 1]; // move non-selected item into vacancy
            }
        } else {
            let mut selected = Vec::with_capacity(k);
            for i in 0..k {
                loop {
                    let j = self.randbelow(n as u64);
                    if !selected.contains(&j) {
                        selected.push(j);
                        result[i] = j;
                        break;
                    }
                }
            }
        }
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Canonical mt19937ar vector, seeded via init_genrand(5489).
    #[test]
    fn canonical_mt19937_vector() {
        let mut rng = MT19937::from_genrand(5489);
        let draws: Vec<u32> = (0..5).map(|_| rng.next_u32()).collect();
        assert_eq!(draws, vec![3499211612, 581869302, 3890346734, 3586334585, 545404204]);
    }

    /// The task-mandated oracle command, bit-for-bit:
    /// `random.Random(12345)`; `[r.random() for _ in range(5)]`;
    /// `r.randrange(100)`; `r.getrandbits(20)`.
    #[test]
    fn matches_cpython_random_randrange_getrandbits() {
        let mut rng = MT19937::new(12345);
        let xs: Vec<f64> = (0..5).map(|_| rng.random()).collect();
        assert_eq!(
            xs,
            vec![
                0.41661987254534116,
                0.010169169457068361,
                0.8252065092537432,
                0.2986398551995928,
                0.3684116894884757,
            ]
        );
        assert_eq!(rng.randrange(100), 24);
        assert_eq!(rng.getrandbits(20), 283372);
    }

    /// `randrange` sequence matching `_block_bootstrap_indices` draws.
    #[test]
    fn matches_cpython_randrange_sequence() {
        let mut rng = MT19937::new(12345);
        let draws: Vec<u64> = (0..6).map(|_| rng.randrange(50)).collect();
        assert_eq!(draws, vec![26, 46, 0, 19, 23, 12]);
    }

    /// `getrandbits` stream incl. 53-bit (k > 32) multi-word path.
    #[test]
    fn matches_cpython_getrandbits_stream() {
        let mut rng = MT19937::new(12345);
        assert_eq!(rng.getrandbits(32), 1789368711);
        assert_eq!(rng.getrandbits(32), 3146859322);
        assert_eq!(rng.getrandbits(32), 43676229);
        assert_eq!(rng.getrandbits(53), 7432800910637164);
    }

    /// `sample(range(10), 10)` — the WRC permutation draw — consumes RNG
    /// (no `k == n` short-circuit on 3.14); the next `random()` must continue
    /// the same stream.
    #[test]
    fn matches_cpython_sample_range_n() {
        let mut rng = MT19937::new(12345);
        assert_eq!(rng.sample(10), vec![6, 0, 4, 9, 2, 1, 5, 3, 7, 8]);
        assert_eq!(rng.random(), 0.3730638408978796);
    }

    /// Seed 5489 (the canonical MT19937 seed through init_by_array).
    #[test]
    fn matches_cpython_seed_5489() {
        let mut rng = MT19937::new(5489);
        let xs: Vec<f64> = (0..3).map(|_| rng.random()).collect();
        assert_eq!(
            xs,
            vec![0.7876110167997803, 0.0972674640914375, 0.9735995707790809]
        );
        assert_eq!(rng.getrandbits(32), 357906529);
        assert_eq!(rng.getrandbits(32), 1672522146);
        assert_eq!(rng.getrandbits(32), 3646913130);
        assert_eq!(rng.getrandbits(32), 8761624);
    }

    /// Edge-case seeds exercising the multi-word `init_by_array` path.
    #[test]
    fn matches_cpython_edge_seeds() {
        let cases: &[(u64, f64, f64, u32)] = &[
            (0, 0.8444218515250481, 0.7579544029403025, 1806341205),
            (1, 0.13436424411240122, 0.8474337369372327, 3280387012),
            (0xffff_ffff, 0.6353574441341173, 0.20319993954407756, 2608619700),
            (2u64.pow(40) + 5, 0.5043802970418443, 0.2686044399723282, 3976222944),
            (2u64.pow(32), 0.11299430095636409, 0.41782886486292836, 71624475),
            (u64::MAX, 0.021825695401270107, 0.3380953268613758, 910393425),
        ];
        for &(seed, r0, r1, b0) in cases {
            let mut rng = MT19937::new(seed);
            assert_eq!(rng.random(), r0, "seed {seed}");
            assert_eq!(rng.random(), r1, "seed {seed}");
            assert_eq!(rng.getrandbits(32), b0 as u64, "seed {seed}");
        }
    }
}
