"""Build the development-only eight-family handbook validation artifact.

This tool is a pipeline probe, not an experiment runner or economic evaluator.
It derives 4h/1d/1w bars solely from closed PIT 1h bars, discards incomplete
aggregation buckets, and never opens the frozen OOS window.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from v8.experts import (CompressionBreakoutExpert, FailedBreakoutExpert,
                        LiquiditySweepReclaimExpert, TrendExhaustionReversalExpert,
                        TrendPullbackExpert, VolumeRangeBreakoutExpert)
from v8.lab import Lab, _code_hash
from v8.schema import ExperimentManifest, TapeRow, sha1_hex

HOUR_NS = 3_600_000_000_000
TIMEFRAMES = {'1h': 1, '4h': 4, '1d': 24, '1w': 168}
ACTIVE = (TrendPullbackExpert, TrendExhaustionReversalExpert,
          CompressionBreakoutExpert, FailedBreakoutExpert,
          LiquiditySweepReclaimExpert, VolumeRangeBreakoutExpert)


def read_tape(path: Path) -> list[TapeRow]:
    return [TapeRow(**json.loads(line)) for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip()]


def bounded_slice(rows: list[TapeRow], max_base_bars: int) -> list[TapeRow]:
    """Keep the newest complete 1h development slice plus contemporaneous funding.

    This is an explicit compute bound, never a performance-selected window.
    The boundary is recorded in the raw artifact so it cannot masquerade as a
    full-history economic evaluation.
    """
    bars = [r for r in rows if r.channel == 'kline' and r.payload.get('closed') is True]
    funding_times = [r.event_time for r in rows if r.channel == 'funding']
    if not funding_times:
        raise ValueError('development probe requires a funding coverage schedule')
    # The canonical simulator fails closed when a held position would cross an
    # undeclared settlement boundary.  Reserve one maximum 1h expiry (8 bars)
    # before the final available funding boundary; this is coverage hygiene,
    # not a selected evaluation cutoff.
    coverage_end = max(funding_times) - 8 * HOUR_NS
    bars = [r for r in bars if r.event_time <= coverage_end]
    if len(bars) <= max_base_bars:
        return rows
    kept = bars[-max_base_bars:]
    start = kept[0].event_time
    funding = [r for r in rows if r.channel == 'funding' and r.event_time >= start]
    return sorted(kept + funding, key=lambda r: (r.event_time, r.available_time, r.venue_sequence))


def resample(rows: list[TapeRow], hours: int) -> list[TapeRow]:
    """Aggregate only complete, contiguous closed 1h buckets.

    The aggregate becomes available only when its final source bar is available;
    funding rows are retained unchanged because they are venue schedule facts,
    not transformed price observations.
    """
    if hours == 1:
        return list(rows)
    klines = [r for r in rows if r.channel == 'kline' and r.payload.get('closed') is True]
    funding = [r for r in rows if r.channel == 'funding']
    buckets: dict[int, list[TapeRow]] = defaultdict(list)
    span = hours * HOUR_NS
    for row in sorted(klines, key=lambda r: (r.event_time, r.available_time, r.venue_sequence)):
        buckets[row.event_time // span].append(row)
    out: list[TapeRow] = []
    for key in sorted(buckets):
        group = buckets[key]
        starts = [r.event_time for r in group]
        if len(group) != hours or starts != list(range(starts[0], starts[0] + span, HOUR_NS)):
            continue
        first, last = group[0], group[-1]
        out.append(TapeRow(
            source=first.source, channel='kline', instrument=first.instrument,
            event_time=last.event_time, available_time=last.available_time,
            ingested_time=last.ingested_time, venue_sequence=last.venue_sequence,
            event_id=f'{first.instrument}:{hours}h:{first.event_id}:{last.event_id}',
            payload={'open': float(first.payload['open']),
                     'high': max(float(r.payload['high']) for r in group),
                     'low': min(float(r.payload['low']) for r in group),
                     'close': float(last.payload['close']),
                     'volume': sum(float(r.payload.get('volume', 0.0)) for r in group),
                     'closed': True,
                     'aggregation': f'{hours}h_from_closed_1h',
                     'source_event_ids': [r.event_id for r in group]}))
    return sorted(out + funding, key=lambda r: (r.event_time, r.available_time, r.venue_sequence))


def run_timeframe(rows: list[TapeRow], tf: str) -> dict:
    # Windows may retain a transient lock on append-only JSONL immediately
    # after the run. Ignore cleanup-only lock failures: the returned hashes
    # are already complete, and the OS temp cleaner can reclaim the directory.
    with tempfile.TemporaryDirectory(prefix=f'v8-handbook-{tf}-',
                                     ignore_cleanup_errors=True) as temp:
        lab = Lab(Path(temp), universe=('BTCUSDT',))
        lab.ingest(rows)
        bars = [r for r in rows if r.channel == 'kline']
        manifest = ExperimentManifest(
            experiment_id=f'handbook_8_dev_{tf}', code_hash=_code_hash(),
            data_hash=sha1_hex([asdict(r) for r in rows]), universe=('BTCUSDT',),
            start_ns=bars[0].available_time, end_ns=bars[-1].available_time,
            interval=tf)
        report = lab.run(manifest, [cls() for cls in ACTIVE])
        detected = Counter(r.get('expert_id') for r in lab.candidates.read()
                           if r.get('to_state') == 'DETECTED')
        return {'bars': len(bars), 'tape_hash': lab.tape_log.hash,
                'detected_by_expert': dict(sorted(detected.items())),
                'report': asdict(report)}


def strategy_rows() -> list[dict]:
    return [
        {'id': 'SF-01', 'family': 'Trend continuation', 'experts': ['trend_pullback'],
         'status': 'FORMALIZED / development simulation', 'basis': 'Handbook Ch. 5, 11'},
        {'id': 'SF-02', 'family': 'Trend exhaustion / reversal', 'experts': ['trend_exhaustion_reversal'],
         'status': 'FORMALIZED / development simulation', 'basis': 'Handbook Ch. 5, 7, 9'},
        {'id': 'SF-03', 'family': 'Volatility contraction to expansion', 'experts': ['compression_breakout'],
         'status': 'FORMALIZED / development simulation', 'basis': 'Handbook Ch. 7, 21'},
        {'id': 'SF-04', 'family': 'Failed move / re-entry', 'experts': ['failed_breakout', 'liquidity_sweep_reclaim'],
         'status': 'FORMALIZED / development simulation', 'basis': 'Handbook Ch. 7'},
        {'id': 'SF-05', 'family': 'Participation-conditioned price action', 'experts': ['volume_range_breakout'],
         'status': 'FORMALIZED / development simulation', 'basis': 'Handbook Ch. 6'},
        {'id': 'SF-06', 'family': 'Range / value mean reversion', 'experts': ['range_value_mean_reversion'],
         'status': 'DATA_BLOCKED', 'basis': 'Handbook Ch. 12, 17, 20; needs PIT volume-at-price / profile'},
        {'id': 'SF-07', 'family': 'Cross-market / relative strength context', 'experts': ['cross_market_relative_strength'],
         'status': 'DATA_BLOCKED', 'basis': 'Handbook Ch. 22–24; needs PIT multi-asset/breadth/sentiment'},
        {'id': 'SF-08', 'family': 'Practitioner geometry and projection', 'experts': ['practitioner_geometry_projection'],
         'status': 'REJECTED', 'basis': 'Handbook Ch. 10, 18, 19; subjective without frozen annotation'},
    ]


def page(report: dict) -> str:
    rows = ''.join('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
        html.escape(item['id']), html.escape(item['family']),
        html.escape(', '.join(item['experts'])), html.escape(item['status']))
        for item in report['strategies'])
    runs = ''.join('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
        tf, value['bars'], value['report']['candidate_count'], value['report']['n_executed'],
        value['report']['verdict']) for tf, value in report['development_runs'].items())
    embedded = html.escape(json.dumps(report, ensure_ascii=False, separators=(',', ':')))
    sources = ''.join('<li>{}</li>'.format(html.escape(s)) for s in report['sources'])
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V8 · Handbook 8</title><style>
body{{margin:0;background:#0c1118;color:#e7edf5;font:15px/1.55 Inter,system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:52px 22px}}h1{{font-size:38px;line-height:1.05;margin:0}}h2{{margin-top:42px}}.tag{{color:#84f2bd;text-transform:uppercase;letter-spacing:.12em;font-size:12px}}.warning{{border-left:3px solid #f2b35d;background:#171d26;padding:16px 18px;margin:28px 0}}table{{width:100%;border-collapse:collapse;background:#111823}}td,th{{padding:11px;border-bottom:1px solid #283342;text-align:left;vertical-align:top}}th{{color:#9ab0c7;font-size:12px;text-transform:uppercase}}code{{color:#9ad5ff}}.muted{{color:#9aabba}}footer{{margin-top:44px;color:#7f91a5;font-size:13px}}</style></head><body><main>
<div class="tag">PRE-EXPERIMENTAL · EVIDENCE-BOUND</div><h1>Handbook → V8: 8 strateji ailesi</h1>
<p class="muted">Kaynak-kitap kavramlarının V8 için denetlenebilir formalizasyonu. Kitapta kanonik “tam sekiz strateji” listesi yoktur; bu sekizli V8 tasnifidir.</p>
<div class="warning"><strong>Ekonomik hüküm yok.</strong> Tüm çalıştırmalar development-only BTCUSDT verisindedir; frozen OOS açılmadı. Her satırın hükmü <code>NO_ECONOMIC_CLAIM</code>.</div>
<h2>8 aile ve uygulama durumu</h2><table><thead><tr><th>ID</th><th>Aile</th><th>Expert(ler)</th><th>Durum</th></tr></thead><tbody>{rows}</tbody></table>
<h2>PIT çoklu-zaman-dilimi pipeline probu</h2><p class="muted">4h/1d/1w, sadece kapalı 1h barlardan türetildi; eksik bucket’lar atıldı. Bu bir edge testi değil, formel pipeline/execution kontrolüdür.</p><table><thead><tr><th>TF</th><th>Bar</th><th>Aday</th><th>Executed</th><th>Hüküm</th></tr></thead><tbody>{runs}</tbody></table>
<h2>Risk ve execution değişikliği</h2><ul><li>Yeni Expert’ler emir vermez; mevcut deterministic admission, tek aktif <code>(instrument,direction)</code> exposure ve heat cap korunur.</li><li>SF-05 sadece venue bar-volume ve realized range kullanır; order-flow/queue/liquidity iddiası yapmaz.</li><li>SF-06 ve SF-07 eksik PIT veri yüzünden proxy ile geçilmedi; SF-08 öznel anotasyon olmadığı için reddedildi.</li><li>1w interval artık canonical lab tarafından açıkça tanınır; funding satırları venue takvimi olarak korunur.</li></ul>
<h2>Kaynak ve yorum sınırı</h2><ul>{sources}</ul>
<script id="raw-manifest" type="application/json">{embedded}</script><footer>Raw JSON kardeşi: <code>v8_handbook_8_strategies_implementation_and_validation.json</code></footer></main></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tape', type=Path, default=Path('tmp/handbook_dev_btcusdt_1h/tape.jsonl'))
    parser.add_argument('--out-dir', type=Path, default=Path('research'))
    parser.add_argument('--max-base-bars', type=int, default=2000)
    args = parser.parse_args()
    full_rows = read_tape(args.tape)
    rows = bounded_slice(full_rows, args.max_base_bars)
    development = {}
    for tf, hours in TIMEFRAMES.items():
        development[tf] = run_timeframe(resample(rows, hours), tf)
    report = {'report_id': 'v8_handbook_8_strategies_implementation_and_validation',
              'status': 'PRE-EXPERIMENTAL / EVIDENCE-BOUND',
              'development_only': True, 'source_tape': str(args.tape),
              'full_source_row_count': len(full_rows), 'development_slice_row_count': len(rows),
              'max_base_bars': args.max_base_bars,
              'code_hash': _code_hash(), 'strategies': strategy_rows(),
              'development_runs': development,
              'risk_execution_contract': {
                  'admission': 'Existing deterministic RiskGate; no Expert submits orders or sizes positions.',
                  'exposure': 'One active exposure per (instrument, direction); conflicts retained counterfactually.',
                  'heat': 'Existing portfolio and cluster heat caps; no ranker or scorer added.',
                  'funding': 'Tape-driven venue funding schedule; slice stops before uncovered settlement horizon.',
                  'sf05_limit': 'relative_volume and range_ratio are bar aggregates, not order flow or order-book liquidity.'},
              'validation': {
                  'focused_command': 'python -m pytest tests/test_expert_registry.py tests/test_artifact_status.py::test_registry_nothing_promoted tests/test_funding_wiring.py::test_audit_passes_sorted_mixed_tape tests/test_golden_backtest.py::test_golden_backtest_regression -q',
                  'focused_result': '10 passed',
                  'full_suite_environment_blockers': ['missing duckdb/tooling dependencies during collection',
                                                      'missing certification and pipeline_v2 fixture artifacts'],
                  'report_integrity': '8 strategy rows; inline CSS/JS-free HTML; raw JSON embedded in HTML'},
              'sources': [
                  'Lim (2016), The Handbook of Technical Analysis: Ch. 5, 6, 7, 10–12, 17–24, 28 (local user-supplied PDF).',
                  'Cont, Kukanov & Stoikov (2014), The Price Impact of Order Book Events, arXiv:1011.6402 — OHLCV is not order-book flow.',
                  'Koshiyama & Firoozye (2019), The Impact of Backtest Overfitting on Out-of-Sample Performance, arXiv:1905.05023.',
                  'Sermpinis et al. (2018), Technical Analysis and FDR, arXiv:1811.06766.',
                  'Lo, Mamaysky & Wang (2000), Foundations of Technical Analysis, NBER w7613 — patterns require explicit formalization.'
              ],
              'hard_limits': ['No frozen OOS opened.', 'No profitability or execution-validity claim.',
                              'SF-06/SF-07 fail closed on missing PIT data.', 'SF-08 rejected as subjective.']}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.out_dir / report['report_id']
    stem.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    stem.with_suffix('.html').write_text(page(report), encoding='utf-8')
    print(json.dumps({'json': str(stem.with_suffix('.json')), 'html': str(stem.with_suffix('.html'))}))


if __name__ == '__main__':
    main()
