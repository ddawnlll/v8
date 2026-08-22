# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0995 inside the random-entry null [-0.1361, -0.0411] (percentile 30.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=0.255 median=0.7393 max=1.837 unique=825

## 1 — Cost census
net_R mean=-0.0995 total=-445.79
gross mean=-0.0295
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0995 no_cost=-0.0295 no_funding=-0.0995 frictionless=-0.0295

## 3 — Null baselines
random-entry median=-0.0823 (actual percentile 30.5%)
inverted=-0.1041 always_long=-0.1116 always_short=-0.0855

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 677, "mean_R": -0.15532260094149158, "mean_duration": 7.790251107828656}, "STOP": {"count": 1909, "mean_R": -1.0509593629938154, "mean_duration": 2.8685175484546885}, "TARGET": {"count": 1896, "mean_R": 0.878506696187485, "mean_duration": 2.788502109704641}}
early-SL: {'n_stopped': 1909, 'n_mfe_gt_half_R_before_stop': 597, 'fraction': 0.3127291775798848, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 1896, 'n_post_exit_gt_2R': 1478, 'fraction': 0.7795358649789029, 'mean_post_exit_max_r': 4.003671151642217, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 73, 'pessimistic_mean': -0.7238984122415477, 'optimistic_mean': 0.5963061308841627, 'spread_R': 1.3202045431257106}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0844 hit=0.425 overlap=3.11
h=2: net_R=-0.0758 hit=0.443 overlap=6.22
h=4: net_R=-0.0721 hit=0.450 overlap=12.43
h=8: net_R=-0.0690 hit=0.461 overlap=24.82
h=12: net_R=-0.0806 hit=0.458 overlap=37.18
h=24: net_R=0.0104 hit=0.466 overlap=74.03
h=48: net_R=0.0186 hit=0.466 overlap=146.79
h=72: net_R=0.1803 hit=0.477 overlap=218.28
h=96: net_R=0.2914 hit=0.477 overlap=288.35
h=120: net_R=0.4021 hit=0.458 overlap=356.97
h=168: net_R=0.5677 hit=0.466 overlap=490.22
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -1.1477388436400773, "n": 4473}, "2": {"mean_markout_bps": -1.1864967919382188, "n": 4471}, "3": {"mean_markout_bps": -0.8538232670350762, "n": 4468}, "6": {"mean_markout_bps": -1.5703594728920696, "n": 4458}, "12": {"mean_markout_bps": -2.7315509310688095, "n": 4441}, "24": {"mean_markout_bps": 2.723847541017083, "n": 4399}}

## 8 — Segments
{"month": {"1": {"N": 223, "net_R": null, "min_N_for_0_01R": 48183.96027615193, "status": "INSUFFICIENT"}, "2": {"N": 2287, "net_R": null, "min_N_for_0_01R": 43431.88246093372, "status": "INSUFFICIENT"}, "3": {"N": 1972, "net_R": null, "min_N_for_0_01R": 44469.61822646857, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 161, "net_R": null, "min_N_for_0_01R": 34477.115864139574, "status": "INSUFFICIENT"}, "1": {"N": 154, "net_R": null, "min_N_for_0_01R": 31741.568528900774, "status": "INSUFFICIENT"}, "2": {"N": 149, "net_R": null, "min_N_for_0_01R": 32251.777906920175, "status": "INSUFFICIENT"}, "3": {"N": 198, "net_R": null, "min_N_for_0_01R": 32611.206475345392, "status": "INSUFFICIENT"}, "4": {"N": 212, "net_R": null, "min_N_for_0_01R": 34454.87683545039, "status": "INSUFFICIENT"}, "5": {"N": 210, "net_R": null, "min_N_for_0_01R": 30906.935800651918, "status": "INSUFFICIENT"}, "6": {"N": 203, "net_R": null, "min_N_for_0_01R": 34917.209976728125, "status": "INSUFFICIENT"}, "7": {"N": 196, "net_R": null, "min_N_for_0_01R": 42084.639015492234, "status": "INSUFFICIENT"}, "8": {"N": 207, "net_R": null, "min_N_for_0_01R": 50979.69699739332, "status": "INSUFFICIENT"}, "9": {"N": 195, "net_R": null, "min_N_for_0_01R": 53757.02635772506, "status": "INSUFFICIENT"}, "10": {"N": 177, "net_R": null, "min_N_for_0_01R": 52085.87923124532, "status": "INSUFFICIENT"}, "11": {"N": 199, "net_R": null, "min_N_for_0_01R": 49116.87410555425, "status": "INSUFFICIENT"}, "12": {"N": 193, "net_R": null, "min_N_for_0_01R": 52719.606743720906, "status": "INSUFFICIENT"}, "13": {"N": 200, "net_R": null, "min_N_for_0_01R": 56034.948427046715, "status": "INSUFFICIENT"}, "14": {"N": 199, "net_R": null, "min_N_for_0_01R": 57832.41821455778, "status": "INSUFFICIENT"}, "15": {"N": 199, "net_R": null, "min_N_for_0_01R": 53896.37852423933, "status": "INSUFFICIENT"}, "16": {"N": 204, "net_R": null, "min_N_for_0_01R": 47415.90683526976, "status": "INSUFFICIENT"}, "17": {"N": 199, "net_R": null, "min_N_for_0_01R": 53387.89607291548, "status": "INSUFFICIENT"}, "18": {"N": 185, "net_R": null, "min_N_for_0_01R": 46409.767519263, "status": "INSUFFICIENT"}, "19": {"N": 169, "net_R": null, "min_N_for_0_01R": 51765.34023592002, "status": "INSUFFICIENT"}, "20": {"N": 182, "net_R": null, "min_N_for_0_01R": 40912.3577589524, "status": "INSUFFICIENT"}, "21": {"N": 176, "net_R": null, "min_N_for_0_01R": 38345.08526428996, "status": "INSUFFICIENT"}, "22": {"N": 184, "net_R": null, "min_N_for_0_01R": 37969.99780738449, "status": "INSUFFICIENT"}, "23": {"N": 131, "net_R": null, "min_N_for_0_01R": 31669.570630554514, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 2179, "net_R": null, "min_N_for_0_01R": 43353.79166890611, "status": "INSUFFICIENT"}, "SHORT": {"N": 2303, "net_R": null, "min_N_for_0_01R": 44531.975920019635, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 331, "net_R": null, "min_N_for_0_01R": 40781.25186547287, "status": "INSUFFICIENT"}, "low": {"N": 1299, "net_R": null, "min_N_for_0_01R": 50719.22430398436, "status": "INSUFFICIENT"}, "mid": {"N": 2852, "net_R": null, "min_N_for_0_01R": 41559.28554069153, "status": "INSUFFICIENT"}}}
