# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1102 inside the random-entry null [-0.1394, -0.0355] (percentile 18.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=112.3 median=436 max=1211 unique=2744

## 1 — Cost census
net_R mean=-0.1102 total=-971.67
gross mean=-0.0402
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.1102 no_cost=-0.0402 no_funding=-0.1102 frictionless=-0.0402

## 3 — Null baselines
random-entry median=-0.0803 (actual percentile 18.5%)
inverted=-0.0660 always_long=-0.1643 always_short=-0.0459

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 1441, "mean_R": -0.18481128130031216, "mean_duration": 7.918112421929216}, "STOP": {"count": 3708, "mean_R": -1.0478730211936202, "mean_duration": 2.778856526429342}, "TARGET": {"count": 3667, "mean_R": 0.8672372528887218, "mean_duration": 2.7071175347695666}}
early-SL: {'n_stopped': 3708, 'n_mfe_gt_half_R_before_stop': 1172, 'fraction': 0.31607335490830635, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 3667, 'n_post_exit_gt_2R': 2903, 'fraction': 0.791655304063267, 'mean_post_exit_max_r': 4.030398619758953, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 146, 'pessimistic_mean': -0.7701244814831592, 'optimistic_mean': 0.7164072789362014, 'spread_R': 1.4865317604193606}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0758 hit=0.434 overlap=3.17
h=2: net_R=-0.0742 hit=0.440 overlap=6.33
h=4: net_R=-0.0817 hit=0.450 overlap=12.66
h=8: net_R=-0.0838 hit=0.451 overlap=25.30
h=12: net_R=-0.0874 hit=0.455 overlap=37.92
h=24: net_R=-0.0820 hit=0.458 overlap=75.67
h=48: net_R=-0.0548 hit=0.456 overlap=150.69
h=72: net_R=0.0923 hit=0.465 overlap=225.04
h=96: net_R=0.1525 hit=0.461 overlap=298.69
h=120: net_R=0.1865 hit=0.451 overlap=371.67
h=168: net_R=0.2347 hit=0.457 overlap=515.67
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -0.5024830927066533, "n": 8809}, "2": {"mean_markout_bps": -0.5612583479218823, "n": 8806}, "3": {"mean_markout_bps": -0.990390728509826, "n": 8803}, "6": {"mean_markout_bps": -1.5325013958465112, "n": 8797}, "12": {"mean_markout_bps": -2.4826939452406194, "n": 8776}, "24": {"mean_markout_bps": -1.3910780663179392, "n": 8737}}

## 8 — Segments
{"month": {"0": {"N": 2210, "net_R": null, "min_N_for_0_01R": 38256.589500680486, "status": "INSUFFICIENT"}, "1": {"N": 2358, "net_R": null, "min_N_for_0_01R": 44342.68171670165, "status": "INSUFFICIENT"}, "2": {"N": 2292, "net_R": null, "min_N_for_0_01R": 41889.37244476094, "status": "INSUFFICIENT"}, "3": {"N": 1955, "net_R": null, "min_N_for_0_01R": 42758.19468761979, "status": "INSUFFICIENT"}, "11": {"N": 1, "net_R": null, "min_N_for_0_01R": Infinity, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 307, "net_R": null, "min_N_for_0_01R": 34268.7564336118, "status": "INSUFFICIENT"}, "1": {"N": 317, "net_R": null, "min_N_for_0_01R": 30855.661539196262, "status": "INSUFFICIENT"}, "2": {"N": 309, "net_R": null, "min_N_for_0_01R": 34821.854616200195, "status": "INSUFFICIENT"}, "3": {"N": 390, "net_R": null, "min_N_for_0_01R": 37126.467663050906, "status": "INSUFFICIENT"}, "4": {"N": 421, "net_R": null, "min_N_for_0_01R": 32047.94959814722, "status": "INSUFFICIENT"}, "5": {"N": 394, "net_R": null, "min_N_for_0_01R": 32800.286707295236, "status": "INSUFFICIENT"}, "6": {"N": 386, "net_R": null, "min_N_for_0_01R": 34107.84340241432, "status": "INSUFFICIENT"}, "7": {"N": 375, "net_R": null, "min_N_for_0_01R": 38931.727795007755, "status": "INSUFFICIENT"}, "8": {"N": 388, "net_R": null, "min_N_for_0_01R": 43558.65429807277, "status": "INSUFFICIENT"}, "9": {"N": 393, "net_R": null, "min_N_for_0_01R": 49506.21377048744, "status": "INSUFFICIENT"}, "10": {"N": 361, "net_R": null, "min_N_for_0_01R": 58612.79118983369, "status": "INSUFFICIENT"}, "11": {"N": 401, "net_R": null, "min_N_for_0_01R": 58224.748046271394, "status": "INSUFFICIENT"}, "12": {"N": 361, "net_R": null, "min_N_for_0_01R": 59063.85863555826, "status": "INSUFFICIENT"}, "13": {"N": 375, "net_R": null, "min_N_for_0_01R": 47420.54560755479, "status": "INSUFFICIENT"}, "14": {"N": 368, "net_R": null, "min_N_for_0_01R": 46109.14103038841, "status": "INSUFFICIENT"}, "15": {"N": 389, "net_R": null, "min_N_for_0_01R": 43924.74035146326, "status": "INSUFFICIENT"}, "16": {"N": 406, "net_R": null, "min_N_for_0_01R": 42552.70863754747, "status": "INSUFFICIENT"}, "17": {"N": 411, "net_R": null, "min_N_for_0_01R": 40703.68094397669, "status": "INSUFFICIENT"}, "18": {"N": 360, "net_R": null, "min_N_for_0_01R": 42655.40253618794, "status": "INSUFFICIENT"}, "19": {"N": 347, "net_R": null, "min_N_for_0_01R": 38242.001932671374, "status": "INSUFFICIENT"}, "20": {"N": 369, "net_R": null, "min_N_for_0_01R": 38824.291907806604, "status": "INSUFFICIENT"}, "21": {"N": 358, "net_R": null, "min_N_for_0_01R": 39131.253712001155, "status": "INSUFFICIENT"}, "22": {"N": 346, "net_R": null, "min_N_for_0_01R": 36861.03671772965, "status": "INSUFFICIENT"}, "23": {"N": 284, "net_R": null, "min_N_for_0_01R": 36555.507135771084, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 4362, "net_R": null, "min_N_for_0_01R": 41180.46416063244, "status": "INSUFFICIENT"}, "SHORT": {"N": 4454, "net_R": null, "min_N_for_0_01R": 42405.63746801361, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 32, "net_R": null, "min_N_for_0_01R": 13086.912645227549, "status": "INSUFFICIENT"}, "low": {"N": 7010, "net_R": null, "min_N_for_0_01R": 42919.36515828297, "status": "INSUFFICIENT"}, "mid": {"N": 1774, "net_R": null, "min_N_for_0_01R": 38010.42013625464, "status": "INSUFFICIENT"}}}
