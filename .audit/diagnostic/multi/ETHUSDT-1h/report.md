# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0999 inside the random-entry null [-0.1307, -0.0395] (percentile 33.0%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=4.669 median=16.4 max=40.73 unique=2623

## 1 — Cost census
net_R mean=-0.0999 total=-865.99
gross mean=-0.0299
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0999 no_cost=-0.0299 no_funding=-0.0999 frictionless=-0.0299

## 3 — Null baselines
random-entry median=-0.0854 (actual percentile 33.0%)
inverted=-0.0718 always_long=-0.1471 always_short=-0.0474

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 1533, "mean_R": -0.15502177861657762, "mean_duration": 7.911937377690802}, "STOP": {"count": 3551, "mean_R": -1.0577833636161358, "mean_duration": 2.783441284145311}, "TARGET": {"count": 3588, "mean_R": 0.8717524330684824, "mean_duration": 2.7842809364548495}}
early-SL: {'n_stopped': 3551, 'n_mfe_gt_half_R_before_stop': 1118, 'fraction': 0.3148408898901718, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 3588, 'n_post_exit_gt_2R': 2781, 'fraction': 0.7750836120401338, 'mean_post_exit_max_r': 4.149545448941863, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 170, 'pessimistic_mean': -0.8286223782862774, 'optimistic_mean': 0.4999891672763352, 'spread_R': 1.3286115455626126}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0785 hit=0.420 overlap=3.11
h=2: net_R=-0.0903 hit=0.440 overlap=6.23
h=4: net_R=-0.0877 hit=0.453 overlap=12.45
h=8: net_R=-0.0859 hit=0.456 overlap=24.88
h=12: net_R=-0.0739 hit=0.463 overlap=37.28
h=24: net_R=-0.0211 hit=0.461 overlap=74.38
h=48: net_R=-0.0274 hit=0.463 overlap=148.13
h=72: net_R=-0.0040 hit=0.461 overlap=221.20
h=96: net_R=0.0499 hit=0.459 overlap=293.48
h=120: net_R=0.1381 hit=0.453 overlap=365.09
h=168: net_R=0.2721 hit=0.449 overlap=506.47
actual duration (bars): mean=3.7 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -0.4910911654278696, "n": 8666}, "2": {"mean_markout_bps": -1.597139546360959, "n": 8661}, "3": {"mean_markout_bps": -1.741491059256417, "n": 8658}, "6": {"mean_markout_bps": -2.749275937571435, "n": 8648}, "12": {"mean_markout_bps": -2.6382204261747897, "n": 8621}, "24": {"mean_markout_bps": 0.8861408610055557, "n": 8589}}

## 8 — Segments
{"month": {"0": {"N": 2182, "net_R": null, "min_N_for_0_01R": 37862.41142915362, "status": "INSUFFICIENT"}, "1": {"N": 2272, "net_R": null, "min_N_for_0_01R": 44445.68700254492, "status": "INSUFFICIENT"}, "2": {"N": 2298, "net_R": null, "min_N_for_0_01R": 45679.908922619274, "status": "INSUFFICIENT"}, "3": {"N": 1919, "net_R": null, "min_N_for_0_01R": 41799.44750044888, "status": "INSUFFICIENT"}, "11": {"N": 1, "net_R": null, "min_N_for_0_01R": Infinity, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 300, "net_R": null, "min_N_for_0_01R": 34507.32995756408, "status": "INSUFFICIENT"}, "1": {"N": 317, "net_R": null, "min_N_for_0_01R": 34933.18585761885, "status": "INSUFFICIENT"}, "2": {"N": 293, "net_R": null, "min_N_for_0_01R": 32743.814344193568, "status": "INSUFFICIENT"}, "3": {"N": 393, "net_R": null, "min_N_for_0_01R": 36335.33819888826, "status": "INSUFFICIENT"}, "4": {"N": 406, "net_R": null, "min_N_for_0_01R": 34884.741254880675, "status": "INSUFFICIENT"}, "5": {"N": 407, "net_R": null, "min_N_for_0_01R": 35835.15718385916, "status": "INSUFFICIENT"}, "6": {"N": 395, "net_R": null, "min_N_for_0_01R": 36639.817115624246, "status": "INSUFFICIENT"}, "7": {"N": 369, "net_R": null, "min_N_for_0_01R": 40207.62235797084, "status": "INSUFFICIENT"}, "8": {"N": 393, "net_R": null, "min_N_for_0_01R": 43267.906923614086, "status": "INSUFFICIENT"}, "9": {"N": 357, "net_R": null, "min_N_for_0_01R": 40616.735981994505, "status": "INSUFFICIENT"}, "10": {"N": 371, "net_R": null, "min_N_for_0_01R": 45415.99628398513, "status": "INSUFFICIENT"}, "11": {"N": 388, "net_R": null, "min_N_for_0_01R": 49596.377842125105, "status": "INSUFFICIENT"}, "12": {"N": 367, "net_R": null, "min_N_for_0_01R": 46458.63674901656, "status": "INSUFFICIENT"}, "13": {"N": 372, "net_R": null, "min_N_for_0_01R": 47210.64008939362, "status": "INSUFFICIENT"}, "14": {"N": 366, "net_R": null, "min_N_for_0_01R": 52396.3882598957, "status": "INSUFFICIENT"}, "15": {"N": 366, "net_R": null, "min_N_for_0_01R": 45826.99611282541, "status": "INSUFFICIENT"}, "16": {"N": 399, "net_R": null, "min_N_for_0_01R": 50968.760007182515, "status": "INSUFFICIENT"}, "17": {"N": 390, "net_R": null, "min_N_for_0_01R": 51674.718163924015, "status": "INSUFFICIENT"}, "18": {"N": 347, "net_R": null, "min_N_for_0_01R": 40116.54200694635, "status": "INSUFFICIENT"}, "19": {"N": 349, "net_R": null, "min_N_for_0_01R": 36889.41830327171, "status": "INSUFFICIENT"}, "20": {"N": 356, "net_R": null, "min_N_for_0_01R": 54428.02899075509, "status": "INSUFFICIENT"}, "21": {"N": 345, "net_R": null, "min_N_for_0_01R": 41000.12127522565, "status": "INSUFFICIENT"}, "22": {"N": 360, "net_R": null, "min_N_for_0_01R": 45102.99137873861, "status": "INSUFFICIENT"}, "23": {"N": 266, "net_R": null, "min_N_for_0_01R": 36899.65594996512, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 4285, "net_R": null, "min_N_for_0_01R": 44446.76211862871, "status": "INSUFFICIENT"}, "SHORT": {"N": 4387, "net_R": null, "min_N_for_0_01R": 40095.7222004339, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 169, "net_R": null, "min_N_for_0_01R": 30377.529880313192, "status": "INSUFFICIENT"}, "low": {"N": 3942, "net_R": null, "min_N_for_0_01R": 45509.79449889519, "status": "INSUFFICIENT"}, "mid": {"N": 4561, "net_R": null, "min_N_for_0_01R": 40429.16766840141, "status": "INSUFFICIENT"}}}
