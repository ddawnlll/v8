//! D-145 economic Kaizen iteration ledger.
//!
//! This runner evaluates only real tape data through the canonical Rust USD-M
//! simulator. It never fabricates market rows or inserts expected metrics.
//! An iteration counts as accepted only when it strictly improves realized
//! net cashflow while staying inside the baseline drawdown and margin safety
//! ceilings. Fee drag is recorded and remains part of realized net cashflow.

use crate::hash::hash_value_blake3;
use crate::kaizen::exit_trailing::ExitArm;
use crate::usdm_sim::{run_simulation, PortfolioReceipt, UsdmSimParams};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::fs::{create_dir_all, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::thread;

pub const ITERATION_SCHEMA_VERSION: &str = "d145.economic-kaizen.v1";
pub const QUAD_SYMBOLS: [&str; 4] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"];
pub const DEFAULT_CHECKPOINT_LABEL: &str = "macro-m2-high-fine-risk-018";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EconomicIterationConfig {
    pub label: String,
    pub tape_path: PathBuf,
    pub initial_balance: f64,
    pub risk_fraction: f64,
    pub leverage: u32,
    pub max_concurrency: usize,
    pub max_heat: f64,
    pub decision_stride_bars: usize,
    pub enabled_experts: Option<Vec<String>>,
    pub variant_overrides: BTreeMap<String, String>,
    pub engine_mode: Option<String>,
    pub exit_arm: Option<ExitArm>,
    #[serde(default = "default_symbols")]
    pub symbols: Vec<String>,
}

fn default_symbols() -> Vec<String> {
    QUAD_SYMBOLS.iter().map(|symbol| (*symbol).to_string()).collect()
}

impl EconomicIterationConfig {
    pub fn baseline(tape_path: impl Into<PathBuf>) -> Self {
        Self {
            label: DEFAULT_CHECKPOINT_LABEL.into(),
            tape_path: tape_path.into(),
            initial_balance: 1000.0,
            risk_fraction: 0.0077725,
            leverage: 10,
            max_concurrency: 1,
            max_heat: 0.05,
            decision_stride_bars: 1,
            enabled_experts: None,
            variant_overrides: BTreeMap::new(),
            engine_mode: Some("macro-m2".into()),
            exit_arm: None,
            symbols: default_symbols(),
        }
    }

    fn params_for(&self, out_dir: PathBuf, symbol: &str) -> UsdmSimParams {
        let variant_overrides = self
            .variant_overrides
            .iter()
            .map(|(expert, variant)| (expert.clone(), variant.clone()))
            .collect::<HashMap<_, _>>();
        UsdmSimParams {
            tape_path: self.tape_path.clone(),
            out_dir,
            initial_balance: self.initial_balance / self.symbols.len().max(1) as f64,
            risk_fraction: self.risk_fraction,
            leverage: self.leverage,
            max_concurrency: self.max_concurrency,
            max_heat: self.max_heat,
            decision_stride_bars: self.decision_stride_bars,
            enabled_experts: self.enabled_experts.clone(),
            variant_overrides,
            engine_mode: self.engine_mode.clone(),
            exit_arm: self.exit_arm.clone(),
            symbol: Some(symbol.to_string()),
        }
    }

    pub fn hash(&self) -> String {
        hash_value_blake3(&serde_json::to_value(self).expect("iteration config serializes"))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EconomicFrontier {
    pub total_net_profit_usdt: f64,
    pub total_gross_market_pnl_usdt: f64,
    pub total_fee_drag_usdt: f64,
    pub max_drawdown_pct: f64,
    pub max_margin_utilization_pct: f64,
    pub per_asset_net_profit_usdt: BTreeMap<String, f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EconomicIterationReceipt {
    pub schema_version: String,
    pub iteration_id: usize,
    pub accepted_iteration_count: usize,
    pub status: String,
    pub decision_reason: String,
    pub config_hash: String,
    pub config: EconomicIterationConfig,
    pub frontier_before: Option<EconomicFrontier>,
    pub frontier_after: EconomicFrontier,
    pub total_net_profit_usdt: f64,
    pub total_gross_market_pnl_usdt: f64,
    pub total_fee_drag_usdt: f64,
    pub max_drawdown_pct: f64,
    pub max_margin_utilization_pct: f64,
    pub asset_receipts: Vec<PortfolioReceipt>,
}

fn frontier(receipts: &[PortfolioReceipt]) -> EconomicFrontier {
    let mut per_asset = BTreeMap::new();
    for receipt in receipts {
        let symbol = receipt
            .frontier_receipt
            .as_ref()
            .map(|frontier| frontier.symbol.clone())
            .unwrap_or_else(|| receipt.receipt_id.clone());
        per_asset.insert(symbol, receipt.net_profit_usdt);
    }
    EconomicFrontier {
        total_net_profit_usdt: receipts.iter().map(|r| r.net_profit_usdt).sum(),
        total_gross_market_pnl_usdt: receipts.iter().map(|r| r.gross_market_pnl_usdt).sum(),
        total_fee_drag_usdt: receipts.iter().map(|r| r.total_fee_drag_usdt).sum(),
        max_drawdown_pct: receipts
            .iter()
            .map(|r| r.max_drawdown_pct)
            .fold(0.0, f64::max),
        max_margin_utilization_pct: receipts
            .iter()
            .map(|r| r.max_margin_utilization_pct)
            .fold(0.0, f64::max),
        per_asset_net_profit_usdt: per_asset,
    }
}

fn write_receipt(path: &Path, receipt: &EconomicIterationReceipt) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "iteration receipt path has no parent".to_string())?;
    create_dir_all(parent).map_err(|e| e.to_string())?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    serde_json::to_writer(&mut file, receipt).map_err(|e| e.to_string())?;
    file.write_all(b"\n").map_err(|e| e.to_string())
}

pub struct EconomicIterationRunner {
    pub tape_path: PathBuf,
    pub output_root: PathBuf,
    pub receipt_path: PathBuf,
    pub accepted_iteration_count: usize,
    pub evaluation_count: usize,
    pub symbols: Vec<String>,
    pub frontier: EconomicFrontier,
    /// Fixed baseline safety budget for accepted candidates.
    pub safety_max_drawdown_pct: f64,
    pub safety_max_margin_utilization_pct: f64,
}

impl EconomicIterationRunner {
    pub fn bootstrap(
        baseline: EconomicIterationConfig,
        output_root: impl Into<PathBuf>,
    ) -> Result<(Self, EconomicIterationReceipt), String> {
        if baseline.symbols.is_empty() {
            return Err("economic iteration symbol set cannot be empty".into());
        }
        let output_root = output_root.into();
        create_dir_all(&output_root).map_err(|e| e.to_string())?;
        let receipt_path = output_root.join("iteration_receipts.jsonl");
        let asset_receipts = run_assets(&baseline, &output_root, 0)?;
        let current_frontier = frontier(&asset_receipts);
        let receipt = EconomicIterationReceipt {
            schema_version: ITERATION_SCHEMA_VERSION.into(),
            iteration_id: 0,
            accepted_iteration_count: 0,
            status: "BASELINE".into(),
            decision_reason: "current canonical real-tape baseline".into(),
            config_hash: baseline.hash(),
            config: baseline.clone(),
            frontier_before: None,
            frontier_after: current_frontier.clone(),
            total_net_profit_usdt: current_frontier.total_net_profit_usdt,
            total_gross_market_pnl_usdt: current_frontier.total_gross_market_pnl_usdt,
            total_fee_drag_usdt: current_frontier.total_fee_drag_usdt,
            max_drawdown_pct: current_frontier.max_drawdown_pct,
            max_margin_utilization_pct: current_frontier.max_margin_utilization_pct,
            asset_receipts,
        };
        write_receipt(&receipt_path, &receipt)?;
        Ok((
            Self {
                tape_path: baseline.tape_path,
                output_root,
                receipt_path,
                accepted_iteration_count: 0,
                evaluation_count: 0,
                symbols: baseline.symbols.clone(),
                safety_max_drawdown_pct: current_frontier.max_drawdown_pct,
                safety_max_margin_utilization_pct: current_frontier.max_margin_utilization_pct,
                frontier: current_frontier,
            },
            receipt,
        ))
    }

    pub fn evaluate(
        &mut self,
        iteration_id: usize,
        mut candidate: EconomicIterationConfig,
    ) -> Result<EconomicIterationReceipt, String> {
        self.evaluation_count += 1;
        candidate.tape_path = self.tape_path.clone();
        candidate.symbols = self.symbols.clone();
        let asset_receipts = run_assets(&candidate, &self.output_root, iteration_id)?;
        let candidate_frontier = frontier(&asset_receipts);
        let before = self.frontier.clone();
        let valid = asset_receipts.iter().all(|receipt| {
            receipt.terminal_equity_usdt.is_finite()
                && receipt.terminal_equity_usdt > 0.0
                && receipt.net_profit_usdt.is_finite()
                && receipt.total_fee_drag_usdt.is_finite()
                && receipt.max_drawdown_pct.is_finite()
                && receipt.max_margin_utilization_pct.is_finite()
        });
        let net_improved = candidate_frontier.total_net_profit_usdt > before.total_net_profit_usdt;
        let fees_increased = candidate_frontier.total_fee_drag_usdt > before.total_fee_drag_usdt;
        let drawdown_safe = candidate_frontier.max_drawdown_pct <= self.safety_max_drawdown_pct;
        let margin_safe =
            candidate_frontier.max_margin_utilization_pct <= self.safety_max_margin_utilization_pct;
        let accepted = valid && net_improved && drawdown_safe && margin_safe;
        let reason = if !valid {
            "invalid or non-finite economic receipt".into()
        } else if !net_improved {
            "net cashflow did not strictly improve".into()
        } else if !drawdown_safe {
            "drawdown increased".into()
        } else if !margin_safe {
            "margin utilization increased".into()
        } else if fees_increased {
            "net improved after costs; fee drag increased but was absorbed by the net gain".into()
        } else {
            "strict net improvement after costs with risk invariants preserved".into()
        };
        if accepted {
            self.accepted_iteration_count += 1;
            self.frontier = candidate_frontier.clone();
        }
        let receipt = EconomicIterationReceipt {
            schema_version: ITERATION_SCHEMA_VERSION.into(),
            iteration_id,
            accepted_iteration_count: self.accepted_iteration_count,
            status: if accepted { "ACCEPTED" } else { "REJECTED" }.into(),
            decision_reason: reason,
            config_hash: candidate.hash(),
            config: candidate,
            frontier_before: Some(before),
            frontier_after: candidate_frontier.clone(),
            total_net_profit_usdt: candidate_frontier.total_net_profit_usdt,
            total_gross_market_pnl_usdt: candidate_frontier.total_gross_market_pnl_usdt,
            total_fee_drag_usdt: candidate_frontier.total_fee_drag_usdt,
            max_drawdown_pct: candidate_frontier.max_drawdown_pct,
            max_margin_utilization_pct: candidate_frontier.max_margin_utilization_pct,
            asset_receipts,
        };
        write_receipt(&self.receipt_path, &receipt)?;
        Ok(receipt)
    }
}

fn run_assets(
    config: &EconomicIterationConfig,
    output_root: &Path,
    iteration_id: usize,
) -> Result<Vec<PortfolioReceipt>, String> {
    let jobs = config
        .symbols
        .iter()
        .map(|symbol| {
            let out_dir = output_root
                .join(format!("iteration-{iteration_id:04}"))
                .join(symbol);
            (symbol.clone(), config.params_for(out_dir, symbol))
        })
        .collect::<Vec<_>>();
    let mut receipts_by_symbol = BTreeMap::new();
    thread::scope(|scope| {
        let handles = jobs
            .into_iter()
            .map(|(symbol, params)| scope.spawn(move || run_simulation(&params).map(|receipt| (symbol, receipt))))
            .collect::<Vec<_>>();
        for handle in handles {
            let result = handle
                .join()
                .map_err(|_| "asset simulation thread panicked".to_string())??;
            receipts_by_symbol.insert(result.0, result.1);
        }
        Ok::<(), String>(())
    })?;
    let mut receipts = Vec::with_capacity(config.symbols.len());
    for symbol in &config.symbols {
        let receipt = receipts_by_symbol
            .remove(symbol)
            .ok_or_else(|| format!("missing receipt for configured symbol {symbol}"))?;
        receipts.push(receipt);
    }
    Ok(receipts)
}


pub fn candidate_seed_set(tape_path: impl Into<PathBuf>) -> Vec<EconomicIterationConfig> {
    let tape_path = tape_path.into();
    let base = EconomicIterationConfig::baseline(tape_path.clone());
    // The first accepted frontier is known from the real-tape pilot only after
    // evaluation, so keep a deterministic local-search anchor alongside the
    // canonical baseline.  These are still ordinary simulator configurations;
    // no observed result is copied into a candidate.
    let mut frontier_anchor = base.clone();
    frontier_anchor.label = "frontier-anchor-concurrency-1".into();
    frontier_anchor.max_concurrency = 1;
    let mut macro_frontier_anchor = frontier_anchor.clone();
    macro_frontier_anchor.label = "frontier-anchor-macro-m1".into();
    macro_frontier_anchor.engine_mode = Some("macro-m1".into());
    let mut candidates = Vec::new();

    for stride in [2usize, 3, 4, 6, 8, 12, 16, 24] {
        let mut candidate = base.clone();
        candidate.label = format!("commission-timing-stride-{stride}");
        candidate.decision_stride_bars = stride;
        candidates.push(candidate);
    }
    for stride in [2usize, 3, 4, 6, 8, 12] {
        for risk_fraction in [0.0065, 0.007, 0.0075, 0.00775, 0.008, 0.009, 0.01] {
            let mut candidate = base.clone();
            candidate.label = format!("commission-timing-stride-{stride}-risk-{risk_fraction}");
            candidate.decision_stride_bars = stride;
            candidate.risk_fraction = risk_fraction;
            candidates.push(candidate);
        }
    }

    for (anchor_name, anchor) in [("baseline", &base), ("frontier", &frontier_anchor)] {
        for engine_mode in [
            "squeeze-swing",
            "macro-m1",
            "macro-m2",
            "macro-m3",
            "macro-swing",
        ] {
            let mut candidate = anchor.clone();
            candidate.label = format!("{anchor_name}-engine-{engine_mode}");
            candidate.engine_mode = Some(engine_mode.into());
            candidates.push(candidate);
        }
    }

    // Fine local search around the first two accepted real-tape settings.
    // These values are declared simulator inputs, not observed outcomes.
    for risk_fraction in [0.00525, 0.0055, 0.00575, 0.006, 0.00625] {
        let mut candidate = macro_frontier_anchor.clone();
        candidate.label = format!("macro-m1-risk-{risk_fraction}");
        candidate.risk_fraction = risk_fraction;
        candidates.push(candidate);
    }
    for max_concurrency in [1, 2, 3, 4] {
        let mut candidate = macro_frontier_anchor.clone();
        candidate.label = format!("macro-m1-concurrency-{max_concurrency}");
        candidate.max_concurrency = max_concurrency;
        candidates.push(candidate);
    }
    for heat in [0.03, 0.04, 0.06, 0.08, 0.10] {
        let mut candidate = macro_frontier_anchor.clone();
        candidate.label = format!("macro-m1-heat-{heat}");
        candidate.max_heat = heat;
        candidates.push(candidate);
    }

    // Quantization-aware fine risk sweep around the best observed engine
    // family. Every point still executes the complete real tape; the grid
    // exists to expose lot-size and fee discontinuities, not to manufacture
    // a smoother equity curve.
    let mut fine_risk_anchor = frontier_anchor.clone();
    fine_risk_anchor.engine_mode = Some("macro-m2".into());
    for step in 1..=100usize {
        let risk_fraction = 0.0065 + (step as f64 * 0.0000025);
        let mut candidate = fine_risk_anchor.clone();
        candidate.label = format!("macro-m2-fine-risk-{step:03}");
        candidate.risk_fraction = risk_fraction;
        candidates.push(candidate);
    }
    let mut high_risk_anchor = frontier_anchor.clone();
    high_risk_anchor.engine_mode = Some("macro-m2".into());
    for step in 1..=100usize {
        let risk_fraction = 0.00775 + (step as f64 * 0.00000125);
        let mut candidate = high_risk_anchor.clone();
        candidate.label = format!("macro-m2-high-fine-risk-{step:03}");
        candidate.risk_fraction = risk_fraction;
        candidates.push(candidate);
    }

    for engine_mode in ["macro-m1", "macro-m2", "macro-m3", "macro-swing"] {
        let mut engine_anchor = frontier_anchor.clone();
        engine_anchor.engine_mode = Some(engine_mode.into());
        for risk_fraction in [0.0065, 0.00675, 0.007, 0.00725, 0.0075, 0.00775, 0.008] {
            let mut candidate = engine_anchor.clone();
            candidate.label = format!("{engine_mode}-risk-{risk_fraction}");
            candidate.risk_fraction = risk_fraction;
            candidates.push(candidate);
        }
        for leverage in [5, 8, 10, 12, 15, 20] {
            let mut candidate = engine_anchor.clone();
            candidate.label = format!("{engine_mode}-leverage-{leverage}");
            candidate.leverage = leverage;
            candidates.push(candidate);
        }
        for arm in [
            ExitArm::ChandelierATR,
            ExitArm::ChandelierATRWithBE05R,
            ExitArm::ChandelierATRWithBE075R,
            ExitArm::ChandelierATRWithBE10R,
            ExitArm::NoTP,
            ExitArm::Static1R,
            ExitArm::Static2R,
            ExitArm::Static3R,
            ExitArm::EMA4hTrail,
            ExitArm::HybridTrail,
            ExitArm::Structural24hTrail,
        ] {
            let mut candidate = engine_anchor.clone();
            candidate.label = format!("{engine_mode}-exit-{:?}", arm);
            candidate.exit_arm = Some(arm);
            candidates.push(candidate);
        }
    }

    // Evaluate every non-trivial subset of the eight alpha paths that are
    // active in the canonical ensemble.  This is a real combinatorial
    // challenger surface: each subset is replayed on all four symbols and is
    // accepted only through the same economic and safety gate.
    let alpha_experts = [
        "floor_trader_pivot",
        "failed_breakout",
        "fib_projection_reversal",
        "liquidity_sweep_reclaim",
        "range_breakout_1to1",
        "ichimoku_cloud",
        "trend_continuation",
        "squeeze_swing",
    ];
    for mask in 1usize..(1usize << alpha_experts.len()) {
        if mask.count_ones() < 2 {
            continue;
        }
        let enabled = alpha_experts
            .iter()
            .enumerate()
            .filter_map(|(index, expert)| {
                (mask & (1usize << index) != 0).then_some((*expert).to_string())
            })
            .collect::<Vec<_>>();
        let mut candidate = macro_frontier_anchor.clone();
        candidate.label = format!("macro-m1-alpha-subset-{mask:03x}");
        candidate.risk_fraction = 0.0065;
        candidate.enabled_experts = Some(enabled);
        candidates.push(candidate);
    }

    for (anchor_name, anchor) in [("baseline", &base), ("frontier", &frontier_anchor)] {
        for arm in [
            ExitArm::ChandelierATR,
            ExitArm::ChandelierATRWithBE05R,
            ExitArm::ChandelierATRWithBE075R,
            ExitArm::ChandelierATRWithBE10R,
            ExitArm::NoTP,
            ExitArm::Static1R,
            ExitArm::Static2R,
            ExitArm::Static3R,
            ExitArm::EMA4hTrail,
            ExitArm::HybridTrail,
            ExitArm::Structural24hTrail,
        ] {
            let mut candidate = anchor.clone();
            candidate.label = format!("{anchor_name}-exit-{:?}", arm);
            candidate.exit_arm = Some(arm);
            candidates.push(candidate);
        }
    }

    for concurrency in 1..=8 {
        let mut candidate = base.clone();
        candidate.label = format!("concurrency-{concurrency}");
        candidate.max_concurrency = concurrency;
        candidates.push(candidate);
    }

    for (anchor_name, anchor) in [("baseline", &base), ("frontier", &frontier_anchor)] {
        for heat in [0.03, 0.04, 0.06, 0.08, 0.10] {
            let mut candidate = anchor.clone();
            candidate.label = format!("{anchor_name}-heat-{heat}");
            candidate.max_heat = heat;
            candidates.push(candidate);
        }

        for risk_fraction in [0.0025, 0.00375, 0.00625, 0.0075, 0.01] {
            let mut candidate = anchor.clone();
            candidate.label = format!("{anchor_name}-risk-{risk_fraction}");
            candidate.risk_fraction = risk_fraction;
            candidates.push(candidate);
        }
    }

    for (anchor_name, anchor) in [("baseline", &base), ("frontier", &frontier_anchor)] {
        for (expert_id, variants) in crate::experts::VARIANT_TABLE {
            for variant in variants.iter().copied() {
                let mut candidate = anchor.clone();
                candidate.label = format!("{anchor_name}-variant-{expert_id}-{variant}");
                candidate
                    .variant_overrides
                    .insert((*expert_id).into(), (*variant).into());
                candidates.push(candidate);
            }
        }
    }

    let mut all_experts = crate::experts::TABLE
        .iter()
        .map(|(id, _, _, _)| (*id).to_string())
        .collect::<Vec<_>>();
    all_experts.extend(["trend_continuation".into(), "squeeze_swing".into()]);
    for (anchor_name, anchor) in [("baseline", &base), ("frontier", &frontier_anchor)] {
        for expert in &all_experts {
            let mut candidate = anchor.clone();
            candidate.label = format!("{anchor_name}-singleton-{expert}");
            candidate.enabled_experts = Some(vec![expert.clone()]);
            candidates.push(candidate);
        }
    }

    for (anchor_name, anchor) in [("baseline", &base), ("frontier", &frontier_anchor)] {
        for width in 2..=all_experts.len() {
            let mut candidate = anchor.clone();
            candidate.label = format!("{anchor_name}-prefix-{width}");
            candidate.enabled_experts = Some(all_experts[..width].to_vec());
            candidates.push(candidate);
        }
    }
    candidates
}

#[cfg(test)]
mod tests {
    use super::{candidate_seed_set, EconomicIterationConfig};
    use std::collections::BTreeMap;

    #[test]
    fn config_hash_is_deterministic_and_binds_variants() {
        let tape = "research/tape/quad-1h-12m/tape.jsonl";
        let first = EconomicIterationConfig::baseline(tape);
        let second = EconomicIterationConfig::baseline(tape);
        assert_eq!(first.hash(), second.hash());

        let mut changed = first.clone();
        changed.variant_overrides = BTreeMap::from([("squeeze_swing".into(), "m1".into())]);
        assert_ne!(first.hash(), changed.hash());
    }

    #[test]
    fn candidate_seed_set_contains_fine_and_subset_challengers() {
        let candidates = candidate_seed_set("research/tape/quad-1h-12m/tape.jsonl");
        let baseline = EconomicIterationConfig::baseline("research/tape/quad-1h-12m/tape.jsonl");
        assert_eq!(baseline.label, super::DEFAULT_CHECKPOINT_LABEL);
        assert_eq!(baseline.risk_fraction, 0.0077725);
        assert_eq!(baseline.max_concurrency, 1);
        assert_eq!(baseline.engine_mode.as_deref(), Some("macro-m2"));
        assert!(candidates
            .iter()
            .any(|candidate| candidate.label == "macro-m2-fine-risk-001"));
        assert!(candidates.iter().any(|candidate| {
            candidate.label == "commission-timing-stride-12"
                && candidate.decision_stride_bars == 12
        }));
        assert!(candidates
            .iter()
            .any(|candidate| candidate.label.starts_with("macro-m1-alpha-subset-")));
    }
}
