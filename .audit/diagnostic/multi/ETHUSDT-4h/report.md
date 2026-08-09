# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1227 inside the random-entry null [-0.1316, -0.0372] (percentile 8.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=15.28 median=33.94 max=64.54 unique=657

## 1 — Cost census
net_R mean=-0.1227 total=-239.18
gross mean=-0.0527
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.1227 no_cost=-0.0527 no_funding=-0.1227 frictionless=-0.0527

## 3 — Null baselines
random-entry median=-0.0840 (actual percentile 8.5%)
inverted=-0.0439 always_long=-0.0588 always_short=-0.0662

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 334, "mean_R": -0.21412652321548223, "mean_duration": 7.688622754491018}, "STOP": {"count": 831, "mean_R": -1.010601580299325, "mean_duration": 2.7701564380264743}, "TARGET": {"count": 784, "mean_R": 0.8573331679539589, "mean_duration": 2.857142857142857}}
early-SL: {'n_stopped': 831, 'n_mfe_gt_half_R_before_stop': 296, 'fraction': 0.3561973525872443, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 784, 'n_post_exit_gt_2R': 609, 'fraction': 0.7767857142857143, 'mean_post_exit_max_r': 3.9535186184770206, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 41, 'pessimistic_mean': -0.7036270784936038, 'optimistic_mean': 0.5883761220341198, 'spread_R': 1.2920032005277235}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0805 hit=0.413 overlap=2.80
h=2: net_R=-0.0611 hit=0.432 overlap=5.59
h=4: net_R=-0.0446 hit=0.456 overlap=11.15
h=8: net_R=-0.1638 hit=0.432 overlap=22.19
h=12: net_R=-0.1513 hit=0.432 overlap=33.14
h=24: net_R=-0.2834 hit=0.410 overlap=65.57
h=48: net_R=-0.3034 hit=0.423 overlap=128.60
h=72: net_R=-0.2965 hit=0.441 overlap=188.89
h=96: net_R=-0.1958 hit=0.449 overlap=246.68
h=120: net_R=-0.2057 hit=0.438 overlap=302.08
h=168: net_R=-0.3726 hit=0.438 overlap=405.12
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 0.15028239659514267, "n": 1940}, "2": {"mean_markout_bps": 1.1013326647810997, "n": 1937}, "3": {"mean_markout_bps": 3.849694963430272, "n": 1934}, "6": {"mean_markout_bps": -1.441962538138387, "n": 1918}, "12": {"mean_markout_bps": -3.173232911224762, "n": 1898}, "24": {"mean_markout_bps": -25.374032070666686, "n": 1862}}

## 8 — Segments
{"month": {"0": {"N": 423, "net_R": null, "min_N_for_0_01R": 38597.90082852325, "status": "INSUFFICIENT"}, "1": {"N": 543, "net_R": null, "min_N_for_0_01R": 44943.07693182566, "status": "INSUFFICIENT"}, "2": {"N": 504, "net_R": null, "min_N_for_0_01R": 38248.761473754275, "status": "INSUFFICIENT"}, "3": {"N": 479, "net_R": null, "min_N_for_0_01R": 32017.118458755544, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 334, "net_R": null, "min_N_for_0_01R": 34870.9906947982, "status": "INSUFFICIENT"}, "4": {"N": 306, "net_R": null, "min_N_for_0_01R": 40738.54564162606, "status": "INSUFFICIENT"}, "8": {"N": 251, "net_R": null, "min_N_for_0_01R": 36939.474704836066, "status": "INSUFFICIENT"}, "12": {"N": 366, "net_R": null, "min_N_for_0_01R": 37213.594709215744, "status": "INSUFFICIENT"}, "16": {"N": 347, "net_R": null, "min_N_for_0_01R": 43163.41795245349, "status": "INSUFFICIENT"}, "20": {"N": 345, "net_R": null, "min_N_for_0_01R": 39333.46590250684, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 944, "net_R": null, "min_N_for_0_01R": 38635.22959188983, "status": "INSUFFICIENT"}, "SHORT": {"N": 1005, "net_R": null, "min_N_for_0_01R": 38726.753184582696, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 751, "net_R": null, "min_N_for_0_01R": 33965.45263761049, "status": "INSUFFICIENT"}, "mid": {"N": 1198, "net_R": null, "min_N_for_0_01R": 41674.47092619225, "status": "INSUFFICIENT"}}}
