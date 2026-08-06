"""Deterministic risk gate (CANDIDATE_LIFECYCLE_SPEC section 6).

Risk preferences are HARD CONSTRAINTS, not reward penalties (LEARNING_PROTOCOL
section 4): admission is a deterministic rule, never a learned component, and
a forbidden action is rejected, not punished.

Policy (provisional baseline, approved 2026-08-01):
- Heat is the sum of per-position risk in R = size * stop_r (RM-01). With
  fixed 1R geometry at size 1.0 this equals the number of open positions and
  is byte-identical to the pre-size gate.
- Correlated clusters are a FIXED instrument list — no rolling estimation
  (DeMiguel et al. 2009: estimation error is what kills allocation models).
- On cap breach the new Candidate is REJECTED (CAPACITY_REJECTED), never
  downsized: downsizing would silently enter the deferred ranker gate
  (OPEN_DECISIONS O-006/O-012).
- O-016 drawdown-conditioned sizing (equity.RiskState, RM-06): at -30%/-50%
  drawdown the effective size is halved/quartered and stop_r doubled/
  quadrupled. size*stop_r is invariant, so the 3.0/2.0 caps (O-018) and every
  admission decision are unchanged — the ladder is pure sizing, its evidence
  lives in the equity diagnostics, never in admission.
- RM-04 risk-freeing hook: a position whose stop rolled to breakeven moves to
  the reported opportunity pool (EXEC-1 call site; dormant until EXEC-1
  lands, so admission is byte-identical today).
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import CandidateDraft
from .lifecycle import ExposureBook
from .equity import RiskState

# Funding boundaries are integer-hour UTC divisible by funding_hours
# (SIMULATION_TRUTH_SPEC: the simulator settles at absolute hour marks,
# independent of bar interval). The veto must measure the SAME schedule.
HOUR_NS = 3_600_000_000_000

DEFAULT_CLUSTERS = {
    'BTCUSDT': 'btc', 'ETHUSDT': 'btc',
    'SOLUSDT': 'major', 'BNBUSDT': 'major', 'XRPUSDT': 'major', 'DOGEUSDT': 'major',
}

# D-024 (CANDIDATE_LIFECYCLE_SPEC section 6.3): data-plane integrity veto,
# distinct from the capacity/heat rejections below. Kept counterfactual.
TRADABILITY_MASK_VETO = 'TRADABILITY_MASK_VETO'


def tradability_mask_veto(bar: dict, state_quality: str, entry_fill_time_ns: int, *,
                          max_bar_range_frac: float, funding_window_bars: int,
                          funding_hours: int, interval_ns: int,
                          ) -> tuple[bool, str | None]:
    """Deterministic D-024 vetoes; data-plane, not a regime filter.

    Pure function of the entry bar and the frozen manifest constants: no
    degrees of freedom, no fitting, no learned component. Returns
    (vetoed, reason) with reason one of 'BAR_RANGE' | 'DEGRADED' |
    'FUNDING_WINDOW' | None. 'BAR_RANGE' fires on the entry bar's
    (high-low)/close — an intrabar range, NOT a bid-ask spread; the tape
    carries no depth. It was reported as 'SPREAD' until 2026-08-04.

    Funding window: a boundary B with 0 < B - fill <= window means the first
    post-entry step crosses B and books funding immediately, so the entry is
    vetoed. `entry_fill_time_ns` is the AVAILABLE time of the entry bar (the
    fill clock, close + latency), NOT the close time: the bar ending exactly on
    B is not vetoed because its fill happens after B settled, and a bar closing
    at B-latency has its fill after B too. Measuring from event_time (close)
    would falsely veto entries whose fill already cleared the boundary.
    """
    high, low, close = float(bar['high']), float(bar['low']), float(bar['close'])
    if close <= 0 or (high - low) / close > max_bar_range_frac:
        return True, 'BAR_RANGE'
    if state_quality == 'DEGRADED':
        return True, 'DEGRADED'
    if funding_hours > 0 and funding_window_bars > 0 and interval_ns > 0:
        # Boundary spacing is WALL-CLOCK hours (funding_hours * 1h), matching
        # simulator._boundaries_crossed (absolute hour marks), NOT funding_hours
        # times the bar interval. On a 4h tape the old period (32h) missed 3 of
        # 4 imminent-boundary closes the simulator would settle one bar later.
        period = funding_hours * HOUR_NS
        window = funding_window_bars * interval_ns
        # When window >= period there is ALWAYS a boundary B with
        # 0 < B - fill <= window, so every entry books funding on its first
        # post-entry step — the veto must fire, not silently disable itself
        # (the old `window < period` guard skipped the whole check, so e.g. 1d
        # bars with funding_hours=8 admitted every entry that settled 3x).
        remainder = entry_fill_time_ns % period
        if remainder >= period - window:
            return True, 'FUNDING_WINDOW'
    return False, None


@dataclass(frozen=True)
class RiskVerdict:
    ok: bool
    reason_code: str | None = None
    detail: str | None = None
    # RISK-2 (O-016): the EFFECTIVE size and stop_r after the drawdown ladder
    # (equity.RiskState) — what the executed OpenPosition is actually sized
    # at. size*stop_r is invariant under the ladder (f*g == 1), so these never
    # change an admission decision; they are the sizing record for the lab.
    size: float = 1.0
    stop_r: float = 1.0


class RiskGate:
    def __init__(self, max_heat: float = 3.0, max_cluster_heat: float = 2.0,
                 clusters: dict[str, str] | None = None,
                 equity: RiskState | None = None):
        self._book = ExposureBook()
        self.max_heat = max_heat
        self.max_cluster_heat = max_cluster_heat
        self.clusters = clusters or DEFAULT_CLUSTERS
        # O-016 drawdown-conditioned sizing state (equity.py). When present,
        # admit() applies its f(dd)/g(dd) multipliers to size/stop_r; because
        # the product is invariant, the D-023 heat caps (3.0/2.0, O-018) and
        # every admission decision are byte-identical to the equity-free gate.
        # The lab wires a RiskState fed from realized net_r (episode order).
        self.equity = equity
        self._heat: dict[str, float] = {}
        # RM-04 (O-013): risk-freed positions move from the capped capital
        # pool to the reported opportunity pool; reported, never capped.
        self._opportunity_heat: dict[str, float] = {}
        # Per-exposure heat contribution (instrument, direction) -> size*stop_r
        # at admit time, so release/risk_free subtract exactly what was added
        # even if the drawdown multipliers moved in between.
        self._pos_heat: dict[tuple[str, str], float] = {}
        self._freed: set[tuple[str, str]] = set()

    def _effective_size(self, draft: CandidateDraft) -> float:
        size = draft.size
        if self.equity is not None:
            size *= self.equity.size_multiplier()
        return size

    def _effective_stop_r(self, draft: CandidateDraft) -> float:
        stop_r = float(draft.risk_geometry.get('stop_r', 1.0))
        if self.equity is not None:
            stop_r *= self.equity.stop_multiplier()
        return stop_r

    def _heat_units(self, draft: CandidateDraft) -> float:
        """Portfolio heat contribution: size * stop_r (RM-01; D-023). With the
        drawdown ladder the product is invariant (f*g == 1), so the heat of a
        sized position is exactly its declared size * stop_r."""
        return self._effective_size(draft) * self._effective_stop_r(draft)

    def _cluster(self, draft: CandidateDraft) -> str:
        return self.clusters.get(draft.instrument, 'other')

    def admit(self, draft: CandidateDraft) -> RiskVerdict:
        if not self._book.acquire(draft.instrument, draft.direction):
            return RiskVerdict(False, 'EXISTING_EXPOSURE_CONFLICT')
        heat = self._heat_units(draft)
        eff_size = self._effective_size(draft)
        eff_stop_r = self._effective_stop_r(draft)
        cluster = self._cluster(draft)
        if self._heat.get(cluster, 0.0) + heat > self.max_cluster_heat:
            self._book.release(draft.instrument, draft.direction)
            return RiskVerdict(False, 'PORTFOLIO_HEAT_EXCEEDED', f'cluster:{cluster}',
                               eff_size, eff_stop_r)
        if sum(self._heat.values()) + heat > self.max_heat:
            self._book.release(draft.instrument, draft.direction)
            return RiskVerdict(False, 'PORTFOLIO_HEAT_EXCEEDED', 'total',
                               eff_size, eff_stop_r)
        self._heat[cluster] = self._heat.get(cluster, 0.0) + heat
        self._pos_heat[(draft.instrument, draft.direction)] = heat
        return RiskVerdict(True, size=eff_size, stop_r=eff_stop_r)

    def risk_free(self, instrument: str, direction: str) -> None:
        """RM-04 risk-freeing hook: move an open exposure's heat from the
        capped capital pool to the reported opportunity pool. A position whose
        stop has rolled to breakeven can only lose opportunity risk, so it no
        longer consumes capital-heat capacity (RM-04; the book's transform of
        capital risk into opportunity risk). DORMANT: EXEC-1's breakeven roll
        now exists in the simulator (OpenPosition.stop_rolled), but the lab
        does not call this hook, and wiring it changes what D-023's heat cap
        is OVER (a risk-freed position's stop sits at breakeven but can still
        gap through to a loss) — a register decision revising D-023's domain
        plus a gap-through-breakeven quantification are required first
        (CRIT-2.6). Until then admission is byte-identical to the pre-hook
        gate and the 3.0/2.0 caps are untouched (O-018); only the pool the
        heat is counted in would move.
        """
        key = (instrument, direction)
        heat = self._pos_heat.get(key)
        if heat is None:
            return
        cluster = self.clusters.get(instrument, 'other')
        self._heat[cluster] = max(0.0, self._heat.get(cluster, 0.0) - heat)
        self._opportunity_heat[cluster] = \
            self._opportunity_heat.get(cluster, 0.0) + heat
        self._freed.add(key)

    def opportunity_heat(self) -> float:
        """RM-04 reported opportunity pool (risk-freed positions). Reported,
        never capped (O-018 unchanged)."""
        return sum(self._opportunity_heat.values())

    def release(self, draft: CandidateDraft) -> None:
        self._book.release(draft.instrument, draft.direction)
        cluster = self._cluster(draft)
        key = (draft.instrument, draft.direction)
        heat = self._pos_heat.pop(key, None)
        if heat is None:
            heat = self._heat_units(draft)      # invariant, so exact
        if key in self._freed:
            self._freed.discard(key)
            self._opportunity_heat[cluster] = \
                max(0.0, self._opportunity_heat.get(cluster, 0.0) - heat)
        else:
            self._heat[cluster] = max(0.0, self._heat.get(cluster, 0.0) - heat)
