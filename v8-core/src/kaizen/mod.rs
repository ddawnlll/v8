pub mod challenger;
pub mod diagnosis;
pub mod hypothesis;
pub mod research_debt;
pub mod robustness;

pub use challenger::{ChallengerFamilySpec, ChallengerVariant, DiscreteParameterRange};
pub use diagnosis::{
    EvidenceRequirement, EvidenceValidity, ExpertForensics, ExpertId, FailureTag,
    ForensicAssessment, ForensicsError, RegimeForensics, ReplicationStatus, VariantId,
};
pub use hypothesis::{
    FalsificationRule, FindingGenerator, HypothesisError, HypothesisGenerator, HypothesisRecord,
    ResearchFinding,
};
pub use research_debt::{GlobalTrialLedger, TrialEntry};
pub use robustness::{
    PlateauCriterion, PointAssessment, RobustnessCampaign, RobustnessCampaignReceipt,
    RobustnessPoint, RobustnessSurface, RobustnessVerdict,
};
