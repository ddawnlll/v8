# Diagnostic report

AUTHORITY: NONE — DIAGNOSTIC ONLY
VERDICT: **NO_EDGE**
Verdict evidence: `{'section2': 'frictionless net_R -0.0686 <= 0.01 (no edge even without cost)'}`
configs searched: 431
PROMOTION_REQUIRES: new preregistration

## 9 — Simulator invariants
ok=True n_fails=0

## 0 — Identity + R denominator
identity_ok=True violations=0
R unit: min=15.28 median=30.3 max=64.54 unique=330

## 1 — Cost census
net_R mean=-0.1010 total=-93.86
gross mean=-0.0686
cost mean=0.0324 (cost is 5.0 bps of notional, resolved per trade as (bps/1e4) * entry_price / risk_unit — so it MOVES with the R unit. The min/max spread below is the R-unit variation across the window, not noise.)
funding mean=0.0000
breakeven gross_R=0.0324
funding-duration corr=None

## 2 — Ablation
actual=-0.1386 no_cost=-0.0686 no_funding=-0.1386 frictionless=-0.0686

## 3 — Null baselines
random-entry median=-0.0845 (actual percentile 29.5%)
inverted=-0.0639 always_long=-0.1231 always_short=-0.0714

## 4 — Path statistics
exit reasons: {"EXPIRY": {"count": 184, "mean_R": -0.1747268076136532, "mean_duration": 7.434782608695652}, "STOP": {"count": 388, "mean_R": -0.9530798916595112, "mean_duration": 2.618556701030928}, "TARGET": {"count": 357, "mean_R": 0.8629797376272865, "mean_duration": 2.7899159663865545}}
early-SL: {'n_stopped': 388, 'n_mfe_gt_half_R_before_stop': 137, 'fraction': 0.35309278350515466, 'meaning': 'a stop that saw >0.5R favorable first suggests an intrabar SL/TP ordering problem'}
early-TP: {'n_target': 357, 'n_post_exit_gt_2R': 253, 'fraction': 0.7086834733893558, 'mean_post_exit_max_r': 4.528248457624677, 'meaning': 'a target that continued >2R after exit suggests the TP is too tight'}
ambiguity: {'ambiguous_count': 30, 'pessimistic_mean': -0.6604763769215951, 'optimistic_mean': 0.724236916965985, 'spread_R': 1.3847132938875801}

## 5 — Horizon sweep (bars = 1h)
h=1: net_R=-0.0391 hit=0.434 overlap=2.58
h=2: net_R=-0.0185 hit=0.451 overlap=5.14
h=4: net_R=0.0027 hit=0.455 overlap=10.22
h=8: net_R=-0.1056 hit=0.439 overlap=20.24
h=12: net_R=-0.0984 hit=0.432 overlap=30.07
h=24: net_R=-0.2513 hit=0.420 overlap=58.78
h=48: net_R=-0.2202 hit=0.437 overlap=112.62
h=72: net_R=-0.0757 hit=0.451 overlap=161.18
h=96: net_R=0.1144 hit=0.476 overlap=204.91
h=120: net_R=0.3934 hit=0.475 overlap=244.03
h=168: net_R=0.2025 hit=0.476 overlap=307.24
actual duration (bars): mean=3.6 median=3.0 p90=8.0

## 6 — Exit surface
(not run; --allow-surface required)

## 7 — Entry timing (mark-out bps)
{"1": {"mean_markout_bps": 2.0607133533882087, "n": 920}, "2": {"mean_markout_bps": 3.7544888741912237, "n": 917}, "3": {"mean_markout_bps": 8.248133181825596, "n": 914}, "6": {"mean_markout_bps": 4.785377490156443, "n": 898}, "12": {"mean_markout_bps": 4.484080845079058, "n": 878}, "24": {"mean_markout_bps": -15.674119928952853, "n": 842}}

## 8 — Segments
{"month": {"1": {"N": 6, "net_R": null, "min_N_for_0_01R": 63100.27173931545, "status": "INSUFFICIENT"}, "2": {"N": 444, "net_R": null, "min_N_for_0_01R": 38543.47654897681, "status": "INSUFFICIENT"}, "3": {"N": 479, "net_R": null, "min_N_for_0_01R": 32050.53663879848, "status": "INSUFFICIENT"}}, "session_hour": {"0": {"N": 174, "net_R": null, "min_N_for_0_01R": 32479.42161047815, "status": "INSUFFICIENT"}, "4": {"N": 141, "net_R": null, "min_N_for_0_01R": 36147.90892775483, "status": "INSUFFICIENT"}, "8": {"N": 120, "net_R": null, "min_N_for_0_01R": 34148.09247415624, "status": "INSUFFICIENT"}, "12": {"N": 169, "net_R": null, "min_N_for_0_01R": 35380.65593649482, "status": "INSUFFICIENT"}, "16": {"N": 168, "net_R": null, "min_N_for_0_01R": 38742.22295802087, "status": "INSUFFICIENT"}, "20": {"N": 157, "net_R": null, "min_N_for_0_01R": 35958.22711698926, "status": "INSUFFICIENT"}}, "side": {"LONG": {"N": 429, "net_R": null, "min_N_for_0_01R": 34942.83920019197, "status": "INSUFFICIENT"}, "SHORT": {"N": 500, "net_R": null, "min_N_for_0_01R": 33968.68036644763, "status": "INSUFFICIENT"}}, "vol_tercile": {"high": {"N": 370, "net_R": null, "min_N_for_0_01R": 30200.862750325945, "status": "INSUFFICIENT"}, "mid": {"N": 559, "net_R": null, "min_N_for_0_01R": 38971.6648022984, "status": "INSUFFICIENT"}}}
