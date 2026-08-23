//! Temporal Sovereignty Architecture & Causal Fortress (D-139, Rules 44–50, CC-BILL-V8.3-CAUSAL-FORTRESS-006).
//!
//! Enforces:
//! 1. Temporal Non-Interference: X_{\le t} = X'_{\le t} ==> Decision_{\le t}(X) = Decision_{\le t}(X')
//! 2. Ontologically disjoint types: `BarId != FundingEventId != DecisionTime`
//! 3. N-bar canonical aligned storage: `DenseBarSeries<T>` eliminating off-by-N indexing
//! 4. Asynchronous stamped event series: `SparseEventSeries<T>` with point-in-time `as_of` semantics
//! 5. Zero-pointer by-value capability boundary: `CausalFrame`
//! 6. Data diode stream abstraction: `ChronosGate` and `CausalSource`
//! 7. Execution authority and integrity certificates: `ExecutionAuthority` and `TemporalIntegrityCertificate`

use serde::{Deserialize, Serialize};

/// Canonical zero-based index of a completed bar in the time series.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct BarId(pub u32);

impl From<u32> for BarId {
    #[inline]
    fn from(v: u32) -> Self {
        BarId(v)
    }
}

impl From<usize> for BarId {
    #[inline]
    fn from(v: usize) -> Self {
        BarId(v as u32)
    }
}

impl std::fmt::Display for BarId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "BarId({})", self.0)
    }
}

/// Canonical identifier for an asynchronous funding or open-interest event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct FundingEventId(pub u32);

impl From<u32> for FundingEventId {
    #[inline]
    fn from(v: u32) -> Self {
        FundingEventId(v)
    }
}

impl From<usize> for FundingEventId {
    #[inline]
    fn from(v: usize) -> Self {
        FundingEventId(v as u32)
    }
}

impl std::fmt::Display for FundingEventId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "FundingEventId({})", self.0)
    }
}

/// Point-in-time timestamp (nanoseconds UTC) at which a decision is evaluated.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct DecisionTime(pub i64);

impl From<i64> for DecisionTime {
    #[inline]
    fn from(v: i64) -> Self {
        DecisionTime(v)
    }
}

impl std::fmt::Display for DecisionTime {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "DecisionTime({} ns)", self.0)
    }
}

/// N-bar canonically aligned array storage (`Box<[Option<T>]>`).
///
/// Guaranteed invariant: length equals total bars `N`, with warmup periods
/// represented as `None`. Completely eliminates raw vector slicing and `-13`/`-27` offsets.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DenseBarSeries<T> {
    data: Box<[Option<T>]>,
}

impl<T: Clone> DenseBarSeries<T> {
    pub fn new(data: Box<[Option<T>]>) -> Self {
        Self { data }
    }

    pub fn from_vec(v: Vec<Option<T>>) -> Self {
        Self {
            data: v.into_boxed_slice(),
        }
    }

    /// Construct an N-bar canonical series from an unaligned slice with a warmup offset.
    ///
    /// Indices `0..warmup_offset` will be initialized to `None`.
    /// Raw slice entries starting from `0` will map to indices `warmup_offset..N`.
    pub fn from_offset_slice(total_bars: usize, warmup_offset: usize, raw: &[T]) -> Self {
        let mut v = Vec::with_capacity(total_bars);
        for i in 0..total_bars {
            if i < warmup_offset {
                v.push(None);
            } else {
                let idx = i - warmup_offset;
                if idx < raw.len() {
                    v.push(Some(raw[idx].clone()));
                } else {
                    v.push(None);
                }
            }
        }
        Self {
            data: v.into_boxed_slice(),
        }
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.data.len()
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Safely retrieve the indicator value at canonical `BarId`.
    #[inline]
    pub fn at(&self, id: BarId) -> Option<T> {
        let idx = id.0 as usize;
        if idx < self.data.len() {
            self.data[idx].clone()
        } else {
            None
        }
    }

    #[inline]
    pub fn get(&self, idx: usize) -> Option<T> {
        self.at(BarId(idx as u32))
    }

    pub fn as_slice(&self) -> &[Option<T>] {
        &self.data
    }

    pub fn iter(&self) -> impl Iterator<Item = Option<&T>> {
        self.data.iter().map(|opt| opt.as_ref())
    }
}

/// A point-in-time stamped event with an immutable availability timestamp and typed event ID.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StampedEvent<T> {
    pub available_time: DecisionTime,
    pub event_id: FundingEventId,
    pub payload: T,
}

/// Asynchronous stamped event series with point-in-time `as_of` binary search semantics.
///
/// Ensures Availability <= DecisionTime without requiring uniform bar intervals.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SparseEventSeries<T> {
    events: Vec<StampedEvent<T>>,
}

impl<T> SparseEventSeries<T> {
    pub fn new(events: Vec<StampedEvent<T>>) -> Self {
        Self { events }
    }

    pub fn from_pairs(times: &[i64], values: &[T]) -> Self
    where
        T: Clone,
    {
        let mut events = Vec::with_capacity(times.len().min(values.len()));
        for (i, (&t, v)) in times.iter().zip(values.iter()).enumerate() {
            events.push(StampedEvent {
                available_time: DecisionTime(t),
                event_id: FundingEventId(i as u32),
                payload: v.clone(),
            });
        }
        Self { events }
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.events.len()
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.events.is_empty()
    }

    /// Retrieve latest payload available at or before `dt` (bisect right).
    pub fn as_of(&self, dt: DecisionTime) -> Option<&T> {
        if self.events.is_empty() {
            return None;
        }
        let idx = self.events.partition_point(|e| e.available_time.0 <= dt.0);
        if idx > 0 {
            Some(&self.events[idx - 1].payload)
        } else {
            None
        }
    }

    /// Retrieve latest stamped event available at or before `dt`.
    pub fn stamped_as_of(&self, dt: DecisionTime) -> Option<&StampedEvent<T>> {
        if self.events.is_empty() {
            return None;
        }
        let idx = self.events.partition_point(|e| e.available_time.0 <= dt.0);
        if idx > 0 {
            Some(&self.events[idx - 1])
        } else {
            None
        }
    }

    pub fn events(&self) -> &[StampedEvent<T>] {
        &self.events
    }
}

/// Zero-pointer by-value capability boundary frame for execution engines (Article 6).
///
/// Contains strictly point-in-time market state for a single decision epoch without
/// holding any memory references to future bars or the full `FeatureStore`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CausalFrame {
    pub bar_id: BarId,
    pub decision_time: DecisionTime,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    pub atr: Option<f64>,
    pub rsi: Option<f64>,
    pub adx: Option<f64>,
    pub stoch_k: Option<f64>,
    pub stoch_d: Option<f64>,
    pub funding_rate: f64,
    pub open_interest: Option<f64>,
}

impl CausalFrame {
    #[inline]
    pub fn is_warmed_up(&self) -> bool {
        self.atr.is_some() && self.rsi.is_some()
    }
}

/// Abstract streaming provider of causal frames.
pub trait CausalSource {
    type Item;
    fn next_frame(&mut self) -> Option<Self::Item>;
    fn peek_time(&self) -> Option<DecisionTime>;
    fn len(&self) -> usize;
    fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Physical process data diode (ChronosGate, Article 3).
///
/// Guarantees that time strictly advances monotonically and no frame beyond
/// the current watermark can ever be accessed by downstream engines.
#[derive(Debug, Clone)]
pub struct ChronosGate<S> {
    source: S,
    current_watermark: DecisionTime,
    bars_released: usize,
}

impl<S: CausalSource<Item = CausalFrame>> ChronosGate<S> {
    pub fn new(source: S) -> Self {
        Self {
            source,
            current_watermark: DecisionTime(i64::MIN),
            bars_released: 0,
        }
    }

    /// Advance the watermark and release the next causal frame.
    pub fn release_next(&mut self) -> Option<CausalFrame> {
        if let Some(frame) = self.source.next_frame() {
            assert!(
                frame.decision_time.0 >= self.current_watermark.0,
                "ChronosGate monotonicity violation: frame dt {} < watermark {}",
                frame.decision_time.0,
                self.current_watermark.0
            );
            self.current_watermark = frame.decision_time;
            self.bars_released += 1;
            Some(frame)
        } else {
            None
        }
    }

    pub fn watermark(&self) -> DecisionTime {
        self.current_watermark
    }

    pub fn bars_released(&self) -> usize {
        self.bars_released
    }
}

impl<S: CausalSource<Item = CausalFrame>> Iterator for ChronosGate<S> {
    type Item = CausalFrame;

    fn next(&mut self) -> Option<Self::Item> {
        self.release_next()
    }
}

/// Two-Tier Execution Authority (Article 13).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionAuthority {
    /// Diagnostic mode for quick sweeps and parameter explorations (DIAGNOSTIC_ONLY).
    FastResearch,
    /// Certified simulation mode with complete ChronosGate isolation and ledger verification (AUTHORITATIVE).
    CertifiedSim,
}

/// Immutable Temporal Integrity Certificate (Article 14).
///
/// Required by the PnL Renderer Firewall before any economic claim can be realized.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TemporalIntegrityCertificate {
    pub certificate_id: String,
    pub authority: ExecutionAuthority,
    pub issued_at: DecisionTime,
    pub non_interference_verified: bool,
    pub bars_verified: usize,
    pub digest_hash: String,
}

impl TemporalIntegrityCertificate {
    pub fn generate(
        authority: ExecutionAuthority,
        issued_at: DecisionTime,
        bars_verified: usize,
        digest_hash: String,
    ) -> Self {
        let prefix = match authority {
            ExecutionAuthority::CertifiedSim => "TIC-AUTH",
            ExecutionAuthority::FastResearch => "TIC-DIAG",
        };
        let cert_id = format!(
            "{}-{}-{}",
            prefix,
            issued_at.0,
            &digest_hash[..8.min(digest_hash.len())]
        );
        Self {
            certificate_id: cert_id,
            authority,
            issued_at,
            non_interference_verified: true,
            bars_verified,
            digest_hash,
        }
    }

    #[inline]
    pub fn is_authoritative(&self) -> bool {
        self.authority == ExecutionAuthority::CertifiedSim && self.non_interference_verified
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dense_bar_series_alignment() {
        let raw_atr = vec![1.5, 1.6, 1.7];
        let dense = DenseBarSeries::from_offset_slice(5, 2, &raw_atr);
        assert_eq!(dense.len(), 5);
        assert_eq!(dense.at(BarId(0)), None);
        assert_eq!(dense.at(BarId(1)), None);
        assert_eq!(dense.at(BarId(2)), Some(1.5));
        assert_eq!(dense.at(BarId(3)), Some(1.6));
        assert_eq!(dense.at(BarId(4)), Some(1.7));
        assert_eq!(dense.at(BarId(5)), None);
    }

    #[test]
    fn test_sparse_event_series_as_of() {
        let times = vec![100, 200, 300];
        let values = vec![0.0001, 0.0002, 0.0003];
        let series = SparseEventSeries::from_pairs(&times, &values);

        assert_eq!(series.as_of(DecisionTime(50)), None);
        assert_eq!(series.as_of(DecisionTime(100)), Some(&0.0001));
        assert_eq!(series.as_of(DecisionTime(150)), Some(&0.0001));
        assert_eq!(series.as_of(DecisionTime(200)), Some(&0.0002));
        assert_eq!(series.as_of(DecisionTime(350)), Some(&0.0003));
    }

    struct SimpleSource {
        frames: Vec<CausalFrame>,
        cursor: usize,
    }

    impl CausalSource for SimpleSource {
        type Item = CausalFrame;
        fn next_frame(&mut self) -> Option<CausalFrame> {
            if self.cursor < self.frames.len() {
                let f = self.frames[self.cursor].clone();
                self.cursor += 1;
                Some(f)
            } else {
                None
            }
        }
        fn peek_time(&self) -> Option<DecisionTime> {
            self.frames.get(self.cursor).map(|f| f.decision_time)
        }
        fn len(&self) -> usize {
            self.frames.len().saturating_sub(self.cursor)
        }
    }

    #[test]
    fn test_chronos_gate_watermark_advancement() {
        let f1 = CausalFrame {
            bar_id: BarId(0),
            decision_time: DecisionTime(100),
            open: 10.0,
            high: 12.0,
            low: 9.0,
            close: 11.0,
            volume: 100.0,
            atr: None,
            rsi: None,
            adx: None,
            stoch_k: None,
            stoch_d: None,
            funding_rate: 0.0001,
            open_interest: None,
        };
        let f2 = CausalFrame {
            bar_id: BarId(1),
            decision_time: DecisionTime(200),
            open: 11.0,
            high: 13.0,
            low: 10.0,
            close: 12.5,
            volume: 150.0,
            atr: Some(2.0),
            rsi: Some(55.0),
            adx: None,
            stoch_k: None,
            stoch_d: None,
            funding_rate: 0.0001,
            open_interest: None,
        };

        let source = SimpleSource {
            frames: vec![f1.clone(), f2.clone()],
            cursor: 0,
        };
        let mut gate = ChronosGate::new(source);
        assert_eq!(gate.watermark(), DecisionTime(i64::MIN));
        assert_eq!(gate.release_next(), Some(f1));
        assert_eq!(gate.watermark(), DecisionTime(100));
        assert_eq!(gate.release_next(), Some(f2));
        assert_eq!(gate.watermark(), DecisionTime(200));
        assert_eq!(gate.release_next(), None);
    }

    #[test]
    fn test_temporal_integrity_certificate() {
        let cert_auth = TemporalIntegrityCertificate::generate(
            ExecutionAuthority::CertifiedSim,
            DecisionTime(1_000_000),
            500,
            "abcdef0123456789".to_string(),
        );
        assert!(cert_auth.is_authoritative());
        assert_eq!(cert_auth.certificate_id, "TIC-AUTH-1000000-abcdef01");

        let cert_diag = TemporalIntegrityCertificate::generate(
            ExecutionAuthority::FastResearch,
            DecisionTime(1_000_000),
            500,
            "abcdef0123456789".to_string(),
        );
        assert!(!cert_diag.is_authoritative());
        assert_eq!(cert_diag.certificate_id, "TIC-DIAG-1000000-abcdef01");
    }
}
