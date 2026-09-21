#!/usr/bin/env python3
"""Inspect, verify and replay the Chapter One round history.

Usage::

    python3 tools/chapter_one_history.py list
    python3 tools/chapter_one_history.py show 7
    python3 tools/chapter_one_history.py show 7 --field encounter.governing_line.name
    python3 tools/chapter_one_history.py verify
    python3 tools/chapter_one_history.py migrate 7 --to edgeworld.chapter-one-snapshot.v2
    python3 tools/chapter_one_history.py export-replay /tmp/replay.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from chapter_one_history import ChapterOneHistory, load_live_snapshot
from snapshot_store import SnapshotError


def _dig(payload: Mapping[str, Any], dotted: str) -> Any:
    current: Any = payload
    for key in dotted.split("."):
        if isinstance(current, Mapping) and key in current:
            current = current[key]
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            return None
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", type=Path, default=ROOT / "models", help="Models directory holding the history.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List archived rounds in order.")

    show = sub.add_parser("show", help="Print one archived round.")
    show.add_argument("tick", type=int)
    show.add_argument("--field", help="Print only this dotted field, e.g. encounter.changed_hexagram.name")

    sub.add_parser("verify", help="Recompute the hash chain and report inconsistencies.")

    migrate = sub.add_parser("migrate", help="Migrate an archived round to another schema version.")
    migrate.add_argument("tick", type=int)
    migrate.add_argument("--to", required=True, dest="target_schema")

    export = sub.add_parser("export-replay", help="Write an ordered replay bundle of every archived round.")
    export.add_argument("output", type=Path)

    sub.add_parser(
        "import-snapshot",
        help="Archive the current live snapshot as-is, without recomputing it (back-fill).",
    ).add_argument("--source", default="imported")

    args = parser.parse_args()
    history = ChapterOneHistory(args.models)

    try:
        if args.command == "list":
            entries = history.entries()
            if not entries:
                print("no archived rounds yet")
                return 0
            print(f"{'tick':>6}  {'score':>7}  {'本卦':<6} {'变卦':<6} {'来源':<24} recorded_at")
            for entry in entries:
                print(
                    f"{entry['tick']:>6}  {str(entry.get('chapter_score')):>7}  "
                    f"{str(entry.get('encounter')):<6} {str(entry.get('changed_hexagram')):<6} "
                    f"{str(entry.get('source')):<24} {entry.get('recorded_at', '')}"
                )
            return 0

        if args.command == "show":
            snapshot = history.load(args.tick)
            if args.field:
                value = _dig(snapshot, args.field)
                print(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
            else:
                print(json.dumps(snapshot, ensure_ascii=False, indent=2))
            return 0

        if args.command == "verify":
            report = history.verify()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ok"] else 1

        if args.command == "migrate":
            migrated = history.migrate_round(args.tick, args.target_schema)
            print(json.dumps(migrated, ensure_ascii=False, indent=2))
            return 0

        if args.command == "import-snapshot":
            live = load_live_snapshot(args.models)
            if live is None:
                print(json.dumps({"error": "no_live_snapshot", "detail": str(args.models / "chapter_one_snapshot.json")}, ensure_ascii=False))
                return 2
            entry = history.append(live, source=args.source)
            print(json.dumps({"archived_round": entry["file"], "tick": entry["tick"], "sha256": entry["sha256"]}, ensure_ascii=False))
            return 0

        if args.command == "export-replay":
            bundle = {
                "schema_version": "edgeworld.chapter-one-replay.v1",
                "source_index": history.index(),
                "rounds": list(history.iter_rounds()),
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(args.output.resolve()), "rounds": len(bundle["rounds"])}, ensure_ascii=False))
            return 0
    except SnapshotError as exc:
        print(json.dumps({"error": "history_error", "detail": str(exc)}, ensure_ascii=False))
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
