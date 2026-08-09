# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0616 inside the random-entry null [-0.1286, -0.0345] (percentile 79.0%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=434.6 median=891.8 max=1839 unique=673

## 1 — Cost census
net_R mean=-0.0616 total=-119.98
gross mean=0.0084
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0616 no_cost=0.0084 no_funding=-0.0616 frictionless=0.0084

## 3 — Null baselines
random-entry median=-0.0851 (actual percentile 79.0%)
inverted=-0.1064 always_long=-0.0943 always_short=-0.0781

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 297, "mean_R": -0.051940908638320925, "mean_duration": 7.622895622895623}, "STOP": {"count": 834, "mean_R": -1.0000740986177212, "mean_duration": 2.675059952038369}, "TARGET": {"count": 818, "mean_R": 0.8918206714393019, "mean_duration": 2.7946210268948657}}
early-SL: {'n_stopped': 834, 'n_mfe_gt_half_R_before_stop': 289, 'fraction': 0.34652278177458035, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 818, 'n_post_exit_gt_2R': 629, 'fraction': 0.7689486552567237, 'mean_post_exit_max_r': 3.8549699017747523, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 33, 'pessimistic_mean': -0.8054787958902815, 'optimistic_mean': 0.695354714884134, 'spread_R': 1.5008335107744155}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0564 hit=0.425 overlap=2.80
h=2: net_R=-0.0580 hit=0.437 overlap=5.59
h=4: net_R=-0.0573 hit=0.452 overlap=11.15
h=8: net_R=-0.1029 hit=0.453 overlap=22.20
h=12: net_R=-0.0761 hit=0.455 overlap=33.18
h=24: net_R=-0.1053 hit=0.455 overlap=65.71
h=48: net_R=-0.1222 hit=0.451 overlap=128.74
h=72: net_R=-0.1561 hit=0.455 overlap=189.09
h=96: net_R=-0.1757 hit=0.448 overlap=247.38
h=120: net_R=-0.1493 hit=0.443 overlap=303.04
h=168: net_R=-0.1744 hit=0.439 overlap=406.95
actual duration (bars): mean=3.5 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 0.4169376042679198, "n": 1940}, "2": {"mean_markout_bps": 0.11339647105560638, "n": 1936}, "3": {"mean_markout_bps": 0.5474848548208102, "n": 1933}, "6": {"mean_markout_bps": -1.4897360959410861, "n": 1921}, "12": {"mean_markout_bps": -2.6172125072349632, "n": 1905}, "24": {"mean_markout_bps": -5.234045890998944, "n": 1865}}

## 8 — Segments
{"month": {"0": {"N": 446, "net_R": null, "min_N_for_0_01R": 42678.89382537208, "status": "INSUFFICIENT"}, "1": {"N": 550, "net_R": null, "min_N_for_0_01R": 49799.324275010375, "status": "INSUFFICIENT"}, "2": {"N": 491, "net_R": null, "min_N_for_0_01R": 36932.35636157006, "status": "INSUFFICIENT"}, "3": {"N": 462, "net_R": null, "min_N_for_0_01R": 38920.79260830139, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 337, "net_R": null, "min_N_for_0_01R": 42873.38673800886, "status": "INSUFFICIENT"}, "4": {"N": 298, "net_R": null, "min_N_for_0_01R": 35437.160051507926, "status": "INSUFFICIENT"}, "8": {"N": 269, "net_R": null, "min_N_for_0_01R": 42638.40161921539, "status": "INSUFFICIENT"}, "12": {"N": 361, "net_R": null, "min_N_for_0_01R": 43578.125468510145, "status": "INSUFFICIENT"}, "16": {"N": 349, "net_R": null, "min_N_for_0_01R": 44593.733714812486, "status": "INSUFFICIENT"}, "20": {"N": 335, "net_R": null, "min_N_for_0_01R": 44132.97560126911, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 958, "net_R": null, "min_N_for_0_01R": 44847.187383996265, "status": "INSUFFICIENT"}, "SHORT": {"N": 991, "net_R": null, "min_N_for_0_01R": 40106.05856634399, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 136, "net_R": null, "min_N_for_0_01R": 30909.074803636988, "status": "INSUFFICIENT"}, "low": {"N": 29, "net_R": null, "min_N_for_0_01R": 43347.08183612274, "status": "INSUFFICIENT"}, "mid": {"N": 1784, "net_R": null, "min_N_for_0_01R": 43311.92547204625, "status": "INSUFFICIENT"}}}
