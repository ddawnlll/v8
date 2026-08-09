# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **NO_EDGE**
Verdict evidence: `{'section2': 'frictionless net_R -0.9783 <= 0.01 (no edge even without cost)'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=0.5491 median=0.6145 max=0.769 unique=37

## 1 — Cost census
net_R mean=-1.0483 total=-104.83
gross mean=-0.9783
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-1.0483 no_cost=-0.9783 no_funding=-1.0483 frictionless=-0.9783

## 3 — Null baselines
random-entry median=-0.4005 (actual percentile 0.0%)
inverted=0.0817 always_long=-0.1259 always_short=-0.3984

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 33, "mean_R": -0.817483101533451, "mean_duration": 4.909090909090909}, "STOP": {"count": 43, "mean_R": -2.496873476907733, "mean_duration": 2.046511627906977}, "TARGET": {"count": 24, "mean_R": 1.229885721430166, "mean_duration": 1.75}}
early-SL: {'n_stopped': 43, 'n_mfe_gt_half_R_before_stop': 19, 'fraction': 0.4418604651162791, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 24, 'n_post_exit_gt_2R': 17, 'fraction': 0.7083333333333334, 'mean_post_exit_max_r': 6.0480564660345335, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 3, 'pessimistic_mean': 0.2145536372677558, 'optimistic_mean': 1.574741874601658, 'spread_R': 1.360188237333902}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.1301 hit=0.410 overlap=1.67
h=2: net_R=-0.1493 hit=0.430 overlap=3.15
h=4: net_R=-0.6176 hit=0.370 overlap=6.00
h=8: net_R=-1.2574 hit=0.360 overlap=11.38
h=12: net_R=-1.6867 hit=0.310 overlap=15.90
h=24: net_R=-1.7988 hit=0.250 overlap=24.72
h=48: net_R=-1.5464 hit=0.260 overlap=27.83
h=72: net_R=-1.5464 hit=0.260 overlap=27.83
h=96: net_R=-1.5464 hit=0.260 overlap=27.83
h=120: net_R=-1.5464 hit=0.260 overlap=27.83
h=168: net_R=-1.5464 hit=0.260 overlap=27.83
actual duration (bars): mean=2.9 median=1.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -6.015116399343822, "n": 89}, "2": {"mean_markout_bps": -6.509516722761175, "n": 86}, "3": {"mean_markout_bps": -36.75248859210813, "n": 85}, "6": {"mean_markout_bps": -95.71108978834988, "n": 80}, "12": {"mean_markout_bps": -124.3656712098943, "n": 60}, "24": {"mean_markout_bps": -111.42864268597758, "n": 27}}

## 8 — Segments
{"month": {"3": {"N": 100, "net_R": null, "min_N_for_0_01R": 328628.3985739893, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 5, "net_R": null, "min_N_for_0_01R": 94661.39965597149, "status": "INSUFFICIENT"}, "1": {"N": 5, "net_R": null, "min_N_for_0_01R": 48226.85971826747, "status": "INSUFFICIENT"}, "2": {"N": 5, "net_R": null, "min_N_for_0_01R": 13257.127224920892, "status": "INSUFFICIENT"}, "3": {"N": 13, "net_R": null, "min_N_for_0_01R": 6811.284146714858, "status": "INSUFFICIENT"}, "4": {"N": 4, "net_R": null, "min_N_for_0_01R": 7366.939522896263, "status": "INSUFFICIENT"}, "5": {"N": 2, "net_R": null, "min_N_for_0_01R": 88938.06763748913, "status": "INSUFFICIENT"}, "6": {"N": 2, "net_R": null, "min_N_for_0_01R": 1117141.3876720904, "status": "INSUFFICIENT"}, "7": {"N": 2, "net_R": null, "min_N_for_0_01R": 533079.3445222309, "status": "INSUFFICIENT"}, "8": {"N": 1, "net_R": null, "min_N_for_0_01R": Infinity, "status": "INSUFFICIENT"}, "9": {"N": 2, "net_R": null, "min_N_for_0_01R": 526283.1211007576, "status": "INSUFFICIENT"}, "10": {"N": 2, "net_R": null, "min_N_for_0_01R": 68867.04733990767, "status": "INSUFFICIENT"}, "11": {"N": 5, "net_R": null, "min_N_for_0_01R": 443017.3173786468, "status": "INSUFFICIENT"}, "12": {"N": 5, "net_R": null, "min_N_for_0_01R": 425659.3833888599, "status": "INSUFFICIENT"}, "13": {"N": 7, "net_R": null, "min_N_for_0_01R": 190459.75016086487, "status": "INSUFFICIENT"}, "14": {"N": 6, "net_R": null, "min_N_for_0_01R": 328101.99268181284, "status": "INSUFFICIENT"}, "15": {"N": 1, "net_R": null, "min_N_for_0_01R": Infinity, "status": "INSUFFICIENT"}, "16": {"N": 4, "net_R": null, "min_N_for_0_01R": 36370.28349042084, "status": "INSUFFICIENT"}, "17": {"N": 4, "net_R": null, "min_N_for_0_01R": 257611.36015694967, "status": "INSUFFICIENT"}, "18": {"N": 4, "net_R": null, "min_N_for_0_01R": 170891.69042469008, "status": "INSUFFICIENT"}, "19": {"N": 2, "net_R": null, "min_N_for_0_01R": 162892.1309530138, "status": "INSUFFICIENT"}, "20": {"N": 6, "net_R": null, "min_N_for_0_01R": 438737.43199177156, "status": "INSUFFICIENT"}, "21": {"N": 4, "net_R": null, "min_N_for_0_01R": 515691.5998351885, "status": "INSUFFICIENT"}, "22": {"N": 4, "net_R": null, "min_N_for_0_01R": 369200.6190503159, "status": "INSUFFICIENT"}, "23": {"N": 5, "net_R": null, "min_N_for_0_01R": 81156.25345539644, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 51, "net_R": null, "min_N_for_0_01R": 271139.540920835, "status": "INSUFFICIENT"}, "SHORT": {"N": 49, "net_R": null, "min_N_for_0_01R": 386900.28485048923, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 73, "net_R": null, "min_N_for_0_01R": 258036.72711431887, "status": "INSUFFICIENT"}, "mid": {"N": 27, "net_R": null, "min_N_for_0_01R": 516783.7181324466, "status": "INSUFFICIENT"}}}
