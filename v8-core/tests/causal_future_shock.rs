//! Causal Fortress & Future-Shock Prefix Non-Interference Fuzzing Suite (D-139, Rules 44–50, CC-BILL-V8.3-CAUSAL-FORTRESS-006).
//!
//! Enforces:
//! 1. Article 1 & 8: Temporal Non-Interference (X_{\le D} = X'_{\le D} ==> Decision_{\le D}(X) = Decision_{\le D}(X')).
//! 2. Article 3: ChronosGate Monotonic Watermark advancement and isolation.
//! 3. Article 4 & 5: DenseBarSeries & SparseEventSeries typed access.
//! 4. Article 9: 100% kill rate against LEAK-001, LEAK-002, and LEAK-003 mutants.
//! 5. Article 14: TemporalIntegrityCertificate PnL Renderer Gatekeeping.

use v8_core::audit::mutants::{LeakMutantId, MutantAuditor};
use v8_core::data::{SymbolBars, TapeRow};
use v8_core::state::{FeatureStore, state_features};
use v8_core::temporal::{
    BarId, CausalFrame, DecisionTime, DenseBarSeries,
    ExecutionAuthority, SparseEventSeries, TemporalIntegrityCertificate,
};

fn clone_bars(b: &SymbolBars) -> SymbolBars {
    SymbolBars {
        symbol: b.symbol.clone(),
        opens: b.opens.clone(),
        highs: b.highs.clone(),
        lows: b.lows.clone(),
        closes: b.closes.clone(),
        volumes: b.volumes.clone(),
        event_times: b.event_times.clone(),
        available_times: b.available_times.clone(),
        ingested_times: b.ingested_times.clone(),
        venue_sequences: b.venue_sequences.clone(),
        event_ids: b.event_ids.clone(),
        row_indices: b.row_indices.clone(),
    }
}

fn generate_synthetic_dataset(num_bars: usize) -> (SymbolBars, Vec<TapeRow>) {
    let mut opens = Vec::with_capacity(num_bars);
    let mut highs = Vec::with_capacity(num_bars);
    let mut lows = Vec::with_capacity(num_bars);
    let mut closes = Vec::with_capacity(num_bars);
    let mut volumes = Vec::with_capacity(num_bars);
    let mut event_times = Vec::with_capacity(num_bars);
    let mut available_times = Vec::with_capacity(num_bars);
    let mut ingested_times = Vec::with_capacity(num_bars);
    let mut venue_sequences = Vec::with_capacity(num_bars);
    let mut event_ids = Vec::with_capacity(num_bars);
    let mut row_indices = Vec::with_capacity(num_bars);

    let base_time = 1_700_000_000_000_000_000i64;
    let bar_ns = 3_600_000_000_000i64; // 1 hour

    for i in 0..num_bars {
        let t = base_time + (i as i64 * bar_ns);
        let cycle = (i as f64 * 0.1).sin() * 5.0;
        let base_p = 50_000.0 + (i as f64 * 10.0) + cycle;
        let o = base_p;
        let h = base_p + 15.0 + ((i % 7) as f64 * 2.0);
        let l = base_p - 15.0 - ((i % 3) as f64 * 2.0);
        let c = base_p + 2.0 * ((i % 4) as f64 - 1.5);
        let v = 100.0 + ((i % 11) as f64 * 15.0);

        opens.push(o);
        highs.push(h);
        lows.push(l);
        closes.push(c);
        volumes.push(v);
        event_times.push(t);
        available_times.push(t + bar_ns);
        ingested_times.push(t + bar_ns + 500);
        venue_sequences.push(i as i64);
        event_ids.push(format!("bar_{:06}", i));
        row_indices.push(i);
    }

    let bars = SymbolBars {
        symbol: "BTCUSDT".to_string(),
        opens,
        highs,
        lows,
        closes,
        volumes,
        event_times,
        available_times,
        ingested_times,
        venue_sequences,
        event_ids,
        row_indices,
    };

    // 8-hour funding events
    let mut rows = Vec::new();
    let funding_ns = 8 * bar_ns;
    let n_funding = (num_bars * bar_ns as usize) / funding_ns as usize + 2;
    for k in 0..n_funding {
        let t = base_time + (k as i64 * funding_ns);
        rows.push(TapeRow {
            source: "synthetic".to_string(),
            channel: "funding".to_string(),
            instrument: "BTCUSDT".to_string(),
            event_time: t,
            available_time: t,
            ingested_time: t,
            venue_sequence: k as i64,
            event_id: format!("fund_{:04}", k),
            payload: serde_json::json!({
                "funding_rate": 0.0001 * if k % 2 == 0 { 1.0 } else { -1.0 }
            }),
            nonfinite: Vec::new(),
        });
    }

    (bars, rows)
}

#[test]
fn test_d139_future_shock_prefix_non_interference_fuzzing() {
    let total_bars = 120;
    let (base_bars, rows) = generate_synthetic_dataset(total_bars);
    let base_store = FeatureStore::build(&base_bars, &rows);

    let cutoffs = [15, 30, 45, 60, 90];

    for &d in &cutoffs {
        // Collect baseline causal frames and state features up to cutoff d
        let base_frames: Vec<CausalFrame> = (0..=d).map(|i| base_store.causal_frame(i)).collect();
        let base_state_feats: Vec<_> = (1..=d)
            .map(|t| state_features(&base_store, t, base_store.avail[t - 1], 32))
            .collect();

        // Shock 1: Future Truncation (only bars 0..=d exist)
        {
            let trunc_bars = SymbolBars {
                symbol: base_bars.symbol.clone(),
                opens: base_bars.opens[..=d].to_vec(),
                highs: base_bars.highs[..=d].to_vec(),
                lows: base_bars.lows[..=d].to_vec(),
                closes: base_bars.closes[..=d].to_vec(),
                volumes: base_bars.volumes[..=d].to_vec(),
                event_times: base_bars.event_times[..=d].to_vec(),
                available_times: base_bars.available_times[..=d].to_vec(),
                ingested_times: base_bars.ingested_times[..=d].to_vec(),
                venue_sequences: base_bars.venue_sequences[..=d].to_vec(),
                event_ids: base_bars.event_ids[..=d].to_vec(),
                row_indices: base_bars.row_indices[..=d].to_vec(),
            };
            let trunc_store = FeatureStore::build(&trunc_bars, &rows);
            let trunc_frames: Vec<CausalFrame> = (0..=d).map(|i| trunc_store.causal_frame(i)).collect();
            assert_eq!(
                base_frames, trunc_frames,
                "Prefix Non-Interference failed under future truncation at cutoff {}",
                d
            );

            let trunc_state_feats: Vec<_> = (1..=d)
                .map(|t| state_features(&trunc_store, t, trunc_store.avail[t - 1], 32))
                .collect();
            assert_eq!(
                base_state_feats, trunc_state_feats,
                "StateFeatures Non-Interference failed under future truncation at cutoff {}",
                d
            );
        }

        // Shock 2: Extreme Price Explosion (10x price shock for t > d)
        {
            let mut shock_bars = clone_bars(&base_bars);
            for i in (d + 1)..total_bars {
                shock_bars.opens[i] *= 10.0;
                shock_bars.highs[i] *= 15.0;
                shock_bars.lows[i] *= 8.0;
                shock_bars.closes[i] *= 12.0;
                shock_bars.volumes[i] *= 100.0;
            }
            let shock_store = FeatureStore::build(&shock_bars, &rows);
            let shock_frames: Vec<CausalFrame> = (0..=d).map(|i| shock_store.causal_frame(i)).collect();
            assert_eq!(
                base_frames, shock_frames,
                "Prefix Non-Interference failed under 10x future explosion at cutoff {}",
                d
            );
        }

        // Shock 3: Extreme Price Collapse (0.01x crash for t > d)
        {
            let mut crash_bars = clone_bars(&base_bars);
            for i in (d + 1)..total_bars {
                crash_bars.opens[i] = (crash_bars.opens[i] * 0.01).max(0.1);
                crash_bars.highs[i] = (crash_bars.highs[i] * 0.02).max(0.2);
                crash_bars.lows[i] = (crash_bars.lows[i] * 0.005).max(0.05);
                crash_bars.closes[i] = (crash_bars.closes[i] * 0.01).max(0.1);
                crash_bars.volumes[i] = 1.0;
            }
            let crash_store = FeatureStore::build(&crash_bars, &rows);
            let crash_frames: Vec<CausalFrame> = (0..=d).map(|i| crash_store.causal_frame(i)).collect();
            assert_eq!(
                base_frames, crash_frames,
                "Prefix Non-Interference failed under 0.01x future crash at cutoff {}",
                d
            );
        }
    }
}

#[test]
fn test_d139_leak_mutant_100pct_kill_rate() {
    let (bars, rows) = generate_synthetic_dataset(120);
    let store = FeatureStore::build(&bars, &rows);

    let res_1 = MutantAuditor::verify_leak_001_killed(&store);
    assert!(
        res_1.killed,
        "LEAK-001 (ATR+13 lookahead mutant) MUST be killed! Details: {}",
        res_1.detection_reason
    );
    assert_eq!(res_1.mutant_id, LeakMutantId::Leak001AtrLookaheadOffset);

    let res_2 = MutantAuditor::verify_leak_002_killed(&store);
    assert!(
        res_2.killed,
        "LEAK-002 (ADX+27 lookahead mutant) MUST be killed! Details: {}",
        res_2.detection_reason
    );
    assert_eq!(res_2.mutant_id, LeakMutantId::Leak002AdxLookaheadOffset);

    let res_3 = MutantAuditor::verify_leak_003_killed(&store);
    assert!(
        res_3.killed,
        "LEAK-003 (Funding sparse misindex mutant) MUST be killed! Details: {}",
        res_3.detection_reason
    );
    assert_eq!(res_3.mutant_id, LeakMutantId::Leak003FundingSparseMisindex);
}

#[test]
fn test_d139_chronos_gate_data_diode_stream() {
    let (bars, rows) = generate_synthetic_dataset(50);
    let store = FeatureStore::build(&bars, &rows);

    let mut gate = store.chronos_gate();
    let mut count = 0;
    let mut prev_dt = i64::MIN;

    while let Some(frame) = gate.release_next() {
        assert!(
            frame.decision_time.0 >= prev_dt,
            "ChronosGate monotonicity violation: {} < {}",
            frame.decision_time.0,
            prev_dt
        );
        assert_eq!(frame.bar_id, BarId(count as u32));
        prev_dt = frame.decision_time.0;
        count += 1;
    }

    assert_eq!(count, 50);
    assert_eq!(gate.bars_released(), 50);
    assert_eq!(gate.watermark(), DecisionTime(store.avail[49]));
}

#[test]
fn test_d139_dense_and_sparse_series_algebra() {
    let raw_atr = vec![2.0, 2.5, 3.0];
    let dense = DenseBarSeries::from_offset_slice(6, 3, &raw_atr);

    assert_eq!(dense.len(), 6);
    assert_eq!(dense.at(BarId(0)), None);
    assert_eq!(dense.at(BarId(1)), None);
    assert_eq!(dense.at(BarId(2)), None);
    assert_eq!(dense.at(BarId(3)), Some(2.0));
    assert_eq!(dense.at(BarId(4)), Some(2.5));
    assert_eq!(dense.at(BarId(5)), Some(3.0));
    assert_eq!(dense.at(BarId(6)), None);

    let times = vec![1_000, 2_000, 3_000];
    let values = vec![0.0001, 0.0002, 0.0003];
    let sparse = SparseEventSeries::from_pairs(&times, &values);

    assert_eq!(sparse.as_of(DecisionTime(500)), None);
    assert_eq!(sparse.as_of(DecisionTime(1_000)), Some(&0.0001));
    assert_eq!(sparse.as_of(DecisionTime(1_999)), Some(&0.0001));
    assert_eq!(sparse.as_of(DecisionTime(2_000)), Some(&0.0002));
    assert_eq!(sparse.as_of(DecisionTime(5_000)), Some(&0.0003));
}

#[test]
fn test_d139_temporal_integrity_certificate_authority() {
    let cert_cert = TemporalIntegrityCertificate::generate(
        ExecutionAuthority::CertifiedSim,
        DecisionTime(1_700_000_000_000),
        100,
        "1122334455667788".to_string(),
    );
    assert!(cert_cert.is_authoritative());

    let cert_fast = TemporalIntegrityCertificate::generate(
        ExecutionAuthority::FastResearch,
        DecisionTime(1_700_000_000_000),
        100,
        "1122334455667788".to_string(),
    );
    assert!(!cert_fast.is_authoritative());
}
