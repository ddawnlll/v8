# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1054 inside the random-entry null [-0.1399, -0.0469] (percentile 33.5%) — signal indistinguishable from random entries'}`
configs searched: 471
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=5.504 median=14.58 max=40.16 unique=1371

## 1 — Cost census
net_R mean=-0.1054 total=-468.88
gross mean=-0.0354
cost mean=0.0700 (cost is ONE flat R charge per trade (fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction). NOTE: being denominated in R, this charge is invariant to the R unit — widening the risk unit cannot dilute it. Use --cost-bps to price cost as a fraction of notional.)
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.1054 no_cost=-0.0354 no_funding=-0.1054 frictionless=-0.0354

## 3 — Null baselines
random-entry median=-0.0905 (actual percentile 33.5%)
inverted=-0.0628 always_long=-0.1905 always_short=-0.0762

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 781, "mean_R": -0.16908437717336441, "mean_duration": 7.827144686299616}, "STOP": {"count": 1830, "mean_R": -1.0660871026611793, "mean_duration": 2.818032786885246}, "TARGET": {"count": 1838, "mean_R": 0.8781882283120804, "mean_duration": 2.792709466811752}}
early-SL: {'n_stopped': 1830, 'n_mfe_gt_half_R_before_stop': 555, 'fraction': 0.30327868852459017, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 1838, 'n_post_exit_gt_2R': 1441, 'fraction': 0.7840043525571273, 'mean_post_exit_max_r': 4.132791146622784, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 70, 'pessimistic_mean': -0.7859590393385858, 'optimistic_mean': 0.5859012445527356, 'spread_R': 1.3718602838913214}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0823 hit=0.418 overlap=3.09
h=2: net_R=-0.0898 hit=0.443 overlap=6.17
h=4: net_R=-0.0822 hit=0.455 overlap=12.34
h=8: net_R=-0.1030 hit=0.447 overlap=24.63
h=12: net_R=-0.1149 hit=0.453 overlap=36.88
h=24: net_R=-0.0099 hit=0.458 overlap=73.41
h=48: net_R=0.0239 hit=0.469 overlap=145.62
h=72: net_R=0.1030 hit=0.463 overlap=216.50
h=96: net_R=0.2558 hit=0.467 overlap=285.86
h=120: net_R=0.4196 hit=0.456 overlap=353.92
h=168: net_R=0.6496 hit=0.453 overlap=486.50
actual duration (bars): mean=3.7 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -0.6156487378730234, "n": 4443}, "2": {"mean_markout_bps": -0.9650726018540182, "n": 4438}, "3": {"mean_markout_bps": -0.46350948665128777, "n": 4435}, "6": {"mean_markout_bps": -2.052652901725038, "n": 4425}, "12": {"mean_markout_bps": -3.1191641282784763, "n": 4398}, "24": {"mean_markout_bps": 3.898752913385895, "n": 4366}}

## 8 — Segments
{"month": {"1": {"N": 233, "net_R": null, "min_N_for_0_01R": 49276.247341696464, "status": "INSUFFICIENT"}, "2": {"N": 2297, "net_R": null, "min_N_for_0_01R": 45694.545274520024, "status": "INSUFFICIENT"}, "3": {"N": 1919, "net_R": null, "min_N_for_0_01R": 41799.44750044888, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 153, "net_R": null, "min_N_for_0_01R": 35764.49802745635, "status": "INSUFFICIENT"}, "1": {"N": 152, "net_R": null, "min_N_for_0_01R": 32431.222774944803, "status": "INSUFFICIENT"}, "2": {"N": 134, "net_R": null, "min_N_for_0_01R": 31990.386186114563, "status": "INSUFFICIENT"}, "3": {"N": 199, "net_R": null, "min_N_for_0_01R": 33252.234193248376, "status": "INSUFFICIENT"}, "4": {"N": 210, "net_R": null, "min_N_for_0_01R": 33388.82311790177, "status": "INSUFFICIENT"}, "5": {"N": 199, "net_R": null, "min_N_for_0_01R": 35878.19254742176, "status": "INSUFFICIENT"}, "6": {"N": 190, "net_R": null, "min_N_for_0_01R": 35665.86680881547, "status": "INSUFFICIENT"}, "7": {"N": 194, "net_R": null, "min_N_for_0_01R": 43358.625868150266, "status": "INSUFFICIENT"}, "8": {"N": 206, "net_R": null, "min_N_for_0_01R": 42703.34616072576, "status": "INSUFFICIENT"}, "9": {"N": 189, "net_R": null, "min_N_for_0_01R": 42797.87528873203, "status": "INSUFFICIENT"}, "10": {"N": 186, "net_R": null, "min_N_for_0_01R": 50107.78499998369, "status": "INSUFFICIENT"}, "11": {"N": 207, "net_R": null, "min_N_for_0_01R": 54023.18534294014, "status": "INSUFFICIENT"}, "12": {"N": 188, "net_R": null, "min_N_for_0_01R": 53395.39159927826, "status": "INSUFFICIENT"}, "13": {"N": 195, "net_R": null, "min_N_for_0_01R": 60109.95047112818, "status": "INSUFFICIENT"}, "14": {"N": 199, "net_R": null, "min_N_for_0_01R": 59212.021918411214, "status": "INSUFFICIENT"}, "15": {"N": 193, "net_R": null, "min_N_for_0_01R": 47771.90944665399, "status": "INSUFFICIENT"}, "16": {"N": 214, "net_R": null, "min_N_for_0_01R": 56128.23466553045, "status": "INSUFFICIENT"}, "17": {"N": 214, "net_R": null, "min_N_for_0_01R": 62260.358922011146, "status": "INSUFFICIENT"}, "18": {"N": 180, "net_R": null, "min_N_for_0_01R": 41230.75636479704, "status": "INSUFFICIENT"}, "19": {"N": 177, "net_R": null, "min_N_for_0_01R": 42209.035305320744, "status": "INSUFFICIENT"}, "20": {"N": 181, "net_R": null, "min_N_for_0_01R": 46422.738591007255, "status": "INSUFFICIENT"}, "21": {"N": 170, "net_R": null, "min_N_for_0_01R": 31841.482246028114, "status": "INSUFFICIENT"}, "22": {"N": 185, "net_R": null, "min_N_for_0_01R": 35971.10172119053, "status": "INSUFFICIENT"}, "23": {"N": 134, "net_R": null, "min_N_for_0_01R": 34873.55118208408, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 2179, "net_R": null, "min_N_for_0_01R": 45691.390905744, "status": "INSUFFICIENT"}, "SHORT": {"N": 2270, "net_R": null, "min_N_for_0_01R": 40991.49945306363, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 169, "net_R": null, "min_N_for_0_01R": 30377.529880313192, "status": "INSUFFICIENT"}, "low": {"N": 2168, "net_R": null, "min_N_for_0_01R": 46646.93316082633, "status": "INSUFFICIENT"}, "mid": {"N": 2112, "net_R": null, "min_N_for_0_01R": 42959.78632743238, "status": "INSUFFICIENT"}}}
