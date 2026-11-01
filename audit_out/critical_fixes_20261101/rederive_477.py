"""Re-derive the COMMITTED bound receipt's capacity block through the #477 producer.

The committed receipt docs/evidence/v87/NX02/bound_receipt_after.json was minted before
the fix and publishes the extrapolated 1%/5%/10% bounds as MEASURED_LINEAR_BOUND.
Its own recorded observed_peak_participation is the input the producer needs, so the
same numbers can be re-derived without the tape. Nothing is hand-edited; the real
producer is called.
"""
import json
from pathlib import Path

from v8_next.app.portfolio import capacity_from_participation

receipt = json.loads(Path("../docs/evidence/v87/NX02/bound_receipt_after.json").read_text())
scen = receipt["capacity_scenarios"]
bounds = [s for s in scen if "max_capital_linear" in s]
peak = bounds[0]["observed_peak_participation"]
capital = 10000.0

print(f"recorded observed_peak_participation : {peak!r}")
print(f"recorded thresholds                  : {[b['participation_threshold'] for b in bounds]}")
print()
print("BEFORE (as committed in the receipt)")
for b in bounds:
    print(f"  thr={b['participation_threshold']:<6} kind={b['kind']:<22} "
          f"max_capital_linear={b['max_capital_linear']:.4f}  status={b.get('status', '<ABSENT>')}")
print()
new = capacity_from_participation([peak], capital, [0.001, -0.002, 0.0015] * 50)
new_bounds = [r for r in new if "max_capital_linear" in r]
print("AFTER (same recorded inputs, through the #477 producer)")
for b in new_bounds:
    print(f"  thr={b['participation_threshold']:<6} kind={b['kind']:<22} "
          f"max_capital_linear={b.get('max_capital_linear')}  status={b.get('status')}  reason={b.get('reason')}")
print()
ok_numbers = all(
    abs(a["max_capital_linear"] - b["max_capital_linear"]) < 1e-6
    for a, b in zip(bounds, new_bounds)
    if b.get("max_capital_linear") is not None
)
print("R2 numbers preserved (same thresholds, same maxima)      :", ok_numbers)
print("R1 every entry carries a contract status                  :",
      all(r.get("status") in {"DATA_BLOCKED", "UNRESOLVED", "NO_ECONOMIC_CLAIM"} for r in new_bounds))
print("R1 no entry published under a MEASURED_* kind             :",
      all(not str(r.get("kind", "")).startswith("MEASURED") for r in new_bounds))
print("R2 observed scale still published in the same entry       :",
      all(r.get("observed_peak_participation") == peak for r in new_bounds))
