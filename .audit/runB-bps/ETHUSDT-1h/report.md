# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1054 inside the random-entry null [-0.1369, -0.0437] (percentile 25.5%) — signal indistinguishable from random entries'}`
configs searched: 471
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=5.504 median=14.58 max=40.16 unique=1371

## 1 — Cost census
net_R mean=-0.1092 total=-485.83
gross mean=-0.0354
cost mean=0.0738 (cost is 5.0 bps of notional, resolved per trade as (bps/1e4) * entry_price / risk_unit — so it MOVES with the R unit. The min/max spread below is the R-unit variation across the window, not noise.)
funding mean=0.0000
breakeven gross_R=0.0738
funding-duration corr=None

## 2 — Ablation
actual=-0.1054 no_cost=-0.0354 no_funding=-0.1054 frictionless=-0.0354

## 3 — Null baselines
random-entry median=-0.0873 (actual percentile 25.5%)
inverted=-0.0660 always_long=-0.1871 always_short=-0.0732

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 781, "mean_R": -0.16491408962550158, "mean_duration": 7.827144686299616}, "STOP": {"count": 1830, "mean_R": -1.0714161827614088, "mean_duration": 2.818032786885246}, "TARGET": {"count": 1838, "mean_R": 0.8725023507556966, "mean_duration": 2.792709466811752}}
early-SL: {'n_stopped': 1830, 'n_mfe_gt_half_R_before_stop': 555, 'fraction': 0.30327868852459017, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 1838, 'n_post_exit_gt_2R': 1441, 'fraction': 0.7840043525571273, 'mean_post_exit_max_r': 4.132791146622784, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 70, 'pessimistic_mean': -0.8022824457464621, 'optimistic_mean': 0.5695778381448592, 'spread_R': 1.3718602838913214}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0861 hit=0.418 overlap=3.09
h=2: net_R=-0.0936 hit=0.439 overlap=6.17
h=4: net_R=-0.0860 hit=0.452 overlap=12.34
h=8: net_R=-0.1069 hit=0.448 overlap=24.63
h=12: net_R=-0.1187 hit=0.452 overlap=36.88
h=24: net_R=-0.0137 hit=0.457 overlap=73.41
h=48: net_R=0.0201 hit=0.470 overlap=145.62
h=72: net_R=0.0991 hit=0.465 overlap=216.50
h=96: net_R=0.2520 hit=0.469 overlap=285.86
h=120: net_R=0.4157 hit=0.458 overlap=353.92
h=168: net_R=0.6458 hit=0.455 overlap=486.50
actual duration (bars): mean=3.7 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -0.6156487378730234, "n": 4443}, "2": {"mean_markout_bps": -0.9650726018540182, "n": 4438}, "3": {"mean_markout_bps": -0.46350948665128777, "n": 4435}, "6": {"mean_markout_bps": -2.052652901725038, "n": 4425}, "12": {"mean_markout_bps": -3.1191641282784763, "n": 4398}, "24": {"mean_markout_bps": 3.898752913385895, "n": 4366}}

## 8 — Segments
{"month": {"1": {"N": 233, "net_R": null, "min_N_for_0_01R": 49757.435884480765, "status": "INSUFFICIENT"}, "2": {"N": 2297, "net_R": null, "min_N_for_0_01R": 45705.643774016826, "status": "INSUFFICIENT"}, "3": {"N": 1919, "net_R": null, "min_N_for_0_01R": 41949.92920255884, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 153, "net_R": null, "min_N_for_0_01R": 36118.74333582276, "status": "INSUFFICIENT"}, "1": {"N": 152, "net_R": null, "min_N_for_0_01R": 32558.439023449875, "status": "INSUFFICIENT"}, "2": {"N": 134, "net_R": null, "min_N_for_0_01R": 32095.14056148922, "status": "INSUFFICIENT"}, "3": {"N": 199, "net_R": null, "min_N_for_0_01R": 33594.020656804394, "status": "INSUFFICIENT"}, "4": {"N": 210, "net_R": null, "min_N_for_0_01R": 33446.412048375016, "status": "INSUFFICIENT"}, "5": {"N": 199, "net_R": null, "min_N_for_0_01R": 35925.09187008275, "status": "INSUFFICIENT"}, "6": {"N": 190, "net_R": null, "min_N_for_0_01R": 35674.128661010574, "status": "INSUFFICIENT"}, "7": {"N": 194, "net_R": null, "min_N_for_0_01R": 43378.948797631296, "status": "INSUFFICIENT"}, "8": {"N": 206, "net_R": null, "min_N_for_0_01R": 42458.901248097376, "status": "INSUFFICIENT"}, "9": {"N": 189, "net_R": null, "min_N_for_0_01R": 42533.72660957299, "status": "INSUFFICIENT"}, "10": {"N": 186, "net_R": null, "min_N_for_0_01R": 49939.87532005719, "status": "INSUFFICIENT"}, "11": {"N": 207, "net_R": null, "min_N_for_0_01R": 54035.83742585039, "status": "INSUFFICIENT"}, "12": {"N": 188, "net_R": null, "min_N_for_0_01R": 53340.935104932905, "status": "INSUFFICIENT"}, "13": {"N": 195, "net_R": null, "min_N_for_0_01R": 59963.61233921393, "status": "INSUFFICIENT"}, "14": {"N": 199, "net_R": null, "min_N_for_0_01R": 59386.225062896534, "status": "INSUFFICIENT"}, "15": {"N": 193, "net_R": null, "min_N_for_0_01R": 47787.0022470397, "status": "INSUFFICIENT"}, "16": {"N": 214, "net_R": null, "min_N_for_0_01R": 56126.52021707201, "status": "INSUFFICIENT"}, "17": {"N": 214, "net_R": null, "min_N_for_0_01R": 62337.948479501945, "status": "INSUFFICIENT"}, "18": {"N": 180, "net_R": null, "min_N_for_0_01R": 41676.04798734299, "status": "INSUFFICIENT"}, "19": {"N": 177, "net_R": null, "min_N_for_0_01R": 42809.691611136055, "status": "INSUFFICIENT"}, "20": {"N": 181, "net_R": null, "min_N_for_0_01R": 46841.58535273421, "status": "INSUFFICIENT"}, "21": {"N": 170, "net_R": null, "min_N_for_0_01R": 31929.881103830412, "status": "INSUFFICIENT"}, "22": {"N": 185, "net_R": null, "min_N_for_0_01R": 35813.934252090155, "status": "INSUFFICIENT"}, "23": {"N": 134, "net_R": null, "min_N_for_0_01R": 35124.25802365964, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 2179, "net_R": null, "min_N_for_0_01R": 45698.64348727847, "status": "INSUFFICIENT"}, "SHORT": {"N": 2270, "net_R": null, "min_N_for_0_01R": 41175.38419523379, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 169, "net_R": null, "min_N_for_0_01R": 30377.11967278667, "status": "INSUFFICIENT"}, "low": {"N": 2168, "net_R": null, "min_N_for_0_01R": 46678.23493657329, "status": "INSUFFICIENT"}, "mid": {"N": 2112, "net_R": null, "min_N_for_0_01R": 43036.66135446776, "status": "INSUFFICIENT"}}}
