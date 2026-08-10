"""Live equity (stock) analysis on the V8 pipeline: Yahoo OHLCV -> tape -> lab.

Fetches OHLCV for a stock symbol from the Yahoo Finance chart API with stdlib
`urllib` (no API key, no wall clock in the replay), builds a V8 TapeRow tape
(`source='yahoo-equity'`, `channel='kline'`, three distinct clocks), validates it
against the ingest contract, runs the full admitted expert roster through
`v8.lab.Lab`, and prints a JSON report.

This is a `tools/` script (D-031: outside the decision-path code hash — the
report surfaces `tooling_hash`). It is an analysis harness, not a preregistered
experiment: the verdict stays NO_ECONOMIC_CLAIM (no authority receipt), and the
report is descriptive of behavior, never a profitability claim
(V8_CONSTITUTION rule 12).

Declared, documented approximations (ad-hoc run, not a preregistration):
- Round-trip cost: `round_trip_cost_bps=10.0` (0.1% of notional round trip —
  conservative for a liquid US equity vs the ~0.01% venue reality; the bps form
  is "what a venue actually charges", per ExperimentManifest).
- Funding/OI: absent from the tape -> the positioning experts
  (funding_crowding_reversal, open_interest_divergence) self-gate to
  NO_HABITAT.
- Session features (vwap, hour_of_day_utc, bar_of_session, day_index) are
  declared for a 24/7 UTC market (G-36/G-38..G-40); a NYSE tape only trades
  13:30-19:30 UTC weekdays, so those feature VALUES are a UTC-anchored
  approximation, never a venue-session reading.
- Yahoo returns a partial first bar (range anchor) and a partial last bar
  (in-progress); bars with volume == 0 are dropped so every kline on the tape is
  a closed bar (FEED_INGESTION_SPEC section 3).

One store directory = one immutable run (O-011): a second run into the same
`--out` fails closed.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'src'))

from v8.lab import Lab  # noqa: E402
from v8.schema import ExperimentManifest, TapeRow  # noqa: E402

HOUR_NS = 3_600_000_000_000
FEED_LATENCY_NS = 1_000_000_000          # 1s configured feed latency (vision_backfill)
SOURCE = 'yahoo-equity'
INTERVAL = '1h'
YAHOO_ENDPOINT = 'https://query1.finance.yahoo.com/v8/finance/chart/{}'
_UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}


def fetch_yahoo_klines(symbol: str, rng: str = '1mo',
                       interval: str = '1h') -> tuple[list[dict], dict]:
    """OHLCV bars from the Yahoo chart API; returns (bars, meta).

    Each bar: {'open_time_s': int, 'open': float, 'high': float, 'low': float,
    'close': float, 'volume': float}. Fail closed on transport / shape errors —
    never fabricate a bar (DATA hashing requires exact provenance).
    """
    url = YAHOO_ENDPOINT.format(symbol)
    q = f'?range={rng}&interval={interval}&includePrePost=false'
    req = urllib.request.Request(url + q, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as exc:                       # URLError / TimeoutError / JSON
        raise RuntimeError(f'Yahoo fetch failed for {symbol}: {exc}') from exc
    result = (data.get('chart') or {}).get('result') or []
    if not result:
        err = (data.get('chart') or {}).get('error') or 'empty result'
        raise RuntimeError(f'Yahoo returned no chart result for {symbol}: {err}')
    r = result[0]
    meta = r.get('meta', {})
    ts = r.get('timestamp') or []
    q = (r.get('indicators') or {}).get('quote') or [{}]
    q = q[0]
    bars = []
    for i, t in enumerate(ts):
        o, h, l, c = q.get('open', [None] * len(ts))[i], \
            q.get('high', [None] * len(ts))[i], \
            q.get('low', [None] * len(ts))[i], \
            q.get('close', [None] * len(ts))[i]
        if None in (o, h, l, c):
            continue                               # never ship a hole in OHLC
        bars.append({'open_time_s': int(t), 'open': float(o), 'high': float(h),
                     'low': float(l), 'close': float(c),
                     'volume': float(q.get('volume', [0.0] * len(ts))[i] or 0.0)})
    if not bars:
        raise RuntimeError(f'Yahoo returned no complete bars for {symbol}')
    return bars, meta


def tape_from_klines(symbol: str, bars: list[dict]) -> list[TapeRow]:
    """Bars -> closed-kline TapeRows (V8 conventions: event_time = bar close,
    available = close + feed latency, venue_sequence 1-based, event_id unique).

    Bars with volume == 0 are the Yahoo partial anchors (range start / in-
    progress bar) and are dropped so every kline is a closed bar. OHLC
    invariants are enforced fail-closed: h >= max(o,c), l <= min(o,c), all > 0.
    """
    rows: list[TapeRow] = []
    seq = 0
    for b in bars:
        if b['volume'] == 0.0:
            continue                               # partial bar — never closed
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        if not (min(o, h, l, c) > 0):
            raise ValueError(f'{symbol}: non-positive OHLC {b}')
        if h < max(o, c) or l > min(o, c) or h < l:
            raise ValueError(f'{symbol}: OHLC invariant violation {b}')
        seq += 1
        open_ns = b['open_time_s'] * 1_000_000_000
        close_ns = open_ns + HOUR_NS - 1_000_000
        rows.append(TapeRow(
            source=SOURCE, channel='kline', instrument=symbol,
            event_time=close_ns,
            available_time=close_ns + FEED_LATENCY_NS,
            ingested_time=close_ns + FEED_LATENCY_NS,
            venue_sequence=seq,
            event_id=f'{symbol}:1h:{b["open_time_s"] * 1000}',
            payload={'open': o, 'high': h, 'low': l, 'close': c,
                     'volume': b['volume'], 'closed': True}))
    return rows


def run_analysis(symbol: str, out_dir: Path, rng: str) -> dict:
    """Fetch -> tape -> lab run -> report dict. One immutable run per store."""
    import v8.experts as registry
    from v8.schema import LabReport

    out_dir.mkdir(parents=True, exist_ok=True)
    bars, meta = fetch_yahoo_klines(symbol, rng, INTERVAL)
    rows = tape_from_klines(symbol, bars)
    if not rows:
        raise RuntimeError(f'{symbol}: no closed bars survived the partial-bar '
                           'filter — cannot analyse an empty tape')
    lab = Lab(out_dir / 'store', universe=(symbol,))
    lab.ingest(rows)
    roster = [getattr(registry, n) for n in registry.__all__
              if isinstance(getattr(registry, n), type)
              and getattr(registry, n).__name__ != 'Expert']
    experts = [cls() for cls in roster]
    manifest = ExperimentManifest(
        experiment_id=f'equity-{symbol.lower()}', code_hash='', data_hash='',
        universe=(symbol,), start_ns=min(r.event_time for r in rows),
        end_ns=max(r.event_time for r in rows), interval=INTERVAL,
        round_trip_cost_bps=10.0)
    report: LabReport = lab.run(manifest, experts)

    evals: dict[str, int] = {}
    for line in (out_dir / 'store' / 'evaluations.jsonl').read_text(
            encoding='utf-8').splitlines():
        if line.strip():
            rec = json.loads(line)
            if 'decision' in rec:
                key = rec['decision']
                evals[key] = evals.get(key, 0) + 1
    # candidates.jsonl mixes lifecycle transitions (no expert_id), full drafts
    # and birth snapshots (both carry expert_id); count distinct candidate_ids
    # per expert so a candidate is never double-counted across record kinds.
    cids_by_expert: dict[str, set[str]] = {}
    for line in (out_dir / 'store' / 'candidates.jsonl').read_text(
            encoding='utf-8').splitlines():
        if line.strip():
            rec = json.loads(line)
            eid = rec.get('expert_id')
            if eid is None:
                continue
            cids_by_expert.setdefault(eid, set()).add(rec['candidate_id'])
    candidates_by_expert = {eid: len(cids)
                            for eid, cids in sorted(cids_by_expert.items())}

    summary = {
        'symbol': symbol,
        'source': SOURCE,
        'interval': INTERVAL,
        'window': {'range': rng, 'bars': len(rows),
                   'first_event_ns': rows[0].event_time,
                   'last_event_ns': rows[-1].event_time},
        'price': {'first_close': rows[0].payload['close'],
                  'last_close': rows[-1].payload['close'],
                  'high': max(b.payload['high'] for b in rows),
                  'low': min(b.payload['low'] for b in rows),
                  'net_pct': (rows[-1].payload['close']
                              / rows[0].payload['close'] - 1.0) * 100.0},
        'exchange': meta.get('fullExchangeName') or meta.get('exchangeName'),
        'currency': meta.get('currency'),
        'lab': {
            'verdict': report.verdict,
            'candidate_count': report.candidate_count,
            'terminal_distribution': report.terminal_distribution,
            'evaluation_distribution': report.evaluation_distribution,
            'rejection_distribution': report.rejection_distribution,
            'data_invalid': report.data_invalid,
            'n_executed': report.n_executed,
            'n_portfolio_rejected': report.n_portfolio_rejected,
            'execution_share': report.execution_share,
            'divergence_ks': report.divergence_ks,
            'code_hash': report.code_hash,
            'data_hash': report.data_hash,
            'ledger_hash': report.ledger_hash,
            'risk_gate_hash': report.risk_gate_hash,
            'tooling_hash': report.tooling_hash,
            'final_equity': report.final_equity,
            'max_drawdown': report.max_drawdown,
            'profit_factor': report.profit_factor,
            'w_min': report.w_min,
            'risk_of_ruin': report.risk_of_ruin,
            'economic_note': report.economic_note,
        },
        'experts': {
            'roster': [cls.__name__ for cls in roster],
            'candidates_by_expert': candidates_by_expert,
        },
        'evaluations': evals,
    }
    (out_dir / 'report.json').write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding='utf-8')
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--symbol', default='XOM', help='Yahoo ticker (default XOM)')
    ap.add_argument('--range', default='1mo', help='Yahoo range (default 1mo)')
    ap.add_argument('--out', type=Path, default=Path('.audit/equity/xom'),
                    help='output dir (default .audit/equity/xom)')
    args = ap.parse_args(argv)
    summary = run_analysis(args.symbol, args.out, args.range)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f'\nreport.json: {args.out / "report.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
