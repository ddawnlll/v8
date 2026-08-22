# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0690 inside the random-entry null [-0.1246, -0.0232] (percentile 60.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=0.03129 median=0.08186 max=0.2236 unique=1220

## 1 — Cost census
net_R mean=-0.0690 total=-602.43
gross mean=0.0010
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0690 no_cost=0.0010 no_funding=-0.0690 frictionless=0.0010

## 3 — Null baselines
random-entry median=-0.0755 (actual percentile 60.5%)
inverted=-0.0977 always_long=-0.1542 always_short=-0.0227

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 1273, "mean_R": -0.2080772822981673, "mean_duration": 7.904948939512962}, "STOP": {"count": 3623, "mean_R": -1.0233079727661043, "mean_duration": 2.715705216671267}, "TARGET": {"count": 3841, "mean_R": 0.8773500148092465, "mean_duration": 2.783910439989586}}
early-SL: {'n_stopped': 3623, 'n_mfe_gt_half_R_before_stop': 1074, 'fraction': 0.2964394148495722, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 3841, 'n_post_exit_gt_2R': 3018, 'fraction': 0.785732882061963, 'mean_post_exit_max_r': 3.7825668765433824, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 102, 'pessimistic_mean': -0.6175594761394917, 'optimistic_mean': 0.6237736686207948, 'spread_R': 1.2413331447602864}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0652 hit=0.432 overlap=3.14
h=2: net_R=-0.0604 hit=0.454 overlap=6.28
h=4: net_R=-0.0614 hit=0.462 overlap=12.54
h=8: net_R=-0.0462 hit=0.473 overlap=25.07
h=12: net_R=-0.0583 hit=0.471 overlap=37.57
h=24: net_R=-0.0900 hit=0.463 overlap=74.97
h=48: net_R=-0.0894 hit=0.453 overlap=149.30
h=72: net_R=-0.0975 hit=0.459 overlap=223.06
h=96: net_R=-0.0424 hit=0.454 overlap=296.13
h=120: net_R=-0.0642 hit=0.445 overlap=368.44
h=168: net_R=0.0910 hit=0.458 overlap=510.82
actual duration (bars): mean=3.5 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 0.575469775607455, "n": 8733}, "2": {"mean_markout_bps": 0.49050740295306544, "n": 8729}, "3": {"mean_markout_bps": 0.26336008382844556, "n": 8726}, "6": {"mean_markout_bps": -0.5329173963664974, "n": 8713}, "12": {"mean_markout_bps": -2.0919462654128327, "n": 8693}, "24": {"mean_markout_bps": -2.1912670930186615, "n": 8654}}

## 8 — Segments
{"month": {"0": {"N": 2157, "net_R": null, "min_N_for_0_01R": 39432.35952907957, "status": "INSUFFICIENT"}, "1": {"N": 2285, "net_R": null, "min_N_for_0_01R": 41333.75880826012, "status": "INSUFFICIENT"}, "2": {"N": 2316, "net_R": null, "min_N_for_0_01R": 43188.583935641436, "status": "INSUFFICIENT"}, "3": {"N": 1978, "net_R": null, "min_N_for_0_01R": 43828.9121752433, "status": "INSUFFICIENT"}, "11": {"N": 1, "net_R": null, "min_N_for_0_01R": Infinity, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 291, "net_R": null, "min_N_for_0_01R": 37029.31446038226, "status": "INSUFFICIENT"}, "1": {"N": 304, "net_R": null, "min_N_for_0_01R": 32276.946304033227, "status": "INSUFFICIENT"}, "2": {"N": 301, "net_R": null, "min_N_for_0_01R": 33569.073200808874, "status": "INSUFFICIENT"}, "3": {"N": 411, "net_R": null, "min_N_for_0_01R": 35539.82754408576, "status": "INSUFFICIENT"}, "4": {"N": 409, "net_R": null, "min_N_for_0_01R": 34962.81560030229, "status": "INSUFFICIENT"}, "5": {"N": 397, "net_R": null, "min_N_for_0_01R": 37903.80545184627, "status": "INSUFFICIENT"}, "6": {"N": 383, "net_R": null, "min_N_for_0_01R": 36717.29770892132, "status": "INSUFFICIENT"}, "7": {"N": 379, "net_R": null, "min_N_for_0_01R": 37050.99718078379, "status": "INSUFFICIENT"}, "8": {"N": 399, "net_R": null, "min_N_for_0_01R": 42966.33774596042, "status": "INSUFFICIENT"}, "9": {"N": 364, "net_R": null, "min_N_for_0_01R": 42543.6621568224, "status": "INSUFFICIENT"}, "10": {"N": 367, "net_R": null, "min_N_for_0_01R": 47818.935067423896, "status": "INSUFFICIENT"}, "11": {"N": 383, "net_R": null, "min_N_for_0_01R": 52556.13435412236, "status": "INSUFFICIENT"}, "12": {"N": 380, "net_R": null, "min_N_for_0_01R": 56845.07255685918, "status": "INSUFFICIENT"}, "13": {"N": 366, "net_R": null, "min_N_for_0_01R": 45271.423192348615, "status": "INSUFFICIENT"}, "14": {"N": 382, "net_R": null, "min_N_for_0_01R": 44654.85886395843, "status": "INSUFFICIENT"}, "15": {"N": 366, "net_R": null, "min_N_for_0_01R": 48039.411262219284, "status": "INSUFFICIENT"}, "16": {"N": 397, "net_R": null, "min_N_for_0_01R": 42109.580971678726, "status": "INSUFFICIENT"}, "17": {"N": 382, "net_R": null, "min_N_for_0_01R": 44132.11937968217, "status": "INSUFFICIENT"}, "18": {"N": 389, "net_R": null, "min_N_for_0_01R": 46939.339742817225, "status": "INSUFFICIENT"}, "19": {"N": 345, "net_R": null, "min_N_for_0_01R": 44094.35443399481, "status": "INSUFFICIENT"}, "20": {"N": 363, "net_R": null, "min_N_for_0_01R": 41031.09170408764, "status": "INSUFFICIENT"}, "21": {"N": 343, "net_R": null, "min_N_for_0_01R": 40347.52999010855, "status": "INSUFFICIENT"}, "22": {"N": 351, "net_R": null, "min_N_for_0_01R": 37915.33581992914, "status": "INSUFFICIENT"}, "23": {"N": 285, "net_R": null, "min_N_for_0_01R": 37450.098816355094, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 4283, "net_R": null, "min_N_for_0_01R": 41126.22552858831, "status": "INSUFFICIENT"}, "SHORT": {"N": 4454, "net_R": null, "min_N_for_0_01R": 42055.97634180622, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 440, "net_R": null, "min_N_for_0_01R": 38954.36491785935, "status": "INSUFFICIENT"}, "low": {"N": 2742, "net_R": null, "min_N_for_0_01R": 44645.924406839484, "status": "INSUFFICIENT"}, "mid": {"N": 5555, "net_R": null, "min_N_for_0_01R": 40800.089629598464, "status": "INSUFFICIENT"}}}
