#!/usr/bin/env python3
"""Fail-closed structural audit for a P4 full-run artifact set.

This audit deliberately does not infer that a non-empty registry means that
the corpus was covered.  It compares the checkpoint with the detailed run
artifact and reports duplicate claim references as an observation, because a
claim reference is not a globally unique key in the P4 contract.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return sorted(duplicate)


def audit(full_run: dict[str, Any], checkpoint: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    ledger = full_run.get("ledger")
    rounds_ledger = full_run.get("rounds_ledger")
    if not isinstance(ledger, dict):
        errors.append("full_run.ledger is missing or is not an object")
        ledger = {}
    if not isinstance(rounds_ledger, list):
        errors.append("full_run.rounds_ledger is missing or is not an array")
        rounds_ledger = []

    ledger_books = sorted(ledger)
    checkpoint_books = sorted(checkpoint.get("processed_books", []))
    if ledger_books != checkpoint_books:
        errors.append(
            "checkpoint processed_books differs from full_run ledger keys "
            f"(checkpoint={len(checkpoint_books)}, ledger={len(ledger_books)})"
        )
    if checkpoint.get("books_processed_total") != len(ledger_books):
        errors.append("checkpoint books_processed_total does not match ledger")
    if checkpoint.get("books_processed_total") != len(checkpoint_books):
        errors.append("checkpoint books_processed_total does not match processed_books")

    claims_by_book = 0
    corr_by_book = 0
    book_round_mismatches: list[str] = []
    for book_id, entry in ledger.items():
        if not isinstance(entry, dict):
            errors.append(f"ledger entry is not an object: {book_id}")
            continue
        claims = entry.get("claims_processed")
        corr = entry.get("corroborations")
        if not isinstance(claims, int) or claims < 0:
            errors.append(f"invalid claims_processed for {book_id}")
        else:
            claims_by_book += claims
        if not isinstance(corr, int) or corr < 0:
            errors.append(f"invalid corroborations for {book_id}")
        else:
            corr_by_book += corr
        rounds = [r for r in rounds_ledger if book_id in (r.get("books") or [])]
        if len(rounds) != 1:
            book_round_mismatches.append(book_id)
        elif rounds[0].get("round") != entry.get("round"):
            book_round_mismatches.append(book_id)
    if book_round_mismatches:
        errors.append("book-to-round mapping is missing or inconsistent: " + ", ".join(book_round_mismatches))

    if claims_by_book != sum([
        int(entry.get("claims_processed", 0))
        for entry in ledger.values()
        if isinstance(entry, dict)
    ]):
        errors.append("internal claims ledger sum is not stable")

    full_corr = full_run.get("corroborations")
    if not isinstance(full_corr, list):
        errors.append("full_run.corroborations is missing or is not an array")
        full_corr = []
    if full_run.get("counts", {}).get("corroborations") != len(full_corr):
        errors.append("full_run counts.corroborations does not match the array")
    if full_run.get("corroborations") is not None and corr_by_book != len(full_corr):
        warnings.append(
            "per-book corroboration ledger does not equal the global corroboration array "
            f"(ledger={corr_by_book}, array={len(full_corr)})"
        )

    counts = full_run.get("counts") if isinstance(full_run.get("counts"), dict) else {}
    generic_count = full_run.get("generic_count")
    dropped = full_run.get("dropped")
    if generic_count != counts.get("generic"):
        errors.append("full_run generic_count does not match counts.generic")
    if not isinstance(dropped, list) or len(dropped) != counts.get("dropped_unreferencable"):
        errors.append("full_run dropped array does not match counts.dropped_unreferencable")
    if (
        isinstance(generic_count, int)
        and isinstance(dropped, list)
        and claims_by_book != len(full_corr) + generic_count
    ):
        errors.append(
            "per-book claims do not close over corroborations + generic "
            f"(books={claims_by_book}, categorized={len(full_corr) + generic_count})"
        )
    if (
        isinstance(dropped, list)
        and sum((counts.get("corroborations", 0), counts.get("generic", 0), len(dropped)))
        != checkpoint.get("corroborations_total", 0)
        + checkpoint.get("generic_total", 0)
        + checkpoint.get("dropped_unreferencable", 0)
    ):
        errors.append("checkpoint category totals do not close")
    for field, checkpoint_field in (
        ("corroborations", "corroborations_total"),
        ("generic", "generic_total"),
        ("dropped_unreferencable", "dropped_unreferencable"),
    ):
        if counts.get(field) != checkpoint.get(checkpoint_field):
            errors.append(f"checkpoint {checkpoint_field} disagrees with full_run counts.{field}")

    expected_rounds = sorted(r.get("round") for r in rounds_ledger)
    actual_rounds = sorted(full_run.get("rounds_executed", []))
    if expected_rounds != actual_rounds:
        errors.append("rounds_executed disagrees with rounds_ledger")

    refs = [str(item.get("claim_ref")) for item in full_corr if item.get("claim_ref") is not None]
    duplicate_refs = _duplicates(refs)
    if duplicate_refs:
        warnings.append(f"duplicate claim_ref values are present ({len(duplicate_refs)} distinct refs)")

    note = str(checkpoint.get("note", ""))
    note_numbers = [int(x) for x in re.findall(r"(\d+)\s+(?:corr|generic|dropped)", note)]
    if note_numbers and note_numbers != [
        checkpoint.get("corroborations_total"),
        checkpoint.get("generic_total"),
        checkpoint.get("dropped_unreferencable"),
    ]:
        errors.append("checkpoint note contains counts different from checkpoint fields")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "observed": {
            "ledger_books": len(ledger_books),
            "claims_by_book": claims_by_book,
            "corroborations_by_book": corr_by_book,
            "corroborations_array": len(full_corr),
            "duplicate_claim_refs": duplicate_refs,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-run", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(_load(args.full_run), _load(args.checkpoint))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "errors": [str(exc)], "warnings": []}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
