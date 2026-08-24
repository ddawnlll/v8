//! D-145 executable driver for real-tape economic Kaizen iterations.

use std::path::PathBuf;

use v8_core::kaizen::{candidate_seed_set, EconomicIterationRunner};

fn main() -> Result<(), String> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    let tape = args
        .first()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("research/tape/quad-1h-12m/tape.jsonl"));
    let output_root = args
        .get(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".audit/kaizen_iterations/current"));
    let target = args
        .get(2)
        .map(|value| value.parse::<usize>().map_err(|e| e.to_string()))
        .transpose()?
        .unwrap_or(100);

    let baseline = v8_core::kaizen::EconomicIterationConfig::baseline(tape.clone());
    let (mut runner, baseline_receipt) =
        EconomicIterationRunner::bootstrap(baseline, &output_root)?;
    println!(
        "BASELINE net={:.6} fees={:.6} max_dd={:.6} receipt={}",
        baseline_receipt.total_net_profit_usdt,
        baseline_receipt.total_fee_drag_usdt,
        baseline_receipt.max_drawdown_pct,
        runner.receipt_path.display()
    );

    let candidates = candidate_seed_set(tape);
    for (offset, candidate) in candidates.into_iter().enumerate() {
        if runner.accepted_iteration_count >= target {
            break;
        }
        let iteration_id = offset + 1;
        let receipt = runner.evaluate(iteration_id, candidate)?;
        println!(
            "ITERATION {:04} {:8} accepted={} net={:.6} delta={:.6} reason={}",
            iteration_id,
            receipt.status,
            receipt.accepted_iteration_count,
            receipt.total_net_profit_usdt,
            receipt
                .frontier_before
                .as_ref()
                .map(|before| receipt.total_net_profit_usdt - before.total_net_profit_usdt)
                .unwrap_or(0.0),
            receipt.decision_reason
        );
    }

    let summary = serde_json::json!({
        "schema_version": v8_core::kaizen::ITERATION_SCHEMA_VERSION,
        "target_accepted_iterations": target,
        "accepted_iterations": runner.accepted_iteration_count,
        "safety_ceiling": {
            "max_drawdown_pct": runner.safety_max_drawdown_pct,
            "max_margin_utilization_pct": runner.safety_max_margin_utilization_pct,
        },
        "frontier": runner.frontier,
        "receipt_path": runner.receipt_path,
        "status": if runner.accepted_iteration_count >= target { "TARGET_REACHED" } else { "TARGET_NOT_REACHED" },
    });
    std::fs::write(
        output_root.join("summary.json"),
        serde_json::to_vec_pretty(&summary).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;

    if runner.accepted_iteration_count < target {
        return Err(format!(
            "accepted iteration target not reached: {} of {target}; rejected candidates remain recorded",
            runner.accepted_iteration_count
        ));
    }
    Ok(())
}
