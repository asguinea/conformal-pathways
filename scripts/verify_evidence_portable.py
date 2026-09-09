"""Verify evidence with a narrow cross-platform allowance for interval arithmetic.

File hashes, design, counts, means, ranges and identifiers must match exactly.
Only recomputed interval endpoints may differ, by at most 1e-12 absolute. This
does not replace the frozen exact experiment/reproduction comparison.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path

from conformal_pathways.benchmarks import reporting, sequential_reporting

INTERVAL_FIELDS = {"interval_low", "interval_high"}
INTERVAL_ATOL = 1e-12


def compare_value(expected, actual, field, differences):
    if expected == actual:
        return
    if field not in INTERVAL_FIELDS:
        raise ValueError(f"Non-interval field changed: {field}: {expected!r} != {actual!r}")
    if isinstance(expected, bool) or isinstance(actual, bool):
        raise ValueError("Boolean value in numerical interval")
    if expected is None or actual is None or expected == "" or actual == "":
        raise ValueError("Interval availability changed")
    try:
        left, right = float(expected), float(actual)
    except (TypeError, ValueError) as error:
        raise ValueError("Non-numerical interval endpoint") from error
    if not math.isfinite(left) or not math.isfinite(right):
        raise ValueError("Non-finite interval endpoint")
    distance = abs(left - right)
    if distance > INTERVAL_ATOL:
        raise ValueError(f"Interval difference exceeds {INTERVAL_ATOL}: {distance}")
    differences.append({"field": field, "absolute_difference": distance})


def compare_rows(expected, actual, differences):
    if len(expected) != len(actual):
        raise ValueError("Row count changed")
    for left, right in zip(expected, actual, strict=True):
        if list(left) != list(right):
            raise ValueError("Columns or their order changed")
        for field in left:
            compare_value(left[field], right[field], field, differences)


def csv_rows(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return list(csv.DictReader(io.StringIO(stream.getvalue())))


def verify(path):
    path = Path(path)
    evidence = json.loads((path / "evidence.json").read_text())
    sequential = evidence["protocol"]["algorithm_version"] == "result-aware-pathways-v1"
    strict_verifier = (
        sequential_reporting.verify_public if sequential else reporting.verify_public_evidence
    )
    try:
        result = strict_verifier(path)
        return {**result, "mode": "exact", "interval_differences": 0, "max_absolute_difference": 0}
    except ValueError as error:
        # These exceptions occur only after the original hash and complete-design
        # checks. Missing files, corrupt content, or an incomplete design still fail.
        if str(error) not in {
            "summary does not regenerate",
            "table does not regenerate",
            "public summary cannot be regenerated",
            "public table cannot be regenerated: summary.csv",
            "public table cannot be regenerated: paired.csv",
        }:
            raise
    rows = [json.loads(line) for line in (path / "trials.jsonl").read_text().splitlines()]
    aggregate = sequential_reporting.aggregate if sequential else reporting.aggregate_records
    summary, paired = aggregate(rows, evidence["protocol"]["statistics"]["confidence"])
    differences = []
    # JSON object ordering is immaterial; CSV column ordering must remain exact.
    expected_summary = json.loads((path / "summary.json").read_text())
    normalized_summary = [{key: row[key] for key in sorted(row)} for row in summary]
    compare_rows(expected_summary, normalized_summary, differences)
    for name, generated in (("summary.csv", summary), ("paired.csv", paired)):
        with (path / name).open(newline="") as handle:
            expected = list(csv.DictReader(handle))
        compare_rows(expected, csv_rows(generated), differences)
    return {
        "status": "passed",
        "mode": "portable_interval_arithmetic",
        "records": len(rows),
        "summary_rows": len(summary),
        "paired_rows": len(paired),
        "interval_absolute_tolerance": INTERVAL_ATOL,
        "interval_differences": len(differences),
        "max_absolute_difference": max((d["absolute_difference"] for d in differences), default=0),
        "differing_fields": sorted({d["field"] for d in differences}),
        "exact_requirements": "file bytes/hashes, complete design, counts, means, ranges, identifiers",
        "scope": "aggregate interval arithmetic only; not exact experiment reproduction",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.path), indent=2))
