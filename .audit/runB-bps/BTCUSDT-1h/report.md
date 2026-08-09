# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1116 inside the random-entry null [-0.1411, -0.0463] (percentile 8.0%) — signal indistinguishable from random entries'}`
configs searched: 471
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=144.6 median=405.3 max=1211 unique=1407

## 1 — Cost census
net_R mean=-0.1383 total=-616.26
gross mean=-0.0416
cost mean=0.0967 (cost is 5.0 bps of notional, resolved per trade as (bps/1e4) * entry_price / risk_unit — so it MOVES with the R unit. The min/max spread below is the R-unit variation across the window, not noise.)
funding mean=0.0000
breakeven gross_R=0.0967
funding-duration corr=None

## 2 — Ablation
actual=-0.1116 no_cost=-0.0416 no_funding=-0.1116 frictionless=-0.0416

## 3 — Null baselines
random-entry median=-0.0953 (actual percentile 8.0%)
inverted=-0.1131 always_long=-0.1285 always_short=-0.1260

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 701, "mean_R": -0.17750229031164327, "mean_duration": 7.831669044222539}, "STOP": {"count": 1902, "mean_R": -1.0787140902260426, "mean_duration": 2.826498422712934}, "TARGET": {"count": 1854, "mean_R": 0.8413612698103231, "mean_duration": 2.72168284789644}}
early-SL: {'n_stopped': 1902, 'n_mfe_gt_half_R_before_stop': 588, 'fraction': 0.30914826498422715, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 1854, 'n_post_exit_gt_2R': 1481, 'fraction': 0.7988133764832794, 'mean_post_exit_max_r': 3.9926779513547235, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 65, 'pessimistic_mean': -0.772227888019861, 'optimistic_mean': 0.5319963173296114, 'spread_R': 1.3042242053494724}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.1084 hit=0.415 overlap=3.10
h=2: net_R=-0.1086 hit=0.426 overlap=6.19
h=4: net_R=-0.1225 hit=0.434 overlap=12.36
h=8: net_R=-0.1541 hit=0.429 overlap=24.69
h=12: net_R=-0.1768 hit=0.440 overlap=36.98
h=24: net_R=-0.1886 hit=0.452 overlap=73.64
h=48: net_R=-0.0985 hit=0.458 overlap=146.03
h=72: net_R=0.1290 hit=0.464 overlap=217.13
h=96: net_R=0.3040 hit=0.462 overlap=286.86
h=120: net_R=0.4149 hit=0.460 overlap=355.31
h=168: net_R=0.5640 hit=0.473 overlap=488.40
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -1.0416026096652407, "n": 4450}, "2": {"mean_markout_bps": -1.2219373635461115, "n": 4447}, "3": {"mean_markout_bps": -1.6742237732860972, "n": 4444}, "6": {"mean_markout_bps": -3.002812111228469, "n": 4438}, "12": {"mean_markout_bps": -3.868845925846668, "n": 4417}, "24": {"mean_markout_bps": -1.6731045793391597, "n": 4378}}

## 8 — Segments
{"month": {"1": {"N": 210, "net_R": null, "min_N_for_0_01R": 56457.80121340824, "status": "INSUFFICIENT"}, "2": {"N": 2292, "net_R": null, "min_N_for_0_01R": 42029.237367916176, "status": "INSUFFICIENT"}, "3": {"N": 1955, "net_R": null, "min_N_for_0_01R": 42663.74833604521, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 156, "net_R": null, "min_N_for_0_01R": 37456.865428337536, "status": "INSUFFICIENT"}, "1": {"N": 155, "net_R": null, "min_N_for_0_01R": 32539.886930778448, "status": "INSUFFICIENT"}, "2": {"N": 150, "net_R": null, "min_N_for_0_01R": 34763.435396018045, "status": "INSUFFICIENT"}, "3": {"N": 199, "net_R": null, "min_N_for_0_01R": 33364.878925426165, "status": "INSUFFICIENT"}, "4": {"N": 223, "net_R": null, "min_N_for_0_01R": 32500.573024529724, "status": "INSUFFICIENT"}, "5": {"N": 196, "net_R": null, "min_N_for_0_01R": 33303.436133447714, "status": "INSUFFICIENT"}, "6": {"N": 207, "net_R": null, "min_N_for_0_01R": 34977.308809483155, "status": "INSUFFICIENT"}, "7": {"N": 188, "net_R": null, "min_N_for_0_01R": 40360.89593326458, "status": "INSUFFICIENT"}, "8": {"N": 189, "net_R": null, "min_N_for_0_01R": 46655.93270387445, "status": "INSUFFICIENT"}, "9": {"N": 210, "net_R": null, "min_N_for_0_01R": 55499.75641721989, "status": "INSUFFICIENT"}, "10": {"N": 184, "net_R": null, "min_N_for_0_01R": 64520.96160721749, "status": "INSUFFICIENT"}, "11": {"N": 209, "net_R": null, "min_N_for_0_01R": 62646.19046569898, "status": "INSUFFICIENT"}, "12": {"N": 181, "net_R": null, "min_N_for_0_01R": 58320.15450405824, "status": "INSUFFICIENT"}, "13": {"N": 194, "net_R": null, "min_N_for_0_01R": 48977.36906261912, "status": "INSUFFICIENT"}, "14": {"N": 178, "net_R": null, "min_N_for_0_01R": 46666.90718574983, "status": "INSUFFICIENT"}, "15": {"N": 190, "net_R": null, "min_N_for_0_01R": 36899.70051133249, "status": "INSUFFICIENT"}, "16": {"N": 209, "net_R": null, "min_N_for_0_01R": 37491.31798928085, "status": "INSUFFICIENT"}, "17": {"N": 221, "net_R": null, "min_N_for_0_01R": 42201.15118035795, "status": "INSUFFICIENT"}, "18": {"N": 185, "net_R": null, "min_N_for_0_01R": 45323.38433970702, "status": "INSUFFICIENT"}, "19": {"N": 170, "net_R": null, "min_N_for_0_01R": 42325.67812943083, "status": "INSUFFICIENT"}, "20": {"N": 180, "net_R": null, "min_N_for_0_01R": 43317.85313273432, "status": "INSUFFICIENT"}, "21": {"N": 165, "net_R": null, "min_N_for_0_01R": 37862.021429957815, "status": "INSUFFICIENT"}, "22": {"N": 166, "net_R": null, "min_N_for_0_01R": 34714.15400707556, "status": "INSUFFICIENT"}, "23": {"N": 152, "net_R": null, "min_N_for_0_01R": 42237.628817953504, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 2197, "net_R": null, "min_N_for_0_01R": 42319.33234494697, "status": "INSUFFICIENT"}, "SHORT": {"N": 2260, "net_R": null, "min_N_for_0_01R": 42522.30242704468, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 32, "net_R": null, "min_N_for_0_01R": 13123.847908131043, "status": "INSUFFICIENT"}, "low": {"N": 3522, "net_R": null, "min_N_for_0_01R": 42698.43139788837, "status": "INSUFFICIENT"}, "mid": {"N": 903, "net_R": null, "min_N_for_0_01R": 45428.385743464474, "status": "INSUFFICIENT"}}}
