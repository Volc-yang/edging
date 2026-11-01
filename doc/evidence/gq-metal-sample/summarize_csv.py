"""Summarize UE CSV frame columns without silently discarding samples."""

import csv
import json
import math
import sys


def percentile_nearest_rank(values, percentile):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def main(path):
    csv.field_size_limit(10_000_000)
    with open(path, newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = [row for row in reader if row and row[0] != "EVENTS" and len(row) >= len(header)]
    result = {"frame_rows": len(rows), "percentile_method": "nearest rank"}
    for column in ("FrameTime", "GameThreadTime", "RenderThreadTime", "GPUTime"):
        index = header.index(column)
        parsed = []
        for row in rows:
            try:
                number = float(row[index])
            except ValueError:
                continue
            if math.isfinite(number):
                parsed.append(number)
        positive = [number for number in parsed if number > 0]
        result[column] = {
            "numeric": len(parsed),
            "positive": len(positive),
            "zero": sum(number == 0 for number in parsed),
            "p50_positive_ms": percentile_nearest_rank(positive, 0.5) if positive else None,
            "p95_positive_ms": percentile_nearest_rank(positive, 0.95) if positive else None,
            "max_positive_ms": max(positive) if positive else None,
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
