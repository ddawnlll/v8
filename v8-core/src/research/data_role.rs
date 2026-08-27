//! Lineage-Aware Data Role Ledger (D-147, D-149, M4).
//!
//! Enforces:
//! 1. Data segments have lineage-relative roles, not global static labels.
//! 2. Once a POLICY_FROZEN_OOS segment is evaluated by a policy lineage, its status
//!    for that lineage transitions irreversibly to BURNED_DIAGNOSTIC.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// The 6 statutory data segment roles.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum DataSegmentRole {
    PolicyDev,
    GeneratorCalibration,
    PolicyFrozenOos,
    BurnedDiagnostic,
    ProspectiveShadow,
    Live,
}

impl DataSegmentRole {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::PolicyDev => "POLICY_DEV",
            Self::GeneratorCalibration => "GENERATOR_CALIBRATION",
            Self::PolicyFrozenOos => "POLICY_FROZEN_OOS",
            Self::BurnedDiagnostic => "BURNED_DIAGNOSTIC",
            Self::ProspectiveShadow => "PROSPECTIVE_SHADOW",
            Self::Live => "LIVE",
        }
    }

    /// Returns true if this data role can be used as pristine unblemished out-of-sample evidence.
    pub const fn is_pristine_oos(&self) -> bool {
        matches!(self, Self::PolicyFrozenOos | Self::ProspectiveShadow)
    }
}

/// Ledger tracking assigned data segment roles per policy lineage.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct DataRoleLedger {
    /// Maps (segment_id, policy_lineage) -> DataSegmentRole
    pub assignments: HashMap<(String, String), DataSegmentRole>,
}

impl DataRoleLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn assign_role(&mut self, segment_id: &str, lineage: &str, role: DataSegmentRole) {
        self.assignments.insert((segment_id.to_string(), lineage.to_string()), role);
    }

    pub fn get_role(&self, segment_id: &str, lineage: &str) -> DataSegmentRole {
        self.assignments
            .get(&(segment_id.to_string(), lineage.to_string()))
            .copied()
            .unwrap_or(DataSegmentRole::PolicyDev)
    }
}
