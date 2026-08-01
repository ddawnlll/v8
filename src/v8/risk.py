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

# D-024 (CANDIDATE_LIFECYCLE_SPEC section 6.3): data-plane integrity veto,
# distinct from the capacity/heat rejections below. Kept counterfactual.
TRADABILITY_MASK_VETO = 'TRADABILITY_MASK_VETO'


def tradability_mask_veto(bar: dict, state_quality: str, close_time_ns: int, *,
                          max_spread_frac: float, funding_window_bars: int,
                          funding_hours: int, interval_ns: int,
                          ) -> tuple[bool, str | None]:
    """Deterministic D-024 vetoes; data-plane, not a regime filter.

    Pure function of the entry bar and the frozen manifest constants: no
    degrees of freedom, no fitting, no learned component. Returns
    (vetoed, reason) with reason one of 'SPREAD' | 'DEGRADED' |
    'FUNDING_WINDOW' | None.

    Funding window: a boundary B with 0 < B - close <= window means the first
    post-entry step crosses B and books funding immediately, so the entry is
    vetoed. The bar ending EXACTLY on B is not vetoed: its fill happens after
    B settled (open-interval start, Step 2 boundary golden), so it enters with
    the next settlement `funding_hours` away.
    """
    high, low, close = float(bar['high']), float(bar['low']), float(bar['close'])
    if close <= 0 or (high - low) / close > max_spread_frac:
        return True, 'SPREAD'
    if state_quality == 'DEGRADED':
        return True, 'DEGRADED'
    if funding_hours > 0 and funding_window_bars > 0 and interval_ns > 0:
        period = funding_hours * interval_ns
        window = funding_window_bars * interval_ns
        if window < period:
            remainder = close_time_ns % period
            if remainder >= period - window:
                return True, 'FUNDING_WINDOW'
    return False, None


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
