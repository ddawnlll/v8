# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0442 inside the random-entry null [-0.1308, -0.0335] (percentile 88.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=0.6207 median=1.482 max=2.846 unique=564

## 1 — Cost census
net_R mean=-0.0442 total=-89.06
gross mean=0.0258
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0442 no_cost=0.0258 no_funding=-0.0442 frictionless=0.0258

## 3 — Null baselines
random-entry median=-0.0783 (actual percentile 88.5%)
inverted=-0.0830 always_long=-0.0439 always_short=-0.0979

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 297, "mean_R": -0.1117024684475496, "mean_duration": 7.505050505050505}, "STOP": {"count": 838, "mean_R": -1.009664964862309, "mean_duration": 2.70763723150358}, "TARGET": {"count": 878, "mean_R": 0.9000214110870358, "mean_duration": 2.7676537585421412}}
early-SL: {'n_stopped': 838, 'n_mfe_gt_half_R_before_stop': 294, 'fraction': 0.35083532219570407, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 878, 'n_post_exit_gt_2R': 670, 'fraction': 0.7630979498861048, 'mean_post_exit_max_r': 3.8408696975488645, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 31, 'pessimistic_mean': -0.6776567617194645, 'optimistic_mean': 0.6177749538800766, 'spread_R': 1.2954317155995412}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0502 hit=0.423 overlap=2.89
h=2: net_R=-0.0650 hit=0.433 overlap=5.77
h=4: net_R=-0.0361 hit=0.454 overlap=11.51
h=8: net_R=-0.0597 hit=0.467 overlap=22.94
h=12: net_R=0.0059 hit=0.477 overlap=34.26
h=24: net_R=-0.0616 hit=0.447 overlap=67.67
h=48: net_R=-0.2140 hit=0.457 overlap=132.52
h=72: net_R=-0.1264 hit=0.449 overlap=194.74
h=96: net_R=-0.1049 hit=0.441 overlap=254.46
h=120: net_R=0.0365 hit=0.445 overlap=311.51
h=168: net_R=-0.0332 hit=0.454 overlap=418.42
actual duration (bars): mean=3.4 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 3.267580023164894, "n": 2003}, "2": {"mean_markout_bps": 3.6662292110734596, "n": 1999}, "3": {"mean_markout_bps": 5.820208442713557, "n": 1996}, "6": {"mean_markout_bps": 10.37676945659365, "n": 1987}, "12": {"mean_markout_bps": 15.810665518785061, "n": 1958}, "24": {"mean_markout_bps": 3.709852650477439, "n": 1917}}

## 8 — Segments
{"month": {"0": {"N": 409, "net_R": null, "min_N_for_0_01R": 38029.9344213665, "status": "INSUFFICIENT"}, "1": {"N": 589, "net_R": null, "min_N_for_0_01R": 38985.16554292405, "status": "INSUFFICIENT"}, "2": {"N": 529, "net_R": null, "min_N_for_0_01R": 41111.535039295886, "status": "INSUFFICIENT"}, "3": {"N": 486, "net_R": null, "min_N_for_0_01R": 44685.07833708456, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 344, "net_R": null, "min_N_for_0_01R": 37576.41397070101, "status": "INSUFFICIENT"}, "4": {"N": 329, "net_R": null, "min_N_for_0_01R": 35588.9911620449, "status": "INSUFFICIENT"}, "8": {"N": 261, "net_R": null, "min_N_for_0_01R": 42611.86206145238, "status": "INSUFFICIENT"}, "12": {"N": 390, "net_R": null, "min_N_for_0_01R": 42028.299861908825, "status": "INSUFFICIENT"}, "16": {"N": 346, "net_R": null, "min_N_for_0_01R": 42417.10645276106, "status": "INSUFFICIENT"}, "20": {"N": 343, "net_R": null, "min_N_for_0_01R": 45327.257233057055, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 970, "net_R": null, "min_N_for_0_01R": 40922.30029188888, "status": "INSUFFICIENT"}, "SHORT": {"N": 1043, "net_R": null, "min_N_for_0_01R": 40927.10346150474, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 1106, "net_R": null, "min_N_for_0_01R": 41390.36672843168, "status": "INSUFFICIENT"}, "mid": {"N": 907, "net_R": null, "min_N_for_0_01R": 40179.383487986976, "status": "INSUFFICIENT"}}}
