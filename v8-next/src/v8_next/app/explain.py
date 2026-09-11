"""Per-trade explanation: which domain the loss belongs to, and what the counterfactual is.

Uses the ported oracle vocabulary, so the answer is a typed outcome rather than prose:

* the failure is charged to one of the seven disjoint domains (conservation-checked);
* the counterfactual under the **other bracket contract** is reported as
  ``MODEL_DERIVED`` - it is a model of what the same decision would have done, and it says so;
* the fill-price counterfactual is refused with ``NON_IDENTIFIABLE_FILL`` because the tape
  carries no mark price and no book: the honest answer there is a refusal, not a number.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from v8_next.adapters.swing_engine import SwingEngineConfig, SwingEngineStrategy
from v8_next.economics.grammar import POLICY_REQUIRED_BARS
from v8_next.economics.swing_baseline import (
    SHARED_CONTRACT,
    policy_spec,
    replay_bracket,
    swing_signal,
)
from v8_next.evaluation.multitape import load_multitape
from v8_next.oracle import (
    AuthorityLevel,
    CounterfactualAuthority,
    Identifiability,
    OracleOutcome,
    OracleRefusal,
)
from v8_next.system_proving import FailureDomain
from v8_next.system_proving.attribution import classify_exit_failure

HOUR_NS = 3_600 * 10**9


def _authority(level: Identifiability, *, support_rule: str, assumptions: tuple[str, ...]) -> CounterfactualAuthority:
    return CounterfactualAuthority(
        oracle_authority_level=AuthorityLevel.L2,
        identifiability_status=level,
        support_rule_id=support_rule,
        environment_model_id="candle-replay-v1",
        assumptions=assumptions,
    )


def explain_trade(*, repo_root: Path, policy_id: str, index: int, tape_rel: str) -> dict[str, Any]:
    tape_path = repo_root / tape_rel
    tape = load_multitape(tape_path)
    series = list(tape.candles["BTCUSDT"])
    instrument_id = series[0].instrument_id
    spec = policy_spec(policy_id)
    warmup = int(POLICY_REQUIRED_BARS[spec.grammar_policy])
    has_bracket_policy = spec.protection_policy not in (None, "timeout-only-v1")

    cfg = SwingEngineConfig(policy_id=policy_id, instrument_id=instrument_id,
                            bar_type_str=f"{instrument_id}-1-HOUR-LAST-EXTERNAL")
    framing = SwingEngineStrategy(cfg, {i: c for i, c in enumerate(series)}, warmup_bars=10**9)
    frames = []
    for position, candle in enumerate(series):
        framing.on_bar(SimpleNamespace(ts_event=position))  # type: ignore[arg-type]
        frames.append(framing._decision_frame(candle))

    taker = Decimal(SHARED_CONTRACT["taker_fee"])
    cursor = warmup
    seen = -1
    while cursor < len(series) - 1:
        decision = swing_signal(frames[cursor], spec, bar_ns=HOUR_NS)
        if decision is None:
            cursor += 1
            continue
        seen += 1
        if seen != index:
            cursor += 1
            continue
        bracketless = Decimal(decision.stop_price) == Decimal(decision.entry_reference)
        actual = replay_bracket(decision, series[cursor + 1 :], bar_ns=HOUR_NS, bps_fee=taker,
                               has_bracket=has_bracket_policy)
        alternate_contract = replay_bracket(decision, series[cursor + 1 :], bar_ns=HOUR_NS,
                                           bps_fee=taker, has_bracket=not (has_bracket_policy and not bracketless))
        domain = (
            classify_exit_failure(
                exit_kind=actual.exit_kind, net_return=actual.net_return,
                has_bracket=has_bracket_policy and not bracketless,
            )
            if actual.net_return < 0
            else None
        )
        modelled = _authority(
            Identifiability.MODEL_DERIVED,
            support_rule="declared bracket contract toggled",
            assumptions=(
                "candle-only data",
                "declared SNU resolution: when one bar touches both legs the stop is taken first",
                f"bracket contract {'declared by the policy name' if has_bracket_policy else 'absent (timeout-only)'}",
            ),
        )
        counterfactual = OracleOutcome.model_derived(
            actual.net_return,
            min(actual.net_return, alternate_contract.net_return),
            max(actual.net_return, alternate_contract.net_return),
            modelled,
        )
        fill_authority = _authority(
            Identifiability.NOT_IDENTIFIABLE,
            support_rule="fill-price counterfactual",
            assumptions=("no mark price and no order book in the tape",),
        )
        fill_counterfactual = OracleOutcome.unknown(
            OracleRefusal.NON_IDENTIFIABLE_FILL, fill_authority
        )
        return {
            "policy_id": policy_id,
            "index": index,
            "decision_ns": int(decision.decision_ns),
            "direction": decision.direction,
            "bracketless_decision": bracketless,
            "actual": {
                "exit_kind": actual.exit_kind,
                "bars_held": actual.bars_held,
                "net_return": actual.net_return,
                "gross_return": actual.gross_return,
                "fee_cost_return": actual.fee_cost_return,
                "gap_through_stop": actual.gap_through_stop,
            },
            "failure_domain": None if domain is None else FailureDomain(domain).value,
            "domain_rule": "EXIT = no bracket carried; SELECTION = target/expiry; EXECUTION = bracketed and still lost",
            "counterfactual_other_bracket_contract": counterfactual.as_dict(),
            "counterfactual_fill_price": fill_counterfactual.as_dict(),
        }
    raise IndexError(f"policy {policy_id!r} has no campaign at index {index}")

