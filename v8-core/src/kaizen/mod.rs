pub mod adaptive;
pub mod campaign;
pub mod challenger;
pub mod chop_suppression;
pub mod controller;
pub mod correlation;
pub mod cost_surface;
pub mod derivatives;
pub mod diagnosis;
pub mod exit_trailing;
pub mod governance;
pub mod hypothesis;
pub mod iteration;
pub mod liquidity_floor;
pub mod mega;
pub mod provenance;
pub mod pyramiding;
pub mod quantization;
pub mod research_debt;
pub mod robustness;
pub mod validation;
pub mod verdict;
pub mod verification;

pub use controller::{KaizenController, KaizenControllerConfig};
pub use verdict::{KaizenVerdict, KaizenVerdictEngine};

pub use adaptive::{
    O032UnblockingCriteria, SweepConfig, SweepEngine, SweepError, SweepMode, SweepReceipt,
};
pub use campaign::{CampaignCluster, CampaignDirection, MechanismFamily, PersistentCampaignRegistry, SensorVote};
pub use challenger::{ChallengerFamilySpec, ChallengerVariant, DiscreteParameterRange};
pub use chop_suppression::{ChopGateContext, ChopSuppressionArm, ChopVerdict, CostAwareNoTradeGate};
pub use correlation::{CrossAssetCorrelationClusterer, ClusterAllocationResult};
pub use cost_surface::{CostFeasibilityCheck, VenueCostEngine, VenueCostProfile, VipTier};
pub use derivatives::{ChannelStatus, DerivativesChannelManifest, DerivativesTapeIngester, MarketSponsorshipBar};
pub use diagnosis::{
    EvidenceRequirement, EvidenceValidity, ExpertForensics, ExpertId, FailureTag,
    ForensicAssessment, ForensicsError, RegimeForensics, ReplicationStatus, VariantId,
};
pub use exit_trailing::{DynamicTrailingEngine, ExitArm, ExitResult, TrailingState};
pub use governance::{AntiPruningCompliance, CertificationStatus, GovernanceGuardrailEngine, KellySizingAssessment};
pub use hypothesis::{
    FalsificationRule, FindingGenerator, HypothesisError, HypothesisGenerator, HypothesisRecord,
    ResearchFinding,
};
pub use iteration::{
    candidate_seed_set, EconomicFrontier, EconomicIterationConfig,
    EconomicIterationReceipt, EconomicIterationRunner, ITERATION_SCHEMA_VERSION,
};
pub use liquidity_floor::{DynamicAllocationBudget, DynamicLiquidityFloorEngine, LiquidityFloorBreakdown};
pub use mega::{ExtremeEpisode, ExtremeMoveDetector, MegaBenchmarkReport, MegaCapabilityStatus, SensorLeadTimeAudit};
pub use provenance::{CertifiedTapeHandle, ProvenanceStatus, TapeProvenanceVerifier};
pub use pyramiding::{PyramidingCampaign, PyramidingDecision, PyramidingEngine};
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
pub use verification::{CampaignSimulationSummary, CampaignSimulator, CampaignTradeExecution};
