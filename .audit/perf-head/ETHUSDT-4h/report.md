# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1386 inside the random-entry null [-0.1754, -0.0847] (percentile 30.5%) — signal indistinguishable from random entries'}`
configs searched: 431
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=15.28 median=30.3 max=64.54 unique=330

## 1 — Cost census
net_R mean=-0.1386 total=-128.80
gross mean=-0.0686
cost mean=0.0700 (cost is ONE flat R charge per trade (fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction). NOTE: being denominated in R, this charge is invariant to the R unit — widening the risk unit cannot dilute it. Use --cost-bps to price cost as a fraction of notional.)
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.1386 no_cost=-0.0686 no_funding=-0.1386 frictionless=-0.0686

## 3 — Null baselines
random-entry median=-0.1223 (actual percentile 30.5%)
inverted=-0.1011 always_long=-0.1614 always_short=-0.1094

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 184, "mean_R": -0.21805681233771096, "mean_duration": 7.434782608695652}, "STOP": {"count": 388, "mean_R": -0.9886048541307958, "mean_duration": 2.618556701030928}, "TARGET": {"count": 357, "mean_R": 0.8260659458822256, "mean_duration": 2.7899159663865545}}
early-SL: {'n_stopped': 388, 'n_mfe_gt_half_R_before_stop': 137, 'fraction': 0.35309278350515466, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 357, 'n_post_exit_gt_2R': 265, 'fraction': 0.742296918767507, 'mean_post_exit_max_r': 4.528248457624677, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 30, 'pessimistic_mean': -0.6932409220210687, 'optimistic_mean': 0.6914723718665114, 'spread_R': 1.3847132938875801}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0767 hit=0.405 overlap=2.58
h=2: net_R=-0.0561 hit=0.411 overlap=5.14
h=4: net_R=-0.0349 hit=0.449 overlap=10.22
h=8: net_R=-0.1432 hit=0.432 overlap=20.24
h=12: net_R=-0.1360 hit=0.425 overlap=30.07
h=24: net_R=-0.2889 hit=0.411 overlap=58.78
h=48: net_R=-0.2578 hit=0.431 overlap=112.62
h=72: net_R=-0.1134 hit=0.446 overlap=161.18
h=96: net_R=0.0768 hit=0.470 overlap=204.91
h=120: net_R=0.3558 hit=0.469 overlap=244.03
h=168: net_R=0.1649 hit=0.467 overlap=307.24
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 2.0607133533882087, "n": 920}, "2": {"mean_markout_bps": 3.7544888741912237, "n": 917}, "3": {"mean_markout_bps": 8.248133181825596, "n": 914}, "6": {"mean_markout_bps": 4.785377490156443, "n": 898}, "12": {"mean_markout_bps": 4.484080845079058, "n": 878}, "24": {"mean_markout_bps": -15.674119928952853, "n": 842}}

## 8 — Segments
{"month": {"1": {"N": 6, "net_R": null, "min_N_for_0_01R": 63047.7172425774, "status": "INSUFFICIENT"}, "2": {"N": 444, "net_R": null, "min_N_for_0_01R": 38465.32523529946, "status": "INSUFFICIENT"}, "3": {"N": 479, "net_R": null, "min_N_for_0_01R": 32017.118458755544, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 174, "net_R": null, "min_N_for_0_01R": 32323.210727115245, "status": "INSUFFICIENT"}, "4": {"N": 141, "net_R": null, "min_N_for_0_01R": 36053.086831286106, "status": "INSUFFICIENT"}, "8": {"N": 120, "net_R": null, "min_N_for_0_01R": 34113.76707623739, "status": "INSUFFICIENT"}, "12": {"N": 169, "net_R": null, "min_N_for_0_01R": 35321.203747613115, "status": "INSUFFICIENT"}, "16": {"N": 168, "net_R": null, "min_N_for_0_01R": 38702.257918444106, "status": "INSUFFICIENT"}, "20": {"N": 157, "net_R": null, "min_N_for_0_01R": 35827.264966289666, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 429, "net_R": null, "min_N_for_0_01R": 34750.75744987408, "status": "INSUFFICIENT"}, "SHORT": {"N": 500, "net_R": null, "min_N_for_0_01R": 33969.57809506122, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 370, "net_R": null, "min_N_for_0_01R": 30180.732302741326, "status": "INSUFFICIENT"}, "mid": {"N": 559, "net_R": null, "min_N_for_0_01R": 38902.14299108085, "status": "INSUFFICIENT"}}}
