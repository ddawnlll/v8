# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **COST_DOMINATED**
Verdict evidence: `{'section2': 'frictionless 0.0397 > 0, actual -0.0303 < 0', 'section1': 'breakeven gross 0.0424', 'section3': 'actual percentile of random null 99.5%'}`
configs searched: 451
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=462.8 median=821.7 max=1839 unique=331

## 1 — Cost census
net_R mean=-0.0027 total=-2.38
gross mean=0.0397
cost mean=0.0424 (cost is 5.0 bps of notional, resolved per trade as (bps/1e4) * entry_price / risk_unit — so it MOVES with the R unit. The min/max spread below is the R-unit variation across the window, not noise.)
funding mean=0.0000
breakeven gross_R=0.0424
funding-duration corr=None

## 2 — Ablation
actual=-0.0303 no_cost=0.0397 no_funding=-0.0303 frictionless=0.0397

## 3 — Null baselines
random-entry median=-0.0958 (actual percentile 99.5%)
inverted=-0.1207 always_long=-0.0881 always_short=-0.1124

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 141, "mean_R": -0.08438843276078155, "mean_duration": 7.205673758865248}, "STOP": {"count": 360, "mean_R": -0.9512046040460562, "mean_duration": 2.7}, "TARGET": {"count": 391, "mean_R": 0.900131827474866, "mean_duration": 2.764705882352941}}
early-SL: {'n_stopped': 360, 'n_mfe_gt_half_R_before_stop': 120, 'fraction': 0.3333333333333333, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 391, 'n_post_exit_gt_2R': 294, 'fraction': 0.7519181585677749, 'mean_post_exit_max_r': 4.121875152270246, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 23, 'pessimistic_mean': -0.7297941154190345, 'optimistic_mean': 0.8252905523154632, 'spread_R': 1.5550846677344978}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0224 hit=0.424 overlap=2.48
h=2: net_R=-0.0255 hit=0.457 overlap=4.93
h=4: net_R=-0.0229 hit=0.478 overlap=9.81
h=8: net_R=-0.0605 hit=0.479 overlap=19.44
h=12: net_R=-0.0470 hit=0.457 overlap=28.92
h=24: net_R=-0.1784 hit=0.441 overlap=56.57
h=48: net_R=-0.1412 hit=0.466 overlap=107.96
h=72: net_R=0.0028 hit=0.471 overlap=154.18
h=96: net_R=0.3270 hit=0.479 overlap=196.40
h=120: net_R=0.6311 hit=0.482 overlap=233.55
h=168: net_R=0.6078 hit=0.482 overlap=293.51
actual duration (bars): mean=3.4 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 1.4121907432145981, "n": 883}, "2": {"mean_markout_bps": 2.434340783973528, "n": 879}, "3": {"mean_markout_bps": 3.389666938169242, "n": 876}, "6": {"mean_markout_bps": 3.4728380184345684, "n": 864}, "12": {"mean_markout_bps": 2.139862652578396, "n": 848}, "24": {"mean_markout_bps": -11.975977819423559, "n": 808}}

## 8 — Segments
{"month": {"1": {"N": 10, "net_R": null, "min_N_for_0_01R": 42357.85580404378, "status": "INSUFFICIENT"}, "2": {"N": 420, "net_R": null, "min_N_for_0_01R": 37582.83741447916, "status": "INSUFFICIENT"}, "3": {"N": 462, "net_R": null, "min_N_for_0_01R": 38813.04558960266, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 166, "net_R": null, "min_N_for_0_01R": 38720.885489677006, "status": "INSUFFICIENT"}, "4": {"N": 134, "net_R": null, "min_N_for_0_01R": 34219.53378221641, "status": "INSUFFICIENT"}, "8": {"N": 114, "net_R": null, "min_N_for_0_01R": 40376.190860530114, "status": "INSUFFICIENT"}, "12": {"N": 165, "net_R": null, "min_N_for_0_01R": 36395.66907732572, "status": "INSUFFICIENT"}, "16": {"N": 162, "net_R": null, "min_N_for_0_01R": 41762.18711365382, "status": "INSUFFICIENT"}, "20": {"N": 151, "net_R": null, "min_N_for_0_01R": 38378.022866019885, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 431, "net_R": null, "min_N_for_0_01R": 39608.08842190235, "status": "INSUFFICIENT"}, "SHORT": {"N": 461, "net_R": null, "min_N_for_0_01R": 36179.55212433062, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 136, "net_R": null, "min_N_for_0_01R": 30942.728294670498, "status": "INSUFFICIENT"}, "low": {"N": 29, "net_R": null, "min_N_for_0_01R": 43384.89664030862, "status": "INSUFFICIENT"}, "mid": {"N": 727, "net_R": null, "min_N_for_0_01R": 39606.54189634214, "status": "INSUFFICIENT"}}}
