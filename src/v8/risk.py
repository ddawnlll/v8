"""Deterministic risk gate (CANDIDATE_LIFECYCLE_SPEC section 6).

Risk preferences are HARD CONSTRAINTS, not reward penalties (LEARNING_PROTOCOL
section 4): admission is a deterministic rule, never a learned component, and
a forbidden action is rejected, not punished.

Policy (provisional baseline, approved 2026-08-01):
- Heat is the sum of per-position stop risk in R; with fixed 1R geometry this
  equals the number of open positions.
- Correlated clusters are a FIXED instrument list — no rolling estimation
  (DeMiguel et al. 2009: estimation error is what kills allocation models).
- On cap breach the new Candidate is REJECTED (CAPACITY_REJECTED), never
  downsized: downsizing would silently enter the deferred ranker gate
  (OPEN_DECISIONS O-006/O-012).
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import CandidateDraft
from .lifecycle import ExposureBook

DEFAULT_CLUSTERS = {
    'BTCUSDT': 'btc', 'ETHUSDT': 'btc',
    'SOLUSDT': 'major', 'BNBUSDT': 'major', 'XRPUSDT': 'major', 'DOGEUSDT': 'major',
}


@dataclass(frozen=True)
class RiskVerdict:
    ok: bool
    reason_code: str | None = None
    detail: str | None = None


class RiskGate:
    def __init__(self, max_heat: float = 3.0, max_cluster_heat: float = 2.0,
                 clusters: dict[str, str] | None = None):
        self._book = ExposureBook()
        self.max_heat = max_heat
        self.max_cluster_heat = max_cluster_heat
        self.clusters = clusters or DEFAULT_CLUSTERS
        self._heat: dict[str, float] = {}

    def _risk_r(self, draft: CandidateDraft) -> float:
        return float(draft.risk_geometry.get('stop_r', 1.0))

    def _cluster(self, draft: CandidateDraft) -> str:
        return self.clusters.get(draft.instrument, 'other')

    def admit(self, draft: CandidateDraft) -> RiskVerdict:
        if not self._book.acquire(draft.instrument, draft.direction):
            return RiskVerdict(False, 'EXISTING_EXPOSURE_CONFLICT')
        risk = self._risk_r(draft)
        cluster = self._cluster(draft)
        if self._heat.get(cluster, 0.0) + risk > self.max_cluster_heat:
            self._book.release(draft.instrument, draft.direction)
            return RiskVerdict(False, 'PORTFOLIO_HEAT_EXCEEDED', f'cluster:{cluster}')
        if sum(self._heat.values()) + risk > self.max_heat:
            self._book.release(draft.instrument, draft.direction)
            return RiskVerdict(False, 'PORTFOLIO_HEAT_EXCEEDED', 'total')
        self._heat[cluster] = self._heat.get(cluster, 0.0) + risk
        return RiskVerdict(True)

    def release(self, draft: CandidateDraft) -> None:
        self._book.release(draft.instrument, draft.direction)
        cluster = self._cluster(draft)
        self._heat[cluster] = max(0.0, self._heat.get(cluster, 0.0) - self._risk_r(draft))
