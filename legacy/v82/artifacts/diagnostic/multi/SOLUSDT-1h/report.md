# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0923 inside the random-entry null [-0.1345, -0.0334] (percentile 40.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=0.2443 median=0.7336 max=1.837 unique=1182

## 1 — Cost census
net_R mean=-0.0923 total=-804.01
gross mean=-0.0223
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0923 no_cost=-0.0223 no_funding=-0.0923 frictionless=-0.0223

## 3 — Null baselines
random-entry median=-0.0825 (actual percentile 40.5%)
inverted=-0.0908 always_long=-0.1230 always_short=-0.0725

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 1369, "mean_R": -0.1286009878710174, "mean_duration": 7.896274653031409}, "STOP": {"count": 3700, "mean_R": -1.0255037788820331, "mean_duration": 2.8216216216216217}, "TARGET": {"count": 3642, "mean_R": 0.86941551499085, "mean_duration": 2.8025809994508513}}
early-SL: {'n_stopped': 3700, 'n_mfe_gt_half_R_before_stop': 1195, 'fraction': 0.32297297297297295, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 3642, 'n_post_exit_gt_2R': 2883, 'fraction': 0.7915980230642504, 'mean_post_exit_max_r': 3.9134963645064476, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 180, 'pessimistic_mean': -0.8269465399142146, 'optimistic_mean': 0.807618081660196, 'spread_R': 1.6345646215744107}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0729 hit=0.427 overlap=3.13
h=2: net_R=-0.0723 hit=0.443 overlap=6.25
h=4: net_R=-0.0754 hit=0.449 overlap=12.50
h=8: net_R=-0.0552 hit=0.466 overlap=24.99
h=12: net_R=-0.0567 hit=0.465 overlap=37.46
h=24: net_R=0.0026 hit=0.469 overlap=74.75
h=48: net_R=0.0173 hit=0.468 overlap=148.84
h=72: net_R=0.1014 hit=0.476 overlap=222.28
h=96: net_R=0.0805 hit=0.467 overlap=294.98
h=120: net_R=0.1019 hit=0.454 overlap=366.92
h=168: net_R=0.1913 hit=0.463 overlap=508.76
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -0.20475873979781337, "n": 8702}, "2": {"mean_markout_bps": -0.5966437343453882, "n": 8700}, "3": {"mean_markout_bps": -0.6805976411077614, "n": 8697}, "6": {"mean_markout_bps": -0.8386633596014571, "n": 8687}, "12": {"mean_markout_bps": -0.7170382720658792, "n": 8670}, "24": {"mean_markout_bps": 2.8442019007317714, "n": 8628}}

## 8 — Segments
{"month": {"0": {"N": 2192, "net_R": null, "min_N_for_0_01R": 37771.7750679512, "status": "INSUFFICIENT"}, "1": {"N": 2259, "net_R": null, "min_N_for_0_01R": 40314.53933747266, "status": "INSUFFICIENT"}, "2": {"N": 2287, "net_R": null, "min_N_for_0_01R": 43431.88246093372, "status": "INSUFFICIENT"}, "3": {"N": 1972, "net_R": null, "min_N_for_0_01R": 44469.61822646857, "status": "INSUFFICIENT"}, "11": {"N": 1, "net_R": null, "min_N_for_0_01R": Infinity, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 303, "net_R": null, "min_N_for_0_01R": 34483.053833017795, "status": "INSUFFICIENT"}, "1": {"N": 293, "net_R": null, "min_N_for_0_01R": 30682.761429196406, "status": "INSUFFICIENT"}, "2": {"N": 299, "net_R": null, "min_N_for_0_01R": 34282.55304507801, "status": "INSUFFICIENT"}, "3": {"N": 388, "net_R": null, "min_N_for_0_01R": 31054.43010469695, "status": "INSUFFICIENT"}, "4": {"N": 395, "net_R": null, "min_N_for_0_01R": 33867.41456053295, "status": "INSUFFICIENT"}, "5": {"N": 427, "net_R": null, "min_N_for_0_01R": 31888.51428003457, "status": "INSUFFICIENT"}, "6": {"N": 387, "net_R": null, "min_N_for_0_01R": 35006.376344489014, "status": "INSUFFICIENT"}, "7": {"N": 374, "net_R": null, "min_N_for_0_01R": 38328.055204554876, "status": "INSUFFICIENT"}, "8": {"N": 388, "net_R": null, "min_N_for_0_01R": 44685.24547056429, "status": "INSUFFICIENT"}, "9": {"N": 390, "net_R": null, "min_N_for_0_01R": 46910.587212889506, "status": "INSUFFICIENT"}, "10": {"N": 360, "net_R": null, "min_N_for_0_01R": 45887.89207023446, "status": "INSUFFICIENT"}, "11": {"N": 382, "net_R": null, "min_N_for_0_01R": 45848.37542506039, "status": "INSUFFICIENT"}, "12": {"N": 368, "net_R": null, "min_N_for_0_01R": 52033.11626556638, "status": "INSUFFICIENT"}, "13": {"N": 372, "net_R": null, "min_N_for_0_01R": 49243.925252319554, "status": "INSUFFICIENT"}, "14": {"N": 380, "net_R": null, "min_N_for_0_01R": 50209.53134297824, "status": "INSUFFICIENT"}, "15": {"N": 387, "net_R": null, "min_N_for_0_01R": 48495.51488187185, "status": "INSUFFICIENT"}, "16": {"N": 378, "net_R": null, "min_N_for_0_01R": 45420.90334766586, "status": "INSUFFICIENT"}, "17": {"N": 379, "net_R": null, "min_N_for_0_01R": 47035.54873100314, "status": "INSUFFICIENT"}, "18": {"N": 370, "net_R": null, "min_N_for_0_01R": 43674.45028672188, "status": "INSUFFICIENT"}, "19": {"N": 352, "net_R": null, "min_N_for_0_01R": 46857.05880665637, "status": "INSUFFICIENT"}, "20": {"N": 358, "net_R": null, "min_N_for_0_01R": 39769.82695817341, "status": "INSUFFICIENT"}, "21": {"N": 353, "net_R": null, "min_N_for_0_01R": 41600.034715714406, "status": "INSUFFICIENT"}, "22": {"N": 366, "net_R": null, "min_N_for_0_01R": 38438.470381901156, "status": "INSUFFICIENT"}, "23": {"N": 262, "net_R": null, "min_N_for_0_01R": 31887.87778425695, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 4254, "net_R": null, "min_N_for_0_01R": 40631.94570492055, "status": "INSUFFICIENT"}, "SHORT": {"N": 4457, "net_R": null, "min_N_for_0_01R": 42090.57133121349, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 331, "net_R": null, "min_N_for_0_01R": 40781.25186547287, "status": "INSUFFICIENT"}, "low": {"N": 3163, "net_R": null, "min_N_for_0_01R": 43598.48579234514, "status": "INSUFFICIENT"}, "mid": {"N": 5217, "net_R": null, "min_N_for_0_01R": 40188.57434746011, "status": "INSUFFICIENT"}}}
