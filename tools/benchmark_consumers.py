#!/usr/bin/env python3
"""Measure the two Chapter One engine consumers (risk R8).

Nothing in the project had measured Godot against UE5: the comparison document
listed startup time, memory, frame time and resource build cost as "next
stage items" with no data behind them. This script produces the first
repeatable numbers so the engine-line decision is not made on impressions.

Usage::

    python3 tools/benchmark_consumers.py                 # 3 runs each
    python3 tools/benchmark_consumers.py --runs 5 --json report.json

It measures, per consumer:

* wall-clock time of a headless cold run,
* peak resident set size,
* the size of the artifact that has to be built and shipped.

It is honest about what it cannot measure: it does **not** render frames, so
frame time is reported as unavailable rather than invented. Add a rendering
harness before claiming any frame-rate numbers.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GODOT = Path("/Applications/Godot.app/Contents/MacOS/Godot")
DEFAULT_UE_EDITOR = Path("/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd")
DEFAULT_UE_PROJECT = Path("/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE")
DEFAULT_SNAPSHOT = ROOT / "models" / "chapter_one_snapshot.json"

GODOT_PROJECT = ROOT / "engine_platforms" / "godot"
GODOT_MARKER = "EDGEWORLD_GODOT_CHAPTER_ONE_VALID"
UE5_MARKER = "EDGEWORLD_UE_CHAPTER_ONE_VALID"


def _peak_child_rss_bytes() -> Optional[int]:
    """Peak RSS across children already waited for.

    ``resource.getrusage(RUSAGE_CHILDREN).ru_maxrss`` is a high-water mark over
    all reaped children, not a per-process figure. Runs are sequential and the
    value is recorded per run, so the reported number is the peak observed for
    the consumer being measured (and never lower than it).
    """
    try:
        import resource
    except ImportError:
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    value = int(usage.ru_maxrss)
    # macOS reports bytes, Linux kilobytes.
    if sys.platform != "darwin":
        value *= 1024
    return value or None


TIME_BINARY = Path("/usr/bin/time")


def _parse_time_l(output: str) -> Optional[int]:
    """Parse macOS ``/usr/bin/time -l`` peak RSS (bytes)."""
    for line in output.splitlines():
        if "maximum resident set size" in line:
            parts = line.split()
            if parts and parts[0].isdigit():
                return int(parts[0])
    return None


def measure(command: list[str], environment: dict[str, str], marker: str, runs: int) -> dict[str, Any]:
    durations: list[float] = []
    peaks: list[int] = []
    marker_seen = False
    last_error = ""

    # /usr/bin/time -l measures the child exactly; RUSAGE_CHILDREN is only a
    # high-water mark across every child the harness has reaped, so it is used
    # only as a fallback and is labelled as such.
    use_time_l = TIME_BINARY.exists()
    wrapped = [str(TIME_BINARY), "-l"] + command if use_time_l else command

    for _ in range(runs):
        started = time.perf_counter()
        process = subprocess.Popen(
            wrapped,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment,
            cwd=str(ROOT),
        )
        output, _ = process.communicate()
        elapsed = time.perf_counter() - started
        text = (output or b"").decode("utf-8", errors="replace")
        if marker in text:
            marker_seen = True
        elif not last_error:
            last_error = text.strip().splitlines()[-1][:300] if text.strip() else f"exit {process.returncode}"
        durations.append(elapsed)

        peak = _parse_time_l(text) if use_time_l else None
        if peak is None:
            peak = _peak_child_rss_bytes()
        if peak:
            peaks.append(peak)

    return {
        "runs": runs,
        "marker_seen": marker_seen,
        "seconds_median": round(statistics.median(durations), 3),
        "seconds_min": round(min(durations), 3),
        "seconds_max": round(max(durations), 3),
        "peak_rss_mb": round(max(peaks) / (1024 * 1024), 1) if peaks else None,
        "peak_rss_source": "time -l (exact child)" if use_time_l and peaks else "rusage high-water mark",
        "note": "" if marker_seen else last_error,
    }


def artifact_size(path: Path) -> Optional[int]:
    return path.stat().st_size if path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--godot", type=Path, default=DEFAULT_GODOT)
    parser.add_argument("--ue-editor", type=Path, default=DEFAULT_UE_EDITOR)
    parser.add_argument("--ue-project", type=Path, default=DEFAULT_UE_PROJECT)
    parser.add_argument("--json", type=Path, help="Also write the report as JSON.")
    args = parser.parse_args()

    environment = os.environ.copy()
    environment["EDGEWORLD_CHAPTER_ONE_JSON"] = str(args.snapshot.resolve())

    report: dict[str, Any] = {
        "snapshot": str(args.snapshot.resolve()),
        "runs": args.runs,
        "consumers": {},
    }

    if args.godot.exists():
        report["consumers"]["godot"] = measure(
            [str(args.godot), "--headless", "--path", str(GODOT_PROJECT), "--quit"],
            environment,
            GODOT_MARKER,
            args.runs,
        )
        report["consumers"]["godot"]["artifact_bytes"] = artifact_size(args.godot)
    else:
        report["consumers"]["godot"] = {"available": False, "reason": f"not found: {args.godot}"}

    project_file = args.ue_project / "EdgeWorldUE.uproject"
    if args.ue_editor.exists() and project_file.exists():
        report["consumers"]["ue5"] = measure(
            [
                str(args.ue_editor),
                str(project_file),
                "-run=EdgeWorldSnapshot",
                "-unattended",
                "-nop4",
                "-nullrhi",
            ],
            environment,
            UE5_MARKER,
            args.runs,
        )
        module = args.ue_project / "Binaries" / "Mac" / "libUnrealEditor-EdgeWorldUE.dylib"
        report["consumers"]["ue5"]["project_module_bytes"] = artifact_size(module)
    else:
        report["consumers"]["ue5"] = {"available": False, "reason": f"not found: {project_file}"}

    report["not_measured"] = {
        "frame_time": "no rendering harness; headless runs do not produce frames",
        "asset_build_cost": "editor asset build was not measured",
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
