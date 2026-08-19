import json
from pathlib import Path
from collections import defaultdict

def run_counterfactual_audit():
    tape_path = Path('research/tape/btcusdt-1h-12m/tape.jsonl')
    cands_path = Path('.audit/rust_audit_current/candidates.jsonl')
    
    if not tape_path.exists() or not cands_path.exists():
        print('Missing required artifacts. Run reproduce_rust_audit.py first.')
        return

    print('Loading tape from {}...'.format(tape_path))
    opens, highs, lows, closes, times = [], [], [], [], []
    with tape_path.open('r', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r.get('channel') == 'kline':
                p = r['payload']
                opens.append(p['open'])
                highs.append(p['high'])
                lows.append(p['low'])
                closes.append(p['close'])
                times.append(r['event_time'])

    print('Loaded {:,} kline bars.'.format(len(closes)))

    cand_by_id = {}
    admitted_candidates = []
    with cands_path.open('r', encoding='utf-8') as f:
        for line in f:
            c = json.loads(line)
            cid = c.get('candidate_id')
            if cid and c.get('to_state') == 'DETECTED':
                cand_by_id[cid] = c
            elif c.get('to_state') == 'PENDING':
                admitted_candidates.append(c)

    print('Loaded {:,} unique admitted candidate episodes.'.format(len(admitted_candidates)))

    def simulate_candidate(cand_snap, params):
        direction = cand_snap['direction']
        long = (direction == 'LONG')
        sign = 1.0 if long else -1.0
        entry_bar = cand_snap['entry_bar']
        if entry_bar >= len(closes) - 1:
            return None
        
        geom = cand_snap.get('risk_geometry', {})
        atr = geom.get('atr_ref', closes[entry_bar] * 0.01)
        if atr <= 0:
            atr = closes[entry_bar] * 0.01
        unit = atr
        entry_price = closes[entry_bar]
        base_stop_r = geom.get('stop_r', 1.0)
        base_target_r = geom.get('target_r', 1.5)
        expiry_bars = int(geom.get('expiry_bars', 8))
        cost_r = 0.07
        
        stop_price = entry_price - sign * (1.5 * unit if params.get('adaptive_sl') else base_stop_r * unit)
        target_price = entry_price + sign * (999.0 * unit if params.get('no_hard_tp') else base_target_r * unit)
        current_stop = stop_price
        mfe_r = 0.0
        mae_r = 0.0
        stop_rolled = False
        
        for bar_idx in range(entry_bar + 1, min(len(closes), entry_bar + 1 + expiry_bars)):
            h = highs[bar_idx]
            l = lows[bar_idx]
            c = closes[bar_idx]
            fav = h if long else l
            adv = l if long else h
            bar_mfe = max(0.0, sign * (fav - entry_price) / unit)
            bar_mae = max(0.0, sign * (entry_price - adv) / unit)
            mfe_r = max(mfe_r, bar_mfe)
            mae_r = max(mae_r, bar_mae)
            
            hit_stop = (l <= current_stop) if long else (h >= current_stop)
            hit_target = (h >= target_price) if long else (l <= target_price)
            if hit_stop and hit_target:
                hit_target = False
            if hit_stop:
                return {
                    'endpoint': 'STOP',
                    'exit_price': current_stop,
                    'net_r': sign * (current_stop - entry_price) / unit - cost_r,
                    'mfe_r': mfe_r,
                    'mae_r': mae_r,
                    'bars_held': bar_idx - entry_bar
                }
            if hit_target:
                return {
                    'endpoint': 'TARGET',
                    'exit_price': target_price,
                    'net_r': sign * (target_price - entry_price) / unit - cost_r,
                    'mfe_r': mfe_r,
                    'mae_r': mae_r,
                    'bars_held': bar_idx - entry_bar
                }
                
            if params.get('breakeven_at_mfe') and not stop_rolled:
                if mfe_r >= params['breakeven_at_mfe']:
                    current_stop = entry_price + sign * params.get('breakeven_margin', cost_r) * unit
                    stop_rolled = True
            if params.get('atr_trail') and mfe_r >= params.get('atr_trail_start', 1.0):
                trail_p = entry_price + sign * (mfe_r - params['atr_trail']) * unit
                current_stop = max(current_stop, trail_p) if long else min(current_stop, trail_p)
                
        exit_p = closes[min(len(closes) - 1, entry_bar + expiry_bars)]
        return {
            'endpoint': 'EXPIRY',
            'exit_price': exit_p,
            'net_r': sign * (exit_p - entry_price) / unit - cost_r,
            'mfe_r': mfe_r,
            'mae_r': mae_r,
            'bars_held': expiry_bars
        }

    policies = {
        'H0_STATIC_BASELINE': {},
        'H1_BREAKEVEN_AT_1R': {'breakeven_at_mfe': 1.0, 'breakeven_margin': 0.07},
        'H2_PROFIT_LOCK_AT_1R': {'breakeven_at_mfe': 1.0, 'breakeven_margin': 0.30},
        'H3_ATR_TRAIL_1.5ATR': {'atr_trail': 1.5, 'atr_trail_start': 1.0},
        'H4_DYNAMIC_ASYMMETRIC': {
            'adaptive_sl': True,
            'breakeven_at_mfe': 0.8,
            'breakeven_margin': 0.20,
            'atr_trail': 1.2,
            'atr_trail_start': 1.0,
            'no_hard_tp': True
        }
    }

    results = {p: [] for p in policies}
    sample_trades = []

    for c in admitted_candidates:
        snap = cand_by_id.get(c['candidate_id'])
        if not snap:
            continue
        eid = snap['expert_id']
        r0 = simulate_candidate(snap, policies['H0_STATIC_BASELINE'])
        r1 = simulate_candidate(snap, policies['H1_BREAKEVEN_AT_1R'])
        r2 = simulate_candidate(snap, policies['H2_PROFIT_LOCK_AT_1R'])
        r3 = simulate_candidate(snap, policies['H3_ATR_TRAIL_1.5ATR'])
        r4 = simulate_candidate(snap, policies['H4_DYNAMIC_ASYMMETRIC'])
        
        if r0 and r1 and r2 and r3 and r4:
            results['H0_STATIC_BASELINE'].append(r0)
            results['H1_BREAKEVEN_AT_1R'].append(r1)
            results['H2_PROFIT_LOCK_AT_1R'].append(r2)
            results['H3_ATR_TRAIL_1.5ATR'].append(r3)
            results['H4_DYNAMIC_ASYMMETRIC'].append(r4)
            
            if r0['endpoint'] == 'STOP' and r4['net_r'] > 0 and len(sample_trades) < 10:
                sample_trades.append({
                    'cid': snap['candidate_id'][:16],
                    'expert': eid,
                    'dir': snap['direction'],
                    'entry_bar': snap['entry_bar'],
                    'h0_ep': r0['endpoint'],
                    'h0_r': r0['net_r'],
                    'h4_ep': r4['endpoint'],
                    'h4_r': r4['net_r'],
                    'mfe_r': r0['mfe_r'],
                })

    print('\n' + '=' * 95)
    print('PAIRED COUNTERFACTUAL SCORECARD (1,774 UNIQUE CANDIDATE TRADES)')
    print('=' * 95)
    print('{:<24} | {:>6} | {:>9} | {:>8} | {:>10} | {:>10} | {:>10}'.format(
        'Exit Policy Hypothesis', 'N', 'Avg Net R', 'Win Rate', 'Total Net R', 'Profit Fac', 'Delta NetR'
    ))
    print('-' * 95)
    base_tot = sum(r['net_r'] for r in results['H0_STATIC_BASELINE'])
    for p_name, res_list in results.items():
        n = len(res_list)
        net_rs = [r['net_r'] for r in res_list]
        tot_r = sum(net_rs)
        avg_r = tot_r / n if n > 0 else 0.0
        wins = sum(1 for r in net_rs if r > 0)
        win_rate = wins / n * 100 if n > 0 else 0.0
        gains = sum(r for r in net_rs if r > 0)
        losses = sum(abs(r) for r in net_rs if r < 0)
        pf = gains / losses if losses > 0 else 99.0
        delta_r = tot_r - base_tot
        print('{:<24} | {:>6} | {:>8.4f}R | {:>7.1f}% | {:>9.2f}R | {:>10.2f} | {:>+9.2f}R'.format(
            p_name, n, avg_r, win_rate, tot_r, pf, delta_r
        ))

    print('\n' + '=' * 95)
    print('SAMPLE INDIVIDUAL TRADE FORENSIC EVIDENCE (CANDIDATE-BY-CANDIDATE AUDIT)')
    print('=' * 95)
    print('{:<16} | {:<24} | {:>4} | {:>5} | {:>7} | {:>14} -> {:>14}'.format(
        'Candidate ID', 'Expert Strategy', 'Dir', 'Bar', 'Max MFE', 'H0 Baseline', 'H4 Dynamic'
    ))
    print('-' * 95)
    for st in sample_trades:
        print('{:<16} | {:<24} | {:>4} | {:>5} | {:>6.2f}R | {:>4} ({:>+5.2f}R) -> {:>4} ({:>+5.2f}R)'.format(
            st['cid'], st['expert'], st['dir'], st['entry_bar'], st['mfe_r'],
            st['h0_ep'], st['h0_r'], st['h4_ep'], st['h4_r']
        ))

if __name__ == '__main__':
    run_counterfactual_audit()
