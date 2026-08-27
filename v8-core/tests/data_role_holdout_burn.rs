//! Constitutional Sabotage Suite — Part 5: AF-T07 & Research Multiplicity (D-147, D-149, Rule 44).

use v8_core::research::data_role::{DataRoleLedger, DataSegmentRole};
use v8_core::research::holdout::HoldoutBurnReceipt;
use v8_core::research::statistical_plan::StatisticalPlan;

#[test]
fn test_af_t07_holdout_burn_transitions_irreversibly_to_burned_diagnostic() {
    let mut ledger = DataRoleLedger::new();

    let segment_id = "oos_slice_2024_q1";
    let lineage_a = "policy_family_momentum_v1";
    let lineage_b = "policy_family_mean_revert_v1";

    // 1. Assign POLICY_FROZEN_OOS to both lineages initially
    ledger.assign_role(segment_id, lineage_a, DataSegmentRole::PolicyFrozenOos);
    ledger.assign_role(segment_id, lineage_b, DataSegmentRole::PolicyFrozenOos);

    assert!(ledger.get_role(segment_id, lineage_a).is_pristine_oos());
    assert!(ledger.get_role(segment_id, lineage_b).is_pristine_oos());

    // 2. Lineage A evaluates and burns the segment
    let burn_receipt = HoldoutBurnReceipt::burn_segment(
        &mut ledger,
        segment_id,
        lineage_a,
        1700000000000000000,
    ).expect("Holdout burn failed");

    assert_eq!(burn_receipt.prior_role, DataSegmentRole::PolicyFrozenOos);
    assert_eq!(burn_receipt.new_role, DataSegmentRole::BurnedDiagnostic);

    // Invariant (AF-T07): Lineage A now sees the segment as BURNED_DIAGNOSTIC (not pristine)
    assert_eq!(ledger.get_role(segment_id, lineage_a), DataSegmentRole::BurnedDiagnostic);
    assert!(!ledger.get_role(segment_id, lineage_a).is_pristine_oos());

    // Lineage B was NOT evaluated on this segment, so for Lineage B it remains pristine
    assert_eq!(ledger.get_role(segment_id, lineage_b), DataSegmentRole::PolicyFrozenOos);
    assert!(ledger.get_role(segment_id, lineage_b).is_pristine_oos());

    // 3. Attempting to re-burn an already burned segment fails closed
    let reburn_res = HoldoutBurnReceipt::burn_segment(
        &mut ledger,
        segment_id,
        lineage_a,
        1700000001000000000,
    );
    assert!(reburn_res.is_err());
}

#[test]
fn test_research_multiplicity_and_trial_debt_accounting() {
    let mut plan = StatisticalPlan::new(
        "family-trend-breakout".to_string(),
        "lineage-v1".to_string(),
        0.05, // Initial alpha budget = 0.05 (5%)
    );

    assert_eq!(plan.total_trial_debt, 1);
    assert!((plan.adjusted_alpha_threshold - 0.05).abs() < 1e-6);

    // Discard 9 failed model variants during research exploration
    for _ in 0..9 {
        plan.record_discarded_variant();
    }

    // Invariant: Trial debt = 9 discarded + 1 retained = 10 total
    assert_eq!(plan.discarded_variants_count, 9);
    assert_eq!(plan.total_trial_debt, 10);

    // Multiplicity adjusted alpha threshold must scale down (0.05 / 10 = 0.005)
    assert!((plan.adjusted_alpha_threshold - 0.005).abs() < 1e-6);
}
