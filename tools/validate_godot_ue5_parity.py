#!/usr/bin/env python3
"""Validate that Godot and UE5 consume the same approved Chapter One snapshot."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "models" / "chapter_one_snapshot.json"
DEFAULT_GODOT = Path("/Applications/Godot.app/Contents/MacOS/Godot")
DEFAULT_UE_EDITOR = Path("/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd")
DEFAULT_UE_PROJECT = Path("/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE/EdgeWorldUE.uproject")
MARKER_PATTERN = re.compile(
    r"schema=(?P<schema>\S+) spirits=(?P<spirits>\d+) primary=(?P<primary>\S+) "
    r"changed=(?P<changed>\S+) houtian=(?P<houtian>[^/\s]+)/(?P<direction>[^/\s]+)/(?P<number>\d+)"
)


def expected_contract(snapshot_path: Path) -> dict[str, str | int]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    transition = payload["cosmology"]["houtian_transition"]
    return {
        "schema": payload["schema_version"],
        "spirits": len(payload["spirits"]),
        "primary": payload["encounter"]["primary_hexagram"]["name"],
        "changed": payload["encounter"]["changed_hexagram"]["name"],
        "houtian": transition["focus_spirit"],
        "direction": transition["direction"],
        "number": transition["luoshu_number"],
    }


def run_and_parse(name: str, command: list[str], environment: dict[str, str]) -> dict[str, str | int]:
    # UE may start trace/storage helpers that inherit stdout. A PIPE would stay
    # open after the commandlet exits, so communicate() could wait forever for
    # EOF. A seekable file captures the same diagnostics without that coupling.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output_file:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=output_file,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
        )
        output_file.flush()
        output_file.seek(0)
        output = output_file.read()
    if completed.returncode != 0:
        raise RuntimeError(f"{name} exited with {completed.returncode}:\n{output[-4000:]}")
    marker = MARKER_PATTERN.search(output)
    if marker is None:
        raise RuntimeError(f"{name} did not emit a Chapter One validation marker:\n{output[-4000:]}")
    parsed: dict[str, str | int] = marker.groupdict()
    parsed["spirits"] = int(parsed["spirits"])
    parsed["number"] = int(parsed["number"])
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--godot", type=Path, default=DEFAULT_GODOT)
    parser.add_argument("--ue-editor", type=Path, default=DEFAULT_UE_EDITOR)
    parser.add_argument("--ue-project", type=Path, default=DEFAULT_UE_PROJECT)
    args = parser.parse_args()

    expected = expected_contract(args.snapshot.resolve())
    environment = os.environ.copy()
    environment["EDGEWORLD_CHAPTER_ONE_JSON"] = str(args.snapshot.resolve())
    godot = run_and_parse(
        "Godot",
        [str(args.godot), "--headless", "--path", str(ROOT / "engine_platforms" / "godot"), "--quit-after", "2"],
        environment,
    )
    ue5 = run_and_parse(
        "UE5",
        [str(args.ue_editor), str(args.ue_project), "-run=EdgeWorldSnapshot", "-unattended", "-nop4", "-nullrhi", "-nosplash"],
        environment,
    )

    if godot != expected or ue5 != expected:
        print(json.dumps({"status": "mismatch", "expected": expected, "godot": godot, "ue5": ue5}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "match", "snapshot": str(args.snapshot.resolve()), "godot": godot, "ue5": ue5}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
