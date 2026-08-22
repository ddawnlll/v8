# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **MECHANICAL_FLOOR**
Verdict evidence: `{'section3': 'actual -0.1116 inside the random-entry null [-0.1238, -0.0297] (percentile 11.5%) — signal indistinguishable from random entries'}`
configs searched: 31
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=144.6 median=405.3 max=1211 unique=1407

## 1 — Cost census
net_R mean=-0.1116 total=-497.27
gross mean=-0.0416
cost mean=0.0700 (cost is ONE flat R charge per trade (V8 models fee+slippage as a single round_trip_cost_r; no per-leg split, no notional % — the exit-fee-on-exit-notional check is therefore not applicable and the cost is entry-price-independent by construction))
funding mean=0.0000
breakeven gross_R=0.0700
funding-duration corr=None

## 2 — Ablation
actual=-0.1116 no_cost=-0.0416 no_funding=-0.1116 frictionless=-0.0416

## 3 — Null baselines
random-entry median=-0.0783 (actual percentile 11.5%)
inverted=-0.0874 always_long=-0.1109 always_short=-0.1091

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 701, "mean_R": -0.16053820838821248, "mean_duration": 7.831669044222539}, "STOP": {"count": 1902, "mean_R": -1.0501672396406077, "mean_duration": 2.826498422712934}, "TARGET": {"count": 1854, "mean_R": 0.8698393840647084, "mean_duration": 2.72168284789644}}
early-SL: {'n_stopped': 1902, 'n_mfe_gt_half_R_before_stop': 588, 'fraction': 0.30914826498422715, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 1854, 'n_post_exit_gt_2R': 1460, 'fraction': 0.7874865156418555, 'mean_post_exit_max_r': 3.9926779513547235, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 65, 'pessimistic_mean': -0.7301016726988037, 'optimistic_mean': 0.5741225326506688, 'spread_R': 1.3042242053494726}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0817 hit=0.432 overlap=3.10
h=2: net_R=-0.0819 hit=0.436 overlap=6.19
h=4: net_R=-0.0959 hit=0.444 overlap=12.36
h=8: net_R=-0.1274 hit=0.434 overlap=24.69
h=12: net_R=-0.1501 hit=0.444 overlap=36.98
h=24: net_R=-0.1619 hit=0.453 overlap=73.64
h=48: net_R=-0.0718 hit=0.460 overlap=146.03
h=72: net_R=0.1557 hit=0.465 overlap=217.13
h=96: net_R=0.3307 hit=0.465 overlap=286.86
h=120: net_R=0.4416 hit=0.461 overlap=355.31
h=168: net_R=0.5907 hit=0.473 overlap=488.40
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": -1.0416026096652407, "n": 4450}, "2": {"mean_markout_bps": -1.2219373635461115, "n": 4447}, "3": {"mean_markout_bps": -1.6742237732860972, "n": 4444}, "6": {"mean_markout_bps": -3.002812111228469, "n": 4438}, "12": {"mean_markout_bps": -3.868845925846668, "n": 4417}, "24": {"mean_markout_bps": -1.6731045793391597, "n": 4378}}

## 8 — Segments
{"month": {"1": {"N": 210, "net_R": null, "min_N_for_0_01R": 55612.85324724189, "status": "INSUFFICIENT"}, "2": {"N": 2292, "net_R": null, "min_N_for_0_01R": 41889.37244476094, "status": "INSUFFICIENT"}, "3": {"N": 1955, "net_R": null, "min_N_for_0_01R": 42758.19468761979, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 156, "net_R": null, "min_N_for_0_01R": 37201.15849434599, "status": "INSUFFICIENT"}, "1": {"N": 155, "net_R": null, "min_N_for_0_01R": 32427.146796132307, "status": "INSUFFICIENT"}, "2": {"N": 150, "net_R": null, "min_N_for_0_01R": 34315.52295464959, "status": "INSUFFICIENT"}, "3": {"N": 199, "net_R": null, "min_N_for_0_01R": 33266.880788247276, "status": "INSUFFICIENT"}, "4": {"N": 223, "net_R": null, "min_N_for_0_01R": 32447.044182324247, "status": "INSUFFICIENT"}, "5": {"N": 196, "net_R": null, "min_N_for_0_01R": 33310.316058041164, "status": "INSUFFICIENT"}, "6": {"N": 207, "net_R": null, "min_N_for_0_01R": 34958.69687142457, "status": "INSUFFICIENT"}, "7": {"N": 188, "net_R": null, "min_N_for_0_01R": 40687.58303411861, "status": "INSUFFICIENT"}, "8": {"N": 189, "net_R": null, "min_N_for_0_01R": 46555.53773486061, "status": "INSUFFICIENT"}, "9": {"N": 210, "net_R": null, "min_N_for_0_01R": 55368.276828252405, "status": "INSUFFICIENT"}, "10": {"N": 184, "net_R": null, "min_N_for_0_01R": 64346.19307505746, "status": "INSUFFICIENT"}, "11": {"N": 209, "net_R": null, "min_N_for_0_01R": 62842.026676768735, "status": "INSUFFICIENT"}, "12": {"N": 181, "net_R": null, "min_N_for_0_01R": 57957.460079344, "status": "INSUFFICIENT"}, "13": {"N": 194, "net_R": null, "min_N_for_0_01R": 48966.92513818115, "status": "INSUFFICIENT"}, "14": {"N": 178, "net_R": null, "min_N_for_0_01R": 46641.55319827491, "status": "INSUFFICIENT"}, "15": {"N": 190, "net_R": null, "min_N_for_0_01R": 36954.8207314291, "status": "INSUFFICIENT"}, "16": {"N": 209, "net_R": null, "min_N_for_0_01R": 37379.83917976823, "status": "INSUFFICIENT"}, "17": {"N": 221, "net_R": null, "min_N_for_0_01R": 42165.04997601397, "status": "INSUFFICIENT"}, "18": {"N": 185, "net_R": null, "min_N_for_0_01R": 45008.51151441115, "status": "INSUFFICIENT"}, "19": {"N": 170, "net_R": null, "min_N_for_0_01R": 41809.683800129715, "status": "INSUFFICIENT"}, "20": {"N": 180, "net_R": null, "min_N_for_0_01R": 43071.91115512732, "status": "INSUFFICIENT"}, "21": {"N": 165, "net_R": null, "min_N_for_0_01R": 37833.708354067814, "status": "INSUFFICIENT"}, "22": {"N": 166, "net_R": null, "min_N_for_0_01R": 34924.63865450872, "status": "INSUFFICIENT"}, "23": {"N": 152, "net_R": null, "min_N_for_0_01R": 41951.793828957496, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 2197, "net_R": null, "min_N_for_0_01R": 42519.05941050864, "status": "INSUFFICIENT"}, "SHORT": {"N": 2260, "net_R": null, "min_N_for_0_01R": 42136.450134969265, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 32, "net_R": null, "min_N_for_0_01R": 13086.912645227549, "status": "INSUFFICIENT"}, "low": {"N": 3522, "net_R": null, "min_N_for_0_01R": 42608.90428891565, "status": "INSUFFICIENT"}, "mid": {"N": 903, "net_R": null, "min_N_for_0_01R": 45410.88205785096, "status": "INSUFFICIENT"}}}
