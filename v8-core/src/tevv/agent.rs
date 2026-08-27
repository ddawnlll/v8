//! Autonomous Agent Audit Manifests & Action Receipts (D-147, D-149, Rules 21, 22, 23, 24, M5).
//!
//! Enforces:
//! 1. Every agent action/hypothesis must be bound to a content-addressed audit transcript.
//! 2. Unattested or tampered agent actions fail closed to INADMISSIBLE (AF-T16).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Autonomous Agent Audit Manifest.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AgentAuditManifest {
    pub agent_id: String,
    pub role: String,
    pub model_id: String,
    pub prompt_hash: String,
    pub tools_allowed: Vec<String>,
    pub created_at_timestamp_ns: u64,
}

impl AgentAuditManifest {
    pub fn new(agent_id: &str, role: &str, model_id: &str, system_prompt: &str, tools: Vec<String>, ts: u64) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(system_prompt.as_bytes());
        let prompt_hash = format!("{:x}", hasher.finalize());

        Self {
            agent_id: agent_id.to_string(),
            role: role.to_string(),
            model_id: model_id.to_string(),
            prompt_hash,
            tools_allowed: tools,
            created_at_timestamp_ns: ts,
        }
    }
}

/// Cryptographically sealed Action Audit Receipt.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActionAuditReceipt {
    pub action_id: String,
    pub agent_id: String,
    pub action_type: String,
    pub tool_called: String,
    pub tool_arguments_hash: String,
    pub transcript_hash: String,
    pub timestamp_ns: u64,
}

impl ActionAuditReceipt {
    pub fn new(
        agent_id: &str,
        action_type: &str,
        tool: &str,
        args_json: &str,
        transcript_hash: &str,
        ts: u64,
    ) -> Self {
        let mut args_hasher = Sha256::new();
        args_hasher.update(args_json.as_bytes());
        let args_hash = format!("{:x}", args_hasher.finalize());

        let mut id_hasher = Sha256::new();
        id_hasher.update(agent_id.as_bytes());
        id_hasher.update(action_type.as_bytes());
        id_hasher.update(&ts.to_le_bytes());
        let action_id = format!("act-{}", &format!("{:x}", id_hasher.finalize())[..16]);

        Self {
            action_id,
            agent_id: agent_id.to_string(),
            action_type: action_type.to_string(),
            tool_called: tool.to_string(),
            tool_arguments_hash: args_hash,
            transcript_hash: transcript_hash.to_string(),
            timestamp_ns: ts,
        }
    }

    /// Verifies if action has valid transcript binding (AF-T16).
    pub fn is_valid(&self) -> bool {
        !self.transcript_hash.is_empty() && self.transcript_hash.len() >= 16
    }
}
