# Specification decisions

## D1 - Funding attribution is boundary-plus-receipt

A settlement is chargeable at `max(venue_boundary, local_receipt)`. Charging at the boundary alone would date cash before it was observable; charging at receipt alone would move the economic boundary. Both instants are recorded, the shift is counted in `funding_receipt_shifted`, and a record that becomes knowable only after the replayed window closes is excluded and counted in `funding_out_of_window`.

## D2 - Repeated records are not merged silently

Two records for the same instrument and boundary would charge one opening twice. The second is dropped and counted in `funding_duplicate_boundary`; the count is published so the exclusion is visible.

## D3 - Funding marks are bounded historical proxies

The mark is the latest bar closing at or before the boundary whose availability is also at or before the boundary. Staleness beyond one bar duration returns `None`. The basis is published as `OHLC_CLOSE_ASOF_BOUNDED_HISTORICAL_MODEL_NOT_VENUE_MARK`; `settlements.py` already forbids backdated account updates for economic decisions, and this change does not weaken that rule.

## D4 - Paper replay fails closed instead of guessing

`_refuse_unattributed_delayed_funding` refuses to publish a simulated balance when an instrument was open at the boundary or at receipt and the settlement arrived late. Closes exactly on the boundary are also refused: equal-time close/funding ordering is not established by the snapshot.

## D5 - G5 needs provenance, not a plausible story

Four stress transformations of one strategy are not a selection family. `evaluate_g5_selection_control` therefore keeps computing DSR, Bonferroni and the White reality check as diagnostics but returns `BLOCKED` with `MISSING_PROVENANCE_BOUND_SELECTION_HISTORY` until a provenance-bound family exists. The declared `multiplicity_trials` still widens the correction and is never widened by the diagnostic variants.

## D6 - Monte Carlo p-values are versioned

`PLUS_ONE_V1` reports `(exceedances + 1) / (reps + 1)` so a finite resampling can never report p = 0. `LEGACY_EXCEED_OVER_REPS_V1` reproduces the old values bit-for-bit for existing evidence. Resolution `1/(reps+1)` and the limitation text travel with the value; the arch library path is labelled a raw finite-bootstrap diagnostic, not an exact test.

## D7 - Tape paths are portable and missing data is loud

Resolution order is explicit argument, `V8_TAPE_PATH`, then a repository-relative default. Relative overrides resolve against the repository, not the shell CWD, and a missing tape raises `FileNotFoundError` instead of producing an empty run.

## Conflicts and fail-closed choices

- D1 does not extend to the paper engine's own exposure snapshots; #2 stays `BLOCKED` there.
- D5 removes any route to a G5 PASS, which is intended: no authority receipt exists.
- No economic claim is minted; `NO_ECONOMIC_CLAIM` remains in force.
