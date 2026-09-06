// Consolidated integration test runner (D-155 / ISSUE_PERF008)
// Aggregates all integration suites into a single Mach-O binary
// eliminating linker storms and redundant symbol resolution on macOS ld64.

#[path = "suites/ai_agent_tevv_sabotage.rs"]
mod ai_agent_tevv_sabotage;

#[path = "suites/assurance_fabric_sabotage.rs"]
mod assurance_fabric_sabotage;

#[path = "suites/causal_future_shock.rs"]
mod causal_future_shock;

#[path = "suites/continuous_certificate_lifecycle.rs"]
mod continuous_certificate_lifecycle;

#[path = "suites/d150_epistemic_succession_sabotage.rs"]
mod d150_epistemic_succession_sabotage;

#[path = "suites/d152_gate_vector_authority_firewall.rs"]
mod d152_gate_vector_authority_firewall;

#[path = "suites/d153_benchmark_fabric_sabotage.rs"]
mod d153_benchmark_fabric_sabotage;

#[path = "suites/d153_minerva_and_dashboard_test.rs"]
mod d153_minerva_and_dashboard_test;

#[path = "suites/data_role_holdout_burn.rs"]
mod data_role_holdout_burn;

#[path = "suites/policy_evidence_profile_adversarial.rs"]
mod policy_evidence_profile_adversarial;

#[path = "suites/production_growth_contract.rs"]
mod production_growth_contract;

#[path = "suites/system_proving_ground.rs"]
mod system_proving_ground;

#[path = "suites/world_foundry_isolation.rs"]
mod world_foundry_isolation;

#[path = "suites/world_foundry_v2_falsification.rs"]
mod world_foundry_v2_falsification;
