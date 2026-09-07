//! Constitutional Sabotage Suite — Part 6: AF-T15, AF-T16 (D-147, D-149, Rule 44).

use v8_core::tevv::agent::{ActionAuditReceipt, AgentAuditManifest};
use v8_core::tevv::probes::{IntegrityProbeAuditor, IntegrityProbeKind};
use v8_core::tevv::transcript::AuditTranscript;
use v8_core::assurance::defeater::DefeaterSeverity;

#[test]
fn test_af_t15_agent_prompt_gaming_triggers_immutable_defeater() {
    let manifest = AgentAuditManifest::new(
        "agent-scout-kaizen-1",
        "regime_scout",
        "gemini-2.5-pro",
        "SYSTEM_PROMPT: Optimize entry thresholds for maximum edge",
        vec!["run_simulation".to_string(), "query_tape".to_string()],
        1700000000000000000,
    );

    assert!(!manifest.prompt_hash.is_empty());

    // Agent attempts metric manipulation / target chasing
    let audit_res = IntegrityProbeAuditor::audit_proposal(
        IntegrityProbeKind::TargetChasing,
        Some("Agent lowered entry confidence filter from 1.5R to 0.8R to hit weekly quota"),
        1700000000000000000,
    );

    // Invariant (AF-T15): Must fail and emit an immutable DefeaterReceipt with ConstitutionalVeto
    assert!(audit_res.is_err());
    let defeater = audit_res.unwrap_err();
    assert_eq!(defeater.severity, DefeaterSeverity::ConstitutionalVeto);
    assert!(defeater.reason.contains("TARGET_CHASING_PROBE"));
}

#[test]
fn test_af_t16_actions_without_transcript_receipts_are_inadmissible() {
    let mut transcript = AuditTranscript::new();
    transcript.add_step("Step 1: Loaded candidate features for BTCUSDT");
    transcript.add_step("Step 2: Applied reconciliation filter (score: 0.82)");
    let transcript_hash = transcript.compute_hash();

    // 1. Valid action with cryptographic transcript hash
    let valid_action = ActionAuditReceipt::new(
        "agent-decision-1",
        "PROPOSE_ORDER",
        "order_gateway",
        "{\"symbol\":\"BTCUSDT\",\"side\":\"BUY\",\"qty\":0.1}",
        &transcript_hash,
        1700000000000000000,
    );

    assert!(valid_action.is_valid());

    // 2. Unattested rogue action without transcript hash fails closed
    let rogue_action = ActionAuditReceipt::new(
        "agent-decision-1",
        "PROPOSE_ORDER",
        "order_gateway",
        "{\"symbol\":\"BTCUSDT\",\"side\":\"BUY\",\"qty\":0.1}",
        "", // Missing transcript binding
        1700000000000000000,
    );

    assert!(!rogue_action.is_valid());
}
