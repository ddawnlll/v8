"""MECHANICS ONLY: exercise both replay contracts on the same decision."""
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from v8_next.economics.swing_baseline import replay_bracket
from v8_next.economics.swing_costs import SlippageModel, campaign_cost


def test_cost_lane_bracketless_readings_and_row_fields() -> None:
    hour = 3_600 * 10**9
    decision: Any = SimpleNamespace(
        stop_price=Decimal('100'), entry_reference=Decimal('100'),
        target_price=Decimal('100'), direction='LONG', decision_ns=0,
        expires_ns=2 * hour, instrument_id='BTCUSDT', policy_id='plain_swing',
    )
    bars: Any = [SimpleNamespace(start_ns=i * hour, end_ns=(i + 1) * hour,
                            open=Decimal('100'), low=Decimal('99'), high=Decimal('101'),
                            close=Decimal('101')) for i in range(2)]
    a = replay_bracket(decision, bars, bar_ns=hour, bps_fee=Decimal('0.0005'), has_bracket=True)
    bracketless = decision.stop_price == decision.entry_reference
    b = replay_bracket(decision, bars, bar_ns=hour, bps_fee=Decimal('0.0005'),
                       has_bracket=not bracketless)
    assert a.exit_kind == 'STOP' and a.bars_held == 1
    assert b.exit_kind == 'EXPIRY' and b.bars_held == 2
    assert not (bracketless and b.exit_kind == 'STOP')
    row = campaign_cost(decision=decision, outcome=b, funding_rows=[],
                        slippage=SlippageModel(model='none')).as_dict()
    assert (row['exit_kind'], row['bars_held'], row['bracketless']) == ('EXPIRY', 2, True)


def test_cost_lane_producer_publishes_both_readings(tmp_path, monkeypatch) -> None:
    """MECHANICS ONLY: the producer keeps A and exposes decision-based B."""
    import importlib.util
    import json
    from pathlib import Path
    from types import SimpleNamespace

    path = Path(__file__).resolve().parents[1] / 'tools/nx_cost_lane.py'
    spec = importlib.util.spec_from_file_location('cost_lane_test', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hour = module.HOUR_NS
    decision = SimpleNamespace(stop_price=Decimal('100'), entry_reference=Decimal('100'),
        target_price=Decimal('100'), direction='LONG', decision_ns=0, expires_ns=3 * hour,
        instrument_id='BTCUSDT', policy_id='plain_swing')
    bars = [SimpleNamespace(start_ns=i * hour, end_ns=(i + 1) * hour,
        open=Decimal('100'), low=Decimal('99'), high=Decimal('101'), close=Decimal('101'),
        instrument_id='BTCUSDT') for i in range(3)]
    tape = SimpleNamespace(candles={'BTCUSDT': bars}, funding=[SimpleNamespace(instrument='BTCUSDT',
        funding_time_ms=999999999, funding_rate=Decimal('0'), interval_hours=8.0)],
        funding_dropped=0, funding_raw_count=1, funding_interval_counts={},
        funding_interval_defaulted=0, mark_price_absent=True, absence_notes=[], tape_sha256='fixture')
    monkeypatch.setattr(module, 'load_multitape', lambda *a, **kw: tape)
    monkeypatch.setattr(module, 'policy_spec', lambda _: SimpleNamespace(
        grammar_policy='fixture', protection_policy='bracket'))
    monkeypatch.setitem(module.POLICY_REQUIRED_BARS, 'fixture', 0)
    monkeypatch.setattr(module, 'frame_at', lambda *a: None)
    monkeypatch.setattr(module, 'swing_signal', lambda *a, **kw: decision)
    assert module.main(['--repo-root', str(tmp_path), '--policies', 'plain_swing',
        '--start-utc', '1970-01-01', '--end-utc', '1970-01-02']) == 0
    entry = json.loads((tmp_path / 'docs/evidence/v87-r3/COST/cost_lane.json').read_text())['family']['plain_swing']
    contract = entry['bracket_contract']
    assert contract['bracketless_campaigns'] == 1
    assert contract['reading_a']['totals_by_slippage_fraction'] == entry['totals_by_slippage_fraction']
    row = entry['campaigns'][0]
    assert row['exit_kind'] == 'STOP' and row['bracketless']
    assert row['counter_reading']['exit_kind'] == 'EXPIRY'
    assert row['counter_reading']['bars_held'] == 2


@pytest.mark.slow
def test_cost_lane_real_window_contract(tmp_path) -> None:
    """Acceptance on the committed tape, when locally available."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    tape = root / 'research/tape/multi-1h-4y/tape.jsonl'
    if not tape.is_file():
        pytest.skip('canonical 4-year tape not available')
    subprocess.run([sys.executable, str(root / 'v8-next/tools/nx_cost_lane.py'),
                    '--repo-root', str(root), '--out', str(tmp_path)], check=True)
    generated = json.loads((tmp_path / 'cost_lane.json').read_bytes())
    committed = json.loads((root / 'docs/evidence/v87-r3/COST/cost_lane.json').read_bytes())
    plain = generated['family']['plain_swing']
    old_plain = committed.get('family', committed.get('families'))['plain_swing']
    def encode(value: Any) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    assert encode(plain['bracket_contract']['reading_a']['totals_by_slippage_fraction']) == encode(old_plain['totals_by_slippage_fraction'])
    assert plain['bracket_contract']['bracketless_campaigns'] == 26
    assert all(not (row['bracketless'] and row['counter_reading']['exit_kind'] == 'STOP')
               for row in plain['campaigns'])
    trend = generated['family']['causal_trend']
    assert trend['campaigns_in_window'] == 27
    assert sum(row['counter_reading']['exit_kind'] == 'EXPIRY' for row in trend['campaigns']) > 13

