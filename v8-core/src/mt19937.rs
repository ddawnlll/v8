//! S7 bit-exact MT19937 RNG parity (issue #127). CPython's stdlib `random`
//! is Mersenne Twister 19937; `random()` draws genrand_res53 (NOT
//! getrandbits(53)/2**53). Unit tests must match CPython 3.14 sequences.
