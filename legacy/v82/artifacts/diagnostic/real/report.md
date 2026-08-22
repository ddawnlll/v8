# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.0618 inside the random-entry null [-0.1363, -0.0296] (percentile 78.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=145.3 median=508 max=2710 unique=2466

## 1 — Cost census
net_R mean=-0.0618 total=-497.49
gross mean=0.0082
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.0618 no_cost=0.0082 no_funding=-0.0618 frictionless=0.0082

## 3 — Null baselines
random-entry median=-0.0815 (actual percentile 78.5%)
inverted=-0.0885 always_long=-0.1031 always_short=-0.0625

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 1510, "mean_R": -0.09940901059037166, "mean_duration": 7.909271523178808}, "STOP": {"count": 3211, "mean_R": -1.0401163082146838, "mean_duration": 2.728122080348801}, "TARGET": {"count": 3326, "mean_R": 0.8997078693552495, "mean_duration": 2.7835237522549607}}
early-SL: {'n_stopped': 3211, 'n_mfe_gt_half_R_before_stop': 1077, 'fraction': 0.33540952974151356, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 3326, 'n_post_exit_gt_2R': 2623, 'fraction': 0.7886349969933855, 'mean_post_exit_max_r': 4.479205207881203, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 144, 'pessimistic_mean': -0.8106013127641837, 'optimistic_mean': 0.9785039558809248, 'spread_R': 1.7891052686451085}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0671 hit=0.439 overlap=3.22
h=2: net_R=-0.0662 hit=0.458 overlap=6.43
h=4: net_R=-0.0772 hit=0.460 overlap=12.86
h=8: net_R=-0.0998 hit=0.462 overlap=25.69
h=12: net_R=-0.1149 hit=0.461 overlap=38.50
h=24: net_R=-0.1089 hit=0.457 overlap=76.79
h=48: net_R=-0.1422 hit=0.453 overlap=152.77
h=72: net_R=-0.1838 hit=0.443 overlap=227.99
h=96: net_R=-0.2492 hit=0.440 overlap=302.54
h=120: net_R=-0.1920 hit=0.438 overlap=376.31
h=168: net_R=-0.2246 hit=0.439 overlap=521.71
actual duration (bars): mean=3.7 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -0.04734821033096023, "n": 8037}, "2": {"mean_markout_bps": 0.04139835067833825, "n": 8032}, "3": {"mean_markout_bps": -0.14066150444431155, "n": 8030}, "6": {"mean_markout_bps": 0.06417989352601937, "n": 8019}, "12": {"mean_markout_bps": -1.4401641984993983, "n": 7993}, "24": {"mean_markout_bps": -0.7800774895802461, "n": 7958}}

## 8 — Segments
{"month": {"3": {"N": 684, "net_R": null, "min_N_for_0_01R": 59095.53436780347, "status": "INSUFFICIENT"}, "4": {"N": 2372, "net_R": null, "min_N_for_0_01R": 39316.532976807015, "status": "INSUFFICIENT"}, "5": {"N": 2322, "net_R": null, "min_N_for_0_01R": 44765.95892828996, "status": "INSUFFICIENT"}, "6": {"N": 2329, "net_R": null, "min_N_for_0_01R": 44009.58189714108, "status": "INSUFFICIENT"}, "7": {"N": 340, "net_R": null, "min_N_for_0_01R": 34225.97030085751, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 258, "net_R": null, "min_N_for_0_01R": 32687.784212344923, "status": "INSUFFICIENT"}, "1": {"N": 265, "net_R": null, "min_N_for_0_01R": 32478.033646670967, "status": "INSUFFICIENT"}, "2": {"N": 274, "net_R": null, "min_N_for_0_01R": 39066.1900419462, "status": "INSUFFICIENT"}, "3": {"N": 379, "net_R": null, "min_N_for_0_01R": 39108.495954590166, "status": "INSUFFICIENT"}, "4": {"N": 364, "net_R": null, "min_N_for_0_01R": 32861.96267844594, "status": "INSUFFICIENT"}, "5": {"N": 364, "net_R": null, "min_N_for_0_01R": 37390.72264465575, "status": "INSUFFICIENT"}, "6": {"N": 353, "net_R": null, "min_N_for_0_01R": 37044.31082521235, "status": "INSUFFICIENT"}, "7": {"N": 354, "net_R": null, "min_N_for_0_01R": 48323.84341214313, "status": "INSUFFICIENT"}, "8": {"N": 358, "net_R": null, "min_N_for_0_01R": 52526.830395529425, "status": "INSUFFICIENT"}, "9": {"N": 342, "net_R": null, "min_N_for_0_01R": 54024.29504255627, "status": "INSUFFICIENT"}, "10": {"N": 363, "net_R": null, "min_N_for_0_01R": 55847.05917274844, "status": "INSUFFICIENT"}, "11": {"N": 355, "net_R": null, "min_N_for_0_01R": 57036.99839098747, "status": "INSUFFICIENT"}, "12": {"N": 342, "net_R": null, "min_N_for_0_01R": 56983.95169615458, "status": "INSUFFICIENT"}, "13": {"N": 343, "net_R": null, "min_N_for_0_01R": 56648.784666740714, "status": "INSUFFICIENT"}, "14": {"N": 347, "net_R": null, "min_N_for_0_01R": 49515.22957961496, "status": "INSUFFICIENT"}, "15": {"N": 369, "net_R": null, "min_N_for_0_01R": 45917.62920225999, "status": "INSUFFICIENT"}, "16": {"N": 381, "net_R": null, "min_N_for_0_01R": 47295.507569440466, "status": "INSUFFICIENT"}, "17": {"N": 404, "net_R": null, "min_N_for_0_01R": 42713.54486354249, "status": "INSUFFICIENT"}, "18": {"N": 334, "net_R": null, "min_N_for_0_01R": 37242.0133739163, "status": "INSUFFICIENT"}, "19": {"N": 344, "net_R": null, "min_N_for_0_01R": 45213.30881266317, "status": "INSUFFICIENT"}, "20": {"N": 301, "net_R": null, "min_N_for_0_01R": 35275.95817392803, "status": "INSUFFICIENT"}, "21": {"N": 305, "net_R": null, "min_N_for_0_01R": 36223.461517022646, "status": "INSUFFICIENT"}, "22": {"N": 301, "net_R": null, "min_N_for_0_01R": 30968.785669592737, "status": "INSUFFICIENT"}, "23": {"N": 247, "net_R": null, "min_N_for_0_01R": 31662.276668836563, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 3986, "net_R": null, "min_N_for_0_01R": 43328.30173699677, "status": "INSUFFICIENT"}, "SHORT": {"N": 4061, "net_R": null, "min_N_for_0_01R": 44228.09405691552, "status": "INSUFFICIENT"}}, "vol_tercile": {"low": {"N": 7461, "net_R": null, "min_N_for_0_01R": 44526.32169184611, "status": "INSUFFICIENT"}, "mid": {"N": 586, "net_R": null, "min_N_for_0_01R": 34312.35296529433, "status": "INSUFFICIENT"}}}
