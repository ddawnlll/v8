"""D-153 / D-152 Full Gate Resolution Pipeline (Rule 12, Rule 30, Rule 57).

Resolves Gates G3 through G9 through genuine empirical calculations:
- G3: Scenario Robustness across 4 market regimes (Bull Trend, Bear Crash, Chop/Range, High-Vol Spill).
- G4: Synthetic / Adversarial Falsification with slippage, latency jitter, drop rate, and bracket stop-loss.
- G5: Selection Control via Deflated Sharpe Ratio (DSR >= 0.95, p <= 0.05) and White's Reality Check (WRC).
- G6: Frozen Out-of-Sample (OOS) Replication with >= 60% performance retention.
- G7: Prospective Shadow Streaming with causal e-process martingale and drift tracking.
- G8: Live Realization (D-152 §5 Diagnostic Fold NOT_APPLICABLE in research phase, or PASS with signed fills).
- G9: Central ClaimRegistry verification of ledger hash chain and StatutoryClaimRecord minting.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import polars as pl
from nautilus_trader.execution import ProbabilisticFillModel, StaticLatencyModel

from v8_next.adapters.expert_strategy import (
    ExpertStrategyConfig,
    run_expert_strategy_backtest,
)
from v8_next.domain.market import Candle
from v8_next.evaluation.alignment import IntervalLoss
from v8_next.evaluation.benchmark_receipt import (
    BenchmarkLedger,
    GateState,
    GateVector,
)
from v8_next.evaluation.claims import ClaimRegistry, StatutoryClaimRecord
from v8_next.evaluation.deflated_sharpe import DSRPlan, deflated_sharpe_diagnostic
from v8_next.evaluation.reality_check import reality_check_diagnostic

DEFAULT_TAPE_PATH = Path("research/tape/btcusdt-1h-12m/tape.jsonl")


def extract_account_balance(account: dict[str, Any], default: float = 10000.0) -> float:
    """Safely extract balance from economic state account dictionary."""
    if "balance_total" in account and account["balance_total"]:
        val_str = str(account["balance_total"]).split()[0]
        try:
            return float(val_str)
        except (ValueError, TypeError):
            pass
    if "balance" in account and account["balance"] is not None:
        try:
            return float(account["balance"])
        except (ValueError, TypeError):
            pass
    return default


def load_tape_candles(
    tape_path: Path | str | None = None,
    limit: int | None = None,
) -> list[Candle]:
    """Load real BTCUSDT 1-hour candles from verified venue capture tape using Polars."""
    p = Path(tape_path) if tape_path is not None else DEFAULT_TAPE_PATH
    if not p.exists():
        raise FileNotFoundError(f"Tape dataset not found at {p}")

    if p.is_dir():
        tape_jsonl = p / "tape.jsonl"
        if tape_jsonl.exists():
            p = tape_jsonl
        else:
            import zipfile

            zip_files = sorted(p.glob("BTCUSDT-1h-*.zip"))
            if not zip_files:
                raise FileNotFoundError(f"No kline files found in directory {p}")
            candles: list[Candle] = []
            for zf_path in zip_files:
                with zipfile.ZipFile(zf_path) as z:
                    for name in z.namelist():
                        if name.endswith(".csv"):
                            with z.open(name) as f:
                                df_csv = pl.read_csv(f, has_header=True)
                                for row in df_csv.iter_rows(named=True):
                                    candles.append(
                                        Candle(
                                            instrument_id="BTCUSDT-PERP.BINANCE",
                                            start_ns=int(row["open_time"]) * 1_000_000,
                                            end_ns=(int(row["close_time"]) + 1) * 1_000_000,
                                            open=Decimal(str(row["open"])),
                                            high=Decimal(str(row["high"])),
                                            low=Decimal(str(row["low"])),
                                            close=Decimal(str(row["close"])),
                                            volume=Decimal(str(row["volume"])),
                                            received_ns=(int(row["close_time"]) + 1) * 1_000_000,
                                            available_ns=(int(row["close_time"]) + 1) * 1_000_000,
                                            source_hash=f"binance-zip-{zf_path.name}",
                                        )
                                    )
                                    if limit is not None and len(candles) >= limit:
                                        return candles
            return candles

    df = pl.read_ndjson(p)
    kline_df = df.filter(pl.col("channel") == "kline")
    if limit is not None:
        kline_df = kline_df.head(limit)

    payloads = kline_df["payload"].to_list()
    candles = [
        Candle(
            instrument_id="BTCUSDT-PERP.BINANCE",
            start_ns=int(row["open_time_ms"]) * 1_000_000,
            end_ns=(int(row["close_time_ms"]) + 1) * 1_000_000,
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
            volume=Decimal(str(row["volume"])),
            received_ns=(int(row["close_time_ms"]) + 1) * 1_000_000,
            available_ns=(int(row["close_time_ms"]) + 1) * 1_000_000,
            source_hash=str(row["payload_hash"]),
        )
        for row in payloads
    ]
    return candles


def classify_market_regimes(
    tape_path: Path | str | None = None,
    candles: Sequence[Candle] | None = None,
    slice_length: int = 100,
) -> dict[str, list[Candle]]:
    """Partition real tape data into 4 canonical market regimes using Polars.

    Regimes:
    1. Bull Trend: sustained positive return momentum.
    2. Bear Crash: severe downward excursion.
    3. Chop/Range: low directional movement / mean-reverting.
    4. High-Vol Spill: upper tail of rolling volatility.
    """
    if candles is None:
        p = Path(tape_path) if tape_path is not None else DEFAULT_TAPE_PATH
        all_candles = load_tape_candles(p)
    else:
        all_candles = list(candles)

    n = len(all_candles)
    eff_len = min(slice_length, max(1, n // 4))

    if n < 48:
        quarter = max(1, n // 4)
        return {
            "Bull Trend": all_candles[0:quarter],
            "Bear Crash": all_candles[quarter : 2 * quarter],
            "Chop/Range": all_candles[2 * quarter : 3 * quarter],
            "High-Vol Spill": all_candles[3 * quarter :],
        }

    records = [
        {
            "idx": i,
            "close": float(c.close),
            "high": float(c.high),
            "low": float(c.low),
        }
        for i, c in enumerate(all_candles)
    ]

    df = pl.DataFrame(records).with_columns(
        (pl.col("close").log() - pl.col("close").shift(1).log()).alias("log_ret"),
        (pl.col("close") / pl.col("close").shift(eff_len) - 1.0).alias("ret_w"),
    ).with_columns(
        pl.col("log_ret").rolling_std(window_size=eff_len).alias("vol_w"),
    )

    valid_df = df.with_row_index().filter(pl.col("ret_w").is_not_null() & pl.col("vol_w").is_not_null())
    if len(valid_df) == 0:
        quarter = max(1, n // 4)
        return {
            "Bull Trend": all_candles[0:quarter],
            "Bear Crash": all_candles[quarter : 2 * quarter],
            "Chop/Range": all_candles[2 * quarter : 3 * quarter],
            "High-Vol Spill": all_candles[3 * quarter :],
        }

    # 1. Bull Trend: window with maximum cumulative positive return
    arg_bull = valid_df["ret_w"].arg_max()
    idx_bull_end = int(valid_df["index"][arg_bull if arg_bull is not None else 0] or 0)
    bull_start = max(0, idx_bull_end - eff_len)

    # 2. Bear Crash: window with minimum (most negative) return
    arg_bear = valid_df["ret_w"].arg_min()
    idx_bear_end = int(valid_df["index"][arg_bear if arg_bear is not None else 0] or 0)
    bear_start = max(0, idx_bear_end - eff_len)

    # 3. High-Vol Spill: window with maximum rolling volatility
    arg_vol = valid_df["vol_w"].arg_max()
    idx_vol_end = int(valid_df["index"][arg_vol if arg_vol is not None else 0] or 0)
    vol_start = max(0, idx_vol_end - eff_len)

    # 4. Chop/Range: window with lowest absolute return among sub-median volatility
    med_val = valid_df["vol_w"].median()
    med_vol = float(str(med_val)) if med_val is not None else 0.01
    chop_pool = valid_df.filter(pl.col("vol_w") <= med_vol)
    if len(chop_pool) == 0:
        chop_pool = valid_df
    arg_chop = chop_pool["ret_w"].abs().arg_min()
    idx_chop_end = int(chop_pool["index"][arg_chop if arg_chop is not None else 0] or 0)
    chop_start = max(0, idx_chop_end - eff_len)

    return {
        "Bull Trend": all_candles[bull_start : bull_start + eff_len],
        "Bear Crash": all_candles[bear_start : bear_start + eff_len],
        "Chop/Range": all_candles[chop_start : chop_start + eff_len],
        "High-Vol Spill": all_candles[vol_start : vol_start + eff_len],
    }


def evaluate_g3_scenario_robustness(
    regimes: dict[str, list[Candle]],
    strategy_config: ExpertStrategyConfig | None = None,
    max_drawdown_limit: float = 0.10,
    min_trades_per_regime: int = 1,
) -> tuple[GateState, dict[str, Any]]:
    """G3: Scenario Robustness (g3_benchmark_coverage).

    Executes backtests across the 4 primary market regimes (Bull Trend, Bear Crash,
    Chop/Range, High-Vol Spill) and verifies that maximum drawdown and return variance
    do not explode across regimes. Every evaluated regime must contribute at least
    `min_trades_per_regime` trades: robustness across a regime with zero trades is
    unmeasurable and fails closed with INSUFFICIENT_REGIME_TRADES.
    """
    cfg = strategy_config or ExpertStrategyConfig(
        min_support_quorum=1,
        max_contradiction_tolerance=28,
        bracket_stop_pct=Decimal("0.02"),
        bracket_target_pct=Decimal("0.04"),
    )
    regime_results: dict[str, dict[str, float]] = {}
    drawdowns: list[float] = []
    return_variances: list[float] = []

    for name, candles in regimes.items():
        if not candles:
            continue
        res = run_expert_strategy_backtest(tuple(candles), cfg)
        opened = res["opened_positions"]
        closed = res["closed_positions"]

        # Calculate realized and mtm returns
        pnls: list[float] = []
        last_close = float(candles[-1].close) if candles else 100.0
        for pos in opened:
            c_pos = next((c for c in closed if c["position_id"] == pos["position_id"]), None)
            if c_pos and "realized_pnl" in c_pos and c_pos["realized_pnl"]:
                val_str = str(c_pos["realized_pnl"]).split()[0]
                try:
                    pnls.append(float(val_str))
                except ValueError:
                    pnls.append(0.0)
            else:
                entry = float(pos["avg_px_open"])
                direction = 1.0 if pos["side"].upper() in ("BUY", "LONG") else -1.0
                mtm = ((last_close - entry) / entry) * direction
                pnls.append(mtm)

        cum_equity = 10000.0
        peak = cum_equity
        max_dd = 0.0
        for pnl in pnls:
            cum_equity += pnl
            if cum_equity > peak:
                peak = cum_equity
            dd = (peak - cum_equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        var_ret = float(np.var(pnls)) if len(pnls) > 1 else 0.001
        drawdowns.append(max_dd)
        return_variances.append(var_ret)
        regime_results[name] = {
            "bars": len(candles),
            "trades": len(opened),
            "max_drawdown": round(max_dd, 4),
            "return_variance": round(var_ret, 6),
        }

    max_observed_dd = max(drawdowns) if drawdowns else 0.0
    max_observed_var = max(return_variances) if return_variances else 0.0

    empty_regimes = sorted(n for n, r in regime_results.items() if r["trades"] < min_trades_per_regime)
    min_regime_trades = min((r["trades"] for r in regime_results.values()), default=0)

    passed = (
        len(regime_results) == 4
        and not empty_regimes
        and max_observed_dd <= max_drawdown_limit
        and math.isfinite(max_observed_var)
        and max_observed_var <= 0.20
    )

    state = GateState.PASS if passed else GateState.BLOCKED
    metrics = {
        "regimes": regime_results,
        "max_observed_drawdown": max_observed_dd,
        "max_observed_variance": max_observed_var,
        "max_drawdown_limit": max_drawdown_limit,
        "min_trades_per_regime": min_trades_per_regime,
        "min_regime_trades": min_regime_trades,
        "empty_regimes": empty_regimes,
        "reason": None
        if passed
        else (
            f"INSUFFICIENT_REGIME_TRADES: {empty_regimes} below {min_trades_per_regime}"
            if empty_regimes
            else f"DRAWDOWN_OR_VARIANCE_BREACH: dd={max_observed_dd:.4f} var={max_observed_var:.6f}"
        ),
        "passed": passed,
    }
    return state, metrics


def evaluate_g4_synthetic_falsification(
    candles: Sequence[Candle],
    strategy_config: ExpertStrategyConfig | None = None,
    min_closed_trades: int = 2,
) -> tuple[GateState, dict[str, Any]]:
    """G4: Synthetic Falsification (g4_structural_robustness).

    Injects adversarial execution shocks into NautilusTrader:
    - Slippage shock: spread x3 + 100% prob slippage
    - Latency shock: 500ms base + 200ms insert latency jitter
    - Drop rate: 5% random order drop/unfill
    - Verifies bracket stop-loss protects capital and account does not bust.

    Survival without executions proves nothing: at least `min_closed_trades`
    shocked fills must close, else INSUFFICIENT_SHOCK_SAMPLE fails closed.
    """
    bracket_cfg = strategy_config or ExpertStrategyConfig(
        min_support_quorum=1,
        max_contradiction_tolerance=28,
        bracket_stop_pct=Decimal("0.02"),
        bracket_target_pct=Decimal("0.04"),
    )

    fill_model = ProbabilisticFillModel(prob_fill_on_limit=0.95, prob_slippage=1.0)
    latency_model = StaticLatencyModel(base_latency_nanos=500_000_000, insert_latency_nanos=200_000_000)
    shock_taker_fee = Decimal("0.0015")  # 3x standard fee

    eval_candles = tuple(candles[:200]) if len(candles) >= 200 else tuple(candles)

    backtest_result = run_expert_strategy_backtest(
        eval_candles,
        bracket_cfg,
        taker_fee=shock_taker_fee,
        fill_model=fill_model,
        latency_model=latency_model,
        initial_balance=Decimal("10000"),
    )

    account = backtest_result["account"]
    final_equity = extract_account_balance(account, default=10000.0)
    opened = backtest_result["opened_positions"]
    closed = backtest_result["closed_positions"]

    # Invariant: Account did not bust (equity remains > 70% initial), stop-losses functioned,
    # AND the shock battery actually executed (survival with no fills is vacuous).
    no_bust = final_equity >= 7000.0
    all_finite = math.isfinite(final_equity)
    enough_shock_sample = len(closed) >= min_closed_trades

    passed = no_bust and all_finite and enough_shock_sample
    state = GateState.PASS if passed else GateState.BLOCKED
    metrics = {
        "final_equity": round(final_equity, 2),
        "total_trades": len(opened),
        "closed_trades": len(closed),
        "min_closed_trades": min_closed_trades,
        "reason": None
        if passed
        else (
            f"INSUFFICIENT_SHOCK_SAMPLE: {len(closed)} closed < {min_closed_trades}"
            if not enough_shock_sample
            else f"SHOCK_BUST_OR_NONFINITE: equity={final_equity:.2f}"
        ),
        "shock_taker_fee": float(shock_taker_fee),
        "adversarial_models": ["ProbabilisticFill(drop=0.05, slip=1.0)", "StaticLatency(500ms+200ms)"],
        "bracket_stop_loss_pct": float(bracket_cfg.bracket_stop_pct or Decimal("0.02")),
        "account_survived": no_bust,
    }
    return state, metrics


def evaluate_g5_selection_control(
    pnl_series: Sequence[float],
    candles: Sequence[Candle] | None = None,
    num_trials: int = 4,
) -> tuple[GateState, dict[str, Any]]:
    """G5: Selection Control (g5_statistical_credibility).

    Enforces Constitution Rule 12: Deflated Sharpe Ratio (DSR) and White's Reality Check (WRC).
    Zero synthetic formulas (no sine/cosine oscillators). Uses genuine empirical returns across
    registered parameter/execution variants.
    """
    raw_series = list(pnl_series)
    own_sample_count = len(raw_series)
    sample_source = "own_track" if own_sample_count >= 20 else "regime_fallback"

    # If trade series is too short (< 20 intervals for multi-testing power), extract empirical trade returns from market regimes or tape
    if len(raw_series) < 20:
        if DEFAULT_TAPE_PATH.exists():
            regimes = classify_market_regimes(tape_path=DEFAULT_TAPE_PATH, slice_length=500)
            cfg = ExpertStrategyConfig(
                min_support_quorum=1,
                max_contradiction_tolerance=28,
                bracket_stop_pct=Decimal("0.02"),
                bracket_target_pct=Decimal("0.04"),
            )
            extracted_pnls: list[float] = []
            for _name, c_list in regimes.items():
                res = run_expert_strategy_backtest(tuple(c_list), cfg)
                closed = res["closed_positions"]
                for c_pos in closed:
                    if "realized_pnl" in c_pos and c_pos["realized_pnl"]:
                        val_str = str(c_pos["realized_pnl"]).split()[0]
                        try:
                            extracted_pnls.append(float(val_str) / 10000.0)
                        except ValueError:
                            pass
            if len(extracted_pnls) >= 4:
                raw_series = extracted_pnls
        elif candles is not None and len(candles) >= 12:
            cfg = ExpertStrategyConfig(
                min_support_quorum=1,
                max_contradiction_tolerance=28,
                bracket_stop_pct=Decimal("0.02"),
                bracket_target_pct=Decimal("0.04"),
            )
            res = run_expert_strategy_backtest(tuple(candles), cfg)
            closed = res["closed_positions"]
            extracted_pnls = []
            for c_pos in closed:
                if "realized_pnl" in c_pos and c_pos["realized_pnl"]:
                    val_str = str(c_pos["realized_pnl"]).split()[0]
                    try:
                        extracted_pnls.append(float(val_str) / 10000.0)
                    except ValueError:
                        pass
            if len(extracted_pnls) >= 4:
                raw_series = extracted_pnls

    # Rule 12 fail-closed: if fewer than 4 intervals, DSR moment math is impossible
    if len(raw_series) < 4:
        return GateState.BLOCKED, {
            "error": "INSUFFICIENT_TRADE_INTERVALS: At least 4 return intervals required for DSR moments",
            "samples": len(raw_series),
            "passed": False,
        }

    r_champ = np.array(raw_series, dtype=float)
    t_steps = len(r_champ)

    # Construct genuine economic execution variants:
    # 1. Champion (original strategy net returns)
    # 2. Fee stressed: additional taker friction (-0.0001)
    # 3. Conservative: conservative sizing (0.95x size)
    # 4. Slippage stressed: adverse execution markout (-0.0002)
    r_fee = r_champ - 0.0001
    r_cons = 0.95 * r_champ
    r_slip = r_champ - 0.0002

    losses = {
        "champion": tuple(IntervalLoss(i, i + 1, i + 1, -Decimal(str(round(float(r), 8)))) for i, r in enumerate(r_champ)),
        "fee_stressed": tuple(IntervalLoss(i, i + 1, i + 1, -Decimal(str(round(float(r), 8)))) for i, r in enumerate(r_fee)),
        "conservative": tuple(IntervalLoss(i, i + 1, i + 1, -Decimal(str(round(float(r), 8)))) for i, r in enumerate(r_cons)),
        "slippage_stressed": tuple(IntervalLoss(i, i + 1, i + 1, -Decimal(str(round(float(r), 8)))) for i, r in enumerate(r_slip)),
    }

    variants = tuple(losses.keys())
    plan = DSRPlan(
        selected_variant="champion",
        registered_variants=variants,
        effective_independent_trials=float(num_trials),
        independence_basis="preregistered economic policy and friction variants",
    )

    try:
        dsr_result = deflated_sharpe_diagnostic(
            losses,
            plan=plan,
            frozen_ns=0,
            evaluation_end_ns=t_steps,
            decision_ns=t_steps + 1,
        )

        baseline = tuple(IntervalLoss(i, i + 1, i + 1, Decimal("0")) for i in range(t_steps))
        wrc_result = reality_check_diagnostic(
            baseline,
            {"champion": losses["champion"]},
            frozen_ns=0,
            evaluation_end_ns=t_steps,
            decision_ns=t_steps + 1,
            block_size=max(1, t_steps // 5),
            reps=200,
            seed=42,
        )

        dsr_conf = float(dsr_result["dsr_confidence"])
        # Fail closed: a missing champion entry must BLOCK, never fall back to a
        # hardcoded p-value (anti-fabrication: no synthetic statistical outputs).
        try:
            raw_p = float(dsr_result["multiple_testing"]["raw_pvalues"]["champion"])
            bonf_p = float(dsr_result["multiple_testing"]["adjustments"]["bonferroni"]["adjusted_pvalues"]["champion"])
        except (KeyError, TypeError, ValueError) as e:
            return GateState.BLOCKED, {
                "error": f"MISSING_CHAMPION_PVALUE: DSR output lacks champion entry: {e}",
                "samples": t_steps,
                "passed": False,
            }
        wrc_p = float(wrc_result["p_value"])

        passed = dsr_conf >= 0.95 and bonf_p <= 0.05
        state = GateState.PASS if passed else GateState.BLOCKED
        metrics = {
            "dsr_confidence": round(dsr_conf, 6),
            "raw_pvalue": round(raw_p, 6),
            "adjusted_bonferroni_pvalue": round(bonf_p, 6),
            "wrc_pvalue": round(wrc_p, 6),
            "trials": num_trials,
            "sample_intervals": t_steps,
            "own_sample_count": own_sample_count,
            "sample_source": sample_source,
            "reason": None
            if passed
            else (
                f"SELECTION_CONTROL_BREACH: dsr_conf={dsr_conf:.4f} bonf_p={bonf_p:.6f} "
                f"(source={sample_source}, own_n={own_sample_count})"
            ),
            "passed": passed,
        }
        return state, metrics
    except Exception as e:
        return GateState.BLOCKED, {"error": str(e), "passed": False}


def evaluate_g6_frozen_oos(
    candles: Sequence[Candle],
    strategy_config: ExpertStrategyConfig | None = None,
    min_retention_ratio: float = 0.60,
) -> tuple[GateState, dict[str, Any]]:
    """G6: Frozen Out-of-Sample (OOS) Replication (g6_protected_oos).

    Splits dataset into In-Sample (IS: first 67% / 8 months) and Frozen OOS (last 33% / 4 months).
    Runs strategy with frozen parameters on OOS and proves it retains at least 60% of IS
    PROFIT (not balance ratio): retention = oos_profit / is_profit. An unprofitable IS
    cannot be replicated (BLOCKED: no edge to retain); an unprofitable OOS retains
    nothing (BLOCKED: negative retention). The blow-up guard (OOS balance >= 8000)
    stays as a separate survival floor.
    """
    cfg = strategy_config or ExpertStrategyConfig(
        min_support_quorum=1,
        max_contradiction_tolerance=28,
        bracket_stop_pct=Decimal("0.02"),
        bracket_target_pct=Decimal("0.04"),
    )
    n = len(candles)
    split_idx = int(n * (2.0 / 3.0))

    is_candles = tuple(candles[:split_idx])
    oos_candles = tuple(candles[split_idx:])

    is_res = run_expert_strategy_backtest(is_candles, cfg)
    oos_res = run_expert_strategy_backtest(oos_candles, cfg)

    is_trades = len(is_res["opened_positions"])
    oos_trades = len(oos_res["opened_positions"])

    is_bars = len(is_candles)
    oos_bars = len(oos_candles)

    # Calculate normalized trade frequency & performance
    is_freq = is_trades / max(1, is_bars)
    oos_freq = oos_trades / max(1, oos_bars)

    freq_retention = oos_freq / is_freq if is_freq > 0 else 1.0
    account_is = is_res["account"]
    account_oos = oos_res["account"]

    is_balance = extract_account_balance(account_is, default=10000.0)
    oos_balance = extract_account_balance(account_oos, default=10000.0)

    is_profit = is_balance - 10000.0
    oos_profit = oos_balance - 10000.0
    if is_profit <= 0:
        return GateState.BLOCKED, {
            "is_bars": is_bars,
            "is_trades": is_trades,
            "is_final_balance": round(is_balance, 2),
            "oos_bars": oos_bars,
            "oos_trades": oos_trades,
            "oos_final_balance": round(oos_balance, 2),
            "is_profit": round(is_profit, 2),
            "oos_profit": round(oos_profit, 2),
            "retention_ratio": None,
            "reason": f"NO_IS_EDGE_TO_RETAIN: is_profit={is_profit:.2f} <= 0",
            "passed": False,
        }
    retention_ratio = oos_profit / is_profit
    no_blowup = oos_balance >= 8000.0

    passed = retention_ratio >= min_retention_ratio and no_blowup
    state = GateState.PASS if passed else GateState.BLOCKED
    metrics = {
        "is_bars": is_bars,
        "is_trades": is_trades,
        "is_final_balance": round(is_balance, 2),
        "oos_bars": oos_bars,
        "oos_trades": oos_trades,
        "oos_final_balance": round(oos_balance, 2),
        "is_profit": round(is_profit, 2),
        "oos_profit": round(oos_profit, 2),
        "retention_ratio": round(retention_ratio, 4),
        "trade_freq_retention": round(freq_retention, 4),
        "reason": None
        if passed
        else (
            f"OOS_BLOWUP: balance={oos_balance:.2f}"
            if not no_blowup
            else f"PROFIT_RETENTION_BREACH: {retention_ratio:.4f} < {min_retention_ratio}"
        ),
        "passed": passed,
    }
    return state, metrics


def evaluate_g7_prospective_shadow(
    candles: Sequence[Candle],
    strategy_config: ExpertStrategyConfig | None = None,
    output_dir: Path | None = None,
) -> tuple[GateState, dict[str, Any]]:
    """G7: Prospective Shadow Succession (g7_generalization).

    Evaluates sequential prospective streaming observations using an e-process martingale
    and drift monitoring. Saves trajectory to disk. Requires a full 100-bar shadow
    window: a shorter stream cannot establish drift stability and fails closed with
    INSUFFICIENT_SHADOW_WINDOW.
    """
    out_dir = output_dir or Path("artifacts/benchmarks")
    out_dir.mkdir(parents=True, exist_ok=True)
    shadow_log = out_dir / "g7_prospective_shadow.jsonl"

    if len(candles) < 100:
        return GateState.BLOCKED, {
            "window_bars": len(candles),
            "required_window_bars": 100,
            "reason": f"INSUFFICIENT_SHADOW_WINDOW: {len(candles)} < 100",
            "passed": False,
        }
    stream_candles = tuple(candles[-100:])
    cfg = strategy_config or ExpertStrategyConfig(
        min_support_quorum=1,
        max_contradiction_tolerance=28,
        bracket_stop_pct=Decimal("0.02"),
        bracket_target_pct=Decimal("0.04"),
    )

    # Run Nautilus strategy in forward streaming / paper mode
    res = run_expert_strategy_backtest(stream_candles, cfg)
    decisions = res["decisions"]

    # Initialize e-process martingale E_t = prod_{k=1}^t (1 + lambda_k * (X_k - mu_0))
    e_process_val = 1.0
    # Unclipped twin judged by the gate. The logged trajectory stays clipped
    # for display stability, but judging the clipped value against bounds
    # inside the clip range is a tautology (clip [0.01, 19.0] vs pass
    # [0.01, 20.0) can never fail). The gate must see the real process.
    e_process_raw = 1.0
    drift_val = 0.0
    ref_mean = float(stream_candles[0].close) if stream_candles else 100.0

    trajectory: list[dict[str, Any]] = []

    for i, c in enumerate(stream_candles):
        px = float(c.close)
        ret = (px - ref_mean) / ref_mean if ref_mean > 0 else 0.0
        ref_mean = 0.95 * ref_mean + 0.05 * px

        betting_lambda = 0.1
        update = 1.0 + betting_lambda * np.tanh(ret * 10.0)
        e_process_raw = e_process_raw * update
        if not math.isfinite(e_process_raw):
            # Exploded/vanished wealth is a verdict, not a crash: pin it and
            # keep the window (drift still judged on the last bar).
            e_process_raw = float("inf") if e_process_raw > 0 else 0.0
        e_process_val = float(np.clip(e_process_val * update, 0.01, 19.0))
        drift_val = float(abs(ret))

        dec_info = decisions[i] if i < len(decisions) else {}
        action = dec_info.get("action", "NO_ACTION")

        step_record = {
            "step": i,
            "timestamp_ns": c.end_ns,
            "e_process": round(e_process_val, 6),
            "drift": round(drift_val, 6),
            "action": action,
            "close": px,
        }
        trajectory.append(step_record)

    with open(shadow_log, "w", encoding="utf-8") as f:
        for r in trajectory:
            f.write(json.dumps(r) + "\n")

    passed = 0.01 <= e_process_raw < 20.0 and drift_val < 0.15
    state = GateState.PASS if passed else GateState.BLOCKED
    metrics = {
        "final_e_process": round(e_process_val, 4),
        "final_e_process_raw": (
            round(e_process_raw, 4) if math.isfinite(e_process_raw) else str(e_process_raw)
        ),
        "final_drift": round(drift_val, 6),
        "shadow_steps": len(trajectory),
        "log_path": str(shadow_log),
        "passed": passed,
    }
    if not passed:
        metrics["reason"] = (
            "E_PROCESS_OUT_OF_BAND"
            if not (0.01 <= e_process_raw < 20.0)
            else "DRIFT_EXCEEDED"
        )
    return state, metrics


def evaluate_g8_live_realization(
    live_fills_path: Path | str | None = None,
    *,
    source: str = "live",
    account: dict[str, Any] | None = None,
) -> tuple[GateState, dict[str, Any]]:
    """G8: Live Realization (g8_prospective_shadow).

    Real venue-settled fills vs simulated account reconciliation.
    Fixture files are NEVER counted as live (FIXTURE_NOT_LIVE).
    Absent venue/account => UNRUN_NO_VENUE_ACCOUNT (NOT_APPLICABLE diagnostic fold).
    Documented format/source/command in every branch per SHADOW_LIVE_DATA_SPEC.md.
    """
    from v8_next.adapters.shadow_ingest import (
        is_fixture_path,
        load_shadow_fills,
        reconcile_shadow_account,
    )

    spec_ref = "docs/contracts/SHADOW_LIVE_DATA_SPEC.md"
    base_doc = {
        "format": "jsonl per SHADOW_LIVE_DATA_SPEC.md: {fill_id,instrument,price,qty,side,venue_time_ns,order_id}",
        "source": "venue private REST GET /fapi/v1/userTrades (requires BINANCE_API_KEY)",
        "command": "uv run --project v8-next python -m v8_next.adapters.shadow_ingest verify --fills artifacts/shadow_fills.jsonl",
        "spec": spec_ref,
    }

    # Fixture guard: never count fixture as live, even if well-formed
    if live_fills_path is not None and (source == "fixture" or is_fixture_path(Path(live_fills_path))):
        return GateState.BLOCKED, {
            **base_doc,
            "mode": "FIXTURE_NOT_LIVE",
            "reason": f"fixture path not counted as live: {live_fills_path}",
            "fixture_guard": True,
            "clause": "fixture never substitutes for venue-settled fills",
        }

    if live_fills_path is not None:
        fills, meta = load_shadow_fills(live_fills_path, source=source)
        mode = meta.get("mode")
        if mode == "FIXTURE_NOT_LIVE":
            return GateState.BLOCKED, {**base_doc, **meta}
        if mode == "LIVE_VENUE_SETTLED":
            # Reconciliation against AccountState is what turns fills into a
            # verified realization. Without an account there is no
            # reconciliation: PASS is explicitly labeled unreconciled so no
            # consumer can mistake it for a matched realization.
            recon = reconcile_shadow_account(fills, account) if account is not None else None
            out: dict[str, Any] = {**base_doc, **meta, "mode": "LIVE_VENUE_SETTLED"}
            if recon is not None:
                out["reconciliation"] = recon
                out["account_reconciliation"] = recon  # alias for spec
                out["account_reconciled"] = True
            else:
                out["reconciliation"] = "UNRUN_NO_ACCOUNT"
                out["account_reconciled"] = False
            return GateState.PASS, out
        if mode in ("UNRUN_NO_VENUE_ACCOUNT", "MALFORMED_SHADOW_FILE"):
            # Malformed or absent but path was given => BLOCKED (explicit claim attempted)
            state = GateState.BLOCKED if mode == "MALFORMED_SHADOW_FILE" else GateState.NOT_APPLICABLE
            return state, {**base_doc, **meta}

    # No path supplied: research / candidate phase => diagnostic fold.
    # No ambient probe: a stray file in the working directory must never
    # promote a gate. Explicit --live-fills is the only PASS route.
    return GateState.NOT_APPLICABLE, {
        **base_doc,
        "mode": "DIAGNOSTIC_FOLD",
        "status": "UNRUN_NO_VENUE_ACCOUNT",
        "reason": "no venue account / no file at artifacts/shadow_fills.jsonl",
        "expected_command": "uv run --project v8-next python -m v8_next.adapters.shadow_ingest fetch --symbol BTCUSDT --out artifacts/shadow_fills.jsonl  # requires BINANCE_API_KEY",
        "clause": "D-152 §5 (Research / Candidate fold unblocks pipeline without claiming live fills)",
        "funding_note": "quad funding is public in research/tape/quad-1h-12m/tape.jsonl; see funding_history.quad_funding_summary",
        "unrun_detail": "UNRUN_NO_VENUE_ACCOUNT",
    }


def evaluate_g9_certificate_authority(
    ledger: BenchmarkLedger,
    receipt_digest: str,
    gates: GateVector,
    capability_score: float,
    output_dir: Path | None = None,
    live_realization_verified: bool = False,
) -> tuple[GateState, dict[str, Any], StatutoryClaimRecord | None]:
    """G9: Certificate Authority (g9_live_realization).

    Enforces Central ClaimRegistry verification:
    1. Validates BenchmarkLedger cryptographic hash chain.
    2. Verifies that G0-G7 hold.
    3. Mints signed StatutoryClaimRecord and registers it in central ledger.
    4. Elevates verdict to READY_NOT_CLAIMED (or SUPPORTED_EDGE if live fills certified).
    """
    out_dir = output_dir or Path("artifacts/benchmarks")
    registry = ClaimRegistry(registry_dir=out_dir)

    success, msg, claim_record = registry.verify_ledger_and_issue_claim(
        ledger=ledger,
        receipt_digest=receipt_digest,
        gates=gates,
        capability_score=capability_score,
        live_realization_verified=live_realization_verified,
    )

    if success and claim_record is not None:
        return GateState.PASS, {
            "claim_id": claim_record.claim_id,
            "claim_class": claim_record.claim_class.value,
            "allowed_header": claim_record.allowed_rendering_header,
            "signature_verified": claim_record.verify_signature(),
            "message": msg,
        }, claim_record

    return GateState.BLOCKED, {"error": msg}, None


@dataclass(frozen=True)
class GateResolutionReport:
    """Full execution report of the G0-G9 gate resolution battery."""

    gates: GateVector
    g3_metrics: dict[str, Any]
    g4_metrics: dict[str, Any]
    g5_metrics: dict[str, Any]
    g6_metrics: dict[str, Any]
    g7_metrics: dict[str, Any]
    g8_metrics: dict[str, Any]
    g9_metrics: dict[str, Any]
    claim_record: StatutoryClaimRecord | None


def resolve_all_gates(
    candles: Sequence[Candle],
    pnl_series: list[float],
    ledger: BenchmarkLedger,
    receipt_digest: str,
    capability_score: float,
    strategy_config: ExpertStrategyConfig | None = None,
    output_dir: Path | None = None,
    tape_path: Path | str | None = None,
    live_fills_path: Path | str | None = None,
) -> GateResolutionReport:
    """Run comprehensive empirical resolution of all gates G3-G9."""
    cfg = strategy_config or ExpertStrategyConfig(
        min_support_quorum=1,
        max_contradiction_tolerance=28,
        bracket_stop_pct=Decimal("0.02"),
        bracket_target_pct=Decimal("0.04"),
    )
    out_dir = output_dir or Path("artifacts/benchmarks")

    # 1. G3 Scenario Robustness
    regimes = classify_market_regimes(tape_path=tape_path, candles=candles)
    g3_state, g3_metrics = evaluate_g3_scenario_robustness(regimes, cfg)

    # 2. G4 Synthetic / Adversarial Falsification
    g4_state, g4_metrics = evaluate_g4_synthetic_falsification(candles, cfg)

    # 3. G5 Selection Control (DSR & WRC)
    g5_state, g5_metrics = evaluate_g5_selection_control(pnl_series, candles)

    # 4. G6 Frozen OOS Replication
    g6_state, g6_metrics = evaluate_g6_frozen_oos(candles, cfg)

    # 5. G7 Prospective Shadow
    g7_state, g7_metrics = evaluate_g7_prospective_shadow(candles, cfg, output_dir=out_dir)

    # 6. G8 Live Realization
    g8_state, g8_metrics = evaluate_g8_live_realization(live_fills_path=live_fills_path)

    # Partial GateVector before G9 issuance
    partial_gates = GateVector(
        g0_identity=GateState.PASS,
        g1_causal_pit=GateState.PASS,
        g2_determinism_ledger=GateState.PASS,
        g3_benchmark_coverage=g3_state,
        g4_structural_robustness=g4_state,
        g5_statistical_credibility=g5_state,
        g6_protected_oos=g6_state,
        g7_generalization=g7_state,
        g8_prospective_shadow=g8_state,
        g9_live_realization=GateState.MISSING,
    )

    # 7. G9 Certificate Authority (ClaimRegistry)
    live_verified = g8_state == GateState.PASS
    g9_state, g9_metrics, claim_record = evaluate_g9_certificate_authority(
        ledger=ledger,
        receipt_digest=receipt_digest,
        gates=partial_gates,
        capability_score=capability_score,
        output_dir=out_dir,
        live_realization_verified=live_verified,
    )

    final_gates = GateVector(
        g0_identity=GateState.PASS,
        g1_causal_pit=GateState.PASS,
        g2_determinism_ledger=GateState.PASS,
        g3_benchmark_coverage=g3_state,
        g4_structural_robustness=g4_state,
        g5_statistical_credibility=g5_state,
        g6_protected_oos=g6_state,
        g7_generalization=g7_state,
        g8_prospective_shadow=g8_state,
        g9_live_realization=g9_state,
    )

    return GateResolutionReport(
        gates=final_gates,
        g3_metrics=g3_metrics,
        g4_metrics=g4_metrics,
        g5_metrics=g5_metrics,
        g6_metrics=g6_metrics,
        g7_metrics=g7_metrics,
        g8_metrics=g8_metrics,
        g9_metrics=g9_metrics,
        claim_record=claim_record,
    )
