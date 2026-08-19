//! Rust-Native Factorial Exit Policy Ablation and Counterfactual Replay Harness (D-106).
//!
//! Authoritative pure-Rust execution of counterfactual exit hypotheses over
//! unique candidate episodes using the byte-exact `ScalarKernel` (Backend-0).

use std::collections::{BTreeMap, HashMap};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

use serde_json::{json, Value};

use crate::backend::scalar::ScalarKernel;
use crate::data;
use crate::runloop;
use crate::simulator::{Draft, FillPolicy, SimulatorParams};
use crate::state;

pub struct AblationConfig {
    pub name: &'static str,
    pub desc: &'static str,
    pub stop_r: Option<f64>,
    pub target_r: Option<f64>,
    pub breakeven_at_mfe: Option<f64>,
    pub breakeven_margin: Option<f64>,
    pub trail_stop_atr: Option<f64>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct PolicyStats {
    pub name: String,
    pub description: String,
    pub n_episodes: usize,
    pub win_rate_pct: f64,
    pub avg_net_r: f64,
    pub total_net_r: f64,
    pub profit_factor: f64,
    pub delta_net_r: f64,
    pub is_net_r: f64,
    pub oos_net_r: f64,
    pub is_win_rate: f64,
    pub oos_win_rate: f64,
}

pub fn run(args: &[String]) -> i32 {
    let audit_dir = if args.is_empty() {
        Path::new(".audit/rust_audit_current")
    } else {
        Path::new(&args[0])
    };

    let tape_path = std::path::PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl");
    let cands_path = audit_dir.join("candidates.jsonl");

    if !tape_path.exists() || !cands_path.exists() {
        eprintln!("exit-ablation: missing required artifacts at {:?} / {:?}", tape_path, cands_path);
        return 1;
    }

    println!("======================================================================");
    println!("V8.2 PURE RUST FACTORIAL EXIT POLICY ABLATION & COUNTERFACTUAL ORACLE");
    println!("======================================================================");
    println!("Ingesting tape: {:?} ...", tape_path);

    let rows = match runloop::read_tape(&tape_path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("failed to read tape: {e}");
            return 1;
        }
    };

    let ds = match data::Dataset::from_rows(rows) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("failed to build dataset: {e}");
            return 1;
        }
    };

    let stores = state::build_stores(&ds);
    let sym_store = match stores.iter().find(|s| s.symbol == "BTCUSDT") {
        Some(s) => s,
        None => {
            eprintln!("no FeatureStore for BTCUSDT");
            return 1;
        }
    };
    let sym_bars = match ds.bars.iter().find(|b| b.symbol == "BTCUSDT") {
        Some(b) => b,
        None => {
            eprintln!("no SymbolBars for BTCUSDT");
            return 1;
        }
    };

    let sim = SimulatorParams {
        round_trip_cost_r: 0.07,
        round_trip_cost_bps: None,
        funding_rate_r: 0.0,
        funding_hours: 8,
        fill_policy: FillPolicy::BarClose,
    };

    let mut funding_schedule: Vec<(i64, f64)> = ds
        .rows
        .iter()
        .filter(|r| r.channel == "funding")
        .map(|r| {
            (
                r.event_time,
                r.payload.get("funding_rate").and_then(Value::as_f64).unwrap_or(0.0),
            )
        })
        .collect();
    funding_schedule.sort_by_key(|(t, _)| *t);

    println!("Building Candidate Snapshot cache from {:?} ...", cands_path);
    let cands_file = match File::open(&cands_path) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("failed to open candidates.jsonl: {e}");
            return 1;
        }
    };

    let mut cand_by_id: HashMap<String, Value> = HashMap::new();
    let mut admitted_cids: Vec<String> = Vec::new();

    for line in BufReader::new(cands_file).lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        if line.trim().is_empty() {
            continue;
        }
        let v: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let to_state = v.get("to_state").and_then(Value::as_str).unwrap_or("");
        let cid = v.get("candidate_id").and_then(Value::as_str).unwrap_or("").to_string();
        if cid.is_empty() {
            continue;
        }
        if to_state == "DETECTED" {
            cand_by_id.insert(cid.clone(), v);
        } else if to_state == "PENDING" {
            admitted_cids.push(cid);
        }
    }

    let n_unique = admitted_cids.len();
    println!("Loaded {} unique admitted candidate episodes.", n_unique);

    let policies = vec![
        AblationConfig {
            name: "M0_FROZEN_BASELINE",
            desc: "Declared frozen geometry (1R SL / 1.5R TP / 8-bar horizon)",
            stop_r: None,
            target_r: None,
            breakeven_at_mfe: None,
            breakeven_margin: None,
            trail_stop_atr: None,
        },
        AblationConfig {
            name: "M1_WIDER_SL_ONLY",
            desc: "Wider Initial Stop only (1.5x ATR)",
            stop_r: Some(1.5),
            target_r: None,
            breakeven_at_mfe: None,
            breakeven_margin: None,
            trail_stop_atr: None,
        },
        AblationConfig {
            name: "M2_NO_HARD_TP_ONLY",
            desc: "No Hard TP (Target -> 999.0R)",
            stop_r: None,
            target_r: Some(999.0),
            breakeven_at_mfe: None,
            breakeven_margin: None,
            trail_stop_atr: None,
        },
        AblationConfig {
            name: "M3_BREAKEVEN_ONLY",
            desc: "Breakeven Roll at +0.8R MFE",
            stop_r: None,
            target_r: None,
            breakeven_at_mfe: Some(0.8),
            breakeven_margin: Some(0.07),
            trail_stop_atr: None,
        },
        AblationConfig {
            name: "M4_PROFIT_LOCK_ONLY",
            desc: "Profit Lock at +0.8R MFE to +0.20R margin",
            stop_r: None,
            target_r: None,
            breakeven_at_mfe: Some(0.8),
            breakeven_margin: Some(0.20),
            trail_stop_atr: None,
        },
        AblationConfig {
            name: "M5_ATR_TRAIL_ONLY",
            desc: "1.2x ATR Trailing Stop only",
            stop_r: None,
            target_r: None,
            breakeven_at_mfe: None,
            breakeven_margin: None,
            trail_stop_atr: Some(1.2),
        },
        AblationConfig {
            name: "M6_WIDER_SL_PLUS_TRAIL",
            desc: "Interaction: 1.5x SL + 1.2x ATR Trail",
            stop_r: Some(1.5),
            target_r: None,
            breakeven_at_mfe: None,
            breakeven_margin: None,
            trail_stop_atr: Some(1.2),
        },
        AblationConfig {
            name: "M7_WIDER_SL_NO_TP_TRAIL",
            desc: "Interaction: 1.5x SL + No TP + 1.2x ATR Trail",
            stop_r: Some(1.5),
            target_r: Some(999.0),
            breakeven_at_mfe: None,
            breakeven_margin: None,
            trail_stop_atr: Some(1.2),
        },
        AblationConfig {
            name: "M8_FULL_DYNAMIC_ASYMMETRIC",
            desc: "Full Package: 1.5x SL + No TP + 0.8R Profit Lock + 1.2x Trail",
            stop_r: Some(1.5),
            target_r: Some(999.0),
            breakeven_at_mfe: Some(0.8),
            breakeven_margin: Some(0.20),
            trail_stop_atr: Some(1.2),
        },
    ];

    let kernel = ScalarKernel {
        round_trip_cost_r: sim.round_trip_cost_r,
        funding_rate_r: sim.funding_rate_r,
        funding_hours: sim.funding_hours,
        fill_policy: sim.fill_policy,
        funding_schedule: &funding_schedule,
        round_trip_cost_bps: sim.round_trip_cost_bps,
        bars: sym_bars,
        store: sym_store,
    };

    let total_bars = sym_bars.highs.len();
    let split_bar = total_bars / 2;

    let mut baseline_total_net_r = 0.0;
    let mut policy_stats_list: Vec<PolicyStats> = Vec::new();
    let mut expert_scores: BTreeMap<String, (f64, f64, usize)> = BTreeMap::new();

    for (p_idx, p) in policies.iter().enumerate() {
        let mut net_rs: Vec<f64> = Vec::with_capacity(n_unique);
        let mut is_net_rs: Vec<f64> = Vec::new();
        let mut oos_net_rs: Vec<f64> = Vec::new();

        for cid in &admitted_cids {
            let snap = match cand_by_id.get(cid) {
                Some(s) => s,
                None => continue,
            };

            let direction = snap.get("direction").and_then(Value::as_str).unwrap_or("LONG").to_string();
            let entry_bar = snap.get("entry_bar").and_then(Value::as_i64).unwrap_or(0) as usize;
            let expert_id = snap.get("expert_id").and_then(Value::as_str).unwrap_or("generic").to_string();

            let mut geom = snap.get("risk_geometry").and_then(Value::as_object).cloned().unwrap_or_default();

            if let Some(sr) = p.stop_r {
                geom.insert("stop_r".to_string(), json!(sr));
            }
            if let Some(tr) = p.target_r {
                geom.insert("target_r".to_string(), json!(tr));
            }
            if let Some(be) = p.breakeven_at_mfe {
                geom.insert("breakeven_roll_at_mfe_r".to_string(), json!(be));
            }
            if let Some(bm) = p.breakeven_margin {
                geom.insert("breakeven_margin_r".to_string(), json!(bm));
            }
            if let Some(tr_atr) = p.trail_stop_atr {
                geom.insert("trail_stop_atr".to_string(), json!(tr_atr));
            }

            let draft = Draft {
                direction,
                birth_time: snap.get("birth_time").and_then(Value::as_i64).unwrap_or(0),
                risk_geometry: geom,
            };

            let outcome = match kernel.run(&draft, entry_bar, total_bars, None) {
                Ok(out) => out,
                Err(_) => continue,
            };

            net_rs.push(outcome.net_r);

            if entry_bar < split_bar {
                is_net_rs.push(outcome.net_r);
            } else {
                oos_net_rs.push(outcome.net_r);
            }

            if p_idx == 0 {
                let e = expert_scores.entry(expert_id.clone()).or_insert((0.0, 0.0, 0));
                e.0 += outcome.net_r;
                e.2 += 1;
            } else if p.name == "M8_FULL_DYNAMIC_ASYMMETRIC" {
                let e = expert_scores.entry(expert_id.clone()).or_insert((0.0, 0.0, 0));
                e.1 += outcome.net_r;
            }
        }

        let n = net_rs.len();
        let tot_r: f64 = net_rs.iter().sum();
        let avg_r = if n > 0 { tot_r / n as f64 } else { 0.0 };
        let wins = net_rs.iter().filter(|r| **r > 0.0).count();
        let win_rate = if n > 0 { (wins as f64 / n as f64) * 100.0 } else { 0.0 };

        let gains: f64 = net_rs.iter().filter(|r| **r > 0.0).sum();
        let losses: f64 = net_rs.iter().filter(|r| **r < 0.0).map(|r| r.abs()).sum();
        let pf = if losses > 0.0 { gains / losses } else { 99.0 };

        if p_idx == 0 {
            baseline_total_net_r = tot_r;
        }
        let delta_net_r = tot_r - baseline_total_net_r;

        let is_tot: f64 = is_net_rs.iter().sum();
        let oos_tot: f64 = oos_net_rs.iter().sum();
        let is_wr = if !is_net_rs.is_empty() {
            (is_net_rs.iter().filter(|r| **r > 0.0).count() as f64 / is_net_rs.len() as f64) * 100.0
        } else {
            0.0
        };
        let oos_wr = if !oos_net_rs.is_empty() {
            (oos_net_rs.iter().filter(|r| **r > 0.0).count() as f64 / oos_net_rs.len() as f64) * 100.0
        } else {
            0.0
        };

        policy_stats_list.push(PolicyStats {
            name: p.name.to_string(),
            description: p.desc.to_string(),
            n_episodes: n,
            win_rate_pct: win_rate,
            avg_net_r: avg_r,
            total_net_r: tot_r,
            profit_factor: pf,
            delta_net_r,
            is_net_r: is_tot,
            oos_net_r: oos_tot,
            is_win_rate: is_wr,
            oos_win_rate: oos_wr,
        });
    }

    println!();
    println!("{:<28} | {:>5} | {:>8} | {:>8} | {:>10} | {:>6} | {:>10} | {:>9} | {:>9}",
        "Policy Model (Rust Backend-0)", "N", "AvgNetR", "WinRate", "TotalNetR", "PF", "DeltaNetR", "IS NetR", "OOS NetR"
    );
    println!("{}", "-".repeat(112));

    for st in &policy_stats_list {
        println!("{:<28} | {:>5} | {:>7.4}R | {:>7.1}% | {:>9.2}R | {:>6.2} | {:>+9.2}R | {:>+8.1}R | {:>+8.1}R",
            st.name, st.n_episodes, st.avg_net_r, st.win_rate_pct, st.total_net_r, st.profit_factor, st.delta_net_r, st.is_net_r, st.oos_net_r
        );
    }

    println!();
    println!("======================================================================");
    println!("EXPERT FAMILY FACTORIAL DECOMPOSITION (PURE RUST AUTHORITATIVE REPLAY)");
    println!("======================================================================");
    println!("{:<28} | {:>5} | {:>9} -> {:>9} | {:>10}",
        "Expert Strategy Family", "N", "M0 NetR", "M8 NetR", "NetR Lift"
    );
    println!("{}", "-".repeat(68));

    for (eid, (m0, m8, n)) in &expert_scores {
        let lift = m8 - m0;
        println!("{:<28} | {:>5} | {:>8.2}R -> {:>8.2}R | {:>+9.2}R",
            eid, n, m0, m8, lift
        );
    }

    let receipt_path = audit_dir.join("exit_ablation_receipt.json");
    let receipt = json!({
        "runtime": "rust_release_v8_core",
        "kernel": "backend::scalar::ScalarKernel",
        "tape": tape_path.to_string_lossy(),
        "n_unique_episodes": n_unique,
        "policies": policy_stats_list,
        "expert_breakdown": expert_scores,
    });

    if let Ok(mut f) = File::create(&receipt_path) {
        use std::io::Write;
        let _ = f.write_all(serde_json::to_string_pretty(&receipt).unwrap_or_default().as_bytes());
        println!("\nDurable receipt written to {:?}", receipt_path);
    }

    0
}
