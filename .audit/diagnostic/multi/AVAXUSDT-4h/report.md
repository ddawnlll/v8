# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1337 inside the random-entry null [-0.1377, -0.0339] (percentile 6.0%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=0.08614 median=0.1711 max=0.3722 unique=564

## 1 — Cost census
net_R mean=-0.1337 total=-267.76
gross mean=-0.0637
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.1337 no_cost=-0.0637 no_funding=-0.1337 frictionless=-0.0637

## 3 — Null baselines
random-entry median=-0.0860 (actual percentile 6.0%)
inverted=-0.0652 always_long=-0.0956 always_short=-0.0345

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 248, "mean_R": -0.113605854578761, "mean_duration": 7.516129032258065}, "STOP": {"count": 915, "mean_R": -1.0013433536507688, "mean_duration": 2.726775956284153}, "TARGET": {"count": 839, "mean_R": 0.8064906287071119, "mean_duration": 2.65554231227652}}
early-SL: {'n_stopped': 915, 'n_mfe_gt_half_R_before_stop': 291, 'fraction': 0.3180327868852459, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 839, 'n_post_exit_gt_2R': 656, 'fraction': 0.7818831942789034, 'mean_post_exit_max_r': 3.4338383759889375, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 33, 'pessimistic_mean': -0.6400529711016965, 'optimistic_mean': 0.7748199099702193, 'spread_R': 1.4148728810719158}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0614 hit=0.429 overlap=2.88
h=2: net_R=-0.0611 hit=0.436 overlap=5.74
h=4: net_R=-0.0907 hit=0.441 overlap=11.45
h=8: net_R=-0.1520 hit=0.435 overlap=22.82
h=12: net_R=-0.0754 hit=0.450 overlap=34.12
h=24: net_R=-0.0253 hit=0.452 overlap=67.64
h=48: net_R=0.0911 hit=0.460 overlap=132.56
h=72: net_R=0.1180 hit=0.449 overlap=194.88
h=96: net_R=0.0958 hit=0.454 overlap=254.70
h=120: net_R=0.1099 hit=0.456 overlap=311.61
h=168: net_R=0.1667 hit=0.440 overlap=417.96
actual duration (bars): mean=3.3 median=2.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 1.4663915401134497, "n": 1991}, "2": {"mean_markout_bps": 2.24667459746822, "n": 1988}, "3": {"mean_markout_bps": 3.0881263381319255, "n": 1986}, "6": {"mean_markout_bps": -6.160700840816397, "n": 1977}, "12": {"mean_markout_bps": -0.6142065676009978, "n": 1959}, "24": {"mean_markout_bps": 13.352106119283127, "n": 1922}}

## 8 — Segments
{"month": {"0": {"N": 427, "net_R": null, "min_N_for_0_01R": 49911.7215058351, "status": "INSUFFICIENT"}, "1": {"N": 574, "net_R": null, "min_N_for_0_01R": 37877.636745014905, "status": "INSUFFICIENT"}, "2": {"N": 519, "net_R": null, "min_N_for_0_01R": 33072.81405297214, "status": "INSUFFICIENT"}, "3": {"N": 482, "net_R": null, "min_N_for_0_01R": 30805.541416596927, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 361, "net_R": null, "min_N_for_0_01R": 34440.972381928346, "status": "INSUFFICIENT"}, "4": {"N": 297, "net_R": null, "min_N_for_0_01R": 33849.99409111242, "status": "INSUFFICIENT"}, "8": {"N": 270, "net_R": null, "min_N_for_0_01R": 33514.84983320437, "status": "INSUFFICIENT"}, "12": {"N": 381, "net_R": null, "min_N_for_0_01R": 43520.85895704624, "status": "INSUFFICIENT"}, "16": {"N": 364, "net_R": null, "min_N_for_0_01R": 40205.31615116646, "status": "INSUFFICIENT"}, "20": {"N": 329, "net_R": null, "min_N_for_0_01R": 37772.6084209657, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 927, "net_R": null, "min_N_for_0_01R": 35944.076464946396, "status": "INSUFFICIENT"}, "SHORT": {"N": 1075, "net_R": null, "min_N_for_0_01R": 39004.16313444659, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 1167, "net_R": null, "min_N_for_0_01R": 40179.86322156637, "status": "INSUFFICIENT"}, "mid": {"N": 835, "net_R": null, "min_N_for_0_01R": 34016.39918221437, "status": "INSUFFICIENT"}}}
