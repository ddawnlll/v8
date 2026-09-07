pub mod adaptive;
pub mod campaign;
pub mod challenger;
pub mod chop_suppression;
pub mod diagnosis;
pub mod exit_trailing;
pub mod hypothesis;
pub mod iteration;
pub mod quantization;
pub mod research_debt;
pub mod robustness;
pub mod validation;


pub use adaptive::{
    O032UnblockingCriteria, SweepConfig, SweepEngine, SweepError, SweepMode, SweepReceipt,
};
pub use campaign::{CampaignCluster, CampaignDirection, MechanismFamily, PersistentCampaignRegistry, SensorVote};
pub use challenger::{ChallengerFamilySpec, ChallengerVariant, DiscreteParameterRange};
pub use chop_suppression::{ChopGateContext, ChopSuppressionArm, ChopVerdict, CostAwareNoTradeGate};
pub use diagnosis::{
    EvidenceRequirement, EvidenceValidity, ExpertForensics, ExpertId, FailureTag,
    ForensicAssessment, ForensicsError, RegimeForensics, ReplicationStatus, VariantId,
};
pub use exit_trailing::{DynamicTrailingEngine, ExitArm, ExitResult, TrailingState};
pub use hypothesis::{
    FalsificationRule, FindingGenerator, HypothesisError, HypothesisGenerator, HypothesisRecord,
    ResearchFinding,
};
pub use iteration::{
    candidate_seed_set, EconomicFrontier, EconomicIterationConfig,
    EconomicIterationReceipt, EconomicIterationRunner, ITERATION_SCHEMA_VERSION,
};
pub use quantization::{QuantizationBudgetResult, QuantizationFeasibilityStatus, QuantizationRiskEngine};
pub use research_debt::{GlobalTrialLedger, TrialEntry};
pub use robustness::{
    PlateauCriterion, PointAssessment, RobustnessCampaign, RobustnessCampaignReceipt,
    RobustnessPoint, RobustnessSurface, RobustnessVerdict,
};
pub use validation::{
    FoldVerdict, HoldoutAccessKey, HoldoutBurnReceipt, HoldoutBurnRegistry, HoldoutError,
    HoldoutState, PurgedWfaEngine, TimeRange, WfaCampaignReceipt, WfaCampaignSpec,
    WfaCampaignVerdict, WfaFoldReceipt, WfaFoldSpec,
};
